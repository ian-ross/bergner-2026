from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/native_adaptive_pilot_reconciliation.json"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_pilot_reconciliation.py"
DOC = EPISODE / "docs/task073-native-adaptive-pilot-reconciliation.md"
README = EPISODE / "README.md"
DECISIONS = EPISODE / "docs/collocation-phase-decisions.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(RESULTS.read_text())


def test_task073_reconciliation_generator_is_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_task073_input_hashes_and_scope_are_current() -> None:
    data = load()
    assert data["schema_version"] == "episode008-native-adaptive-pilot-reconciliation-v1"
    assert data["artifact_kind"] == "task073-native-adaptive-pilot-reconciliation"
    assert data["manifest_identity"]["path"] == RESULTS.relative_to(ROOT).as_posix()
    names = {artifact["name"] for artifact in data["input_artifacts"]}
    assert {
        "task072_measured_pilot_summary",
        "task072_measured_pilot_events",
        "task072_measured_pilot_run_metadata",
        "task072_measured_pilot_run_manifest",
        "task068_python_validation",
    }.issubset(names)
    for artifact in data["input_artifacts"]:
        assert sha(ROOT / artifact["path"]) == artifact["sha256"]
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]


def test_task073_preserves_terminal_statuses_without_interpolation() -> None:
    data = load()
    assert data["truthfulness_policy"] == {
        "digitized_paper_evidence_used_for_acceptance": False,
        "fixed_mesh_or_python_evidence_promoted_to_task072_acceptance": False,
        "interpolation_used_to_change_terminal_statuses": False,
        "terminal_statuses_preserved_from_TASK072": True,
        "unaccepted_targets_remain_non_authoritative_gap_evidence": True,
    }
    terminal = data["terminal_status_review"]
    assert terminal["target_count"] == 31
    assert terminal["exactly_one_terminal_status_per_target"] is True
    assert terminal["allowed_statuses_match_task073_contract"] is True
    assert terminal["all_statuses_preserved_across_pilot_events_and_manifest"] is True
    assert terminal["status_mismatches"] == []
    assert terminal["terminal_status_counts"] == {
        "accepted": 0,
        "resolution_unresolved": 31,
        "near_hopf_stop": 0,
        "tripwire_stop": 0,
        "failed": 0,
    }
    assert len(terminal["target_status_table"]) == 31
    assert len(terminal["unresolved_target_ids"]) == 31
    assert terminal["accepted_target_ids"] == []
    assert terminal["failed_target_ids"] == []
    assert terminal["near_hopf_target_ids"] == []
    assert terminal["tripwire_target_ids"] == []
    assert terminal["all_unaccepted_targets_are_explicit_gap_records"] is True
    assert terminal["all_unaccepted_targets_have_blocking_reasons"] is True


def test_task073_accepted_python_validation_and_post_remesh_blocker_policy() -> None:
    review = load()["accepted_point_validation_review"]
    assert review["accepted_pilot_target_count"] == 0
    assert review["accepted_point_reviews"] == []
    assert review["production_use_blockers_for_accepted_points"] == []
    assert review["all_accepted_points_have_python_validation_or_blocking_reason"] is True
    post_remesh = review["post_remesh_restart_review"]
    assert post_remesh == {
        "target_id": "spine-210K",
        "pilot_terminal_status": "resolution_unresolved",
        "review_status": "not_accepted_validation_unavailable_blocks_production_use",
        "reason": post_remesh["reason"],
    }
    assert "exact restart vector lacks backend-bound independent defect" in post_remesh["reason"]
    boundary = review["task068_python_validation_boundary"]
    assert boundary["selected_point_count"] == 32
    assert boundary["all_selected_points_pass"] is True
    assert boundary["usable_for_task073_pilot_acceptance"] is False
    assert "not same-coordinate validation" in boundary["reason"]


def test_task073_ivp_subset_is_not_selected_without_accepted_pilot_points() -> None:
    ivp = load()["ivp_validation_review"]
    assert ivp["selection_status"] == "not_justified_no_accepted_native_adaptive_pilot_points"
    assert ivp["selected_subset"] == []
    assert ivp["method_assignment"] == {"DOP853": [], "Radau": []}
    assert ivp["blocks_full_domain_production"] is True
    assert "accepted none" in ivp["reason"]
    assert any("near-Hopf" in trigger for trigger in ivp["difficulty_triggers"]["radau_required"])
    assert any("accepted regular" in trigger for trigger in ivp["difficulty_triggers"]["dop853_default"])


def test_task073_full_domain_go_no_go_and_ac_review_are_explicit() -> None:
    data = load()
    decision = data["production_gate_decision"]
    assert decision["decision"] == "full_domain_continuation_not_authorized"
    assert decision["full_domain_continuation_authorized"] is False
    assert decision["retained_method_version"] == "external-gauss3-hr-adaptive-v1"
    assert decision["method_version_revision_required_now"] is False
    assert decision["follow_up_required_before_TASK075"] is True
    assert decision["follow_up_task"] == "TASK-081"
    assert "zero accepted" in decision["blockers"][0]
    assert "not falsified" in decision["rationale"]

    ac = data["acceptance_criteria_review"]
    assert [entry["task073_ac"] for entry in ac] == [1, 2, 3, 4]
    assert all(entry["review_status"].startswith("satisfied") for entry in ac)
    assert data["near_hopf_and_tripwire_review"]["near_hopf_count"] == 0
    assert data["near_hopf_and_tripwire_review"]["tripwire_count"] == 0
    assert "no quadratic/quartic" in data["near_hopf_and_tripwire_review"]["fit_policy"]


def test_task073_documentation_links_outputs_commands_and_decision() -> None:
    doc = DOC.read_text()
    for required in (
        "native_adaptive_pilot_reconciliation.json",
        "generate_native_adaptive_pilot_reconciliation.py --check",
        "accepted` | 0",
        "resolution_unresolved` | 31",
        "Full-domain native adaptive continuation is **not authorized**",
        "No interpolation",
        "DOP853",
        "Radau",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task073-native-adaptive-pilot-reconciliation.md" in readme
    assert "native_adaptive_pilot_reconciliation.json" in readme
    assert "Full-domain continuation is **not authorized**" in readme
    assert "TASK-081 follow-up gate work" in readme
    decisions = DECISIONS.read_text()
    assert "TASK-072/TASK-073 measured pilot gate" in decisions
    assert "full-domain production continuation is not authorized" in decisions
