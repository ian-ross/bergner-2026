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

from .collocation_coefficients import CollocationRule, gauss_legendre_rule
from .constants import Environment
from .core import Coefficients, coefficients, vector_field
from .residuals import physical_state_from_log_coordinates
from .stability import physical_jacobian


ArrayLike = Iterable[float] | np.ndarray
STATE_DIMENSION = 3
MIDPOINT_FORMULATION_VERSION = "explicit-stage-midpoint-v1"
JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE = 1.0e-6
MIDPOINT_SOLVER_VERSION = "scipy-trf-block-acceptance-v1"


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


class MidpointCollocationAssembler:
    """Assemble the fixed-parameter explicit-stage midpoint base system."""

    def __init__(
        self,
        mesh: FixedMesh,
        env: Environment,
        phase_reference: FrozenPhaseReference,
        *,
        coeff: Coefficients | None = None,
    ) -> None:
        if env.include_evaporation:
            raise ValueError("midpoint collocation requires the smooth no-evaporation model.")
        if not isinstance(mesh, FixedMesh):
            raise TypeError("mesh must be a FixedMesh.")
        if not isinstance(phase_reference, FrozenPhaseReference):
            raise TypeError("phase_reference must be a FrozenPhaseReference.")
        if not np.array_equal(mesh.boundaries, phase_reference.mesh.boundaries):
            raise ValueError("phase-reference mesh does not match the assembler mesh.")
        rule = gauss_legendre_rule(1)
        if phase_reference.stage_values.shape[1] != rule.stage_count:
            raise ValueError("midpoint phase reference must contain exactly one stage per interval.")
        if not np.array_equal(phase_reference.collocation_nodes, np.asarray(rule.nodes)):
            raise ValueError("phase-reference nodes do not match the midpoint rule.")
        if not np.array_equal(phase_reference.quadrature_weights, np.asarray(rule.quadrature_weights)):
            raise ValueError("phase-reference quadrature does not match the midpoint rule.")
        self.mesh = mesh
        self.env = env
        self.phase_reference = phase_reference
        self.rule = rule
        self.layout = OrbitLayout(mesh.interval_count, rule.stage_count, STATE_DIMENSION)
        self.coeff = coeff or coefficients(env)

    @property
    def formulation_version(self) -> str:
        return MIDPOINT_FORMULATION_VERSION

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
            state = stages[interval, 0]
            values[interval, 0] = transformed_vector_field(state, self.env, self.coeff)
            if jacobians is not None:
                jacobians[interval, 0] = transformed_vector_field_jacobian(state, self.env, self.coeff)
        return values, jacobians

    def residual_blocks(self, unknowns: ArrayLike) -> CollocationResidualBlocks:
        variables = self._variables(unknowns)
        period = exp(variables.log_period)
        field, _ = self._stage_model_values(variables.stages, with_jacobian=False)
        stages = np.empty_like(variables.stages)
        updates = np.empty_like(variables.endpoints)
        scaling = self.state_scaling
        stage_coefficient = self.rule.stage_coefficients[0][0]
        update_weight = self.rule.quadrature_weights[0]
        for interval, width in enumerate(self.mesh.widths):
            endpoint = variables.endpoints[interval]
            next_endpoint = variables.endpoints[(interval + 1) % self.layout.interval_count]
            stage_field = field[interval, 0]
            stages[interval, 0] = scaling * (
                variables.stages[interval, 0]
                - endpoint
                - width * period * stage_coefficient * stage_field
            )
            updates[interval] = scaling * (
                next_endpoint - endpoint - width * period * update_weight * stage_field
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

        Endpoint and midpoint-stage representations each receive half of the
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
        stage_coefficient = self.rule.stage_coefficients[0][0]
        update_weight = self.rule.quadrature_weights[0]
        identity = np.eye(STATE_DIMENSION)

        for interval, width in enumerate(self.mesh.widths):
            stage_row = self.layout.stage_row_slice(interval).start
            update_row = self.layout.update_row_slice(interval).start
            endpoint_column = self.layout.endpoint_slice(interval).start
            next_endpoint_column = self.layout.endpoint_slice(
                (interval + 1) % self.layout.interval_count
            ).start
            stage_column = self.layout.stage_slice(interval).start
            stage_field = field[interval, 0]
            local_jacobian = field_jacobian[interval, 0]

            self._append_diagonal(rows, columns, data, stage_row, endpoint_column, -scaling)
            self._append_dense(
                rows,
                columns,
                data,
                stage_row,
                stage_column,
                row_scaling @ (identity - width * period * stage_coefficient * local_jacobian),
            )
            self._append_column(
                rows,
                columns,
                data,
                stage_row,
                self.layout.log_period_index,
                scaling * (-width * period * stage_coefficient * stage_field),
            )

            self._append_diagonal(rows, columns, data, update_row, endpoint_column, -scaling)
            self._append_diagonal(rows, columns, data, update_row, next_endpoint_column, scaling)
            self._append_dense(
                rows,
                columns,
                data,
                update_row,
                stage_column,
                row_scaling @ (-width * period * update_weight * local_jacobian),
            )
            self._append_column(
                rows,
                columns,
                data,
                update_row,
                self.layout.log_period_index,
                scaling * (-width * period * update_weight * stage_field),
            )

            phase_gradient = (
                width
                * update_weight
                * scaling**2
                * self.phase_reference.stage_derivatives[interval, 0]
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

        result = csr_matrix(
            (data, (rows, columns)),
            shape=(self.layout.residual_size, self.layout.unknown_size),
        )
        result.sum_duplicates()
        result.sort_indices()
        return result


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
    """Correct one fixed-parameter orbit with SciPy TRF and strict block gates.

    SciPy's termination flag is only one gate.  A result is accepted only when
    every independently recomputed residual block meets its explicit tolerance
    and the packed solution, residual, and positive physical period are finite.
    """
    if not isinstance(assembler, MidpointCollocationAssembler):
        raise TypeError("assembler must be a MidpointCollocationAssembler.")
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
