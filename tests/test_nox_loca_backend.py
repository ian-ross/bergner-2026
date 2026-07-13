import csv
import json
import shutil
import subprocess
from functools import lru_cache
from math import log
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import equilibrium
from bergner_spichtinger_2026.residuals import log_coordinates_from_physical_state


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
RUN_SCRIPT = REPO_ROOT / "episodes/004-figure1-loca-continuation/scripts/run_nox_loca_figure1.py"
DOC = REPO_ROOT / "docs/NOX_LOCA_BACKEND.md"


def _missing_toolchain_reason():
    if not TRILINOS_CONFIG.is_file():
        return f"Trilinos CMake config not found at {TRILINOS_CONFIG}"
    for tool in ("cmake", "g++"):
        if shutil.which(tool) is None:
            return f"{tool} is unavailable"
    return None


@lru_cache(maxsize=1)
def _build_executable():
    reason = _missing_toolchain_reason()
    if reason:
        pytest.skip(reason)
    build_dir = REPO_ROOT / ".pytest_cache" / "nox-loca-test-build"
    subprocess.run(
        ["cmake", "-S", str(LOCA_ROOT), "-B", str(build_dir), f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}"],
        check=True,
        cwd=REPO_ROOT,
    )
    subprocess.run(["cmake", "--build", str(build_dir), "--parallel", "2"], check=True, cwd=REPO_ROOT)
    exe = build_dir / "bs2026_loca_model"
    assert exe.is_file()
    return exe


def _figure1_initial_state(T=230.0):
    env = Environment(p=30000.0, T=T, w=0.005, F=1.0, N_a=N_a_figure1_high, Δz=100.0)
    return env, log_coordinates_from_physical_state(equilibrium(env))


def test_nox_loca_sources_document_dense_lapack_adapter_and_cli_commands():
    header = (LOCA_ROOT / "include/bergner_spichtinger_2026_loca/nox_loca_backend.hpp").read_text(encoding="utf-8")
    cli = (LOCA_ROOT / "src/model_cli.cpp").read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "LOCA::LAPACK::Interface" in header
    assert "NOX::LAPACK::Vector" in header and "NOX::LAPACK::Matrix" in header
    assert "LOCA::ParameterVector" in header
    assert "residual_values" in header and "state_jacobian" in header
    assert "nox-loca-smoke" in cli and "nox-loca-continue" in cli
    assert "write_nox_loca_continuation_csv" in cli and "NOX::Solver::buildSolver" in cli
    assert 'command == "nox-loca-continue"' in cli
    assert "write_nox_loca_continuation_csv(x, control, options)" in cli
    assert "Lightweight backend vs NOX/LOCA adapter" in doc
    assert "TASK-030" in doc


def test_nox_loca_smoke_exercises_residual_jacobian_callbacks():
    exe = _build_executable()
    env, x0 = _figure1_initial_state()
    args = [
        str(exe),
        "nox-loca-smoke",
        *(f"{value:.17g}" for value in x0),
        f"{log(env.w):.17g}",
        "--p",
        f"{env.p:.17g}",
        "--T",
        f"{env.T:.17g}",
        "--F",
        f"{env.F:.17g}",
        "--N-a",
        f"{env.N_a:.17g}",
        "--dz",
        f"{env.Δz:.17g}",
    ]
    completed = subprocess.run(args, check=True, text=True, capture_output=True, cwd=REPO_ROOT)
    rows = list(csv.DictReader(completed.stdout.splitlines()))

    assert len(rows) == 1
    assert rows[0]["backend"] == "nox_loca"
    assert rows[0]["interface"] == "LOCA::LAPACK::Interface"
    assert rows[0]["continuation_parameter"] == "log_w"
    assert float(rows[0]["residual_norm"]) < 1e-8
    assert np.isfinite(float(rows[0]["jacobian_00"]))


def test_nox_loca_continue_matches_lightweight_cxx_continuation_rows():
    exe = _build_executable()
    env, x0 = _figure1_initial_state()
    common = [
        *(f"{value:.17g}" for value in x0),
        f"{log(env.w):.17g}",
        "--log-w-end",
        f"{log(0.02):.17g}",
        "--steps",
        "4",
        "--p",
        f"{env.p:.17g}",
        "--T",
        f"{env.T:.17g}",
        "--F",
        f"{env.F:.17g}",
        "--N-a",
        f"{env.N_a:.17g}",
        "--dz",
        f"{env.Δz:.17g}",
    ]
    lightweight = subprocess.run([str(exe), "continue", *common], check=True, text=True, capture_output=True, cwd=REPO_ROOT)
    nox_loca = subprocess.run([str(exe), "nox-loca-continue", *common], check=True, text=True, capture_output=True, cwd=REPO_ROOT)
    light_rows = list(csv.DictReader(lightweight.stdout.splitlines()))
    nox_rows = list(csv.DictReader(nox_loca.stdout.splitlines()))

    assert len(light_rows) == len(nox_rows) == 5
    for light, full in zip(light_rows, nox_rows, strict=True):
        assert full["loca_continuation_mode"] == "nox_loca_lapack_group_nox_solver"
        for field in ("log_w", "log_n", "log_q", "s", "residual_norm"):
            assert float(full[field]) == pytest.approx(float(light[field]), rel=2e-13, abs=1e-15)


def test_nox_loca_continue_preserves_normalized_output_contract(tmp_path):
    reason = _missing_toolchain_reason()
    if reason:
        pytest.skip(reason)
    output_dir = tmp_path / "figure1_nox_loca_branches"
    build_dir = tmp_path / "build"
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(RUN_SCRIPT),
            "--output-dir",
            str(output_dir),
            "--build-dir",
            str(build_dir),
            "--temperatures",
            "230",
            "--steps",
            "8",
            "--clean",
        ],
        check=True,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )

    metadata = json.loads((output_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["backend_command"] == "nox-loca-continue"
    assert metadata["backend_label"] == "nox_loca"
    assert metadata["schema_version"] == "figure1-branch-schema-v1"
    assert all(run["ok"] for run in metadata["runs"])

    with (output_dir / "branches_all.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {row["backend"] for row in rows} == {"nox_loca"}
    assert {row["loca_continuation_mode"] for row in rows} == {"nox_loca_lapack_group_nox_solver"}
    assert all(row["converged"].lower() == "true" for row in rows)
    assert all(float(row["n"]) > 0.0 and float(row["q"]) > 0.0 for row in rows)
    assert max(float(row["residual_norm"]) for row in rows) < 1e-7
