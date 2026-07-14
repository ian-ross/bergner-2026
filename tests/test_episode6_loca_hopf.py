from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation" / "scripts" / "run_loca_hopf_loci.py"
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


def test_loca_figure3_script_uses_native_cpp_loca_hopf_not_python_corrector() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    cli = (LOCA_ROOT / "src/model_cli.cpp").read_text(encoding="utf-8")

    assert "nox-loca-hopf-continue" in script
    assert "continue_characteristic_hopf_branch" not in script
    assert "No Python Hopf corrector is used" in script
    assert "LOCA::Hopf::MooreSpence::ExtendedGroup" in cli
    assert "nox_loca_native_moore_spence_hopf_continuation" in cli
    assert "compute_initial_hopf_guess" in cli
    assert 'command == "nox-loca-hopf-continue"' in cli


@pytest.mark.skipif(
    not TRILINOS_CONFIG.is_file() or shutil.which("cmake") is None or shutil.which("g++") is None,
    reason="NOX/LOCA toolchain is unavailable",
)
def test_native_loca_hopf_runner_outputs_both_figure3_branches(tmp_path: Path) -> None:
    output_dir = tmp_path / "figure3_loca_hopf_loci"
    build_dir = tmp_path / "build"
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(SCRIPT_PATH),
            "--output-dir",
            str(output_dir),
            "--build-dir",
            str(build_dir),
            "--steps-each-side",
            "80",
            "--clean",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    loci = pd.read_csv(output_dir / "loca_figure3_hopf_loci.csv")
    summary = json.loads((output_dir / "loca_figure3_summary.json").read_text(encoding="utf-8"))
    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))

    assert summary["native_loca_hopf"] is True
    assert summary["all_converged"] is True
    assert metadata["method"]["python_corrector_used"] is False
    assert {"lower_hopf", "upper_hopf"} == set(loci["branch_id"])
    assert loci.groupby("branch_id")["T_K"].min().to_dict() == {"lower_hopf": 190.0, "upper_hopf": 190.0}
    assert loci.groupby("branch_id")["T_K"].max().to_dict() == {"lower_hopf": 240.0, "upper_hopf": 240.0}
    assert set(loci["loca_native_hopf_stepper"]) == {True}
    assert set(loci["loca_continuation_mode"]) == {"nox_loca_native_moore_spence_hopf_continuation"}
    seed_w = dict(zip(loci.loc[(loci["T_K"] - 230.0).abs() < 1e-9, "branch_id"], loci.loc[(loci["T_K"] - 230.0).abs() < 1e-9, "w_m_s"]))
    assert abs(seed_w["lower_hopf"] - 0.048531) < 2e-5
    assert abs(seed_w["upper_hopf"] - 0.768680) < 2e-5
    assert (output_dir / "loca_figure3_hopf_loci.png").stat().st_size > 0
