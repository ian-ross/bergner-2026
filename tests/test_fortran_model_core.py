import shutil
import subprocess
from dataclasses import dataclass
from math import log
from pathlib import Path

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients, process_terms, vector_field
from bergner_spichtinger_2026.residuals import equilibrium_residual


REPO_ROOT = Path(__file__).resolve().parents[1]
FORTRAN_SOURCES = [
    REPO_ROOT / "auto/src/bs2026_constants.f90",
    REPO_ROOT / "auto/src/bs2026_model.f90",
    REPO_ROOT / "auto/src/bs2026_evaluator.f90",
]
COEFFICIENT_KEYS = ["rho", "D", "p_si", "p1e", "p2", "A_n", "A_q", "A_s", "B_q", "B_s", "C_n", "C_q"]
TERM_KEYS = ["Nuc_n", "Nuc_q", "Nuc_s", "Dep_q", "Dep_s", "Evap_n", "Sed_n", "Sed_q", "Cool"]


@dataclass(frozen=True)
class EquivalenceCase:
    env: Environment
    state: tuple[float, float, float]


@pytest.fixture(scope="session")
def fortran_evaluator(tmp_path_factory):
    """Build the standalone shared Fortran evaluator from repository-root paths."""
    gfortran = shutil.which("gfortran")
    if gfortran is None:
        pytest.skip("gfortran is required for shared Fortran model-core tests")

    build_dir = tmp_path_factory.mktemp("bs2026_fortran")
    exe = build_dir / "bs2026_evaluator"
    subprocess.run(
        [
            gfortran,
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-std=f2008",
            f"-J{build_dir}",
            f"-I{build_dir}",
            *map(str, FORTRAN_SOURCES),
            "-o",
            str(exe),
        ],
        check=True,
        cwd=REPO_ROOT,
    )
    return exe


def _run_evaluator(exe, *args):
    result = subprocess.run([str(exe), *map(str, args)], check=True, text=True, capture_output=True)
    parsed = {}
    for line in result.stdout.splitlines():
        key, value = line.split()
        parsed[key] = float(value)
    return parsed


def _required_environment_args(env: Environment):
    return [env.p, env.T, env.w, env.F]


def _optional_environment_args(env: Environment):
    return [env.N_a, env.Δz, int(env.include_evaporation)]


def _complete_environment_args(env: Environment):
    return [*_required_environment_args(env), *_optional_environment_args(env)]


def _assert_componentwise_close(actual, expected, *, rtol=1e-10):
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    atol = np.maximum(1e-300, 1e-12 * np.abs(expected))
    close = np.isclose(actual, expected, rtol=rtol, atol=atol)
    if not np.all(close):
        raise AssertionError(
            f"mismatched components: actual={actual!r}, expected={expected!r}, "
            f"absdiff={np.abs(actual - expected)!r}, rtol={rtol}, atol={atol!r}"
        )


def _compare_case(exe, case: EquivalenceCase):
    env = case.env
    state = case.state

    actual_coefficients = _run_evaluator(exe, "coefficients", *_complete_environment_args(env))
    expected_coefficients = coefficients(env)
    for key in COEFFICIENT_KEYS:
        python_key = "ρ" if key == "rho" else key
        _assert_componentwise_close(actual_coefficients[key], getattr(expected_coefficients, python_key), rtol=1e-11)

    actual_terms = _run_evaluator(exe, "terms", *_required_environment_args(env), *state, *_optional_environment_args(env))
    expected_terms = process_terms(*state, env=env)
    for key in TERM_KEYS:
        _assert_componentwise_close(actual_terms[key], expected_terms[key])

    actual_rhs = _run_evaluator(exe, "rhs", *_required_environment_args(env), *state, *_optional_environment_args(env))
    expected_rhs = vector_field(*state, env)
    _assert_componentwise_close([actual_rhs[f"rhs_{i}"] for i in range(1, 4)], expected_rhs)

    log_state = np.array([log(state[0]), log(state[1]), state[2]])
    log_w = log(env.w)
    actual_residual = _run_evaluator(
        exe,
        "residual",
        env.p,
        env.T,
        log_w,
        env.F,
        *log_state,
        env.N_a,
        env.Δz,
        int(env.include_evaporation),
    )
    expected_residual = equilibrium_residual(log_state, log_w, env)
    _assert_componentwise_close([actual_residual[f"residual_{i}"] for i in range(1, 4)], expected_residual)


def _log_uniform(min_value: float, max_value: float):
    return st.floats(np.log(min_value), np.log(max_value), allow_nan=False, allow_infinity=False).map(np.exp)


@st.composite
def physically_valid_cases(draw):
    env = Environment(
        T=draw(st.floats(190.0, 235.0, allow_nan=False, allow_infinity=False)),
        p=draw(st.floats(15_000.0, 60_000.0, allow_nan=False, allow_infinity=False)),
        w=draw(_log_uniform(0.005, 2.0)),
        F=draw(st.floats(0.05, 1.0, allow_nan=False, allow_infinity=False)),
        N_a=draw(_log_uniform(3.0e8, 1.0e10)),
        Δz=draw(st.floats(50.0, 500.0, allow_nan=False, allow_infinity=False)),
        include_evaporation=draw(st.booleans()),
    )
    state = (
        draw(_log_uniform(1.0e1, 1.0e9)),
        draw(_log_uniform(1.0e-12, 1.0e-3)),
        draw(st.floats(0.8, 1.8, allow_nan=False, allow_infinity=False)),
    )
    return EquivalenceCase(env=env, state=state)


@pytest.mark.parametrize(
    "case",
    [
        # Figure 1 pressure/sedimentation with exact temperatures and velocity endpoints/midpoint.
        EquivalenceCase(Environment(p=30_000.0, T=190.0, w=0.005, F=1.0), (1.0e4, 1.0e-8, 1.30)),
        EquivalenceCase(Environment(p=30_000.0, T=210.0, w=0.1, F=1.0), (1.0e5, 1.0e-7, 1.35)),
        EquivalenceCase(Environment(p=30_000.0, T=230.0, w=2.0, F=1.0), (1.0e6, 1.0e-6, 1.40)),
        # Figure 4 environment with representative updraft speeds.
        EquivalenceCase(Environment(p=30_000.0, T=225.0, w=0.01, F=1.0), (1.0e4, 1.0e-6, 1.20)),
        EquivalenceCase(Environment(p=30_000.0, T=225.0, w=0.1, F=1.0), (1.0e4, 1.0e-6, 1.40)),
        EquivalenceCase(Environment(p=30_000.0, T=225.0, w=1.0, F=1.0), (1.0e5, 1.0e-5, 1.60)),
        # Optional environment fields and evaporation switch are part of the evaluator contract.
        EquivalenceCase(
            Environment(p=45_000.0, T=215.0, w=0.25, F=0.5, N_a=1.0e10, Δz=250.0, include_evaporation=True),
            (1.0e6, 1.0e-5, 0.9),
        ),
    ],
)
def test_fortran_evaluator_smoke_cases_match_python(fortran_evaluator, case):
    _compare_case(fortran_evaluator, case)


@given(physically_valid_cases())
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fortran_evaluator_matches_python_for_generated_physical_cases(fortran_evaluator, case):
    _compare_case(fortran_evaluator, case)


def test_fortran_rejects_invalid_unregularized_cloud_state(fortran_evaluator):
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    result = subprocess.run(
        [str(fortran_evaluator), "rhs", *map(str, _required_environment_args(env)), "0.0", "1.0e-6", "1.4", *map(str, _optional_environment_args(env))],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "strictly positive" in result.stdout


def test_shared_auto_expected_installation_path_exists():
    auto = Path("/usr/local/bin/auto")
    if not auto.exists():
        pytest.skip("AUTO-07p is not installed at /usr/local/bin/auto")
    assert auto.is_file()
