from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_full_domain_run.json"
POINTS = EPISODE / "outputs/native_adaptive_full_domain_points.json"
EVENTS = EPISODE / "outputs/native_adaptive_full_domain_events.json"
RUN_METADATA = EPISODE / "outputs/native_adaptive_full_domain_run_metadata.json"
ORBIT_MANIFEST = EPISODE / "outputs/native_adaptive_full_domain_orbit_manifest.json"
ORBIT_NPZ = EPISODE / "outputs/native_adaptive_full_domain_orbits.npz"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_full_domain_run.py"
DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
README = EPISODE / "README.md"
TASK081 = EPISODE / "outputs/native_adaptive_pilot_gate_followup.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_summary() -> dict:
    return json.loads(SUMMARY.read_text())


def test_task075_generator_is_current_and_production_artifacts_validate() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(json.loads(POINTS.read_text()), root=ROOT, artifact_path=POINTS)
    validate_production_artifact(json.loads(EVENTS.read_text()), root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(json.loads(RUN_METADATA.read_text()), root=ROOT, artifact_path=RUN_METADATA)
    validate_production_artifact(json.loads(ORBIT_MANIFEST.read_text()), root=ROOT, artifact_path=ORBIT_MANIFEST)


def test_task075_full_domain_manifest_covers_approved_skeleton_with_unique_statuses() -> None:
    data = load_summary()
    manifest = data["requested_target_manifest"]
    assert manifest["temperature_domain_K"] == [190.0, 240.0]
    assert manifest["temperature_spacing_policy"] == "T=190,192,...,240 K plus exact 225 K"
    assert manifest["exact_225K_anchor_included"] is True
    assert manifest["spine_points_included"] is True
    assert manifest["rho_anchors_included"] is True
    ledger = data["terminal_target_ledger"]
    assert ledger["target_count"] == 298
    assert ledger["temperature_slices_K"] == sorted([*range(190, 241, 2), 225])
    assert ledger["rho_anchors"] == [-0.97, -0.9, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 0.9, 0.97]
    assert ledger["exactly_one_terminal_status_per_target"] is True
    assert ledger["terminal_status_counts"] == {
        "accepted": 1,
        "failed": 0,
        "near_hopf_stop": 0,
        "resolution_unresolved": 297,
        "tripwire_stop": 0,
    }
    assert ledger["accepted_target_ids"] == ["spine-210K"]
    by_id = {target["target_id"]: target for target in ledger["targets"]}
    assert "move-225K-to-spine-rho0" in by_id
    assert "spine-225K" in by_id
    assert "slice-240K-rho-+0.97" in by_id
    assert "slice-190K-rho--0.97" in by_id
    assert all(target["terminal_status_recorded"] for target in ledger["targets"])
    assert by_id["spine-210K"]["native_backend_emitted_terminal_status"] is True
    assert by_id["spine-210K"]["terminal_status_source"] == "task081-native-exact-restart-gate-backend"
    assert all(
        target["terminal_status_source"] == "task075-explicit-gap-policy-after-no-authorized-native-route"
        for target in ledger["targets"]
        if target["terminal_status"] == "resolution_unresolved"
    )
    assert not any(
        target["native_backend_emitted_terminal_status"]
        for target in ledger["targets"]
        if target["terminal_status"] == "resolution_unresolved"
    )


def test_task075_accepted_point_is_task081_backed_and_passes_required_gates() -> None:
    data = load_summary()
    task081 = json.loads(TASK081.read_text())
    gate_summary = data["accepted_point_gate_summary"]
    assert gate_summary["accepted_target_count"] == 1
    assert gate_summary["all_accepted_points_pass_production_gates"] is True
    assert gate_summary["task081_exact_gate_bundle"]["all_required_gates_pass"] is True
    assert gate_summary["task081_accepted_point_validation"]["all_accepted_points_have_python_and_ivp_validation"] is True
    point = json.loads(POINTS.read_text())["continuation_points"][0]
    assert point["record_id"] == "task075-point-spine-210K"
    assert point["validity"] == {"status": "accepted", "source": "computed_native_adaptive", "authoritative": True}
    assert point["period"]["value"] == task081["exact_restart_gate_bundle"]["exact_native_restart_vector"]["period_s"]
    assert point["orbit_vector_ref"]["restart_vector_sha256"] == task081["exact_restart_gate_bundle"]["exact_native_restart_vector"]["sha256"]
    assert set(point["acceptance_gates"]) == {
        "production_residual",
        "phase",
        "positivity",
        "linear_klu2",
        "independent_defect",
        "period_orbit_convergence",
        "remesh_restart",
        "provenance",
        "restartability",
    }
    assert all(point["acceptance_gates"].values())


def test_task075_unresolved_regions_are_explicit_gaps_in_events_without_interpolation() -> None:
    data = load_summary()
    assert data["truthfulness_policy"] == {
        "accepted_target_requires_complete_gate_bundle": True,
        "digitized_paper_evidence_used_for_acceptance": False,
        "fixed_mesh_or_python_evidence_relabelled_as_native_adaptive_acceptance": False,
        "interpolation_used_to_fill_targets": False,
        "native_backend_emitted_accepted_terminal_statuses": True,
        "one_terminal_status_recorded_for_every_requested_target": True,
        "unaccepted_targets_are_explicit_unresolved_gap_records": True,
        "unresolved_statuses_are_policy_gap_records_not_native_cpp_solves": True,
    }
    events = json.loads(EVENTS.read_text())["continuation_events"]
    accepted = [event for event in events if event["validity"]["status"] == "accepted"]
    unresolved = [event for event in events if event["validity"]["status"] == "resolution_unresolved"]
    assert len(accepted) == 1
    assert accepted[0]["event_id"] == "task075-terminal-spine-210K"
    assert len(unresolved) == 297
    assert all(event["validity"]["source"] == "unresolved_native_adaptive" for event in unresolved)
    assert all(event["validity"]["authoritative"] is False for event in unresolved)
    assert all(event["validity"].get("reason") for event in unresolved)


def test_task075_sampling_refinement_records_holdout_errors_without_crossing_gaps() -> None:
    sampling = load_summary()["sampling_refinement"]
    assert sampling["accepted_point_count"] == 1
    assert sampling["holdout_gate_tolerance_abs_log_period"] == 2.0e-3
    assert sampling["interpolation_created"] is False
    assert sampling["no_crossing_policy"] == {
        "hopf_boundaries": True,
        "instability_checkpoints": True,
        "tripwires": True,
        "unresolved_gaps": True,
    }
    assert set(sampling["refinement_neighborhood_target_ids"]) == {
        "spine-208K",
        "spine-212K",
        "slice-210K-rho--0.25",
        "slice-210K-rho-+0.25",
    }
    assert sampling["refinement_neighborhood_terminal_status_counts"] == {
        "accepted": 0,
        "failed": 0,
        "near_hopf_stop": 0,
        "resolution_unresolved": 4,
        "tripwire_stop": 0,
    }
    assert len(sampling["along_slice_log_period_errors"]) == 27
    assert all(row["status"] == "not_evaluated" and row["max_abs_log_period_error"] is None for row in sampling["along_slice_log_period_errors"])
    assert len(sampling["between_slice_log_period_errors"]) == 11
    assert all(row["status"] == "not_evaluated" and row["max_abs_log_period_error"] is None for row in sampling["between_slice_log_period_errors"])


def test_task075_curated_orbit_manifest_is_restartable_and_hashes_are_current() -> None:
    data = load_summary()
    manifest = json.loads(ORBIT_MANIFEST.read_text())["orbit_vector_manifest"]
    assert manifest["npz_path"] == ORBIT_NPZ.relative_to(ROOT).as_posix()
    assert manifest["npz_sha256"] == sha(ORBIT_NPZ)
    assert manifest["accepted_point_ids"] == ["spine-210K"]
    assert manifest["restartable"] is True
    assert set(manifest["arrays"]) == {
        "spine_210K_boundaries",
        "spine_210K_unknowns",
        "spine_210K_phase_values",
        "spine_210K_phase_derivatives",
    }
    with np.load(ORBIT_NPZ, allow_pickle=False) as arrays:
        assert arrays["spine_210K_boundaries"].shape == (85,)
        assert arrays["spine_210K_unknowns"].shape == (1009,)
    for key, path in {
        "continuation_points": POINTS,
        "continuation_events": EVENTS,
        "run_metadata": RUN_METADATA,
        "curated_orbit_npz_manifest": ORBIT_MANIFEST,
        "curated_orbit_npz": ORBIT_NPZ,
    }.items():
        assert data["production_schema_artifact_sha256"][key] == sha(path)
    for record in data["source_provenance"].values():
        assert sha(ROOT / record["path"]) == record["sha256"]


def test_task075_documentation_links_artifacts_and_validation_commands() -> None:
    doc = DOC.read_text()
    for required in (
        "native_adaptive_full_domain_run.json",
        "native_adaptive_full_domain_points.json",
        "native_adaptive_full_domain_events.json",
        "native_adaptive_full_domain_orbit_manifest.json",
        "accepted=1",
        "resolution_unresolved=297",
        "generate_native_adaptive_full_domain_run.py --check",
        "No interpolation",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task075-full-domain-native-adaptive-continuation.md" in readme
    assert "native_adaptive_full_domain_run.json" in readme
    assert "Current production gates accept only `spine-210K`" in readme
