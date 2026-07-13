from __future__ import annotations

from math import exp

import numpy as np

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.hopf import (
    HopfUnknowns,
    augmented_hopf_residual,
    hopf_phase_condition,
    initial_hopf_guess_from_equilibrium,
    solve_hopf_point,
)


def test_hopf_unknowns_pack_unpack_round_trip() -> None:
    unknowns = HopfUnknowns(
        log_state=np.array([1.0, -2.0, 1.2]),
        log_w=-3.0,
        omega=0.01,
        eigenvector_real=np.array([1.0, 0.0, 0.0]),
        eigenvector_imag=np.array([0.0, 1.0, 0.0]),
    )

    unpacked = HopfUnknowns.unpack(unknowns.pack())

    assert np.allclose(unpacked.log_state, unknowns.log_state)
    assert unpacked.log_w == unknowns.log_w
    assert unpacked.omega == unknowns.omega
    assert np.allclose(unpacked.eigenvector_real, unknowns.eigenvector_real)
    assert np.allclose(unpacked.eigenvector_imag, unknowns.eigenvector_imag)


def test_phase_condition_is_zero_for_self_reference() -> None:
    real = np.array([0.5, 0.25, 0.0])
    imag = np.array([0.0, -0.25, 0.5])

    assert hopf_phase_condition(real, imag, real, imag) == 0.0


def test_t230_lower_augmented_hopf_seed_corrects_to_episode5_landmark() -> None:
    env = Environment(p=30_000.0, T=230.0, w=0.048531, F=1.0, N_a=N_a_figure1_high)
    guess = initial_hopf_guess_from_equilibrium(env, 0.048531)

    point = solve_hopf_point(env, guess, guess.eigenvector_real, guess.eigenvector_imag)
    residual = augmented_hopf_residual(point.unknowns.pack(), env, point.unknowns.eigenvector_real, point.unknowns.eigenvector_imag)

    assert point.converged
    assert abs(point.w_m_s - 0.048531) <= 1e-5
    assert 0.006 < point.frequency < 0.007
    assert np.linalg.norm(residual) <= 1e-8
    assert exp(point.log_w) == point.w_m_s
