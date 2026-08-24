#!/usr/bin/env python3
"""Generate the TASK-073 native adaptive pilot reconciliation artifact.

This review is a gate between the measured TASK-072 pilot and any later
full-domain Figure 5 continuation.  It validates only backend-emitted TASK-072
pilot terminal statuses and records whether independent validation is available
for accepted native adaptive pilot points.  It must not promote unresolved,
fixed-mesh-only, Python-only, or interpolated evidence to accepted production
continuation data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
RESULTS = OUTPUT / "native_adaptive_pilot_reconciliation.json"

PILOT_SUMMARY = OUTPUT / "native_adaptive_measured_pilot.json"
PILOT_EVENTS = OUTPUT / "native_adaptive_measured_pilot_events.json"
PILOT_RUN_METADATA = OUTPUT / "native_adaptive_measured_pilot_run_metadata.json"
PILOT_RUN_MANIFEST = OUTPUT / "native_adaptive_measured_pilot/manifest.json"
TASK068_PYTHON_VALIDATION = OUTPUT / "native_adaptive_python_validation.json"
TASK068_PYTHON_VALIDATION_VECTORS = OUTPUT / "native_adaptive_python_validation_vectors.npz"
TASK069_REVIEW = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_SCHEMA_DOC = EPISODE / "docs/production-schemas.md"
TASK072_DOC = EPISODE / "docs/task072-measured-native-adaptive-pilot.md"
TASK073_DOC = EPISODE / "docs/task073-native-adaptive-pilot-reconciliation.md"
README = EPISODE / "README.md"
GENERATOR = Path(__file__).resolve()

SCHEMA_VERSION = "episode008-native-adaptive-pilot-reconciliation-v1"
ARTIFACT_KIND = "task073-native-adaptive-pilot-reconciliation"
ALLOWED_TERMINAL_STATUSES = ("accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed")
RETAINED_METHOD_VERSION = "external-gauss3-hr-adaptive-v1"
PILOT_METHOD_VERSION = "episode008-native-adaptive-measured-pilot-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def artifact_record(name: str, path: Path, role: str, data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if data is None and path.suffix == ".json":
        data = load_json(path)
    record: dict[str, Any] = {
        "name": name,
        "path": rel(path),
        "sha256": sha(path),
        "role": role,
    }
    if data is not None:
        record["schema_version"] = data.get("schema_version")
        record["artifact_kind"] = data.get("artifact_kind")
    return record


def status_rollup(targets: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {status: sum(target["terminal_status"] == status for target in targets) for status in ALLOWED_TERMINAL_STATUSES}
    return {
        "terminal_status_counts": counts,
        "accepted_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "accepted"],
        "unresolved_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "resolution_unresolved"],
        "failed_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "failed"],
        "near_hopf_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "near_hopf_stop"],
        "tripwire_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "tripwire_stop"],
    }


def terminal_status_review(pilot: Mapping[str, Any], events: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    ledger = pilot["terminal_target_ledger"]
    targets = list(ledger["targets"])
    event_status_by_id = {
        str(event["event_id"]).removeprefix("task072-terminal-"): event["validity"]["status"]
        for event in events["continuation_events"]
    }
    manifest_status_by_id = {
        target_id: record["terminal_status"] for target_id, record in manifest["target_status"].items()
    }
    mismatches = []
    for target in targets:
        target_id = str(target["target_id"])
        expected = target["terminal_status"]
        event_status = event_status_by_id.get(target_id)
        manifest_status = manifest_status_by_id.get(target_id)
        if event_status != expected or manifest_status != expected:
            mismatches.append({
                "target_id": target_id,
                "pilot_status": expected,
                "event_status": event_status,
                "manifest_status": manifest_status,
            })
    return {
        "source": "TASK-072 measured pilot summary, events artifact, and run manifest",
        "target_count": ledger["target_count"],
        "exactly_one_terminal_status_per_target": bool(ledger["exactly_one_terminal_status_per_target"]),
        "allowed_terminal_statuses": list(ledger["terminal_status_allowed_values"]),
        "allowed_statuses_match_task073_contract": tuple(ledger["terminal_status_allowed_values"]) == ALLOWED_TERMINAL_STATUSES,
        **status_rollup(targets),
        "all_statuses_preserved_across_pilot_events_and_manifest": not mismatches,
        "status_mismatches": mismatches,
        "all_unaccepted_targets_are_explicit_gap_records": all(
            target["terminal_status"] == "accepted" or bool(target.get("explicit_gap_record")) for target in targets
        ),
        "all_unaccepted_targets_have_blocking_reasons": all(
            target["terminal_status"] == "accepted" or bool(target.get("reason")) for target in targets
        ),
        "target_status_table": [
            {
                "target_id": target["target_id"],
                "temperature_K": target.get("temperature_K"),
                "rho": target.get("rho"),
                "target_type": target.get("target_type"),
                "terminal_status": target["terminal_status"],
                "provisional_terminal_status": target.get("provisional_terminal_status"),
                "backend_emitted_terminal_status": bool(target.get("backend_emitted_terminal_status")),
                "explicit_gap_record": bool(target.get("explicit_gap_record")),
                "reason": target.get("reason"),
            }
            for target in targets
        ],
    }


def accepted_point_validation_review(pilot: Mapping[str, Any], python_validation: Mapping[str, Any]) -> dict[str, Any]:
    accepted_targets = [target for target in pilot["terminal_target_ledger"]["targets"] if target["terminal_status"] == "accepted"]
    validation_records = {record.get("target_id") or record.get("point_id"): record for record in python_validation.get("selected_validations", [])}
    reviews = []
    blockers = []
    for target in accepted_targets:
        target_id = str(target["target_id"])
        validation = validation_records.get(target_id)
        if validation and validation.get("validation_status") == "passed":
            reviews.append({
                "target_id": target_id,
                "python_validation_status": "passed",
                "blocks_production_use": False,
                "source": "same-coordinate independent Python validation",
            })
        else:
            reason = (
                "accepted pilot target lacks same-coordinate independent Python correction in the TASK-073 input set; "
                "production use is blocked until validation passes or the target is downgraded to explicit gap evidence"
            )
            reviews.append({
                "target_id": target_id,
                "python_validation_status": "validation_unavailable",
                "blocks_production_use": True,
                "reason": reason,
            })
            blockers.append({"target_id": target_id, "reason": reason})
    post_remesh = {
        "target_id": "spine-210K",
        "pilot_terminal_status": next(
            target["terminal_status"] for target in pilot["terminal_target_ledger"]["targets"] if target["target_id"] == "spine-210K"
        ),
        "review_status": "not_accepted_validation_unavailable_blocks_production_use",
        "reason": (
            "TASK-072 records a measured native remesh/restart seam at spine-210K, but the exact restart vector lacks "
            "backend-bound independent defect and period/orbit convergence gates and is not an accepted pilot point."
        ),
    }
    return {
        "accepted_pilot_target_count": len(accepted_targets),
        "accepted_point_reviews": reviews,
        "all_accepted_points_have_python_validation_or_blocking_reason": not accepted_targets or all(
            (not review.get("blocks_production_use")) or bool(review.get("reason")) for review in reviews
        ),
        "production_use_blockers_for_accepted_points": blockers,
        "post_remesh_restart_review": post_remesh,
        "task068_python_validation_boundary": {
            "selected_point_count": python_validation["summary"]["selected_point_count"],
            "all_selected_points_pass": python_validation["summary"]["all_selected_points_pass"],
            "usable_for_task073_pilot_acceptance": False,
            "reason": (
                "TASK-068 Python validation covers provisional/fixed-mesh native points. It is retained as background evidence, "
                "but it is not same-coordinate validation of accepted TASK-072 native adaptive pilot points because TASK-072 has no accepted pilot targets."
            ),
        },
    }


def ivp_validation_review(pilot: Mapping[str, Any]) -> dict[str, Any]:
    accepted_targets = [target for target in pilot["terminal_target_ledger"]["targets"] if target["terminal_status"] == "accepted"]
    difficulty_triggers = {
        "dop853_default": [
            "accepted regular native adaptive pilot point selected by stratified coverage",
            "headline/canonical accepted point without stiffness or convergence-warning trigger",
        ],
        "radau_required": [
            "DOP853 fails, is excessively costly, or produces event-location ambiguity",
            "near-Hopf or long-period approach point",
            "persistent ringing/nonphysical-value diagnostic despite collocation gates",
            "mesh-cap stagnation or defect-passing/Gauss-failing difficulty trigger",
        ],
    }
    if not accepted_targets:
        return {
            "selection_status": "not_justified_no_accepted_native_adaptive_pilot_points",
            "selected_subset": [],
            "stratification_policy_when_available": [
                "include accepted spine anchors and signed rho slices across the covered temperature range",
                "include post-remesh accepted targets",
                "include difficult/headline/near-Hopf or tripwire-adjacent accepted points if present",
            ],
            "method_assignment": {"DOP853": [], "Radau": []},
            "difficulty_triggers": difficulty_triggers,
            "blocks_full_domain_production": True,
            "reason": "TASK-069 justifies selected IVP checks only after accepted native adaptive pilot points exist; TASK-072 accepted none.",
        }
    # Future-proof conservative selection for any later pilot revision.
    selected = []
    for target in accepted_targets:
        method = "Radau" if target.get("terminal_status") == "near_hopf_stop" or "near_hopf" in str(target.get("reason", "")) else "DOP853"
        selected.append({
            "target_id": target["target_id"],
            "temperature_K": target.get("temperature_K"),
            "rho": target.get("rho"),
            "assigned_method": method,
            "validation_status": "not_run_in_current_artifact",
            "blocks_production_use": True,
        })
    return {
        "selection_status": "selected_but_validation_not_run_current_artifact",
        "selected_subset": selected,
        "method_assignment": {
            "DOP853": [item["target_id"] for item in selected if item["assigned_method"] == "DOP853"],
            "Radau": [item["target_id"] for item in selected if item["assigned_method"] == "Radau"],
        },
        "difficulty_triggers": difficulty_triggers,
        "blocks_full_domain_production": True,
        "reason": "Accepted pilot points require one-period IVP validation before production use.",
    }


def production_gate_decision(terminal: Mapping[str, Any], accepted_validation: Mapping[str, Any], ivp: Mapping[str, Any]) -> dict[str, Any]:
    accepted_count = terminal["terminal_status_counts"]["accepted"]
    all_statuses_preserved = bool(terminal["all_statuses_preserved_across_pilot_events_and_manifest"])
    accepted_valid = bool(accepted_validation["all_accepted_points_have_python_validation_or_blocking_reason"])
    ivp_blocks = bool(ivp["blocks_full_domain_production"])
    blockers = []
    if accepted_count == 0:
        blockers.append("TASK-072 produced zero accepted native adaptive pilot targets over the 210--226 K skeleton")
    if not all_statuses_preserved:
        blockers.append("pilot summary, event artifact, and run manifest terminal statuses disagree")
    if accepted_validation["production_use_blockers_for_accepted_points"]:
        blockers.append("one or more accepted pilot points lack same-coordinate independent Python validation")
    if ivp_blocks:
        blockers.append(ivp["reason"])
    return {
        "decision": "full_domain_continuation_not_authorized",
        "full_domain_continuation_authorized": False,
        "retained_method_version": RETAINED_METHOD_VERSION,
        "pilot_method_version": PILOT_METHOD_VERSION,
        "method_version_revision_required_now": False,
        "follow_up_required_before_TASK075": True,
        "follow_up_task": "TASK-081",
        "follow_up_scope": (
            "complete backend-bound exact restart-vector defect and period/orbit convergence gates, rerun or revise the "
            "native adaptive pilot until accepted targets either pass independent Python/IVP validation or remain explicit gaps"
        ),
        "blockers": blockers,
        "rationale": (
            "The retained v1 method is not falsified by TASK-072, but the measured pilot supplies no accepted production-use "
            "native adaptive points. Full-domain continuation must not proceed from an all-unresolved pilot gate."
        ),
    }


def build() -> bytes:
    pilot = load_json(PILOT_SUMMARY)
    events = load_json(PILOT_EVENTS)
    run_metadata = load_json(PILOT_RUN_METADATA)
    manifest = load_json(PILOT_RUN_MANIFEST)
    python_validation = load_json(TASK068_PYTHON_VALIDATION)

    terminal = terminal_status_review(pilot, events, manifest)
    accepted_validation = accepted_point_validation_review(pilot, python_validation)
    ivp = ivp_validation_review(pilot)
    decision = production_gate_decision(terminal, accepted_validation, ivp)

    review = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "scope": (
            "TASK-073 gate review of the measured 210--226 K native adaptive pilot. The artifact records independent-validation "
            "coverage and full-domain production authorization without changing TASK-072 terminal statuses."
        ),
        "manifest_identity": {
            "path": rel(RESULTS),
            "generator_path": rel(GENERATOR),
            "deterministic_serialization": "canonical sorted-key JSON with trailing newline",
            "self_hash_policy": "no in-payload sha256; tests compute file hash externally",
        },
        "input_artifacts": [
            artifact_record("task072_measured_pilot_summary", PILOT_SUMMARY, "measured native adaptive pilot terminal ledger", pilot),
            artifact_record("task072_measured_pilot_events", PILOT_EVENTS, "production-v1 continuation events", events),
            artifact_record("task072_measured_pilot_run_metadata", PILOT_RUN_METADATA, "production-v1 run metadata", run_metadata),
            artifact_record("task072_measured_pilot_run_manifest", PILOT_RUN_MANIFEST, "resumable pilot run manifest", manifest),
            artifact_record("task068_python_validation", TASK068_PYTHON_VALIDATION, "background independent Python validation boundary", python_validation),
            artifact_record("task068_python_validation_vectors", TASK068_PYTHON_VALIDATION_VECTORS, "background Python-validation vector fingerprints"),
        ],
        "source_provenance": {
            "generator": artifact_record("task073_reconciliation_generator", GENERATOR, "TASK-073 reconciliation generator"),
            "task069_review": artifact_record("task069_evidence_review", TASK069_REVIEW, "TASK-069 retained-v1 and IVP/Radau trigger decisions"),
            "task070_schema_doc": artifact_record("task070_schema_doc", TASK070_SCHEMA_DOC, "production schema boundary"),
            "task072_doc": artifact_record("task072_doc", TASK072_DOC, "measured pilot documentation"),
            "task073_doc": artifact_record("task073_doc", TASK073_DOC, "pilot reconciliation documentation"),
            "episode_readme": artifact_record("episode008_readme", README, "Episode 008 documentation index"),
        },
        "truthfulness_policy": {
            "terminal_statuses_preserved_from_TASK072": True,
            "interpolation_used_to_change_terminal_statuses": False,
            "fixed_mesh_or_python_evidence_promoted_to_task072_acceptance": False,
            "digitized_paper_evidence_used_for_acceptance": False,
            "unaccepted_targets_remain_non_authoritative_gap_evidence": True,
        },
        "terminal_status_review": terminal,
        "accepted_point_validation_review": accepted_validation,
        "ivp_validation_review": ivp,
        "near_hopf_and_tripwire_review": {
            "near_hopf_count": terminal["terminal_status_counts"]["near_hopf_stop"],
            "tripwire_count": terminal["terminal_status_counts"]["tripwire_stop"],
            "near_hopf_target_ids": terminal["near_hopf_target_ids"],
            "tripwire_target_ids": terminal["tripwire_target_ids"],
            "fit_policy": "no quadratic/quartic near-Hopf fit is supported by this pilot; preserve explicit gaps until sufficient approach points exist",
        },
        "production_gate_decision": decision,
        "acceptance_criteria_review": [
            {
                "task073_ac": 1,
                "review_status": "satisfied_with_zero_accepted_points_and_blocking_policy",
                "evidence": [
                    "accepted_target_count is zero",
                    "post-remesh spine-210K remains resolution_unresolved with validation-unavailable blocker",
                    "future accepted targets require same-coordinate independent Python validation or blocking reasons",
                ],
            },
            {
                "task073_ac": 2,
                "review_status": "satisfied_not_justified_for_current_pilot",
                "evidence": [
                    "no accepted pilot points exist for a stratified IVP subset",
                    "DOP853/Radau difficulty triggers are recorded for future accepted points",
                ],
            },
            {
                "task073_ac": 3,
                "review_status": "satisfied_full_domain_not_authorized_follow_up_required",
                "evidence": [decision["decision"], decision["rationale"]],
            },
            {
                "task073_ac": 4,
                "review_status": "satisfied_terminal_statuses_preserved_without_interpolation",
                "evidence": [
                    f"status counts: {terminal['terminal_status_counts']}",
                    "target status table preserves TASK-072 terminal statuses",
                    "interpolation and digitized-paper evidence are not used for acceptance",
                ],
            },
        ],
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_events.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_run_metadata.json",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_reconciliation.py --check",
            ],
            "focused_tests": [
                "uv run pytest tests/test_episode8_native_adaptive_pilot_reconciliation.py tests/test_episode8_native_adaptive_measured_pilot.py tests/test_episode8_production_schema.py -q",
            ],
            "full_tests": ["uv run pytest -q"],
        },
    }
    return canonical(review)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify existing output without rewriting")
    args = parser.parse_args()
    result_bytes = build()
    if args.check:
        if not RESULTS.is_file() or RESULTS.read_bytes() != result_bytes:
            raise SystemExit("native adaptive pilot reconciliation artifact is stale")
        print("verified TASK-073 native adaptive pilot reconciliation artifact")
    else:
        RESULTS.write_bytes(result_bytes)
        print(f"wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
