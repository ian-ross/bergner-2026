from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
GENERATOR = EPISODE / "scripts/generate_paper_figure5_digitization.py"
ARTIFACT = EPISODE / "outputs/paper_figure5_digitization.json"
UPPER_BOUNDARIES = EPISODE / "outputs/paper_figure5_digitization_upper_hopf_boundaries.csv"
UPPER_SAMPLES = EPISODE / "outputs/paper_figure5_digitization_upper_period_samples.csv"
LOWER_CURVES = EPISODE / "outputs/paper_figure5_digitization_lower_curves.csv"
OVERLAY = EPISODE / "outputs/paper_figure5_digitization_overlay.png"
RESIDUALS = EPISODE / "outputs/paper_figure5_digitization_residuals.png"
DOC = EPISODE / "docs/task063-paper-figure5-digitization.md"
README = EPISODE / "README.md"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json() -> dict:
    return json.loads(ARTIFACT.read_text())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_task063_generator_outputs_are_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    data = load_json()
    assert data["schema_version"] == "episode008-paper-figure5-digitization-v1"
    assert data["artifact_kind"] == "task063-paper-figure5-digitization"
    assert data["data_role"] == "external_digitized_paper_comparison_only"
    assert data["not_authoritative_for_continuation_convergence"] is True
    assert data["source_figure"]["source_originals_modified"] is False


def test_task063_records_source_checksums_and_schema_links() -> None:
    data = load_json()
    source_records = data["provenance"]["source_artifacts"] + [data["provenance"]["generator"]]
    for record in source_records:
        path = ROOT / record["path"]
        assert path.is_file()
        assert sha(path) == record["sha256"]
        assert path.stat().st_size == record["bytes"]

    schemas = data["schemas"]
    assert schemas["upper_hopf_boundaries_csv"]["path"].endswith("upper_hopf_boundaries.csv")
    assert schemas["upper_period_samples_csv"]["source_type"].startswith("direct color samples")
    assert "no extrapolation" in schemas["lower_curves_csv"]["gap_policy"]
    assert set(data["dataset_summary"]["machine_readable_outputs"]) == {
        schemas["upper_hopf_boundaries_csv"]["path"],
        schemas["upper_period_samples_csv"]["path"],
        schemas["lower_curves_csv"]["path"],
    }


def test_task063_upper_panel_digitization_has_boundaries_and_color_samples() -> None:
    data = load_json()
    boundaries = read_csv(UPPER_BOUNDARIES)
    samples = read_csv(UPPER_SAMPLES)

    assert len(boundaries) == data["dataset_summary"]["upper_boundary_rows"] == 366
    assert len(samples) == data["dataset_summary"]["upper_period_color_samples"] == 690
    assert {row["validity"] for row in boundaries} == {"direct_edge_detected"}
    assert {row["source_type"] for row in samples} == {"direct_digitized_color_sample"}
    assert {row["value_role"] for row in samples} == {"image_colorbar_lookup_not_backend_result"}

    first = boundaries[0]
    last = boundaries[-1]
    assert 190.0 < float(first["temperature_K"]) < 191.0
    assert 239.0 < float(last["temperature_K"]) < 240.0
    for row in boundaries[::40]:
        assert float(row["upper_boundary_w_m_s"]) > float(row["lower_boundary_w_m_s"])
        assert int(row["vertical_color_run_pixels"]) > 100

    periods = [float(row["period_s"]) for row in samples]
    assert min(periods) >= 1.0e2
    assert max(periods) <= 1.0e5
    assert data["validation"]["upper_color_validity_counts"]["valid"] == len(samples)


def test_task063_lower_panel_curves_and_endpoint_policy_are_explicit() -> None:
    data = load_json()
    curves = read_csv(LOWER_CURVES)
    counts = Counter(row["curve_id"] for row in curves)

    assert counts == Counter(data["dataset_summary"]["lower_curve_counts"])
    assert counts["equilibrium_linearized_period_red_curve"] == 365
    assert counts["nonlinear_limitcycle_period_black_curve"] == 127
    assert {row["temperature_K"] for row in curves} == {"210.0"}
    assert {row["source_type"] for row in curves} == {"direct_digitized_curve_pixel"}
    assert {row["validity"] for row in curves} == {"valid_curve_pixel"}

    endpoints = data["validation"]["lower_curve_endpoints"]
    black = endpoints["nonlinear_limitcycle_period_black_curve"]
    red = endpoints["equilibrium_linearized_period_red_curve"]
    assert 0.01 < black["first_w_m_s"] < 0.02
    assert 0.2 < black["last_w_m_s"] < 0.25
    assert "no Hopf endpoint extrapolation" in black["endpoint_policy"]
    assert red["first_w_m_s"] == 0.0004999999999999999
    assert red["last_w_m_s"] > 1.9


def test_task063_validation_outputs_and_docs_are_present() -> None:
    data = load_json()
    validation = data["validation"]
    assert validation["calibration_residual_px_max_abs"] < 0.51
    assert validation["upper_colorbar_rgb_distance_p95"] < 20.0
    assert OVERLAY.is_file() and OVERLAY.stat().st_size > 100_000
    assert RESIDUALS.is_file() and RESIDUALS.stat().st_size > 1_000
    assert set(data["dataset_summary"]["validation_outputs"]) == {
        "episodes/008-figure5-periodic-orbit-continuation/outputs/paper_figure5_digitization_overlay.png",
        "episodes/008-figure5-periodic-orbit-continuation/outputs/paper_figure5_digitization_residuals.png",
    }

    doc = DOC.read_text()
    for required in (
        "paper_figure5_digitization.json",
        "direct_digitized_color_sample",
        "No interpolation rows are emitted",
        "max(3*sigma_digitized_logP, 0.02)",
        "external_digitized_paper_comparison",
    ):
        assert required in doc
    readme = README.read_text()
    assert "task063-paper-figure5-digitization.md" in readme
    assert "generate_paper_figure5_digitization.py --check" in readme
