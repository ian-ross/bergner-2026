from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_spine_slices_run.json"
RUN_DIR = EPISODE / "outputs/native_adaptive_spine_slices_run"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_spine_slices_run.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_summary() -> dict:
    return json.loads(SUMMARY.read_text())


def load_run_manifest() -> dict:
    return json.loads((RUN_DIR / "manifest.json").read_text())


def test_native_adaptive_spine_slices_generator_is_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_run_manifest_covers_spine_skeleton_slices_anchors_and_single_terminal_statuses() -> None:
    data = load_summary()
    planned = data["planned_run_manifest"]
    ledger = data["terminal_target_ledger"]
    assert data["schema_version"] == "episode008-native-adaptive-spine-slices-run-v1"
    assert planned["provisional_spine_range_K"] == [210, 226]
    assert planned["temperature_skeleton_K"] == [210, 212, 214, 216, 218, 220, 222, 224, 225, 226]
    assert planned["signed_rho_slice_targets"] == [-0.15, 0.15]
    assert ledger["target_count"] == planned["target_count"] == 31
    assert ledger["exactly_one_terminal_status_per_target"] is True
    assert sum(ledger["terminal_status_counts"].values()) == ledger["target_count"]
    allowed = set(ledger["terminal_status_allowed_values"])
    assert allowed == {"accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed"}
    by_id = {target["target_id"]: target for target in ledger["targets"]}
    assert by_id["move-225K-to-spine-rho0"]["terminal_status"] == "accepted"
    assert by_id["spine-210K"]["terminal_status"] == "accepted"
    assert by_id["spine-225K"]["terminal_status"] == "accepted"
    assert by_id["spine-226K"]["terminal_status"] == "accepted"
    assert by_id["slice-210K-rho--0.15"]["terminal_status"] == "accepted"
    assert by_id["slice-210K-rho-+0.15"]["terminal_status"] == "accepted"
    assert all(target.get("reason") for target in ledger["targets"] if target["terminal_status"] == "failed")


def test_driver_run_directory_is_resumable_and_checkpointed() -> None:
    data = load_summary()
    manifest = load_run_manifest()
    assert data["run_manifest"]["sha256"] == sha(RUN_DIR / "manifest.json")
    assert manifest["artifact_kind"] == "native-adaptive-driver-run-manifest"
    assert manifest["status"] == "complete"
    assert manifest["run_id"] == "task06803-provisional-spine-slices"
    assert manifest["resume"]["complete_checkpoint_count"] == len(manifest["segments"]) == data["run_manifest"]["segment_count"]
    assert data["run_manifest"]["checkpoint_count"] == len(manifest["segments"])
    assert manifest["resource_accounting"] == {"max_rss_kib": 0, "segment_cpu_s": 0.0, "segment_wall_clock_s": 0.0}
    for segment in manifest["segments"]:
        path = RUN_DIR / segment["checkpoint_path"]
        assert path.is_file()
        assert segment["checkpoint_complete"] is True
        assert segment["checkpoint_sha256"] == sha(path)
        checkpoint = json.loads(path.read_text())
        assert checkpoint["segment_id"] == segment["segment_id"]
        assert checkpoint["fingerprints_sha256"] == manifest["fingerprints_sha256"]
        assert checkpoint["segment_sha256"]


def test_accepted_points_and_remesh_restart_gates_are_recorded() -> None:
    data = load_summary()
    gates = data["validation_gates"]
    assert gates["accepted_segment_count"] == 7
    assert gates["accepted_point_count"] >= 32
    assert gates["all_accepted_points_pass_residual_phase_positivity_linear_gates"] is True
    assert gates["restart_count"] == 1
    assert gates["all_restart_gates_pass_residual_phase_positivity_finite_change_linear_tangent"] is True
    assert len(gates["unresolved_rejected_capped_tripwire_outcomes_recorded"]) == data["terminal_target_ledger"]["terminal_status_counts"]["failed"]

    manifest = load_run_manifest()
    remesh_segments = [segment for segment in manifest["segments"] if segment["remesh_kind"] == "h+r"]
    assert len(remesh_segments) == 1
    remesh = remesh_segments[0]
    assert remesh["target_id"] == "spine-210K"
    assert remesh["event_partition"]["rejected_remesh_boundary_count"] == 0
    assert remesh["restart"]["accepted"] is True
    assert all(remesh["restart"]["gates"].values())
    assert remesh["restart"]["linear"]["backend"] == "KLU2"


def test_near_hopf_and_truthfulness_boundaries_are_explicit() -> None:
    data = load_summary()
    assert data["truthfulness_policy"]["generalized_native_adaptive_driver_executed"] is True
    assert data["truthfulness_policy"]["production_cpp_adaptive_backend_executed"] is False
    assert data["truthfulness_policy"]["python_or_fixed_mesh_evidence_not_rebranded_as_full_native_adaptive_completion"] is True
    near_hopf = data["near_hopf_evidence"]
    assert near_hopf["status"] == "not_reached_in_provisional_run"
    assert near_hopf["approach_point_count"] == 0
    assert near_hopf["reliable_point_target_when_reachable"] == 5
    assert {"amplitude", "period_s", "coordinates", "diagnostics", "terminal_status"}.issubset(near_hopf["required_fields_when_reached"])
    assert near_hopf["fit_and_connection_policy_deferred_to"] == "TASK-069"
    for source in data["provenance"].values():
        if isinstance(source, dict) and "path" in source:
            assert sha(ROOT / source["path"]) == source["sha256"]
