from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    DEFECT_RECURRENCE_BIN_COUNT,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    MidpointCollocationAssembler,
    PeriodicHermiteSeed,
    gauss_legendre_rule,
)
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.periodic_orbits import transformed_vector_field


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "episodes/008-figure5-periodic-orbit-continuation/outputs/bootstrap_seed.json"


def fixture(stage_count: int, mesh: FixedMesh | None = None):
    mapping = json.loads(SEED_PATH.read_text())
    parameters = mapping["canonical_parameters"]
    environment = Environment(
        T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
        N_a=parameters["N_a"], Δz=parameters["Delta_z"], include_evaporation=False,
    )
    seed = PeriodicHermiteSeed.from_json(SEED_PATH)
    active_mesh = mesh or FixedMesh.uniform(5)
    rule = gauss_legendre_rule(stage_count)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    reference = FrozenPhaseReference.from_evaluator(
        active_mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling
    )
    assembler = GaussCollocationAssembler(active_mesh, environment, reference, rule)
    return seed, assembler, assembler.reference_unknowns(seed.evaluate, seed.log_period)


@pytest.mark.parametrize("stage_count", [1, 2, 3])
def test_generic_layout_residual_and_jacobian_use_every_gauss_stage(stage_count):
    _, assembler, unknowns = fixture(stage_count)
    layout = assembler.layout
    assert layout.unknown_size == 3 * layout.interval_count * (stage_count + 1) + 1
    variables = layout.unpack(unknowns)
    np.testing.assert_array_equal(layout.unpack(layout.pack(
        variables.endpoints, variables.stages, variables.log_period
    )).stages, variables.stages)

    blocks = assembler.residual_blocks(unknowns)
    period = np.exp(variables.log_period)
    interval = 1
    width = assembler.mesh.widths[interval]
    fields = np.array([
        transformed_vector_field(state, assembler.env, assembler.coeff)
        for state in variables.stages[interval]
    ])
    for stage in range(stage_count):
        expected = assembler.state_scaling * (
            variables.stages[interval, stage] - variables.endpoints[interval]
            - width * period * np.einsum(
                "k,kq->q", np.asarray(assembler.rule.stage_coefficients)[stage], fields
            )
        )
        np.testing.assert_allclose(blocks.stages[interval, stage], expected, rtol=2e-14, atol=2e-14)

    direction = np.sin(np.arange(unknowns.size) + 0.37)
    direction /= np.linalg.norm(direction)
    epsilon = 2e-7
    analytic = assembler.jacobian(unknowns) @ direction
    finite = (assembler.residual(unknowns + epsilon * direction)
              - assembler.residual(unknowns - epsilon * direction)) / (2 * epsilon)
    assert np.linalg.norm(analytic - finite) / max(1, np.linalg.norm(analytic)) <= 1e-6
    phase_columns = set(assembler.jacobian(unknowns).getrow(layout.phase_row).nonzero()[1])
    assert phase_columns == set(range(layout.endpoint_size, layout.log_period_index))


def test_polynomial_evaluation_and_cross_rule_transfer_are_rule_driven():
    _, source, unknowns = fixture(3, FixedMesh(np.array([0.0, 0.07, 0.31, 0.73, 1.0])))
    variables = source.layout.unpack(unknowns)
    evaluate = source.polynomial_evaluator(unknowns)
    np.testing.assert_allclose(evaluate(source.mesh.boundaries[:-1]), variables.endpoints, atol=2e-15)
    destination_mesh = FixedMesh.uniform(9)
    destination_rule = gauss_legendre_rule(2)
    packed = source.transfer_unknowns(unknowns, destination_mesh, destination_rule)
    destination_layout_stages = packed[3 * destination_mesh.interval_count:-1].reshape(9, 2, 3)
    np.testing.assert_allclose(
        destination_layout_stages,
        evaluate(destination_mesh.stage_phases(destination_rule.nodes).reshape(-1)).reshape(9, 2, 3),
    )
    transferred_reference = source.transferred_phase_reference(
        unknowns, destination_mesh, destination_rule
    )
    assert transferred_reference.stage_values.shape == (9, 2, 3)
    assert transferred_reference.phase_energy > 0


def test_weighted_comparison_is_stage_count_independent_for_identical_polynomial():
    seed, source, unknowns = fixture(1, FixedMesh.uniform(8))
    destination_mesh = FixedMesh.uniform(8)
    destination_rule = gauss_legendre_rule(3)
    transferred = source.transfer_unknowns(unknowns, destination_mesh, destination_rule)
    reference = FrozenPhaseReference.from_evaluator(
        destination_mesh, destination_rule, seed.evaluate, seed.derivative,
        state_scaling=source.state_scaling,
    )
    destination = GaussCollocationAssembler(destination_mesh, source.env, reference, destination_rule)
    comparison = destination.compare_with_collocation(transferred, source, unknowns)
    assert comparison.distance < 1e-8


def test_reference_comparison_recovers_a_known_nonzero_phase_shift():
    seed, assembler, unknowns = fixture(3, FixedMesh.uniform(16))
    shift = 0.137
    shifted = assembler.reference_unknowns(seed.evaluate, seed.log_period, phase_shift=shift)
    comparison = assembler.compare_with_reference(
        shifted, seed.evaluate, seed.log_period, align_phase=True
    )
    assert comparison.phase_shift == pytest.approx(shift, abs=2e-7)
    assert comparison.distance < 2e-7


def test_independent_defect_reports_both_grids_escalation_and_periodic_bin(monkeypatch):
    _, assembler, unknowns = fixture(2)
    original = assembler._defect_grid

    def controlled(value, name, nodes):
        result = original(value, name, nodes)
        if name == "next_higher_gauss":
            relative = np.full_like(result.relative_defects, 2e-4)
        elif name == "staggered_dyadic":
            relative = np.full_like(result.relative_defects, 2e-5)
        else:
            relative = np.full_like(result.relative_defects, 3e-4)
        relative.setflags(write=False)
        return type(result)(name, result.local_nodes, relative, float(relative.max()), 0,
                            float(result.local_nodes[0]), 0.999999)

    monkeypatch.setattr(assembler, "_defect_grid", controlled)
    defect = assembler.independent_defect(unknowns)
    assert defect.next_gauss.local_nodes.size == 3
    np.testing.assert_array_equal(defect.staggered_dyadic.local_nodes, [.125, .375, .625, .875])
    assert defect.probe_16 is not None and defect.probe_16.local_nodes.size == 16
    assert defect.materially_disagreeing_elements == tuple(range(5))
    assert np.all(defect.probe_admitted)
    np.testing.assert_allclose(defect.admitted_probe_element_maxima, 3e-4)
    assert 0 <= defect.argmax_bin < DEFECT_RECURRENCE_BIN_COUNT
    assert defect.endpoint_left.shape == defect.endpoint_right.shape == (5,)
    assert defect.derivative_jumps.shape == (5,)


def test_unflagged_probe_maximum_cannot_control_combined_argmax(monkeypatch):
    _, assembler, unknowns = fixture(2)
    original = assembler._defect_grid

    def controlled(value, name, nodes):
        result = original(value, name, nodes)
        relative = np.full_like(result.relative_defects, 2e-5)
        if name == "next_higher_gauss":
            relative[0] = 2e-4
        elif name == "staggered_dyadic":
            relative[0] = 2e-5
        else:
            relative[0] = 3e-4
            relative[1] = 9e-1  # unrestricted maximum on an unflagged element
        flat = int(np.argmax(relative))
        interval, node = np.unravel_index(flat, relative.shape)
        phase = assembler.mesh.boundaries[interval] + assembler.mesh.widths[interval] * result.local_nodes[node]
        relative.setflags(write=False)
        return type(result)(name, result.local_nodes, relative, float(relative[interval, node]),
                            int(interval), float(result.local_nodes[node]), float(phase))

    monkeypatch.setattr(assembler, "_defect_grid", controlled)
    defect = assembler.independent_defect(unknowns)
    assert defect.materially_disagreeing_elements == (0,)
    assert defect.maximum == pytest.approx(3e-4)
    assert defect.argmax_phase < assembler.mesh.boundaries[1]
    assert defect.probe_admitted.tolist() == [True, False, False, False, False]
    assert defect.admitted_probe_element_maxima[1] == 0.0


def test_midpoint_wrapper_remains_numerically_identical_to_generic_one_stage():
    _, generic, unknowns = fixture(1)
    midpoint = MidpointCollocationAssembler(generic.mesh, generic.env, generic.phase_reference)
    np.testing.assert_array_equal(midpoint.residual(unknowns), generic.residual(unknowns))
    np.testing.assert_array_equal(midpoint.jacobian(unknowns).toarray(), generic.jacobian(unknowns).toarray())
