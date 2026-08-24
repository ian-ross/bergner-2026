from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/native_adaptive_loca_manifest.json"
VECTORS = EPISODE / "outputs/native_adaptive_loca_manifest_vectors.npz"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_loca_manifest.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(RESULTS.read_text())


def test_native_adaptive_manifest_generator_is_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_native_adaptive_manifest_records_truthful_evidence_boundary_and_versions() -> None:
    data = load()
    assert data["schema_version"] == "episode008-native-adaptive-loca-manifest-v1"
    assert data["truthfulness_policy"] == {
        "native_adaptive_remesh_executed": False,
        "native_adaptive_remesh_restart_smoke_executed": True,
        "native_adaptive_one_branch_segment_executed": True,
        "fixed_mesh_native_evidence_may_seed_adaptive_run": True,
        "python_adaptive_evidence_not_rebranded_as_native": True,
        "broader_ivp_based_evidence": "not_evaluated",
        "floquet_dependent_evidence": "not_evaluated",
    }
    assert data["versions"]["adaptive_method"] == "external-gauss3-hr-adaptive-v1"
    assert data["versions"]["native_loca_fixed_mesh"] == "native-loca-gauss-fixed-mesh-pseudo-arclength-v1"
    contract = data["native_segment_contract"]
    assert contract["remesh_boundary_policy"].startswith("stop only at accepted native points")
    assert contract["fixed_mesh_segment_owner"] == "LOCA::Stepper"
    assert "LOCA::Stepper" in contract["full_rebuild_lineage"]
    retry = contract["retry_order_from_TASK067_fixture"]["h_plus_r"]
    assert [attempt["name"] for attempt in retry] == [
        "h_r_transfer_correct",
        "h_r_refresh_reference_recorrect",
        "h_r_rebootstrap_tangent_recorrect",
    ]


def test_planned_manifest_covers_skeleton_anchors_slices_and_single_terminal_status() -> None:
    planned = load()["planned_run_manifest"]
    assert planned["provisional_spine_range_K"] == [210, 226]
    assert planned["temperature_skeleton_K"] == [210, 212, 214, 216, 218, 220, 222, 224, 225, 226]
    targets = planned["targets"]
    allowed = set(planned["terminal_status_allowed_values"])
    assert len(targets) == planned["target_count"] == 1 + 3 * len(planned["temperature_skeleton_K"])
    assert len({target["target_id"] for target in targets}) == len(targets)
    assert sum(planned["terminal_status_counts"].values()) == len(targets)
    assert all(target["terminal_status"] in allowed for target in targets)
    assert all("reason" in target for target in targets if target["terminal_status"] == "failed")

    by_id = {target["target_id"]: target for target in targets}
    assert by_id["move-225K-to-spine-rho0"]["terminal_status"] == "accepted"
    assert by_id["spine-210K"]["terminal_status"] == "accepted"
    assert by_id["spine-225K"]["terminal_status"] == "accepted"
    assert by_id["spine-226K"]["terminal_status"] == "accepted"
    assert by_id["slice-210K-rho--0.15"]["terminal_status"] == "accepted"
    assert by_id["slice-210K-rho-+0.15"]["terminal_status"] == "accepted"
    assert by_id["slice-226K-rho-+0.15"]["terminal_status"] == "failed"


def test_vector_artifact_hashes_match_arrays_and_sources() -> None:
    data = load()
    assert sha(VECTORS) == data["vector_artifact"]["sha256"]
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert len(arrays.files) == data["vector_artifact"]["array_count"]
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        assert any(name.startswith("native_fixed_mesh_checkpoint__fixed225-to-spine") for name in arrays.files)
        assert any(name.startswith("adaptive_final__canonical-g3-n32") for name in arrays.files)
        for name in arrays.files:
            spec = data["vector_artifact"]["arrays"][name]
            value = np.ascontiguousarray(np.asarray(arrays[name], dtype="<f8"))
            assert list(value.shape) == spec["shape"]
            assert hashlib.sha256(value.tobytes(order="C")).hexdigest() == spec["sha256"]
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]


def test_segment_restart_artifact_ledger_records_events_meshes_gates_and_terminal_targets() -> None:
    artifacts = load()["segment_restart_artifacts"]
    assert artifacts["artifact_purpose"].startswith("deterministic segment/restart ledger")
    branches = artifacts["native_fixed_mesh_branch_ledgers"]
    assert len(branches) == 5
    assert all(branch["event_partition"]["loca_accepted_count"] == len(branch["checkpoint_vector_keys"]) for branch in branches)
    assert all(branch["event_partition"]["loca_rejected_count"] == 0 for branch in branches)
    assert all(branch["accounting_invariants"]["saved_points_equal_accepted_callbacks"] for branch in branches)
    assert max(branch["maximum_python_same_coordinate_period_relative_error"] for branch in branches) <= 2e-7

    histories = artifacts["adaptive_reference_mesh_histories"]
    assert len(histories) == 4
    assert all(history["converged"] and history["final_defect_maximum"] < 1e-4 for history in histories)
    assert any(event["kind"] == "h+r" and event["correction_accepted"] for history in histories for event in history["remesh_events"])
    assert all(
        event["restart_plan"] == [
            "h_r_transfer_correct",
            "h_r_refresh_reference_recorrect",
            "h_r_rebootstrap_tangent_recorrect",
        ]
        for history in histories
        for event in history["remesh_events"]
        if event["kind"] == "h+r"
    )

    restart_cases = artifacts["native_remesh_restart_smoke_cases"]
    assert sum(case["restart_executed"] for case in restart_cases) == 2
    for case in restart_cases:
        assert case["controller_restart_retry_order_h_plus_r"] == [
            "h_r_transfer_correct",
            "h_r_refresh_reference_recorrect",
            "h_r_rebootstrap_tangent_recorrect",
        ]
        if case["restart_executed"]:
            restart = case["restart"]
            assert restart["graph_rebuilt"] is True
            assert restart["retained_graph_reuse"] is True
            assert all(restart["gates"].values())
            assert restart["linear"]["backend"] == "KLU2"
            assert restart["correction"]["status"] == "accepted"
    one_branch = artifacts["native_adaptive_one_branch_segment"]
    assert one_branch["branch_id"] == "spine-negative-T-hat-to-210"
    assert one_branch["adaptive_case_id"] == "adaptive-guard-rho-0-g3-n32"
    assert one_branch["remesh_boundary"]["policy"].startswith("stop only after an accepted native LOCA callback")
    assert all(one_branch["gates"].values())
    assert all(one_branch["restart_gates"].values())
    assert one_branch["resumable_state"]["full_run_terminal_status"] == "not_claimed"

    assert len(artifacts["phase_lineage"]) == 2
    assert all(refresh["verification"]["accepted"] for refresh in artifacts["phase_lineage"])
    terminal = artifacts["terminal_target_ledger"]
    assert terminal["exactly_one_terminal_status_per_target"] is True
    assert terminal["target_count"] == 31
    assert sum(terminal["terminal_status_counts"].values()) == terminal["target_count"]
    profile = artifacts["runtime_memory_profile_policy"]
    assert profile["deterministic_artifact_records_runtime_identity"] is True
    assert "segment_wall_clock_s" in profile["required_full_run_fields"]
    assert artifacts["not_evaluated_evidence"] == {
        "broader_ivp_based": "not_evaluated",
        "floquet_dependent": "not_evaluated",
    }


def test_failure_policy_coverage_records_tripwires_reasons_and_deferred_evidence() -> None:
    coverage = load()["failure_policy_coverage"]
    assert coverage["artifact_purpose"].startswith("TASK-068.05")
    synthetic = coverage["native_driver_synthetic_test_coverage"]
    assert synthetic["test_file"] == "tests/test_episode8_native_adaptive_driver.py"
    assert "failed h+r transfer/correction restart with preserved rejection reasons" in synthetic["covered_paths"]
    assert "pure-r deterministic retry order" in synthetic["covered_paths"]
    assert "mesh cap escalation diagnostic channel" in synthetic["covered_paths"]
    assert "process interruption and resume without rerunning completed checkpoints" in synthetic["covered_paths"]
    assert "stale source/configuration checkpoint rejection" in synthetic["covered_paths"]
    assert "tangent_only_rebootstrap" in synthetic["tangent_only_rebootstrap_coverage"]

    channels = coverage["diagnostic_channels"]
    assert channels["aliasing_events"]["event_count"] >= 1
    assert channels["aliasing_events"]["persistent_case_ids"]
    radau = channels["radau_triggers"]
    assert radau["polynomial_ringing"]["unique_recorded_values"] == ["'not_evaluated'"]
    assert radau["broader_ivp_based"]["not_evaluated_through_TASK_068"] is True
    assert radau["floquet_dependent"]["not_evaluated_through_TASK_068"] is True
    assert channels["single_valued_tripwire"]["version"] == "single-valued-tripwire-v1"
    assert channels["rejection_reasons"]["failed_targets_have_reasons"] is True
    assert channels["phase_refresh_triggers"]
    assert all({"case_id", "cycle_index", "triggers"}.issubset(record) for record in channels["phase_refresh_triggers"])

    near_hopf = coverage["near_hopf_policy"]
    assert near_hopf["fixture_status"] == "fixture_missing"
    assert near_hopf["diagnostics_status"] == "not_evaluated"
    assert near_hopf["minimum_reliable_point_target_when_reached"] == 5
    assert coverage["truthful_deferred_evidence"] == {
        "broader_ivp_based": "not_evaluated_through_TASK_068",
        "floquet_dependent": "not_evaluated_through_TASK_068",
    }


def test_parity_and_near_hopf_scope_are_explicit() -> None:
    data = load()
    parity = data["parity"]
    assert parity["python_adaptive_all_qualification_cases_converged"] is True
    assert parity["native_fixed_parameter_correction_cases"]["accepted_count"] >= 6
    assert parity["cpp_nonuniform_fixture_parity"]["case_count"] == 4
    assert parity["cpp_nonuniform_fixture_parity"]["all_projected_from_final_adaptive_cycles"] is True
    assert "adaptive-controller" in parity["cpp_nonuniform_fixture_parity"]["source"]
    assert "adaptive-restart" in parity["cpp_nonuniform_fixture_parity"]["source"]
    smoke = parity["native_adaptive_restart_smoke"]
    assert smoke["controller_case_count"] == 4
    assert smoke["restart_case_count"] == 2
    assert smoke["all_restart_gates_passed"] is True
    assert "not the full adaptive" in smoke["source"]
    one_branch = parity["native_adaptive_one_branch_segment"]
    assert one_branch["selected_branch_id"] == "spine-negative-T-hat-to-210"
    assert one_branch["selected_adaptive_case_id"] == "adaptive-guard-rho-0-g3-n32"
    assert one_branch["all_gates_passed"] is True
    assert one_branch["restart_solution_matches_smoke"] is True
    assert parity["stratified_native_fixed_mesh_python_corrections"]["maximum_all_point_period_relative_error"] <= 2e-7
    assert "Adaptive remesh" in parity["evidence_boundary"]
    near_hopf = data["near_hopf_evidence"]
    assert near_hopf["status"] == "not_reached_in_this_preparatory_manifest"
    assert near_hopf["minimum_reliable_point_target_when_reached"] == 5
    assert near_hopf["fit_review_deferred_to"] == "TASK-069"
