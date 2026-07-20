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
  /** Hard cap on requested plotting samples. Default: 20,000. */
  maxOutputSamples?: number;
}

export interface IntegrationProgress { time: number; acceptedSteps: number; }
export interface IntegrationResult { samples: TrajectorySample[]; acceptedSteps: number; rejectedSteps: number; }
export interface IntegrationHooks {
  isCancelled?: () => boolean;
  onProgress?: (progress: IntegrationProgress) => void;
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

/**
 * Adaptive Dormand--Prince 5(4) integration in `(log(n), log(q), s)`.
 *
 * The returned samples are linearly interpolated in these transformed coordinates
 * onto a uniform, endpoint-inclusive grid. Process terms and physical tendencies
 * are evaluated anew at every grid state, so plotting never uses stale RK stages.
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
      const oldT = t, oldX = x;
      t += h; x = candidate; acceptedSteps += 1;
      while (nextOutput < grid.length && grid[nextOutput] <= t + 1e-12 * Math.max(1, options.duration)) {
        const fraction = (grid[nextOutput] - oldT) / h;
        samples.push(makeSample(grid[nextOutput], oldX.map((value, i) => value + fraction * (x[i] - value)) as Coordinates));
        nextOutput += 1;
      }
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
