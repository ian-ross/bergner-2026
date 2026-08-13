import shutil
import subprocess
from dataclasses import replace
from functools import lru_cache
from math import log
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import vector_field
from bergner_spichtinger_2026.periodic_orbits import (
    transformed_vector_field,
    transformed_vector_field_environment_derivatives,
)
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state
from bergner_spichtinger_2026.stability import physical_eigenvalues, physical_jacobian


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


def _run_model(command, x, log_w, env, *, extra_args=()):
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
    args.extend(extra_args)
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
    assert "physical_vector_field" in header
    assert "physical_jacobian" in header
    assert "Teuchos::LAPACK" in cli and "GEEV" in cli
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


@pytest.mark.parametrize(
    "env,state,log_w",
    [
        (Environment(p=30000.0, T=225.0, w=0.1, F=1.0, N_a=1.0e10), [2.5e5, 4.0e-7, 1.35], log(0.12)),
        (Environment(p=30000.0, T=210.0, w=0.05, F=1.0, N_a=1.0e10), [8.0e4, 2.0e-7, 1.55], log(0.05)),
        (Environment(p=25000.0, T=230.0, w=0.2, F=0.7, N_a=3.0e8), [2.0e3, 8.0e-7, 1.25], log(0.2)),
    ],
)
def test_loca_local_sacado_derivatives_match_values_python_and_centered_checks(env, state, log_w):
    x = log_coordinates_from_physical_state(state)
    local = np.atleast_2d(_run_model("local-derivatives", x, log_w, env))
    assert local.shape == (3, 6)
    values = local[:, 0]
    state_jacobian = local[:, 1:4]
    temperature_column = local[:, 4]
    log_w_column = local[:, 5]

    physical_env = Environment(
        p=env.p,
        T=env.T,
        w=np.exp(log_w),
        F=env.F,
        N_a=env.N_a,
        Δz=env.Δz,
        include_evaporation=False,
    )
    python_values = transformed_vector_field(x, physical_env)
    python_temperature, python_log_w = transformed_vector_field_environment_derivatives(x, physical_env)
    np.testing.assert_allclose(values, _run_model("residual", x, log_w, env), rtol=2e-13, atol=1e-16)
    np.testing.assert_allclose(values, python_values, rtol=2e-12, atol=1e-16)
    np.testing.assert_allclose(temperature_column, python_temperature, rtol=3e-11, atol=2e-14)
    np.testing.assert_allclose(log_w_column, python_log_w, rtol=2e-12, atol=1e-16)

    finite_state = _central_difference_jacobian(
        lambda candidate: _run_model("residual", candidate, log_w, env),
        x,
        relative_step=1.0e-6,
    )
    temperature_step = 1.0e-4
    finite_temperature = (
        _run_model("residual", x, log_w, replace(env, T=env.T + temperature_step))
        - _run_model("residual", x, log_w, replace(env, T=env.T - temperature_step))
    ) / (2.0 * temperature_step)
    log_w_step = 1.0e-6
    finite_log_w = (
        _run_model("residual", x, log_w + log_w_step, env)
        - _run_model("residual", x, log_w - log_w_step, env)
    ) / (2.0 * log_w_step)
    assert np.linalg.norm(state_jacobian - finite_state) / max(1.0, np.linalg.norm(state_jacobian)) < 1.0e-6
    assert np.linalg.norm(temperature_column - finite_temperature) / max(
        1.0, np.linalg.norm(temperature_column)
    ) < 1.0e-8
    assert np.linalg.norm(log_w_column - finite_log_w) / max(1.0, np.linalg.norm(log_w_column)) < 1.0e-9


def test_loca_normalized_parameter_columns_apply_documented_chain_rules():
    env = Environment(p=30000.0, T=210.0, w=0.05, F=1.0, N_a=1.0e10)
    x = log_coordinates_from_physical_state([8.0e4, 2.0e-7, 1.55])
    log_w = log(0.05)
    lower = log(0.01)
    upper = log(0.25)
    spine_log_w_derivative = 0.037
    local = np.atleast_2d(_run_model("local-derivatives", x, log_w, env))
    columns = np.atleast_2d(
        _run_model(
            "parameter-columns",
            x,
            log_w,
            env,
            extra_args=(
                "--log-w-lower",
                f"{lower:.17g}",
                "--log-w-upper",
                f"{upper:.17g}",
                "--d-spine-log-w-dT",
                f"{spine_log_w_derivative:.17g}",
            ),
        )
    )
    assert columns.shape == (3, 2)
    expected_rho = 0.5 * (upper - lower) * local[:, 5]
    expected_temperature_hat = 25.0 * (
        local[:, 4] + spine_log_w_derivative * local[:, 5]
    )
    np.testing.assert_allclose(columns[:, 0], expected_rho, rtol=2e-15, atol=1e-16)
    np.testing.assert_allclose(columns[:, 1], expected_temperature_hat, rtol=2e-15, atol=1e-16)

    coordinate_step = 1.0e-6
    rho_factor = 0.5 * (upper - lower)
    finite_rho = (
        _run_model("residual", x, log_w + rho_factor * coordinate_step, env)
        - _run_model("residual", x, log_w - rho_factor * coordinate_step, env)
    ) / (2.0 * coordinate_step)
    temperature_factor = 25.0
    log_w_factor = temperature_factor * spine_log_w_derivative
    finite_temperature_hat = (
        _run_model(
            "residual",
            x,
            log_w + log_w_factor * coordinate_step,
            replace(env, T=env.T + temperature_factor * coordinate_step),
        )
        - _run_model(
            "residual",
            x,
            log_w - log_w_factor * coordinate_step,
            replace(env, T=env.T - temperature_factor * coordinate_step),
        )
    ) / (2.0 * coordinate_step)
    assert np.linalg.norm(columns[:, 0] - finite_rho) / max(1.0, np.linalg.norm(columns[:, 0])) < 1.0e-8
    assert np.linalg.norm(columns[:, 1] - finite_temperature_hat) / max(
        1.0, np.linalg.norm(columns[:, 1])
    ) < 1.0e-7


def test_loca_local_derivatives_reject_the_discontinuous_evaporation_switch():
    env = Environment(
        p=30000.0,
        T=225.0,
        w=0.1,
        F=1.0,
        N_a=1.0e10,
        include_evaporation=True,
    )
    x = log_coordinates_from_physical_state([2.5e5, 4.0e-7, 0.95])
    with pytest.raises(subprocess.CalledProcessError) as error:
        _run_model("local-derivatives", x, log(0.1), env)
    assert "smooth no-evaporation model" in error.value.stderr


def test_loca_sacado_state_jacobian_matches_python_central_difference():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0, N_a=1.0e10)
    x = log_coordinates_from_physical_state([2.5e5, 4.0e-7, 1.35])
    log_w = log(0.12)

    cxx_jacobian = _run_model("jacobian", x, log_w, env)
    py_jacobian = _central_difference_jacobian(lambda z: equilibrium_residual(z, log_w, env), x)

    np.testing.assert_allclose(cxx_jacobian, py_jacobian, rtol=3e-6, atol=1e-11)


def test_loca_physical_rhs_and_sacado_physical_jacobian_match_python_reference():
    env = Environment(p=30000.0, T=225.0, w=0.12, F=1.0, N_a=1.0e10)
    state = np.array([2.5e5, 4.0e-7, 1.35], dtype=float)

    cxx_rhs = _run_model("physical-rhs", state, env.w, env)
    cxx_jacobian = _run_model("physical-jacobian", state, env.w, env)

    np.testing.assert_allclose(cxx_rhs, vector_field(*state, env), rtol=2e-12, atol=1e-16)
    np.testing.assert_allclose(cxx_jacobian, physical_jacobian(state, env=env), rtol=2e-12, atol=1e-15)


def test_loca_teuchos_lapack_physical_eigenvalues_match_python_reference():
    env = Environment(p=30000.0, T=230.0, w=0.05, F=1.0, N_a=1.0e10)
    state = np.array([1.0e5, 2.0e-7, 1.55], dtype=float)
    exe = _build_loca_executable()
    args = [
        str(exe),
        "eigenvalues",
        *(f"{value:.17g}" for value in state),
        f"{env.w:.17g}",
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
    cxx_rows = np.genfromtxt(completed.stdout.splitlines(), delimiter=",", names=True, dtype=None, encoding=None)
    cxx_eigenvalues = cxx_rows["eigenvalue_real"] + 1j * cxx_rows["eigenvalue_imag"]
    py_eigenvalues = physical_eigenvalues(state, env=env)

    np.testing.assert_allclose(cxx_eigenvalues, py_eigenvalues, rtol=2e-10, atol=1e-12)
    assert set(cxx_rows["eigenvalue_source"]) == {"teuchos_lapack_geev"}
    assert set(cxx_rows["jacobian_coordinate_system"]) == {"physical_ode_state"}
