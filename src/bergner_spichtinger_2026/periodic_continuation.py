"""Transparent fixed-mesh pseudo-arclength periodic-orbit continuation.

The Python implementation in this module is an executable reference for the
Episode 008 migration to native LOCA.  It deliberately keeps the midpoint mesh
and phase reference fixed within each continuation segment.  The active
normalized coordinate is appended to the fixed-parameter orbit vector only in
the Python augmented corrector; it is not part of the square NOX/LOCA base
system used by the later C++ backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import exp
from pathlib import Path
from typing import Iterable

import csv
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.sparse import bmat, csr_matrix

from .constants import Environment
from .periodic_orbits import (
    ArrayLike,
    CollocationResidualBlocks,
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    MidpointCorrectionResult,
    MidpointResidualDiagnostics,
    MidpointResidualTolerances,
    OrbitLayout,
    correct_midpoint_orbit,
    midpoint_residual_diagnostics,
    transformed_vector_field,
    transformed_vector_field_environment_derivatives,
)


CONTINUATION_FORMULATION_VERSION = "fixed-mesh-midpoint-pseudo-arclength-v1"
CONTINUATION_METRIC_VERSION = "endpoint-stage-half-weighted-l2-v1"
PARAMETER_COLUMN_VERSION = "analytic-normalized-coordinate-chain-rule-v1"


def _readonly_vector(values: Iterable[float], *, name: str) -> np.ndarray:
    result = np.array(tuple(values), dtype=float)
    if result.ndim != 1 or result.size < 2:
        raise ValueError(f"{name} must be a one-dimensional vector with at least two entries.")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values.")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class HopfLocusCoordinates:
    """Shape-preserving lower/upper Hopf-locus interpolation in ``log(w)``."""

    temperatures_K: np.ndarray
    lower_log_w: np.ndarray
    upper_log_w: np.ndarray
    _lower_interpolator: PchipInterpolator = field(init=False, repr=False, compare=False)
    _upper_interpolator: PchipInterpolator = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        temperatures = _readonly_vector(self.temperatures_K, name="temperatures_K")
        lower = _readonly_vector(self.lower_log_w, name="lower_log_w")
        upper = _readonly_vector(self.upper_log_w, name="upper_log_w")
        if lower.shape != temperatures.shape or upper.shape != temperatures.shape:
            raise ValueError("Hopf-locus temperature and log(w) vectors must have identical shapes.")
        if np.any(np.diff(temperatures) <= 0.0):
            raise ValueError("Hopf-locus temperatures must be strictly increasing.")
        if np.any(lower >= upper):
            raise ValueError("lower Hopf log(w) must be below upper Hopf log(w).")
        object.__setattr__(self, "temperatures_K", temperatures)
        object.__setattr__(self, "lower_log_w", lower)
        object.__setattr__(self, "upper_log_w", upper)
        object.__setattr__(self, "_lower_interpolator", PchipInterpolator(temperatures, lower))
        object.__setattr__(self, "_upper_interpolator", PchipInterpolator(temperatures, upper))

    @classmethod
    def from_episode6_csv(cls, path: str | Path) -> HopfLocusCoordinates:
        """Load converged native-LOCA lower/upper rows from the Episode 006 CSV."""
        rows: dict[str, dict[float, float]] = {"lower_hopf": {}, "upper_hopf": {}}
        with Path(path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                branch = row["branch_id"]
                if branch in rows and row["converged"] == "True":
                    rows[branch][float(row["T_K"])] = float(row["log_w"])
        common = sorted(set(rows["lower_hopf"]) & set(rows["upper_hopf"]))
        if len(common) < 2:
            raise ValueError("Hopf-locus CSV does not contain a common converged temperature grid.")
        return cls(
            temperatures_K=np.asarray(common),
            lower_log_w=np.asarray([rows["lower_hopf"][value] for value in common]),
            upper_log_w=np.asarray([rows["upper_hopf"][value] for value in common]),
        )

    def _temperature(self, temperature_K: float) -> float:
        value = float(temperature_K)
        if not np.isfinite(value):
            raise ValueError("temperature must be finite.")
        if value < self.temperatures_K[0] or value > self.temperatures_K[-1]:
            raise ValueError("temperature lies outside the validated Hopf-locus domain.")
        return value

    def bounds(self, temperature_K: float) -> tuple[float, float]:
        temperature = self._temperature(temperature_K)
        return float(self._lower_interpolator(temperature)), float(self._upper_interpolator(temperature))

    def spine_log_w(self, temperature_K: float) -> float:
        lower, upper = self.bounds(temperature_K)
        return 0.5 * (lower + upper)

    def spine_log_w_derivative(self, temperature_K: float) -> float:
        temperature = self._temperature(temperature_K)
        return 0.5 * float(
            self._lower_interpolator.derivative()(temperature)
            + self._upper_interpolator.derivative()(temperature)
        )

    def rho(self, temperature_K: float, log_w: float) -> float:
        lower, upper = self.bounds(temperature_K)
        return (float(log_w) - 0.5 * (lower + upper)) / (0.5 * (upper - lower))

    def log_w_from_rho(self, temperature_K: float, rho: float) -> float:
        lower, upper = self.bounds(temperature_K)
        return 0.5 * (lower + upper) + float(rho) * 0.5 * (upper - lower)

    @staticmethod
    def temperature_hat(temperature_K: float) -> float:
        return (float(temperature_K) - 215.0) / 25.0

    @staticmethod
    def temperature_from_hat(temperature_hat: float) -> float:
        return 215.0 + 25.0 * float(temperature_hat)


@dataclass(frozen=True)
class PhysicalContinuationCoordinates:
    active_coordinate: float
    temperature_hat: float
    rho: float
    temperature_K: float
    log_w: float
    w_m_s: float


@dataclass(frozen=True)
class FixedTemperatureRhoPath:
    """Map normalized slice coordinate ``rho`` to physical environment values."""

    locus: HopfLocusCoordinates
    base_environment: Environment
    temperature_K: float
    coordinate_name: str = field(default="rho", init=False)

    def coordinates(self, coordinate: float) -> PhysicalContinuationCoordinates:
        rho = float(coordinate)
        temperature = self.locus._temperature(self.temperature_K)
        log_w = self.locus.log_w_from_rho(temperature, rho)
        return PhysicalContinuationCoordinates(
            active_coordinate=rho,
            temperature_hat=self.locus.temperature_hat(temperature),
            rho=rho,
            temperature_K=temperature,
            log_w=log_w,
            w_m_s=exp(log_w),
        )

    def environment(self, coordinate: float) -> Environment:
        values = self.coordinates(coordinate)
        return replace(self.base_environment, T=values.temperature_K, w=values.w_m_s)

    def physical_derivative_factors(self, coordinate: float) -> tuple[float, float]:
        del coordinate
        lower, upper = self.locus.bounds(self.temperature_K)
        return 0.0, 0.5 * (upper - lower)


@dataclass(frozen=True)
class SpineTemperaturePath:
    """Map normalized spine coordinate ``T_hat`` to ``(T, log(w_spine(T)))``."""

    locus: HopfLocusCoordinates
    base_environment: Environment
    coordinate_name: str = field(default="temperature_hat", init=False)

    def coordinates(self, coordinate: float) -> PhysicalContinuationCoordinates:
        temperature_hat = float(coordinate)
        temperature = self.locus.temperature_from_hat(temperature_hat)
        log_w = self.locus.spine_log_w(temperature)
        return PhysicalContinuationCoordinates(
            active_coordinate=temperature_hat,
            temperature_hat=temperature_hat,
            rho=0.0,
            temperature_K=temperature,
            log_w=log_w,
            w_m_s=exp(log_w),
        )

    def environment(self, coordinate: float) -> Environment:
        values = self.coordinates(coordinate)
        return replace(self.base_environment, T=values.temperature_K, w=values.w_m_s)

    def physical_derivative_factors(self, coordinate: float) -> tuple[float, float]:
        temperature = self.locus.temperature_from_hat(coordinate)
        return 25.0, 25.0 * self.locus.spine_log_w_derivative(temperature)


ContinuationPath = FixedTemperatureRhoPath | SpineTemperaturePath


@dataclass(frozen=True)
class FixedMeshOrbitFamily:
    """One square midpoint system family with an immutable phase reference."""

    mesh: FixedMesh
    phase_reference: FrozenPhaseReference
    path: ContinuationPath
    phase_reference_id: str

    def assembler(self, coordinate: float) -> MidpointCollocationAssembler:
        return MidpointCollocationAssembler(
            self.mesh,
            self.path.environment(coordinate),
            self.phase_reference,
        )

    def parameter_column(self, unknowns: ArrayLike, coordinate: float) -> np.ndarray:
        """Assemble the analytic derivative with respect to the normalized path coordinate."""
        assembler = self.assembler(coordinate)
        variables = assembler._variables(unknowns)
        period = exp(variables.log_period)
        temperature_factor, log_w_factor = self.path.physical_derivative_factors(coordinate)
        stages = np.empty_like(variables.stages)
        updates = np.empty_like(variables.endpoints)
        stage_coefficient = assembler.rule.stage_coefficients[0][0]
        update_weight = assembler.rule.quadrature_weights[0]
        for interval, width in enumerate(self.mesh.widths):
            g_temperature, g_log_w = transformed_vector_field_environment_derivatives(
                variables.stages[interval, 0], assembler.env, assembler.coeff
            )
            model_derivative = temperature_factor * g_temperature + log_w_factor * g_log_w
            stages[interval, 0] = assembler.state_scaling * (
                -width * period * stage_coefficient * model_derivative
            )
            updates[interval] = assembler.state_scaling * (
                -width * period * update_weight * model_derivative
            )
        return assembler.layout.pack_residual(
            CollocationResidualBlocks(stages=stages, updates=updates, phase=0.0)
        )


@dataclass(frozen=True)
class FixedMeshContinuationMetric:
    """Diagonal weighted metric for packed orbit plus active coordinate.

    Endpoint and explicit-stage orbit representations each receive half of the
    total orbit weight.  ``log(P)`` and the normalized active coordinate use
    fixed unit weights by default.  The resulting diagonal is independent of
    mesh count and is used without substitution in every continuation
    operation.
    """

    layout: OrbitLayout
    mesh: FixedMesh
    state_scaling: np.ndarray
    log_period_weight: float = 1.0
    coordinate_weight: float = 1.0
    weights: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        scaling = np.asarray(self.state_scaling, dtype=float)
        if scaling.shape != (self.layout.state_dimension,) or np.any(scaling <= 0.0):
            raise ValueError("state_scaling must contain one positive value per state component.")
        if self.layout.interval_count != self.mesh.interval_count or self.layout.stage_count != 1:
            raise ValueError("continuation metric currently requires the matching midpoint layout.")
        if not np.isfinite(self.log_period_weight) or self.log_period_weight <= 0.0:
            raise ValueError("log_period_weight must be positive and finite.")
        if not np.isfinite(self.coordinate_weight) or self.coordinate_weight <= 0.0:
            raise ValueError("coordinate_weight must be positive and finite.")
        diagonal = np.empty(self.layout.unknown_size + 1, dtype=float)
        for interval in range(self.layout.interval_count):
            endpoint_coefficient = 0.25 * (
                self.mesh.widths[interval] + self.mesh.widths[(interval - 1) % self.layout.interval_count]
            )
            diagonal[self.layout.endpoint_slice(interval)] = endpoint_coefficient * scaling**2
            diagonal[self.layout.stage_slice(interval)] = 0.5 * self.mesh.widths[interval] * scaling**2
        diagonal[self.layout.log_period_index] = self.log_period_weight**2
        diagonal[-1] = self.coordinate_weight**2
        diagonal.setflags(write=False)
        scaling = np.array(scaling, copy=True)
        scaling.setflags(write=False)
        object.__setattr__(self, "state_scaling", scaling)
        object.__setattr__(self, "weights", diagonal)

    @classmethod
    def from_family(
        cls,
        family: FixedMeshOrbitFamily,
        *,
        log_period_weight: float = 1.0,
        coordinate_weight: float = 1.0,
    ) -> FixedMeshContinuationMetric:
        assembler = family.assembler(0.0)
        return cls(
            assembler.layout,
            family.mesh,
            family.phase_reference.state_scaling,
            log_period_weight,
            coordinate_weight,
        )

    def _vector(self, value: ArrayLike) -> np.ndarray:
        vector = np.asarray(value, dtype=float)
        if vector.shape != self.weights.shape:
            raise ValueError(f"augmented vector must have shape {self.weights.shape}, got {vector.shape}.")
        if not np.all(np.isfinite(vector)):
            raise ValueError("augmented vector must contain only finite values.")
        return vector

    def inner(self, first: ArrayLike, second: ArrayLike) -> float:
        left = self._vector(first)
        right = self._vector(second)
        return float(np.dot(self.weights * left, right))

    def norm(self, value: ArrayLike) -> float:
        vector = self._vector(value)
        return float(np.sqrt(max(0.0, self.inner(vector, vector))))

    def normalize(self, value: ArrayLike) -> np.ndarray:
        vector = self._vector(value)
        length = self.norm(vector)
        if not np.isfinite(length) or length <= 0.0:
            raise ValueError("cannot normalize a zero or nonfinite continuation vector.")
        return vector / length

    def arclength_gradient(self, tangent: ArrayLike) -> np.ndarray:
        return self.weights * self._vector(tangent)


@dataclass(frozen=True)
class ContinuationPoint:
    point_id: str
    branch_id: str
    point_kind: str
    unknowns: np.ndarray
    coordinate: float
    phase_reference_id: str
    parent_point_id: str | None
    branch_orientation: int
    accepted_step_size: float

    def __post_init__(self) -> None:
        unknowns = np.array(self.unknowns, dtype=float, copy=True)
        if unknowns.ndim != 1 or not np.all(np.isfinite(unknowns)):
            raise ValueError("continuation point unknowns must be a finite vector.")
        if not np.isfinite(self.coordinate):
            raise ValueError("continuation point coordinate must be finite.")
        if self.branch_orientation not in (-1, 1):
            raise ValueError("branch orientation must be -1 or +1.")
        if not np.isfinite(self.accepted_step_size) or self.accepted_step_size < 0.0:
            raise ValueError("accepted step size must be finite and nonnegative.")
        unknowns.setflags(write=False)
        object.__setattr__(self, "unknowns", unknowns)

    @property
    def augmented(self) -> np.ndarray:
        return np.concatenate((self.unknowns, [self.coordinate]))


@dataclass(frozen=True)
class PseudoArclengthTolerances:
    midpoint: MidpointResidualTolerances = field(default_factory=MidpointResidualTolerances)
    arclength_abs: float = 1.0e-10

    def __post_init__(self) -> None:
        if not np.isfinite(self.arclength_abs) or self.arclength_abs <= 0.0:
            raise ValueError("arclength tolerance must be positive and finite.")


@dataclass(frozen=True)
class PseudoArclengthCorrectionResult:
    augmented: np.ndarray
    residual: np.ndarray
    diagnostics: MidpointResidualDiagnostics
    arclength_abs: float
    accepted: bool
    rejection_reasons: tuple[str, ...]
    scipy_success: bool
    scipy_status: int
    scipy_message: str
    scipy_cost: float
    scipy_optimality: float
    function_evaluations: int
    jacobian_evaluations: int | None
    weighted_step_norm: float


def _validate_family_metric(
    family: FixedMeshOrbitFamily,
    metric: FixedMeshContinuationMetric,
) -> None:
    assembler = family.assembler(0.0)
    if metric.layout != assembler.layout or not np.array_equal(metric.mesh.boundaries, family.mesh.boundaries):
        raise ValueError("continuation metric layout/mesh does not match the orbit family.")
    if not np.array_equal(metric.state_scaling, family.phase_reference.state_scaling):
        raise ValueError("continuation metric state scaling does not match the orbit family.")


def _validate_point_family(point: ContinuationPoint, family: FixedMeshOrbitFamily) -> None:
    if point.phase_reference_id != family.phase_reference_id:
        raise ValueError("continuation point phase reference does not match the orbit family.")
    family.assembler(point.coordinate)._variables(point.unknowns)


class PseudoArclengthProblem:
    """Augment a fixed-reference midpoint family with one weighted arc row."""

    def __init__(
        self,
        family: FixedMeshOrbitFamily,
        metric: FixedMeshContinuationMetric,
        predictor: ArrayLike,
        tangent: ArrayLike,
    ) -> None:
        _validate_family_metric(family, metric)
        self.family = family
        self.metric = metric
        self.predictor = np.array(metric._vector(predictor), copy=True)
        self.tangent = metric.normalize(tangent)

    def residual(self, augmented: ArrayLike) -> np.ndarray:
        vector = self.metric._vector(augmented)
        assembler = self.family.assembler(float(vector[-1]))
        base = assembler.residual(vector[:-1])
        arclength = self.metric.inner(vector - self.predictor, self.tangent)
        return np.concatenate((base, [arclength]))

    def jacobian(self, augmented: ArrayLike) -> csr_matrix:
        vector = self.metric._vector(augmented)
        unknowns = vector[:-1]
        coordinate = float(vector[-1])
        state = self.family.assembler(coordinate).jacobian(unknowns)
        parameter = csr_matrix(self.family.parameter_column(unknowns, coordinate)[:, None])
        arc = csr_matrix(self.metric.arclength_gradient(self.tangent)[None, :])
        result = bmat([[state, parameter], [arc[:, :-1], arc[:, -1:]]], format="csr")
        result.sum_duplicates()
        result.sort_indices()
        return result


def _physical_vector_is_finite(assembler: MidpointCollocationAssembler, unknowns: np.ndarray) -> bool:
    try:
        variables = assembler.layout.unpack(unknowns)
        with np.errstate(over="ignore", invalid="ignore"):
            positive_states = np.exp(
                np.concatenate((variables.endpoints[:, :2].ravel(), variables.stages[:, :, :2].ravel()))
            )
            period = np.exp(variables.log_period)
        return bool(np.all(np.isfinite(positive_states)) and np.all(positive_states > 0.0) and np.isfinite(period) and period > 0.0)
    except (ValueError, OverflowError, FloatingPointError):
        return False


def correct_pseudo_arclength(
    problem: PseudoArclengthProblem,
    initial_augmented: ArrayLike,
    *,
    tolerances: PseudoArclengthTolerances | None = None,
    max_nfev: int = 400,
) -> PseudoArclengthCorrectionResult:
    """Correct one predictor and independently gate every augmented block."""
    active_tolerances = tolerances or PseudoArclengthTolerances()
    initial = np.array(problem.metric._vector(initial_augmented), copy=True)
    solution = least_squares(
        problem.residual,
        initial,
        jac=problem.jacobian,
        method="trf",
        x_scale="jac",
        xtol=1.0e-13,
        ftol=1.0e-13,
        gtol=1.0e-13,
        max_nfev=max_nfev,
    )
    candidate = np.asarray(solution.x, dtype=float)
    reasons: list[str] = []
    if not bool(solution.success):
        reasons.append("scipy_unsuccessful")
    candidate_valid = candidate.shape == initial.shape and np.all(np.isfinite(candidate))
    if not candidate_valid:
        reasons.append("nonfinite_or_malformed_augmented_vector")
        residual = np.full(initial.shape, np.inf)
        diagnostics = MidpointResidualDiagnostics(*(float("inf"),) * 5)
        arclength_abs = float("inf")
        coordinate = float(initial[-1])
        unknowns = initial[:-1]
    else:
        coordinate = float(candidate[-1])
        unknowns = candidate[:-1]
        try:
            assembler = problem.family.assembler(coordinate)
            blocks = assembler.residual_blocks(unknowns)
            diagnostics = midpoint_residual_diagnostics(blocks)
            residual = np.concatenate((assembler.layout.pack_residual(blocks), [problem.metric.inner(candidate - problem.predictor, problem.tangent)]))
            arclength_abs = abs(float(residual[-1]))
        except (ValueError, OverflowError, FloatingPointError):
            residual = np.full(initial.shape, np.inf)
            diagnostics = MidpointResidualDiagnostics(*(float("inf"),) * 5)
            arclength_abs = float("inf")
    thresholds = active_tolerances.midpoint
    checks = (
        (diagnostics.stage_max <= thresholds.stage_max, "stage_max_tolerance"),
        (diagnostics.stage_rms <= thresholds.stage_rms, "stage_rms_tolerance"),
        (diagnostics.update_max <= thresholds.update_max, "update_max_tolerance"),
        (diagnostics.update_rms <= thresholds.update_rms, "update_rms_tolerance"),
        (diagnostics.phase_abs <= thresholds.phase_abs, "phase_tolerance"),
        (arclength_abs <= active_tolerances.arclength_abs, "arclength_tolerance"),
    )
    reasons.extend(reason for passed, reason in checks if not passed)
    try:
        assembler = problem.family.assembler(coordinate)
        if not _physical_vector_is_finite(assembler, unknowns):
            reasons.append("nonfinite_or_nonpositive_physical_values")
    except (ValueError, OverflowError, FloatingPointError):
        reasons.append("invalid_active_coordinate")
    reasons = list(dict.fromkeys(reasons))
    weighted_step = problem.metric.norm(candidate - initial) if candidate_valid else float("inf")
    return PseudoArclengthCorrectionResult(
        augmented=np.array(candidate, copy=True),
        residual=np.array(residual, copy=True),
        diagnostics=diagnostics,
        arclength_abs=arclength_abs,
        accepted=not reasons,
        rejection_reasons=tuple(reasons),
        scipy_success=bool(solution.success),
        scipy_status=int(solution.status),
        scipy_message=str(solution.message),
        scipy_cost=float(solution.cost),
        scipy_optimality=float(solution.optimality),
        function_evaluations=int(solution.nfev),
        jacobian_evaluations=None if solution.njev is None else int(solution.njev),
        weighted_step_norm=weighted_step,
    )


@dataclass(frozen=True)
class BranchBootstrapResult:
    neighbor: ContinuationPoint
    tangent: np.ndarray
    events: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ContinuationSegmentResult:
    points: tuple[ContinuationPoint, ...]
    events: tuple[dict[str, object], ...]
    reached_target: bool


def _correction_event_fields(result: MidpointCorrectionResult) -> dict[str, object]:
    return {
        "accepted": result.accepted,
        "rejection_reasons": list(result.rejection_reasons),
        "stage_residual_max": result.diagnostics.stage_max,
        "stage_residual_rms": result.diagnostics.stage_rms,
        "update_residual_max": result.diagnostics.update_max,
        "update_residual_rms": result.diagnostics.update_rms,
        "phase_residual_abs": result.diagnostics.phase_abs,
        "arclength_residual_abs": None,
        "scipy_success": result.scipy_success,
        "scipy_status": result.scipy_status,
        "scipy_message": result.scipy_message,
        "scipy_cost": result.scipy_cost,
        "scipy_optimality": result.scipy_optimality,
        "function_evaluations": result.function_evaluations,
        "jacobian_evaluations": result.jacobian_evaluations,
    }


def _pseudo_event_fields(result: PseudoArclengthCorrectionResult) -> dict[str, object]:
    return {
        "accepted": result.accepted,
        "rejection_reasons": list(result.rejection_reasons),
        "stage_residual_max": result.diagnostics.stage_max,
        "stage_residual_rms": result.diagnostics.stage_rms,
        "update_residual_max": result.diagnostics.update_max,
        "update_residual_rms": result.diagnostics.update_rms,
        "phase_residual_abs": result.diagnostics.phase_abs,
        "arclength_residual_abs": result.arclength_abs,
        "scipy_success": result.scipy_success,
        "scipy_status": result.scipy_status,
        "scipy_message": result.scipy_message,
        "scipy_cost": result.scipy_cost,
        "scipy_optimality": result.scipy_optimality,
        "function_evaluations": result.function_evaluations,
        "jacobian_evaluations": result.jacobian_evaluations,
    }


def bootstrap_branch(
    family: FixedMeshOrbitFamily,
    metric: FixedMeshContinuationMetric,
    origin: ContinuationPoint,
    *,
    branch_id: str,
    direction: int,
    initial_coordinate_step: float,
    maximum_weighted_step: float = 0.25,
    minimum_coordinate_step: float = 1.0e-5,
    max_halvings: int = 12,
) -> BranchBootstrapResult:
    """Create the deterministic fixed-parameter second point for one direction."""
    _validate_family_metric(family, metric)
    _validate_point_family(origin, family)
    if direction not in (-1, 1):
        raise ValueError("bootstrap direction must be -1 or +1.")
    if initial_coordinate_step <= 0.0 or not np.isfinite(initial_coordinate_step):
        raise ValueError("initial bootstrap step must be positive and finite.")
    events: list[dict[str, object]] = []
    step = float(initial_coordinate_step)
    for attempt in range(max_halvings + 1):
        coordinate = origin.coordinate + direction * step
        assembler = family.assembler(coordinate)
        result = correct_midpoint_orbit(assembler, origin.unknowns)
        delta = np.concatenate((result.unknowns - origin.unknowns, [coordinate - origin.coordinate]))
        weighted_step = metric.norm(delta) if np.all(np.isfinite(delta)) else float("inf")
        excessive = weighted_step > maximum_weighted_step
        accepted = result.accepted and not excessive
        event = {
            "event_type": "branch_bootstrap_attempt",
            "branch_id": branch_id,
            "phase_reference_id": family.phase_reference_id,
            "parent_point_id": origin.point_id,
            "branch_orientation": direction,
            "attempt": attempt,
            "requested_coordinate_step": direction * step,
            "trial_coordinate": coordinate,
            "weighted_step_norm": weighted_step,
            "maximum_weighted_step": maximum_weighted_step,
            "excessive_weighted_step": excessive,
            **_correction_event_fields(result),
        }
        event["accepted"] = accepted
        if excessive:
            event["rejection_reasons"] = list(event["rejection_reasons"]) + ["excessive_weighted_bootstrap_step"]
        events.append(event)
        if accepted:
            neighbor = ContinuationPoint(
                point_id=f"{branch_id}-bootstrap",
                branch_id=branch_id,
                point_kind="branch_bootstrap",
                unknowns=result.unknowns,
                coordinate=coordinate,
                phase_reference_id=family.phase_reference_id,
                parent_point_id=origin.point_id,
                branch_orientation=direction,
                accepted_step_size=weighted_step,
            )
            tangent = metric.normalize(neighbor.augmented - origin.augmented)
            events.append(
                {
                    "event_type": "branch_bootstrap_accepted",
                    "branch_id": branch_id,
                    "phase_reference_id": family.phase_reference_id,
                    "point_id": neighbor.point_id,
                    "parent_point_id": origin.point_id,
                    "branch_orientation": direction,
                    "coordinate": coordinate,
                    "weighted_step_norm": weighted_step,
                    "tangent_coordinate_component": float(tangent[-1]),
                    "attempts": attempt + 1,
                }
            )
            return BranchBootstrapResult(neighbor, tangent, tuple(events))
        step *= 0.5
        if step < minimum_coordinate_step:
            break
    raise RuntimeError(f"deterministic branch bootstrap failed for {branch_id}")


def continue_to_coordinate(
    family: FixedMeshOrbitFamily,
    metric: FixedMeshContinuationMetric,
    origin: ContinuationPoint,
    *,
    branch_id: str,
    target_coordinate: float,
    bootstrap_coordinate_step: float = 0.02,
    initial_arclength_step: float = 0.04,
    minimum_arclength_step: float = 1.0e-4,
    maximum_arclength_step: float = 0.08,
    maximum_bootstrap_weighted_step: float = 0.25,
    maximum_steps: int = 80,
) -> ContinuationSegmentResult:
    """Continue from ``origin`` and land exactly on the requested coordinate."""
    _validate_family_metric(family, metric)
    _validate_point_family(origin, family)
    target = float(target_coordinate)
    if not np.isfinite(target) or target == origin.coordinate:
        raise ValueError("target coordinate must be finite and differ from the origin.")
    direction = 1 if target > origin.coordinate else -1
    bootstrap_step = min(abs(target - origin.coordinate), bootstrap_coordinate_step)
    bootstrap = bootstrap_branch(
        family,
        metric,
        origin,
        branch_id=branch_id,
        direction=direction,
        initial_coordinate_step=bootstrap_step,
        maximum_weighted_step=maximum_bootstrap_weighted_step,
    )
    points = [origin, bootstrap.neighbor]
    events = list(bootstrap.events)
    if bootstrap.neighbor.coordinate == target:
        return ContinuationSegmentResult(tuple(points), tuple(events), True)
    current = bootstrap.neighbor
    tangent = bootstrap.tangent
    step = min(maximum_arclength_step, max(initial_arclength_step, current.accepted_step_size))
    accepted_index = 0
    rejected_attempt = 0
    while accepted_index < maximum_steps:
        remaining = target - current.coordinate
        if remaining == 0.0:
            return ContinuationSegmentResult(tuple(points), tuple(events), True)
        if direction * remaining < 0.0:
            raise RuntimeError(f"continuation crossed target without exact landing on {branch_id}")
        if abs(tangent[-1]) < 1.0e-12:
            raise RuntimeError(f"continuation tangent lost active-coordinate orientation on {branch_id}")
        distance_to_target = abs(remaining / tangent[-1])
        if distance_to_target <= 1.25 * step:
            predictor = current.augmented + tangent * (remaining / tangent[-1])
            assembler = family.assembler(target)
            result = correct_midpoint_orbit(assembler, predictor[:-1])
            delta = np.concatenate((result.unknowns - current.unknowns, [target - current.coordinate]))
            weighted_step = metric.norm(delta) if np.all(np.isfinite(delta)) else float("inf")
            event = {
                "event_type": "exact_target_landing",
                "branch_id": branch_id,
                "phase_reference_id": family.phase_reference_id,
                "parent_point_id": current.point_id,
                "branch_orientation": direction,
                "target_coordinate": target,
                "predictor_weighted_step": metric.norm(predictor - current.augmented),
                "weighted_step_norm": weighted_step,
                **_correction_event_fields(result),
            }
            events.append(event)
            if result.accepted:
                point = ContinuationPoint(
                    point_id=f"{branch_id}-target",
                    branch_id=branch_id,
                    point_kind="exact_target",
                    unknowns=result.unknowns,
                    coordinate=target,
                    phase_reference_id=family.phase_reference_id,
                    parent_point_id=current.point_id,
                    branch_orientation=direction,
                    accepted_step_size=weighted_step,
                )
                points.append(point)
                return ContinuationSegmentResult(tuple(points), tuple(events), True)
            step *= 0.5
            rejected_attempt += 1
            if step < minimum_arclength_step:
                break
            continue
        predictor = current.augmented + step * tangent
        problem = PseudoArclengthProblem(family, metric, predictor, tangent)
        result = correct_pseudo_arclength(problem, predictor)
        candidate_coordinate = float(result.augmented[-1]) if np.all(np.isfinite(result.augmented)) else float("nan")
        directional_progress = bool(
            np.isfinite(candidate_coordinate)
            and direction * (candidate_coordinate - current.coordinate) > 0.0
        )
        event = {
            "event_type": "pseudo_arclength_step",
            "branch_id": branch_id,
            "phase_reference_id": family.phase_reference_id,
            "parent_point_id": current.point_id,
            "branch_orientation": direction,
            "accepted_step_index": accepted_index,
            "rejected_attempt": rejected_attempt,
            "requested_arclength_step": step,
            "predictor_coordinate": float(predictor[-1]),
            "corrected_coordinate": candidate_coordinate,
            "predictor_weighted_norm": metric.norm(predictor - current.augmented),
            "weighted_step_norm": (
                metric.norm(result.augmented - current.augmented)
                if np.all(np.isfinite(result.augmented))
                else float("inf")
            ),
            "directional_progress": directional_progress,
            **_pseudo_event_fields(result),
        }
        crosses_target = bool(
            directional_progress and direction * (candidate_coordinate - target) >= 0.0
        )
        event["crosses_target"] = crosses_target
        if result.accepted and (not directional_progress or crosses_target):
            event["accepted"] = False
            reason = "crosses_exact_target" if crosses_target else "wrong_branch_orientation"
            event["rejection_reasons"] = list(event["rejection_reasons"]) + [reason]
        events.append(event)
        if result.accepted and directional_progress and not crosses_target:
            accepted_index += 1
            point = ContinuationPoint(
                point_id=f"{branch_id}-step-{accepted_index:03d}",
                branch_id=branch_id,
                point_kind="pseudo_arclength",
                unknowns=result.augmented[:-1],
                coordinate=candidate_coordinate,
                phase_reference_id=family.phase_reference_id,
                parent_point_id=current.point_id,
                branch_orientation=direction,
                accepted_step_size=metric.norm(result.augmented - current.augmented),
            )
            secant = metric.normalize(point.augmented - current.augmented)
            if metric.inner(secant, tangent) < 0.0:
                secant = -secant
            tangent = secant
            current = point
            points.append(point)
            rejected_attempt = 0
            step = min(maximum_arclength_step, step * 1.25)
        else:
            rejected_attempt += 1
            step *= 0.5
            if step < minimum_arclength_step:
                break
    return ContinuationSegmentResult(tuple(points), tuple(events), False)


def refreshed_phase_reference(
    family: FixedMeshOrbitFamily,
    point: ContinuationPoint,
) -> FrozenPhaseReference:
    """Freeze one accepted discrete orbit as the next segment's phase reference."""
    _validate_point_family(point, family)
    assembler = family.assembler(point.coordinate)
    variables = assembler.layout.unpack(point.unknowns)
    period = exp(variables.log_period)
    derivatives = np.empty_like(variables.stages)
    for interval in range(assembler.layout.interval_count):
        derivatives[interval, 0] = period * transformed_vector_field(
            variables.stages[interval, 0], assembler.env, assembler.coeff
        )
    return FrozenPhaseReference(
        mesh=family.mesh,
        stage_values=variables.stages,
        stage_derivatives=derivatives,
        state_scaling=family.phase_reference.state_scaling,
        collocation_nodes=family.phase_reference.collocation_nodes,
        quadrature_weights=family.phase_reference.quadrature_weights,
    )


def controlled_phase_reference_restart(
    family: FixedMeshOrbitFamily,
    point: ContinuationPoint,
    *,
    new_phase_reference_id: str,
    new_path: ContinuationPath | None = None,
) -> tuple[FixedMeshOrbitFamily, ContinuationPoint, dict[str, object]]:
    """Create, re-coordinate, and verify an explicit phase-reference refresh boundary."""
    _validate_point_family(point, family)
    reference = refreshed_phase_reference(family, point)
    restarted = FixedMeshOrbitFamily(
        mesh=family.mesh,
        phase_reference=reference,
        path=family.path if new_path is None else new_path,
        phase_reference_id=new_phase_reference_id,
    )
    new_coordinate = point.coordinate
    physical = family.path.coordinates(point.coordinate)
    if new_path is not None:
        if isinstance(new_path, FixedTemperatureRhoPath):
            if not np.isclose(new_path.temperature_K, physical.temperature_K, rtol=0.0, atol=1.0e-12):
                raise ValueError("phase-reference restart must preserve physical temperature.")
            new_coordinate = new_path.locus.rho(new_path.temperature_K, physical.log_w)
        else:
            new_coordinate = new_path.locus.temperature_hat(physical.temperature_K)
        mapped = new_path.coordinates(new_coordinate)
        if not np.isclose(mapped.log_w, physical.log_w, rtol=0.0, atol=1.0e-12):
            raise ValueError("phase-reference restart must preserve physical log(w).")
    assembler = restarted.assembler(new_coordinate)
    blocks = assembler.residual_blocks(point.unknowns)
    diagnostics = midpoint_residual_diagnostics(blocks)
    phase_abs = diagnostics.phase_abs
    tolerances = MidpointResidualTolerances()
    if not (
        diagnostics.stage_max <= tolerances.stage_max
        and diagnostics.stage_rms <= tolerances.stage_rms
        and diagnostics.update_max <= tolerances.update_max
        and diagnostics.update_rms <= tolerances.update_rms
        and phase_abs <= min(tolerances.phase_abs, 1.0e-14)
    ):
        raise RuntimeError("refreshed orbit fails the fixed-parameter residual gates.")
    restarted_point = ContinuationPoint(
        point_id=f"{point.point_id}-restart-{new_phase_reference_id}",
        branch_id=point.branch_id,
        point_kind="controlled_restart",
        unknowns=point.unknowns,
        coordinate=new_coordinate,
        phase_reference_id=new_phase_reference_id,
        parent_point_id=point.point_id,
        branch_orientation=point.branch_orientation,
        accepted_step_size=0.0,
    )
    event = {
        "event_type": "phase_reference_refresh",
        "point_id": point.point_id,
        "restarted_point_id": restarted_point.point_id,
        "old_phase_reference_id": family.phase_reference_id,
        "new_phase_reference_id": new_phase_reference_id,
        "old_coordinate_name": family.path.coordinate_name,
        "new_coordinate_name": restarted.path.coordinate_name,
        "new_coordinate": new_coordinate,
        "phase_energy": reference.phase_energy,
        "stage_residual_max_after_refresh": diagnostics.stage_max,
        "stage_residual_rms_after_refresh": diagnostics.stage_rms,
        "update_residual_max_after_refresh": diagnostics.update_max,
        "update_residual_rms_after_refresh": diagnostics.update_rms,
        "phase_residual_abs_after_refresh": phase_abs,
        "controlled_restart": True,
    }
    return restarted, restarted_point, event


def point_diagnostics(
    point: ContinuationPoint,
    family: FixedMeshOrbitFamily,
    metric: FixedMeshContinuationMetric,
) -> dict[str, object]:
    """Return the required physical, residual, period, phase, and orientation fields."""
    _validate_family_metric(family, metric)
    _validate_point_family(point, family)
    assembler = family.assembler(point.coordinate)
    variables = assembler.layout.unpack(point.unknowns)
    diagnostics = midpoint_residual_diagnostics(assembler.residual_blocks(point.unknowns))
    physical = family.path.coordinates(point.coordinate)
    scaling = assembler.state_scaling
    stage_delta = (variables.stages - assembler.phase_reference.stage_values) * scaling
    phase_distance = float(
        np.sqrt(
            np.einsum(
                "i,j,ijq,ijq->",
                assembler.mesh.widths,
                assembler.phase_reference.quadrature_weights,
                stage_delta,
                stage_delta,
            )
        )
    )
    period = exp(variables.log_period)
    current_tangent = np.empty_like(variables.stages)
    for interval in range(assembler.layout.interval_count):
        current_tangent[interval, 0] = period * transformed_vector_field(
            variables.stages[interval, 0], assembler.env, assembler.coeff
        )
    scaled_current = current_tangent * scaling
    scaled_reference = assembler.phase_reference.stage_derivatives * scaling
    current_energy = float(
        np.einsum(
            "i,j,ijq,ijq->",
            assembler.mesh.widths,
            assembler.phase_reference.quadrature_weights,
            scaled_current,
            scaled_current,
        )
    )
    cross_energy = float(
        np.einsum(
            "i,j,ijq,ijq->",
            assembler.mesh.widths,
            assembler.phase_reference.quadrature_weights,
            scaled_current,
            scaled_reference,
        )
    )
    alignment = cross_energy / np.sqrt(current_energy * assembler.phase_energy)
    return {
        "point_id": point.point_id,
        "branch_id": point.branch_id,
        "point_kind": point.point_kind,
        "parent_point_id": point.parent_point_id,
        "phase_reference_id": point.phase_reference_id,
        "branch_orientation": point.branch_orientation,
        "active_coordinate_name": family.path.coordinate_name,
        "active_coordinate": point.coordinate,
        "temperature_hat": physical.temperature_hat,
        "rho": physical.rho,
        "temperature_K": physical.temperature_K,
        "log_w": physical.log_w,
        "w_m_s": physical.w_m_s,
        "period_s": period,
        "accepted_step_size": point.accepted_step_size,
        "stage_residual_max": diagnostics.stage_max,
        "stage_residual_rms": diagnostics.stage_rms,
        "update_residual_max": diagnostics.update_max,
        "update_residual_rms": diagnostics.update_rms,
        "phase_residual_abs": diagnostics.phase_abs,
        "phase_energy": assembler.phase_energy,
        "current_time_shift_energy": current_energy,
        "phase_reference_alignment_cosine": alignment,
        "weighted_distance_from_phase_reference": phase_distance,
    }
