"""Reusable analysis primitives for oscillatory trajectories.

Cycles are delimited by successive *refined local maxima* of a scalar signal
(typically the saturation ratio).  A cycle is retained only when a local
minimum lies strictly between its bounding maxima, so partial trajectory ends
and malformed oscillations are excluded.  Peak times and values are refined
with a local quadratic through the three adjacent irregular samples.

The orbit metric treats each supplied trajectory as one complete cycle.  It
linearly resamples both on normalized phase, normalizes every state component
by its peak-to-peak range across both orbits, and reports the minimum RMS
separation over cyclic phase shifts.  It is consequently symmetric and a phase
shift alone does not constitute orbit disagreement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.signal import find_peaks


@dataclass(frozen=True)
class Extremum:
    """A sampled local extremum with a locally refined time and value."""

    index: int
    time: float
    value: float


@dataclass(frozen=True)
class Cycle:
    """One complete maximum-to-maximum cycle of a scalar trajectory."""

    start: Extremum
    minimum: Extremum
    end: Extremum
    period: float
    amplitude: float

    @property
    def maximum(self) -> Extremum:
        """The larger of the two bounding maxima."""
        return self.start if self.start.value >= self.end.value else self.end


@dataclass(frozen=True)
class CycleExtraction:
    """Detected extrema and complete cycles, in chronological order."""

    maxima: tuple[Extremum, ...]
    minima: tuple[Extremum, ...]
    cycles: tuple[Cycle, ...]


@dataclass(frozen=True)
class DriftAnalysis:
    """Late-cycle relative drift and the associated threshold decision."""

    cycle_count: int
    window: int
    period_drifts: np.ndarray
    amplitude_drifts: np.ndarray
    threshold: float
    converged: bool


@dataclass(frozen=True)
class OrbitDistance:
    """Phase-independent normalized RMS distance between two complete orbits."""

    distance: float
    phase_shift: float
    samples: int


def _validated_signal(
    time: Iterable[float] | np.ndarray, signal: Iterable[float] | np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray(time, dtype=float)
    y = np.asarray(signal, dtype=float)
    if t.ndim != 1 or y.ndim != 1:
        raise ValueError("time and signal must be one-dimensional arrays.")
    if t.size != y.size:
        raise ValueError("time and signal must have the same length.")
    if t.size < 3:
        raise ValueError("time and signal must contain at least three samples.")
    if not (np.isfinite(t).all() and np.isfinite(y).all()):
        raise ValueError("time and signal must contain only finite values.")
    if not np.all(np.diff(t) > 0.0):
        raise ValueError("time must be strictly increasing.")
    return t, y


def _refine_extremum(time: np.ndarray, signal: np.ndarray, index: int) -> Extremum:
    """Refine a sampled extremum with its three-point irregular-grid parabola."""
    local_time = time[index - 1 : index + 2]
    local_signal = signal[index - 1 : index + 2]
    coefficients = np.polyfit(local_time - time[index], local_signal, deg=2)
    curvature, slope, intercept = coefficients
    offset = -slope / (2.0 * curvature) if curvature != 0.0 else 0.0
    # Numerical noise may locate the vertex outside its supporting samples.
    if not np.isfinite(offset) or offset < local_time[0] - time[index] or offset > local_time[-1] - time[index]:
        offset = 0.0
    return Extremum(index=index, time=float(time[index] + offset), value=float(np.polyval(coefficients, offset)))


def extract_cycles(
    time: Iterable[float] | np.ndarray, signal: Iterable[float] | np.ndarray
) -> CycleExtraction:
    """Extract complete maximum-to-maximum cycles from an irregular trajectory.

    Endpoints cannot be extrema because they lack samples on both sides.  Thus,
    portions before the first maximum and after the last maximum are excluded.
    A trajectory with fewer than two maxima, or with no valid intervening
    minimum, returns an extraction with no complete cycles rather than raising.
    Input shape, ordering, and finiteness errors raise :class:`ValueError`.
    """
    t, y = _validated_signal(time, signal)
    maxima = tuple(_refine_extremum(t, y, int(i)) for i in find_peaks(y)[0])
    minima = tuple(_refine_extremum(t, y, int(i)) for i in find_peaks(-y)[0])

    cycles: list[Cycle] = []
    for start, end in zip(maxima[:-1], maxima[1:]):
        interior_minima = [minimum for minimum in minima if start.index < minimum.index < end.index]
        if not interior_minima:
            continue
        minimum = min(interior_minima, key=lambda item: item.value)
        amplitude = max(start.value, end.value) - minimum.value
        cycles.append(
            Cycle(
                start=start,
                minimum=minimum,
                end=end,
                period=end.time - start.time,
                amplitude=float(amplitude),
            )
        )
    return CycleExtraction(maxima=maxima, minima=minima, cycles=tuple(cycles))


def analyze_late_cycle_drift(
    cycles: Iterable[Cycle], *, window: int = 20, threshold: float = 1e-3
) -> DriftAnalysis:
    """Compare each of the final ``window`` cycles with its predecessor.

    Relative drift is ``abs(current - previous) / abs(previous)`` for period
    and peak-to-peak amplitude.  At least ``window + 1`` complete cycles are
    required, because every cycle in the requested window needs a predecessor.
    The standard Episode 007 decision is therefore the default final 20 cycles
    with both drift arrays strictly below ``1e-3``.
    """
    cycle_values = tuple(cycles)
    if window < 1:
        raise ValueError("window must be at least one.")
    if not np.isfinite(threshold) or threshold < 0.0:
        raise ValueError("threshold must be finite and non-negative.")
    if len(cycle_values) < window + 1:
        raise ValueError(f"at least {window + 1} complete cycles are required for a final-{window} drift analysis.")

    selected = cycle_values[-(window + 1) :]
    periods = np.array([cycle.period for cycle in selected], dtype=float)
    amplitudes = np.array([cycle.amplitude for cycle in selected], dtype=float)
    if not (np.isfinite(periods).all() and np.isfinite(amplitudes).all()):
        raise ValueError("cycle periods and amplitudes must be finite.")
    if np.any(periods <= 0.0) or np.any(amplitudes <= 0.0):
        raise ValueError("cycle periods and amplitudes must be positive.")

    period_drifts = np.abs(np.diff(periods)) / np.abs(periods[:-1])
    amplitude_drifts = np.abs(np.diff(amplitudes)) / np.abs(amplitudes[:-1])
    converged = bool(np.all(period_drifts < threshold) and np.all(amplitude_drifts < threshold))
    return DriftAnalysis(
        cycle_count=len(cycle_values),
        window=window,
        period_drifts=period_drifts,
        amplitude_drifts=amplitude_drifts,
        threshold=float(threshold),
        converged=converged,
    )


def _validated_orbit(time: Iterable[float] | np.ndarray, states: Iterable[Iterable[float]] | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray(time, dtype=float)
    values = np.asarray(states, dtype=float)
    if t.ndim != 1 or values.ndim != 2:
        raise ValueError("orbit time must be one-dimensional and states two-dimensional.")
    if values.shape[0] != t.size:
        raise ValueError("orbit states must have one row per time sample.")
    if values.shape[1] == 0:
        raise ValueError("orbit states must include at least one component.")
    _validated_signal(t, values[:, 0])
    if not np.isfinite(values).all():
        raise ValueError("orbit states must contain only finite values.")
    return t, values


def _resample_orbit(time: np.ndarray, states: np.ndarray, samples: int) -> np.ndarray:
    phase_time = time[0] + np.arange(samples, dtype=float) * (time[-1] - time[0]) / samples
    return np.column_stack([np.interp(phase_time, time, states[:, j]) for j in range(states.shape[1])])


def phase_independent_orbit_distance(
    reference_time: Iterable[float] | np.ndarray,
    reference_states: Iterable[Iterable[float]] | np.ndarray,
    candidate_time: Iterable[float] | np.ndarray,
    candidate_states: Iterable[Iterable[float]] | np.ndarray,
    *,
    samples: int = 512,
) -> OrbitDistance:
    """Compare two complete cycles with a symmetric phase-independent metric.

    Inputs are samples covering one complete cycle, including the terminal
    boundary if available.  Components are normalized by their combined
    peak-to-peak range; an effectively constant component uses a small,
    scale-aware floor.  The returned phase shift is in cycles and is applied to
    the candidate relative to the reference.
    """
    if samples < 8:
        raise ValueError("samples must be at least eight.")
    t_ref, states_ref = _validated_orbit(reference_time, reference_states)
    t_candidate, states_candidate = _validated_orbit(candidate_time, candidate_states)
    if states_ref.shape[1] != states_candidate.shape[1]:
        raise ValueError("orbits must have the same number of state components.")

    reference = _resample_orbit(t_ref, states_ref, samples)
    candidate = _resample_orbit(t_candidate, states_candidate, samples)
    combined = np.vstack((reference, candidate))
    magnitude = np.maximum(np.max(np.abs(combined), axis=0), 1.0)
    scale = np.maximum(np.ptp(combined, axis=0), np.sqrt(np.finfo(float).eps) * magnitude)

    distances = np.array(
        [np.sqrt(np.mean(((reference - np.roll(candidate, shift, axis=0)) / scale) ** 2)) for shift in range(samples)]
    )
    best_shift = int(np.argmin(distances))
    phase = np.arange(samples, dtype=float) / samples
    extended_phase = np.r_[phase - 1.0, phase, phase + 1.0]
    extended_candidate = np.vstack((candidate, candidate, candidate))

    def distance_at_shift(shift: float) -> float:
        shifted = np.column_stack(
            [np.interp(phase + shift, extended_phase, extended_candidate[:, component]) for component in range(candidate.shape[1])]
        )
        return float(np.sqrt(np.mean(((reference - shifted) / scale) ** 2)))

    # The discrete scan locates the global basin; bounded refinement avoids
    # making phase-equivalent smooth trajectories appear different merely due
    # to the phase grid resolution.
    initial_shift = -best_shift / samples
    optimized = minimize_scalar(
        distance_at_shift,
        bounds=(initial_shift - 1.0 / samples, initial_shift + 1.0 / samples),
        method="bounded",
        options={"xatol": 1e-12},
    )
    return OrbitDistance(distance=float(optimized.fun), phase_shift=float(optimized.x % 1.0), samples=samples)
