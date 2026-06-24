import numpy as np

from math import log

from bergner_spichtinger_2026.approximations import L_MIDPOINT, approximate_equilibrium, approximate_equilibrium_s, sigma_equilibrium
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
