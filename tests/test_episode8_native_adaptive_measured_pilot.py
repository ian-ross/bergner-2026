from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_measured_pilot.json"
RUN_DIR = EPISODE / "outputs/native_adaptive_measured_pilot"
EVENTS = EPISODE / "outputs/native_adaptive_measured_pilot_events.json"
RUN_METADATA = EPISODE / "outputs/native_adaptive_measured_pilot_run_metadata.json"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_measured_pilot.py"
DOC = EPISODE / "docs/task072-measured-native-adaptive-pilot.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_summary() -> dict:
    return json.loads(SUMMARY.read_text())


def load_manifest() -> dict:
    return json.loads((RUN_DIR / "manifest.json").read_text())


def test_task072_measured_pilot_generator_is_current_and_schema_valid() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(json.loads(EVENTS.read_text()), root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(json.loads(RUN_METADATA.read_text()), root=ROOT, artifact_path=RUN_METADATA)


def test_task072_terminal_ledger_has_one_backend_status_per_skeleton_target() -> None:
    data = load_summary()
    ledger = data["terminal_target_ledger"]
    assert data["schema_version"] == "episode008-native-adaptive-measured-pilot-v1"
    assert data["truthfulness_policy"] == {
        "accepted_target_requires_complete_exact_native_gate_bundle": True,
        "fixed_mesh_or_python_evidence_not_relabelled_as_task072_acceptance": True,
        "interpolation_used_to_fill_targets": False,
        "native_backend_emitted_every_terminal_status": True,
        "unaccepted_targets_are_explicit_unresolved_gap_records": True,
    }
    assert ledger["target_count"] == data["planned_run_manifest"]["target_count"] == 31
    assert ledger["exactly_one_terminal_status_per_target"] is True
    assert ledger["terminal_status_counts"] == {
        "accepted": 0,
        "resolution_unresolved": 31,
        "near_hopf_stop": 0,
        "tripwire_stop": 0,
        "failed": 0,
    }
    by_id = {target["target_id"]: target for target in ledger["targets"]}
    assert by_id["spine-210K"]["terminal_status"] == "resolution_unresolved"
    assert by_id["spine-210K"]["backend_emitted_terminal_status"] is True
    assert "exact native restart-vector" in by_id["spine-210K"]["reason"]
    unresolved = [target for target in ledger["targets"] if target["terminal_status"] != "accepted"]
    assert len(unresolved) == 31
    assert all(target["terminal_status"] == "resolution_unresolved" for target in unresolved)
    assert all(target["reason"] and target["explicit_gap_record"] for target in unresolved)


def test_task072_no_target_is_accepted_without_complete_exact_gate_bundle() -> None:
    gates = load_summary()["validation_gates"]
    assert gates["accepted_target_count"] == 0
    assert gates["accepted_point_count"] == 0
    assert gates["restart_count"] == 0
    assert gates["all_accepted_points_pass_required_gates"] is True
    assert gates["all_remesh_restarts_pass_required_gates"] is True
    assert gates["required_gate_names"] == [
        "residual",
        "phase",
        "positivity",
        "finite_change",
        "tangent",
        "linear_solve",
        "defect",
        "period_orbit_convergence",
    ]
    assert gates["accepted_points"] == []
    assert gates["adaptive_defect_gate"]["final_defect_maximum"] < gates["adaptive_defect_gate"]["defect_tolerance"]


def test_task072_resources_identity_checkpoints_and_resume_are_recorded() -> None:
    data = load_summary()
    resources = data["measured_resource_accounting"]
    assert resources["wall_clock_s"] > 0.0
    assert resources["cpu_time_s"] >= 0.0
    assert resources["max_rss_kib"] > 0
    assert len(data["measured_commands"]) == 2
    assert all(item["resources"]["wall_clock_s"] > 0.0 for item in data["measured_commands"])

    manifest = load_manifest()
    assert manifest["status"] == "complete"
    assert manifest["run_id"] == "task072-measured-native-adaptive-pilot"
    assert data["run_manifest"]["sha256"] == sha(RUN_DIR / "manifest.json")
    assert manifest["fingerprints_sha256"] == data["run_manifest"]["fingerprints_sha256"]
    assert manifest["resume"]["complete_checkpoint_count"] == len(manifest["segments"]) == data["run_manifest"]["segment_count"]
    assert data["run_manifest"]["checkpoint_count"] == len(manifest["segments"])
    for segment in manifest["segments"]:
        checkpoint = RUN_DIR / segment["checkpoint_path"]
        assert checkpoint.is_file()
        assert segment["checkpoint_complete"] is True
        assert segment["checkpoint_sha256"] == sha(checkpoint)
        payload = json.loads(checkpoint.read_text())
        assert payload["fingerprints_sha256"] == manifest["fingerprints_sha256"]
        assert payload["segment_sha256"]
    identity = data["source_build_checkpoint_identity"]
    assert identity["executable_identity"]["sha256"]
    assert identity["build_identity"]["compiled_source_fingerprint_sha256"]
    assert "validates schema" in identity["stale_checkpoint_policy"]


def test_task072_production_events_preserve_unresolved_gaps_without_interpolation() -> None:
    events = json.loads(EVENTS.read_text())["continuation_events"]
    assert len(events) == 31
    accepted = [event for event in events if event["validity"]["status"] == "accepted"]
    unresolved = [event for event in events if event["validity"]["status"] == "resolution_unresolved"]
    assert len(accepted) == 0
    assert len(unresolved) == 31
    assert all(event["validity"]["source"] == "unresolved_native_adaptive" for event in unresolved)
    assert all(event["validity"]["authoritative"] is False for event in unresolved)
    assert all(event["validity"].get("reason") for event in unresolved)
    assert all(event["validity"]["status"] != "interpolated" for event in events)
    assert all(event["validity"]["source"] != "interpolated_holdout_validated" for event in events)
    assert all("interpolation" not in event for event in events)


def test_task072_documentation_links_outputs_and_commands() -> None:
    text = DOC.read_text()
    for required in (
        "native_adaptive_measured_pilot.json",
        "native_adaptive_measured_pilot_events.json",
        "native_adaptive_measured_pilot_run_metadata.json",
        "generate_native_adaptive_measured_pilot.py --check",
        "resolution_unresolved",
        "No interpolation",
    ):
        assert required in text
    readme = README.read_text()
    assert "task072-measured-native-adaptive-pilot.md" in readme
    assert "native_adaptive_measured_pilot.json" in readme
