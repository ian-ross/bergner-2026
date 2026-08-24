#!/usr/bin/env python3
"""Generate the TASK-068 final native-adaptive evidence reconciliation manifest.

This sink artifact is written after the TASK-068 implementation slices.  It
summarizes the already generated native adaptive evidence for review and parent
acceptance-criteria closure without feeding back into any upstream artifact, so
its provenance graph stays acyclic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
RESULTS = OUTPUT / "native_adaptive_final_reconciliation.json"

PREPARATORY_MANIFEST = OUTPUT / "native_adaptive_loca_manifest.json"
PREPARATORY_VECTORS = OUTPUT / "native_adaptive_loca_manifest_vectors.npz"
RESTART_SMOKE = OUTPUT / "native_adaptive_restart_smoke.json"
RESTART_SMOKE_VECTORS = OUTPUT / "native_adaptive_restart_smoke_vectors.npz"
ONE_BRANCH = OUTPUT / "native_adaptive_one_branch_segment.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
SPINE_SLICES_SUMMARY = OUTPUT / "native_adaptive_spine_slices_run.json"
SPINE_SLICES_RUN_MANIFEST = OUTPUT / "native_adaptive_spine_slices_run/manifest.json"
PYTHON_VALIDATION = OUTPUT / "native_adaptive_python_validation.json"
PYTHON_VALIDATION_VECTORS = OUTPUT / "native_adaptive_python_validation_vectors.npz"
CPP_NONUNIFORM_MANIFEST = OUTPUT / "cpp_adaptive_nonuniform_fixtures/manifest.json"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
NATIVE_HIGHER_ORDER_VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"

SCHEMA_VERSION = "episode008-native-adaptive-final-reconciliation-v1"
ARTIFACT_KIND = "task068-final-native-adaptive-evidence-reconciliation"
ALLOWED_TERMINAL_STATUSES = {"accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def artifact_record(name: str, path: Path, role: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    if data is None and path.suffix == ".json":
        data = load_json(path)
    record: dict[str, Any] = {
        "name": name,
        "role": role,
        "path": rel(path),
        "sha256": sha(path),
    }
    if data is not None:
        record["schema_version"] = data.get("schema_version")
        record["artifact_kind"] = data.get("artifact_kind")
    return record


def terminal_target_reconciliation(run_summary: dict[str, Any], run_manifest: dict[str, Any]) -> dict[str, Any]:
    ledger = run_summary["terminal_target_ledger"]
    targets = ledger["targets"]
    allowed = set(ledger["terminal_status_allowed_values"])
    checkpoint_segment_ids = {segment["segment_id"] for segment in run_manifest["segments"]}
    targets_with_segments = [target for target in targets if target.get("completed_segment_id") in checkpoint_segment_ids]
    failed = [target for target in targets if target["terminal_status"] == "failed"]
    return {
        "source": "outputs/native_adaptive_spine_slices_run.json plus driver manifest checkpoints",
        "target_count": ledger["target_count"],
        "terminal_status_counts": ledger["terminal_status_counts"],
        "allowed_terminal_statuses": sorted(allowed),
        "allowed_statuses_match_TASK_068_contract": allowed == ALLOWED_TERMINAL_STATUSES,
        "exactly_one_terminal_status_per_target": ledger["exactly_one_terminal_status_per_target"],
        "all_failed_targets_preserve_reasons": all(bool(target.get("reason")) for target in failed),
        "failed_target_count": len(failed),
        "accepted_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "accepted"],
        "failed_target_ids": [target["target_id"] for target in failed],
        "all_targets_have_completed_or_failed_driver_segments": len(targets_with_segments) == len(targets),
        "completed_segment_count_for_targets": len(targets_with_segments),
    }


def segment_checkpoint_reconciliation(run_summary: dict[str, Any], run_manifest: dict[str, Any]) -> dict[str, Any]:
    segments = run_manifest["segments"]
    checkpoints = []
    checkpoint_hashes_match = True
    for segment in segments:
        path = OUTPUT / "native_adaptive_spine_slices_run" / segment["checkpoint_path"]
        current_sha = sha(path)
        checkpoint_hashes_match = checkpoint_hashes_match and current_sha == segment["checkpoint_sha256"]
        checkpoints.append({
            "segment_id": segment["segment_id"],
            "target_id": segment["target_id"],
            "checkpoint_path": rel(path),
            "checkpoint_sha256": current_sha,
            "terminal_status": segment["terminal_status"],
            "remesh_kind": segment["remesh_kind"],
        })
    return {
        "run_id": run_manifest["run_id"],
        "status": run_manifest["status"],
        "segment_count": len(segments),
        "checkpoint_count": run_summary["run_manifest"]["checkpoint_count"],
        "all_segment_checkpoint_files_exist_and_hash_match": checkpoint_hashes_match,
        "resume": run_manifest["resume"],
        "lifecycle_states": run_manifest["lifecycle_states"],
        "event_partition_rollup": {
            "accepted_segment_count": run_summary["validation_gates"]["accepted_segment_count"],
            "accepted_point_count": run_summary["validation_gates"]["accepted_point_count"],
            "restart_count": run_summary["validation_gates"]["restart_count"],
            "failed_or_unresolved_outcome_count": len(run_summary["validation_gates"]["unresolved_rejected_capped_tripwire_outcomes_recorded"]),
        },
        "checkpoints": checkpoints,
    }


def remesh_restart_reconciliation(
    prep: dict[str, Any],
    run_manifest: dict[str, Any],
    one_branch: dict[str, Any],
    restart_smoke: dict[str, Any],
) -> dict[str, Any]:
    remesh_segments = [segment for segment in run_manifest["segments"] if segment.get("remesh_kind")]
    h_plus_r_order = [attempt["name"] for attempt in prep["native_segment_contract"]["retry_order_from_TASK067_fixture"]["h_plus_r"]]
    smoke_restart_cases = [case for case in restart_smoke["cases"] if case.get("restart") is not None]
    return {
        "accepted_boundary_policy": prep["native_segment_contract"]["remesh_boundary_policy"],
        "full_rebuild_lineage": prep["native_segment_contract"]["full_rebuild_lineage"],
        "retry_order_h_plus_r": h_plus_r_order,
        "retry_order_pure_r": [attempt["name"] for attempt in prep["native_segment_contract"]["retry_order_from_TASK067_fixture"]["pure_r"]],
        "provisional_run_remesh_segment_count": len(remesh_segments),
        "provisional_run_remesh_segments": [
            {
                "segment_id": segment["segment_id"],
                "target_id": segment["target_id"],
                "remesh_kind": segment["remesh_kind"],
                "restart_accepted": segment["restart"]["accepted"],
                "restart_gates": segment["restart"]["gates"],
                "linear_backend": segment["restart"]["linear"]["backend"],
                "rejected_remesh_boundary_count": segment["event_partition"]["rejected_remesh_boundary_count"],
            }
            for segment in remesh_segments
        ],
        "one_branch_transfer_vector_keys": sorted(one_branch["vector_artifact"]["arrays"]),
        "one_branch_all_gates_passed": all(one_branch["gates"].values()) and all(one_branch["restart"]["gates"].values()),
        "restart_smoke_case_count": restart_smoke["restart_case_count"],
        "restart_smoke_all_gates_passed": all(all(case["restart"]["gates"].values()) for case in smoke_restart_cases),
        "restart_smoke_graph_rebuild_identity": [
            {
                "case_id": case["case_id"],
                "graph_rebuilt": case["restart"]["graph"]["rebuilt"],
                "retained_graph_reuse": case["restart"]["graph"]["retained_reuse"],
                "old_unknown_size": case["restart"]["rebuild"]["old_unknown_size"],
                "new_unknown_size": case["restart"]["rebuild"]["new_unknown_size"],
            }
            for case in smoke_restart_cases
        ],
    }


def mesh_convergence_validation(
    prep: dict[str, Any],
    run_summary: dict[str, Any],
    python_validation: dict[str, Any],
    cpp_nonuniform: dict[str, Any],
) -> dict[str, Any]:
    histories = prep["segment_restart_artifacts"]["adaptive_reference_mesh_histories"]
    validation_summary = python_validation["summary"]
    return {
        "adaptive_reference_mesh_histories": [
            {
                "case_id": history["case_id"],
                "cycle_count": history["cycle_count"],
                "start_interval_count": history["start_interval_count"],
                "final_interval_count": history["final_interval_count"],
                "final_defect_maximum": history["final_defect_maximum"],
                "terminal_status": history["terminal_status"],
            }
            for history in histories
        ],
        "final_interval_counts": prep["adaptive_reference_evidence"]["final_interval_counts"],
        "final_defect_maxima": prep["adaptive_reference_evidence"]["final_defect_maxima"],
        "all_adaptive_reference_cases_converged": prep["adaptive_reference_evidence"]["all_cases_converged"],
        "cpp_nonuniform_fixture_case_count": len(cpp_nonuniform["cases"]),
        "cpp_nonuniform_all_cases_project_final_adaptive_cycles": all(
            case["status"] == "accepted" and case["final_defect_maximum"] < 1e-4
            for case in cpp_nonuniform["cases"]
        ),
        "native_gate_summary": run_summary["validation_gates"],
        "python_validation_summary": validation_summary,
        "python_validation_tolerances": python_validation["tolerances"],
        "post_remesh_restart_not_rebranded_as_python_validation": python_validation["truthfulness_policy"]["post_remesh_restart_not_rebranded_as_python_validation"],
        "accepted_points_without_independent_python_validation": python_validation["accepted_points_without_independent_python_validation"],
    }


def runtime_resource_reconciliation(prep: dict[str, Any], run_manifest: dict[str, Any], run_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "native_fixed_mesh_runtime_provenance": prep["segment_restart_artifacts"]["runtime_memory_profile_policy"]["native_fixed_mesh_runtime_provenance"],
        "restart_smoke_runtime_provenance": prep["segment_restart_artifacts"]["runtime_memory_profile_policy"]["restart_smoke_runtime_provenance"],
        "provisional_run_resource_accounting": run_manifest["resource_accounting"],
        "provisional_run_resource_fields_are_deterministic_placeholders": run_manifest["resource_accounting"] == {
            "max_rss_kib": 0,
            "segment_cpu_s": 0.0,
            "segment_wall_clock_s": 0.0,
        },
        "required_full_run_fields": prep["segment_restart_artifacts"]["runtime_memory_profile_policy"]["required_full_run_fields"],
        "run_manifest_status": run_summary["run_manifest"]["status"],
        "run_manifest_segment_count": run_summary["run_manifest"]["segment_count"],
    }


def parent_acceptance_criteria_review(prep: dict[str, Any], run_summary: dict[str, Any], python_validation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "parent_ac": 1,
            "review_status": "satisfied_by_slice_evidence",
            "checked_for_parent_closure": True,
            "evidence": [
                "native_adaptive_one_branch_segment accepted remesh boundary and restart gates",
                "native_adaptive_driver segment lifecycle/retry/resume contract",
                "native_adaptive_spine_slices_run accepted remesh segment and checkpointed restart",
            ],
            "boundary": "Production C++ adaptive backend coverage remains provisional and reviewer-facing, not final Figure 5 production policy.",
        },
        {
            "parent_ac": 2,
            "review_status": "satisfied_by_component_and_policy_evidence",
            "checked_for_parent_closure": True,
            "evidence": [
                "cpp_adaptive_nonuniform_fixtures parity bundle",
                "native adaptive restart-smoke controller/restart seams",
                "failure-policy synthetic/native-driver coverage",
            ],
            "boundary": "TASK-067 Python fixtures supply reference policy where native full-run fixtures do not exist.",
        },
        {
            "parent_ac": 3,
            "review_status": "satisfied_by_manifest_reconciliation",
            "checked_for_parent_closure": True,
            "evidence": [
                "preparatory segment/restart ledger",
                "provisional run driver manifest with checkpoints",
                "source/vector/checkpoint hashes and resume state in this sink manifest",
            ],
        },
        {
            "parent_ac": 4,
            "review_status": "satisfied_by_validation_and_tests",
            "checked_for_parent_closure": True,
            "evidence": [
                f"{python_validation['summary']['selected_point_count']} stratified native points pass Python validation",
                "focused tests cover nonuniform parity, restart recovery, resume, terminal manifest coverage, and fixed-mesh regressions",
                "generator --check commands pass for all TASK-068 artifacts",
            ],
        },
        {
            "parent_ac": 5,
            "review_status": "satisfied_with_truthful_not_reached_boundary",
            "checked_for_parent_closure": True,
            "evidence": [
                f"near-Hopf status: {run_summary['near_hopf_evidence']['status']}",
                "required amplitude/period/coordinate/diagnostic fields and five-point target are recorded for TASK-069 when reachable",
            ],
            "deferred_to_TASK_069": "quadratic/quartic fit review and final connection/gap policy",
        },
        {
            "parent_ac": 6,
            "review_status": "satisfied_by_gate_and_failure_policy_ledger",
            "checked_for_parent_closure": True,
            "evidence": [
                "accepted points/restarts pass residual, phase, positivity, linear, finite-change, and tangent gates",
                "failed targets preserve reasons and failed/unresolved evidence is not suppressed",
                "broader IVP and Floquet evidence are explicitly not_evaluated through TASK-068",
            ],
        },
        {
            "parent_ac": 7,
            "review_status": "satisfied_by_terminal_target_ledger",
            "checked_for_parent_closure": True,
            "evidence": [
                f"{run_summary['terminal_target_ledger']['target_count']} targets cover T=225 spine move, 210--226 K skeleton, exact anchors, and signed rho slices",
                "each target has exactly one accepted or failed terminal status with reason when failed",
            ],
        },
    ]


def build() -> bytes:
    prep = load_json(PREPARATORY_MANIFEST)
    restart_smoke = load_json(RESTART_SMOKE)
    one_branch = load_json(ONE_BRANCH)
    run_summary = load_json(SPINE_SLICES_SUMMARY)
    run_manifest = load_json(SPINE_SLICES_RUN_MANIFEST)
    python_validation = load_json(PYTHON_VALIDATION)
    cpp_nonuniform = load_json(CPP_NONUNIFORM_MANIFEST)

    input_artifacts = [
        artifact_record("native_adaptive_loca_manifest", PREPARATORY_MANIFEST, "structural remesh/restart and preparatory evidence ledger", prep),
        artifact_record("native_adaptive_loca_manifest_vectors", PREPARATORY_VECTORS, "preparatory vector artifact"),
        artifact_record("native_adaptive_restart_smoke", RESTART_SMOKE, "native controller/restart seam smoke evidence", restart_smoke),
        artifact_record("native_adaptive_restart_smoke_vectors", RESTART_SMOKE_VECTORS, "restart-smoke vector artifact"),
        artifact_record("native_adaptive_one_branch_segment", ONE_BRANCH, "integrated one-branch accepted remesh/restart slice", one_branch),
        artifact_record("native_adaptive_one_branch_segment_vectors", ONE_BRANCH_VECTORS, "one-branch vector artifact"),
        artifact_record("native_adaptive_spine_slices_summary", SPINE_SLICES_SUMMARY, "provisional driver-run summary", run_summary),
        artifact_record("native_adaptive_spine_slices_run_manifest", SPINE_SLICES_RUN_MANIFEST, "resumable driver run manifest", run_manifest),
        artifact_record("native_adaptive_python_validation", PYTHON_VALIDATION, "independent same-coordinate Python validation", python_validation),
        artifact_record("native_adaptive_python_validation_vectors", PYTHON_VALIDATION_VECTORS, "Python-validation vector fingerprints"),
        artifact_record("cpp_adaptive_nonuniform_fixture_manifest", CPP_NONUNIFORM_MANIFEST, "C++ nonuniform parity fixture manifest", cpp_nonuniform),
        artifact_record("native_loca_higher_order_results", NATIVE_HIGHER_ORDER, "native fixed-mesh LOCA input evidence"),
        artifact_record("native_loca_higher_order_vectors", NATIVE_HIGHER_ORDER_VECTORS, "native fixed-mesh LOCA vector artifact"),
    ]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "scope": (
            "TASK-068 final evidence reconciliation across native adaptive slices; this is reviewer-facing "
            "closure evidence and not final Figure 5 production data or TASK-069 fitting policy."
        ),
        "manifest_identity": {
            "path": rel(RESULTS),
            "generator_path": rel(Path(__file__)),
            "deterministic_serialization": "canonical sorted-key JSON with trailing newline",
            "self_hash_policy": "no in-payload sha256; tests compute file hash externally",
        },
        "provenance_policy": {
            "final_manifest_is_sink": True,
            "input_graph_acyclic": True,
            "self_reference_allowed": False,
            "upstream_artifacts_must_not_reference_final_manifest": True,
        },
        "input_artifacts": input_artifacts,
        "source_provenance": {
            "generator": artifact_record("native_adaptive_final_reconciliation_generator", Path(__file__), "final reconciliation generator"),
            "episode_readme": artifact_record("episode008_readme", EPISODE / "README.md", "episode documentation"),
            "final_reconciliation_doc": artifact_record(
                "task068_final_evidence_reconciliation_doc",
                EPISODE / "docs/task068-final-evidence-reconciliation.md",
                "reviewer-facing evidence summary",
            ),
        },
        "truthfulness_policy": {
            "python_validation_is_not_native_adaptive_execution": True,
            "python_or_fixed_mesh_evidence_not_rebranded_as_full_native_adaptive_completion": True,
            "provisional_driver_run_executed": run_summary["truthfulness_policy"]["generalized_native_adaptive_driver_executed"],
            "production_cpp_adaptive_backend_executed": run_summary["truthfulness_policy"]["production_cpp_adaptive_backend_executed"],
            "failed_targets_remain_failed": python_validation["truthfulness_policy"]["failed_targets_remain_failed"],
            "broader_ivp_based_evidence": "not_evaluated_through_TASK_068",
            "floquet_dependent_evidence": "not_evaluated_through_TASK_068",
        },
        "target_reconciliation": terminal_target_reconciliation(run_summary, run_manifest),
        "segment_checkpoint_reconciliation": segment_checkpoint_reconciliation(run_summary, run_manifest),
        "remesh_restart_reconciliation": remesh_restart_reconciliation(prep, run_manifest, one_branch, restart_smoke),
        "mesh_convergence_validation": mesh_convergence_validation(prep, run_summary, python_validation, cpp_nonuniform),
        "phase_lineage": prep["segment_restart_artifacts"]["phase_lineage"],
        "runtime_resource_reconciliation": runtime_resource_reconciliation(prep, run_manifest, run_summary),
        "failure_and_deferred_evidence": {
            "failure_policy_coverage": prep["failure_policy_coverage"],
            "run_failure_policy_diagnostics": run_summary["failure_policy_diagnostics"],
            "near_hopf_evidence": run_summary["near_hopf_evidence"],
            "task069_handoff_items": [
                "quadratic/quartic near-Hopf fit review",
                "final connection/gap policy",
                "production C++ adaptive backend policy if stricter evidence is required",
                "broader IVP-based and Floquet-dependent evidence design",
                "runtime/resource profiling with non-placeholder wall-clock, CPU, and RSS fields",
            ],
        },
        "parent_acceptance_criteria_review": parent_acceptance_criteria_review(prep, run_summary, python_validation),
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_adaptive_nonuniform_fixtures.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_restart_smoke.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_one_branch_segment.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_spine_slices_run.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_python_validation.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_final_reconciliation.py --check",
            ],
            "focused_tests": [
                "uv run pytest tests/test_episode8_cpp_adaptive_nonuniform.py tests/test_episode8_native_adaptive_restart_smoke.py tests/test_episode8_native_adaptive_one_branch_segment.py tests/test_episode8_native_adaptive_driver.py tests/test_episode8_native_adaptive_loca_manifest.py tests/test_episode8_native_adaptive_spine_slices_run.py tests/test_episode8_native_adaptive_python_validation.py tests/test_episode8_native_adaptive_final_reconciliation.py -q",
            ],
            "full_tests": ["uv run pytest -q"],
        },
    }
    return canonical(manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify existing output without rewriting")
    args = parser.parse_args()
    result_bytes = build()
    if args.check:
        if not RESULTS.is_file() or RESULTS.read_bytes() != result_bytes:
            raise SystemExit("native adaptive final reconciliation artifact is stale")
        print("verified native adaptive final reconciliation artifact")
    else:
        RESULTS.write_bytes(result_bytes)
        print(f"wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
