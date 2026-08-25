from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_near_hopf_review.json"
POLICY_RECORDS = EPISODE / "outputs/native_adaptive_near_hopf_policy_records.json"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_near_hopf_review.py"
DOC = EPISODE / "docs/task076-near-hopf-approach-policy.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_summary() -> dict:
    return json.loads(SUMMARY.read_text())


def test_task076_generator_is_current_and_policy_records_validate() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(json.loads(POLICY_RECORDS.read_text()), root=ROOT, artifact_path=POLICY_RECORDS)


def test_task076_reviews_both_t210_hopf_sides_and_documents_terminal_statuses() -> None:
    data = load_summary()
    assert data["evidence_policy"] == {
        "production_native_adaptive_records_only": True,
        "minimum_reliable_monotone_approach_points_per_side": 5,
        "fits_require_amplitude_period_coordinates_diagnostics_terminal_statuses": True,
        "quadratic_and_quartic_fits_only_if_prerequisites_met": True,
        "episode006_hopf_periods_used_only_for_fit_intercept_comparison": True,
        "digitized_paper_evidence_used_for_acceptance": False,
        "regular_orbit_values_invented_at_hopf_boundaries": False,
    }
    reviews = {review["side_id"]: review for review in data["side_reviews"]}
    assert set(reviews) == {"lower_hopf_T210K", "upper_hopf_T210K"}
    assert reviews["lower_hopf_T210K"]["boundary_rho"] == -1.0
    assert reviews["upper_hopf_T210K"]["boundary_rho"] == 1.0
    for review in reviews.values():
        assert review["temperature_K"] == 210.0
        rows = review["terminal_statuses_under_review"]
        assert len(rows) == 6
        assert rows[0]["target_id"] == "spine-210K"
        assert rows[0]["terminal_status"] == "accepted"
        assert rows[0]["native_backend_emitted_terminal_status"] is True
        assert rows[0]["period_s"] == 5718.140409482163
        assert rows[0]["amplitude"] is None
        assert all(row["terminal_status"] == "resolution_unresolved" for row in rows[1:])
        assert all(row["period_s"] is None for row in rows[1:])
        assert all(row["amplitude"] is None for row in rows)
        assert review["terminal_status_counts_under_review"] == {
            "accepted": 1,
            "failed": 0,
            "near_hopf_stop": 0,
            "resolution_unresolved": 5,
            "tripwire_stop": 0,
        }
        assert review["explicit_gap_reason"]


def test_task076_skips_fits_without_five_reliable_monotone_approach_points() -> None:
    for review in load_summary()["side_reviews"]:
        assert review["minimum_reliable_approach_points_required"] == 5
        assert review["reliable_monotone_approach_point_count"] == 0
        assert review["reliable_monotone_approach_points"] == []
        assert review["evidence_prerequisites_met"] is False
        fit = review["fit_review"]
        assert fit["fits_performed"] is False
        assert fit["quadratic_P_of_A"]["status"] == "not_evaluated"
        assert fit["quartic_P_of_A"]["status"] == "not_evaluated"
        assert fit["leave_one_out_intercept_checks"]["status"] == "not_evaluated"
        assert fit["residual_checks"]["status"] == "not_evaluated"
        assert fit["episode006_hopf_period_comparison"]["status"] == "not_evaluated"
        reference = review["episode006_hopf_reference"]
        assert reference["source_backend"] == "loca"
        assert reference["linearized_hopf_period_s"] > 0.0


def test_task076_policy_records_are_schema_valid_explicit_gaps_with_no_boundary_periods() -> None:
    data = load_summary()
    assert data["connection_gap_policy"] == {
        "reviewed_side_count": 2,
        "sides_with_connection_supported_by_fit": [],
        "sides_with_explicit_gap": ["lower_hopf_T210K", "upper_hopf_T210K"],
        "fits_performed": False,
        "policy_record_artifact": POLICY_RECORDS.relative_to(ROOT).as_posix(),
        "policy_record_artifact_sha256": sha(POLICY_RECORDS),
    }
    artifact = json.loads(POLICY_RECORDS.read_text())
    validate_production_artifact(artifact, root=ROOT, artifact_path=POLICY_RECORDS)
    records = artifact["browser_records"]
    assert len(records) == 2
    assert {record["hopf_side"] for record in records} == {"lower_hopf_T210K", "upper_hopf_T210K"}
    for record in records:
        assert record["record_role"] == "hopf_boundary_limit"
        assert record["validity"]["status"] == "gap"
        assert record["validity"]["source"] == "explicit_gap"
        assert record["validity"]["authoritative"] is False
        assert record["display_period"] == {"quantity": "display_period", "value": None, "unit": "s", "log_value": None}
        assert record["connection_policy"]["decision"] == "explicit_gap"
        assert record["connection_policy"]["regular_orbit_boundary_period_s"] is None
        assert record["connection_policy"]["regular_orbit_boundary_amplitude"] is None
        assert record["connection_policy"]["invented_regular_orbit_values_at_hopf_boundary"] is False
        rho = record["coordinates"]["rho"]["value"]
        assert rho in {-1.0, 1.0}
        assert math.isfinite(record["episode006_linearized_hopf_period_reference_s"])


def test_task076_documentation_links_artifacts_validation_and_readme() -> None:
    doc = DOC.read_text()
    for required in (
        "native_adaptive_near_hopf_review.json",
        "native_adaptive_near_hopf_policy_records.json",
        "zero reliable near-Hopf approach points",
        "performs no quadratic or quartic fits",
        "validity.status = gap",
        "generate_native_adaptive_near_hopf_review.py --check",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task076-near-hopf-approach-policy.md" in readme
    assert "native_adaptive_near_hopf_review.json" in readme


def test_task076_source_hashes_are_current() -> None:
    data = load_summary()
    for record in data["source_provenance"].values():
        assert sha(ROOT / record["path"]) == record["sha256"]
