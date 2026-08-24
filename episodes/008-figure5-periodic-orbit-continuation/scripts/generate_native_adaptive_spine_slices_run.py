#!/usr/bin/env python3
"""Generate the TASK-068.03 provisional native adaptive spine-and-slices run.

The production C++ adaptive backend is still intentionally separated from the
shared resumable driver.  This slice therefore executes the complete provisional
spine-and-slices target manifest through the generalized driver with a curated
scripted backend built only from existing native fixed-mesh, one-branch remesh,
and restart-smoke evidence.  Targets without native adaptive evidence receive
truthful terminal failures with explicit reasons; no fixed-mesh or Python-only
point is relabeled as a completed production adaptive continuation target.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import (  # noqa: E402
    NativeAdaptiveDriver,
    NativeAdaptiveDriverConfig,
    ScriptedNativeAdaptiveBackend,
    canonical_sha256,
    sha256_file,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_spine_slices_run.json"
RUN_DIR = OUTPUT / "native_adaptive_spine_slices_run"
GENERATOR = Path(__file__).resolve()
DRIVER_SOURCE = ROOT / "src/bergner_spichtinger_2026/native_adaptive_driver.py"

PREPARATORY_MANIFEST = OUTPUT / "native_adaptive_loca_manifest.json"
PREPARATORY_VECTORS = OUTPUT / "native_adaptive_loca_manifest_vectors.npz"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
NATIVE_HIGHER_ORDER_VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"
ONE_BRANCH = OUTPUT / "native_adaptive_one_branch_segment.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
RESTART_SMOKE = OUTPUT / "native_adaptive_restart_smoke.json"
RESTART_SMOKE_VECTORS = OUTPUT / "native_adaptive_restart_smoke_vectors.npz"
CPP_NONUNIFORM = OUTPUT / "cpp_adaptive_nonuniform_fixtures/manifest.json"

SCHEMA_VERSION = "episode008-native-adaptive-spine-slices-run-v1"
ARTIFACT_KIND = "task06803-provisional-native-adaptive-spine-slices-run"
RUN_ID = "task06803-provisional-spine-slices"
NORMALIZED_TIME = "2026-08-24T00:00:00Z"
ALLOWED_TERMINAL_STATUSES = (
    "accepted",
    "resolution_unresolved",
    "near_hopf_stop",
    "tripwire_stop",
    "failed",
)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def file_inputs() -> tuple[Path, ...]:
    return (
        PREPARATORY_MANIFEST,
        PREPARATORY_VECTORS,
        NATIVE_HIGHER_ORDER,
        NATIVE_HIGHER_ORDER_VECTORS,
        ONE_BRANCH,
        ONE_BRANCH_VECTORS,
        RESTART_SMOKE,
        RESTART_SMOKE_VECTORS,
        CPP_NONUNIFORM,
    )


def point_passes_native_gates(point: dict[str, Any]) -> bool:
    gates = point["native_validation"]
    return bool(
        gates["stage_residual_max"] <= 1e-9
        and gates["update_residual_max"] <= 1e-9
        and gates["phase_residual_abs"] <= 1e-10
        and gates["physical_states_positive_finite"]
        and gates["period_positive_finite"]
        and gates["linear_solve_complete"]
    )


def branch_points(native: dict[str, Any], branch_id: str) -> list[dict[str, Any]]:
    points = [copy.deepcopy(point) for point in native["points"] if point["branch_id"] == branch_id]
    if not points:
        raise RuntimeError(f"missing native points for branch {branch_id}")
    points.sort(key=lambda point: int(point["point_index"]))
    return points


def branch_events(points: list[dict[str, Any]], *, remesh_boundary: bool = False) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for callback_index, point in enumerate(points):
        role = "initial" if callback_index == 0 else "final" if callback_index == len(points) - 1 else "regular"
        events.append({
            "callback_index": callback_index,
            "status": "accepted",
            "accepted": True,
            "save_role": role,
            "point_index": int(point["point_index"]),
            "vector_key": point["vector_key"],
            "period_s": point["period_s"],
            "active_coordinate": point["active_coordinate"],
            "remesh_boundary_candidate": bool(remesh_boundary and role == "final"),
        })
    return events


def accepted_branch_spec(native: dict[str, Any], branch_id: str, *, remesh_boundary: bool = False) -> dict[str, Any]:
    points = branch_points(native, branch_id)
    max_residual = max(
        max(point["native_validation"]["stage_residual_max"], point["native_validation"]["update_residual_max"])
        for point in points
    )
    max_phase = max(point["native_validation"]["phase_residual_abs"] for point in points)
    return {
        "events": branch_events(points, remesh_boundary=remesh_boundary),
        "points": [{
            "point_id": point["point_id"],
            "point_index": point["point_index"],
            "branch_id": point["branch_id"],
            "active_coordinate_name": point["active_coordinate_name"],
            "active_coordinate": point["active_coordinate"],
            "period_s": point["period_s"],
            "vector_key": point["vector_key"],
            "native_validation": point["native_validation"],
            "independent_python_validation": {
                "period_relative_error": point["python_same_coordinate_period_relative_error"],
                "weighted_orbit_error": point["python_same_coordinate_weighted_orbit_error"],
            },
            "accepted_gates_passed": point_passes_native_gates(point),
        } for point in points],
        "mesh_history": [{"rule": "gauss3", "interval_count": 32, "source": "native_fixed_mesh_higher_order_checkpoint"}],
        "defects": {"maximum": max_residual, "source": "native residual gate summary; independent adaptive defects remain restart/controller evidence"},
        "convergence": {"nox_status": "converged", "linear_backend": "KLU2", "maximum_phase_residual_abs": max_phase},
        "phase_lineage": sorted({point["phase_reference_id"] for point in points}),
        "diagnostics": {
            "accepted_point_count": len(points),
            "all_accepted_points_pass_residual_phase_positivity_linear_gates": all(point_passes_native_gates(point) for point in points),
            "maximum_native_residual": max_residual,
            "maximum_phase_residual_abs": max_phase,
        },
        "decision": {"action": "stop_converged", "terminal_status": "converged"},
    }


def failed_spec(target: dict[str, Any]) -> dict[str, Any]:
    reason = target.get("reason", "no native adaptive evidence for provisional target")
    return {
        "events": [{
            "callback_index": 0,
            "status": "rejected",
            "accepted": False,
            "save_role": "final",
            "reason": reason,
        }],
        "points": [],
        "mesh_history": [{"status": "not_started", "reason": reason}],
        "defects": {"maximum": None, "status": "not_evaluated", "reason": reason},
        "convergence": {"nox_status": "not_started", "reason": reason},
        "phase_lineage": [],
        "diagnostics": {"terminal_failure_reason": reason},
        "decision": {"action": "stop_failed", "terminal_status": "failed", "reason": reason},
    }


def restart_spec(one_branch: dict[str, Any]) -> dict[str, Any]:
    restart = one_branch["restart"]
    return {
        "status": "accepted",
        "accepted": True,
        "attempt_order": restart["attempts"],
        "tangent": restart["tangent"],
        "rebuild": {
            "identity_changed": True,
            "graph_rebuilt": restart["graph"]["rebuilt"],
            "retained_graph_reuse": restart["graph"]["retained_reuse"],
            "old_unknown_size": restart["rebuild"]["old_unknown_size"],
            "new_unknown_size": restart["rebuild"]["new_unknown_size"],
        },
        "transfer_residual": restart["transfer_residual"],
        "correction": restart["correction"],
        "linear": restart["linear"],
        "gates": restart["gates"],
        "solution_vector_key": restart["solution_vector_key"],
        "solution_sha256": restart["solution_sha256"],
    }


def build_script(planned: dict[str, Any], native: dict[str, Any], one_branch: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    script: dict[str, list[dict[str, Any]]] = {}
    for target in planned["targets"]:
        target_id = target["target_id"]
        if target["terminal_status"] != "accepted":
            script[target_id] = [failed_spec(target)]
            continue
        branch_id = target.get("native_branch_id")
        if branch_id is None:
            raise RuntimeError(f"accepted target {target_id} lacks a native branch id")
        if target_id == "spine-210K":
            first = accepted_branch_spec(native, branch_id, remesh_boundary=True)
            first["decision"] = {
                "action": "ordinary_h_r",
                "terminal_status": "continue",
                "remesh_kind": "h+r",
                "reason": "accepted final spine point selected as remesh boundary before adaptive restart",
            }
            first["transfer_correction_details"] = [one_branch["transfer"], one_branch["restart"]]
            second = {
                "events": [
                    {"callback_index": 0, "status": "accepted", "accepted": True, "save_role": "initial", "point_index": 0, "vector_key": one_branch["restart"]["solution_vector_key"]},
                    {"callback_index": 1, "status": "accepted", "accepted": True, "save_role": "final", "point_index": 1, "vector_key": one_branch["restart"]["solution_vector_key"]},
                ],
                "points": [{
                    "point_id": "spine-210K-post-remesh-restart",
                    "active_coordinate_name": "temperature_hat",
                    "active_coordinate": one_branch["native_fixed_mesh_segment"]["target_coordinate"],
                    "period_s": one_branch["restart"]["correction"]["period_s"],
                    "vector_key": one_branch["restart"]["solution_vector_key"],
                    "restart_solution_sha256": one_branch["restart"]["solution_sha256"],
                    "restart_gates": one_branch["restart"]["gates"],
                }],
                "mesh_history": [{
                    "source": "native_adaptive_one_branch_restart",
                    "old_unknown_size": one_branch["restart"]["rebuild"]["old_unknown_size"],
                    "new_unknown_size": one_branch["restart"]["rebuild"]["new_unknown_size"],
                }],
                "defects": {"maximum": max(one_branch["restart"]["final_diagnostics"]["stage_max"], one_branch["restart"]["final_diagnostics"]["update_max"])},
                "convergence": {"nox_status": one_branch["restart"]["correction"]["nox_status"], "linear_backend": one_branch["restart"]["linear"]["backend"]},
                "phase_lineage": ["phase-ref-spine-225", "native_adaptive_one_branch_restart"],
                "diagnostics": {
                    "restart_gates_passed": all(one_branch["restart"]["gates"].values()),
                    "post_restart_phase_abs": one_branch["restart"]["final_diagnostics"]["phase_abs"],
                },
                "decision": {"action": "stop_converged", "terminal_status": "converged"},
            }
            script[target_id] = [{**first, "restart": restart_spec(one_branch)}, second]
        else:
            script[target_id] = [accepted_branch_spec(native, branch_id)]
    return script


def target_terminal_ledger(manifest: dict[str, Any]) -> dict[str, Any]:
    segments_by_target: dict[str, list[dict[str, Any]]] = {}
    for segment in manifest["segments"]:
        segments_by_target.setdefault(segment["target_id"], []).append(segment)
    targets = []
    for target in manifest["target_manifest"]:
        target_id = target["target_id"]
        status = manifest["target_status"][target_id]["terminal_status"]
        segment = segments_by_target[target_id][-1]
        reason = segment["adaptive_decision"].get("reason") or target.get("reason")
        entry = {
            "target_id": target_id,
            "target_type": target["target_type"],
            "temperature_K": target["temperature_K"],
            "rho": target.get("rho"),
            "terminal_status": status,
            "completed_segment_id": manifest["target_status"][target_id]["completed_segment_id"],
        }
        if status == "failed":
            entry["reason"] = reason
        targets.append(entry)
    counts = {status: sum(target["terminal_status"] == status for target in targets) for status in ALLOWED_TERMINAL_STATUSES}
    return {
        "target_count": len(targets),
        "terminal_status_allowed_values": list(ALLOWED_TERMINAL_STATUSES),
        "terminal_status_counts": counts,
        "exactly_one_terminal_status_per_target": len({target["target_id"] for target in targets}) == len(targets) and sum(counts.values()) == len(targets),
        "targets": targets,
    }


def validation_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    accepted_segments = [segment for segment in manifest["segments"] if segment["terminal_status"] == "accepted" or segment["terminal_status"] == "continue"]
    accepted_points = []
    restart_gates = []
    unresolved_or_rejected = []
    for segment in manifest["segments"]:
        for point in segment["fixed_mesh_segment"].get("points", []):
            if "accepted_gates_passed" in point:
                accepted_points.append(point["accepted_gates_passed"])
        if segment.get("restart") is not None:
            restart_gates.append(all(segment["restart"].get("gates", {}).values()))
        if segment["terminal_status"] == "failed":
            unresolved_or_rejected.append({
                "segment_id": segment["segment_id"],
                "target_id": segment["target_id"],
                "terminal_status": "failed",
                "reason": segment["adaptive_decision"].get("reason"),
            })
    return {
        "accepted_segment_count": len(accepted_segments),
        "accepted_point_count": len(accepted_points),
        "all_accepted_points_pass_residual_phase_positivity_linear_gates": all(accepted_points),
        "restart_count": len(restart_gates),
        "all_restart_gates_pass_residual_phase_positivity_finite_change_linear_tangent": all(restart_gates),
        "unresolved_rejected_capped_tripwire_outcomes_recorded": unresolved_or_rejected,
    }


def failure_policy_diagnostics(manifest: dict[str, Any], preparatory: dict[str, Any]) -> dict[str, Any]:
    diagnostics = [segment["diagnostics"] for segment in manifest["segments"]]
    failed_targets = [target for target in target_terminal_ledger(manifest)["targets"] if target["terminal_status"] == "failed"]
    return {
        "source": "NativeAdaptiveDriver normalized per-segment diagnostics plus preparatory TASK-068.05 coverage ledger",
        "cap_escalation_channel_present": all("cap_escalations" in item for item in diagnostics),
        "aliasing_channel_present": all("aliasing_events" in item for item in diagnostics),
        "radau_trigger_channel_present": all("radau_triggers" in item for item in diagnostics),
        "single_valued_tripwire_channel_present": all("single_valued_tripwire" in item for item in diagnostics),
        "rejection_reasons_preserved_for_failed_targets": len(failed_targets) == len([
            segment for segment in manifest["segments"] if segment["terminal_status"] == "failed"
        ]),
        "failed_targets_have_reasons": all(bool(target.get("reason")) for target in failed_targets),
        "not_evaluated_evidence": {
            "broader_ivp_based": "not_evaluated_through_TASK_068",
            "floquet_dependent": "not_evaluated_through_TASK_068",
        },
        "preparatory_failure_policy_coverage_sha256": sha256_file(PREPARATORY_MANIFEST),
        "preparatory_single_valued_tripwire_version": preparatory["failure_policy_coverage"]["diagnostic_channels"]["single_valued_tripwire"]["version"],
    }


def near_hopf_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    terminal_statuses = [item["terminal_status"] for item in manifest["target_status"].values()]
    return {
        "status": "not_reached_in_provisional_run",
        "approach_point_count": 0,
        "reliable_point_target_when_reachable": 5,
        "required_fields_when_reached": ["amplitude", "period_s", "coordinates", "diagnostics", "terminal_status"],
        "approach_points": [],
        "terminal_statuses_observed": sorted(set(terminal_statuses)),
        "reason": "The provisional run terminates accepted fixed-mesh/restart anchors and explicit failed targets before any near-Hopf approach is reached.",
        "fit_and_connection_policy_deferred_to": "TASK-069",
    }


def normalize_run(run_manifest: dict[str, Any], run_directory: Path) -> dict[str, bytes]:
    manifest = copy.deepcopy(run_manifest)
    manifest["created_at"] = NORMALIZED_TIME
    manifest["updated_at"] = NORMALIZED_TIME
    manifest["resource_accounting"] = {"segment_wall_clock_s": 0.0, "segment_cpu_s": 0.0, "max_rss_kib": 0}
    for status in manifest["target_status"].values():
        target_id = next(key for key, value in manifest["target_status"].items() if value is status)
        matching = [segment for segment in manifest["segments"] if segment["target_id"] == target_id]
        if matching and status["terminal_status"] == "failed":
            status["reason"] = matching[-1]["adaptive_decision"].get("reason")
    files: dict[str, bytes] = {}
    for segment in manifest["segments"]:
        segment["resources"] = {"segment_wall_clock_s": 0.0, "segment_cpu_s": 0.0, "segment_max_rss_kib": 0}
        checkpoint_rel = segment["checkpoint_path"]
        checkpoint = load_json(run_directory / checkpoint_rel)
        checkpoint["created_at"] = NORMALIZED_TIME
        checkpoint["segment"]["resources"] = copy.deepcopy(segment["resources"])
        checkpoint["segment_sha256"] = canonical_sha256(checkpoint["segment"])
        checkpoint_bytes = canonical(checkpoint)
        segment["checkpoint_sha256"] = hashlib.sha256(checkpoint_bytes).hexdigest()
        files[checkpoint_rel] = checkpoint_bytes
    manifest["updated_at"] = NORMALIZED_TIME
    files["manifest.json"] = canonical(manifest)
    return files


def build() -> tuple[bytes, dict[str, bytes]]:
    preparatory = load_json(PREPARATORY_MANIFEST)
    native = load_json(NATIVE_HIGHER_ORDER)
    one_branch = load_json(ONE_BRANCH)
    restart_smoke = load_json(RESTART_SMOKE)
    planned = preparatory["planned_run_manifest"]
    script = build_script(planned, native, one_branch)
    targets = tuple(copy.deepcopy(target) for target in planned["targets"])
    with tempfile.TemporaryDirectory() as tmp:
        run_directory = Path(tmp) / "run"
        config = NativeAdaptiveDriverConfig(
            run_id=RUN_ID,
            run_directory=run_directory,
            targets=targets,
            configuration={
                "schema_version": SCHEMA_VERSION,
                "backend": "scripted-curated-native-evidence",
                "rule": "gauss3",
                "provisional_spine_range_K": planned["provisional_spine_range_K"],
                "temperature_skeleton_K": planned["temperature_skeleton_K"],
                "signed_rho_slice_targets": planned["signed_rho_slice_targets"],
                "truthfulness_policy": "failed targets remain failed with reasons; no interpolation or Python relabeling",
            },
            source_paths=(GENERATOR, DRIVER_SOURCE),
            source_root=ROOT,
            executable_identity={
                "backend": "ScriptedNativeAdaptiveBackend",
                "production_cpp_adaptive_backend_executed": False,
                "native_fixed_mesh_and_restart_artifacts_replayed": True,
            },
            vector_fingerprints={path.relative_to(ROOT).as_posix(): sha256_file(path) for path in file_inputs()},
            max_cycles_per_target=4,
        )
        run_manifest = NativeAdaptiveDriver(config, ScriptedNativeAdaptiveBackend(script)).run()
        run_files = normalize_run(run_manifest, run_directory)
    normalized_manifest = json.loads(run_files["manifest.json"].decode())
    ledger = target_terminal_ledger(normalized_manifest)
    validation = validation_summary(normalized_manifest)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "scope": "provisional spine-and-slices native adaptive driver run using curated native fixed-mesh and one-branch remesh/restart evidence; not final Figure 5 production data",
        "truthfulness_policy": {
            "generalized_native_adaptive_driver_executed": True,
            "production_cpp_adaptive_backend_executed": False,
            "native_fixed_mesh_evidence_replayed_as_segment_evidence": True,
            "native_one_branch_remesh_restart_evidence_replayed": True,
            "python_or_fixed_mesh_evidence_not_rebranded_as_full_native_adaptive_completion": True,
            "unreached_targets_are_terminal_failed_with_reasons": True,
        },
        "planned_run_manifest": {
            "provisional_spine_range_K": planned["provisional_spine_range_K"],
            "temperature_skeleton_K": planned["temperature_skeleton_K"],
            "signed_rho_slice_targets": planned["signed_rho_slice_targets"],
            "target_count": planned["target_count"],
            "coverage_statement": planned["coverage_statement"],
        },
        "run_directory": RUN_DIR.relative_to(ROOT).as_posix(),
        "run_manifest": {
            "path": RUN_DIR.joinpath("manifest.json").relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(run_files["manifest.json"]).hexdigest(),
            "segment_count": len(normalized_manifest["segments"]),
            "checkpoint_count": len([name for name in run_files if name.startswith("checkpoints/")]),
            "status": normalized_manifest["status"],
            "resume": normalized_manifest["resume"],
        },
        "terminal_target_ledger": ledger,
        "validation_gates": validation,
        "failure_policy_diagnostics": failure_policy_diagnostics(normalized_manifest, preparatory),
        "near_hopf_evidence": near_hopf_evidence(normalized_manifest),
        "provenance": {
            "preparatory_manifest": source_record(PREPARATORY_MANIFEST),
            "native_higher_order_results": source_record(NATIVE_HIGHER_ORDER),
            "native_one_branch_segment": source_record(ONE_BRANCH),
            "native_adaptive_restart_smoke": source_record(RESTART_SMOKE),
            "cpp_nonuniform_fixture_manifest": source_record(CPP_NONUNIFORM),
            "driver_source": source_record(DRIVER_SOURCE),
            "generator": source_record(GENERATOR),
            "input_files": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in file_inputs()},
        },
        "restart_smoke_crosscheck": {
            "schema_version": restart_smoke["schema_version"],
            "all_restart_gates_passed": all(
                all(case["restart"]["gates"].values())
                for case in restart_smoke["cases"] if case.get("restart") is not None
            ),
            "one_branch_restart_solution_sha256": one_branch["restart"]["solution_sha256"],
        },
        "regeneration_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_spine_slices_run.py [--check]",
    }
    return canonical(summary), run_files


def write_outputs(summary_bytes: bytes, run_files: dict[str, bytes]) -> None:
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for relative, body in sorted(run_files.items()):
        path = RUN_DIR / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    SUMMARY.write_bytes(summary_bytes)


def check_outputs(summary_bytes: bytes, run_files: dict[str, bytes]) -> None:
    if not SUMMARY.is_file() or SUMMARY.read_bytes() != summary_bytes:
        raise SystemExit("native adaptive spine-and-slices run summary is stale")
    actual_files = {path.relative_to(RUN_DIR).as_posix(): path.read_bytes() for path in RUN_DIR.rglob("*") if path.is_file()}
    if actual_files != run_files:
        raise SystemExit("native adaptive spine-and-slices run directory is stale")
    print("verified native adaptive spine-and-slices run artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary_bytes, run_files = build()
    if args.check:
        check_outputs(summary_bytes, run_files)
    else:
        write_outputs(summary_bytes, run_files)
        print(f"wrote {SUMMARY.relative_to(ROOT)}")
        print(f"wrote {RUN_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
