from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "005-figure2-eigenvalues" / "scripts" / "generate_python_figure2_eigenvalues.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("generate_python_figure2_eigenvalues", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_python_figure2_smoke_outputs_contract(tmp_path: Path) -> None:
    module = _load_script_module()
    output_dir = tmp_path / "figure2_python_eigenvalues"

    module.main(["--output-dir", str(output_dir), "--points", "400"])

    eigenvalues_path = output_dir / "python_figure2_eigenvalues.csv"
    points_path = output_dir / "python_figure2_branch_points.csv"
    crossings_path = output_dir / "python_figure2_hopf_landmark_comparison.csv"
    metadata_path = output_dir / "run_metadata.json"
    plot_path = output_dir / "python_figure2_eigenvalues.png"

    eigenvalues = pd.read_csv(eigenvalues_path)
    points = pd.read_csv(points_path)
    crossings = pd.read_csv(crossings_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert len(points) == 400
    assert int(points["converged"].sum()) == 400
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
        "tracked_lambda1_real",
        "tracked_lambda1_imag",
        "tracked_lambda2_real",
        "tracked_lambda2_imag",
        "tracked_lambda3_real",
        "tracked_lambda3_imag",
    ]
    assert np.isfinite(points[finite_columns].to_numpy()).all()
    assert len(eigenvalues) == 3 * len(points)
    assert set(eigenvalues["eigen_index"]) == {1, 2, 3}

    required_columns = {
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
    }
    assert required_columns.issubset(eigenvalues.columns)

    observed = sorted(crossings["observed_w_m_s"].tolist())
    assert len(observed) == 2
    assert abs(observed[0] - 0.048) <= module.HOPF_LANDMARK_TOLERANCE_M_S
    assert abs(observed[1] - 0.77) <= module.HOPF_LANDMARK_TOLERANCE_M_S
    assert crossings["within_documented_tolerance"].all()

    assert metadata["parameters"]["N_a_m3"] == module.AEROSOL_N_A
    assert metadata["grid"]["density_points"] == 400
    assert metadata["jacobian"]["matrix"].startswith("d(dn/dt,dq/dt,ds/dt)/d(n,q,s)")
    assert metadata["eigenvalues"]["sorting_tolerance_imag"] == module.DEFAULT_IMAG_TOL
    assert "minimum-distance" in metadata["eigenvalues"]["plot_branch_tracking"]
    assert "recommended" in metadata["commands"]
    assert plot_path.exists() and plot_path.stat().st_size > 0


def test_tracked_eigenvalue_branches_remove_canonical_label_jump() -> None:
    module = _load_script_module()
    # Synthetic version of the observed plotting problem: canonical labels swap
    # when a complex pair becomes three real values.  Plot-tracked identities
    # should follow the nearby values instead of drawing a vertical jump.
    canonical = np.array(
        [
            [-2.4e-3 + 1.0e-4j, -2.4e-3 - 1.0e-4j, -8.0e-4 + 0j],
            [-8.5e-4 + 0j, -2.35e-3 + 0j, -2.5e-3 + 0j],
        ],
        dtype=complex,
    )

    tracked = module.track_eigenvalue_branches(canonical)

    assert tracked[1, 0] == canonical[1, 1]
    assert tracked[1, 1] == canonical[1, 2]
    assert tracked[1, 2] == canonical[1, 0]
    assert np.max(np.abs(tracked[1] - tracked[0])) < np.max(np.abs(canonical[1] - canonical[0]))



def test_generate_python_figure2_requires_dense_grid() -> None:
    module = _load_script_module()

    try:
        module.generate_branch(points=399, tolerance=module.DEFAULT_TOLERANCE, max_iterations=module.DEFAULT_MAX_ITERATIONS)
    except ValueError as exc:
        assert "at least 400" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("generate_branch accepted an under-dense Figure 2 grid")
