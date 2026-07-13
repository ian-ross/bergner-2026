from __future__ import annotations

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.stability import physical_eigenvalues, physical_jacobian

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "episodes/005-figure2-eigenvalues/scripts/run_loca_figure2_eigenvalues.py"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


def _missing_loca_toolchain_reason():
    if not TRILINOS_CONFIG.is_file():
        return f"Trilinos CMake config not found at {TRILINOS_CONFIG}"
    for tool in ("cmake", "g++"):
        if shutil.which(tool) is None:
            return f"{tool} is unavailable"
    return None


def test_episode5_loca_script_documents_backend_eigenvalue_and_diagnostic_contract():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Teuchos::LAPACK GEEV" in text
    assert "Sacado" in text
    assert "loca_figure2_branch_points.csv" in text
    assert "loca_figure2_eigenvalues.csv" in text
    assert "loca_figure2_physical_jacobian_diagnostics.csv" in text
    assert "physical Jacobian entries are kept out of the primary" in text
    assert "--points must be at least 400" in text


@lru_cache(maxsize=1)
def _run_episode5_loca_outputs(tmp_root: str) -> Path:
    reason = _missing_loca_toolchain_reason()
    if reason:
        pytest.skip(reason)
    output_dir = Path(tmp_root) / "figure2_loca_eigenvalues"
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
            "--points",
            "400",
            "--clean",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return output_dir


def test_episode5_loca_smoke_outputs_dense_backend_eigenvalue_contract(tmp_path: Path):
    output_dir = _run_episode5_loca_outputs(str(tmp_path))
    points = pd.read_csv(output_dir / "loca_figure2_branch_points.csv")
    eigenvalues = pd.read_csv(output_dir / "loca_figure2_eigenvalues.csv")
    jacobian = pd.read_csv(output_dir / "loca_figure2_physical_jacobian_diagnostics.csv")
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    summary = json.loads((output_dir / "loca_figure2_summary.json").read_text(encoding="utf-8"))

    assert len(points) == 400
    assert int(points["converged"].sum()) == 400
    assert summary["finite_converged_point_count"] == 400
    assert points["w_m_s"].min() <= 0.0005 * (1.0 + 1e-12)
    assert points["w_m_s"].max() >= 2.0 * (1.0 - 1e-12)
    assert len(eigenvalues) == 3 * len(points)
    assert len(jacobian) == len(points)
    assert set(eigenvalues["eigen_index"]) == {1, 2, 3}
    assert set(points["eigenvalue_source"]) == {"teuchos_lapack_geev"}
    assert set(points["jacobian_method"]) == {"sacado_forward_ad_physical_ode_state"}
    assert metadata["jacobian"]["primary_csv_policy"].startswith("physical Jacobian entries are kept out")
    assert "physical_jacobian_11" not in points.columns
    assert "physical_jacobian_11" in jacobian.columns

    finite_columns = [
        "n",
        "q",
        "s",
        "lambda1_real",
        "lambda1_imag",
        "lambda2_real",
        "lambda2_imag",
        "lambda3_real",
        "lambda3_imag",
    ]
    assert np.isfinite(points[finite_columns].to_numpy()).all()


def test_episode5_loca_output_jacobian_and_eigenvalues_match_python_reference(tmp_path: Path):
    output_dir = _run_episode5_loca_outputs(str(tmp_path))
    points = pd.read_csv(output_dir / "loca_figure2_branch_points.csv")
    jacobian = pd.read_csv(output_dir / "loca_figure2_physical_jacobian_diagnostics.csv")
    row = points.iloc[len(points) // 2]
    jrow = jacobian.iloc[len(jacobian) // 2]
    env = Environment(p=float(row.p_Pa), T=float(row.T_K), w=float(row.w_m_s), F=float(row.F), N_a=float(row.N_a_m3))
    state = np.array([float(row.n), float(row.q), float(row.s)], dtype=float)

    cxx_jacobian = np.array(
        [[float(jrow[f"physical_jacobian_{i}{j}"]) for j in (1, 2, 3)] for i in (1, 2, 3)],
        dtype=float,
    )
    cxx_eigenvalues = np.array(
        [complex(row[f"lambda{i}_real"], row[f"lambda{i}_imag"]) for i in (1, 2, 3)],
        dtype=complex,
    )

    np.testing.assert_allclose(cxx_jacobian, physical_jacobian(state, env=env), rtol=2e-10, atol=1e-14)
    np.testing.assert_allclose(cxx_eigenvalues, physical_eigenvalues(state, env=env), rtol=2e-8, atol=1e-10)
