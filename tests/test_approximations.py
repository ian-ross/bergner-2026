import numpy as np

from math import log

from bergner_spichtinger_2026.approximations import (
    L_MIDPOINT,
    TABLE_II_HOPF_WA_COEFFICIENTS,
    TABLE_II_HOPF_WB_COEFFICIENTS,
    approximate_equilibrium,
    approximate_equilibrium_s,
    sigma_equilibrium,
    table_ii_hopf_w_a,
    table_ii_hopf_w_b,
    table_ii_lower_hopf_w,
    table_ii_upper_hopf_w,
)
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients


def test_eq92_to_94_approximation_returns_positive_supersaturated_state():
    env = Environment(p=30000.0, T=210.0, w=0.1, F=1.0)

    state = approximate_equilibrium(env)

    assert state.shape == (3,)
    assert state[0] > 0.0
    assert state[1] > 0.0
    assert state[2] > 1.0


def test_eq92_saturation_matches_sigma_formula():
    env = Environment(p=30000.0, T=230.0, w=0.1, F=1.0)
    coeff = coefficients(env)

    s0 = approximate_equilibrium_s(env, coeff=coeff)

    expected = sigma_equilibrium(env, coeff=coeff) + (L_MIDPOINT + log(env.w) + 0.75 * log(env.F)) / coeff.p1e
    np.testing.assert_allclose(s0, expected)
    np.testing.assert_allclose(approximate_equilibrium(env, coeff=coeff)[2], s0)


def test_table_ii_hopf_fit_coefficients_are_paper_values():
    assert TABLE_II_HOPF_WA_COEFFICIENTS.c0 == -38.30947
    assert TABLE_II_HOPF_WA_COEFFICIENTS.c1_per_K == 0.278555
    assert TABLE_II_HOPF_WA_COEFFICIENTS.c2_per_K2 == -0.00049191
    assert TABLE_II_HOPF_WA_COEFFICIENTS.w_bar_m_s == 1.0

    assert TABLE_II_HOPF_WB_COEFFICIENTS.c0 == -36.15046
    assert TABLE_II_HOPF_WB_COEFFICIENTS.c1_per_K == 0.229111
    assert TABLE_II_HOPF_WB_COEFFICIENTS.c2_per_K2 == -0.00036997
    assert TABLE_II_HOPF_WB_COEFFICIENTS.w_bar_m_s == 1.0


def test_table_ii_hopf_fit_values_at_representative_temperatures():
    temperatures = np.array([190.0, 210.0, 230.0, 240.0])

    np.testing.assert_allclose(
        table_ii_hopf_w_a(temperatures),
        np.array([0.04319757152548583, 0.2217618989347088, 0.7680818315601948, 1.233325278481749]),
    )
    np.testing.assert_allclose(
        table_ii_hopf_w_b(temperatures),
        np.array([0.002540772780330422, 0.012870376547913, 0.048492651887080344, 0.08423944495764461]),
    )


def test_table_ii_hopf_fit_scalar_and_vectorized_behavior():
    assert isinstance(table_ii_hopf_w_a(230.0), float)
    assert isinstance(table_ii_hopf_w_b(230.0), float)

    temperatures = np.array([210.0, 230.0])
    wa = table_ii_hopf_w_a(temperatures)
    wb = table_ii_hopf_w_b(temperatures)

    assert wa.shape == temperatures.shape
    assert wb.shape == temperatures.shape
    np.testing.assert_allclose(table_ii_upper_hopf_w(temperatures), wa)
    np.testing.assert_allclose(table_ii_lower_hopf_w(temperatures), wb)
    assert np.all(table_ii_lower_hopf_w(temperatures) < table_ii_upper_hopf_w(temperatures))


def test_table_ii_hopf_fit_outputs_are_positive_on_figure3_temperature_domain():
    temperatures = np.linspace(190.0, 240.0, 101)

    assert np.all(table_ii_hopf_w_a(temperatures) > 0.0)
    assert np.all(table_ii_hopf_w_b(temperatures) > 0.0)
