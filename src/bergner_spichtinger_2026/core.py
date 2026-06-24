"""Paper-faithful numeric core for the ice-cloud oscillator model.

Implements the core ODE RHS requested for Phase 2. Numeric inputs and outputs
are SI values; see individual docstrings. The notation follows Bergner &
Spichtinger (2026) closely: ``n`` is per dry-air mass, ``q`` is ice mass per
dry-air mass, and ``s`` is the saturation ratio over ice.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log, pi
from typing import Iterable

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, root

from . import constants as C
from .constants import Environment


@dataclass(frozen=True)
class Coefficients:
    """Temperature/pressure-dependent coefficients in Eqs. (4)--(6)."""

    ρ: float
    D: float
    p_si: float
    p1e: float
    p2: float
    A_n: float
    A_q: float
    A_s: float
    B_q: float
    B_s: float
    C_n: float
    C_q: float


def ρ_air(p: float, T: float) -> float:
    """Dry-air density from ideal gas law. p [Pa], T [K] -> ρ [kg m^-3]."""
    return p / (C.R_d * T)


def L(T: float) -> float:
    """Latent heat of sublimation, App. A Eqs. (A24)--(A29). T [K] -> J kg^-1."""
    L_mol = C.l0 + C.l1 * T + C.l2 * T**2 + C.l3 * exp(-((T / C.T_l) ** 2))
    return L_mol / C.M_mol_v


def p_si(T: float) -> float:
    """Saturation vapor pressure over hexagonal ice, Eq. (A30). T [K] -> Pa."""
    return exp(C.b0 + C.b1 / T + C.b2 * log(T) + C.b3 * T)


def D_v(T: float, p: float) -> float:
    """Diffusion coefficient of water vapor in air, Eq. (47). T [K], p [Pa] -> m^2 s^-1."""
    return C.D_v0 * (T / C.T0) ** 2 * (C.p0 / p)


def K_T(T: float) -> float:
    """Heat conduction of air, Eq. (A34). T [K] -> W m^-1 K^-1.

    Uses the user-confirmed transcription:
    K_T(T) = (a_K T^b_K) / (T + T_K 10^(c_K/T)).
    """
    return (C.a_K * T**C.b_K) / (T + C.T_K * 10 ** (C.c_K / T))


def G_v(T: float, p: float) -> float:
    """Howell growth factor, Eq. (50). T [K], p [Pa]."""
    Lv = L(T)
    return 1.0 / (((Lv / (C.R_v * T)) - 1.0) * Lv * D_v(T, p) / (T * K_T(T)) + C.R_v * T / p_si(T))


def D(T: float) -> float:
    """Cooling coefficient in ``Cool = D w s``, Eq. (15)/(30)/(38). T [K] -> m^-1."""
    return ((L(T) / (C.c_p * C.R_v * T**2)) - (1.0 / (C.R_d * T))) * C.g


def p1(T: float) -> float:
    """Base-10 nucleation steepness polynomial, Eq. (A18)."""
    return C.p1_a0 + C.p1_a1 * T


def p1e(T: float) -> float:
    """Natural-exponential nucleation steepness ``log(10) p1(T)``, Eq. (A18)."""
    return log(10.0) * p1(T)


def p2(T: float) -> float:
    """Critical saturation fit, Eq. (A19)."""
    return C.p2_as2 * T**2 + C.p2_as1 * T + C.p2_as0


def V_sol() -> float:
    """Mean solution-droplet volume factor, Eq. (A15). -> m^3."""
    c_sol = exp(4.5 * log(C.σ_r) ** 2)
    return (4.0 / 3.0) * pi * C.r_sol**3 * c_sol


def c_radius() -> float:
    """Radius/mass coefficient from Eq. (31): r = c m^(1/3)."""
    return (3.0 / (4.0 * pi * C.ρ_b)) ** (1.0 / 3.0)


def c_fall(p: float, T: float) -> float:
    """Pressure/temperature fall-speed correction, Eq. (55)."""
    return (p / C.p_c) ** C.a_c * (T / C.T_c) ** C.b_c


def coefficients(env: Environment) -> Coefficients:
    """Compute coefficients for Eqs. (4)--(6) for one environment."""
    ρ = ρ_air(env.p, env.T)
    psi = p_si(env.T)
    An = (env.N_a / ρ) * V_sol() * C.J0  # Eq. (A16), n_a=N_a/ρ converts to kg_dry_air^-1.
    Aq = C.m_nuc * An
    As = Aq * env.p / (C.ε * psi)
    Bq = 4.0 * pi * G_v(env.T, env.p) * D_v(env.T, env.p) * c_radius() * C.r0 ** (-1.0 / 9.0)
    Bs = Bq * env.p / (C.ε * psi)
    cf = c_fall(env.p, env.T)
    Cn = cf * C.a_sed * C.r0 ** (-1.0 / 9.0) / env.Δz
    Cq = cf * C.a_sed * C.r0 ** (5.0 / 9.0) / env.Δz
    return Coefficients(
        ρ=ρ,
        D=D(env.T),
        p_si=psi,
        p1e=p1e(env.T),
        p2=p2(env.T),
        A_n=An,
        A_q=Aq,
        A_s=As,
        B_q=Bq,
        B_s=Bs,
        C_n=Cn,
        C_q=Cq,
    )


def H(x: float) -> float:
    """Heaviside switch used in Eq. (12)/(54): 1 for x > 0 else 0."""
    return 1.0 if x > 0.0 else 0.0


def process_terms(n: float, q: float, s: float, env: Environment, coeff: Coefficients | None = None) -> dict[str, float]:
    """Evaluate individual process terms from Sec. II.D.

    n [kg_dry_air^-1], q [kg kg_dry_air^-1], s [1] -> rates per second.
    Requires positive n and q; Eq. (16) regularization is intentionally not used.
    """
    if n <= 0.0 or q <= 0.0:
        raise ValueError("The unregularized paper RHS requires positive n and q.")
    c = coeff or coefficients(env)
    expo = exp(c.p1e * (s - c.p2))
    Nuc_n = c.A_n * expo  # Eq. (7)/(43)
    Nuc_q = c.A_q * expo  # Eq. (8)/(44)
    Nuc_s = -c.A_s * expo  # Eq. (9)/(45)
    Dep_q = c.B_q * n ** (2.0 / 3.0) * q ** (1.0 / 3.0) * (s - 1.0)  # Eq. (10)/(51)
    Dep_s = -c.B_s * n ** (2.0 / 3.0) * q ** (1.0 / 3.0) * (s - 1.0)  # Eq. (11)/(53)
    Evap_n = (n / q) * Dep_q * H(1.0 - s) if env.include_evaporation else 0.0  # Eq. (12)/(54)
    Sed_n = -env.F * c.C_n * n ** (1.0 / 3.0) * q ** (2.0 / 3.0)  # Eq. (13)/(69)
    Sed_q = -env.F * c.C_q * n ** (-2.0 / 3.0) * q ** (5.0 / 3.0)  # Eq. (14)/(70)
    Cool = c.D * env.w * s  # Eq. (15)/(38)
    return {
        "Nuc_n": Nuc_n,
        "Nuc_q": Nuc_q,
        "Nuc_s": Nuc_s,
        "Dep_q": Dep_q,
        "Dep_s": Dep_s,
        "Evap_n": Evap_n,
        "Sed_n": Sed_n,
        "Sed_q": Sed_q,
        "Cool": Cool,
    }


def vector_field(n: float, q: float, s: float, env: Environment, coeff: Coefficients | None = None) -> np.ndarray:
    """Core ODE RHS, Eqs. (4)--(6).

    Args:
        n: ice crystal number concentration [kg_dry_air^-1]
        q: ice crystal mass concentration [kg kg_dry_air^-1]
        s: saturation ratio over ice [1]
        env: fixed environment/parameters

    Returns:
        ``[dn/dt, dq/dt, ds/dt]`` in units of input variable per second.
    """
    terms = process_terms(n, q, s, env, coeff)
    dn = terms["Nuc_n"] + terms["Evap_n"] + terms["Sed_n"]
    dq = terms["Nuc_q"] + terms["Dep_q"] + terms["Sed_q"]
    ds = terms["Cool"] + terms["Nuc_s"] + terms["Dep_s"]
    return np.array([dn, dq, ds], dtype=float)


def rhs(t: float, y: Iterable[float], env: Environment) -> np.ndarray:
    """``solve_ivp`` adapter for Eqs. (4)--(6)."""
    n, q, s = y
    return vector_field(float(n), float(q), float(s), env)


def _equilibrium_guess_from_s(s: float, env: Environment, coeff: Coefficients) -> np.ndarray:
    """Approximate equilibrium relations from Appendix B, Eqs. (B28)--(B35)."""
    mbar = (coeff.B_q * (s - 1.0) / (env.F * coeff.C_q)) ** (3.0 / 4.0)
    n = coeff.A_n * exp(coeff.p1e * (s - coeff.p2)) / (env.F * coeff.C_n * mbar ** (2.0 / 3.0))
    q = n * mbar
    return np.array([n, q, s], dtype=float)


def equilibrium(env: Environment, bracket: tuple[float, float] = (1.000001, 2.0)) -> np.ndarray:
    """Numerically estimate the positive equilibrium for an environment.

    Uses Appendix B scalar relations for an initial guess, then refines the full
    three-equation RHS with ``scipy.optimize.root``.
    """
    coeff = coefficients(env)

    def scalar(s: float) -> float:
        n, q, _ = _equilibrium_guess_from_s(s, env, coeff)
        return vector_field(n, q, s, env, coeff)[2]

    lo, hi = bracket
    grid = np.linspace(lo, hi, 400)
    vals = [scalar(float(x)) for x in grid]
    root_s = None
    for a, b, fa, fb in zip(grid[:-1], grid[1:], vals[:-1], vals[1:]):
        if np.isfinite(fa) and np.isfinite(fb) and fa == 0:
            root_s = float(a)
            break
        if np.isfinite(fa) and np.isfinite(fb) and fa * fb < 0:
            root_s = brentq(scalar, float(a), float(b))
            break
    if root_s is None:
        raise RuntimeError("Could not bracket equilibrium saturation ratio.")

    y0 = _equilibrium_guess_from_s(root_s, env, coeff)

    def residual(logy: np.ndarray) -> np.ndarray:
        # Solve in log(n), log(q), and raw s for positivity/scaling.
        y = np.array([exp(logy[0]), exp(logy[1]), logy[2]])
        scale = np.maximum(np.abs(y), 1.0)
        return vector_field(y[0], y[1], y[2], env, coeff) / scale

    sol = root(residual, np.array([log(y0[0]), log(y0[1]), y0[2]]), method="hybr")
    if not sol.success:
        # The Appendix-B approximation is often already close; return it but make
        # failure visible to callers via RuntimeError only when residual is large.
        res = vector_field(y0[0], y0[1], y0[2], env, coeff)
        if np.linalg.norm(res / np.maximum(np.abs(y0), 1.0)) > 1e-8:
            raise RuntimeError(f"Equilibrium refinement failed: {sol.message}")
        return y0
    return np.array([exp(sol.x[0]), exp(sol.x[1]), sol.x[2]], dtype=float)


def integrate_trajectory(
    env: Environment,
    y0: Iterable[float],
    t_span: tuple[float, float],
    *,
    max_step: float | None = None,
    rtol: float = 1e-7,
    atol: float = 1e-12,
):
    """Integrate Eqs. (4)--(6) with ``scipy.integrate.solve_ivp``."""
    kwargs = {"rtol": rtol, "atol": atol, "method": "LSODA"}
    if max_step is not None:
        kwargs["max_step"] = max_step
    return solve_ivp(lambda t, y: rhs(t, y, env), t_span, np.array(list(y0), dtype=float), **kwargs)
