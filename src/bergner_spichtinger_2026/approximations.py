"""Analytic equilibrium approximations from Bergner & Spichtinger (2026).

This module contains package-level formulas for the Figure 1 / Sec. IV.A
approximation, especially Eqs. (84) and (92)--(94).  Inputs and outputs are
plain SI numeric values, matching :mod:`bergner_spichtinger_2026.core`.
"""

from __future__ import annotations

from dataclasses import replace
from math import log

import numpy as np

from .core import Coefficients, coefficients
from .constants import Environment

S_MIN = 1.37
S_MAX = 1.59
L_MIDPOINT = 0.5 * (log(S_MIN / (S_MIN - 1.0) ** (3.0 / 4.0)) + log(S_MAX / (S_MAX - 1.0) ** (3.0 / 4.0)))


def sigma_equilibrium(env: Environment, *, coeff: Coefficients | None = None) -> float:
    """Return ``sigma(T, p)`` from Eq. (84).

    ``env.w`` is ignored; the formula depends on fixed thermodynamic and
    sedimentation coefficients through pressure, temperature, aerosol loading,
    layer depth, and ``F``-independent constants.
    """
    c = coeff or coefficients(env)
    factor = (c.D * c.C_n / (c.B_s * c.A_n)) * (c.B_q / c.C_q) ** (1.0 / 4.0)
    if factor <= 0.0:
        raise ValueError("Eq. (84) sigma factor must be positive.")
    return c.p2 + (1.0 / c.p1e) * log(factor)


def approximate_equilibrium_s(env: Environment, *, coeff: Coefficients | None = None, l_midpoint: float = L_MIDPOINT) -> float:
    """Approximate equilibrium saturation ratio ``s0`` using Eq. (92)."""
    c = coeff or coefficients(env)
    if env.w <= 0.0:
        raise ValueError("Eq. (92) requires positive vertical velocity w.")
    if env.F <= 0.0:
        raise ValueError("Eq. (92) requires positive sedimentation parameter F.")
    return sigma_equilibrium(env, coeff=c) + (l_midpoint + log(env.w) + (3.0 / 4.0) * log(env.F)) / c.p1e


def approximate_equilibrium(env: Environment, *, coeff: Coefficients | None = None, s0: float | None = None) -> np.ndarray:
    """Approximate physical equilibrium ``(n0, q0, s0)`` using Eqs. (92)--(94).

    Args:
        env: fixed environment with positive ``w`` and ``F``.
        coeff: optional precomputed coefficients for ``env``.
        s0: optional saturation ratio to use in Eqs. (93)--(94).  If omitted,
            Eq. (92) is used for the same ``env``.
    """
    c = coeff or coefficients(env)
    env_w = replace(env, w=float(env.w))
    s = approximate_equilibrium_s(env_w, coeff=c) if s0 is None else float(s0)
    if env_w.w <= 0.0 or env_w.F <= 0.0:
        raise ValueError("Eqs. (93)--(94) require positive w and F.")
    if s <= 1.0:
        raise ValueError("Eqs. (93)--(94) require supersaturation s > 1.")

    n0 = (
        (c.D / c.B_s)
        * (c.C_q / c.B_q) ** (1.0 / 4.0)
        * env_w.w
        * env_w.F ** (1.0 / 4.0)
        * s
        * (s - 1.0) ** (-5.0 / 4.0)
    )
    q0 = (
        (c.D / c.B_s)
        * (c.B_q / c.C_q) ** (1.0 / 2.0)
        * env_w.w
        * env_w.F ** (-1.0 / 2.0)
        * s
        * (s - 1.0) ** (-1.0 / 2.0)
    )
    return np.array([n0, q0, s], dtype=float)
