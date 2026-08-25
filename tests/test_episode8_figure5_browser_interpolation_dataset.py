from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
ARTIFACT = EPISODE / "outputs/figure5_browser_interpolation_dataset.json"
GENERATOR = EPISODE / "scripts/generate_figure5_browser_interpolation_dataset.py"
DOC = EPISODE / "docs/task079-browser-interpolation-dataset.md"
README = EPISODE / "README.md"
FULL_DOMAIN = EPISODE / "outputs/native_adaptive_full_domain_run.json"
LINEARIZED = EPISODE / "outputs/t210_linearized_period_curve.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_task079_generator_is_current_and_schema_valid() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    validate_production_artifact(load_artifact(), root=ROOT, artifact_path=ARTIFACT)


def test_task079_records_all_display_categories_with_explicit_zero_interpolation() -> None:
    data = load_artifact()
    records = data["browser_records"]
    summary = data["dataset_summary"]
    categories = Counter(record["display_category"] for record in records)
    statuses = Counter(record["validity"]["status"] for record in records)

    assert summary["record_count"] == len(records)
    assert summary["record_category_counts"]["solved_native_nonlinear"] == 2
    assert summary["record_category_counts"]["validated_interpolated_nonlinear"] == 0
    assert summary["record_category_counts"]["gap_unresolved_native_target"] == 297
    assert summary["record_category_counts"]["hopf_limit_explicit_gap"] == 2
    assert summary["record_category_counts"]["invalid_outside_hopf_domain"] == 54
    assert summary["record_category_counts"]["linearized_equilibrium_T210K"] == 403
    assert summary["record_category_counts"]["image_derived_comparison_pending"] == 2
    assert summary["record_category_counts"]["image_derived_comparison_value"] == 0
    assert categories == Counter(summary["record_category_counts"]) - Counter({"image_derived_comparison_value": 0, "validated_interpolated_nonlinear": 0})
    assert statuses == Counter(summary["validity_status_counts"])


def test_task079_interpolation_gates_are_not_evaluated_and_do_not_cross_gaps() -> None:
    data = load_artifact()
    review = data["interpolation_review"]
    full_domain = json.loads(FULL_DOMAIN.read_text())

    assert review["quantity_interpolated_if_enabled"] == "log(nonlinear_period_s)"
    assert review["interpolation_created"] is False
    assert review["interpolated_record_count"] == 0
    assert review["accepted_native_nonlinear_source_point_count"] == 1
    assert review["along_slice_holdout"]["overall_status"] == "not_evaluated"
    assert review["withheld_slice_holdout"]["overall_status"] == "not_evaluated"
    assert review["withheld_slice_holdout"]["accepted_source_temperatures_K"] == [210.0]
    assert review["blocked_region_counts"]["resolution_unresolved_targets"] == 297
    assert review["blocked_region_counts"]["resolution_unresolved_targets"] == full_domain["terminal_target_ledger"]["terminal_status_counts"]["resolution_unresolved"]
    no_crossing = review["no_crossing_policy"]
    assert no_crossing["hopf_boundaries_crossed"] is False
    assert no_crossing["unresolved_targets_crossed"] is False
    assert no_crossing["instability_checkpoints_crossed"] is False
    assert no_crossing["tripwire_or_near_hopf_stops_crossed"] is False
    assert no_crossing["multivalued_tripwires_crossed"] is False

    stability = data["stability_and_validation_barriers"]
    assert stability["floquet_diagnostic_count"] == 1
    assert stability["ambiguous_or_unstable_target_ids"] == []
    assert stability["ivp_failure_target_ids"] == []

    assert not any(record["validity"]["status"] == "interpolated" for record in data["browser_records"])
    unresolved = [record for record in data["browser_records"] if record["display_category"] == "gap_unresolved_native_target"]
    assert unresolved
    assert all(record["display_period"]["value"] is None for record in unresolved)
    assert all("not filled by interpolation" in record["interpolation_policy"] for record in unresolved)


def test_task079_browser_records_distinguish_gap_hopf_invalid_and_pending_comparison() -> None:
    data = load_artifact()
    by_category: dict[str, list[dict]] = {}
    for record in data["browser_records"]:
        by_category.setdefault(record["display_category"], []).append(record)

    hopf = by_category["hopf_limit_explicit_gap"]
    assert {record["record_role"] for record in hopf} == {"hopf_boundary_limit"}
    assert {record["validity"]["source"] for record in hopf} == {"explicit_gap"}
    assert all(record["display_period"]["value"] is None for record in hopf)
    assert all("near_hopf_policy_record_id" in record["source_links"] for record in hopf)

    invalid = by_category["invalid_outside_hopf_domain"]
    assert invalid
    assert {record["validity"]["status"] for record in invalid} == {"invalid"}
    assert {record["validity"]["source"] for record in invalid} == {"invalid_outside_hopf_domain"}
    assert all(abs(record["coordinates"]["rho"]["value"]) > 1.0 for record in invalid)

    pending = by_category["image_derived_comparison_pending"]
    assert len(pending) == 2
    assert {record["record_role"] for record in pending} == {"external_comparison_overlay"}
    assert {record["validity"]["status"] for record in pending} == {"not_evaluated"}
    assert all(record["source_links"] == {"pending_task": "TASK-063"} for record in pending)
    assert data["image_derived_comparison_policy"]["image_derived_values_included"] is False
    assert data["image_derived_comparison_policy"]["future_overlay_source_flag"] == "external_digitized_paper_comparison"


def test_task079_lower_panel_uses_native_nonlinear_and_independent_linearized_sources() -> None:
    data = load_artifact()
    records = data["browser_records"]
    lower_nonlinear = [record for record in records if record["display_layer"] == "lower_panel_T210K_nonlinear_continuation"]
    lower_linearized = [record for record in records if record["display_layer"] == "lower_panel_T210K_linearized_curve"]
    linearized_rows = json.loads(LINEARIZED.read_text())["linearized_period_rows"]

    assert data["lower_panel_source_policy"] == {
        "nonlinear_records_source": "TASK-075 accepted native nonlinear continuation points only",
        "linearized_records_source": "TASK-074 independent T=210 K equilibrium-linearized period curve",
        "heatmap_resampling_used": False,
        "nonlinear_record_count": 1,
        "linearized_record_count": len(linearized_rows),
    }
    assert len(lower_nonlinear) == 1
    assert lower_nonlinear[0]["validity"]["source"] == "computed_native_adaptive"
    assert lower_nonlinear[0]["source_links"]["continuation_point_record_id"] == "task075-point-spine-210K"
    assert "not heatmap resampling" in lower_nonlinear[0]["lower_panel_source_policy"]

    assert len(lower_linearized) == len(linearized_rows) == 403
    assert {record["validity"]["source"] for record in lower_linearized} == {"computed_linearized_equilibrium"}
    assert all(record["coordinates"]["temperature"]["value"] == 210.0 for record in lower_linearized)
    assert all("linearized_period_record_id" in record["source_links"] for record in lower_linearized)
    assert all("not heatmap resampling" in record["lower_panel_source_policy"] for record in lower_linearized)


def test_task079_documentation_and_source_hashes_are_current() -> None:
    doc = DOC.read_text()
    for required in (
        "figure5_browser_interpolation_dataset.json",
        "no interpolated nonlinear browser values",
        "validity.status = resolution_unresolved",
        "lower panel is **not** generated by resampling",
        "TASK-063 is still To Do",
        "generate_figure5_browser_interpolation_dataset.py --check",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task079-browser-interpolation-dataset.md" in readme
    assert "figure5_browser_interpolation_dataset.json" in readme

    data = load_artifact()
    for record in data["provenance"]["source_artifacts"]:
        path = ROOT / record["path"]
        if path.is_file():
            assert sha(path) == record["sha256"]
