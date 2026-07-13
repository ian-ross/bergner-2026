from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation" / "scripts" / "run_auto_hopf_loci.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_auto_hopf_loci", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(shutil.which("auto") is None, reason="AUTO-07p executable is not installed")
def test_run_auto_figure3_hopf_loci_smoke_contract(tmp_path: Path) -> None:
    module = _load_script_module()
    output_dir = tmp_path / "figure3_auto_hopf_loci"

    module.main(["--output-dir", str(output_dir), "--clean"])

    loci_path = output_dir / "auto_figure3_hopf_loci.csv"
    labels_path = output_dir / "auto_figure3_hopf_labels.csv"
    diagnostics_path = output_dir / "run_diagnostics.json"
    metadata_path = output_dir / "run_metadata.json"
    summary_path = output_dir / "auto_figure3_summary.json"
    backend_plot_path = output_dir / "auto_figure3_hopf_loci.png"

    loci = pd.read_csv(loci_path)
    labels = pd.read_csv(labels_path)
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert diagnostics["ok"] is True
    assert summary["diagnostics_ok"] is True
    assert {"lower_hopf", "upper_hopf"} == set(loci["branch_id"])
    assert len(labels) == 2
    assert set(labels["auto_label"]) == set(diagnostics["equilibrium_hopf_labels"])
    assert float(loci["T_K"].min()) == 190.0
    assert float(loci["T_K"].max()) == 240.0
    for _, group in loci.groupby("branch_id"):
        assert float(group["T_K"].min()) == 190.0
        assert float(group["T_K"].max()) == 240.0
    assert loci["converged"].all()

    required_columns = {
        "backend",
        "branch_id",
        "paper_fit_branch",
        "T_K",
        "log_w",
        "w_m_s",
        "n",
        "q",
        "s",
        "hopf_frequency",
        "residual_norm",
        "jacobian_coordinate_system",
        "continuation_parameterization",
        "method_metadata",
        "raw_auto_run",
        "auto_hopf_source_label",
    }
    assert required_columns.issubset(loci.columns)
    assert np.isfinite(loci[["log_w", "w_m_s", "n", "q", "s", "hopf_frequency", "residual_norm"]].to_numpy()).all()
    assert (loci["w_m_s"] > 0.0).all()
    assert (loci["hopf_frequency"] > 0.0).all()
    assert (loci["jacobian_coordinate_system"] == "physical_ode_state").all()
    assert loci["continuation_parameterization"].str.contains("AUTO_ISW2").all()
    assert loci["method_metadata"].str.contains("ISP=2").all()

    seed_w = dict(zip(labels.sort_values("w_m_s")["auto_label"], labels.sort_values("w_m_s")["w_m_s"]))
    observed = sorted(seed_w.values())
    assert abs(observed[0] - module.LOWER_ANCHOR_W_M_S) <= 2e-5
    assert abs(observed[1] - module.UPPER_ANCHOR_W_M_S) <= 2e-5
    assert all(item["T230_within_tolerance"] for item in summary["branch_summaries"])

    raw_paths = diagnostics["raw_auto_output_paths"]
    assert any(path.endswith("b.bs2026_figure3_hopf.eq") for path in raw_paths)
    assert any(path.endswith("s.bs2026_figure3_hopf.hb1.fw") for path in raw_paths)
    assert any(path.endswith("d.bs2026_figure3_hopf.hb2.bw") for path in raw_paths)
    assert metadata["method"]["hopf_continuation"].startswith("Restart from AUTO HB1/HB2")
    assert backend_plot_path.exists() and backend_plot_path.stat().st_size > 0
