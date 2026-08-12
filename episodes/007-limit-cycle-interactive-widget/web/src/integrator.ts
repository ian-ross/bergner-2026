import { coefficients, processTerms, vectorField, type ProcessTerms, type State } from "./model";
import type { Environment } from "./parameters";

export interface TrajectorySample {
  /** Seconds since the requested initial state. Samples lie on a uniform grid. */
  time: number;
  state: State;
  terms: ProcessTerms;
  tendency: State;
}

export interface IntegrationOptions {
  /** Positive integration duration in seconds. */
  duration: number;
  /** Relative tolerance for each transformed state component. Default: 1e-8. */
  rtol?: number;
  /** Absolute tolerance for each transformed state component. Default: 1e-10. */
  atol?: number;
  /** Initial trial step in seconds. Default: min(maxStep, duration / 1,000). */
  initialStep?: number;
  /** Largest accepted trial step in seconds. Default: duration / 100. */
  maxStep?: number;
  /** Hard cap on accepted RK steps. Default: 200,000. */
  maxAcceptedSteps?: number;
  /** Number of uniform plotting samples, including both endpoints. Default: 1,001. */
  outputSamples?: number;
  /** Hard cap on requested uniform plotting samples. Default: 20,000. */
  maxOutputSamples?: number;
  /** Include every adaptive accepted-step endpoint in the output. Default: false. */
  includeAcceptedSteps?: boolean;
}

export interface IntegrationProgress { time: number; acceptedSteps: number; }
export interface IntegrationResult { samples: TrajectorySample[]; acceptedSteps: number; rejectedSteps: number; }
export interface IntegrationHooks {
  isCancelled?: () => boolean;
  onProgress?: (progress: IntegrationProgress) => void;
  /** Newly completed output-grid samples, suitable for batched worker streaming. */
  onSamples?: (samples: TrajectorySample[]) => void;
}

/** Production profile shared by the widget and its numerical regression tests. */
export function browserIntegrationOptions(duration: number): IntegrationOptions {
  finitePositive("duration", duration);
  return { duration, rtol: 1e-8, atol: 1e-10, maxStep: Math.min(15, duration), outputSamples: 1_001, includeAcceptedSteps: true };
}

export class IntegrationCancelled extends Error {
  constructor() { super("Trajectory integration cancelled."); this.name = "IntegrationCancelled"; }
}

type Coordinates = [number, number, number];

const DOPRI_A: readonly (readonly number[])[] = [
  [], [1 / 5], [3 / 40, 9 / 40], [44 / 45, -56 / 15, 32 / 9],
  [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
  [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656],
  [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84],
];
const DOPRI_B5 = [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0];
const DOPRI_B4 = [5179 / 57600, 0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40];
const SAFETY = 0.9;

function finitePositive(name: string, value: number): void {
  if (!Number.isFinite(value) || value <= 0) throw new RangeError(`${name} must be finite and greater than zero.`);
}
function addScaled(x: Coordinates, stages: Coordinates[], weights: readonly number[], h: number): Coordinates {
  return x.map((value, component) => value + h * weights.reduce((sum, weight, stage) => sum + weight * stages[stage][component], 0)) as Coordinates;
}
function toCoordinates(state: State): Coordinates {
  finitePositive("initial n", state.n); finitePositive("initial q", state.q);
  if (!Number.isFinite(state.s)) throw new RangeError("initial s must be finite.");
  return [Math.log(state.n), Math.log(state.q), state.s];
}
function toState(x: Coordinates): State {
  const n = Math.exp(x[0]), q = Math.exp(x[1]);
  if (!Number.isFinite(n) || !Number.isFinite(q) || !Number.isFinite(x[2])) throw new RangeError("Log-coordinate integration produced a non-finite state.");
  return { n, q, s: x[2] };
}
function hermiteCoordinates(start: Coordinates, end: Coordinates, startDerivative: Coordinates, endDerivative: Coordinates, h: number, fraction: number): Coordinates {
  const f2 = fraction * fraction, f3 = f2 * fraction;
  return start.map((value, i) =>
    (2 * f3 - 3 * f2 + 1) * value
    + (f3 - 2 * f2 + fraction) * h * startDerivative[i]
    + (-2 * f3 + 3 * f2) * end[i]
    + (f3 - f2) * h * endDerivative[i]) as Coordinates;
}
/** Interior stationary points of the cubic Hermite saturation-ratio interpolant. */
function saturationStationaryFractions(start: Coordinates, end: Coordinates, startDerivative: Coordinates, endDerivative: Coordinates, h: number): number[] {
  const y0 = start[2], y1 = end[2], m0 = startDerivative[2], m1 = endDerivative[2];
  const a = 2 * y0 - 2 * y1 + h * (m0 + m1);
  const b = -3 * y0 + 3 * y1 - h * (2 * m0 + m1);
  const c = h * m0;
  if (Math.abs(a) < 1e-15) return Math.abs(b) < 1e-15 ? [] : [-c / (2 * b)].filter((root) => root > 0 && root < 1);
  const discriminant = 4 * b * b - 12 * a * c;
  if (discriminant < 0) return [];
  const root = Math.sqrt(discriminant);
  return [(-2 * b - root) / (6 * a), (-2 * b + root) / (6 * a)].filter((value) => value > 0 && value < 1);
}

/**
 * Adaptive Dormand--Prince 5(4) integration in `(log(n), log(q), s)`.
 *
 * Uniform samples use cubic Hermite dense output in transformed coordinates.
 * Callers may also retain accepted endpoints and saturation stationary points to
 * resolve narrow process peaks. Terms and tendencies are reevaluated at every sample.
 */
function* integrationSteps(initial: State, env: Environment, options: IntegrationOptions, hooks: IntegrationHooks = {}): Generator<IntegrationProgress, IntegrationResult, void> {
  finitePositive("duration", options.duration);
  const rtol = options.rtol ?? 1e-8, atol = options.atol ?? 1e-10;
  finitePositive("rtol", rtol); finitePositive("atol", atol);
  const maxAcceptedSteps = options.maxAcceptedSteps ?? 200_000;
  const maxOutputSamples = options.maxOutputSamples ?? 20_000;
  const outputSamples = options.outputSamples ?? 1_001;
  if (!Number.isInteger(maxAcceptedSteps) || maxAcceptedSteps < 1) throw new RangeError("maxAcceptedSteps must be a positive integer.");
  if (!Number.isInteger(maxOutputSamples) || maxOutputSamples < 2) throw new RangeError("maxOutputSamples must be an integer of at least two.");
  if (!Number.isInteger(outputSamples) || outputSamples < 2 || outputSamples > maxOutputSamples) throw new RangeError("outputSamples must be an integer between two and maxOutputSamples.");
  const maxStep = options.maxStep ?? options.duration / 100;
  finitePositive("maxStep", maxStep);
  const initialStep = options.initialStep ?? Math.min(maxStep, options.duration / 1_000);
  finitePositive("initialStep", initialStep);

  const c = coefficients(env);
  const rhs = (x: Coordinates): Coordinates => {
    const state = toState(x), tendency = vectorField(state, env, c);
    return [tendency.n / state.n, tendency.q / state.q, tendency.s];
  };
  const makeSample = (time: number, x: Coordinates): TrajectorySample => {
    const state = toState(x);
    return { time, state, terms: processTerms(state, env, c), tendency: vectorField(state, env, c) };
  };
  const grid = Array.from({ length: outputSamples }, (_, i) => options.duration * i / (outputSamples - 1));
  const samples = [makeSample(0, toCoordinates(initial))];
  hooks.onSamples?.(samples.slice());
  let nextOutput = 1, t = 0, x = toCoordinates(initial), h = Math.min(maxStep, initialStep);
  let acceptedSteps = 0, rejectedSteps = 0;

  while (t < options.duration) {
    if (hooks.isCancelled?.()) throw new IntegrationCancelled();
    if (acceptedSteps >= maxAcceptedSteps) throw new RangeError(`Accepted-step limit (${maxAcceptedSteps}) exhausted.`);
    h = Math.min(h, maxStep, options.duration - t);
    const stages: Coordinates[] = [];
    try {
      for (let stage = 0; stage < 7; stage += 1) stages.push(rhs(addScaled(x, stages, DOPRI_A[stage], h)));
    } catch (error) {
      throw new RangeError(`Trajectory RHS failed at t=${t}: ${(error as Error).message}`);
    }
    const candidate = addScaled(x, stages, DOPRI_B5, h);
    const embedded = addScaled(x, stages, DOPRI_B4, h);
    if (!candidate.every(Number.isFinite) || !embedded.every(Number.isFinite)) throw new RangeError(`Trajectory produced a non-finite RK stage at t=${t}.`);
    const errorNorm = Math.max(...candidate.map((value, i) => Math.abs(value - embedded[i]) / (atol + rtol * Math.max(Math.abs(x[i]), Math.abs(value)))));
    if (!Number.isFinite(errorNorm)) throw new RangeError(`Trajectory error estimate is non-finite at t=${t}.`);
    if (errorNorm <= 1) {
      const oldT = t, oldX = x, oldDerivative = stages[0], newDerivative = stages[6];
      t += h; x = candidate; acceptedSteps += 1;
      const completedSamples: TrajectorySample[] = [], sampleTimes: number[] = [];
      while (nextOutput < grid.length && grid[nextOutput] <= t + 1e-12 * Math.max(1, options.duration)) {
        sampleTimes.push(grid[nextOutput]); nextOutput += 1;
      }
      if (options.includeAcceptedSteps) {
        sampleTimes.push(...saturationStationaryFractions(oldX, x, oldDerivative, newDerivative, h).map((fraction) => oldT + fraction * h));
        sampleTimes.push(t);
      }
      sampleTimes.sort((left, right) => left - right);
      for (const sampleTime of sampleTimes) {
        if (Math.abs((samples.at(-1)?.time ?? -1) - sampleTime) <= 1e-10 * Math.max(1, sampleTime)) continue;
        const fraction = (sampleTime - oldT) / h;
        const sample = makeSample(sampleTime, fraction >= 1 - 1e-12 ? x : hermiteCoordinates(oldX, x, oldDerivative, newDerivative, h, fraction));
        samples.push(sample); completedSamples.push(sample);
      }
      if (completedSamples.length) hooks.onSamples?.(completedSamples);
      const progress = { time: t, acceptedSteps };
      hooks.onProgress?.(progress);
      yield progress;
      h *= errorNorm === 0 ? 5 : Math.min(5, Math.max(0.2, SAFETY * errorNorm ** (-1 / 5)));
    } else {
      rejectedSteps += 1;
      h *= Math.max(0.1, SAFETY * errorNorm ** (-1 / 5));
    }
    if (!Number.isFinite(h) || h <= Number.EPSILON * Math.max(1, t)) throw new RangeError(`Adaptive RK45 step underflow at t=${t}.`);
  }
  if (nextOutput !== grid.length) throw new Error("Trajectory output grid was not completed.");
  return { samples, acceptedSteps, rejectedSteps };
}

/** Run the RK45 state machine synchronously (useful for deterministic tests). */
export function integrateTrajectory(initial: State, env: Environment, options: IntegrationOptions, hooks: IntegrationHooks = {}): IntegrationResult {
  const steps = integrationSteps(initial, env, options, hooks);
  let current = steps.next();
  while (!current.done) current = steps.next();
  return current.value;
}

/**
 * Run the same RK45 state machine cooperatively. Yielding to the worker event loop
 * after bounded batches lets a `cancel` message update its cancellation predicate.
 */
export async function integrateTrajectoryAsync(initial: State, env: Environment, options: IntegrationOptions, hooks: IntegrationHooks = {}, yieldEveryAcceptedSteps = 32): Promise<IntegrationResult> {
  if (!Number.isInteger(yieldEveryAcceptedSteps) || yieldEveryAcceptedSteps < 1) throw new RangeError("yieldEveryAcceptedSteps must be a positive integer.");
  const steps = integrationSteps(initial, env, options, hooks);
  let current = steps.next(), yielded = 0;
  while (!current.done) {
    yielded += 1;
    if (yielded % yieldEveryAcceptedSteps === 0) await new Promise<void>((resolve) => setTimeout(resolve, 0));
    current = steps.next();
  }
  return current.value;
}
