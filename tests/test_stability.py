import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import equilibrium, vector_field
from bergner_spichtinger_2026.stability import (
    canonical_eigenvalues,
    classify_eigenvalues,
    detect_hopf_crossings,
    derive_physical_jacobian_expressions,
    physical_eigenvalues,
    physical_jacobian,
)


def finite_difference_jacobian(state, env, rel_step=1e-6):
    state = np.asarray(state, dtype=float)
    jac = np.zeros((3, 3), dtype=float)
    for j in range(3):
        step = rel_step * abs(state[j])
        if j == 2:
            step = rel_step
        step = max(step, 1e-14)
        plus = state.copy()
        minus = state.copy()
        plus[j] += step
        minus[j] -= step
        jac[:, j] = (vector_field(*plus, env) - vector_field(*minus, env)) / (2.0 * step)
    return jac


@pytest.mark.parametrize(
    "env",
    [
        Environment(p=30000.0, T=230.0, w=0.001, F=1.0),
        Environment(p=30000.0, T=230.0, w=0.05, F=1.0),
        Environment(p=30000.0, T=230.0, w=1.0, F=1.0),
    ],
)
def test_physical_jacobian_matches_finite_differences_at_figure2_states(env):
    state = equilibrium(env)
    assert state[2] > 1.0

    analytic = physical_jacobian(state, env=env)
    finite_diff = finite_difference_jacobian(state, env)

    np.testing.assert_allclose(analytic, finite_diff, rtol=2e-4, atol=1e-10)


def test_physical_eigenvalues_are_jacobian_eigenvalues_in_canonical_order():
    env = Environment(p=30000.0, T=230.0, w=0.05, F=1.0)
    state = equilibrium(env)

    vals = physical_eigenvalues(state, env=env)
    expected = canonical_eigenvalues(np.linalg.eigvals(physical_jacobian(state, env=env)))

    np.testing.assert_allclose(vals, expected)


def test_sympy_derivation_provenance_includes_expected_physical_terms():
    expressions = derive_physical_jacobian_expressions()

    assert len(expressions) == 3
    assert all(len(row) == 3 for row in expressions)
    assert expressions[0][2] in {
        "A_n*p1e*exp(p1e*(-p2 + s))",
        "A_n*p1e*exp(-p1e*(p2 - s))",
    }
    assert "B_q" in expressions[1][0]
    assert "D*w" in expressions[2][2]


def test_eigenvalue_canonicalization_and_classification_records_tolerances():
    pair = np.array([-3.0 + 2.0j, -7.0 + 0.0j, -3.0 - 2.0j])
    ordered = canonical_eigenvalues(pair, imag_tol=1e-12)

    assert ordered[0].imag > 0.0
    assert ordered[1].imag < 0.0
    assert ordered[2] == pytest.approx(-7.0 + 0.0j)

    classification = classify_eigenvalues(ordered, real_tol=1e-8, imag_tol=1e-12)
    assert classification.regime == "complex_pair"
    assert classification.stability == "stable"
    assert classification.real_tol == 1e-8
    assert classification.imag_tol == 1e-12

    real_ordered = canonical_eigenvalues([-2.0, -5.0, -1.0 + 1e-13j], imag_tol=1e-10)
    np.testing.assert_allclose(real_ordered, [-1.0, -2.0, -5.0])
    assert classify_eigenvalues(real_ordered, imag_tol=1e-10).regime == "three_real"


def test_detect_hopf_crossings_interpolates_pair_real_part_over_log_w():
    log_w = np.log([0.01, 0.1, 1.0])
    spectra = [
        [-0.2 + 1.0j, -0.2 - 1.0j, -2.0],
        [0.1 + 0.8j, 0.1 - 0.8j, -1.5],
        [0.4 + 0.5j, 0.4 - 0.5j, -1.0],
    ]

    crossings = detect_hopf_crossings(log_w, spectra, imag_tol=1e-12)

    assert len(crossings) == 1
    crossing = crossings[0]
    expected = log_w[0] - (-0.2) * (log_w[1] - log_w[0]) / (0.1 - (-0.2))
    assert crossing.log_w == pytest.approx(expected)
    assert crossing.w == pytest.approx(np.exp(expected))
    assert crossing.left_index == 0
    assert crossing.right_index == 1


def test_physical_jacobian_rejects_evaporation_switch():
    env = Environment(p=30000.0, T=230.0, w=0.05, F=1.0, include_evaporation=True)

    with pytest.raises(ValueError, match="evaporation"):
        physical_jacobian([1.0e4, 1.0e-6, 0.9], env=env)
