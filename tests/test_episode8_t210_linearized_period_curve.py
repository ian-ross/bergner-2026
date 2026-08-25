from __future__ import annotations

import copy
import csv
import json
import math
import subprocess
from pathlib import Path

import pytest

from bergner_spichtinger_2026.episode8_production_schema import validate_production_artifact

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
ARTIFACT = EPISODE / "outputs/t210_linearized_period_curve.json"
GENERATOR = EPISODE / "scripts/generate_t210_linearized_period_curve.py"
EPISODE006_LOCA_HOPF = (
    ROOT
    / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
)
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_loca_model"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text())


def episode006_t210_anchors() -> dict[str, dict[str, float]]:
    with EPISODE006_LOCA_HOPF.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if math.isclose(float(row["T_K"]), 210.0, abs_tol=1e-12)]
    return {
        row["branch_id"]: {
            "log_w": float(row["log_w"]),
            "w": float(row["w_m_s"]),
            "frequency": abs(float(row["eigenvalue_imag"])),
        }
        for row in rows
    }


def test_t210_linearized_period_artifact_passes_production_schema() -> None:
    validate_production_artifact(load_artifact(), root=ROOT)


def test_t210_linearized_period_generator_check_is_current_when_native_executable_exists() -> None:
    if not DEFAULT_EXECUTABLE.is_file():
        pytest.skip("native C++ bs2026_loca_model executable is not built")
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_t210_linearized_period_rows_cover_initial_grid_and_exact_episode006_hopf_anchors() -> None:
    data = load_artifact()
    rows = data["linearized_period_rows"]
    summary = data["summary"]
    anchors = episode006_t210_anchors()
    assert summary["initial_grid_points"] == 401
    assert summary["total_rows"] == 403
    assert summary["gap_or_invalid_rows"] == 0
    assert {anchor["branch_id"] for anchor in summary["exact_hopf_anchors"]} == {"lower_hopf", "upper_hopf"}

    anchor_rows = {row["sampling"]["anchor_branch_id"]: row for row in rows if row["sampling"]["anchor_branch_id"]}
    assert set(anchor_rows) == {"lower_hopf", "upper_hopf"}
    for branch_id, row in anchor_rows.items():
        expected = anchors[branch_id]
        assert row["sampling"]["sample_source"] == "episode006_exact_hopf_anchor"
        assert row["coordinates"]["temperature"]["value"] == 210.0
        assert row["coordinates"]["log_w"]["value"] == pytest.approx(expected["log_w"], abs=1e-12)
        assert row["coordinates"]["w"]["value"] == pytest.approx(expected["w"], rel=1e-12)
        assert row["eigenvalue_imaginary_part"]["value"] == pytest.approx(expected["frequency"], rel=1e-8)


def test_t210_linearized_period_formula_continuity_and_no_clipping_policy() -> None:
    data = load_artifact()
    rows = data["linearized_period_rows"]
    assert data["summary"]["period_clipping_policy"] == "never_clip_or_invent_finite_periods"
    assert data["summary"]["period_max_s"] > 10_000.0

    overlaps = []
    log_ws = []
    for row in rows:
        log_ws.append(row["coordinates"]["log_w"]["value"])
        assert row["sampling"]["period_clipped_to_plot_range"] is False
        if row["validity"]["status"] == "accepted":
            frequency = row["eigenvalue_imaginary_part"]["value"]
            assert row["period"]["value"] == pytest.approx(2.0 * math.pi / frequency, rel=1e-12)
            overlap = row["eigenpair_continuity"]["eigenvector_overlap_from_previous"]
            if overlap is not None:
                overlaps.append(overlap)
        else:
            assert row["validity"]["reason"]
            assert row["period"]["value"] is None
            assert row["eigenvalue_imaginary_part"]["value"] is None
    assert log_ws == sorted(log_ws)
    assert min(overlaps) > 0.999999


def test_t210_linearized_period_holdout_and_python_parity_pass() -> None:
    data = load_artifact()
    holdout = data["sampling_refinement"]["holdout"]
    parity = data["validation"]["python_physical_jacobian_parity"]
    hopf = data["validation"]["episode006_hopf_frequency_checks"]
    assert holdout["status"] == "passed"
    assert holdout["max_abs_log_period_error"] <= holdout["tolerance"] == pytest.approx(2e-3)
    assert parity["passed"] is True
    assert parity["sample_count"] >= 12
    assert parity["max_jacobian_relative_error"] <= parity["rtol"]
    assert parity["max_eigen_imag_relative_error"] <= parity["rtol"]
    assert hopf["passed"] is True
    assert {check["branch_id"] for check in hopf["checks"]} == {"lower_hopf", "upper_hopf"}


def test_linearized_period_schema_accepts_explicit_gap_rows_without_finite_periods() -> None:
    data = load_artifact()
    gap_artifact = copy.deepcopy(data)
    row = gap_artifact["linearized_period_rows"][0]
    row["validity"] = {
        "status": "gap",
        "source": "explicit_gap",
        "authoritative": False,
        "reason": "pytest synthetic real_pair gap",
    }
    row["period"]["value"] = None
    row["period"]["log_value"] = None
    row["eigenvalue_imaginary_part"]["value"] = None
    validate_production_artifact(gap_artifact, root=ROOT)
