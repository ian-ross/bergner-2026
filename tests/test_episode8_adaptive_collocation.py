from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    DEFECT_ACCEPTANCE_TOLERANCE,
    MONITOR_SUBCELLS_PER_ELEMENT,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    PeriodicHermiteSeed,
    apply_global_beta_r_movement,
    bisect_marked_elements,
    build_composite_r_monitor,
    decide_adaptation_cycle,
    gauss_legendre_rule,
    mark_h_refinement,
    normalize_monitor_density,
    restart_plan,
    transfer_orbit_phase_and_tangent,
)
from bergner_spichtinger_2026.constants import Environment

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "episodes/008-figure5-periodic-orbit-continuation/outputs/bootstrap_seed.json"


def fixture(mesh: FixedMesh | None = None):
    mapping = json.loads(SEED_PATH.read_text())
    parameters = mapping["canonical_parameters"]
    env = Environment(
        T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
        N_a=parameters["N_a"], Δz=parameters["Delta_z"], include_evaporation=False,
    )
    seed = PeriodicHermiteSeed.from_json(SEED_PATH)
    active_mesh = mesh or FixedMesh.uniform(6)
    rule = gauss_legendre_rule(3)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    reference = FrozenPhaseReference.from_evaluator(active_mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling)
    assembler = GaussCollocationAssembler(active_mesh, env, reference, rule)
    return assembler, assembler.reference_unknowns(seed.evaluate, seed.log_period)


def test_density_normalization_uses_max_average_winsorize_average_order():
    weights = np.full(4, 0.25)
    raw = np.array([0.0, 1.0, 2.0, 1000.0])
    density = normalize_monitor_density("D", raw, weights)
    max_rescaled = raw / raw.max()
    first = np.sum(weights * max_rescaled)
    winsorized = np.minimum(max_rescaled / first, 20.0)
    second = np.sum(weights * winsorized)
    np.testing.assert_allclose(density.normalized, winsorized / second)
    assert np.sum(weights * density.normalized) == pytest.approx(1.0)
    zero = normalize_monitor_density("zero", np.zeros(4), weights)
    np.testing.assert_array_equal(zero.normalized, np.zeros(4))
    with pytest.raises(ValueError, match="negative"):
        normalize_monitor_density("bad", [1.0, -1.0], [0.5, 0.5])


def test_composite_monitor_samples_16_subcells_and_inverts_positive_cdf():
    assembler, unknowns = fixture(FixedMesh(np.array([0.0, 0.1, 0.4, 1.0])))
    monitor = build_composite_r_monitor(assembler, unknowns)
    assert monitor.version == "composite-r-monitor-v1"
    assert monitor.values.shape == (3 * MONITOR_SUBCELLS_PER_ELEMENT,)
    assert monitor.subcell_widths.shape == monitor.values.shape
    assert all(d.normalized.shape == monitor.values.shape for d in monitor.densities)
    assert np.all(monitor.values >= 0.20)
    assert monitor.total_mass > 0.0
    assert np.all(np.diff(monitor.cumulative_upper) > 0.0)
    np.testing.assert_allclose(monitor.target_boundaries[[0, -1]], [0.0, 1.0])
    assert np.all(np.diff(monitor.target_boundaries) > 0.0)


def test_h_marking_bulk_halfmax_growth_cap_and_bisection_are_deterministic():
    eta = np.array([0.01, 0.02, 0.50, 0.49, 0.03, 0.25])
    marking = mark_h_refinement(eta, max_interval_count=8)
    # Growth cap allows only floor(0.5*6)=3 splits, additionally capped by N<=8 to two splits.
    assert marking.growth_limit == 2
    assert marking.marked_elements == (2, 3)
    assert marking.uncapped_marked_elements[:3] == (2, 3, 5)
    mesh = FixedMesh.uniform(6)
    bisected = bisect_marked_elements(mesh, marking.marked_elements)
    assert bisected.interval_count == 8
    np.testing.assert_allclose(bisected.boundaries[[3, 5]], [5 / 12, 7 / 12])


def test_global_beta_movement_retries_simultaneously_and_stalls_without_projection():
    old = FixedMesh(np.array([0.0, 0.25, 0.5, 0.75, 1.0]))
    target = np.array([0.0, 0.03, 0.97, 0.98, 1.0])
    moved = apply_global_beta_r_movement(old, target)
    assert moved.accepted
    assert moved.beta < 0.5
    assert np.all(np.diff(moved.new_boundaries) > 0.0)
    # A mesh that already violates cyclic adjacent-ratio bounds cannot be rescued by retaining endpoints.
    bad_old = FixedMesh(np.array([0.0, 0.001, 0.5, 0.75, 1.0]))
    bad_target = np.array([0.0, 0.2, 0.4, 0.8, 1.0])
    stalled = apply_global_beta_r_movement(bad_old, bad_target)
    assert stalled.stalled
    assert len(stalled.attempted_betas) == 20
    np.testing.assert_array_equal(stalled.new_boundaries, bad_old.boundaries)


def test_controller_distinguishes_stop_hr_purer_forced_caps_and_unresolved():
    assert decide_adaptation_cycle(
        interval_count=32, cycle_index=0, defect_maximum=1e-5,
        period_relative_change=5e-4, weighted_orbit_change=5e-4,
        consecutive_pure_r_cycles=0, pure_r_defect_reduction=None,
    ).action == "stop_converged"
    assert decide_adaptation_cycle(
        interval_count=32, cycle_index=0, defect_maximum=DEFECT_ACCEPTANCE_TOLERANCE,
        period_relative_change=5e-4, weighted_orbit_change=5e-4,
        consecutive_pure_r_cycles=0, pure_r_defect_reduction=None,
    ).action == "ordinary_h_r"
    assert decide_adaptation_cycle(
        interval_count=32, cycle_index=0, defect_maximum=1e-5,
        period_relative_change=2e-3, weighted_orbit_change=5e-4,
        consecutive_pure_r_cycles=2, pure_r_defect_reduction=0.5,
    ).action == "pure_r"
    forced = decide_adaptation_cycle(
        interval_count=32, cycle_index=0, defect_maximum=1e-5,
        period_relative_change=2e-3, weighted_orbit_change=5e-4,
        consecutive_pure_r_cycles=3, pure_r_defect_reduction=0.1, maximum_defect_element=7,
    )
    assert forced.action == "forced_single_split_h_r" and forced.force_split_element == 7
    assert decide_adaptation_cycle(
        interval_count=256, cycle_index=3, defect_maximum=1e-3,
        period_relative_change=None, weighted_orbit_change=None,
        consecutive_pure_r_cycles=0, pure_r_defect_reduction=None,
    ).action == "mesh_cap_escalation"
    unresolved = decide_adaptation_cycle(
        interval_count=512, cycle_index=5, defect_maximum=1e-3,
        period_relative_change=None, weighted_orbit_change=None,
        consecutive_pure_r_cycles=0, pure_r_defect_reduction=None, soft_cap_escalated=True,
    )
    assert unresolved.terminal_status == "resolution_unresolved"


def test_transfer_solution_phase_reference_tangent_and_retry_plans_are_versioned():
    assembler, unknowns = fixture(FixedMesh.uniform(4))
    tangent = np.cos(np.arange(unknowns.size))
    destination_mesh = FixedMesh.uniform(7)
    destination_rule = gauss_legendre_rule(3)
    transferred, reference, transferred_tangent = transfer_orbit_phase_and_tangent(
        assembler, unknowns, tangent, destination_mesh, destination_rule
    )
    assert transferred.shape == transferred_tangent.shape == (3 * 7 * (3 + 1) + 1,)
    assert reference.mesh.interval_count == 7
    assert reference.phase_energy > 0.0
    assert transferred[-1] == pytest.approx(unknowns[-1])
    assert transferred_tangent[-1] == pytest.approx(tangent[-1], rel=2e-9, abs=2e-9)

    hr = restart_plan(remesh_kind="h+r")
    pure = restart_plan(remesh_kind="pure-r")
    tangent_failure = restart_plan(remesh_kind="h+r", tangent_only_failure=True)
    assert [attempt.name for attempt in hr.attempts] == [
        "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect"
    ]
    assert pure.attempts[0].name == "pure_r_transfer_correct"
    assert tangent_failure.attempts[0].rebootstrap_tangent
