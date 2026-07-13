"""Physical Jacobian and eigenvalue utilities for stability analysis.

This module works in the paper's physical state coordinates ``(n, q, s)``.
It deliberately does *not* differentiate the log-coordinate continuation
residual from :mod:`bergner_spichtinger_2026.residuals`.

The analytic Jacobian implemented by :func:`physical_jacobian` is the SymPy
Jacobian of the no-evaporation Bergner & Spichtinger ODE vector field

``dn = A_n E - F C_n n^(1/3) q^(2/3)``
``dq = A_q E + B_q n^(2/3) q^(1/3)(s - 1) - F C_q n^(-2/3) q^(5/3)``
``ds = D w s - A_s E - B_s n^(2/3) q^(1/3)(s - 1)``

where ``E = exp(p1e (s - p2))``.  Reproduce the symbolic derivation with
:func:`derive_physical_jacobian_expressions`; the runtime implementation below
is the generated, hand-transcribed numeric form for efficient evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Literal

import numpy as np

from .constants import Environment
from .core import Coefficients, coefficients

ArrayLike = Iterable[float] | np.ndarray
EigenRegime = Literal["complex_pair", "three_real"]
StabilityClass = Literal["stable", "unstable", "mixed"]


@dataclass(frozen=True)
class EigenvalueClassification:
    """Classification of a three-eigenvalue spectrum.

    Attributes:
        regime: ``"complex_pair"`` when one conjugate pair has imaginary part
            larger than ``imag_tol``; otherwise ``"three_real"``.
        stability: sign classification of real parts using ``real_tol``.
        real_tol: real-part tolerance used for stability decisions.
        imag_tol: imaginary-part tolerance used for regime decisions and
            canonical ordering.
    """

    regime: EigenRegime
    stability: StabilityClass
    real_tol: float
    imag_tol: float


@dataclass(frozen=True)
class HopfCrossing:
    """Linear crossing estimate for ``Re(lambda_pair)`` over ``log(w)``."""

    log_w: float
    w: float
    left_index: int
    right_index: int
    real_part_left: float
    real_part_right: float


def _as_physical_state(n: float | ArrayLike, q: float | None, s: float | None) -> tuple[float, float, float]:
    if q is None and s is None:
        state = np.asarray(n, dtype=float)
        if state.shape != (3,):
            raise ValueError("state must have shape (3,) for (n, q, s).")
        return float(state[0]), float(state[1]), float(state[2])
    if q is None or s is None:
        raise ValueError("Provide either a state vector or all of n, q, and s.")
    return float(n), float(q), float(s)


def physical_jacobian(
    n: float | ArrayLike,
    q: float | None = None,
    s: float | None = None,
    env: Environment | None = None,
    coeff: Coefficients | None = None,
) -> np.ndarray:
    """Evaluate ``d(vector_field)/d(n, q, s)`` in physical coordinates.

    Args:
        n, q, s: either separate physical state components or ``n`` as a
            length-3 state vector with ``q=s=None``.
        env: fixed model environment. Required unless ``coeff`` is supplied;
            still required for ``w`` and ``F``.
        coeff: optional precomputed coefficients for ``env``.

    Returns:
        A ``(3, 3)`` NumPy array whose rows correspond to ``dn/dt``, ``dq/dt``,
        ``ds/dt`` and columns to physical variables ``n``, ``q``, ``s``.

    Notes:
        The analytic formula covers the Figure 2 equilibrium regime with no
        evaporation.  The paper evaporation switch is discontinuous at
        ``s = 1`` and is not included here.
    """
    if env is None:
        raise ValueError("env is required to evaluate the physical Jacobian.")
    if env.include_evaporation:
        raise ValueError("physical_jacobian does not include the discontinuous evaporation term.")
    n0, q0, s0 = _as_physical_state(n, q, s)
    if n0 <= 0.0 or q0 <= 0.0:
        raise ValueError("Physical Jacobian requires positive n and q.")

    c = coeff or coefficients(env)
    E = exp(c.p1e * (s0 - c.p2))
    n_m53 = n0 ** (-5.0 / 3.0)
    n_m23 = n0 ** (-2.0 / 3.0)
    n_m13 = n0 ** (-1.0 / 3.0)
    n_p13 = n0 ** (1.0 / 3.0)
    n_p23 = n0 ** (2.0 / 3.0)
    q_m23 = q0 ** (-2.0 / 3.0)
    q_m13 = q0 ** (-1.0 / 3.0)
    q_p13 = q0 ** (1.0 / 3.0)
    q_p23 = q0 ** (2.0 / 3.0)
    q_p53 = q0 ** (5.0 / 3.0)
    supersat = s0 - 1.0

    jac = np.array(
        [
            [
                -(env.F * c.C_n / 3.0) * n_m23 * q_p23,
                -(2.0 * env.F * c.C_n / 3.0) * n_p13 * q_m13,
                c.A_n * c.p1e * E,
            ],
            [
                (2.0 * c.B_q / 3.0) * n_m13 * q_p13 * supersat
                + (2.0 * env.F * c.C_q / 3.0) * n_m53 * q_p53,
                (c.B_q / 3.0) * n_p23 * q_m23 * supersat
                - (5.0 * env.F * c.C_q / 3.0) * n_m23 * q_p23,
                c.A_q * c.p1e * E + c.B_q * n_p23 * q_p13,
            ],
            [
                -(2.0 * c.B_s / 3.0) * n_m13 * q_p13 * supersat,
                -(c.B_s / 3.0) * n_p23 * q_m23 * supersat,
                c.D * env.w - c.A_s * c.p1e * E - c.B_s * n_p23 * q_p13,
            ],
        ],
        dtype=float,
    )
    return jac


def physical_eigenvalues(
    n: float | ArrayLike,
    q: float | None = None,
    s: float | None = None,
    env: Environment | None = None,
    coeff: Coefficients | None = None,
    *,
    canonical: bool = True,
    imag_tol: float = 1e-10,
) -> np.ndarray:
    """Eigenvalues of the physical ODE Jacobian at a physical state."""
    vals = np.linalg.eigvals(physical_jacobian(n, q, s, env, coeff))
    return canonical_eigenvalues(vals, imag_tol=imag_tol) if canonical else vals


def canonical_eigenvalues(eigenvalues: ArrayLike, *, imag_tol: float = 1e-10) -> np.ndarray:
    """Return a deterministic order for a three-eigenvalue spectrum.

    Complex-pair spectra are ordered as ``[positive-imaginary pair member,
    negative-imaginary pair member, real eigenvalue]``.  Three-real spectra are
    ordered by descending real part.  Tiny imaginary parts within ``imag_tol``
    are canonicalized to exactly zero.
    """
    vals = np.asarray(eigenvalues, dtype=complex)
    if vals.shape != (3,):
        raise ValueError("eigenvalues must have shape (3,).")
    vals = np.array([complex(v.real, 0.0 if abs(v.imag) <= imag_tol else v.imag) for v in vals], dtype=complex)
    complex_idx = [i for i, v in enumerate(vals) if abs(v.imag) > imag_tol]
    if len(complex_idx) >= 2:
        pair_idx = sorted(complex_idx, key=lambda i: vals[i].imag, reverse=True)[:2]
        remaining = [i for i in range(3) if i not in pair_idx]
        real_idx = remaining[0]
        return np.array([vals[pair_idx[0]], vals[pair_idx[1]], vals[real_idx]], dtype=complex)
    order = np.argsort([-v.real for v in vals])
    return vals[order]


def classify_eigenvalues(
    eigenvalues: ArrayLike,
    *,
    real_tol: float = 1e-10,
    imag_tol: float = 1e-10,
) -> EigenvalueClassification:
    """Classify eigenvalue regime and stability using explicit tolerances."""
    vals = canonical_eigenvalues(eigenvalues, imag_tol=imag_tol)
    regime: EigenRegime = "complex_pair" if abs(vals[0].imag) > imag_tol and abs(vals[1].imag) > imag_tol else "three_real"
    real_parts = vals.real
    if np.all(real_parts < -real_tol):
        stability: StabilityClass = "stable"
    elif np.any(real_parts > real_tol):
        stability = "unstable"
    else:
        stability = "mixed"
    return EigenvalueClassification(regime=regime, stability=stability, real_tol=real_tol, imag_tol=imag_tol)


def detect_hopf_crossings(
    log_w: ArrayLike,
    eigenvalues: Iterable[ArrayLike],
    *,
    real_tol: float = 0.0,
    imag_tol: float = 1e-10,
) -> list[HopfCrossing]:
    """Detect simple sign changes of ``Re(lambda_pair)`` over ``log(w)``.

    Only intervals whose endpoints are classified as ``complex_pair`` are used.
    The crossing location is estimated by linear interpolation in ``log(w)``.
    """
    xs = np.asarray(log_w, dtype=float)
    spectra = [canonical_eigenvalues(vals, imag_tol=imag_tol) for vals in eigenvalues]
    if xs.shape != (len(spectra),):
        raise ValueError("log_w and eigenvalues must have the same leading length.")

    pair_reals = np.full(len(spectra), np.nan, dtype=float)
    for i, vals in enumerate(spectra):
        if classify_eigenvalues(vals, real_tol=real_tol, imag_tol=imag_tol).regime == "complex_pair":
            pair_reals[i] = float((vals[0].real + vals[1].real) / 2.0)

    crossings: list[HopfCrossing] = []
    for i in range(len(xs) - 1):
        y0 = pair_reals[i]
        y1 = pair_reals[i + 1]
        if not (np.isfinite(y0) and np.isfinite(y1)):
            continue
        if abs(y0) <= real_tol:
            crossings.append(HopfCrossing(float(xs[i]), float(np.exp(xs[i])), i, i, float(y0), float(y0)))
            continue
        if y0 * y1 < 0.0 or (real_tol > 0.0 and np.sign(y0) != np.sign(y1) and abs(y1) > real_tol):
            x_cross = float(xs[i] - y0 * (xs[i + 1] - xs[i]) / (y1 - y0))
            crossings.append(HopfCrossing(x_cross, float(np.exp(x_cross)), i, i + 1, float(y0), float(y1)))
    return crossings


def derive_physical_jacobian_expressions() -> tuple[tuple[str, str, str], tuple[str, str, str], tuple[str, str, str]]:
    """Reproduce the SymPy derivation for the no-evaporation physical Jacobian.

    Returns a tuple of stringified symbolic rows.  This lightweight provenance
    helper intentionally names coefficients like :class:`~.core.Coefficients`
    fields so the generated expressions can be compared to
    :func:`physical_jacobian`.
    """
    import sympy as sp

    n, q, s, F, w = sp.symbols("n q s F w", positive=True)
    A_n, A_q, A_s, B_q, B_s, C_n, C_q, D, p1e, p2 = sp.symbols(
        "A_n A_q A_s B_q B_s C_n C_q D p1e p2"
    )
    E = sp.exp(p1e * (s - p2))
    vector = sp.Matrix(
        [
            A_n * E - F * C_n * n ** sp.Rational(1, 3) * q ** sp.Rational(2, 3),
            A_q * E + B_q * n ** sp.Rational(2, 3) * q ** sp.Rational(1, 3) * (s - 1)
            - F * C_q * n ** sp.Rational(-2, 3) * q ** sp.Rational(5, 3),
            D * w * s - A_s * E - B_s * n ** sp.Rational(2, 3) * q ** sp.Rational(1, 3) * (s - 1),
        ]
    )
    jac = vector.jacobian(sp.Matrix([n, q, s]))
    return tuple(tuple(str(sp.simplify(jac[i, j])) for j in range(3)) for i in range(3))  # type: ignore[return-value]
