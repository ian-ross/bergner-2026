from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation" / "scripts" / "compare_figure3_hopf_loci.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("compare_figure3_hopf_loci", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_backend_csv(path: Path, module, backend: str, *, offset: float = 0.0, duplicate_anchor: bool = False) -> None:
    rows = []
    for branch_id in ("lower_hopf", "upper_hopf"):
        for point_index, T_K in enumerate([190.0, 230.0, 240.0]):
            fit_w = float(module.table_ii_w(branch_id, T_K))
            w = fit_w * np.exp(offset)
            rows.append(
                {
                    "backend": backend,
                    "schema_version": "synthetic-v1",
                    "branch_id": branch_id,
                    "paper_fit_branch": module.PAPER_FIT_BY_BRANCH[branch_id],
                    "point_index": point_index,
                    "T_K": T_K,
                    "log_w": float(np.log(w)),
                    "w_m_s": float(w),
                    "converged": True,
                    "method": f"{backend}_synthetic_hopf",
                    "method_metadata": f"synthetic {backend} metadata",
                    "source_file": f"synthetic/{backend}.csv",
                    "continuation_parameterization": f"{backend}_continuation",
                    "jacobian_coordinate_system": "physical_ode_state",
                }
            )
            if duplicate_anchor and T_K == 230.0:
                dup = dict(rows[-1])
                dup["point_index"] = 99
                dup["log_w"] = float(np.log(w * np.exp(1.0e-6)))
                dup["w_m_s"] = float(w * np.exp(1.0e-6))
                rows.append(dup)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_compare_figure3_backend_outputs_contract(tmp_path: Path) -> None:
    module = _load_script_module()
    inputs = {}
    for backend, offset in {"python": 0.0, "auto": 1.0e-4, "loca": -1.0e-4}.items():
        path = tmp_path / f"{backend}.csv"
        _write_backend_csv(path, module, backend, offset=offset, duplicate_anchor=(backend == "auto"))
        inputs[backend] = path

    output_dir = tmp_path / "comparison"
    module.main(
        [
            "--output-dir",
            str(output_dir),
            "--canonical-points",
            "3",
            "--python-input",
            str(inputs["python"]),
            "--auto-input",
            str(inputs["auto"]),
            "--loca-input",
            str(inputs["loca"]),
            "--require-all",
        ]
    )

    merged = pd.read_csv(output_dir / "figure3_backend_merged_hopf_loci.csv")
    pairwise = pd.read_csv(output_dir / "figure3_backend_pairwise_differences.csv")
    fit_diffs = pd.read_csv(output_dir / "figure3_backend_to_table_ii_differences.csv")
    anchors = pd.read_csv(output_dir / "figure3_backend_T230_anchor_comparisons.csv")
    summary = json.loads((output_dir / "figure3_backend_comparison_summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    merged_json = json.loads((output_dir / "figure3_backend_merged_hopf_loci.json").read_text(encoding="utf-8"))

    assert set(merged["backend"]) == {"python", "auto", "loca"}
    assert set(merged["branch_id"]) == {"lower_hopf", "upper_hopf"}
    assert {"input_path", "input_row_index", "method", "method_metadata", "source_file"}.issubset(merged.columns)
    assert np.isfinite(merged[["delta_to_table_ii_log_w", "delta_to_table_ii_w_m_s"]].to_numpy()).all()
    assert len(merged_json["records"]) == len(merged)

    assert {"python_vs_auto:lower_hopf", "python_vs_loca:upper_hopf", "auto_vs_loca:lower_hopf"}.issubset(summary["pairwise_backend_differences"])
    assert len(pairwise) == 18  # 3 backend pairs * 2 branches * 3 canonical temperatures
    assert len(fit_diffs) == 18
    assert set(anchors["T_K"]) == {230.0}
    assert set(anchors["backend"]) == {"python", "auto", "loca"}
    assert summary["backends"]["auto"]["branches"]["lower_hopf"]["point_count"] == 4
    assert "Table II curves are paper fit references" in summary["known_caveats"][0]
    assert metadata["schema"]["required_columns"] == sorted(module.REQUIRED_COLUMNS)
    assert (output_dir / "figure3_table_ii_hopf_fit_references.csv").stat().st_size > 0
    assert (output_dir / "figure3_hopf_backend_comparison.png").stat().st_size > 0


def test_compare_figure3_schema_validation_rejects_missing_required_columns(tmp_path: Path) -> None:
    module = _load_script_module()
    bad_path = tmp_path / "bad.csv"
    pd.DataFrame({"branch_id": ["lower_hopf"], "T_K": [230.0], "w_m_s": [0.05]}).to_csv(bad_path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        module.load_backend_frame("python", bad_path)
