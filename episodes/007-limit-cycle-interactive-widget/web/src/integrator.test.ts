import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { solveEquilibrium } from "./equilibrium";
import { browserIntegrationOptions, IntegrationCancelled, integrateTrajectory, integrateTrajectoryAsync, type TrajectorySample } from "./integrator";
import { processTerms } from "./model";
import { canonicalUiParameters, environmentFromUi } from "./parameters";

// Row at t=60.50903999700683 s from outputs/reference_trajectory.csv.
const shortHorizonReference = {
  time: 60.50903999700683, n: 35247.381593711834, q: 5.1400203581961392e-6, s: 1.4541132677232809,
  terms: { Nuc_n: 0.2988994076358287, Nuc_q: 2.9889940763582864e-17, Nuc_s: -2.918008437627053e-13,
    Dep_q: 1.4026383360730109e-8, Dep_s: -0.000136932706958955, Evap_n: 0,
    Sed_n: -52.577703287946136, Sed_q: -1.5948521439008765e-8, Cool: 0.0001504731728867183 },
};
const csvRows = readFileSync(new URL("../../outputs/reference_trajectory.csv", import.meta.url), "utf8").trim().split("\n").slice(1)
  .map((line: string) => line.split(",").map(Number));
const canonical = environmentFromUi(canonicalUiParameters);
const close = (actual: number, expected: number, relative = 1e-4) =>
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(Math.max(1e-300, Math.abs(expected) * relative));

function paperStart() {
  const equilibrium = solveEquilibrium(canonical).state;
  return { n: equilibrium.n * 0.99, q: equilibrium.q * 0.99, s: equilibrium.s * 0.99 };
}

function localMaxima(values: number[]): number[] {
  return values.flatMap((value, i) => i > 0 && i < values.length - 1 && value >= values[i - 1] && value > values[i + 1] ? [i] : []);
}
function interpolate(points: number[][], time: number): number[] {
  const right = points.findIndex((point) => point[0] >= time);
  if (right <= 0) return points[Math.max(0, right)].slice(1);
  const before = points[right - 1], after = points[right], fraction = (time - before[0]) / (after[0] - before[0]);
  return before.slice(1).map((value, i) => value + fraction * (after[i + 1] - value));
}
function phaseIndependentDistance(left: number[][], right: number[][]): number {
  const ranges = [0, 1, 2].map((component) => {
    const values = [...left.map((p) => p[component]), ...right.map((p) => p[component])];
    return Math.max(1e-300, Math.max(...values) - Math.min(...values));
  });
  return Math.min(...Array.from({ length: left.length }, (_, shift) => Math.sqrt(left.reduce((sum, point, i) => sum + point.reduce((componentSum, value, component) => componentSum + ((value - right[(i + shift) % right.length][component]) / ranges[component]) ** 2, 0), 0) / (left.length * 3))));
}

describe("adaptive log-coordinate RK45", () => {
  it("matches the Python short-horizon state before phase drift and returns plot-ready rates", () => {
    const result = integrateTrajectory(paperStart(), canonical, {
      duration: shortHorizonReference.time, outputSamples: 2, maxStep: 797.0601943441069 / 15,
    });
    const sample = result.samples.at(-1)!;
    close(sample.state.n, shortHorizonReference.n);
    close(sample.state.q, shortHorizonReference.q);
    close(sample.state.s, shortHorizonReference.s);
    expect(sample.state.n).toBeGreaterThan(0);
    expect(sample.state.q).toBeGreaterThan(0);
    expect(sample.terms).toEqual(processTerms(sample.state, canonical));
    for (const [name, value] of Object.entries(shortHorizonReference.terms)) close(sample.terms[name as keyof typeof sample.terms], value);
    close(sample.tendency.n, sample.terms.Nuc_n + sample.terms.Evap_n + sample.terms.Sed_n, 1e-12);
    close(sample.tendency.q, sample.terms.Nuc_q + sample.terms.Dep_q + sample.terms.Sed_q, 1e-12);
    close(sample.tendency.s, sample.terms.Cool + sample.terms.Nuc_s + sample.terms.Dep_s, 1e-12);
  });

  it("uses the validated browser profile and streams each completed plotting sample", () => {
    const options = browserIntegrationOptions(239_118.05830323207);
    expect(options.maxStep).toBe(15);
    expect(options.outputSamples).toBe(1_001);
    expect(options.includeAcceptedSteps).toBe(true);
    const streamed: TrajectorySample[] = [];
    const result = integrateTrajectory(paperStart(), canonical, { ...options, duration: 120, outputSamples: 5, includeAcceptedSteps: false }, {
      onSamples: (samples) => streamed.push(...samples),
    });
    expect(streamed).toEqual(result.samples);
    expect(streamed.map((sample) => sample.time)).toEqual([0, 30, 60, 90, 120]);
  });

  it("enforces cancellation, invalid-input, step, and output-size limits", async () => {
    expect(() => integrateTrajectory(paperStart(), canonical, { duration: 1 }, { isCancelled: () => true })).toThrow(IntegrationCancelled);
    let cancelled = false;
    await expect(integrateTrajectoryAsync(paperStart(), canonical, { duration: 10, maxStep: 0.01 }, {
      isCancelled: () => cancelled,
      onProgress: () => { cancelled = true; },
    }, 1)).rejects.toThrow(IntegrationCancelled);
    expect(() => integrateTrajectory({ ...paperStart(), n: 0 }, canonical, { duration: 1 })).toThrow(/initial n/);
    expect(() => integrateTrajectory(paperStart(), canonical, { duration: 10, maxAcceptedSteps: 1, maxStep: 0.01 })).toThrow(/Accepted-step limit/);
    expect(() => integrateTrajectory(paperStart(), canonical, { duration: 1, outputSamples: 3, maxOutputSamples: 2 })).toThrow(/outputSamples/);
  });

  it("keeps canonical and damped-regime trajectories positive", () => {
    const canonicalResult = integrateTrajectory(paperStart(), canonical, { duration: 5_000, maxStep: 797.0601943441069 / 15, outputSamples: 501 });
    for (const sample of canonicalResult.samples) { expect(sample.state.n).toBeGreaterThan(0); expect(sample.state.q).toBeGreaterThan(0); }
    const damped = { T: 235, p: 60000, w: 2, F: 1, N_a: 1e10, deltaZ: 500, includeEvaporation: false as const };
    const equilibrium = solveEquilibrium(damped).state;
    const result = integrateTrajectory({ n: equilibrium.n * 1.01, q: equilibrium.q, s: equilibrium.s }, damped, { duration: 1_000, outputSamples: 101 });
    expect(result.samples.at(-1)!.state.n).toBeGreaterThan(0);
    expect(result.samples.at(-1)!.state.q).toBeGreaterThan(0);
  });

  it("reproduces canonical late-cycle period and amplitude to 1e-3", () => {
    const duration = 238_305.99976106847;
    const result = integrateTrajectory(paperStart(), canonical, browserIntegrationOptions(duration));
    const maxima = localMaxima(result.samples.map((sample) => sample.state.s));
    const last = maxima.slice(-2);
    expect(last).toHaveLength(2);
    const states = result.samples.map((sample) => sample.state.s);
    const period = result.samples[last[1]].time - result.samples[last[0]].time;
    const amplitude = Math.max(...states.slice(last[0], last[1] + 1)) - Math.min(...states.slice(last[0], last[1] + 1));
    close(period, 2461.6049244675669, 1e-3);
    close(amplitude, 0.12070503120469511, 1e-3);
    const cycleStart = 235_844.3884928263;
    const browserPoints = result.samples.map((sample) => [sample.time, sample.state.n, sample.state.q, sample.state.s]);
    const browserOrbit = Array.from({ length: 128 }, (_, i) => interpolate(browserPoints, cycleStart + (duration - cycleStart) * i / 127));
    const pythonOrbit = Array.from({ length: 128 }, (_, i) => interpolate(csvRows, cycleStart + (duration - cycleStart) * i / 127));
    // Same symmetric, cyclic-shift-minimized normalized RMS metric as the metadata contract.
    expect(phaseIndependentDistance(browserOrbit, pythonOrbit)).toBeLessThan(1e-3);
    const nucleation = result.samples.map((sample) => sample.terms.Nuc_n);
    const lateNucleationPeaks = localMaxima(nucleation).slice(-20).map((peak) => nucleation[peak]);
    const meanPeak = lateNucleationPeaks.reduce((sum, value) => sum + value, 0) / lateNucleationPeaks.length;
    expect((Math.max(...lateNucleationPeaks) - Math.min(...lateNucleationPeaks)) / meanPeak).toBeLessThan(1e-4);
    close(meanPeak, 1635.8950, 1e-5); // SciPy dense-output maximum over the final three reference cycles.
  }, 30_000);
});
