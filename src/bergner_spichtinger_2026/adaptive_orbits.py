"""Deterministic h/r adaptive collocation helpers for Episode 008.

The routines in this module are intentionally small and transparent.  They do
not make remeshing a native nonlinear-solver operation; they compute the v1
external defect, monitor, marking, movement, transfer, and retry decisions used
by the Python reference before a fixed-parameter correction is restarted on the
new mesh.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Literal

import numpy as np

from .collocation_coefficients import CollocationRule
from .core import process_terms
from .periodic_orbits import (
    STATE_DIMENSION,
    ArrayLike,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    IndependentDefectDiagnostics,
    MidpointCorrectionResult,
    MidpointResidualTolerances,
    OrbitLayout,
    _positive_integer,
    correct_gauss_orbit,
    transformed_vector_field,
)
from .residuals import physical_state_from_log_coordinates

ADAPTIVE_METHOD_VERSION = "external-gauss3-hr-adaptive-v1"
MONITOR_VERSION = "composite-r-monitor-v1"
H_MARKING_VERSION = "defect-bulk-halfmax-marking-v1"
R_MOVEMENT_VERSION = "global-beta-r-movement-v1"
ADAPTIVE_CONTROLLER_VERSION = "adaptive-cycle-controller-v1"
RESTART_RETRY_VERSION = "fixed-parameter-remesh-restart-retry-v1"
MONITOR_SUBCELLS_PER_ELEMENT = 16
DEFECT_ACCEPTANCE_TOLERANCE = 1.0e-4
PERIOD_ORBIT_CONVERGENCE_TOLERANCE = 1.0e-3
SOFT_INTERVAL_CAP = 256
HARD_INTERVAL_CAP = 512
CYCLE_BUDGET = 8


@dataclass(frozen=True)
class NormalizedMonitorDensity:
    """One raw density and its deterministic normalized contribution."""

    name: str
    raw: np.ndarray
    maximum: float
    weighted_average_after_max_rescale: float
    weighted_average_after_winsorization: float
    normalized: np.ndarray


@dataclass(frozen=True)
class CompositeMonitor:
    """Piecewise-constant v1 r-redistribution monitor on old subcells."""

    version: str
    subcell_midpoint_phases: np.ndarray
    subcell_widths: np.ndarray
    densities: tuple[NormalizedMonitorDensity, ...]
    values: np.ndarray
    total_mass: float
    cumulative_upper: np.ndarray
    target_boundaries: np.ndarray


@dataclass(frozen=True)
class HMarkingResult:
    """Deterministic defect-driven h-marking decision."""

    version: str
    marked_elements: tuple[int, ...]
    uncapped_marked_elements: tuple[int, ...]
    growth_limit: int
    new_interval_count: int
    bulk_fraction: float
    halfmax_threshold: float


@dataclass(frozen=True)
class RMovementResult:
    """Result of simultaneous globally relaxed r movement."""

    version: str
    accepted: bool
    stalled: bool
    beta: float
    attempted_betas: tuple[float, ...]
    old_boundaries: np.ndarray
    target_boundaries: np.ndarray
    new_boundaries: np.ndarray
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class AdaptationCycleDecision:
    """High-level deterministic controller outcome for one corrected mesh."""

    version: str
    action: Literal[
        "stop_converged",
        "ordinary_h_r",
        "pure_r",
        "forced_single_split_h_r",
        "mesh_cap_escalation",
        "resolution_unresolved",
    ]
    terminal_status: Literal["continue", "converged", "resolution_unresolved"]
    force_split_element: int | None
    permit_hard_cap: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RestartAttempt:
    """One deterministic fixed-parameter restart attempt."""

    name: str
    refresh_phase_reference: bool
    apply_fixed_parameter_correction: bool
    rebootstrap_tangent: bool
    accept_tangent_failure: bool = False


@dataclass(frozen=True)
class RestartPlan:
    """The exact v1 attempt order for a remesh restart."""

    version: str
    context: str
    attempts: tuple[RestartAttempt, ...]


@dataclass(frozen=True)
class RestartGateDiagnostics:
    """Independent gates applied after a fixed-parameter remesh correction."""

    residual_gate: bool
    phase_gate: bool
    positivity_gate: bool
    finite_change_gate: bool
    tangent_gate: bool
    packed_change_norm: float
    tangent_norm: float | None
    rejection_reasons: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return not self.rejection_reasons


@dataclass(frozen=True)
class RemeshRestartAttemptResult:
    """One executed remesh-restart attempt and its gates."""

    attempt: RestartAttempt
    correction: MidpointCorrectionResult | None
    gates: RestartGateDiagnostics
    tangent: np.ndarray | None


@dataclass(frozen=True)
class RemeshRestartResult:
    """Executed v1 restart plan with correction and tangent-gate evidence."""

    version: str
    plan: RestartPlan
    accepted: bool
    attempts: tuple[RemeshRestartAttemptResult, ...]
    unknowns: np.ndarray
    tangent: np.ndarray | None
    rejection_reasons: tuple[str, ...]


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, dtype=float, copy=True)
    result.setflags(write=False)
    return result


def _sample_phases(mesh: FixedMesh) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    local = (np.arange(MONITOR_SUBCELLS_PER_ELEMENT, dtype=float) + 0.5) / MONITOR_SUBCELLS_PER_ELEMENT
    phases = mesh.stage_phases(local)
    widths = np.repeat(mesh.widths / MONITOR_SUBCELLS_PER_ELEMENT, MONITOR_SUBCELLS_PER_ELEMENT)
    intervals = np.repeat(np.arange(mesh.interval_count), MONITOR_SUBCELLS_PER_ELEMENT)
    local_flat = np.tile(local, mesh.interval_count)
    return phases.reshape(-1), widths, intervals, local_flat


def _polynomial_second_derivative_evaluator(assembler: GaussCollocationAssembler, unknowns: ArrayLike):
    variables = assembler.layout.unpack(np.asarray(unknowns, dtype=float))
    period = exp(variables.log_period)
    field, _ = assembler._stage_model_values(variables.stages, with_jacobian=False)
    coefficients = np.asarray(assembler.rule.transfer_coefficients)
    second_coefficients = coefficients[:, 2:] * (
        np.arange(2, coefficients.shape[1])[None, :] * np.arange(1, coefficients.shape[1] - 1)[None, :]
    )
    boundaries = assembler.mesh.boundaries

    def evaluate(phases: ArrayLike) -> np.ndarray:
        values = np.asarray(phases, dtype=float)
        scalar = values.ndim == 0
        flat = np.mod(values.reshape(-1), 1.0)
        intervals = np.searchsorted(boundaries, flat, side="right") - 1
        intervals = np.clip(intervals, 0, assembler.layout.interval_count - 1)
        tau = (flat - boundaries[intervals]) / assembler.mesh.widths[intervals]
        if second_coefficients.shape[1] == 0:
            result = np.zeros((flat.size, STATE_DIMENSION))
        else:
            powers = tau[:, None] ** np.arange(second_coefficients.shape[1])[None, :]
            lagrange_prime = powers @ second_coefficients.T
            result = np.empty((flat.size, STATE_DIMENSION))
            for row, interval in enumerate(intervals):
                result[row] = (period / assembler.mesh.widths[interval]) * np.einsum(
                    "j,jq->q", lagrange_prime[row], field[interval]
                )
        return result[0] if scalar else result.reshape(values.shape + (STATE_DIMENSION,))

    return evaluate


def _monitor_defect_density(assembler: GaussCollocationAssembler, unknowns: ArrayLike, phases: np.ndarray) -> np.ndarray:
    variables = assembler.layout.unpack(np.asarray(unknowns, dtype=float))
    period = exp(variables.log_period)
    states = assembler.polynomial_evaluator(unknowns)(phases)
    slopes = assembler.polynomial_derivative_evaluator(unknowns)(phases)
    ode = np.array([period * transformed_vector_field(state, assembler.env, assembler.coeff) for state in states])
    return np.linalg.norm((slopes - ode) * assembler.state_scaling, axis=1) / (
        1.0 + np.linalg.norm(ode * assembler.state_scaling, axis=1)
    )


def _nucleation_density(assembler: GaussCollocationAssembler, unknowns: ArrayLike, phases: np.ndarray) -> np.ndarray:
    variables = assembler.layout.unpack(np.asarray(unknowns, dtype=float))
    period = exp(variables.log_period)
    states = assembler.polynomial_evaluator(unknowns)(phases)
    values = np.empty((states.shape[0], STATE_DIMENSION), dtype=float)
    for row, state in enumerate(states):
        n, q, s = physical_state_from_log_coordinates(state)
        terms = process_terms(float(n), float(q), float(s), assembler.env, assembler.coeff)
        values[row] = [terms["Nuc_n"] / n, terms["Nuc_q"] / q, terms["Nuc_s"]]
    return np.linalg.norm(period * values * assembler.state_scaling, axis=1)


def normalize_monitor_density(name: str, raw: ArrayLike, weights: ArrayLike) -> NormalizedMonitorDensity:
    """Normalize one nonnegative density by the documented v1 order."""
    raw_array = np.asarray(raw, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    if raw_array.ndim != 1 or weight_array.shape != raw_array.shape:
        raise ValueError("raw density and weights must be one-dimensional arrays with identical shape.")
    if not np.all(np.isfinite(raw_array)) or np.any(raw_array < 0.0):
        raise ValueError(f"density {name!r} contains a nonfinite or negative sample.")
    if not np.all(np.isfinite(weight_array)) or np.any(weight_array <= 0.0):
        raise ValueError("monitor weights must be finite and positive.")
    maximum = float(np.max(raw_array)) if raw_array.size else 0.0
    if maximum == 0.0:
        normalized = np.zeros_like(raw_array)
        first_average = 0.0
        second_average = 0.0
    else:
        max_rescaled = raw_array / maximum
        first_average = float(np.sum(weight_array * max_rescaled))
        if first_average <= 0.0 or not np.isfinite(first_average):
            raise ValueError(f"density {name!r} has invalid weighted average after max rescaling.")
        phase_normalized = max_rescaled / first_average
        winsorized = np.minimum(phase_normalized, 20.0)
        second_average = float(np.sum(weight_array * winsorized))
        if second_average <= 0.0 or not np.isfinite(second_average):
            raise ValueError(f"density {name!r} has invalid weighted average after winsorization.")
        normalized = winsorized / second_average
    return NormalizedMonitorDensity(
        name=name,
        raw=_readonly(raw_array),
        maximum=maximum,
        weighted_average_after_max_rescale=first_average,
        weighted_average_after_winsorization=second_average,
        normalized=_readonly(normalized),
    )


def build_composite_r_monitor(assembler: GaussCollocationAssembler, unknowns: ArrayLike) -> CompositeMonitor:
    """Evaluate and invert the v1 composite r monitor at 16 subcells per element."""
    phases, weights, _, _ = _sample_phases(assembler.mesh)
    derivative = assembler.polynomial_derivative_evaluator(unknowns)(phases)
    curvature = _polynomial_second_derivative_evaluator(assembler, unknowns)(phases)
    raw = {
        "D": _monitor_defect_density(assembler, unknowns, phases),
        "V": np.linalg.norm(derivative * assembler.state_scaling, axis=1),
        "C": np.linalg.norm(curvature * assembler.state_scaling, axis=1),
        "A_nuc": _nucleation_density(assembler, unknowns, phases),
    }
    densities = tuple(normalize_monitor_density(name, raw[name], weights) for name in ("D", "V", "C", "A_nuc"))
    by_name = {density.name: density.normalized for density in densities}
    values = 0.20 + 0.80 * (
        0.50 * by_name["D"] + 0.20 * by_name["V"] + 0.20 * by_name["C"] + 0.10 * by_name["A_nuc"]
    )
    masses = weights * values
    cumulative = np.cumsum(masses)
    total = float(cumulative[-1])
    targets = invert_piecewise_constant_monitor(assembler.mesh, values, target_count=assembler.mesh.interval_count)
    return CompositeMonitor(
        version=MONITOR_VERSION,
        subcell_midpoint_phases=_readonly(phases),
        subcell_widths=_readonly(weights),
        densities=densities,
        values=_readonly(values),
        total_mass=total,
        cumulative_upper=_readonly(cumulative),
        target_boundaries=_readonly(targets),
    )


def invert_piecewise_constant_monitor(mesh: FixedMesh, monitor_values: ArrayLike, *, target_count: int) -> np.ndarray:
    """Invert a positive piecewise-constant subcell monitor into ``target_count`` intervals."""
    count = _positive_integer(target_count, "target_count")
    values = np.asarray(monitor_values, dtype=float)
    expected = mesh.interval_count * MONITOR_SUBCELLS_PER_ELEMENT
    if values.shape != (expected,):
        raise ValueError(f"monitor_values must have shape ({expected},), got {values.shape}.")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("monitor values must be finite and positive.")
    sub_widths = np.repeat(mesh.widths / MONITOR_SUBCELLS_PER_ELEMENT, MONITOR_SUBCELLS_PER_ELEMENT)
    lower = np.repeat(mesh.boundaries[:-1], MONITOR_SUBCELLS_PER_ELEMENT) + np.tile(
        np.arange(MONITOR_SUBCELLS_PER_ELEMENT), mesh.interval_count
    ) * sub_widths
    masses = sub_widths * values
    cumulative = np.cumsum(masses)
    total = float(cumulative[-1])
    eps_reach = 64.0 * np.finfo(float).eps * max(1.0, total)
    boundaries = np.empty(count + 1, dtype=float)
    boundaries[0] = 0.0
    boundaries[-1] = 1.0
    previous_upper = 0.0
    cursor = 0
    for j in range(1, count):
        target = total * j / count
        while cursor < cumulative.size - 1 and cumulative[cursor] + eps_reach < target:
            previous_upper = cumulative[cursor]
            cursor += 1
        mass = masses[cursor]
        fraction = 0.0 if mass <= 0.0 else (target - previous_upper) / mass
        fraction = min(1.0, max(0.0, float(fraction)))
        boundaries[j] = lower[cursor] + fraction * sub_widths[cursor]
    return boundaries


def mark_h_refinement(
    defect: IndependentDefectDiagnostics | ArrayLike,
    *,
    current_interval_count: int | None = None,
    max_interval_count: int = SOFT_INTERVAL_CAP,
    growth_fraction: float = 0.5,
) -> HMarkingResult:
    """Mark the smallest deterministic 70%-bulk/half-max defect set, capped by growth."""
    if isinstance(defect, IndependentDefectDiagnostics):
        eta = np.asarray(defect.combined_element_maxima, dtype=float)
    else:
        eta = np.asarray(defect, dtype=float)
    if eta.ndim != 1 or eta.size == 0 or not np.all(np.isfinite(eta)) or np.any(eta < 0.0):
        raise ValueError("defect maxima must be a nonempty finite nonnegative vector.")
    n = eta.size if current_interval_count is None else _positive_integer(current_interval_count, "current_interval_count")
    if n != eta.size:
        raise ValueError("current_interval_count does not match defect vector length.")
    cap = _positive_integer(max_interval_count, "max_interval_count")
    max_growth_splits = int(np.floor(growth_fraction * n))
    split_budget = max(0, min(max_growth_splits, cap - n))
    max_eta = float(np.max(eta))
    halfmax = 0.5 * max_eta
    if max_eta <= 0.0 or split_budget == 0:
        return HMarkingResult(H_MARKING_VERSION, (), (), split_budget, n, 0.70, halfmax)
    order = sorted(range(n), key=lambda i: (-float(eta[i]), i))
    total_square = float(np.sum(eta * eta))
    bulk: set[int] = set()
    running = 0.0
    for i in order:
        if total_square > 0.0 and running >= 0.70 * total_square:
            break
        bulk.add(i)
        running += float(eta[i] * eta[i])
    half = {i for i, value in enumerate(eta) if value >= halfmax}
    uncapped = tuple(sorted(bulk | half, key=lambda i: (-float(eta[i]), i)))
    marked = tuple(uncapped[:split_budget])
    return HMarkingResult(H_MARKING_VERSION, marked, uncapped, split_budget, n + len(marked), 0.70, halfmax)


def bisect_marked_elements(mesh: FixedMesh, marked_elements: Iterable[int]) -> FixedMesh:
    """Bisect marked old elements before r redistribution."""
    marked = {int(i) for i in marked_elements}
    pieces: list[float] = [0.0]
    for i, (left, right) in enumerate(zip(mesh.boundaries[:-1], mesh.boundaries[1:])):
        if i in marked:
            pieces.append(0.5 * (float(left) + float(right)))
        pieces.append(float(right))
    return FixedMesh(np.asarray(pieces, dtype=float))


def apply_global_beta_r_movement(old_mesh: FixedMesh, target_boundaries: ArrayLike) -> RMovementResult:
    """Apply simultaneous global-beta feasibility retries through ``2^-20``."""
    target = np.asarray(target_boundaries, dtype=float)
    if target.shape != old_mesh.boundaries.shape:
        raise ValueError("target_boundaries must have the same shape as old mesh boundaries.")
    if target[0] != 0.0 or target[-1] != 1.0 or np.any(np.diff(target) <= 0.0):
        raise ValueError("target boundaries must be a valid normalized mesh.")
    old = old_mesh.boundaries
    n = old_mesh.interval_count
    attempted: list[float] = []
    last_reasons: tuple[str, ...] = ()
    for exponent in range(1, 21):
        beta = 2.0 ** (-exponent)
        attempted.append(beta)
        candidate = old.copy()
        candidate[1:-1] = old[1:-1] + beta * (target[1:-1] - old[1:-1])
        reasons: list[str] = []
        if np.any(np.diff(candidate) <= 0.0):
            reasons.append("nonmonotone")
        displacement = np.abs(candidate[1:-1] - old[1:-1])
        adjacent = np.minimum(old_mesh.widths[:-1], old_mesh.widths[1:]) if n > 1 else np.array([])
        if displacement.size and np.any(displacement > 0.5 * adjacent):
            reasons.append("displacement_limit")
        widths = np.diff(candidate)
        if np.any(widths < 1.0 / (20.0 * n)) or np.any(widths > 5.0 / n):
            reasons.append("width_bounds")
        ratios = widths / np.roll(widths, -1)
        if np.any(ratios < 1.0 / 3.0) or np.any(ratios > 3.0):
            reasons.append("adjacent_ratio_bounds")
        if not reasons:
            return RMovementResult(
                R_MOVEMENT_VERSION, True, False, beta, tuple(attempted), _readonly(old), _readonly(target), _readonly(candidate), ()
            )
        last_reasons = tuple(dict.fromkeys(reasons))
    return RMovementResult(
        R_MOVEMENT_VERSION, False, True, 0.0, tuple(attempted), _readonly(old), _readonly(target), _readonly(old), last_reasons or ("no_feasible_beta",),
    )


def decide_adaptation_cycle(
    *,
    interval_count: int,
    cycle_index: int,
    defect_maximum: float,
    period_relative_change: float | None,
    weighted_orbit_change: float | None,
    consecutive_pure_r_cycles: int,
    pure_r_defect_reduction: float | None,
    maximum_defect_element: int | None = None,
    soft_cap_escalated: bool = False,
) -> AdaptationCycleDecision:
    """Classify the next v1 adaptive action or terminal status."""
    n = _positive_integer(interval_count, "interval_count")
    defect_pass = defect_maximum < DEFECT_ACCEPTANCE_TOLERANCE
    convergence_pass = False
    if period_relative_change is not None and weighted_orbit_change is not None:
        convergence_pass = bool(
            period_relative_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE
            and weighted_orbit_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE
        )
    if defect_pass and convergence_pass:
        return AdaptationCycleDecision(ADAPTIVE_CONTROLLER_VERSION, "stop_converged", "converged", None, soft_cap_escalated, ())
    if cycle_index >= CYCLE_BUDGET or n >= HARD_INTERVAL_CAP:
        return AdaptationCycleDecision(
            ADAPTIVE_CONTROLLER_VERSION, "resolution_unresolved", "resolution_unresolved", None, soft_cap_escalated,
            ("cycle_budget_exhausted" if cycle_index >= CYCLE_BUDGET else "hard_cap_reached",),
        )
    if n >= SOFT_INTERVAL_CAP and not soft_cap_escalated:
        return AdaptationCycleDecision(
            ADAPTIVE_CONTROLLER_VERSION, "mesh_cap_escalation", "continue", None, True, ("soft_cap_failed_after_corrected_cycle",)
        )
    if not defect_pass:
        return AdaptationCycleDecision(ADAPTIVE_CONTROLLER_VERSION, "ordinary_h_r", "continue", None, soft_cap_escalated, ("defect_gate_failed",))
    if consecutive_pure_r_cycles >= 3 and (pure_r_defect_reduction is None or pure_r_defect_reduction < 0.25):
        if maximum_defect_element is None:
            raise ValueError("maximum_defect_element is required for forced split decisions.")
        return AdaptationCycleDecision(
            ADAPTIVE_CONTROLLER_VERSION, "forced_single_split_h_r", "continue", int(maximum_defect_element), soft_cap_escalated,
            ("pure_r_stagnation",),
        )
    return AdaptationCycleDecision(
        ADAPTIVE_CONTROLLER_VERSION, "pure_r", "continue", None, soft_cap_escalated, ("convergence_gate_failed",)
    )


def transfer_tangent_by_collocation_polynomial(
    assembler: GaussCollocationAssembler,
    unknowns: ArrayLike,
    tangent: ArrayLike,
    destination_mesh: FixedMesh,
    destination_rule: CollocationRule,
    *,
    epsilon: float = 1.0e-6,
) -> np.ndarray:
    """Transfer a packed tangent by differentiating collocation-polynomial transfer."""
    base = np.asarray(unknowns, dtype=float)
    direction = np.asarray(tangent, dtype=float)
    if base.shape != direction.shape:
        raise ValueError("unknowns and tangent must have identical shape.")
    if not np.all(np.isfinite(direction)):
        raise ValueError("tangent must be finite.")
    step = float(epsilon)
    if not np.isfinite(step) or step <= 0.0:
        raise ValueError("epsilon must be positive and finite.")
    plus = assembler.transfer_unknowns(base + step * direction, destination_mesh, destination_rule)
    minus = assembler.transfer_unknowns(base - step * direction, destination_mesh, destination_rule)
    result = (plus - minus) / (2.0 * step)
    result.setflags(write=False)
    return result


def transfer_orbit_phase_and_tangent(
    assembler: GaussCollocationAssembler,
    unknowns: ArrayLike,
    tangent: ArrayLike | None,
    destination_mesh: FixedMesh,
    destination_rule: CollocationRule,
) -> tuple[np.ndarray, FrozenPhaseReference, np.ndarray | None]:
    """Transfer solution, refreshed phase reference, and optional tangent to a new mesh."""
    transferred_unknowns = assembler.transfer_unknowns(unknowns, destination_mesh, destination_rule)
    reference = assembler.transferred_phase_reference(unknowns, destination_mesh, destination_rule)
    transferred_tangent = None if tangent is None else transfer_tangent_by_collocation_polynomial(
        assembler, unknowns, tangent, destination_mesh, destination_rule
    )
    transferred_unknowns.setflags(write=False)
    return transferred_unknowns, reference, transferred_tangent


def restart_plan(*, remesh_kind: Literal["h+r", "pure-r"], tangent_only_failure: bool = False) -> RestartPlan:
    """Return the exact v1 three-attempt retry order for a remesh restart."""
    if tangent_only_failure:
        return RestartPlan(
            RESTART_RETRY_VERSION,
            "tangent_only_failure",
            (
                RestartAttempt("deterministic_two_point_rebootstrap", True, False, True),
                RestartAttempt("restart_with_rebootstrapped_tangent", True, True, False),
                RestartAttempt("reject_after_rebootstrap_failure", True, False, False),
            ),
        )
    if remesh_kind not in {"h+r", "pure-r"}:
        raise ValueError("remesh_kind must be 'h+r' or 'pure-r'.")
    prefix = "pure_r" if remesh_kind == "pure-r" else "h_r"
    return RestartPlan(
        RESTART_RETRY_VERSION,
        remesh_kind,
        (
            RestartAttempt(f"{prefix}_transfer_correct", True, True, False),
            RestartAttempt(f"{prefix}_refresh_reference_recorrect", True, True, False),
            RestartAttempt(f"{prefix}_rebootstrap_tangent_recorrect", True, True, True),
        ),
    )


def physical_mapping_passes(assembler: GaussCollocationAssembler, unknowns: ArrayLike) -> bool:
    """Check that transformed endpoint/stage states and period map to positive finite values."""
    variables = assembler.layout.unpack(np.asarray(unknowns, dtype=float))
    with np.errstate(over="ignore", invalid="ignore"):
        positives = np.exp(
            np.concatenate(
                (variables.endpoints[:, :2].reshape(-1), variables.stages[:, :, :2].reshape(-1))
            )
        )
        period = np.exp(variables.log_period)
    return bool(np.all(np.isfinite(positives)) and np.all(positives > 0.0) and np.isfinite(period) and period > 0.0)


def deterministic_two_point_rebootstrap_tangent(
    previous_unknowns: ArrayLike,
    current_unknowns: ArrayLike,
) -> np.ndarray:
    """Return the deterministic two-point secant used for tangent-only restart failure."""
    previous = np.asarray(previous_unknowns, dtype=float)
    current = np.asarray(current_unknowns, dtype=float)
    if previous.shape != current.shape:
        raise ValueError("previous_unknowns and current_unknowns must have identical shape.")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(current)):
        raise ValueError("two-point tangent inputs must be finite.")
    tangent = current - previous
    norm = float(np.linalg.norm(tangent))
    if not np.isfinite(norm) or norm <= 0.0:
        raise ValueError("two-point tangent inputs must be distinct.")
    result = tangent / norm
    result.setflags(write=False)
    return result


def evaluate_restart_gates(
    assembler: GaussCollocationAssembler,
    correction: MidpointCorrectionResult | None,
    initial_unknowns: ArrayLike,
    tangent: ArrayLike | None,
    *,
    tolerances: MidpointResidualTolerances | None = None,
    max_packed_change_norm: float = np.inf,
    require_tangent: bool = True,
) -> RestartGateDiagnostics:
    """Evaluate v1 residual, phase, positivity, finite-change, and tangent gates."""
    active_tolerances = tolerances or MidpointResidualTolerances()
    reasons: list[str] = []
    if correction is None:
        residual_gate = False
        phase_gate = False
        positivity_gate = False
        finite_change_gate = False
        packed_change_norm = np.nan
        unknowns = np.asarray(initial_unknowns, dtype=float)
        reasons.append("correction_not_executed")
    else:
        unknowns = np.asarray(correction.unknowns, dtype=float)
        residual_gate = bool(correction.accepted)
        phase_gate = bool(np.isfinite(correction.diagnostics.phase_abs) and correction.diagnostics.phase_abs <= active_tolerances.phase_abs)
        positivity_gate = physical_mapping_passes(assembler, unknowns)
        initial = np.asarray(initial_unknowns, dtype=float)
        packed_change_norm = float(np.linalg.norm(unknowns - initial)) if initial.shape == unknowns.shape else np.nan
        finite_change_gate = bool(
            np.isfinite(packed_change_norm)
            and (np.isinf(max_packed_change_norm) or packed_change_norm <= max_packed_change_norm)
        )
        if not residual_gate:
            reasons.append("residual_gate_failed")
        if not phase_gate:
            reasons.append("phase_gate_failed")
        if not positivity_gate:
            reasons.append("positivity_gate_failed")
        if not finite_change_gate:
            reasons.append("finite_change_gate_failed")
    tangent_norm: float | None = None
    tangent_gate = True
    if require_tangent:
        if tangent is None:
            tangent_gate = False
            reasons.append("tangent_missing")
        else:
            tangent_array = np.asarray(tangent, dtype=float)
            tangent_norm = float(np.linalg.norm(tangent_array))
            tangent_gate = bool(
                tangent_array.shape == unknowns.shape
                and np.all(np.isfinite(tangent_array))
                and np.isfinite(tangent_norm)
                and tangent_norm > 0.0
            )
            if not tangent_gate:
                reasons.append("tangent_gate_failed")
    return RestartGateDiagnostics(
        residual_gate=residual_gate,
        phase_gate=phase_gate,
        positivity_gate=positivity_gate,
        finite_change_gate=finite_change_gate,
        tangent_gate=tangent_gate,
        packed_change_norm=packed_change_norm,
        tangent_norm=tangent_norm,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )


def execute_fixed_parameter_restart(
    assembler: GaussCollocationAssembler,
    initial_unknowns: ArrayLike,
    *,
    remesh_kind: Literal["h+r", "pure-r"],
    tangent: ArrayLike | None = None,
    previous_unknowns: ArrayLike | None = None,
    require_tangent: bool = True,
    tolerances: MidpointResidualTolerances | None = None,
    max_nfev: int = 1000,
    max_packed_change_norm: float = np.inf,
) -> RemeshRestartResult:
    """Execute fixed-parameter correction attempts in the v1 deterministic order.

    A tangent-only failure (all non-tangent gates pass but the tangent is missing
    or invalid) switches to the documented deterministic two-point rebootstrap
    plan.  The caller supplies ``previous_unknowns`` from the preceding accepted
    mesh when tangent rebootstrap is allowed.
    """
    active_plan = restart_plan(remesh_kind=remesh_kind)
    initial = np.asarray(initial_unknowns, dtype=float)
    active_tangent = None if tangent is None else np.asarray(tangent, dtype=float).copy()
    attempts: list[RemeshRestartAttemptResult] = []

    def run_attempt(attempt: RestartAttempt, attempt_tangent: np.ndarray | None) -> RemeshRestartAttemptResult:
        correction = None
        if attempt.apply_fixed_parameter_correction:
            correction = correct_gauss_orbit(
                assembler,
                initial,
                tolerances=tolerances,
                max_nfev=max_nfev,
            )
        gates = evaluate_restart_gates(
            assembler,
            correction,
            initial,
            attempt_tangent,
            tolerances=tolerances,
            max_packed_change_norm=max_packed_change_norm,
            require_tangent=require_tangent,
        )
        return RemeshRestartAttemptResult(attempt=attempt, correction=correction, gates=gates, tangent=attempt_tangent)

    for attempt in active_plan.attempts:
        if attempt.rebootstrap_tangent and previous_unknowns is not None:
            active_tangent = deterministic_two_point_rebootstrap_tangent(previous_unknowns, initial)
        result = run_attempt(attempt, active_tangent)
        attempts.append(result)
        correction = result.correction
        if result.gates.accepted and correction is not None:
            return RemeshRestartResult(
                RESTART_RETRY_VERSION,
                active_plan,
                True,
                tuple(attempts),
                correction.unknowns,
                result.tangent,
                (),
            )
        only_tangent_failed = result.gates.rejection_reasons in (("tangent_missing",), ("tangent_gate_failed",))
        if only_tangent_failed and previous_unknowns is not None:
            tangent_plan = restart_plan(remesh_kind=remesh_kind, tangent_only_failure=True)
            for tangent_attempt in tangent_plan.attempts:
                if tangent_attempt.rebootstrap_tangent:
                    active_tangent = deterministic_two_point_rebootstrap_tangent(previous_unknowns, initial)
                tangent_result = run_attempt(tangent_attempt, active_tangent)
                attempts.append(tangent_result)
                tangent_correction = tangent_result.correction
                if tangent_result.gates.accepted and tangent_correction is not None:
                    return RemeshRestartResult(
                        RESTART_RETRY_VERSION,
                        tangent_plan,
                        True,
                        tuple(attempts),
                        tangent_correction.unknowns,
                        tangent_result.tangent,
                        (),
                    )
            active_plan = tangent_plan
            break
    final_unknowns = initial if not attempts or attempts[-1].correction is None else attempts[-1].correction.unknowns
    final_reasons = attempts[-1].gates.rejection_reasons if attempts else ("no_restart_attempts",)
    return RemeshRestartResult(
        RESTART_RETRY_VERSION,
        active_plan,
        False,
        tuple(attempts),
        final_unknowns,
        active_tangent,
        final_reasons,
    )
