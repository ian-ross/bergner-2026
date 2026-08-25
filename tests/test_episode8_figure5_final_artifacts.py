from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
GENERATOR = EPISODE / "scripts/generate_figure5_final_artifacts.py"
FINAL_BROWSER = EPISODE / "outputs/figure5_final_browser_dataset.json"
FINAL_COMPARISON = EPISODE / "outputs/figure5_final_paper_comparison.json"
FINAL_PLOT = EPISODE / "outputs/figure5_final_reproduction.png"
TASK079_BROWSER = EPISODE / "outputs/figure5_browser_interpolation_dataset.json"
DOC = EPISODE / "docs/task080-final-figure5-artifacts.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_browser() -> dict:
    return json.loads(FINAL_BROWSER.read_text())


def load_comparison() -> dict:
    return json.loads(FINAL_COMPARISON.read_text())


def test_task080_generator_outputs_are_current_and_schema_valid() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(load_browser(), root=ROOT, artifact_path=FINAL_BROWSER)
    assert FINAL_PLOT.is_file()
    assert FINAL_PLOT.stat().st_size > 100_000


def test_task080_final_browser_dataset_has_expected_provenance_categories() -> None:
    data = load_browser()
    task079 = json.loads(TASK079_BROWSER.read_text())
    summary = data["dataset_summary"]
    records = data["browser_records"]
    categories = Counter(record["display_category"] for record in records)
    statuses = Counter(record["validity"]["status"] for record in records)

    assert summary["record_count"] == len(records) == 1940
    assert summary["record_category_counts"] == dict(sorted(categories.items()))
    assert summary["validity_status_counts"] == dict(sorted(statuses.items()))
    assert summary["record_category_counts"]["solved_native_nonlinear"] == 2
    assert summary["record_category_counts"]["gap_unresolved_native_target"] == 297
    assert summary["record_category_counts"]["invalid_outside_hopf_domain"] == 54
    assert summary["record_category_counts"]["linearized_equilibrium_T210K"] == 403
    assert summary["record_category_counts"]["image_derived_comparison_value_upper_period_map"] == 690
    assert summary["record_category_counts"]["image_derived_comparison_value_lower_equilibrium_linearized_period_red_curve"] == 365
    assert summary["record_category_counts"]["image_derived_comparison_value_lower_nonlinear_limitcycle_period_black_curve"] == 127
    assert "image_derived_comparison_pending" not in summary["record_category_counts"]
    assert summary["interpolated_nonlinear_record_count"] == 0
    assert data["upstream_interpolation_review"] == task079["interpolation_review"]


def test_task080_paper_records_are_external_non_authoritative_with_uncertainty() -> None:
    data = load_browser()
    paper = [record for record in data["browser_records"] if record["validity"]["status"] == "external_comparison"]
    assert len(paper) == data["dataset_summary"]["external_comparison_record_count"] == 1182
    assert {record["validity"]["source"] for record in paper} == {"external_digitized_paper_comparison"}
    assert all(record["validity"]["authoritative"] is False for record in paper)
    assert all(record["record_role"] == "external_comparison_overlay" for record in paper)
    assert all(record["display_period"]["value"] > 0 for record in paper)
    assert all("uncertainty" in record for record in paper)
    assert all("cannot override numerical convergence" in record["comparison_policy"] for record in paper)
    assert data["image_derived_comparison_policy"]["agreement_with_digitized_pixels_can_override_numerical_validation"] is False


def test_task080_lower_panel_source_separation_and_no_episode007_coupling() -> None:
    data = load_browser()
    records = data["browser_records"]
    lower_nonlinear = [record for record in records if record["display_layer"] == "lower_panel_T210K_nonlinear_continuation"]
    lower_linearized = [record for record in records if record["display_layer"] == "lower_panel_T210K_linearized_curve"]
    paper_lower = [record for record in records if record["display_layer"] == "external_digitized_paper_lower_T210K_slice"]

    assert len(lower_nonlinear) == 1
    assert len(lower_linearized) == 403
    assert len(paper_lower) == 492
    assert lower_nonlinear[0]["validity"]["source"] == "computed_native_adaptive"
    assert {record["validity"]["source"] for record in lower_linearized} == {"computed_linearized_equilibrium"}
    assert {record["validity"]["source"] for record in paper_lower} == {"external_digitized_paper_comparison"}
    assert data["lower_panel_source_policy"]["heatmap_resampling_used"] is False
    assert data["source_separation_policy"] == {
        "episode007_widget_integration_code_used": False,
        "browser_artifact_role": "data-only JSON payload for future browser use",
        "digitized_paper_records_authoritative": False,
        "heatmap_resampling_used_for_lower_panel": False,
    }
    assert "Episode 007 widget code are excluded" in data["dataset_summary"]["compact_browser_payload_policy"]


def test_task080_paper_comparison_report_uses_subordinate_discrepancy_rule() -> None:
    report = load_comparison()
    assert report["schema_version"] == "episode008-figure5-paper-comparison-report-v1"
    rule = report["discrepancy_rule"]
    assert "max(3*sigma_digitized_log_period_natural, 0.02)" in rule["rule"]
    assert rule["agreement_can_override_numerical_convergence_or_ivp_validation"] is False
    assert rule["discrepancy_action"].startswith("investigate and document")

    pairwise = {item["comparison_layer"]: item for item in report["pairwise_comparisons"]}
    assert pairwise["upper_period_map"]["status"] == "discrepancy_requires_investigation"
    assert pairwise["upper_period_map"]["override_numerical_validation"] is False
    assert pairwise["lower_T210K_nonlinear_slice"]["status"] == "within_digitization_uncertainty"
    assert pairwise["lower_T210K_nonlinear_slice"]["override_numerical_validation"] is False

    linearized = report["linearized_curve_summary"]
    assert linearized["paper_row_count_compared_to_nearest_authoritative_row"] == 365
    assert linearized["status_counts"]["discrepancy_requires_investigation"] > 0
    assert linearized["status_counts"]["within_digitization_uncertainty"] > 0
    assert report["scientific_outcome"] == {
        "accepted_native_nonlinear_points": 1,
        "floquet_ambiguous_or_unstable_targets": [],
        "interpolated_nonlinear_points": 0,
        "ivp_failures": [],
        "unresolved_native_targets": 297,
    }


def test_task080_docs_and_hashes_are_current() -> None:
    doc = DOC.read_text()
    for required in (
        "figure5_final_reproduction.png",
        "figure5_final_browser_dataset.json",
        "external_digitized_paper_comparison",
        "abs(delta_log_period_natural)",
        "Episode 007 widget integration code",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task080-final-figure5-artifacts.md" in readme
    assert "figure5_final_browser_dataset.json" in readme

    data = load_browser()
    for record in data["provenance"]["source_artifacts"]:
        path = ROOT / record["path"]
        assert path.is_file()
        assert sha(path) == record["sha256"]
    for record in load_comparison()["provenance"]["source_artifacts"]:
        path = ROOT / record["path"]
        assert path.is_file()
        assert sha(path) == record["sha256"]
