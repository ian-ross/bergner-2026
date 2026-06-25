import shutil
import subprocess
from math import log
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients, process_terms, vector_field
from bergner_spichtinger_2026.residuals import equilibrium_residual


REPO_ROOT = Path(__file__).resolve().parents[1]
FORTRAN_SOURCES = [
    REPO_ROOT / "auto/src/bs2026_constants.f90",
    REPO_ROOT / "auto/src/bs2026_model.f90",
    REPO_ROOT / "auto/src/bs2026_evaluator.f90",
]


@pytest.fixture(scope="session")
def fortran_evaluator(tmp_path_factory):
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


def test_fortran_coefficients_match_python(fortran_evaluator):
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    actual = _run_evaluator(fortran_evaluator, "coefficients", env.p, env.T, env.w, env.F)
    expected = coefficients(env)

    for key in ["rho", "D", "p_si", "p1e", "p2", "A_n", "A_q", "A_s", "B_q", "B_s", "C_n", "C_q"]:
        python_key = "ρ" if key == "rho" else key
        np.testing.assert_allclose(actual[key], getattr(expected, python_key), rtol=1e-12, atol=1e-300)


def test_fortran_process_terms_and_rhs_match_python(fortran_evaluator):
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    state = (1.0e4, 1.0e-6, 1.4)

    actual_terms = _run_evaluator(fortran_evaluator, "terms", env.p, env.T, env.w, env.F, *state)
    expected_terms = process_terms(*state, env=env)
    for key, expected in expected_terms.items():
        np.testing.assert_allclose(actual_terms[key], expected, rtol=1e-12, atol=1e-300)

    actual_rhs = _run_evaluator(fortran_evaluator, "rhs", env.p, env.T, env.w, env.F, *state)
    expected_rhs = vector_field(*state, env)
    np.testing.assert_allclose(
        [actual_rhs["rhs_1"], actual_rhs["rhs_2"], actual_rhs["rhs_3"]],
        expected_rhs,
        rtol=1e-12,
        atol=1e-300,
    )


def test_fortran_log_coordinate_residual_matches_python(fortran_evaluator):
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    log_state = np.array([log(1.0e4), log(1.0e-6), 1.4])
    log_w = log(env.w)

    actual = _run_evaluator(fortran_evaluator, "residual", env.p, env.T, log_w, env.F, *log_state)
    expected = equilibrium_residual(log_state, log_w, env)

    np.testing.assert_allclose(
        [actual["residual_1"], actual["residual_2"], actual["residual_3"]],
        expected,
        rtol=1e-12,
        atol=1e-300,
    )


def test_shared_auto_expected_installation_path_exists():
    auto = Path("/usr/local/bin/auto")
    if not auto.exists():
        pytest.skip("AUTO-07p is not installed at /usr/local/bin/auto")
    assert auto.is_file()
