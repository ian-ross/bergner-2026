from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation" / "scripts" / "generate_python_hopf_loci.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("generate_python_hopf_loci", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_python_figure3_hopf_loci_smoke_contract(tmp_path: Path) -> None:
    module = _load_script_module()
    output_dir = tmp_path / "figure3_python_hopf_loci"

    module.main(["--output-dir", str(output_dir), "--t-step", "50"])

    loci_path = output_dir / "python_figure3_hopf_loci.csv"
    seeds_path = output_dir / "python_figure3_hopf_seeds.csv"
    diagnostics_path = output_dir / "python_figure3_hopf_diagnostics.csv"
    metadata_path = output_dir / "run_metadata.json"
    backend_plot_path = output_dir / "python_figure3_hopf_loci.png"
    comparison_plot_path = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation" / "outputs" / "figure3_backend_comparison" / "figure3_hopf_backend_comparison.png"

    loci = pd.read_csv(loci_path)
    seeds = pd.read_csv(seeds_path)
    diagnostics = pd.read_csv(diagnostics_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert {"lower_hopf", "upper_hopf"} == set(loci["branch_id"])
    assert len(seeds) == 2
    assert len(diagnostics) == len(loci)
    assert float(loci["T_K"].min()) == 190.0
    assert float(loci["T_K"].max()) == 240.0
    for values in loci.groupby("branch_id")["T_K"].apply(set):
        assert values == {190.0, 230.0, 240.0}
    assert loci["converged"].all()

    required_columns = {
        "T_K",
        "log_w",
        "w_m_s",
        "n",
        "q",
        "s",
        "hopf_frequency",
        "residual_norm",
        "branch_id",
        "converged",
        "method_metadata",
        "jacobian_coordinate_system",
        "state_coordinate_system",
    }
    assert required_columns.issubset(loci.columns)
    assert np.isfinite(loci[["log_w", "w_m_s", "n", "q", "s", "hopf_frequency", "residual_norm"]].to_numpy()).all()
    assert (loci["w_m_s"] > 0.0).all()
    assert (loci["hopf_frequency"] > 0.0).all()
    assert (loci["jacobian_coordinate_system"] == "physical_ode_state").all()
    assert loci["method_metadata"].str.contains("physical ODE Jacobian").all()
    relative_fit_error = ((loci["w_m_s"] - loci["table_ii_reference_w_m_s"]).abs() / loci["table_ii_reference_w_m_s"]).max()
    assert relative_fit_error < 0.02

    seed_w = dict(zip(seeds["branch_id"], seeds["w_m_s"]))
    assert abs(seed_w["lower_hopf"] - module.LOWER_SEED_W_M_S) <= 2e-5
    assert abs(seed_w["upper_hopf"] - module.UPPER_SEED_W_M_S) <= 2e-5
    assert metadata["summary"]["all_converged"] is True
    assert metadata["summary"]["temperature_min_K"] == 190.0
    assert metadata["summary"]["temperature_max_K"] == 240.0
    assert metadata["method"]["hopf_jacobian_coordinates"] == "physical_ode_state_n_q_s"
    assert backend_plot_path.exists() and backend_plot_path.stat().st_size > 0
    assert comparison_plot_path.exists() and comparison_plot_path.stat().st_size > 0
    assert metadata["outputs"]["backend_plot_png"].endswith("python_figure3_hopf_loci.png")
    assert metadata["outputs"]["comparison_plot_png"].endswith("figure3_hopf_backend_comparison.png")
