"""Small reusable continuation primitives for one-parameter branches.

The public API operates on an abstract state vector and scalar control
parameter.  For Bergner & Spichtinger equilibrium work the intended coordinates
are ``(log(n), log(q), s)`` for state and ``log(w)`` for control, but this module
contains no figure- or episode-specific assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
from scipy.optimize import root


ResidualFunction = Callable[[np.ndarray, float], np.ndarray]


@dataclass(frozen=True)
class ContinuationPoint:
    """One corrected point on a continuation branch."""

    state: np.ndarray
    control: float
    residual_norm: float
    converged: bool
    iterations: int | None
    message: str


@dataclass(frozen=True)
class ContinuationResult:
    """Result of following a one-parameter branch over requested controls."""

    points: list[ContinuationPoint]

    @property
    def states(self) -> np.ndarray:
        """Corrected states as an ``(n_points, state_dim)`` array."""
        return np.vstack([point.state for point in self.points])

    @property
    def controls(self) -> np.ndarray:
        """Corrected controls as an ``(n_points,)`` array."""
        return np.array([point.control for point in self.points], dtype=float)

    @property
    def converged(self) -> bool:
        """True when every requested point converged."""
        return all(point.converged for point in self.points)


def _correct_state(
    residual: ResidualFunction,
    state_guess: np.ndarray,
    control: float,
    *,
    tolerance: float,
    max_iterations: int,
) -> ContinuationPoint:
    sol = root(lambda x: residual(np.asarray(x, dtype=float), control), state_guess, method="hybr", options={"maxfev": max_iterations})
    corrected = np.asarray(sol.x, dtype=float)
    residual_norm = float(np.linalg.norm(residual(corrected, control), ord=2))
    converged = bool(sol.success and residual_norm <= tolerance)
    return ContinuationPoint(
        state=corrected,
        control=float(control),
        residual_norm=residual_norm,
        converged=converged,
        iterations=getattr(sol, "nfev", None),
        message=str(sol.message),
    )


def continue_branch(
    residual: ResidualFunction,
    initial_state: Iterable[float] | np.ndarray,
    controls: Iterable[float] | np.ndarray,
    *,
    tolerance: float = 1e-9,
    max_iterations: int = 100,
    stop_on_failure: bool = True,
) -> ContinuationResult:
    """Follow a branch by predictor-corrector continuation at fixed controls.

    ``controls`` are the requested scalar continuation-parameter values.  The
    first point is corrected from ``initial_state``. Later points use a secant
    predictor from the previous two corrected states, falling back to the latest
    corrected state for the second point.

    This is deliberately modest: it provides a transparent package-level smoke
    continuation primitive for monotone control paths and independent backend
    comparisons, not a replacement for full pseudo-arclength packages such as
    AUTO/LOCA.
    """
    control_values = np.asarray(list(controls), dtype=float)
    if control_values.ndim != 1 or control_values.size == 0:
        raise ValueError("controls must be a non-empty one-dimensional sequence.")

    state0 = np.asarray(initial_state, dtype=float)
    if state0.ndim != 1:
        raise ValueError("initial_state must be a one-dimensional state vector.")

    points: list[ContinuationPoint] = []
    for i, control in enumerate(control_values):
        if i == 0:
            guess = state0
        elif i == 1:
            guess = points[-1].state
        else:
            c0 = points[-2].control
            c1 = points[-1].control
            if c1 == c0:
                guess = points[-1].state
            else:
                tangent = (points[-1].state - points[-2].state) / (c1 - c0)
                guess = points[-1].state + tangent * (float(control) - c1)

        point = _correct_state(residual, guess, float(control), tolerance=tolerance, max_iterations=max_iterations)
        points.append(point)
        if stop_on_failure and not point.converged:
            break

    return ContinuationResult(points=points)
