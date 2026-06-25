import csv
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/run_loca_figure1.py"
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
