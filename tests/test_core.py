import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients, equilibrium, process_terms, vector_field


def test_coefficients_positive_for_figure4_environment():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    c = coefficients(env)
    for name in ["ρ", "D", "p_si", "p1e", "A_n", "A_q", "A_s", "B_q", "B_s", "C_n", "C_q"]:
        assert getattr(c, name) > 0, name
    assert 1.0 < c.p2 < 2.0


def test_vector_field_sedimentation_sinks_are_negative():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    terms = process_terms(n=1.0e4, q=1.0e-6, s=1.4, env=env)
    assert terms["Sed_n"] < 0
    assert terms["Sed_q"] < 0
    assert terms["Dep_q"] > 0
    assert terms["Dep_s"] < 0
    assert terms["Cool"] > 0


def test_unregularized_rhs_rejects_zero_cloud_state():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    with pytest.raises(ValueError):
        vector_field(0.0, 1.0e-6, 1.4, env)
    with pytest.raises(ValueError):
        vector_field(1.0e4, 0.0, 1.4, env)


def test_equilibrium_residual_is_small_for_figure4_cases():
    for w in [0.01, 0.1, 1.0]:
        env = Environment(p=30000.0, T=225.0, w=w, F=1.0)
        y = equilibrium(env)
        rhs = vector_field(*y, env)
        assert np.linalg.norm(rhs / np.maximum(np.abs(y), 1.0)) < 1e-8
        assert y[0] > 0
        assert y[1] > 0
        assert 1.0 < y[2] < 2.0
