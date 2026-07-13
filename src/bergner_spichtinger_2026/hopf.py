"""Augmented Hopf continuation utilities.

This module represents Hopf points of the paper ODE as an augmented nonlinear
system.  The equilibrium unknowns use continuation-friendly coordinates
``(log(n), log(q), s, log(w))`` so positive ``n``, ``q``, and ``w`` are enforced
by construction.  The Hopf equations, however, are always evaluated with the
physical ODE Jacobian ``d(dn/dt,dq/dt,ds/dt)/d(n,q,s)`` in physical state
coordinates.  This distinction is intentional: log coordinates condition the
nonlinear solve, while the eigenpair condition must describe the physical ODE.

For a fixed temperature ``T`` the packed unknown vector is

``[log_n, log_q, s, log_w, omega, v_r[0:3], v_i[0:3]]``.

The residual enforces equilibrium, ``J v_r + omega v_i = 0``,
``J v_i - omega v_r = 0``, unit eigenvector normalization, real/imaginary
eigenvector orthogonality, and a phase condition relative to the previous
eigenvector.  The orthogonality row prevents nearly collinear real/imaginary
vectors from satisfying the eigenpair equations as a spurious
real-invariant-subspace condition; the phase row removes the remaining arbitrary
complex rotation during continuation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import atan2, exp, log
from typing import Iterable

import numpy as np
from scipy.optimize import least_squares

from .constants import Environment
from .core import coefficients, equilibrium, vector_field
from .residuals import (
    equilibrium_residual,
    log_coordinates_from_physical_state,
    physical_state_from_log_coordinates,
)
from .stability import physical_eigenvalues, physical_jacobian

ArrayLike = Iterable[float] | np.ndarray


@dataclass(frozen=True)
class HopfUnknowns:
    """Packed augmented Hopf unknowns for one fixed-temperature solve."""

    log_state: np.ndarray
    log_w: float
    omega: float
    eigenvector_real: np.ndarray
    eigenvector_imag: np.ndarray

    def pack(self) -> np.ndarray:
        """Return ``[log_state, log_w, omega, v_real, v_imag]`` as a vector."""
        return np.r_[self.log_state, self.log_w, self.omega, self.eigenvector_real, self.eigenvector_imag].astype(float)

    @classmethod
    def unpack(cls, packed: ArrayLike) -> "HopfUnknowns":
        """Create unknowns from an 11-entry packed vector."""
        x = np.asarray(packed, dtype=float)
        if x.shape != (11,):
            raise ValueError("packed Hopf unknown vector must have shape (11,).")
        return cls(
            log_state=np.array(x[0:3], dtype=float),
            log_w=float(x[3]),
            omega=float(x[4]),
            eigenvector_real=np.array(x[5:8], dtype=float),
            eigenvector_imag=np.array(x[8:11], dtype=float),
        )


@dataclass(frozen=True)
class HopfPoint:
    """One corrected Hopf point at a fixed temperature."""

    T_K: float
    unknowns: HopfUnknowns
    residual_norm: float
    equilibrium_residual_norm: float
    eigen_residual_norm: float
    physical_residual_norm: float
    converged: bool
    iterations: int
    message: str

    @property
    def log_w(self) -> float:
        return self.unknowns.log_w

    @property
    def w_m_s(self) -> float:
        return exp(self.unknowns.log_w)

    @property
    def state(self) -> np.ndarray:
        return physical_state_from_log_coordinates(self.unknowns.log_state)

    @property
    def frequency(self) -> float:
        return abs(self.unknowns.omega)


@dataclass(frozen=True)
class HopfBranchResult:
    """A fixed-label Hopf branch followed over requested temperatures."""

    branch_id: str
    seed_T_K: float
    points: list[HopfPoint]

    @property
    def converged(self) -> bool:
        return all(point.converged for point in self.points)


def characteristic_hopf_residual(log_state_and_w: ArrayLike, env: Environment) -> np.ndarray:
    """Four-row Hopf residual using the 3D characteristic-polynomial condition.

    For ``det(lambda I - J) = lambda^3 + a1 lambda^2 + a2 lambda + a3``, a
    simple Hopf point with eigenvalues ``-a1`` and ``+- i sqrt(a2)`` satisfies
    ``a1*a2 - a3 = 0``.  This scalar condition avoids the ill-conditioned
    physical-coordinate eigenvector unknowns while still evaluating ``J`` as the
    physical ODE Jacobian in physical ``(n, q, s)`` coordinates.
    """
    x = np.asarray(log_state_and_w, dtype=float)
    if x.shape != (4,):
        raise ValueError("log_state_and_w must have shape (4,).")
    log_state = x[:3]
    log_w = float(x[3])
    env_w = replace(env, w=exp(log_w))
    coeff = coefficients(env_w)
    state = physical_state_from_log_coordinates(log_state)
    eq = equilibrium_residual(log_state, log_w, env_w, coeff=coeff)
    poly = np.poly(physical_jacobian(state, env=env_w, coeff=coeff))
    a1 = float(poly[1].real)
    a2 = float(poly[2].real)
    a3 = float(poly[3].real)
    hopf = a1 * a2 - a3
    hopf_scale = abs(a1 * a2) + abs(a3) + 1.0e-30
    return np.r_[eq, hopf / hopf_scale]


def solve_characteristic_hopf_point(
    env: Environment,
    initial_log_state_and_w: ArrayLike,
    *,
    tolerance: float = 1e-8,
    max_evaluations: int = 1000,
) -> HopfPoint:
    """Correct one fixed-temperature Hopf point with the characteristic condition."""
    guess = np.asarray(initial_log_state_and_w, dtype=float)
    lower = np.array([-50.0, -90.0, 0.5, -12.0])
    upper = np.array([60.0, 20.0, 5.0, 3.0])
    guess = np.minimum(np.maximum(guess, lower), upper)
    sol = least_squares(
        lambda x: characteristic_hopf_residual(x, env),
        guess,
        bounds=(lower, upper),
        xtol=1e-11,
        ftol=1e-11,
        gtol=1e-11,
        max_nfev=max_evaluations,
        x_scale="jac",
    )
    x = np.asarray(sol.x, dtype=float)
    env_w = replace(env, w=exp(float(x[3])))
    coeff = coefficients(env_w)
    state = physical_state_from_log_coordinates(x[:3])
    eig = physical_eigenvalues(state, env=env_w, coeff=coeff, canonical=True)
    omega = abs(float(eig[0].imag))
    residual = characteristic_hopf_residual(x, env)
    rhs = vector_field(float(state[0]), float(state[1]), float(state[2]), env_w, coeff)
    # Retain HopfPoint for schema compatibility; eigenvectors are not used by
    # the characteristic-polynomial solve path.
    unknowns = HopfUnknowns(x[:3], float(x[3]), omega, np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
    return HopfPoint(
        T_K=float(env.T),
        unknowns=unknowns,
        residual_norm=float(np.linalg.norm(residual, ord=2)),
        equilibrium_residual_norm=float(np.linalg.norm(residual[:3], ord=2)),
        eigen_residual_norm=abs(float(residual[3])),
        physical_residual_norm=float(np.linalg.norm(rhs, ord=2)),
        converged=bool(sol.success and np.linalg.norm(residual, ord=2) <= tolerance),
        iterations=int(sol.nfev),
        message=str(sol.message),
    )


def continue_characteristic_hopf_branch(
    base_env: Environment,
    branch_id: str,
    seed_T_K: float,
    seed_w_m_s: float,
    temperatures_K: ArrayLike,
    *,
    tolerance: float = 1e-8,
    max_evaluations: int = 1000,
) -> HopfBranchResult:
    """Continue one Hopf branch using equilibrium plus characteristic Hopf rows."""
    requested = np.asarray(list(temperatures_K), dtype=float)
    if not np.any(np.isclose(requested, seed_T_K, rtol=0.0, atol=1e-12)):
        raise ValueError("temperatures_K must include seed_T_K.")
    seed_env = replace(base_env, T=float(seed_T_K), w=float(seed_w_m_s))
    seed_state = log_coordinates_from_physical_state(equilibrium(seed_env, bracket=(1.000001, 3.0)))
    seed_guess = np.r_[seed_state, log(float(seed_w_m_s))]
    seed_point = solve_characteristic_hopf_point(seed_env, seed_guess, tolerance=tolerance, max_evaluations=max_evaluations)
    points_by_T: dict[float, HopfPoint] = {float(seed_T_K): seed_point}

    def follow(path: np.ndarray) -> None:
        previous = [np.r_[seed_point.unknowns.log_state, seed_point.unknowns.log_w]]
        current_T = float(seed_T_K)
        targets = {float(T) for T in path}
        for target_T in path:
            direction = 1.0 if float(target_T) > current_T else -1.0
            while direction * (float(target_T) - current_T) > 1e-12:
                next_T = current_T + direction * min(1.0, abs(float(target_T) - current_T))
                guess = previous[-1] if len(previous) == 1 else previous[-1] + (previous[-1] - previous[-2])
                point = solve_characteristic_hopf_point(
                    replace(base_env, T=float(next_T), w=exp(float(guess[3]))),
                    guess,
                    tolerance=tolerance,
                    max_evaluations=max_evaluations,
                )
                vector = np.r_[point.unknowns.log_state, point.unknowns.log_w]
                previous.append(vector)
                if float(next_T) in targets:
                    points_by_T[float(next_T)] = point
                current_T = float(next_T)

    follow(np.array(sorted([float(T) for T in requested if T < seed_T_K], reverse=True), dtype=float))
    follow(np.array(sorted([float(T) for T in requested if T > seed_T_K]), dtype=float))
    return HopfBranchResult(branch_id=branch_id, seed_T_K=float(seed_T_K), points=[points_by_T[float(T)] for T in sorted(points_by_T)])


def normalize_eigenvector(v: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Rotate and normalize a complex eigenvector into real/imaginary parts.

    The largest component is made real and non-negative for deterministic seed
    construction.  During continuation, phase is controlled by the residual's
    previous-eigenvector phase row rather than by this helper.
    """
    z = np.asarray(v, dtype=complex)
    if z.shape != (3,):
        raise ValueError("eigenvector must have shape (3,).")
    real0 = z.real.astype(float)
    imag0 = z.imag.astype(float)
    diff = float(np.dot(real0, real0) - np.dot(imag0, imag0))
    cross = float(np.dot(real0, imag0))
    theta = 0.5 * atan2(-2.0 * cross, diff)
    z = z * np.exp(1j * theta)
    real = z.real.astype(float)
    imag = z.imag.astype(float)
    pivot = int(np.argmax(np.abs(real) + np.abs(imag)))
    if real[pivot] < 0.0:
        real = -real
        imag = -imag
    norm = float(np.sqrt(np.dot(real, real) + np.dot(imag, imag)))
    if norm == 0.0:
        raise ValueError("zero eigenvector cannot be normalized.")
    return real / norm, imag / norm


def hopf_phase_condition(
    eigenvector_real: ArrayLike,
    eigenvector_imag: ArrayLike,
    reference_real: ArrayLike,
    reference_imag: ArrayLike,
) -> float:
    """Previous-eigenvector phase condition used to remove complex rotation.

    This is the imaginary part of the complex inner-product alignment with the
    previous eigenvector, written in real arithmetic:
    ``dot(v_r, ref_i) - dot(v_i, ref_r) = 0``.
    """
    vr = np.asarray(eigenvector_real, dtype=float)
    vi = np.asarray(eigenvector_imag, dtype=float)
    rr = np.asarray(reference_real, dtype=float)
    ri = np.asarray(reference_imag, dtype=float)
    for name, arr in {"eigenvector_real": vr, "eigenvector_imag": vi, "reference_real": rr, "reference_imag": ri}.items():
        if arr.shape != (3,):
            raise ValueError(f"{name} must have shape (3,).")
    return float(np.dot(vr, ri) - np.dot(vi, rr))


def initial_hopf_guess_from_equilibrium(env: Environment, w_m_s: float) -> HopfUnknowns:
    """Build an augmented Hopf initial guess from an equilibrium/eigenpair.

    ``env.T`` supplies the seed temperature.  ``w_m_s`` is normally taken from a
    prior scan/interpolated Hopf crossing.  The returned eigenpair is not forced
    to have zero real part; the augmented solve corrects it.
    """
    env_w = replace(env, w=float(w_m_s))
    coeff = coefficients(env_w)
    state = equilibrium(env_w, bracket=(1.000001, 3.0))
    jac = physical_jacobian(state, env=env_w, coeff=coeff)
    values, vectors = np.linalg.eig(jac)
    positive_imag = [i for i, value in enumerate(values) if value.imag > 0.0]
    index = max(positive_imag or range(3), key=lambda i: values[i].imag)
    omega = abs(float(values[index].imag))
    real, imag = normalize_eigenvector(vectors[:, index])
    return HopfUnknowns(log_coordinates_from_physical_state(state), log(float(w_m_s)), omega, real, imag)


def augmented_hopf_residual(
    packed: ArrayLike,
    env: Environment,
    reference_real: ArrayLike,
    reference_imag: ArrayLike,
    *,
    equilibrium_scale: float = 10.0,
) -> np.ndarray:
    """Evaluate the fixed-temperature augmented Hopf residual.

    The environment's ``T`` is fixed and its ``w`` value is replaced by
    ``exp(log_w)`` from the packed unknowns.  Equilibrium rows are the scaled
    log-coordinate residual rows from :mod:`.residuals`; Hopf rows use the
    analytic physical-coordinate Jacobian from :mod:`.stability`.
    """
    unknowns = HopfUnknowns.unpack(packed)
    env_w = replace(env, w=exp(float(np.clip(unknowns.log_w, -12.0, 3.0))))
    coeff = coefficients(env_w)
    state = physical_state_from_log_coordinates(unknowns.log_state)
    jac = physical_jacobian(state, env=env_w, coeff=coeff)
    eq = equilibrium_residual(unknowns.log_state, unknowns.log_w, env_w, coeff=coeff) * equilibrium_scale
    ev_real = jac @ unknowns.eigenvector_real + unknowns.omega * unknowns.eigenvector_imag
    ev_imag = jac @ unknowns.eigenvector_imag - unknowns.omega * unknowns.eigenvector_real
    real_norm_sq = float(np.dot(unknowns.eigenvector_real, unknowns.eigenvector_real))
    imag_norm_sq = float(np.dot(unknowns.eigenvector_imag, unknowns.eigenvector_imag))
    normalization = real_norm_sq + imag_norm_sq - 1.0
    orthogonality = float(np.dot(unknowns.eigenvector_real, unknowns.eigenvector_imag))
    phase = hopf_phase_condition(unknowns.eigenvector_real, unknowns.eigenvector_imag, reference_real, reference_imag)
    return np.r_[eq, ev_real, ev_imag, normalization, orthogonality, phase]


def solve_hopf_point(
    env: Environment,
    guess: HopfUnknowns | ArrayLike,
    reference_real: ArrayLike,
    reference_imag: ArrayLike,
    *,
    tolerance: float = 1e-8,
    max_evaluations: int = 4000,
) -> HopfPoint:
    """Correct one fixed-temperature augmented Hopf point."""
    guess_vector = guess.pack() if isinstance(guess, HopfUnknowns) else np.asarray(guess, dtype=float)
    lower = np.array([-50.0, -90.0, 0.5, -12.0, 1e-10, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf, -np.inf])
    upper = np.array([60.0, 20.0, 5.0, 3.0, 1.0, np.inf, np.inf, np.inf, np.inf, np.inf, np.inf])
    guess_vector = np.minimum(np.maximum(guess_vector, lower), upper)
    sol = least_squares(
        lambda x: augmented_hopf_residual(x, env, reference_real, reference_imag),
        guess_vector,
        bounds=(lower, upper),
        xtol=1e-11,
        ftol=1e-11,
        gtol=1e-11,
        max_nfev=max_evaluations,
        x_scale="jac",
    )
    unknowns = HopfUnknowns.unpack(sol.x)
    residual = augmented_hopf_residual(sol.x, env, reference_real, reference_imag)
    residual_norm = float(np.linalg.norm(residual, ord=2))
    equilibrium_residual_norm = float(np.linalg.norm(residual[:3], ord=2))
    eigen_residual_norm = float(np.linalg.norm(residual[3:9], ord=2))
    env_w = replace(env, w=exp(unknowns.log_w))
    state = physical_state_from_log_coordinates(unknowns.log_state)
    physical_residual_norm = float(np.linalg.norm(vector_field(float(state[0]), float(state[1]), float(state[2]), env_w, coefficients(env_w)), ord=2))
    return HopfPoint(
        T_K=float(env.T),
        unknowns=unknowns,
        residual_norm=residual_norm,
        equilibrium_residual_norm=equilibrium_residual_norm,
        eigen_residual_norm=eigen_residual_norm,
        physical_residual_norm=physical_residual_norm,
        converged=bool(residual_norm <= tolerance),
        iterations=int(sol.nfev),
        message=str(sol.message),
    )


def continue_hopf_branch(
    base_env: Environment,
    branch_id: str,
    seed_T_K: float,
    seed_w_m_s: float,
    temperatures_K: ArrayLike,
    *,
    tolerance: float = 1e-8,
    max_evaluations: int = 4000,
) -> HopfBranchResult:
    """Continue one Hopf branch over fixed requested temperatures.

    Temperatures may be supplied in any order, but they must include
    ``seed_T_K``.  The branch is followed from the seed downward and upward in
    separate predictor-corrector passes, then returned sorted by temperature.
    """
    requested = np.asarray(list(temperatures_K), dtype=float)
    if requested.ndim != 1 or requested.size == 0:
        raise ValueError("temperatures_K must be a non-empty one-dimensional sequence.")
    if not np.any(np.isclose(requested, seed_T_K, rtol=0.0, atol=1e-12)):
        raise ValueError("temperatures_K must include seed_T_K.")

    seed_env = replace(base_env, T=float(seed_T_K), w=float(seed_w_m_s))
    seed_guess = initial_hopf_guess_from_equilibrium(seed_env, seed_w_m_s)
    seed_point = solve_hopf_point(
        seed_env,
        seed_guess,
        seed_guess.eigenvector_real,
        seed_guess.eigenvector_imag,
        tolerance=tolerance,
        max_evaluations=max_evaluations,
    )

    points_by_T: dict[float, HopfPoint] = {float(seed_T_K): seed_point}

    def follow(path: np.ndarray) -> None:
        previous_vectors = [seed_point.unknowns.pack()]
        previous_point = seed_point
        current_T = float(seed_T_K)
        requested_targets = {float(T) for T in path}
        for target_T in path:
            direction = 1.0 if float(target_T) > current_T else -1.0
            while direction * (float(target_T) - current_T) > 1e-12:
                next_T = current_T + direction * min(1.0, abs(float(target_T) - current_T))
                if len(previous_vectors) == 1:
                    guess = previous_vectors[-1]
                else:
                    guess = previous_vectors[-1] + (previous_vectors[-1] - previous_vectors[-2])
                point = solve_hopf_point(
                    replace(base_env, T=float(next_T), w=previous_point.w_m_s),
                    guess,
                    previous_point.unknowns.eigenvector_real,
                    previous_point.unknowns.eigenvector_imag,
                    tolerance=tolerance,
                    max_evaluations=max_evaluations,
                )
                if float(next_T) in requested_targets:
                    points_by_T[float(next_T)] = point
                previous_vectors.append(point.unknowns.pack())
                previous_point = point
                current_T = float(next_T)

    lower_path = np.array(sorted([float(T) for T in requested if T < seed_T_K], reverse=True), dtype=float)
    upper_path = np.array(sorted([float(T) for T in requested if T > seed_T_K]), dtype=float)
    follow(lower_path)
    follow(upper_path)
    return HopfBranchResult(branch_id=branch_id, seed_T_K=float(seed_T_K), points=[points_by_T[float(T)] for T in sorted(points_by_T)])
