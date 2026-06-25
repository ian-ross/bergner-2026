import shutil
import subprocess
from functools import lru_cache
from math import log
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


def _missing_loca_toolchain_reason():
    if not TRILINOS_CONFIG.is_file():
        return f"Trilinos CMake config not found at {TRILINOS_CONFIG}"
    for tool in ("cmake", "g++"):
        if shutil.which(tool) is None:
            return f"{tool} is unavailable"
    return None


@lru_cache(maxsize=1)
def _build_loca_executable():
    reason = _missing_loca_toolchain_reason()
    if reason:
        pytest.skip(reason)

    build_dir = REPO_ROOT / ".pytest_cache" / "loca-build"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "cmake",
            "-S",
            str(LOCA_ROOT),
            "-B",
            str(build_dir),
            f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}",
        ],
        check=True,
        cwd=REPO_ROOT,
    )
    subprocess.run(["cmake", "--build", str(build_dir), "--parallel", "2"], check=True, cwd=REPO_ROOT)
    exe = build_dir / "bs2026_loca_model"
    assert exe.is_file()
    return exe


def _run_model(command, x, log_w, env):
    exe = _build_loca_executable()
    args = [
        str(exe),
        command,
        *(f"{value:.17g}" for value in x),
        f"{log_w:.17g}",
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
    if env.include_evaporation:
        args.append("--include-evaporation")
    completed = subprocess.run(args, check=True, text=True, capture_output=True, cwd=REPO_ROOT)
    return np.loadtxt(completed.stdout.splitlines())


def _central_difference_jacobian(fn, x, *, relative_step=1e-5):
    x = np.asarray(x, dtype=float)
    jac = np.empty((3, 3), dtype=float)
    for j in range(3):
        step = relative_step * max(1.0, abs(x[j]))
        plus = x.copy()
        minus = x.copy()
        plus[j] += step
        minus[j] -= step
        jac[:, j] = (fn(plus) - fn(minus)) / (2.0 * step)
    return jac


def test_loca_cmake_project_and_cli_sources_are_top_level_reusable_assets():
    assert (LOCA_ROOT / "CMakeLists.txt").is_file()
    assert (LOCA_ROOT / "include/bergner_spichtinger_2026_loca/model.hpp").is_file()
    assert (LOCA_ROOT / "src/model_cli.cpp").is_file()

    cmake = (LOCA_ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    header = (LOCA_ROOT / "include/bergner_spichtinger_2026_loca/model.hpp").read_text(encoding="utf-8")
    cli = (LOCA_ROOT / "src/model_cli.cpp").read_text(encoding="utf-8")

    assert "find_package(Trilinos REQUIRED CONFIG)" in cmake
    assert "Sacado" in header
    assert "residual" in cli and "jacobian" in cli
    assert "dn/dt / n" in header


@pytest.mark.parametrize(
    "env,state,log_w",
    [
        (Environment(p=30000.0, T=225.0, w=0.1, F=1.0), [1.0e4, 1.0e-6, 1.4], log(0.1)),
        (Environment(p=30000.0, T=210.0, w=0.05, F=1.0, N_a=1.0e10), [5.0e5, 2.0e-7, 1.55], log(0.05)),
        (Environment(p=25000.0, T=230.0, w=0.2, F=0.7), [2.0e3, 8.0e-7, 1.25], log(0.2)),
    ],
)
def test_loca_residual_cli_matches_python_reference(env, state, log_w):
    x = log_coordinates_from_physical_state(state)

    cxx_residual = _run_model("residual", x, log_w, env)
    py_residual = equilibrium_residual(x, log_w, env)

    np.testing.assert_allclose(cxx_residual, py_residual, rtol=2e-12, atol=1e-16)


def test_loca_sacado_state_jacobian_matches_python_central_difference():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0, N_a=1.0e10)
    x = log_coordinates_from_physical_state([2.5e5, 4.0e-7, 1.35])
    log_w = log(0.12)

    cxx_jacobian = _run_model("jacobian", x, log_w, env)
    py_jacobian = _central_difference_jacobian(lambda z: equilibrium_residual(z, log_w, env), x)

    np.testing.assert_allclose(cxx_jacobian, py_jacobian, rtol=3e-6, atol=1e-11)
