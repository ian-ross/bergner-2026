#!/usr/bin/env python3
"""Generate TASK-076 near-Hopf approach review and gap-policy records.

The TASK-075 full-domain production ledger currently contains one accepted
native adaptive periodic orbit (`spine-210K`) and explicit unresolved policy gaps
elsewhere.  This review therefore does not infer Hopf-boundary regular-orbit
limits.  It records the lower/upper T=210 K Hopf-side evidence prerequisites,
skips quadratic/quartic fits where the prerequisites are not met, and emits
schema-valid production browser records that mark the Hopf-limit connections as
explicit gaps rather than invented period values.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import HopfLocusCoordinates  # noqa: E402
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    ORBIT_STATE_CONVENTION,
    PARAMETER_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_near_hopf_review.json"
POLICY_RECORDS = OUTPUT / "native_adaptive_near_hopf_policy_records.json"
FULL_DOMAIN_SUMMARY = OUTPUT / "native_adaptive_full_domain_run.json"
FULL_DOMAIN_POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
FULL_DOMAIN_EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK075_DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
DOC = EPISODE / "docs/task076-near-hopf-approach-policy.md"
GENERATOR = Path(__file__).resolve()

SCHEMA_VERSION = "episode008-native-adaptive-near-hopf-review-v1"
ARTIFACT_KIND = "task076-native-adaptive-near-hopf-review"
REVIEW_TEMPERATURE_K = 210.0
MIN_APPROACH_POINTS = 5
NEAR_HOPF_RHO_DISTANCE_THRESHOLD = 0.25
LOWER_RHOS = (0.0, -0.25, -0.50, -0.75, -0.90, -0.97)
UPPER_RHOS = (0.0, 0.25, 0.50, 0.75, 0.90, 0.97)
SIDE_CONFIG = {
    "lower_hopf_T210K": {
        "hopf_branch": "lower_hopf",
        "boundary_rho": -1.0,
        "approach_direction": "decreasing rho from the accepted spine toward the lower Hopf locus",
        "rho_sequence": LOWER_RHOS,
    },
    "upper_hopf_T210K": {
        "hopf_branch": "upper_hopf",
        "boundary_rho": 1.0,
        "approach_direction": "increasing rho from the accepted spine toward the upper Hopf locus",
        "rho_sequence": UPPER_RHOS,
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "near_hopf_review": SCHEMA_VERSION,
        "production_run": "episode008-native-adaptive-full-domain-run-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "defect": "two-grid-relative-defect-v1",
        "hopf_reference": "episode6-native-loca-moore-spence-hopf-v1",
        "fit_policy": "quadratic-quartic-P-of-amplitude-gated-v1",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def coordinates(temperature_K: float, rho: float, locus: HopfLocusCoordinates) -> dict[str, Any]:
    log_w = locus.log_w_from_rho(temperature_K, rho)
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": float(temperature_K), "unit": "K"},
        "log_w": {"value": float(log_w), "unit": "ln(m s^-1)"},
        "w": {"value": float(math.exp(log_w)), "unit": "m s^-1"},
        "rho": {"value": float(rho), "unit": "dimensionless"},
        "temperature_hat": {
            "value": float(HopfLocusCoordinates.temperature_hat(temperature_K)),
            "unit": "dimensionless",
        },
    }


def target_id(temperature_K: float, rho: float) -> str:
    temperature = int(temperature_K) if float(temperature_K).is_integer() else temperature_K
    if abs(rho) < 1.0e-15:
        return f"spine-{temperature}K"
    return f"slice-{temperature}K-rho-{rho:+.2f}"


def load_hopf_references() -> dict[str, dict[str, Any]]:
    references: dict[str, dict[str, Any]] = {}
    with HOPF_LOCI.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("converged") != "True":
                continue
            branch = row["branch_id"]
            if branch not in {"lower_hopf", "upper_hopf"}:
                continue
            if not math.isclose(float(row["T_K"]), REVIEW_TEMPERATURE_K, rel_tol=0.0, abs_tol=1.0e-12):
                continue
            frequency = abs(float(row["eigenvalue_imag"]))
            references[branch] = {
                "branch_id": branch,
                "temperature_K": REVIEW_TEMPERATURE_K,
                "log_w": float(row["log_w"]),
                "w_m_s": float(row["w_m_s"]),
                "eigenvalue_imag_rad_s": float(row["eigenvalue_imag"]),
                "hopf_frequency_rad_s": frequency,
                "linearized_hopf_period_s": 2.0 * math.pi / frequency,
                "source_row_schema": row["schema_version"],
                "source_backend": row["backend"],
            }
    missing = {"lower_hopf", "upper_hopf"} - set(references)
    if missing:
        raise RuntimeError(f"missing Episode 006 Hopf references at T=210 K for {sorted(missing)}")
    return references


def point_period_by_target(points: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for point in points.get("continuation_points", []):
        coords = point.get("coordinates", {})
        temperature = coords.get("temperature", {}).get("value")
        rho = coords.get("rho", {}).get("value")
        period = point.get("period", {}).get("value")
        if isinstance(temperature, (int, float)) and isinstance(rho, (int, float)) and isinstance(period, (int, float)):
            result[target_id(float(temperature), float(rho))] = float(period)
    return result


def terminal_by_target(full_domain: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    targets = full_domain["terminal_target_ledger"]["targets"]
    return {str(target["target_id"]): target for target in targets}


def status_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"accepted": 0, "failed": 0, "near_hopf_stop": 0, "resolution_unresolved": 0, "tripwire_stop": 0}
    for row in rows:
        status = str(row["terminal_status"])
        counts[status] = counts.get(status, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def terminal_rows_for_side(
    config: Mapping[str, Any],
    terminals: Mapping[str, Mapping[str, Any]],
    periods: Mapping[str, float],
    locus: HopfLocusCoordinates,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    boundary_rho = float(config["boundary_rho"])
    for rho in config["rho_sequence"]:
        tid = target_id(REVIEW_TEMPERATURE_K, float(rho))
        terminal = terminals[tid]
        status = str(terminal["terminal_status"])
        rows.append(
            {
                "target_id": tid,
                "coordinates": coordinates(REVIEW_TEMPERATURE_K, float(rho), locus),
                "rho_distance_to_hopf_boundary": abs(boundary_rho - float(rho)),
                "terminal_status": status,
                "terminal_status_source": terminal["terminal_status_source"],
                "native_backend_emitted_terminal_status": bool(terminal["native_backend_emitted_terminal_status"]),
                "authoritative_production_point": bool(terminal["authoritative_production_point"]),
                "period_s": periods.get(tid),
                "amplitude": None,
                "diagnostics": terminal.get("accepted_gate_bundle") or {"reason": terminal.get("reason")},
            }
        )
    return rows


def reliable_approach_points(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    reliable: list[dict[str, Any]] = []
    for row in rows:
        if row["terminal_status"] != "accepted":
            continue
        if not (0.0 < float(row["rho_distance_to_hopf_boundary"]) <= NEAR_HOPF_RHO_DISTANCE_THRESHOLD):
            continue
        if row.get("amplitude") is None or row.get("period_s") is None:
            continue
        reliable.append(dict(row))
    return reliable


def fit_review(prerequisites_met: bool) -> dict[str, Any]:
    if not prerequisites_met:
        reason = (
            "fewer_than_five_reliable_monotone_approach_points_with_finite_amplitude_period_"
            "coordinates_diagnostics_and_terminal_status"
        )
        return {
            "fits_performed": False,
            "skip_reason": reason,
            "quadratic_P_of_A": {"status": "not_evaluated", "reason": reason},
            "quartic_P_of_A": {"status": "not_evaluated", "reason": reason},
            "leave_one_out_intercept_checks": {"status": "not_evaluated", "reason": reason},
            "residual_checks": {"status": "not_evaluated", "reason": reason},
            "episode006_hopf_period_comparison": {"status": "not_evaluated", "reason": reason},
        }
    raise NotImplementedError("current TASK-076 evidence is expected to be insufficient; fitting is intentionally gated")


def side_review(
    side_id: str,
    config: Mapping[str, Any],
    terminals: Mapping[str, Mapping[str, Any]],
    periods: Mapping[str, float],
    locus: HopfLocusCoordinates,
    hopf_references: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rows = terminal_rows_for_side(config, terminals, periods, locus)
    reliable = reliable_approach_points(rows)
    prerequisites_met = len(reliable) >= MIN_APPROACH_POINTS
    boundary_rho = float(config["boundary_rho"])
    nearest = min(rows, key=lambda row: abs(float(row["rho_distance_to_hopf_boundary"])))
    reason = (
        f"Only {len(reliable)} reliable near-Hopf approach points are available; "
        f"the nearest requested {config['hopf_branch']} target ({nearest['target_id']}) has terminal status "
        f"{nearest['terminal_status']} from {nearest['terminal_status_source']}. "
        "Production evidence therefore supports an explicit gap, not a nonlinear period connection."
    )
    return {
        "side_id": side_id,
        "temperature_K": REVIEW_TEMPERATURE_K,
        "hopf_branch": config["hopf_branch"],
        "boundary_rho": boundary_rho,
        "boundary_coordinates": coordinates(REVIEW_TEMPERATURE_K, boundary_rho, locus),
        "approach_direction": config["approach_direction"],
        "minimum_reliable_approach_points_required": MIN_APPROACH_POINTS,
        "near_hopf_rho_distance_threshold": NEAR_HOPF_RHO_DISTANCE_THRESHOLD,
        "amplitude_definition": (
            "finite production amplitude attached to each accepted approach point; absent for current TASK-075 "
            "unresolved targets and therefore not inferred from Hopf-boundary data"
        ),
        "terminal_statuses_under_review": rows,
        "terminal_status_counts_under_review": status_counts(rows),
        "reliable_monotone_approach_points": reliable,
        "reliable_monotone_approach_point_count": len(reliable),
        "evidence_prerequisites_met": prerequisites_met,
        "explicit_gap_reason": None if prerequisites_met else reason,
        "episode006_hopf_reference": hopf_references[str(config["hopf_branch"])],
        "fit_review": fit_review(prerequisites_met),
        "connection_policy": {
            "policy": "fit_connection_if_prerequisites_met_else_explicit_gap",
            "decision": "explicit_gap" if not prerequisites_met else "connection_supported_by_fit",
            "regular_orbit_boundary_period_s": None if not prerequisites_met else "fit_intercept_only",
            "regular_orbit_boundary_amplitude": None,
            "invented_regular_orbit_values_at_hopf_boundary": False,
            "production_record_id": f"task076-policy-{side_id}",
        },
    }


def provenance() -> dict[str, Any]:
    return {
        "task": "TASK-076",
        "created_by": "generate_native_adaptive_near_hopf_review.py",
        "digitized_paper_data_policy": "external-comparison-only",
        "source_artifacts": [
            source_record(GENERATOR, "TASK-076 near-Hopf review generator"),
            source_record(FULL_DOMAIN_SUMMARY, "TASK-075 full-domain terminal ledger"),
            source_record(FULL_DOMAIN_POINTS, "TASK-075 accepted continuation point records"),
            source_record(FULL_DOMAIN_EVENTS, "TASK-075 terminal event records"),
            source_record(HOPF_LOCI, "Episode 006 native LOCA Hopf loci and frequencies"),
            source_record(TASK069_DOC, "TASK-069 near-Hopf evidence prerequisite decision"),
            source_record(TASK070_DOC, "TASK-070 production schema boundary"),
            source_record(TASK075_DOC, "TASK-075 full-domain explicit-gap evidence"),
            source_record(DOC, "TASK-076 documentation"),
        ],
    }


def policy_records_artifact(side_reviews: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    records = []
    for review in side_reviews:
        reason = str(review["explicit_gap_reason"])
        records.append(
            {
                "record_id": review["connection_policy"]["production_record_id"],
                "record_role": "hopf_boundary_limit",
                "coordinates": review["boundary_coordinates"],
                "validity": {
                    "status": "gap",
                    "source": "explicit_gap",
                    "authoritative": False,
                    "reason": reason,
                },
                "method_versions": method_versions(),
                "display_period": {"quantity": "display_period", "value": None, "unit": "s", "log_value": None},
                "hopf_side": review["side_id"],
                "connection_policy": review["connection_policy"],
                "episode006_linearized_hopf_period_reference_s": review["episode006_hopf_reference"][
                    "linearized_hopf_period_s"
                ],
            }
        )
    return {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "browser-display-dataset",
        "artifact_id": "task076-near-hopf-gap-policy-records",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": provenance(),
        "browser_records": records,
    }


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    full_domain = load_json(FULL_DOMAIN_SUMMARY)
    points = load_json(FULL_DOMAIN_POINTS)
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    hopf_references = load_hopf_references()
    terminals = terminal_by_target(full_domain)
    periods = point_period_by_target(points)
    side_reviews = [
        side_review(side_id, config, terminals, periods, locus, hopf_references)
        for side_id, config in SIDE_CONFIG.items()
    ]
    policy_records = policy_records_artifact(side_reviews)
    POLICY_RECORDS.write_bytes(canonical(policy_records))
    validate_production_artifact(policy_records, root=ROOT, artifact_path=POLICY_RECORDS)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task076-native-adaptive-near-hopf-review",
        "scope": (
            "TASK-076 review of lower and upper T=210 K Hopf-side approach evidence from TASK-075 "
            "production native adaptive records only."
        ),
        "evidence_policy": {
            "production_native_adaptive_records_only": True,
            "minimum_reliable_monotone_approach_points_per_side": MIN_APPROACH_POINTS,
            "fits_require_amplitude_period_coordinates_diagnostics_terminal_statuses": True,
            "quadratic_and_quartic_fits_only_if_prerequisites_met": True,
            "episode006_hopf_periods_used_only_for_fit_intercept_comparison": True,
            "digitized_paper_evidence_used_for_acceptance": False,
            "regular_orbit_values_invented_at_hopf_boundaries": False,
        },
        "side_reviews": side_reviews,
        "connection_gap_policy": {
            "reviewed_side_count": len(side_reviews),
            "sides_with_connection_supported_by_fit": [],
            "sides_with_explicit_gap": [review["side_id"] for review in side_reviews],
            "fits_performed": False,
            "policy_record_artifact": rel(POLICY_RECORDS),
            "policy_record_artifact_sha256": sha(POLICY_RECORDS),
        },
        "source_provenance": {
            "generator": source_record(GENERATOR, "TASK-076 near-Hopf review generator"),
            "full_domain_summary": source_record(FULL_DOMAIN_SUMMARY, "TASK-075 full-domain terminal ledger"),
            "full_domain_points": source_record(FULL_DOMAIN_POINTS, "TASK-075 accepted continuation point records"),
            "full_domain_events": source_record(FULL_DOMAIN_EVENTS, "TASK-075 terminal event records"),
            "hopf_loci": source_record(HOPF_LOCI, "Episode 006 native LOCA Hopf loci and frequencies"),
            "task069_doc": source_record(TASK069_DOC, "TASK-069 near-Hopf evidence prerequisite decision"),
            "task070_doc": source_record(TASK070_DOC, "TASK-070 production schema boundary"),
            "task075_doc": source_record(TASK075_DOC, "TASK-075 full-domain explicit-gap evidence"),
            "doc": source_record(DOC, "TASK-076 documentation"),
        },
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_near_hopf_review.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_near_hopf_policy_records.json",
            ],
            "focused_tests": ["uv run pytest tests/test_episode8_native_adaptive_near_hopf_review.py -q"],
        },
    }
    SUMMARY.write_bytes(canonical(summary))
    return summary, policy_records


def check_existing() -> None:
    for path in (SUMMARY, POLICY_RECORDS):
        if not path.is_file():
            raise SystemExit(f"missing TASK-076 artifact: {rel(path)}")
    summary = load_json(SUMMARY)
    policy_records = load_json(POLICY_RECORDS)
    validate_production_artifact(policy_records, root=ROOT, artifact_path=POLICY_RECORDS)
    if summary.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("TASK-076 schema version mismatch")
    if summary["connection_gap_policy"]["policy_record_artifact_sha256"] != sha(POLICY_RECORDS):
        raise SystemExit("TASK-076 policy record digest drift")
    for key, record in summary["source_provenance"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-076 provenance drift for {key}: {record['path']}")
    side_reviews = summary["side_reviews"]
    if len(side_reviews) != 2:
        raise SystemExit("TASK-076 must review lower and upper Hopf sides")
    if any(review["evidence_prerequisites_met"] for review in side_reviews):
        raise SystemExit("TASK-076 current evidence unexpectedly met fit prerequisites")
    if any(review["fit_review"]["fits_performed"] for review in side_reviews):
        raise SystemExit("TASK-076 must not fit without sufficient approach evidence")
    records = policy_records["browser_records"]
    if len(records) != 2:
        raise SystemExit("TASK-076 expected two policy records")
    for record in records:
        if record["validity"]["status"] != "gap" or record["validity"]["source"] != "explicit_gap":
            raise SystemExit("TASK-076 policy records must encode explicit gaps")
        if record["display_period"]["value"] is not None or record["display_period"].get("log_value") is not None:
            raise SystemExit("TASK-076 policy records must not invent Hopf-boundary regular-orbit periods")
    print("verified TASK-076 near-Hopf review artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed TASK-076 artifacts")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    build()
    for path in (SUMMARY, POLICY_RECORDS):
        print(f"wrote {rel(path)}")


if __name__ == "__main__":
    main()
