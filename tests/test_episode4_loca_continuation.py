import csv
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/run_loca_figure1.py"
COMPARE_SCRIPT = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/compare_loca_figure1.py"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
EXPECTED_SCHEMA_PREFIX = [
    "backend",
    "schema_version",
    "branch_id",
    "T_K",
    "temperature_K",
    "p_Pa",
    "pressure_Pa",
    "F",
    "N_a_m3",
    "log_w",
    "w_m_s",
    "log_n",
    "log_q",
    "n",
    "n_kg_dry_air_inv",
    "q",
    "q_kg_kg",
    "s",
    "residual_norm",
    "converged",
    "stability",
    "backend_step_index",
    "source_file",
]


def _missing_loca_toolchain_reason():
    if not TRILINOS_CONFIG.is_file():
        return f"Trilinos CMake config not found at {TRILINOS_CONFIG}"
    for tool in ("cmake", "g++"):
        if shutil.which(tool) is None:
            return f"{tool} is unavailable"
    return None


def _load_compare_module():
    spec = importlib.util.spec_from_file_location("compare_loca_figure1", COMPARE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_episode4_loca_script_documents_required_build_run_and_normalization_contract():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "_build_executable" in text
    assert "equilibrium(env)" in text
    assert "continue" in text
    assert "branch_T{int(T)}K.csv" in text
    assert "branches_all.csv" in text
    assert "run_metadata.json" in text
    assert "run_diagnostics.json" in text
    assert "loca" in text


def test_episode4_loca_comparison_script_documents_backend_inputs_and_outputs():
    text = COMPARE_SCRIPT.read_text(encoding="utf-8")
    assert "DEFAULT_LOCA_DIR" in text
    assert "DEFAULT_AUTO_DIR" in text
    assert "DEFAULT_PYTHON_DIR" in text
    assert "loca_vs_python_continuation" in text
    assert "loca_vs_auto_continuation" in text
    assert "loca_vs_eq92_94" in text
    assert "loca_vs_python_root_solve" in text
    assert "loca_vs_digitized_figure1" in text
    assert "figure1_backend_comparison.png" in text
    assert "figure1_backend_residuals.png" in text


def test_episode4_loca_comparison_interpolates_positive_variables_in_log_space():
    module = _load_compare_module()
    branch = pd.DataFrame(
        {
            "log_w": [math.log(0.01), math.log(1.0)],
            "n": [1.0e2, 1.0e6],
            "q": [1.0e-8, 1.0e-4],
            "s": [1.4, 1.6],
        }
    )

    midpoint = [(math.log(0.01) + math.log(1.0)) / 2.0]

    assert module._interp_branch_at_log_w(branch, "n", midpoint)[0] == pytest.approx(1.0e4)
    assert module._interp_branch_at_log_w(branch, "q", midpoint)[0] == pytest.approx(1.0e-6)
    assert module._interp_branch_at_log_w(branch, "s", midpoint)[0] == pytest.approx(1.5)


def _minimal_comparison_inputs():
    log_ws = [math.log(0.01), math.log(0.1), math.log(1.0)]
    base = {
        "T_K": [190.0, 190.0, 190.0],
        "log_w": log_ws,
        "w_m_s": [math.exp(x) for x in log_ws],
        "n": [100.0, 1000.0, 10000.0],
        "q": [1.0e-8, 1.0e-7, 1.0e-6],
        "s": [1.45, 1.50, 1.55],
        "residual_norm": [1.0e-10, 2.0e-10, 3.0e-10],
        "N_a_m3": [1.0e10, 1.0e10, 1.0e10],
    }
    loca = pd.DataFrame(base)
    python = pd.DataFrame({**base, "n": [101.0, 1001.0, 10001.0]})
    auto = pd.DataFrame({**base, "q": [1.1e-8, 1.1e-7, 1.1e-6]})
    checks = pd.DataFrame(
        {
            "T_K": [190.0],
            "source": ["root_solve"],
            "log_w": [log_ws[1]],
            "w_m_s": [math.exp(log_ws[1])],
            "n_check": [999.0],
            "q_check": [1.1e-7],
            "s_check": [1.49],
            "check_converged": [True],
            "check_residual_norm": [1.0e-12],
        }
    )
    digitized = pd.DataFrame(
        {
            "panel": ["number_concentration", "mass_concentration", "saturation_ratio"],
            "T_K": [190, 190, 190],
            "w_m_s": [0.1, 0.1, 0.1],
            "value": [1000.0, 1.0e-7, 1.5],
        }
    )
    return loca, auto, python, checks, digitized


def test_episode4_loca_comparison_frames_cover_python_auto_eq_root_and_digitized_sources():
    module = _load_compare_module()
    loca, auto, python, checks, digitized = _minimal_comparison_inputs()

    details, summary, analytic = module._comparison_frames(loca, auto, python, checks, digitized)

    assert not analytic.empty
    assert set(details["comparison"]) == {
        "loca_vs_python_continuation",
        "loca_vs_auto_continuation",
        "loca_vs_eq92_94",
        "loca_vs_python_root_solve",
        "loca_vs_digitized_figure1",
    }
    assert {"n", "q", "s"}.issubset(set(details["variable"]))
    assert set(summary["comparison"]) == set(details["comparison"])


def test_episode4_loca_comparison_cli_writes_expected_artifacts(tmp_path):
    loca, auto, python, checks, digitized = _minimal_comparison_inputs()
    loca_dir = tmp_path / "loca"
    auto_dir = tmp_path / "auto"
    python_dir = tmp_path / "python"
    digitized_dir = tmp_path / "digitized"
    output_dir = tmp_path / "comparison"
    for directory in (loca_dir, auto_dir, python_dir, digitized_dir):
        directory.mkdir()
    loca.to_csv(loca_dir / "branches_all.csv", index=False)
    auto.to_csv(auto_dir / "branches_all.csv", index=False)
    python.to_csv(python_dir / "branches_all.csv", index=False)
    checks.to_csv(python_dir / "comparison_details.csv", index=False)
    digitized.to_csv(digitized_dir / "figure1_digitized_curves.csv", index=False)

    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(COMPARE_SCRIPT),
            "--loca-dir",
            str(loca_dir),
            "--auto-dir",
            str(auto_dir),
            "--python-dir",
            str(python_dir),
            "--digitized-dir",
            str(digitized_dir),
            "--output-dir",
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    expected = {
        "backend_comparison_details.csv",
        "backend_comparison_summary.csv",
        "backend_comparison_summary.json",
        "figure1_backend_comparison.png",
        "figure1_backend_residuals.png",
        "run_metadata.json",
    }
    assert expected.issubset({path.name for path in output_dir.iterdir()})
    details = pd.read_csv(output_dir / "backend_comparison_details.csv")
    assert "loca_value" in details.columns
    assert set(details["comparison"]) == {
        "loca_vs_python_continuation",
        "loca_vs_auto_continuation",
        "loca_vs_eq92_94",
        "loca_vs_python_root_solve",
        "loca_vs_digitized_figure1",
    }


@lru_cache(maxsize=1)
def _run_episode4_outputs(tmp_root):
    reason = _missing_loca_toolchain_reason()
    if reason:
        pytest.skip(reason)
    output_dir = Path(tmp_root) / "figure1_loca_branches"
    build_dir = Path(tmp_root) / "loca-build"
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(SCRIPT),
            "--output-dir",
            str(output_dir),
            "--build-dir",
            str(build_dir),
            "--steps",
            "12",
            "--clean",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return output_dir


def test_episode4_loca_orchestration_writes_normalized_branch_outputs(tmp_path):
    output_dir = _run_episode4_outputs(str(tmp_path))
    expected_files = {
        "branch_T190K.csv",
        "branch_T210K.csv",
        "branch_T230K.csv",
        "branches_all.csv",
        "run_metadata.json",
        "run_diagnostics.json",
    }
    assert expected_files.issubset({path.name for path in output_dir.iterdir()})

    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((output_dir / "run_diagnostics.json").read_text(encoding="utf-8"))
    assert metadata["schema_version"] == "figure1-branch-schema-v1"
    assert metadata["normalized_schema_columns"][: len(EXPECTED_SCHEMA_PREFIX)] == EXPECTED_SCHEMA_PREFIX
    assert "tool_versions" in metadata and "build_commands" in metadata
    assert all(run["ok"] for run in diagnostics["runs"])


def test_episode4_loca_normalized_csv_schema_and_diagnostics_are_valid(tmp_path):
    output_dir = _run_episode4_outputs(str(tmp_path))
    combined_rows = []
    for temperature in (190, 210, 230):
        branch_path = output_dir / f"branch_T{temperature}K.csv"
        with branch_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames[: len(EXPECTED_SCHEMA_PREFIX)] == EXPECTED_SCHEMA_PREFIX
            assert {"loca_newton_iterations", "loca_continuation_status", "loca_step_size", "loca_continuation_mode"}.issubset(reader.fieldnames)
            rows = list(reader)
        assert rows
        combined_rows.extend(rows)
        log_ws = np.array([float(row["log_w"]) for row in rows])
        assert log_ws.min() <= np.log(0.005) + 5e-10
        assert log_ws.max() >= np.log(2.0) - 5e-10
        assert all(row["backend"] == "loca" for row in rows)
        assert all(row["branch_id"] == f"figure1_T{temperature}K" for row in rows)
        assert all(float(row["n"]) > 0.0 and float(row["q"]) > 0.0 for row in rows)
        assert all(np.isfinite(float(row["residual_norm"])) for row in rows)
        assert all(row["converged"].lower() == "true" for row in rows)
        assert all(row["loca_continuation_mode"] == "natural_parameter_predictor_corrector" for row in rows)

    with (output_dir / "branches_all.csv").open("r", encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    assert len(all_rows) == len(combined_rows)
