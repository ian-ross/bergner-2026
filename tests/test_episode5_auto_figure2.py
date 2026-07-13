from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "005-figure2-eigenvalues" / "scripts" / "run_auto_figure2_eigenvalues.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_auto_figure2_eigenvalues", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_episode5_auto_templates_use_shared_model_core_and_figure2_range():
    module = _load_script_module()
    rendered = module._render_problem()
    constants = module._render_constants()

    assert "use bs2026_model, only: environment_t, equilibrium_residual" in rendered
    assert "include 'bs2026_constants.f90'" in rendered
    assert "include 'bs2026_model.f90'" in rendered
    assert "call equilibrium_residual(log_state, PAR(1), env, residual, status)" in rendered
    assert "ICP =  [1]" in constants
    assert f"{math.log(0.0005):.17e}" in constants
    assert f"{math.log(2.0):.17e}" in constants


def test_episode5_auto_eigenvalue_records_label_python_postprocessing_fallback():
    module = _load_script_module()
    rows = [module.AutoRow(1, -1, 9, 1, module.LOG_W_MIN, 0.0, 5.14681049, -17.18141262, 1.43556141)]

    eigenvalues = module._eigenvalue_records(rows, run_name="bs2026_figure2_T230K")
    points = module.make_point_table(eigenvalues)

    required = {
        "backend",
        "branch_id",
        "n",
        "q",
        "s",
        "continuation_residual_norm",
        "physical_residual_norm",
        "scaled_physical_residual_norm",
        "converged",
        "eigenvalue_real",
        "eigenvalue_imag",
        "eigenvalue_regime",
        "stability_classification",
        "jacobian_coordinate_system",
        "eigenvalue_source",
        "auto_branch",
        "auto_point",
        "auto_type_code",
        "auto_label",
        "auto_l2_norm",
    }
    assert required.issubset(eigenvalues.columns)
    assert len(eigenvalues) == 3
    assert set(eigenvalues["eigen_index"]) == {1, 2, 3}
    assert set(eigenvalues["eigenvalue_source"]) == {module.EIGENVALUE_SOURCE}
    assert "postprocessed_from_auto_equilibria" in module.EIGENVALUE_SOURCE
    assert points.loc[0, "backend"] == "auto"
    assert points.loc[0, "w_m_s"] == pytest.approx(module.W_MIN)
    assert np.isfinite(points[["lambda1_real", "lambda1_imag", "lambda2_real", "lambda2_imag", "lambda3_real", "lambda3_imag"]].to_numpy()).all()


def test_episode5_auto_diagnostics_cover_requested_range_and_warn_sparse_branch():
    module = _load_script_module()
    rows = [
        module.AutoRow(1, -1, 9, 1, module.LOG_W_MIN, 0.0, 5.0, -17.0, 1.4),
        module.AutoRow(1, -2, 0, 0, 0.0, 0.0, 7.0, -14.0, 1.5),
        module.AutoRow(1, -3, -4, 2, module.LOG_W_MAX, 0.0, 8.0, -13.0, 1.6),
        module.AutoRow(1, -4, 0, 0, module.LOG_W_MAX + 1.0, 0.0, 9.0, -12.0, 1.7),
    ]

    requested = module._requested_range_rows(rows)
    diagnostics = module._diagnose(rows, "", "")

    assert [row.log_w for row in requested] == [module.LOG_W_MIN, 0.0, module.LOG_W_MAX]
    assert diagnostics["ok"] is True
    assert diagnostics["row_count"] == 3
    assert diagnostics["w_min_m_s"] == pytest.approx(module.W_MIN)
    assert diagnostics["w_max_m_s"] == pytest.approx(module.W_MAX)
    assert any(">=200" in warning for warning in diagnostics["warnings"])
    assert any("continued beyond requested" in warning for warning in diagnostics["warnings"])


def test_episode5_auto_single_run_smoke_outputs_contract(tmp_path: Path):
    if shutil.which("gfortran") is None or not Path("/usr/local/bin/auto").exists():
        pytest.skip("gfortran and AUTO-07p at /usr/local/bin/auto are required for the Episode 5 AUTO smoke run")

    module = _load_script_module()
    output_dir = tmp_path / "figure2_auto_eigenvalues"
    module.main(["--output-dir", str(output_dir)])

    eigenvalues_path = output_dir / "auto_figure2_eigenvalues.csv"
    points_path = output_dir / "auto_figure2_branch_points.csv"
    crossings_path = output_dir / "auto_figure2_hopf_landmark_comparison.csv"
    metadata_path = output_dir / "run_metadata.json"

    eigenvalues = pd.read_csv(eigenvalues_path)
    points = pd.read_csv(points_path)
    crossings = pd.read_csv(crossings_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert len(points) >= 200
    assert int(points["converged"].sum()) == len(points)
    assert points["w_m_s"].min() == pytest.approx(module.W_MIN, rel=1e-8)
    assert points["w_m_s"].max() == pytest.approx(module.W_MAX, rel=1e-8)
    assert len(eigenvalues) == 3 * len(points)
    assert set(eigenvalues["eigen_index"]) == {1, 2, 3}
    assert set(eigenvalues["eigenvalue_source"]) == {module.EIGENVALUE_SOURCE}
    assert np.isfinite(points[["n", "q", "s", "lambda1_real", "lambda1_imag", "lambda2_real", "lambda2_imag", "lambda3_real", "lambda3_imag"]].to_numpy()).all()

    observed = sorted(crossings["observed_w_m_s"].tolist())
    assert len(observed) == 2
    assert abs(observed[0] - 0.048) <= module.HOPF_LANDMARK_TOLERANCE_M_S
    assert abs(observed[1] - 0.77) <= module.HOPF_LANDMARK_TOLERANCE_M_S
    assert crossings["within_documented_tolerance"].all()

    assert metadata["parameters"]["T_K"] == module.TEMPERATURE_K
    assert metadata["runs"][0]["ok"] is True
    assert metadata["eigenvalues"]["source"] == module.EIGENVALUE_SOURCE
    assert "not AUTO-native" in metadata["eigenvalues"]["source_clarification"]
    assert metadata["auto"]["native_eigenvalue_investigation"]
