"""Reusable equilibrium residual adapters.

The adapters in this module expose the paper ODE equilibrium equations in
coordinates useful for continuation work: ``(log(n), log(q), s)`` as the state
and ``log(w)`` as the continuation/control parameter.  They do not know about
figures, files, plotting, or episode-specific paths.
"""

from __future__ import annotations

from dataclasses import replace
from math import exp
from typing import Callable, Iterable

import numpy as np

from .constants import Environment
from .core import Coefficients, coefficients, vector_field


ArrayLike = Iterable[float] | np.ndarray


def physical_state_from_log_coordinates(log_state: ArrayLike) -> np.ndarray:
    """Convert ``(log(n), log(q), s)`` to physical ``(n, q, s)``.

    Log coordinates enforce the positive ``n`` and ``q`` domain required by the
    unregularized paper RHS while leaving saturation ratio ``s`` untransformed.
    """
    x = np.asarray(log_state, dtype=float)
    if x.shape != (3,):
        raise ValueError("log_state must have shape (3,) for (log n, log q, s).")
    n = exp(float(x[0]))
    q = exp(float(x[1]))
    return np.array([n, q, float(x[2])], dtype=float)


def log_coordinates_from_physical_state(state: ArrayLike) -> np.ndarray:
    """Convert physical ``(n, q, s)`` to ``(log(n), log(q), s)``.

    Raises:
        ValueError: if ``n`` or ``q`` is non-positive.
    """
    y = np.asarray(state, dtype=float)
    if y.shape != (3,):
        raise ValueError("state must have shape (3,) for (n, q, s).")
    if y[0] <= 0.0 or y[1] <= 0.0:
        raise ValueError("Physical state must have positive n and q for log coordinates.")
    return np.array([np.log(y[0]), np.log(y[1]), y[2]], dtype=float)


def equilibrium_residual(
    log_state: ArrayLike,
    log_w: float,
    env: Environment,
    *,
    coeff: Coefficients | None = None,
    row_scaling: ArrayLike | None = None,
) -> np.ndarray:
    """Evaluate the scaled equilibrium residual in continuation coordinates.

    Args:
        log_state: state vector ``(log(n), log(q), s)``.
        log_w: control parameter ``log(w)``.
        env: fixed environment; its ``w`` value is replaced by ``exp(log_w)``.
        coeff: optional precomputed coefficients for ``env``. Coefficients do
            not depend on ``w``, so they can be reused along a branch at fixed
            pressure/temperature/sedimentation settings.
        row_scaling: optional multiplicative scaling for the residual rows.

    Returns:
        ``[dn/dt / n, dq/dt / q, ds/dt]``, optionally multiplied elementwise by
        ``row_scaling``.
    """
    n, q, s = physical_state_from_log_coordinates(log_state)
    env_w = replace(env, w=exp(float(log_w)))
    c = coeff or coefficients(env_w)
    rhs = vector_field(float(n), float(q), float(s), env_w, c)
    residual = np.array([rhs[0] / n, rhs[1] / q, rhs[2]], dtype=float)
    if row_scaling is not None:
        scaling = np.asarray(row_scaling, dtype=float)
        if scaling.shape != (3,):
            raise ValueError("row_scaling must have shape (3,).")
        residual = residual * scaling
    return residual


def make_equilibrium_residual(
    env: Environment,
    *,
    row_scaling: ArrayLike | None = None,
    coeff: Coefficients | None = None,
) -> Callable[[np.ndarray, float], np.ndarray]:
    """Create a ``residual(log_state, log_w)`` callable for branch tracing."""
    c = coeff or coefficients(env)

    def residual(log_state: np.ndarray, log_w: float) -> np.ndarray:
        return equilibrium_residual(log_state, log_w, env, coeff=c, row_scaling=row_scaling)

    return residual
