from math import log

import numpy as np
import pytest

from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.continuation import continue_branch
from bergner_spichtinger_2026.core import equilibrium, vector_field
from bergner_spichtinger_2026.residuals import (
    equilibrium_residual,
    log_coordinates_from_physical_state,
    make_equilibrium_residual,
    physical_state_from_log_coordinates,
)


def test_log_state_residual_matches_normalized_vector_field():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    state = np.array([1.0e4, 1.0e-6, 1.4])
    log_state = log_coordinates_from_physical_state(state)

    residual = equilibrium_residual(log_state, log(env.w), env)
    rhs = vector_field(*state, env)

    np.testing.assert_allclose(residual, [rhs[0] / state[0], rhs[1] / state[1], rhs[2]])


def test_equilibrium_residual_supports_row_scaling():
    env = Environment(p=30000.0, T=225.0, w=0.1, F=1.0)
    state = log_coordinates_from_physical_state([1.0e4, 1.0e-6, 1.4])

    raw = equilibrium_residual(state, log(env.w), env)
    scaled = equilibrium_residual(state, log(env.w), env, row_scaling=[2.0, 0.5, -1.0])

    np.testing.assert_allclose(scaled, raw * np.array([2.0, 0.5, -1.0]))


def test_log_coordinate_helpers_enforce_positive_physical_state():
    log_state = np.array([log(1.0e-30), log(1.0e-20), 1.1])
    physical = physical_state_from_log_coordinates(log_state)

    assert physical[0] > 0.0
    assert physical[1] > 0.0
    assert physical[2] == pytest.approx(1.1)

    with pytest.raises(ValueError):
        log_coordinates_from_physical_state([0.0, 1.0e-6, 1.4])
    with pytest.raises(ValueError):
        log_coordinates_from_physical_state([1.0e4, -1.0e-6, 1.4])


def test_short_log_w_continuation_smoke_case():
    env = Environment(p=30000.0, T=225.0, w=0.01, F=1.0)
    initial = log_coordinates_from_physical_state(equilibrium(env))
    controls = np.log([0.01, 0.012, 0.015])

    result = continue_branch(make_equilibrium_residual(env), initial, controls, tolerance=1e-8)

    assert result.converged
    assert len(result.points) == len(controls)
    np.testing.assert_allclose(result.controls, controls)
    assert np.all(result.states[:, 0] < np.log(1.0e10))
    assert np.all(np.exp(result.states[:, 0]) > 0.0)
    assert np.all(np.exp(result.states[:, 1]) > 0.0)
    assert max(point.residual_norm for point in result.points) < 1e-8
