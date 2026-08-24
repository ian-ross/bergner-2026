from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/native_adaptive_final_reconciliation.json"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_final_reconciliation.py"
RUN_MANIFEST = EPISODE / "outputs/native_adaptive_spine_slices_run/manifest.json"
DOC = EPISODE / "docs/task068-final-evidence-reconciliation.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(RESULTS.read_text())


def test_final_reconciliation_generator_is_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_input_artifacts_have_current_hashes_and_final_manifest_is_sink() -> None:
    data = load()
    assert data["schema_version"] == "episode008-native-adaptive-final-reconciliation-v1"
    assert data["artifact_kind"] == "task068-final-native-adaptive-evidence-reconciliation"
    assert data["provenance_policy"] == {
        "final_manifest_is_sink": True,
        "input_graph_acyclic": True,
        "self_reference_allowed": False,
        "upstream_artifacts_must_not_reference_final_manifest": True,
    }
    assert data["manifest_identity"]["path"] == RESULTS.relative_to(ROOT).as_posix()
    input_paths = [artifact["path"] for artifact in data["input_artifacts"]]
    assert RESULTS.relative_to(ROOT).as_posix() not in input_paths
    names = {artifact["name"] for artifact in data["input_artifacts"]}
    assert {
        "native_adaptive_loca_manifest",
        "native_adaptive_restart_smoke",
        "native_adaptive_one_branch_segment",
        "native_adaptive_spine_slices_summary",
        "native_adaptive_spine_slices_run_manifest",
        "native_adaptive_python_validation",
        "cpp_adaptive_nonuniform_fixture_manifest",
    }.issubset(names)
    for artifact in data["input_artifacts"]:
        assert sha(ROOT / artifact["path"]) == artifact["sha256"]
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]


def test_terminal_targets_segments_checkpoints_and_resume_are_reconciled() -> None:
    data = load()
    target = data["target_reconciliation"]
    assert target["target_count"] == 31
    assert target["terminal_status_counts"] == {
        "accepted": 6,
        "failed": 25,
        "near_hopf_stop": 0,
        "resolution_unresolved": 0,
        "tripwire_stop": 0,
    }
    assert target["allowed_statuses_match_TASK_068_contract"] is True
    assert target["exactly_one_terminal_status_per_target"] is True
    assert target["all_failed_targets_preserve_reasons"] is True
    assert target["all_targets_have_completed_or_failed_driver_segments"] is True
    assert "move-225K-to-spine-rho0" in target["accepted_target_ids"]
    assert "slice-226K-rho-+0.15" in target["failed_target_ids"]

    segments = data["segment_checkpoint_reconciliation"]
    assert segments["status"] == "complete"
    assert segments["segment_count"] == segments["checkpoint_count"] == 32
    assert segments["all_segment_checkpoint_files_exist_and_hash_match"] is True
    assert segments["resume"]["complete_checkpoint_count"] == 32
    assert segments["resume"]["latest_complete_segment_id"].startswith("segment-0031")
    assert segments["event_partition_rollup"]["accepted_segment_count"] == 7
    assert segments["event_partition_rollup"]["restart_count"] == 1
    for checkpoint in segments["checkpoints"]:
        assert sha(ROOT / checkpoint["checkpoint_path"]) == checkpoint["checkpoint_sha256"]
    assert sha(RUN_MANIFEST) in {artifact["sha256"] for artifact in data["input_artifacts"]}


def test_remesh_restart_mesh_validation_and_runtime_boundaries_are_reconciled() -> None:
    data = load()
    remesh = data["remesh_restart_reconciliation"]
    assert remesh["accepted_boundary_policy"].startswith("stop only at accepted native points")
    assert remesh["retry_order_h_plus_r"] == [
        "h_r_transfer_correct",
        "h_r_refresh_reference_recorrect",
        "h_r_rebootstrap_tangent_recorrect",
    ]
    assert remesh["retry_order_pure_r"] == [
        "pure_r_transfer_correct",
        "pure_r_refresh_reference_recorrect",
        "pure_r_rebootstrap_tangent_recorrect",
    ]
    assert remesh["provisional_run_remesh_segment_count"] == 1
    segment = remesh["provisional_run_remesh_segments"][0]
    assert segment["target_id"] == "spine-210K"
    assert segment["remesh_kind"] == "h+r"
    assert segment["restart_accepted"] is True
    assert all(segment["restart_gates"].values())
    assert segment["linear_backend"] == "KLU2"
    assert remesh["one_branch_all_gates_passed"] is True
    assert remesh["restart_smoke_all_gates_passed"] is True
    assert all(case["graph_rebuilt"] and case["retained_graph_reuse"] for case in remesh["restart_smoke_graph_rebuild_identity"])

    validation = data["mesh_convergence_validation"]
    assert validation["all_adaptive_reference_cases_converged"] is True
    assert max(validation["final_defect_maxima"].values()) < 1e-4
    assert validation["cpp_nonuniform_fixture_case_count"] == 4
    assert validation["cpp_nonuniform_all_cases_project_final_adaptive_cycles"] is True
    assert validation["native_gate_summary"]["all_accepted_points_pass_residual_phase_positivity_linear_gates"] is True
    assert validation["native_gate_summary"]["all_restart_gates_pass_residual_phase_positivity_finite_change_linear_tangent"] is True
    assert validation["python_validation_summary"]["all_selected_points_pass"] is True
    assert validation["python_validation_summary"]["selected_point_count"] == 32
    assert validation["post_remesh_restart_not_rebranded_as_python_validation"] is True

    runtime = data["runtime_resource_reconciliation"]
    assert runtime["provisional_run_resource_fields_are_deterministic_placeholders"] is True
    assert {"segment_wall_clock_s", "segment_cpu_s", "segment_max_rss_kib"}.issubset(runtime["required_full_run_fields"])


def test_truthfulness_near_hopf_task069_handoff_and_parent_ac_review_are_explicit() -> None:
    data = load()
    assert data["truthfulness_policy"] == {
        "broader_ivp_based_evidence": "not_evaluated_through_TASK_068",
        "failed_targets_remain_failed": True,
        "floquet_dependent_evidence": "not_evaluated_through_TASK_068",
        "production_cpp_adaptive_backend_executed": False,
        "provisional_driver_run_executed": True,
        "python_or_fixed_mesh_evidence_not_rebranded_as_full_native_adaptive_completion": True,
        "python_validation_is_not_native_adaptive_execution": True,
    }
    deferred = data["failure_and_deferred_evidence"]
    assert deferred["near_hopf_evidence"]["status"] == "not_reached_in_provisional_run"
    assert deferred["near_hopf_evidence"]["approach_point_count"] == 0
    assert deferred["near_hopf_evidence"]["reliable_point_target_when_reachable"] == 5
    assert {"quadratic/quartic near-Hopf fit review", "final connection/gap policy"}.issubset(deferred["task069_handoff_items"])
    assert deferred["failure_policy_coverage"]["truthful_deferred_evidence"] == {
        "broader_ivp_based": "not_evaluated_through_TASK_068",
        "floquet_dependent": "not_evaluated_through_TASK_068",
    }

    review = data["parent_acceptance_criteria_review"]
    assert [entry["parent_ac"] for entry in review] == list(range(1, 8))
    assert all(entry["checked_for_parent_closure"] is True for entry in review)
    assert all(entry["review_status"].startswith("satisfied") for entry in review)
    assert any("TASK-069" in str(entry) for entry in review)


def test_episode_documentation_summarizes_final_evidence_scope_and_commands() -> None:
    doc = DOC.read_text()
    readme = README.read_text()
    required_phrases = [
        "Coverage and mesh behavior",
        "Convergence, restart, and validation evidence",
        "Failures, near-Hopf evidence, and deferred scope",
        "Runtime and resource cost",
        "TASK-069",
        "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_final_reconciliation.py --check",
    ]
    for phrase in required_phrases:
        assert phrase in doc
    assert "TASK-068 final native adaptive evidence reconciliation" in readme
    assert "outputs/native_adaptive_final_reconciliation.json" in readme
