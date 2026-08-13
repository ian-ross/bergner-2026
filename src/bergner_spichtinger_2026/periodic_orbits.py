"""Fixed-mesh periodic-orbit collocation primitives.

This module is the transparent Python reference formulation for the first
Episode 008 periodic-orbit milestone.  It stores periodic endpoints without a
duplicated terminal value, keeps collocation stages explicit, represents the
period by ``log(P)``, and assembles the one-stage Gauss (implicit midpoint)
base system and its analytic sparse Jacobian.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from operator import index
from typing import Callable, Iterable

import numpy as np
from scipy.optimize import least_squares, minimize_scalar
from scipy.sparse import csr_matrix

from . import constants as C
from .collocation_coefficients import CollocationRule, gauss_legendre_rule
from .constants import Environment
from .core import Coefficients, D_v, K_T, L, coefficients, vector_field
from .residuals import physical_state_from_log_coordinates
from .stability import physical_jacobian


ArrayLike = Iterable[float] | np.ndarray
STATE_DIMENSION = 3
MIDPOINT_FORMULATION_VERSION = "explicit-stage-midpoint-v1"
GAUSS_FORMULATION_VERSION = "explicit-stage-gauss-fixed-mesh-v1"
JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE = 1.0e-6
MIDPOINT_SOLVER_VERSION = "scipy-trf-block-acceptance-v1"
GAUSS_SOLVER_VERSION = "scipy-trf-gauss-block-acceptance-v1"
DEFECT_DIAGNOSTIC_VERSION = "two-grid-relative-defect-v1"
DEFECT_MATERIAL_ABSOLUTE_THRESHOLD = 1.0e-5
DEFECT_MATERIAL_RELATIVE_THRESHOLD = 0.5
DEFECT_RECURRENCE_BIN_COUNT = 128


def _positive_integer(value: int, name: str) -> int:
    try:
        result = index(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer.") from exc
    if result <= 0:
        raise ValueError(f"{name} must be positive.")
    return result


def _readonly_array(value: ArrayLike, *, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    result = np.array(value, dtype=float, copy=True)
    if shape is not None and result.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {result.shape}.")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values.")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class OrbitVariables:
    """Unpacked endpoint, explicit-stage, and log-period unknowns."""

    endpoints: np.ndarray
    stages: np.ndarray
    log_period: float


@dataclass(frozen=True)
class CollocationResidualBlocks:
    """Residual blocks in their natural interval/stage shapes."""

    stages: np.ndarray
    updates: np.ndarray
    phase: float


@dataclass(frozen=True)
class MidpointResidualTolerances:
    """Independent acceptance thresholds for a corrected midpoint orbit."""

    stage_max: float = 1.0e-9
    stage_rms: float = 1.0e-9
    update_max: float = 1.0e-9
    update_rms: float = 1.0e-9
    phase_abs: float = 1.0e-10

    def __post_init__(self) -> None:
        values = (
            self.stage_max,
            self.stage_rms,
            self.update_max,
            self.update_rms,
            self.phase_abs,
        )
        if not all(np.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("midpoint residual tolerances must be positive and finite.")


@dataclass(frozen=True)
class MidpointResidualDiagnostics:
    """Norms used to accept or reject a discrete nonlinear solution."""

    stage_max: float
    stage_rms: float
    update_max: float
    update_rms: float
    phase_abs: float


@dataclass(frozen=True)
class MidpointCorrectionResult:
    """A SciPy correction plus acceptance diagnostics independent of SciPy."""

    unknowns: np.ndarray
    residual: np.ndarray
    diagnostics: MidpointResidualDiagnostics
    accepted: bool
    rejection_reasons: tuple[str, ...]
    scipy_success: bool
    scipy_status: int
    scipy_message: str
    scipy_cost: float
    scipy_optimality: float
    function_evaluations: int
    jacobian_evaluations: int | None
    packed_step_norm: float


@dataclass(frozen=True)
class WeightedOrbitComparison:
    """Quadrature-weighted orbit distance and the applied reference phase shift."""

    distance: float
    phase_shift: float


@dataclass(frozen=True)
class DefectGridDiagnostics:
    """Scaled relative defects on one deterministic off-collocation grid."""

    name: str
    local_nodes: np.ndarray
    relative_defects: np.ndarray
    maximum: float
    argmax_interval: int
    argmax_local_node: float
    argmax_phase: float


@dataclass(frozen=True)
class IndependentDefectDiagnostics:
    """Two-grid fixed-mesh defect evidence independent of solver residuals."""

    next_gauss: DefectGridDiagnostics
    staggered_dyadic: DefectGridDiagnostics
    probe_16: DefectGridDiagnostics | None
    combined_element_maxima: np.ndarray
    admitted_probe_element_maxima: np.ndarray
    probe_admitted: np.ndarray
    maximum: float
    argmax_phase: float
    argmax_bin: int
    endpoint_left: np.ndarray
    endpoint_right: np.ndarray
    derivative_jumps: np.ndarray
    grid_disagreement: np.ndarray
    materially_disagreeing_elements: tuple[int, ...]


@dataclass(frozen=True)
class OrbitLayout:
    """Own all unknown and residual indices for a periodic collocation mesh.

    Unknowns are ordered as all endpoint blocks, all explicit stage blocks,
    and ``log(P)``.  Residuals are ordered as all stage equations, all cyclic
    endpoint updates, and the scalar phase equation.  Only ``N`` endpoint
    blocks are stored; endpoint ``N`` is endpoint ``0`` by periodic indexing.
    """

    interval_count: int
    stage_count: int = 1
    state_dimension: int = STATE_DIMENSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "interval_count", _positive_integer(self.interval_count, "interval_count"))
        object.__setattr__(self, "stage_count", _positive_integer(self.stage_count, "stage_count"))
        object.__setattr__(self, "state_dimension", _positive_integer(self.state_dimension, "state_dimension"))

    @property
    def endpoint_size(self) -> int:
        return self.interval_count * self.state_dimension

    @property
    def stage_size(self) -> int:
        return self.interval_count * self.stage_count * self.state_dimension

    @property
    def log_period_index(self) -> int:
        return self.endpoint_size + self.stage_size

    @property
    def unknown_size(self) -> int:
        return self.log_period_index + 1

    @property
    def stage_row_size(self) -> int:
        return self.stage_size

    @property
    def update_row_start(self) -> int:
        return self.stage_row_size

    @property
    def phase_row(self) -> int:
        return self.stage_row_size + self.endpoint_size

    @property
    def residual_size(self) -> int:
        return self.phase_row + 1

    def _interval_index(self, interval: int) -> int:
        result = index(interval)
        if not 0 <= result < self.interval_count:
            raise IndexError(f"interval index {result} is outside [0, {self.interval_count}).")
        return result

    def _stage_index(self, stage: int) -> int:
        result = index(stage)
        if not 0 <= result < self.stage_count:
            raise IndexError(f"stage index {result} is outside [0, {self.stage_count}).")
        return result

    def endpoint_slice(self, interval: int) -> slice:
        i = self._interval_index(interval)
        start = i * self.state_dimension
        return slice(start, start + self.state_dimension)

    def stage_slice(self, interval: int, stage: int = 0) -> slice:
        i = self._interval_index(interval)
        j = self._stage_index(stage)
        start = self.endpoint_size + (i * self.stage_count + j) * self.state_dimension
        return slice(start, start + self.state_dimension)

    def stage_row_slice(self, interval: int, stage: int = 0) -> slice:
        i = self._interval_index(interval)
        j = self._stage_index(stage)
        start = (i * self.stage_count + j) * self.state_dimension
        return slice(start, start + self.state_dimension)

    def update_row_slice(self, interval: int) -> slice:
        i = self._interval_index(interval)
        start = self.update_row_start + i * self.state_dimension
        return slice(start, start + self.state_dimension)

    def pack(self, endpoints: ArrayLike, stages: ArrayLike, log_period: float) -> np.ndarray:
        endpoint_array = np.asarray(endpoints, dtype=float)
        stage_array = np.asarray(stages, dtype=float)
        endpoint_shape = (self.interval_count, self.state_dimension)
        stage_shape = (self.interval_count, self.stage_count, self.state_dimension)
        if endpoint_array.shape != endpoint_shape:
            raise ValueError(f"endpoints must have shape {endpoint_shape}, got {endpoint_array.shape}.")
        if stage_array.shape != stage_shape:
            raise ValueError(f"stages must have shape {stage_shape}, got {stage_array.shape}.")
        result = np.empty(self.unknown_size, dtype=float)
        result[: self.endpoint_size] = endpoint_array.reshape(-1)
        result[self.endpoint_size : self.log_period_index] = stage_array.reshape(-1)
        result[self.log_period_index] = float(log_period)
        return result

    def unpack(self, unknowns: ArrayLike) -> OrbitVariables:
        vector = np.asarray(unknowns, dtype=float)
        if vector.shape != (self.unknown_size,):
            raise ValueError(f"unknowns must have shape ({self.unknown_size},), got {vector.shape}.")
        endpoints = vector[: self.endpoint_size].reshape(self.interval_count, self.state_dimension).copy()
        stages = vector[self.endpoint_size : self.log_period_index].reshape(
            self.interval_count, self.stage_count, self.state_dimension
        ).copy()
        return OrbitVariables(endpoints=endpoints, stages=stages, log_period=float(vector[self.log_period_index]))

    def pack_residual(self, blocks: CollocationResidualBlocks) -> np.ndarray:
        stage_shape = (self.interval_count, self.stage_count, self.state_dimension)
        update_shape = (self.interval_count, self.state_dimension)
        stages = np.asarray(blocks.stages, dtype=float)
        updates = np.asarray(blocks.updates, dtype=float)
        if stages.shape != stage_shape:
            raise ValueError(f"stage residuals must have shape {stage_shape}, got {stages.shape}.")
        if updates.shape != update_shape:
            raise ValueError(f"update residuals must have shape {update_shape}, got {updates.shape}.")
        result = np.empty(self.residual_size, dtype=float)
        result[: self.stage_row_size] = stages.reshape(-1)
        result[self.update_row_start : self.phase_row] = updates.reshape(-1)
        result[self.phase_row] = float(blocks.phase)
        return result

    def unpack_residual(self, residual: ArrayLike) -> CollocationResidualBlocks:
        vector = np.asarray(residual, dtype=float)
        if vector.shape != (self.residual_size,):
            raise ValueError(f"residual must have shape ({self.residual_size},), got {vector.shape}.")
        stages = vector[: self.stage_row_size].reshape(
            self.interval_count, self.stage_count, self.state_dimension
        ).copy()
        updates = vector[self.update_row_start : self.phase_row].reshape(
            self.interval_count, self.state_dimension
        ).copy()
        return CollocationResidualBlocks(stages=stages, updates=updates, phase=float(vector[self.phase_row]))


@dataclass(frozen=True)
class FixedMesh:
    """A fixed normalized-phase mesh represented by its ``N + 1`` boundaries."""

    boundaries: np.ndarray

    def __post_init__(self) -> None:
        boundaries = _readonly_array(self.boundaries, name="boundaries")
        if boundaries.ndim != 1 or boundaries.size < 2:
            raise ValueError("boundaries must be a one-dimensional array with at least two entries.")
        if boundaries[0] != 0.0 or boundaries[-1] != 1.0:
            raise ValueError("normalized mesh boundaries must start at 0 and end at 1.")
        if np.any(np.diff(boundaries) <= 0.0):
            raise ValueError("mesh boundaries must be strictly increasing.")
        object.__setattr__(self, "boundaries", boundaries)

    @classmethod
    def uniform(cls, interval_count: int) -> FixedMesh:
        count = _positive_integer(interval_count, "interval_count")
        return cls(np.linspace(0.0, 1.0, count + 1))

    @property
    def interval_count(self) -> int:
        return self.boundaries.size - 1

    @property
    def widths(self) -> np.ndarray:
        result = np.diff(self.boundaries)
        result.setflags(write=False)
        return result

    def stage_phases(self, nodes: ArrayLike) -> np.ndarray:
        node_array = np.asarray(nodes, dtype=float)
        if node_array.ndim != 1 or node_array.size == 0:
            raise ValueError("nodes must be a nonempty one-dimensional array.")
        if not np.all(np.isfinite(node_array)) or np.any((node_array < 0.0) | (node_array > 1.0)):
            raise ValueError("collocation nodes must be finite and lie in [0, 1].")
        return self.boundaries[:-1, None] + self.widths[:, None] * node_array[None, :]


@dataclass(frozen=True)
class FrozenPhaseReference:
    """Stage-sampled orbit reference frozen for one collocation segment."""

    mesh: FixedMesh
    stage_values: np.ndarray
    stage_derivatives: np.ndarray
    state_scaling: np.ndarray
    collocation_nodes: np.ndarray
    quadrature_weights: np.ndarray
    phase_energy: float = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mesh, FixedMesh):
            raise TypeError("mesh must be a FixedMesh.")
        values = np.array(self.stage_values, dtype=float, copy=True)
        derivatives = np.array(self.stage_derivatives, dtype=float, copy=True)
        scaling = _readonly_array(self.state_scaling, name="state_scaling", shape=(STATE_DIMENSION,))
        nodes = np.array(self.collocation_nodes, dtype=float, copy=True)
        weights = np.array(self.quadrature_weights, dtype=float, copy=True)
        expected_prefix = (self.mesh.interval_count,)
        if values.ndim != 3 or values.shape[0:1] != expected_prefix or values.shape[2] != STATE_DIMENSION:
            raise ValueError(
                "stage_values must have shape "
                f"({self.mesh.interval_count}, stage_count, {STATE_DIMENSION}), got {values.shape}."
            )
        if derivatives.shape != values.shape:
            raise ValueError(f"stage_derivatives must have shape {values.shape}, got {derivatives.shape}.")
        if nodes.shape != (values.shape[1],):
            raise ValueError(f"collocation_nodes must have shape ({values.shape[1]},), got {nodes.shape}.")
        if weights.shape != (values.shape[1],):
            raise ValueError(f"quadrature_weights must have shape ({values.shape[1]},), got {weights.shape}.")
        if not np.all(np.isfinite(values)) or not np.all(np.isfinite(derivatives)):
            raise ValueError("phase-reference samples must contain only finite values.")
        if np.any(scaling <= 0.0):
            raise ValueError("state_scaling entries must be positive.")
        if not np.all(np.isfinite(nodes)) or np.any((nodes < 0.0) | (nodes > 1.0)):
            raise ValueError("collocation_nodes must be finite and lie in [0, 1].")
        if not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
            raise ValueError("quadrature_weights must be finite and positive.")
        if not np.isclose(np.sum(weights), 1.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("quadrature_weights must sum to one.")
        scaled_derivatives = derivatives * scaling
        energy = float(
            np.einsum(
                "i,j,ijq,ijq->",
                self.mesh.widths,
                weights,
                scaled_derivatives,
                scaled_derivatives,
            )
        )
        if not np.isfinite(energy) or energy <= 0.0:
            raise ValueError("phase reference must have positive finite phase energy.")
        values.setflags(write=False)
        derivatives.setflags(write=False)
        nodes.setflags(write=False)
        weights.setflags(write=False)
        object.__setattr__(self, "stage_values", values)
        object.__setattr__(self, "stage_derivatives", derivatives)
        object.__setattr__(self, "state_scaling", scaling)
        object.__setattr__(self, "collocation_nodes", nodes)
        object.__setattr__(self, "quadrature_weights", weights)
        object.__setattr__(self, "phase_energy", energy)

    @classmethod
    def from_evaluator(
        cls,
        mesh: FixedMesh,
        rule: CollocationRule,
        evaluate: Callable[[np.ndarray], ArrayLike],
        derivative: Callable[[np.ndarray], ArrayLike],
        *,
        state_scaling: ArrayLike | None = None,
    ) -> FrozenPhaseReference:
        """Freeze a periodic evaluator at the rule's collocation stages."""
        phases = mesh.stage_phases(rule.nodes)
        flat_phases = phases.reshape(-1)
        flat_shape = (flat_phases.size, STATE_DIMENSION)
        values_flat = np.asarray(evaluate(flat_phases), dtype=float)
        derivatives_flat = np.asarray(derivative(flat_phases), dtype=float)
        if values_flat.shape != flat_shape:
            raise ValueError(f"evaluate must return shape {flat_shape}, got {values_flat.shape}.")
        if derivatives_flat.shape != flat_shape:
            raise ValueError(f"derivative must return shape {flat_shape}, got {derivatives_flat.shape}.")
        expected_shape = (mesh.interval_count, rule.stage_count, STATE_DIMENSION)
        values = values_flat.reshape(expected_shape)
        derivatives = derivatives_flat.reshape(expected_shape)
        scaling = np.ones(STATE_DIMENSION) if state_scaling is None else state_scaling
        return cls(
            mesh=mesh,
            stage_values=values,
            stage_derivatives=derivatives,
            state_scaling=np.asarray(scaling, dtype=float),
            collocation_nodes=np.asarray(rule.nodes, dtype=float),
            quadrature_weights=np.asarray(rule.quadrature_weights, dtype=float),
        )


def transformed_vector_field(
    log_state: ArrayLike,
    env: Environment,
    coeff: Coefficients | None = None,
) -> np.ndarray:
    """Evaluate ``g=(dn/dt/n, dq/dt/q, ds/dt)`` in ``(log(n), log(q), s)``."""
    state = np.asarray(log_state, dtype=float)
    if state.shape != (STATE_DIMENSION,):
        raise ValueError(f"log_state must have shape ({STATE_DIMENSION},).")
    if not np.all(np.isfinite(state)):
        raise ValueError("log_state must contain only finite values.")
    n, q, s = physical_state_from_log_coordinates(state)
    rhs = vector_field(float(n), float(q), float(s), env, coeff)
    return np.array([rhs[0] / n, rhs[1] / q, rhs[2]], dtype=float)


def transformed_vector_field_environment_derivatives(
    log_state: ArrayLike,
    env: Environment,
    coeff: Coefficients | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return analytic ``(g_T, g_log_w)`` at fixed transformed state.

    This is the Python reference counterpart of the local Sacado derivatives
    planned for C++.  It differentiates every temperature-dependent model
    coefficient explicitly; finite differences are reserved for validation.
    """
    if env.include_evaporation:
        raise ValueError("environment derivatives require the smooth no-evaporation model.")
    state = np.asarray(log_state, dtype=float)
    if state.shape != (STATE_DIMENSION,) or not np.all(np.isfinite(state)):
        raise ValueError(f"log_state must be a finite vector of shape ({STATE_DIMENSION},).")
    n, q, s = physical_state_from_log_coordinates(state)
    c = coeff or coefficients(env)
    temperature = env.T

    latent = L(temperature)
    latent_molar_prime = (
        C.l1
        + 2.0 * C.l2 * temperature
        - 2.0 * C.l3 * temperature / C.T_l**2 * exp(-((temperature / C.T_l) ** 2))
    )
    latent_prime = latent_molar_prime / C.M_mol_v
    saturation_log_prime = -C.b1 / temperature**2 + C.b2 / temperature + C.b3
    diffusivity_log_prime = 2.0 / temperature
    conduction_denominator = temperature + C.T_K * 10.0 ** (C.c_K / temperature)
    conduction_denominator_prime = 1.0 + (
        C.T_K
        * 10.0 ** (C.c_K / temperature)
        * np.log(10.0)
        * (-C.c_K / temperature**2)
    )
    conduction_log_prime = C.b_K / temperature - conduction_denominator_prime / conduction_denominator

    diffusion = D_v(temperature, env.p)
    conduction = K_T(temperature)
    howell_first = latent / (C.R_v * temperature) - 1.0
    howell_first_prime = latent_prime / (C.R_v * temperature) - latent / (C.R_v * temperature**2)
    howell_second = latent * diffusion / (temperature * conduction)
    howell_second_log_prime = (
        latent_prime / latent
        + diffusivity_log_prime
        - 1.0 / temperature
        - conduction_log_prime
    )
    howell_second_prime = howell_second * howell_second_log_prime
    howell_third = C.R_v * temperature / c.p_si
    howell_third_prime = howell_third * (1.0 / temperature - saturation_log_prime)
    howell_denominator = howell_first * howell_second + howell_third
    howell_denominator_prime = (
        howell_first_prime * howell_second
        + howell_first * howell_second_prime
        + howell_third_prime
    )
    growth_log_prime = -howell_denominator_prime / howell_denominator

    cooling_prime = C.g * (
        latent_prime / (C.c_p * C.R_v * temperature**2)
        - 2.0 * latent / (C.c_p * C.R_v * temperature**3)
        + 1.0 / (C.R_d * temperature**2)
    )
    p1e_prime = np.log(10.0) * C.p1_a1
    p2_prime = 2.0 * C.p2_as2 * temperature + C.p2_as1
    exponent = exp(c.p1e * (s - c.p2))
    exponent_log_prime = p1e_prime * (s - c.p2) - c.p1e * p2_prime

    an_prime = c.A_n / temperature
    aq_prime = c.A_q / temperature
    as_prime = c.A_s * (1.0 / temperature - saturation_log_prime)
    bq_prime = c.B_q * (growth_log_prime + diffusivity_log_prime)
    bs_prime = c.B_s * (growth_log_prime + diffusivity_log_prime - saturation_log_prime)
    cn_prime = c.C_n * C.b_c / temperature
    cq_prime = c.C_q * C.b_c / temperature

    n_two_thirds = n ** (2.0 / 3.0)
    q_one_third = q ** (1.0 / 3.0)
    sediment_number_shape = n ** (1.0 / 3.0) * q ** (2.0 / 3.0)
    sediment_mass_shape = n ** (-2.0 / 3.0) * q ** (5.0 / 3.0)
    nucleation_number_T = (an_prime + c.A_n * exponent_log_prime) * exponent
    nucleation_mass_T = (aq_prime + c.A_q * exponent_log_prime) * exponent
    nucleation_saturation_T = -(as_prime + c.A_s * exponent_log_prime) * exponent
    deposition_mass_T = bq_prime * n_two_thirds * q_one_third * (s - 1.0)
    deposition_saturation_T = -bs_prime * n_two_thirds * q_one_third * (s - 1.0)
    sediment_number_T = -env.F * cn_prime * sediment_number_shape
    sediment_mass_T = -env.F * cq_prime * sediment_mass_shape
    cooling_T = cooling_prime * env.w * s

    physical_T = np.array(
        [
            nucleation_number_T + sediment_number_T,
            nucleation_mass_T + deposition_mass_T + sediment_mass_T,
            cooling_T + nucleation_saturation_T + deposition_saturation_T,
        ]
    )
    transformed_T = np.array([physical_T[0] / n, physical_T[1] / q, physical_T[2]])
    transformed_log_w = np.array([0.0, 0.0, c.D * env.w * s])
    return transformed_T, transformed_log_w


def transformed_vector_field_jacobian(
    log_state: ArrayLike,
    env: Environment,
    coeff: Coefficients | None = None,
) -> np.ndarray:
    """Evaluate the analytic derivative ``D_x g`` in transformed coordinates."""
    if env.include_evaporation:
        raise ValueError("transformed Jacobian does not support the discontinuous evaporation term.")
    state = np.asarray(log_state, dtype=float)
    physical_state = physical_state_from_log_coordinates(state)
    n, q, _ = physical_state
    c = coeff or coefficients(env)
    g = transformed_vector_field(state, env, c)
    jacobian = (
        np.diag([1.0 / n, 1.0 / q, 1.0])
        @ physical_jacobian(physical_state, env=env, coeff=c)
        @ np.diag([n, q, 1.0])
    )
    jacobian[0, 0] -= g[0]
    jacobian[1, 1] -= g[1]
    return jacobian


class GaussCollocationAssembler:
    """Assemble a fixed-parameter explicit-stage Gauss collocation system."""

    def __init__(
        self,
        mesh: FixedMesh,
        env: Environment,
        phase_reference: FrozenPhaseReference,
        rule: CollocationRule,
        *,
        coeff: Coefficients | None = None,
    ) -> None:
        if env.include_evaporation:
            raise ValueError("Gauss collocation requires the smooth no-evaporation model.")
        if not isinstance(mesh, FixedMesh):
            raise TypeError("mesh must be a FixedMesh.")
        if not isinstance(phase_reference, FrozenPhaseReference):
            raise TypeError("phase_reference must be a FrozenPhaseReference.")
        if not np.array_equal(mesh.boundaries, phase_reference.mesh.boundaries):
            raise ValueError("phase-reference mesh does not match the assembler mesh.")
        if not isinstance(rule, CollocationRule):
            raise TypeError("rule must be a CollocationRule.")
        canonical_rule = gauss_legendre_rule(rule.stage_count)
        if rule != canonical_rule:
            raise ValueError("rule must be one of the frozen one-, two-, or three-stage Gauss rules.")
        if phase_reference.stage_values.shape[1] != rule.stage_count:
            raise ValueError("phase reference stage count does not match the Gauss rule.")
        if not np.array_equal(phase_reference.collocation_nodes, np.asarray(rule.nodes)):
            raise ValueError("phase-reference nodes do not match the Gauss rule.")
        if not np.array_equal(phase_reference.quadrature_weights, np.asarray(rule.quadrature_weights)):
            raise ValueError("phase-reference quadrature does not match the Gauss rule.")
        self.mesh = mesh
        self.env = env
        self.phase_reference = phase_reference
        self.rule = rule
        self.layout = OrbitLayout(mesh.interval_count, rule.stage_count, STATE_DIMENSION)
        self.coeff = coeff or coefficients(env)

    @property
    def formulation_version(self) -> str:
        return GAUSS_FORMULATION_VERSION

    @property
    def phase_energy(self) -> float:
        return self.phase_reference.phase_energy

    @property
    def state_scaling(self) -> np.ndarray:
        return self.phase_reference.state_scaling

    def _variables(self, unknowns: ArrayLike) -> OrbitVariables:
        vector = np.asarray(unknowns, dtype=float)
        if vector.shape != (self.layout.unknown_size,):
            raise ValueError(
                f"unknowns must have shape ({self.layout.unknown_size},), got {vector.shape}."
            )
        if not np.all(np.isfinite(vector)):
            raise ValueError("unknowns must contain only finite values.")
        return self.layout.unpack(vector)

    def _stage_model_values(self, stages: np.ndarray, *, with_jacobian: bool) -> tuple[np.ndarray, np.ndarray | None]:
        values = np.empty_like(stages)
        jacobians = (
            np.empty(stages.shape + (STATE_DIMENSION,), dtype=float) if with_jacobian else None
        )
        for interval in range(self.layout.interval_count):
            for stage in range(self.layout.stage_count):
                state = stages[interval, stage]
                values[interval, stage] = transformed_vector_field(state, self.env, self.coeff)
                if jacobians is not None:
                    jacobians[interval, stage] = transformed_vector_field_jacobian(
                        state, self.env, self.coeff
                    )
        return values, jacobians

    def residual_blocks(self, unknowns: ArrayLike) -> CollocationResidualBlocks:
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        field, _ = self._stage_model_values(variables.stages, with_jacobian=False)
        stages = np.empty_like(variables.stages)
        updates = np.empty_like(variables.endpoints)
        scaling = self.state_scaling
        stage_coefficients = np.asarray(self.rule.stage_coefficients)
        update_weights = np.asarray(self.rule.quadrature_weights)
        for interval, width in enumerate(self.mesh.widths):
            endpoint = variables.endpoints[interval]
            next_endpoint = variables.endpoints[(interval + 1) % self.layout.interval_count]
            if self.layout.stage_count == 1:
                # Preserve the established midpoint operation order exactly.
                stage_field = field[interval, 0]
                stages[interval, 0] = scaling * (
                    variables.stages[interval, 0]
                    - endpoint
                    - width * period * stage_coefficients[0, 0] * stage_field
                )
                updates[interval] = scaling * (
                    next_endpoint - endpoint - width * period * update_weights[0] * stage_field
                )
                continue
            for stage in range(self.layout.stage_count):
                weighted_field = np.zeros(STATE_DIMENSION)
                for coupled_stage in range(self.layout.stage_count):
                    weighted_field += stage_coefficients[stage, coupled_stage] * field[
                        interval, coupled_stage
                    ]
                stages[interval, stage] = scaling * (
                    variables.stages[interval, stage]
                    - endpoint
                    - width * period * weighted_field
                )
            update_field = np.zeros(STATE_DIMENSION)
            for stage in range(self.layout.stage_count):
                update_field += update_weights[stage] * field[interval, stage]
            updates[interval] = scaling * (
                next_endpoint - endpoint - width * period * update_field
            )
        delta = (variables.stages - self.phase_reference.stage_values) * scaling
        tangent = self.phase_reference.stage_derivatives * scaling
        numerator = float(
            np.einsum(
                "i,j,ijq,ijq->",
                self.mesh.widths,
                self.phase_reference.quadrature_weights,
                delta,
                tangent,
            )
        )
        return CollocationResidualBlocks(
            stages=stages,
            updates=updates,
            phase=numerator / self.phase_energy,
        )

    def residual(self, unknowns: ArrayLike) -> np.ndarray:
        """Return stage, cyclic-update, and normalized-phase residuals."""
        return self.layout.pack_residual(self.residual_blocks(unknowns))

    @staticmethod
    def _append_diagonal(
        rows: list[int],
        columns: list[int],
        data: list[float],
        row_start: int,
        column_start: int,
        diagonal: np.ndarray,
    ) -> None:
        for component, value in enumerate(diagonal):
            rows.append(row_start + component)
            columns.append(column_start + component)
            data.append(float(value))

    @staticmethod
    def _append_dense(
        rows: list[int],
        columns: list[int],
        data: list[float],
        row_start: int,
        column_start: int,
        block: np.ndarray,
    ) -> None:
        for row_component in range(block.shape[0]):
            for column_component in range(block.shape[1]):
                rows.append(row_start + row_component)
                columns.append(column_start + column_component)
                data.append(float(block[row_component, column_component]))

    @staticmethod
    def _append_column(
        rows: list[int],
        columns: list[int],
        data: list[float],
        row_start: int,
        column: int,
        values: np.ndarray,
    ) -> None:
        for component, value in enumerate(values):
            rows.append(row_start + component)
            columns.append(column)
            data.append(float(value))

    @staticmethod
    def _append_row(
        rows: list[int],
        columns: list[int],
        data: list[float],
        row: int,
        column_start: int,
        values: np.ndarray,
    ) -> None:
        for component, value in enumerate(values):
            rows.append(row)
            columns.append(column_start + component)
            data.append(float(value))

    def weighted_orbit_distance(self, first: ArrayLike, second: ArrayLike) -> float:
        """Return the mesh-independent endpoint/stage weighted orbit distance.

        Endpoint and collocation-stage representations each receive half of the
        total orbit weight.  The result therefore approximates one scaled L2
        orbit norm without doubling merely because both representations are
        stored, and its normalization does not depend on the interval count.
        """
        first_variables = self._variables(first)
        second_variables = self._variables(second)
        endpoint_delta = (first_variables.endpoints - second_variables.endpoints) * self.state_scaling
        stage_delta = (first_variables.stages - second_variables.stages) * self.state_scaling
        next_endpoint_delta = np.roll(endpoint_delta, -1, axis=0)
        endpoint_term = 0.5 * np.einsum(
            "i,iq,iq->",
            self.mesh.widths,
            endpoint_delta,
            endpoint_delta,
        ) + 0.5 * np.einsum(
            "i,iq,iq->",
            self.mesh.widths,
            next_endpoint_delta,
            next_endpoint_delta,
        )
        stage_term = np.einsum(
            "i,j,ijq,ijq->",
            self.mesh.widths,
            np.asarray(self.rule.quadrature_weights),
            stage_delta,
            stage_delta,
        )
        return float(np.sqrt(0.5 * (endpoint_term + stage_term)))

    def reference_unknowns(
        self,
        evaluate: Callable[[np.ndarray], ArrayLike],
        log_period: float,
        *,
        phase_shift: float = 0.0,
    ) -> np.ndarray:
        """Sample a continuous periodic reference into this assembler's layout."""
        endpoint_phases = np.mod(self.mesh.boundaries[:-1] + phase_shift, 1.0)
        stage_phases = np.mod(
            self.mesh.stage_phases(self.rule.nodes).reshape(-1) + phase_shift,
            1.0,
        )
        endpoints = np.asarray(evaluate(endpoint_phases), dtype=float)
        stages = np.asarray(evaluate(stage_phases), dtype=float).reshape(
            self.layout.interval_count,
            self.layout.stage_count,
            STATE_DIMENSION,
        )
        return self.layout.pack(endpoints, stages, log_period)

    def polynomial_evaluator(self, unknowns: ArrayLike) -> Callable[[ArrayLike], np.ndarray]:
        """Return the periodic piecewise collocation-polynomial state evaluator."""
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        field, _ = self._stage_model_values(variables.stages, with_jacobian=False)
        transfer = np.asarray(self.rule.transfer_coefficients)
        boundaries = self.mesh.boundaries

        def evaluate(phases: ArrayLike) -> np.ndarray:
            values = np.asarray(phases, dtype=float)
            scalar = values.ndim == 0
            flat = np.mod(values.reshape(-1), 1.0)
            intervals = np.searchsorted(boundaries, flat, side="right") - 1
            intervals = np.clip(intervals, 0, self.layout.interval_count - 1)
            tau = (flat - boundaries[intervals]) / self.mesh.widths[intervals]
            result = variables.endpoints[intervals].copy()
            powers = tau[:, None] ** np.arange(transfer.shape[1])[None, :]
            integrated = powers @ transfer.T
            for row, interval in enumerate(intervals):
                result[row] += (
                    self.mesh.widths[interval]
                    * period
                    * np.einsum("j,jq->q", integrated[row], field[interval])
                )
            return result[0] if scalar else result.reshape(values.shape + (STATE_DIMENSION,))

        return evaluate

    def polynomial_derivative_evaluator(
        self, unknowns: ArrayLike
    ) -> Callable[[ArrayLike], np.ndarray]:
        """Return ``dp/dtheta`` from the piecewise collocation polynomial."""
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        field, _ = self._stage_model_values(variables.stages, with_jacobian=False)
        coefficients = np.asarray(self.rule.transfer_coefficients)
        derivative_coefficients = (
            coefficients[:, 1:] * np.arange(1, coefficients.shape[1])[None, :]
        )
        boundaries = self.mesh.boundaries

        def evaluate(phases: ArrayLike) -> np.ndarray:
            values = np.asarray(phases, dtype=float)
            scalar = values.ndim == 0
            flat = np.mod(values.reshape(-1), 1.0)
            intervals = np.searchsorted(boundaries, flat, side="right") - 1
            intervals = np.clip(intervals, 0, self.layout.interval_count - 1)
            tau = (flat - boundaries[intervals]) / self.mesh.widths[intervals]
            powers = tau[:, None] ** np.arange(derivative_coefficients.shape[1])[None, :]
            lagrange = powers @ derivative_coefficients.T
            result = np.empty((flat.size, STATE_DIMENSION))
            for row, interval in enumerate(intervals):
                result[row] = period * np.einsum("j,jq->q", lagrange[row], field[interval])
            return result[0] if scalar else result.reshape(values.shape + (STATE_DIMENSION,))

        return evaluate

    def transfer_unknowns(
        self,
        unknowns: ArrayLike,
        destination_mesh: FixedMesh,
        destination_rule: CollocationRule,
    ) -> np.ndarray:
        """Evaluate this collocation polynomial into another fixed Gauss layout."""
        variables = self._variables(unknowns)
        evaluate = self.polynomial_evaluator(unknowns)
        destination_layout = OrbitLayout(
            destination_mesh.interval_count, destination_rule.stage_count, STATE_DIMENSION
        )
        endpoints = evaluate(destination_mesh.boundaries[:-1])
        stages = evaluate(destination_mesh.stage_phases(destination_rule.nodes).reshape(-1)).reshape(
            destination_mesh.interval_count, destination_rule.stage_count, STATE_DIMENSION
        )
        return destination_layout.pack(endpoints, stages, variables.log_period)

    def transferred_phase_reference(
        self,
        unknowns: ArrayLike,
        destination_mesh: FixedMesh,
        destination_rule: CollocationRule,
    ) -> FrozenPhaseReference:
        """Freeze the represented orbit and its polynomial derivative on a new rule/mesh."""
        return FrozenPhaseReference.from_evaluator(
            destination_mesh,
            destination_rule,
            self.polynomial_evaluator(unknowns),
            self.polynomial_derivative_evaluator(unknowns),
            state_scaling=self.state_scaling,
        )

    def compare_with_collocation(
        self,
        unknowns: ArrayLike,
        reference_assembler: GaussCollocationAssembler,
        reference_unknowns: ArrayLike,
        *,
        align_phase: bool = True,
    ) -> WeightedOrbitComparison:
        reference_variables = reference_assembler._variables(reference_unknowns)
        return self.compare_with_reference(
            unknowns,
            reference_assembler.polynomial_evaluator(reference_unknowns),
            reference_variables.log_period,
            align_phase=align_phase,
        )

    def compare_with_reference(
        self,
        unknowns: ArrayLike,
        evaluate: Callable[[np.ndarray], ArrayLike],
        log_period: float,
        *,
        align_phase: bool = True,
    ) -> WeightedOrbitComparison:
        """Compare to a continuous reference after an optional periodic phase fit."""
        candidate = np.asarray(unknowns, dtype=float)

        def distance(phase_shift: float) -> float:
            reference = self.reference_unknowns(evaluate, log_period, phase_shift=phase_shift)
            return self.weighted_orbit_distance(candidate, reference)

        if not align_phase:
            return WeightedOrbitComparison(distance=distance(0.0), phase_shift=0.0)
        optimum = minimize_scalar(
            distance,
            bounds=(-0.5, 0.5),
            method="bounded",
            options={"xatol": 1.0e-12},
        )
        phase_shift = float(optimum.x)
        wrapped_shift = (phase_shift + 0.5) % 1.0 - 0.5
        return WeightedOrbitComparison(distance=distance(wrapped_shift), phase_shift=wrapped_shift)

    def _defect_grid(
        self,
        unknowns: ArrayLike,
        name: str,
        local_nodes: np.ndarray,
    ) -> DefectGridDiagnostics:
        evaluate = self.polynomial_evaluator(unknowns)
        derivative = self.polynomial_derivative_evaluator(unknowns)
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        phases = self.mesh.stage_phases(local_nodes)
        states = evaluate(phases.reshape(-1)).reshape(phases.shape + (STATE_DIMENSION,))
        polynomial_slopes = derivative(phases.reshape(-1)).reshape(states.shape)
        ode_slopes = np.empty_like(states)
        for interval in range(self.layout.interval_count):
            for node in range(local_nodes.size):
                ode_slopes[interval, node] = period * transformed_vector_field(
                    states[interval, node], self.env, self.coeff
                )
        scaled_difference = (polynomial_slopes - ode_slopes) * self.state_scaling
        scaled_ode = ode_slopes * self.state_scaling
        relative = np.linalg.norm(scaled_difference, axis=2) / (
            1.0 + np.linalg.norm(scaled_ode, axis=2)
        )
        flat_index = int(np.argmax(relative))
        interval, node = np.unravel_index(flat_index, relative.shape)
        local = float(local_nodes[node])
        phase = float(self.mesh.boundaries[interval] + self.mesh.widths[interval] * local)
        nodes = np.array(local_nodes, copy=True)
        relative.setflags(write=False)
        nodes.setflags(write=False)
        return DefectGridDiagnostics(
            name=name,
            local_nodes=nodes,
            relative_defects=relative,
            maximum=float(relative[interval, node]),
            argmax_interval=int(interval),
            argmax_local_node=local,
            argmax_phase=phase,
        )

    def independent_defect(self, unknowns: ArrayLike) -> IndependentDefectDiagnostics:
        """Evaluate the TASK-062 two-grid independent fixed-mesh defect contract."""
        next_grid = self._defect_grid(
            unknowns,
            "next_higher_gauss",
            np.asarray(self.rule.defect_check_nodes),
        )
        dyadic = self._defect_grid(
            unknowns,
            "staggered_dyadic",
            np.asarray((0.125, 0.375, 0.625, 0.875)),
        )
        next_element = np.max(next_grid.relative_defects, axis=1)
        dyadic_element = np.max(dyadic.relative_defects, axis=1)
        larger = np.maximum(next_element, dyadic_element)
        disagreement = np.divide(
            np.abs(next_element - dyadic_element),
            larger,
            out=np.zeros_like(larger),
            where=larger > 0.0,
        )
        material = np.flatnonzero(
            (larger > DEFECT_MATERIAL_ABSOLUTE_THRESHOLD)
            & (disagreement > DEFECT_MATERIAL_RELATIVE_THRESHOLD)
        )
        probe = None
        combined = larger.copy()
        probe_admitted = np.zeros(self.layout.interval_count, dtype=bool)
        admitted_probe = np.zeros(self.layout.interval_count, dtype=float)
        if material.size:
            probe = self._defect_grid(
                unknowns,
                "uniform_probe_16",
                (np.arange(16, dtype=float) + 0.5) / 16.0,
            )
            probe_element = np.max(probe.relative_defects, axis=1)
            probe_admitted[material] = True
            admitted_probe[material] = probe_element[material]
            combined[material] = np.maximum(combined[material], probe_element[material])

        evaluate = self.polynomial_evaluator(unknowns)
        derivative = self.polynomial_derivative_evaluator(unknowns)
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        epsilon = np.finfo(float).eps * 32.0
        left_phases = self.mesh.boundaries[:-1] + epsilon * self.mesh.widths
        right_phases = self.mesh.boundaries[1:] - epsilon * self.mesh.widths

        def point_defect(phases: np.ndarray) -> np.ndarray:
            states = evaluate(phases)
            slopes = derivative(phases)
            ode = np.array(
                [period * transformed_vector_field(state, self.env, self.coeff) for state in states]
            )
            return np.linalg.norm((slopes - ode) * self.state_scaling, axis=1) / (
                1.0 + np.linalg.norm(ode * self.state_scaling, axis=1)
            )

        endpoint_left = point_defect(left_phases)
        endpoint_right = point_defect(right_phases)
        left_slopes = derivative(left_phases)
        right_slopes = derivative(right_phases)
        derivative_jumps = np.linalg.norm(
            (np.roll(left_slopes, -1, axis=0) - right_slopes) * self.state_scaling,
            axis=1,
        )
        interval = int(np.argmax(combined))
        admitted_grids = [next_grid, dyadic]
        if probe is not None and probe_admitted[interval]:
            admitted_grids.append(probe)
        best_grid = max(
            admitted_grids,
            key=lambda grid: float(np.max(grid.relative_defects[interval])),
        )
        best_node = int(np.argmax(best_grid.relative_defects[interval]))
        maximum = float(best_grid.relative_defects[interval, best_node])
        if maximum != float(combined[interval]):
            raise RuntimeError("independent-defect maximum and admitted argmax are inconsistent.")
        argmax_phase = float(
            self.mesh.boundaries[interval]
            + self.mesh.widths[interval] * best_grid.local_nodes[best_node]
        )
        argmax_bin = int(np.floor(DEFECT_RECURRENCE_BIN_COUNT * (argmax_phase % 1.0)))
        combined.setflags(write=False)
        admitted_probe.setflags(write=False)
        probe_admitted.setflags(write=False)
        disagreement.setflags(write=False)
        endpoint_left.setflags(write=False)
        endpoint_right.setflags(write=False)
        derivative_jumps.setflags(write=False)
        return IndependentDefectDiagnostics(
            next_gauss=next_grid,
            staggered_dyadic=dyadic,
            probe_16=probe,
            combined_element_maxima=combined,
            admitted_probe_element_maxima=admitted_probe,
            probe_admitted=probe_admitted,
            maximum=maximum,
            argmax_phase=argmax_phase,
            argmax_bin=argmax_bin,
            endpoint_left=endpoint_left,
            endpoint_right=endpoint_right,
            derivative_jumps=derivative_jumps,
            grid_disagreement=disagreement,
            materially_disagreeing_elements=tuple(int(value) for value in material),
        )

    def jacobian(self, unknowns: ArrayLike) -> csr_matrix:
        """Return the explicitly assembled analytic sparse CSR Jacobian."""
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        field, field_jacobian = self._stage_model_values(variables.stages, with_jacobian=True)
        assert field_jacobian is not None
        rows: list[int] = []
        columns: list[int] = []
        data: list[float] = []
        scaling = self.state_scaling
        row_scaling = np.diag(scaling)
        stage_coefficients = np.asarray(self.rule.stage_coefficients)
        update_weights = np.asarray(self.rule.quadrature_weights)
        identity = np.eye(STATE_DIMENSION)

        for interval, width in enumerate(self.mesh.widths):
            update_row = self.layout.update_row_slice(interval).start
            endpoint_column = self.layout.endpoint_slice(interval).start
            next_endpoint_column = self.layout.endpoint_slice(
                (interval + 1) % self.layout.interval_count
            ).start

            for stage in range(self.layout.stage_count):
                stage_row = self.layout.stage_row_slice(interval, stage).start
                self._append_diagonal(rows, columns, data, stage_row, endpoint_column, -scaling)
                log_period_field = np.zeros(STATE_DIMENSION)
                for coupled_stage in range(self.layout.stage_count):
                    stage_column = self.layout.stage_slice(interval, coupled_stage).start
                    coefficient = stage_coefficients[stage, coupled_stage]
                    block = -width * period * coefficient * field_jacobian[
                        interval, coupled_stage
                    ]
                    if coupled_stage == stage:
                        block = identity + block
                    self._append_dense(
                        rows, columns, data, stage_row, stage_column, row_scaling @ block
                    )
                    log_period_field += coefficient * field[interval, coupled_stage]
                self._append_column(
                    rows,
                    columns,
                    data,
                    stage_row,
                    self.layout.log_period_index,
                    scaling * (-width * period * log_period_field),
                )

            self._append_diagonal(rows, columns, data, update_row, endpoint_column, -scaling)
            self._append_diagonal(rows, columns, data, update_row, next_endpoint_column, scaling)
            update_field = np.zeros(STATE_DIMENSION)
            for stage in range(self.layout.stage_count):
                stage_column = self.layout.stage_slice(interval, stage).start
                weight = update_weights[stage]
                self._append_dense(
                    rows,
                    columns,
                    data,
                    update_row,
                    stage_column,
                    row_scaling @ (-width * period * weight * field_jacobian[interval, stage]),
                )
                update_field += weight * field[interval, stage]
                phase_gradient = (
                    width
                    * weight
                    * scaling**2
                    * self.phase_reference.stage_derivatives[interval, stage]
                    / self.phase_energy
                )
                self._append_row(
                    rows,
                    columns,
                    data,
                    self.layout.phase_row,
                    stage_column,
                    phase_gradient,
                )
            self._append_column(
                rows,
                columns,
                data,
                update_row,
                self.layout.log_period_index,
                scaling * (-width * period * update_field),
            )

        result = csr_matrix(
            (data, (rows, columns)),
            shape=(self.layout.residual_size, self.layout.unknown_size),
        )
        result.sum_duplicates()
        result.sort_indices()
        return result


class MidpointCollocationAssembler(GaussCollocationAssembler):
    """Compatibility wrapper for the established one-stage midpoint contract."""

    def __init__(
        self,
        mesh: FixedMesh,
        env: Environment,
        phase_reference: FrozenPhaseReference,
        *,
        coeff: Coefficients | None = None,
    ) -> None:
        super().__init__(
            mesh,
            env,
            phase_reference,
            gauss_legendre_rule(1),
            coeff=coeff,
        )

    @property
    def formulation_version(self) -> str:
        return MIDPOINT_FORMULATION_VERSION


def midpoint_residual_diagnostics(blocks: CollocationResidualBlocks) -> MidpointResidualDiagnostics:
    """Compute independent maximum/RMS norms for every nonlinear block."""
    stages = np.asarray(blocks.stages, dtype=float)
    updates = np.asarray(blocks.updates, dtype=float)
    return MidpointResidualDiagnostics(
        stage_max=float(np.max(np.abs(stages))),
        stage_rms=float(np.sqrt(np.mean(stages * stages))),
        update_max=float(np.max(np.abs(updates))),
        update_rms=float(np.sqrt(np.mean(updates * updates))),
        phase_abs=abs(float(blocks.phase)),
    )


def correct_gauss_orbit(
    assembler: GaussCollocationAssembler,
    initial_unknowns: ArrayLike,
    *,
    tolerances: MidpointResidualTolerances | None = None,
    max_nfev: int = 1000,
    xtol: float = 1.0e-13,
    ftol: float = 1.0e-13,
    gtol: float = 1.0e-13,
) -> MidpointCorrectionResult:
    """Correct one fixed-parameter Gauss orbit with SciPy TRF and strict block gates.

    SciPy's termination flag is only one gate.  A result is accepted only when
    every independently recomputed residual block meets its explicit tolerance
    and the packed solution, residual, and positive physical period are finite.
    """
    if not isinstance(assembler, GaussCollocationAssembler):
        raise TypeError("assembler must be a GaussCollocationAssembler.")
    active_tolerances = tolerances or MidpointResidualTolerances()
    initial = np.asarray(initial_unknowns, dtype=float)
    assembler._variables(initial)
    solution = least_squares(
        assembler.residual,
        initial,
        jac=assembler.jacobian,
        method="trf",
        x_scale="jac",
        xtol=xtol,
        ftol=ftol,
        gtol=gtol,
        max_nfev=_positive_integer(max_nfev, "max_nfev"),
    )
    unknowns = np.asarray(solution.x, dtype=float).copy()
    residual = np.full(assembler.layout.residual_size, np.nan)
    diagnostics = MidpointResidualDiagnostics(*(np.nan for _ in range(5)))
    reasons: list[str] = []
    if not bool(solution.success):
        reasons.append("scipy_unsuccessful")

    shape_is_valid = unknowns.shape == (assembler.layout.unknown_size,)
    values_are_finite = bool(shape_is_valid and np.all(np.isfinite(unknowns)))
    physical_state_is_valid = False
    period_is_valid = False
    if not shape_is_valid:
        reasons.append("invalid_solution_shape")
    elif not values_are_finite:
        reasons.append("nonfinite_unknowns")
    else:
        variables = assembler.layout.unpack(unknowns)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            positive_states = np.exp(
                np.concatenate(
                    (
                        variables.endpoints[:, :2].reshape(-1),
                        variables.stages[:, :, :2].reshape(-1),
                    )
                )
            )
            period = np.exp(variables.log_period)
        physical_state_is_valid = bool(
            np.all(np.isfinite(positive_states)) and np.all(positive_states > 0.0)
        )
        period_is_valid = bool(np.isfinite(period) and period > 0.0)
        if not physical_state_is_valid:
            reasons.append("nonpositive_or_nonfinite_physical_state")
        if not period_is_valid:
            reasons.append("nonpositive_or_nonfinite_period")

    residual_is_available = bool(
        shape_is_valid and values_are_finite and physical_state_is_valid and period_is_valid
    )
    if residual_is_available:
        try:
            blocks = assembler.residual_blocks(unknowns)
            residual = assembler.layout.pack_residual(blocks)
            diagnostics = midpoint_residual_diagnostics(blocks)
        except (ArithmeticError, FloatingPointError, OverflowError, ValueError):
            residual = np.full(assembler.layout.residual_size, np.nan)
            diagnostics = MidpointResidualDiagnostics(*(np.nan for _ in range(5)))
            reasons.append("residual_evaluation_failed")
    else:
        reasons.append("residual_unavailable")
    if not np.all(np.isfinite(residual)):
        reasons.append("nonfinite_residual")

    block_checks = (
        ("stage_max_tolerance", diagnostics.stage_max, active_tolerances.stage_max),
        ("stage_rms_tolerance", diagnostics.stage_rms, active_tolerances.stage_rms),
        ("update_max_tolerance", diagnostics.update_max, active_tolerances.update_max),
        ("update_rms_tolerance", diagnostics.update_rms, active_tolerances.update_rms),
        ("phase_tolerance", diagnostics.phase_abs, active_tolerances.phase_abs),
    )
    for reason, value, threshold in block_checks:
        if not np.isfinite(value) or value > threshold:
            reasons.append(reason)
    packed_step_norm = (
        float(np.linalg.norm(unknowns - initial)) if shape_is_valid and values_are_finite else np.nan
    )
    unknowns.setflags(write=False)
    residual.setflags(write=False)
    return MidpointCorrectionResult(
        unknowns=unknowns,
        residual=residual,
        diagnostics=diagnostics,
        accepted=not reasons,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        scipy_success=bool(solution.success),
        scipy_status=int(solution.status),
        scipy_message=str(solution.message),
        scipy_cost=float(solution.cost),
        scipy_optimality=float(solution.optimality),
        function_evaluations=int(solution.nfev),
        jacobian_evaluations=(None if solution.njev is None else int(solution.njev)),
        packed_step_norm=packed_step_norm,
    )


def correct_midpoint_orbit(
    assembler: MidpointCollocationAssembler,
    initial_unknowns: ArrayLike,
    *,
    tolerances: MidpointResidualTolerances | None = None,
    max_nfev: int = 1000,
    xtol: float = 1.0e-13,
    ftol: float = 1.0e-13,
    gtol: float = 1.0e-13,
) -> MidpointCorrectionResult:
    """Compatibility wrapper for the established midpoint correction API."""
    if not isinstance(assembler, MidpointCollocationAssembler):
        raise TypeError("assembler must be a MidpointCollocationAssembler.")
    return correct_gauss_orbit(
        assembler,
        initial_unknowns,
        tolerances=tolerances,
        max_nfev=max_nfev,
        xtol=xtol,
        ftol=ftol,
        gtol=gtol,
    )
