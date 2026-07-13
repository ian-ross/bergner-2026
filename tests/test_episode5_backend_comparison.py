from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "005-figure2-eigenvalues" / "scripts" / "compare_figure2_eigenvalues.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("compare_figure2_eigenvalues", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_backend_csv(path: Path, backend: str, log_w: np.ndarray, offset: float = 0.0) -> None:
    w = np.exp(log_w)
    data = {
        "backend": backend,
        "point_index": np.arange(len(log_w)),
        "log_w": log_w,
        "w_m_s": w,
        "n": 1.0 + w,
        "q": 2.0 + w,
        "s": 1.01 + 0.01 * w,
        "lambda1_real": log_w + 1.0 + offset,
        "lambda1_imag": np.full_like(log_w, 0.5),
        "lambda2_real": -2.0 - 0.1 * log_w + offset,
        "lambda2_imag": np.zeros_like(log_w),
        "lambda3_real": log_w + 1.0 + offset,
        "lambda3_imag": np.full_like(log_w, -0.5),
        "eigenvalue_regime": ["complex_pair", "three_real", "complex_pair", "complex_pair"][: len(log_w)],
        "stability_classification": ["stable", "stable", "unstable", "unstable"][: len(log_w)],
        "jacobian_method": "synthetic",
        "eigenvalue_source": f"{backend}_synthetic",
    }
    pd.DataFrame(data).to_csv(path, index=False)


def test_compare_figure2_backend_outputs_contract(tmp_path: Path) -> None:
    module = _load_script_module()
    inputs = {}
    grids = {
        "python": np.linspace(-2.0, 1.0, 4),
        "auto": np.linspace(-2.0, 1.0, 4),
        "loca": np.linspace(-2.0, 1.0, 4),
    }
    offsets = {"python": 0.0, "auto": 0.1, "loca": -0.1}
    for backend, grid in grids.items():
        path = tmp_path / f"{backend}.csv"
        _write_backend_csv(path, backend, grid, offsets[backend])
        inputs[backend] = path

    output_dir = tmp_path / "comparison"
    module.main(
        [
            "--output-dir",
            str(output_dir),
            "--canonical-points",
            "4",
            "--python-input",
            str(inputs["python"]),
            "--auto-input",
            str(inputs["auto"]),
            "--loca-input",
            str(inputs["loca"]),
        ]
    )

    aligned = pd.read_csv(output_dir / "figure2_backend_aligned_eigenvalues.csv")
    differences = pd.read_csv(output_dir / "figure2_backend_pairwise_differences.csv")
    hopf = pd.read_csv(output_dir / "figure2_backend_hopf_estimates.csv")
    three_real = pd.read_csv(output_dir / "figure2_backend_three_real_intervals.csv")
    summary = json.loads((output_dir / "figure2_backend_comparison_summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))

    assert len(aligned) == 12
    assert set(aligned["backend"]) == {"python", "auto", "loca"}
    assert len(differences) == 12
    assert {"python_vs_auto", "python_vs_loca", "auto_vs_loca"} == set(summary["pairwise_backend_differences"])
    assert set(hopf["backend"]) == {"python", "auto", "loca"}
    assert len(hopf) == 3
    assert np.isclose(float(hopf.loc[hopf["backend"] == "python", "w_m_s"].iloc[0]), np.exp(-1.0))
    assert set(three_real["backend"]) == {"python", "auto", "loca"}
    assert summary["canonical_grid"]["point_count"] == 4
    assert summary["digitized_paper"]["status"] == "deferred"
    assert "secondary evidence" in summary["digitized_paper"]["uncertainty_note"]
    assert "numpy.interp" in metadata["interpolation"]["method"]
    assert (output_dir / "figure2_reproduction_backend_comparison.png").stat().st_size > 0


def test_canonical_grid_uses_common_overlap() -> None:
    module = _load_script_module()
    series = {}
    for backend, grid in {
        "python": np.linspace(-3.0, 1.0, 5),
        "auto": np.linspace(-2.0, 0.5, 4),
        "loca": np.linspace(-2.5, 0.75, 4),
    }.items():
        points = pd.DataFrame(
            {
                "log_w": grid,
                "w_m_s": np.exp(grid),
                "lambda1_real": grid,
                "lambda1_imag": np.ones_like(grid),
                "lambda2_real": -grid,
                "lambda2_imag": np.zeros_like(grid),
                "lambda3_real": grid,
                "lambda3_imag": -np.ones_like(grid),
            }
        )
        series[backend] = module.BackendSeries(backend, points, module.track_eigenvalue_branches(module._spectra_from_columns(points, "lambda")))

    grid = module.canonical_log_grid(series, points=6, reference_backend="python")

    assert len(grid) == 6
    assert grid[0] == -2.0
    assert grid[-1] == 0.5
