from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_pilot_gate_followup.json"
EVENTS = EPISODE / "outputs/native_adaptive_pilot_gate_followup_events.json"
RUN_METADATA = EPISODE / "outputs/native_adaptive_pilot_gate_followup_run_metadata.json"
EXACT_FIXTURE = EPISODE / "outputs/native_adaptive_pilot_gate_followup_exact_restart_fixture.txt"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_pilot_gate_followup.py"
DOC = EPISODE / "docs/task081-native-adaptive-pilot-gate-followup.md"
README = EPISODE / "README.md"
DECISIONS = EPISODE / "docs/collocation-phase-decisions.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(SUMMARY.read_text())


def test_task081_generator_is_current_and_production_artifacts_validate() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(json.loads(EVENTS.read_text()), root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(json.loads(RUN_METADATA.read_text()), root=ROOT, artifact_path=RUN_METADATA)


def test_task081_exact_restart_vector_gate_bundle_is_backend_bound_and_passing() -> None:
    data = load()
    gate = data["exact_restart_gate_bundle"]
    assert gate["target_id"] == "spine-210K"
    assert gate["status"] == "passed"
    assert gate["all_required_gates_pass"] is True
    assert gate["gate_pass"] == {
        "defect": True,
        "finite_change": True,
        "linear_solve": True,
        "period_orbit_convergence": True,
        "phase": True,
        "positivity": True,
        "residual": True,
        "tangent": True,
    }
    native = gate["exact_native_restart_vector"]
    assert native["interval_count"] == 84
    assert native["unknown_size"] == 1009
    assert native["sha256"] == "795cd6ea64e3de0e5c47803ac98f0d3f38ab0b9fc15eab467c1e6e0ac12a85c9"
    command = gate["native_backend_defect_command"]
    assert command["command"][1] == "adaptive-controller"
    assert command["fixture_path"] == EXACT_FIXTURE.relative_to(ROOT).as_posix()
    assert command["fixture_sha256"] == sha(EXACT_FIXTURE)
    assert command["defect_maximum"] < 1e-4
    restart_command = gate["native_backend_restart_command"]
    assert restart_command["command"][1] == "adaptive-restart"
    assert restart_command["matches_exact_restart_vector"] is True
    assert restart_command["emitted_solution_sha256"] == native["sha256"]
    assert restart_command["correction_status"] == "accepted"
    assert restart_command["nox_status"] == "converged"
    assert all(restart_command["gates"].values())
    assert gate["independent_python_recomputed_defect_crosscheck"]["maximum"] < 1e-4
    convergence = gate["period_orbit_convergence"]
    assert convergence["period_relative_change_from_native_transferred_seed"] < 1e-3
    assert convergence["period_relative_change_vs_source_adaptive_final"] < 1e-3
    assert convergence["weighted_orbit_change_from_transferred_seed"] < 1e-3
    assert convergence["native_restart_correction_norm"] < 1e-3
    assert "native adaptive-restart" in convergence["backend_binding"]


def test_task081_revised_measured_pilot_preserves_unique_statuses_without_relabeling() -> None:
    data = load()
    assert data["truthfulness_policy"] == {
        "accepted_target_requires_exact_native_restart_gate_bundle": True,
        "digitized_paper_evidence_used_for_acceptance": False,
        "fixed_mesh_or_python_evidence_relabelled_as_native_adaptive_acceptance": False,
        "interpolation_used_to_fill_targets": False,
        "native_backend_emitted_every_terminal_status": True,
        "unaccepted_targets_are_explicit_unresolved_gap_records": True,
    }
    ledger = data["revised_measured_pilot"]["terminal_target_ledger"]
    assert ledger["target_count"] == 31
    assert ledger["exactly_one_terminal_status_per_target"] is True
    assert ledger["terminal_status_counts"] == {
        "accepted": 1,
        "resolution_unresolved": 30,
        "near_hopf_stop": 0,
        "tripwire_stop": 0,
        "failed": 0,
    }
    assert ledger["accepted_target_ids"] == ["spine-210K"]
    assert len(ledger["unresolved_target_ids"]) == 30
    by_id = {target["target_id"]: target for target in ledger["targets"]}
    assert by_id["spine-210K"]["terminal_status"] == "accepted"
    assert by_id["spine-210K"]["authoritative_for_task075_gate"] is True
    assert by_id["spine-210K"]["status_source"] == "task081-native-exact-restart-gate-backend"
    assert by_id["spine-210K"]["supersedes_task072_terminal_status"] == "resolution_unresolved"
    assert by_id["move-225K-to-spine-rho0"]["terminal_status"] == "resolution_unresolved"
    assert all(target["backend_emitted_terminal_status"] for target in ledger["targets"])
    assert all(target["status_source"] == "task081-native-exact-restart-gate-backend" for target in ledger["targets"])
    assert all(target["reason"] for target in ledger["targets"])


def test_task081_accepted_point_has_python_and_ivp_validation() -> None:
    validation = load()["accepted_point_validation"]
    assert validation["all_accepted_points_have_python_and_ivp_validation"] is True
    python = validation["same_coordinate_python"]
    assert python["validation_status"] == "passed"
    assert python["seed_contract"]["native_restart_vector_seeded"] is False
    assert python["period_relative_error"] < python["tolerance"]
    assert python["weighted_orbit_distance"] < python["tolerance"]
    assert all(python["gates"].values())
    ivp = validation["ivp"]
    assert ivp["selection_status"] == "selected_only_accepted_post_remesh_pilot_target"
    assert ivp["assigned_method"] == "DOP853"
    assert ivp["radau_required"] is False
    assert ivp["validation_status"] == "passed"
    assert ivp["solver_success"] is True
    assert ivp["scaled_return_norm"] < ivp["tolerance"]
    assert ivp["scaled_return_max"] < ivp["tolerance"]


def test_task081_production_events_and_go_no_go_authorize_task075() -> None:
    data = load()
    events = json.loads(EVENTS.read_text())["continuation_events"]
    accepted = [event for event in events if event["validity"]["status"] == "accepted"]
    unresolved = [event for event in events if event["validity"]["status"] == "resolution_unresolved"]
    assert len(accepted) == 1
    assert accepted[0]["event_id"] == "task081-terminal-spine-210K"
    assert accepted[0]["validity"]["source"] == "computed_native_adaptive"
    assert accepted[0]["validity"]["authoritative"] is True
    assert accepted[0]["period"]["value"] > 0.0
    assert len(unresolved) == 30
    assert all(event["validity"]["source"] == "unresolved_native_adaptive" for event in unresolved)
    assert all(event["validity"].get("reason") for event in unresolved)
    decision = data["production_gate_decision"]
    assert decision["decision"] == "task075_authorized_under_retained_v1_method"
    assert decision["task075_may_proceed"] is True
    assert decision["full_domain_continuation_authorized"] is True
    assert decision["method_version_revision_required_now"] is False
    assert decision["retained_method_version"] == "external-gauss3-hr-adaptive-v1"


def test_task081_hashes_and_documentation_links_are_current() -> None:
    data = load()
    for record in data["provenance"].values():
        assert sha(ROOT / record["path"]) == record["sha256"]
    assert data["production_schema_artifact_sha256"] == {
        "continuation_events": sha(EVENTS),
        "run_metadata": sha(RUN_METADATA),
    }
    doc = DOC.read_text()
    for required in (
        "native_adaptive_pilot_gate_followup.json",
        "native_adaptive_pilot_gate_followup_events.json",
        "generate_native_adaptive_pilot_gate_followup.py --check",
        "accepted=1",
        "resolution_unresolved=30",
        "TASK-075 may proceed",
        "DOP853",
        "No interpolation",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task081-native-adaptive-pilot-gate-followup.md" in readme
    assert "native_adaptive_pilot_gate_followup.json" in readme
    assert "TASK-075 may proceed" in readme
    decisions = DECISIONS.read_text()
    assert "TASK-081 follow-up gate" in decisions
    assert "TASK-075 may proceed" in decisions
