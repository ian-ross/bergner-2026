import numpy as np
import pytest

from bergner_spichtinger_2026.limit_cycles import (
    Cycle,
    Extremum,
    analyze_late_cycle_drift,
    extract_cycles,
    phase_independent_orbit_distance,
)


def irregular_time(stop, count=4000):
    increments = 1.0 + 0.3 * np.sin(np.arange(count - 1) * 0.37)
    return np.r_[0.0, np.cumsum(increments)] * (stop / np.sum(increments))


def test_extract_cycles_refines_irregular_periodic_signal_and_excludes_edge_segments():
    time = irregular_time(8.0, 3000)
    signal = 1.2 + 0.4 * np.sin(2.0 * np.pi * time)

    extraction = extract_cycles(time, signal)

    assert len(extraction.maxima) == 8
    assert len(extraction.minima) == 8
    assert len(extraction.cycles) == 7
    np.testing.assert_allclose([cycle.period for cycle in extraction.cycles], 1.0, rtol=2e-4)
    np.testing.assert_allclose([cycle.amplitude for cycle in extraction.cycles], 0.8, rtol=2e-4)
    assert extraction.cycles[0].start.time > time[0]
    assert extraction.cycles[-1].end.time < time[-1]


def test_extract_cycles_reports_damped_amplitudes():
    time = irregular_time(12.0)
    signal = 1.0 + np.exp(-0.08 * time) * np.sin(2.0 * np.pi * time)

    cycles = extract_cycles(time, signal).cycles

    assert len(cycles) >= 10
    assert cycles[-1].amplitude < cycles[0].amplitude


def make_cycles(periods, amplitudes):
    cycles = []
    time = 0.0
    for period, amplitude in zip(periods, amplitudes):
        start = Extremum(index=0, time=time, value=amplitude / 2.0)
        minimum = Extremum(index=1, time=time + period / 2.0, value=-amplitude / 2.0)
        end = Extremum(index=2, time=time + period, value=amplitude / 2.0)
        cycles.append(Cycle(start=start, minimum=minimum, end=end, period=period, amplitude=amplitude))
        time += period
    return cycles


def test_final_twenty_cycle_drift_uses_predecessors_and_approved_threshold():
    steady = make_cycles(np.ones(21), np.full(21, 2.0))

    analysis = analyze_late_cycle_drift(steady)

    assert analysis.window == 20
    assert analysis.converged
    np.testing.assert_array_equal(analysis.period_drifts, np.zeros(20))
    np.testing.assert_array_equal(analysis.amplitude_drifts, np.zeros(20))


@pytest.mark.parametrize(
    ("periods", "amplitudes"),
    [
        (1.0 + 0.002 * np.arange(21), np.full(21, 2.0)),
        (np.ones(21), 2.0 + 0.004 * np.arange(21)),
    ],
)
def test_drifting_cycles_fail_threshold(periods, amplitudes):
    analysis = analyze_late_cycle_drift(make_cycles(periods, amplitudes))

    assert not analysis.converged
    assert np.any(analysis.period_drifts > 1e-3) or np.any(analysis.amplitude_drifts > 1e-3)


def test_phase_independent_orbit_distance_accepts_phase_shifted_orbits():
    reference_time = irregular_time(1.0, 1500)
    candidate_time = irregular_time(1.0, 1800)
    reference = np.column_stack((2.0 * np.sin(2 * np.pi * reference_time), np.cos(2 * np.pi * reference_time)))
    shifted = candidate_time + 0.173
    candidate = np.column_stack((2.0 * np.sin(2 * np.pi * shifted), np.cos(2 * np.pi * shifted)))

    result = phase_independent_orbit_distance(reference_time, reference, candidate_time, candidate)

    assert result.distance < 1e-3
    assert result.samples == 512


def test_phase_independent_orbit_distance_detects_different_orbits():
    time = np.linspace(0.0, 1.0, 1001)
    reference = np.column_stack((np.sin(2 * np.pi * time), np.cos(2 * np.pi * time)))
    candidate = np.column_stack((1.3 * np.sin(2 * np.pi * time), np.cos(2 * np.pi * time)))

    assert phase_independent_orbit_distance(time, reference, time, candidate).distance > 0.05


@pytest.mark.parametrize(
    ("time", "signal", "message"),
    [
        ([0.0, 1.0], [0.0, 1.0], "at least three"),
        ([0.0, 1.0, 1.0], [0.0, 1.0, 0.0], "strictly increasing"),
        ([0.0, 1.0, np.nan], [0.0, 1.0, 0.0], "finite"),
        ([0.0, 1.0, 2.0], [0.0, np.inf, 0.0], "finite"),
    ],
)
def test_extract_cycles_rejects_invalid_input(time, signal, message):
    with pytest.raises(ValueError, match=message):
        extract_cycles(time, signal)


def test_incomplete_and_insufficient_cycles_have_explicit_behavior():
    extraction = extract_cycles(np.linspace(0.0, 0.75, 100), np.sin(2 * np.pi * np.linspace(0.0, 0.75, 100)))
    assert extraction.cycles == ()

    with pytest.raises(ValueError, match="at least 21"):
        analyze_late_cycle_drift(make_cycles(np.ones(20), np.ones(20)))

    invalid_final = make_cycles(np.ones(21), np.ones(21))
    invalid_final[-1] = Cycle(
        start=invalid_final[-1].start,
        minimum=invalid_final[-1].minimum,
        end=invalid_final[-1].end,
        period=0.0,
        amplitude=0.0,
    )
    with pytest.raises(ValueError, match="must be positive"):
        analyze_late_cycle_drift(invalid_final)


def test_orbit_distance_rejects_invalid_orbits():
    time = np.linspace(0.0, 1.0, 10)
    states = np.column_stack((time, time))
    with pytest.raises(ValueError, match="same number"):
        phase_independent_orbit_distance(time, states, time, states[:, :1])
    with pytest.raises(ValueError, match="finite"):
        phase_independent_orbit_distance(time, states, time, np.full_like(states, np.nan))
