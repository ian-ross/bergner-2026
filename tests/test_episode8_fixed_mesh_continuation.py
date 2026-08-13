from __future__ import annotations

import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    FixedMesh,
    FixedMeshContinuationMetric,
    FixedMeshOrbitFamily,
    FixedTemperatureRhoPath,
    FrozenPhaseReference,
    HopfLocusCoordinates,
    OrbitContinuationPoint,
    PeriodicHermiteSeed,
    PseudoArclengthProblem,
    SpineTemperaturePath,
    bootstrap_branch,
    controlled_phase_reference_restart,
    gauss_legendre_rule,
    sha256_file,
    transformed_vector_field,
    transformed_vector_field_environment_derivatives,
)
import bergner_spichtinger_2026.periodic_continuation as periodic_continuation
from bergner_spichtinger_2026.constants import Environment


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SEED_PATH = EPISODE_ROOT / "outputs/bootstrap_seed.json"
MIDPOINT_VECTORS = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_vectors.npz"
RESULTS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_continuation_results.json"
VECTORS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_continuation_vectors.npz"
HOPF_PATH = (
    REPO_ROOT
    / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
)
SCRIPT_DIR = EPISODE_ROOT / "scripts"


def _base_environment() -> Environment:
    parameters = json.loads(SEED_PATH.read_text())["canonical_parameters"]
    return Environment(
        T=parameters["T"],
        p=parameters["p"],
        w=parameters["w"],
        F=parameters["F"],
        N_a=parameters["N_a"],
        Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )


def _family(interval_count: int = 64):
    seed = PeriodicHermiteSeed.from_json(SEED_PATH, verify_upstream_root=REPO_ROOT)
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_PATH)
    mesh = FixedMesh.uniform(interval_count)
    rule = gauss_legendre_rule(1)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    reference = FrozenPhaseReference.from_evaluator(
        mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling
    )
    path = FixedTemperatureRhoPath(locus, _base_environment(), 225.0)
    family = FixedMeshOrbitFamily(mesh, reference, path, "test-phase-reference")
    metric = FixedMeshContinuationMetric.from_family(family)
    return seed, locus, family, metric


def test_hopf_paths_reproduce_exact_normalized_coordinates_and_chain_rules():
    _, locus, _, _ = _family(8)
    assert locus.spine_log_w(225.0) == pytest.approx(-1.934045042863362)
    assert np.exp(locus.spine_log_w(225.0)) == pytest.approx(0.1445622536840862)
    assert locus.spine_log_w(210.0) == pytest.approx(-2.9324347616541555)
    assert locus.temperature_hat(225.0) == pytest.approx(0.4)
    assert locus.temperature_hat(210.0) == pytest.approx(-0.2)
    slice_path = FixedTemperatureRhoPath(locus, _base_environment(), 210.0)
    lower, upper = locus.bounds(210.0)
    assert slice_path.physical_derivative_factors(0.3) == pytest.approx((0.0, 0.5 * (upper - lower)))
    spine_path = SpineTemperaturePath(locus, _base_environment())
    dt, dlogw = spine_path.physical_derivative_factors(locus.temperature_hat(225.0))
    assert dt == 25.0
    h = 1.0e-5
    finite_difference = (
        spine_path.coordinates(0.4 + h).log_w - spine_path.coordinates(0.4 - h).log_w
    ) / (2.0 * h)
    assert dlogw == pytest.approx(finite_difference, rel=5.0e-8)


@pytest.mark.parametrize(
    "temperature,w,state",
    [
        (225.0, 0.1, np.array([12.0, -11.0, 1.4])),
        (210.0, 0.05, np.array([13.0, -10.0, 1.5])),
    ],
)
def test_transformed_environment_derivatives_are_analytic_and_match_centered_checks(
    temperature, w, state
):
    env = replace(_base_environment(), T=temperature, w=w)
    temperature_column, log_w_column = transformed_vector_field_environment_derivatives(state, env)
    h_temperature = 1.0e-4
    finite_temperature = (
        transformed_vector_field(state, replace(env, T=temperature + h_temperature))
        - transformed_vector_field(state, replace(env, T=temperature - h_temperature))
    ) / (2.0 * h_temperature)
    h_log_w = 1.0e-6
    finite_log_w = (
        transformed_vector_field(state, replace(env, w=w * np.exp(h_log_w)))
        - transformed_vector_field(state, replace(env, w=w * np.exp(-h_log_w)))
    ) / (2.0 * h_log_w)
    assert np.linalg.norm(temperature_column - finite_temperature) / max(
        1.0, np.linalg.norm(finite_temperature)
    ) < 1.0e-11
    assert np.linalg.norm(log_w_column - finite_log_w) / max(
        1.0, np.linalg.norm(finite_log_w)
    ) < 1.0e-11


def test_metric_is_mesh_independent_and_owns_all_arclength_algebra():
    for interval_count in (8, 16, 64):
        _, _, family, metric = _family(interval_count)
        layout = family.assembler(0.0).layout
        first = np.zeros(layout.unknown_size + 1)
        second = np.zeros_like(first)
        variables = layout.unpack(first[:-1])
        shifted = layout.pack(
            variables.endpoints + np.array([1.0, -2.0, 0.5]),
            variables.stages + np.array([1.0, -2.0, 0.5]),
            0.25,
        )
        second[:-1] = shifted
        second[-1] = -0.4
        expected_orbit = np.linalg.norm(
            family.phase_reference.state_scaling * np.array([1.0, -2.0, 0.5])
        )
        expected = np.sqrt(expected_orbit**2 + 0.25**2 + 0.4**2)
        assert metric.norm(second - first) == pytest.approx(expected, rel=2.0e-15)
        tangent = metric.normalize(second - first)
        assert metric.norm(tangent) == pytest.approx(1.0)
        predictor = first + 0.037 * tangent
        assert metric.norm(predictor - first) == pytest.approx(0.037)
        assert metric.inner(predictor - first, tangent) == pytest.approx(0.037)
        assert np.array_equal(metric.arclength_gradient(tangent), metric.weights * tangent)


def test_analytic_parameter_column_and_augmented_sparse_jacobian_match_centered_directions():
    _, locus, family, metric = _family(64)
    with np.load(MIDPOINT_VECTORS, allow_pickle=False) as vectors:
        unknowns = np.array(vectors["n64_unknowns"], copy=True)
    coordinate = locus.rho(225.0, np.log(0.1))
    analytic = family.parameter_column(unknowns, coordinate)
    step = 1.0e-6
    finite = (
        family.assembler(coordinate + step).residual(unknowns)
        - family.assembler(coordinate - step).residual(unknowns)
    ) / (2.0 * step)
    assert np.linalg.norm(analytic - finite) / max(1.0, np.linalg.norm(analytic)) < 1.0e-7

    augmented = np.concatenate((unknowns, [coordinate]))
    tangent = np.zeros_like(augmented)
    tangent[-1] = 1.0
    problem = PseudoArclengthProblem(family, metric, augmented, tangent)
    jacobian = problem.jacobian(augmented)
    assert jacobian.format == "csr"
    direction = np.sin(np.arange(augmented.size) + 0.125)
    direction /= np.linalg.norm(direction)
    epsilon = 1.0e-6
    finite_direction = (
        problem.residual(augmented + epsilon * direction)
        - problem.residual(augmented - epsilon * direction)
    ) / (2.0 * epsilon)
    analytic_direction = jacobian @ direction
    assert np.linalg.norm(analytic_direction - finite_direction) / max(
        1.0, np.linalg.norm(analytic_direction)
    ) < 1.0e-6


def test_bootstrap_records_deterministic_step_halving_and_oriented_weighted_secant():
    _, locus, family, metric = _family(64)
    with np.load(MIDPOINT_VECTORS, allow_pickle=False) as vectors:
        unknowns = np.array(vectors["n64_unknowns"], copy=True)
    coordinate = locus.rho(225.0, np.log(0.1))
    origin = OrbitContinuationPoint(
        "test-origin", "test-origin", "origin", unknowns, coordinate,
        family.phase_reference_id, None, 1, 0.0
    )
    result = bootstrap_branch(
        family,
        metric,
        origin,
        branch_id="test-bootstrap",
        direction=1,
        initial_coordinate_step=0.02,
        maximum_weighted_step=0.025,
    )
    attempts = [event for event in result.events if event["event_type"] == "branch_bootstrap_attempt"]
    assert len(attempts) == 2
    assert attempts[0]["accepted"] is False
    assert attempts[0]["rejection_reasons"][-1] == "excessive_weighted_bootstrap_step"
    assert attempts[1]["requested_coordinate_step"] == pytest.approx(0.01)
    assert attempts[1]["accepted"] is True
    assert result.neighbor.point_kind == "branch_bootstrap"
    assert result.neighbor.parent_point_id == origin.point_id
    assert metric.norm(result.tangent) == pytest.approx(1.0)
    assert result.tangent[-1] > 0.0


def test_controlled_restart_changes_reference_only_at_recorded_boundary():
    _, locus, family, _ = _family(64)
    mapping = json.loads(RESULTS_PATH.read_text())
    target = next(point for point in mapping["points"] if point["point_id"] == "fixed225-to-spine-target")
    with np.load(VECTORS_PATH, allow_pickle=False) as vectors:
        unknowns = vectors[target["vector_key"]]
    point = OrbitContinuationPoint(
        target["point_id"], target["branch_id"], target["point_kind"], unknowns,
        target["active_coordinate"], family.phase_reference_id, target["parent_point_id"],
        target["branch_orientation"], target["accepted_step_size"]
    )
    restarted_family, restarted_point, event = controlled_phase_reference_restart(
        family,
        point,
        new_phase_reference_id="new-reference",
        new_path=SpineTemperaturePath(locus, _base_environment()),
    )
    assert family.phase_reference_id == "test-phase-reference"
    assert restarted_family.phase_reference_id == "new-reference"
    assert restarted_point.phase_reference_id == "new-reference"
    assert restarted_point.coordinate == pytest.approx(0.4)
    assert event["controlled_restart"] is True
    assert event["phase_residual_abs_after_refresh"] == 0.0
    assert event["stage_residual_max_after_refresh"] < 1.0e-9
    assert event["update_residual_max_after_refresh"] < 1.0e-9
    with pytest.raises(ValueError, match="preserve physical temperature"):
        controlled_phase_reference_restart(
            family,
            point,
            new_phase_reference_id="invalid-reference",
            new_path=FixedTemperatureRhoPath(locus, _base_environment(), 210.0),
        )


def test_near_target_nonexact_coordinates_are_never_reported_as_success(monkeypatch):
    _, locus, family, metric = _family(64)
    with np.load(MIDPOINT_VECTORS, allow_pickle=False) as vectors:
        unknowns = np.array(vectors["n64_unknowns"], copy=True)
    target = locus.rho(225.0, np.log(0.1))
    for offset in (-5.0e-15, 5.0e-15):
        origin = OrbitContinuationPoint(
            f"near-target-{offset}", "near-target", "origin", unknowns, target + offset,
            family.phase_reference_id, None, -1 if offset > 0.0 else 1, 0.0
        )
        monkeypatch.setattr(
            periodic_continuation,
            "bootstrap_branch",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("exact landing attempted")),
        )
        with pytest.raises(RuntimeError, match="exact landing attempted"):
            periodic_continuation.continue_to_coordinate(
                family,
                metric,
                origin,
                branch_id="near-target",
                target_coordinate=target,
                bootstrap_coordinate_step=1.0e-15,
            )


def test_overshooting_pseudo_arclength_candidate_is_not_reported_as_exact_target(monkeypatch):
    _, locus, family, metric = _family(64)
    with np.load(MIDPOINT_VECTORS, allow_pickle=False) as vectors:
        unknowns = np.array(vectors["n64_unknowns"], copy=True)
    coordinate = locus.rho(225.0, np.log(0.1))
    origin = OrbitContinuationPoint(
        "overshoot-origin", "overshoot", "origin", unknowns, coordinate,
        family.phase_reference_id, None, 1, 0.0
    )
    real_bootstrap = periodic_continuation.bootstrap_branch
    monkeypatch.setattr(
        periodic_continuation,
        "bootstrap_branch",
        lambda *args, **kwargs: real_bootstrap(*args, **kwargs),
    )
    original_corrector = periodic_continuation.correct_pseudo_arclength

    def overshooting_corrector(problem, initial_augmented, **kwargs):
        result = original_corrector(problem, initial_augmented, **kwargs)
        augmented = np.array(result.augmented, copy=True)
        augmented[-1] = 0.5
        return replace(result, augmented=augmented)

    monkeypatch.setattr(periodic_continuation, "correct_pseudo_arclength", overshooting_corrector)
    result = periodic_continuation.continue_to_coordinate(
        family,
        metric,
        origin,
        branch_id="overshoot",
        target_coordinate=coordinate + 0.03,
        bootstrap_coordinate_step=0.005,
        initial_arclength_step=0.005,
        minimum_arclength_step=0.002,
        maximum_arclength_step=0.005,
        maximum_steps=1,
    )
    assert result.reached_target is False
    crossing = [event for event in result.events if event.get("crosses_target")]
    assert crossing and all(event["accepted"] is False for event in crossing)
    assert all("crosses_exact_target" in event["rejection_reasons"] for event in crossing)


def test_curated_artifact_covers_exact_spine_bidirectional_segments_and_diagnostics():
    mapping = json.loads(RESULTS_PATH.read_text())
    assert mapping["summary"]["every_branch_reached_exact_target"] is True
    assert mapping["summary"]["rejected_event_count"] >= 1
    assert mapping["summary"]["rejected_event_count"] == sum(
        event.get("accepted") is False for event in mapping["events"]
    )
    refresh_events = [event for event in mapping["events"] if event["event_type"] == "phase_reference_refresh"]
    assert len(refresh_events) == 2
    assert mapping["summary"]["controlled_phase_reference_refresh_count"] == len(refresh_events)
    assert mapping["summary"]["accepted_event_count"] == sum(
        event.get("accepted") is True for event in mapping["events"]
    )
    assert mapping["summary"]["informational_event_count"] == sum(
        "accepted" not in event for event in mapping["events"]
    )
    assert (
        mapping["summary"]["accepted_event_count"]
        + mapping["summary"]["rejected_event_count"]
        + mapping["summary"]["informational_event_count"]
        == len(mapping["events"])
    )
    refresh_by_id = {event["new_phase_reference_id"]: event for event in refresh_events}
    spine_refresh = refresh_by_id["phase-ref-spine-225"]
    slice_refresh = refresh_by_id["phase-ref-slice-210"]
    assert spine_refresh["old_coordinate_name"] == "rho"
    assert spine_refresh["new_coordinate_name"] == "temperature_hat"
    assert spine_refresh["physical_coordinates"]["temperature_K"] == 225.0
    assert spine_refresh["physical_coordinates"]["rho"] == 0.0
    assert slice_refresh["old_coordinate_name"] == "temperature_hat"
    assert slice_refresh["new_coordinate_name"] == "rho"
    assert slice_refresh["physical_coordinates"]["temperature_K"] == 210.0
    assert slice_refresh["physical_coordinates"]["rho"] == 0.0
    assert slice_refresh["point_id"] == "spine-negative-T-hat-to-210-target"
    assert slice_refresh["restarted_point_id"].endswith("phase-ref-slice-210")
    for refresh in refresh_events:
        assert refresh["stage_residual_max_after_refresh"] < 1.0e-9
        assert refresh["update_residual_max_after_refresh"] < 1.0e-9
        assert refresh["phase_residual_abs_after_refresh"] < 1.0e-10
    branches = {branch["branch_id"]: branch for branch in mapping["branches"]}
    assert branches["fixed225-to-spine"]["target_coordinate"] == 0.0
    assert branches["spine-positive-T-hat"]["branch_orientation"] == 1
    assert branches["spine-negative-T-hat-to-210"]["branch_orientation"] == -1
    assert branches["slice210-negative-rho"]["branch_orientation"] == -1
    assert branches["slice210-positive-rho"]["branch_orientation"] == 1

    exact_225 = next(point for point in mapping["points"] if point["point_id"] == "fixed225-to-spine-target")
    exact_210 = next(point for point in mapping["points"] if point["point_id"] == "spine-negative-T-hat-to-210-target")
    exact_226 = next(point for point in mapping["points"] if point["point_id"] == "spine-positive-T-hat-target")
    exact_lower = next(point for point in mapping["points"] if point["point_id"] == "slice210-negative-rho-target")
    exact_upper = next(point for point in mapping["points"] if point["point_id"] == "slice210-positive-rho-target")
    assert exact_225["temperature_K"] == 225.0 and exact_225["rho"] == 0.0
    assert exact_210["temperature_K"] == 210.0 and exact_210["rho"] == 0.0
    assert exact_226["temperature_K"] == 226.0 and exact_226["temperature_hat"] == pytest.approx(0.44)
    assert exact_lower["temperature_K"] == 210.0 and exact_lower["rho"] == -0.15
    assert exact_upper["temperature_K"] == 210.0 and exact_upper["rho"] == 0.15
    required = {
        "stage_residual_max", "stage_residual_rms", "update_residual_max",
        "update_residual_rms", "phase_residual_abs", "phase_energy",
        "phase_reference_alignment_cosine", "weighted_distance_from_phase_reference",
        "temperature_hat", "rho", "temperature_K", "log_w", "w_m_s", "period_s",
        "branch_orientation", "phase_reference_id",
    }
    assert all(required <= set(point) for point in mapping["points"])
    assert all(point["stage_residual_max"] < 1.0e-9 for point in mapping["points"])
    assert all(point["update_residual_max"] < 1.0e-9 for point in mapping["points"])
    assert all(point["phase_residual_abs"] < 1.0e-10 for point in mapping["points"])
    assert all(event["phase_reference_id"] == branches[event["branch_id"]]["phase_reference_id"]
               for event in mapping["events"]
               if event.get("branch_id") in branches and "phase_reference_id" in event)
    provenance = mapping["source_provenance"]
    assert {
        "generator_path", "generator_sha256", "periodic_continuation_path",
        "periodic_continuation_sha256", "periodic_orbits_path", "periodic_orbits_sha256",
        "episode007_seed_path", "episode007_seed_sha256", "episode006_hopf_loci_path",
        "episode006_hopf_loci_sha256", "task056_midpoint_vectors_path",
        "task056_midpoint_vectors_sha256",
    } <= set(provenance)
    for prefix in ("generator", "periodic_continuation", "periodic_orbits"):
        path = REPO_ROOT / provenance[f"{prefix}_path"]
        assert sha256_file(path) == provenance[f"{prefix}_sha256"]
    solver_fields = {
        "scipy_success", "scipy_status", "scipy_message", "scipy_cost",
        "scipy_optimality", "function_evaluations", "jacobian_evaluations",
        "stage_residual_max", "update_residual_max", "phase_residual_abs",
        "arclength_residual_abs",
    }
    solver_events = [event for event in mapping["events"] if "accepted" in event]
    assert solver_events and all(solver_fields <= set(event) for event in solver_events)


def test_curated_vectors_have_documented_shapes_checksums_and_exact_point_values():
    mapping = json.loads(RESULTS_PATH.read_text())
    manifest = mapping["vector_artifact"]["arrays"]
    with np.load(VECTORS_PATH, allow_pickle=False) as vectors:
        assert set(vectors.files) == set(manifest)
        for key, metadata in manifest.items():
            assert list(vectors[key].shape) == metadata["shape"]
            assert vectors[key].dtype == np.dtype("<f8")
            value = np.ascontiguousarray(vectors[key], dtype="<f8")
            import hashlib
            assert hashlib.sha256(value.tobytes(order="C")).hexdigest() == metadata["sha256"]
        for point in mapping["points"]:
            assert vectors[point["vector_key"]].shape == (385,)


def test_fixed_mesh_continuation_generator_rebuilds_committed_outputs_exactly():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        generator = importlib.import_module("generate_fixed_mesh_continuation_results")
        mapping, arrays = generator.build_outputs()
        expected_npz = generator._npz_bytes(arrays)
        mapping["vector_artifact"]["file_sha256"] = generator._sha256(expected_npz)
        assert generator._canonical_json(mapping) == RESULTS_PATH.read_bytes()
        assert expected_npz == VECTORS_PATH.read_bytes()
        generator.generate(check=True)
    finally:
        sys.path.remove(str(SCRIPT_DIR))
