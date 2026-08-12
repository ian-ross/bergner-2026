from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from bergner_spichtinger_2026.collocation_coefficients import gauss_legendre_rule
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.periodic_orbits import (
    JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
    MIDPOINT_FORMULATION_VERSION,
    CollocationResidualBlocks,
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    OrbitLayout,
    transformed_vector_field,
    transformed_vector_field_jacobian,
)
from bergner_spichtinger_2026.periodic_seed import PeriodicHermiteSeed


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation/outputs/bootstrap_seed.json"


def canonical_seed_and_environment() -> tuple[PeriodicHermiteSeed, Environment]:
    mapping = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    parameters = mapping["canonical_parameters"]
    environment = Environment(
        T=parameters["T"],
        p=parameters["p"],
        w=parameters["w"],
        F=parameters["F"],
        N_a=parameters["N_a"],
        Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )
    return PeriodicHermiteSeed.from_json(SEED_PATH), environment


def midpoint_fixture(
    mesh: FixedMesh | None = None,
) -> tuple[PeriodicHermiteSeed, MidpointCollocationAssembler, np.ndarray]:
    seed, environment = canonical_seed_and_environment()
    active_mesh = mesh or FixedMesh.uniform(8)
    rule = gauss_legendre_rule(1)
    ranges = np.ptp(seed.transformed_state[:-1], axis=0)
    scaling = 1.0 / ranges
    reference = FrozenPhaseReference.from_evaluator(
        active_mesh,
        rule,
        seed.evaluate,
        seed.derivative,
        state_scaling=scaling,
    )
    assembler = MidpointCollocationAssembler(active_mesh, environment, reference)
    endpoints = seed.evaluate(active_mesh.boundaries[:-1])
    stages = seed.evaluate(active_mesh.stage_phases(rule.nodes).reshape(-1)).reshape(
        active_mesh.interval_count, 1, 3
    )
    unknowns = assembler.layout.pack(endpoints, stages, seed.log_period)
    return seed, assembler, unknowns


def deterministic_nonsolution(unknowns: np.ndarray) -> np.ndarray:
    result = unknowns.copy()
    direction = np.sin(np.arange(result.size, dtype=float) + 0.375)
    result[:-1] += 2.0e-3 * direction[:-1]
    result[-1] += 3.0e-4 * direction[-1]
    return result


def test_orbit_layout_owns_indices_and_round_trips_without_a_terminal_endpoint():
    layout = OrbitLayout(interval_count=8, stage_count=1)

    assert layout.endpoint_size == 24
    assert layout.stage_size == 24
    assert layout.endpoint_slice(0) == slice(0, 3)
    assert layout.endpoint_slice(7) == slice(21, 24)
    assert layout.stage_slice(0) == slice(24, 27)
    assert layout.stage_slice(7) == slice(45, 48)
    assert layout.log_period_index == 48
    assert layout.unknown_size == 49
    assert layout.stage_row_slice(7) == slice(21, 24)
    assert layout.update_row_slice(0) == slice(24, 27)
    assert layout.update_row_slice(7) == slice(45, 48)
    assert layout.phase_row == 48
    assert layout.residual_size == layout.unknown_size

    endpoints = np.arange(24, dtype=float).reshape(8, 3)
    stages = (100.0 + np.arange(24, dtype=float)).reshape(8, 1, 3)
    packed = layout.pack(endpoints, stages, np.log(2000.0))
    unpacked = layout.unpack(packed)
    np.testing.assert_array_equal(unpacked.endpoints, endpoints)
    np.testing.assert_array_equal(unpacked.stages, stages)
    assert unpacked.log_period == np.log(2000.0)
    assert unpacked.endpoints.shape[0] == 8

    two_stage_layout = OrbitLayout(interval_count=3, stage_count=2)
    assert two_stage_layout.endpoint_size == 9
    assert two_stage_layout.stage_slice(2, 1) == slice(24, 27)
    assert two_stage_layout.unknown_size == 28
    with pytest.raises(IndexError, match="interval"):
        layout.endpoint_slice(8)
    with pytest.raises(ValueError, match="endpoints"):
        layout.pack(np.zeros((9, 3)), stages, 0.0)


def test_fixed_mesh_and_phase_reference_support_arbitrary_nonuniform_intervals():
    seed, _ = canonical_seed_and_environment()
    mesh = FixedMesh(np.array([0.0, 0.04, 0.2, 0.55, 1.0]))
    rule = gauss_legendre_rule(1)
    reference = FrozenPhaseReference.from_evaluator(
        mesh,
        rule,
        seed.evaluate,
        seed.derivative,
    )

    np.testing.assert_allclose(mesh.widths, [0.04, 0.16, 0.35, 0.45])
    np.testing.assert_allclose(
        mesh.stage_phases(rule.nodes).ravel(),
        [0.02, 0.12, 0.375, 0.775],
    )
    assert reference.stage_values.shape == (4, 1, 3)
    assert reference.stage_derivatives.shape == (4, 1, 3)
    assert reference.phase_energy > 0.0
    with pytest.raises(ValueError, match="read-only"):
        reference.stage_values[0, 0, 0] += 1.0
    with pytest.raises(ValueError, match="strictly increasing"):
        FixedMesh(np.array([0.0, 0.5, 0.5, 1.0]))


def test_midpoint_assembler_rejects_a_reference_sampled_at_another_node():
    seed, environment = canonical_seed_and_environment()
    mesh = FixedMesh.uniform(3)
    off_midpoint_rule = replace(gauss_legendre_rule(1), nodes=(0.25,))
    reference = FrozenPhaseReference.from_evaluator(
        mesh,
        off_midpoint_rule,
        seed.evaluate,
        seed.derivative,
    )

    with pytest.raises(ValueError, match="nodes do not match"):
        MidpointCollocationAssembler(mesh, environment, reference)


def test_transformed_model_jacobian_matches_centered_finite_differences():
    seed, environment = canonical_seed_and_environment()
    state = seed.evaluate(0.137)
    analytic = transformed_vector_field_jacobian(state, environment)
    finite_difference = np.empty((3, 3))
    epsilon = 1.0e-6
    for column in range(3):
        offset = np.zeros(3)
        offset[column] = epsilon
        finite_difference[:, column] = (
            transformed_vector_field(state + offset, environment)
            - transformed_vector_field(state - offset, environment)
        ) / (2.0 * epsilon)

    np.testing.assert_allclose(analytic, finite_difference, rtol=2.0e-7, atol=2.0e-10)


def test_n8_midpoint_residual_blocks_and_phase_normalization_are_explicit():
    seed, assembler, unknowns = midpoint_fixture()
    layout = assembler.layout
    variables = layout.unpack(unknowns)
    blocks = assembler.residual_blocks(unknowns)
    period = np.exp(variables.log_period)
    expected_stages = np.empty_like(blocks.stages)
    expected_updates = np.empty_like(blocks.updates)

    for interval, width in enumerate(assembler.mesh.widths):
        field = transformed_vector_field(variables.stages[interval, 0], assembler.env)
        expected_stages[interval, 0] = assembler.state_scaling * (
            variables.stages[interval, 0]
            - variables.endpoints[interval]
            - 0.5 * width * period * field
        )
        expected_updates[interval] = assembler.state_scaling * (
            variables.endpoints[(interval + 1) % 8]
            - variables.endpoints[interval]
            - width * period * field
        )

    np.testing.assert_allclose(blocks.stages, expected_stages, rtol=2.0e-14, atol=2.0e-14)
    np.testing.assert_allclose(blocks.updates, expected_updates, rtol=2.0e-14, atol=2.0e-14)
    assert blocks.phase == 0.0
    np.testing.assert_array_equal(
        layout.unpack_residual(assembler.residual(unknowns)).stages,
        blocks.stages,
    )

    shifted_stages = assembler.phase_reference.stage_values + 0.0125 * assembler.phase_reference.stage_derivatives
    shifted = layout.pack(variables.endpoints, shifted_stages, variables.log_period)
    assert assembler.residual_blocks(shifted).phase == pytest.approx(0.0125, rel=2.0e-15, abs=2.0e-15)
    assert assembler.formulation_version == MIDPOINT_FORMULATION_VERSION
    assert seed.log_period == variables.log_period


def test_n8_sparse_jacobian_has_expected_blocks_wraparound_and_phase_row():
    _, assembler, seed_unknowns = midpoint_fixture()
    unknowns = deterministic_nonsolution(seed_unknowns)
    layout = assembler.layout
    jacobian = assembler.jacobian(unknowns)

    assert isinstance(jacobian, csr_matrix)
    assert jacobian.shape == (49, 49)
    assert jacobian.has_sorted_indices
    assert jacobian.nnz == 8 * (15 + 18 + 3)

    first_stage_columns = set(jacobian[layout.stage_row_slice(0)].nonzero()[1])
    assert first_stage_columns == (
        set(range(0, 3))
        | set(range(24, 27))
        | {layout.log_period_index}
    )
    last_update_columns = set(jacobian[layout.update_row_slice(7)].nonzero()[1])
    assert last_update_columns == (
        set(range(21, 24))
        | set(range(0, 3))
        | set(range(45, 48))
        | {layout.log_period_index}
    )
    phase_columns = set(jacobian.getrow(layout.phase_row).nonzero()[1])
    assert phase_columns == set(range(layout.endpoint_size, layout.log_period_index))
    assert jacobian[layout.phase_row, layout.log_period_index] == 0.0


def test_deterministic_nonsolution_exercises_every_residual_block():
    _, assembler, seed_unknowns = midpoint_fixture()
    unknowns = deterministic_nonsolution(seed_unknowns)
    first = assembler.residual_blocks(unknowns)
    second = assembler.residual_blocks(unknowns.copy())

    np.testing.assert_array_equal(first.stages, second.stages)
    np.testing.assert_array_equal(first.updates, second.updates)
    assert first.phase == second.phase
    assert np.all(np.linalg.norm(first.stages[:, 0], axis=1) > 0.0)
    assert np.all(np.linalg.norm(first.updates, axis=1) > 0.0)
    assert abs(first.phase) > 0.0


def directional_error(
    assembler: MidpointCollocationAssembler,
    unknowns: np.ndarray,
    direction: np.ndarray,
    *,
    epsilon: float = 2.0e-7,
) -> float:
    normalized = direction / np.linalg.norm(direction)
    analytic = assembler.jacobian(unknowns) @ normalized
    finite_difference = (
        assembler.residual(unknowns + epsilon * normalized)
        - assembler.residual(unknowns - epsilon * normalized)
    ) / (2.0 * epsilon)
    return float(np.linalg.norm(analytic - finite_difference) / max(1.0, np.linalg.norm(analytic)))


def test_centered_directional_checks_cover_state_log_period_and_phase_row():
    _, assembler, seed_unknowns = midpoint_fixture()
    unknowns = deterministic_nonsolution(seed_unknowns)
    layout = assembler.layout
    directions = []

    state_direction = np.zeros(layout.unknown_size)
    state_direction[: layout.log_period_index] = np.cos(
        np.arange(layout.log_period_index, dtype=float) + 0.125
    )
    directions.append(state_direction)

    log_period_direction = np.zeros(layout.unknown_size)
    log_period_direction[layout.log_period_index] = 1.0
    directions.append(log_period_direction)

    mixed_direction = np.sin(np.arange(layout.unknown_size, dtype=float) + 0.75)
    directions.append(mixed_direction)

    errors = [directional_error(assembler, unknowns, direction) for direction in directions]
    assert JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE == 1.0e-6
    assert max(errors) <= JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE


def test_nonuniform_mesh_jacobian_passes_the_same_versioned_directional_check():
    mesh = FixedMesh(np.array([0.0, 0.03, 0.11, 0.37, 0.68, 1.0]))
    _, assembler, seed_unknowns = midpoint_fixture(mesh)
    unknowns = deterministic_nonsolution(seed_unknowns)
    direction = np.cos(np.arange(unknowns.size, dtype=float) + 0.42)

    assert directional_error(assembler, unknowns, direction) <= JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE


def test_residual_pack_validates_block_shapes():
    layout = OrbitLayout(2)
    with pytest.raises(ValueError, match="stage residuals"):
        layout.pack_residual(
            CollocationResidualBlocks(
                stages=np.zeros((2, 3)),
                updates=np.zeros((2, 3)),
                phase=0.0,
            )
        )
