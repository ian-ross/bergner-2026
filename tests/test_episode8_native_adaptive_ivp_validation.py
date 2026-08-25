from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SCRIPTS = EPISODE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SUMMARY = EPISODE / "outputs/native_adaptive_ivp_validation.json"
GENERATOR = SCRIPTS / "generate_native_adaptive_ivp_validation.py"
DOC = EPISODE / "docs/task078-stratified-ivp-validation.md"
README = EPISODE / "README.md"
POINTS = EPISODE / "outputs/native_adaptive_full_domain_points.json"
EVENTS = EPISODE / "outputs/native_adaptive_full_domain_events.json"
ORBIT_MANIFEST = EPISODE / "outputs/native_adaptive_full_domain_orbit_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(SUMMARY.read_text())


def test_task078_generator_is_current_and_upstream_artifacts_validate() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(SCRIPTS / "validate_production_artifacts.py"),
            str(POINTS),
            str(EVENTS),
            str(ORBIT_MANIFEST),
        ],
        cwd=ROOT,
        check=True,
    )


def test_task078_stratification_documents_twelve_categories_and_deduplicates_current_point() -> None:
    policy = load()["stratification_policy"]
    assert policy["version"] == "task078-production-ivp-stratification-v1"
    assert policy["documented_category_count"] == 12
    category_ids = {row["category_id"] for row in policy["category_selection"]}
    assert category_ids == {
        "qualification_point_lineage",
        "t210_lower_hopf_side",
        "t210_upper_hopf_side",
        "low_temperature_interior",
        "high_temperature_interior",
        "largest_period",
        "shortest_period",
        "worst_accepted_defect",
        "worst_floquet_trivial_multiplier",
        "worst_interpolation_holdout",
        "canonical_spine_anchor",
        "restart_remesh_boundary",
    }
    assert policy["deduplicated_selected_target_ids"] == ["spine-210K"]
    assert policy["deduplicated_selected_point_count"] == 1
    assert policy["available_category_count"] == 7
    assert policy["unavailable_category_count"] == 5
    by_category = {row["category_id"]: row for row in policy["category_selection"]}
    assert by_category["qualification_point_lineage"]["deduplicated_into_validation_set"] is True
    assert by_category["largest_period"]["selected_target_id"] == "spine-210K"
    assert by_category["shortest_period"]["selected_target_id"] == "spine-210K"
    assert by_category["worst_accepted_defect"]["selected_target_id"] == "spine-210K"
    assert by_category["worst_floquet_trivial_multiplier"]["selected_target_id"] == "spine-210K"
    for unavailable in (
        "t210_lower_hopf_side",
        "t210_upper_hopf_side",
        "low_temperature_interior",
        "high_temperature_interior",
        "worst_interpolation_holdout",
    ):
        assert by_category[unavailable]["status"] == "unavailable_explicit_gap"
        assert by_category[unavailable]["selected_target_id"] is None
    assert policy["unavailable_strata_remain_explicit_gaps"] is True


def test_task078_dop853_one_period_return_and_phase_aligned_trajectory_pass() -> None:
    data = load()
    summary = data["dop853_validation_summary"]
    assert summary == {
        "all_selected_points_have_explicit_pass_or_failure_reasons": True,
        "failed_count": 0,
        "passed_count": 1,
        "selected_point_count": 1,
    }
    row = data["dop853_validations"][0]
    assert row["target_id"] == "spine-210K"
    assert row["native_period_is_read_only_validation_target"] is True
    result = row["dop853_one_period_return_and_trajectory"]
    assert result["solver"]["method"] == "DOP853"
    assert result["success"] is True
    assert result["validation_status"] == "passed"
    assert result["failure_reasons"] == []
    assert all(result["gates"].values())
    tolerances = data["validation_tolerances"]
    assert result["period_relative_error"] <= tolerances["period_relative"]
    assert result["scaled_return_norm_at_native_period"] <= tolerances["scaled_return_norm_or_max"]
    assert result["scaled_return_max_at_native_period"] <= tolerances["scaled_return_norm_or_max"]
    assert result["phase_aligned_weighted_orbit_rms"] <= tolerances["phase_aligned_weighted_orbit"]
    assert result["phase_aligned_weighted_orbit_max"] <= tolerances["phase_aligned_weighted_orbit"]
    assert result["phase_sample_count"] == 257


def test_task078_radau_and_perturbed_equilibrium_policy_are_truthful_for_current_accepted_set() -> None:
    data = load()
    headline = data["headline_selection"]
    assert headline["requested_hardest_or_headline_count"] == 6
    assert headline["available_hardest_or_headline_target_ids"] == ["spine-210K"]
    assert headline["production_evidence_insufficient_for_six_unique_points"] is True
    radau_summary = data["radau_agreement_summary"]
    assert radau_summary == {
        "passed_count": 1,
        "production_evidence_insufficient_for_six_unique_points": True,
        "requested_headline_count": 6,
        "run_count": 1,
    }
    radau = data["radau_agreement_checks"][0]
    assert radau["target_id"] == "spine-210K"
    assert radau["radau_result"]["solver"]["method"] == "Radau"
    assert radau["agreement_gate_pass"] is True
    assert max(radau["agreement_vs_dop853"].values()) <= radau["agreement_tolerance"]
    attractor_summary = data["perturbed_equilibrium_attractor_summary"]
    assert attractor_summary["documented_minimum_unique_points"] == 4
    assert attractor_summary["available_unique_headline_points"] == 1
    assert attractor_summary["production_evidence_insufficient_for_four_unique_points"] is True
    assert attractor_summary["trial_count"] == 4
    assert attractor_summary["unique_target_ids_receiving_trials"] == ["spine-210K"]
    assert attractor_summary["failures_are_recorded_not_suppressed"] is True
    assert all(row["failure_reasons"] for row in data["perturbed_equilibrium_attractor_checks"] if not row["attractor_gate_pass"])


def test_task078_independence_policy_and_hashes_are_current() -> None:
    data = load()
    assert data["input_validation"] == {
        "accepted_only_processing": True,
        "accepted_production_target_count": 1,
        "continuation_events_schema_valid": True,
        "continuation_points_schema_valid": True,
        "orbit_manifest_schema_valid": True,
        "production_schema_version": "episode8-figure5-production-v1",
        "schema_valid_accepted_target_ids": ["spine-210K"],
    }
    assert data["independence_policy"] == {
        "native_continuation_periods_overwritten": False,
        "native_continuation_periods_tuned_by_ivp": False,
        "native_orbit_vectors_recorrected_by_ivp": False,
        "native_period_is_read_only_validation_target": True,
        "unresolved_failed_hopf_interpolated_digitized_or_qualification_only_records_promoted": False,
        "validation_can_only_record_pass_fail_or_unavailable": True,
    }
    for record in data["source_provenance"].values():
        assert sha(ROOT / record["path"]) == record["sha256"]


def test_task078_documentation_and_readme_link_artifacts_and_limits() -> None:
    doc = DOC.read_text()
    for required in (
        "native_adaptive_ivp_validation.json",
        "twelve categories",
        "DOP853 one-period return",
        "Radau agreement is run",
        "insufficient production evidence for four unique points",
        "does not tune or overwrite native continuation periods",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task078-stratified-ivp-validation.md" in readme
    assert "native_adaptive_ivp_validation.json" in readme
    assert "DOP853 one-period return and phase-aligned trajectory validation" in readme
