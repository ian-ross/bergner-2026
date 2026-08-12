import type { State } from "./model";
import { canonicalUiParameters, environmentFromUi, type UiParameters } from "./parameters";

export const DEFAULT_INTEGRATION_DURATION_SECONDS = 60_000;
export const FIGURE4_LIMIT_CYCLE_PERIOD_SECONDS = 2461.6049244675669;
export const DEFAULT_TIME_WINDOW_SECONDS = 5 * FIGURE4_LIMIT_CYCLE_PERIOD_SECONDS;
export const START_OPTIONS = ["paper", "n", "q"] as const;
export type StartOption = (typeof START_OPTIONS)[number];
export const BUDGET_OPTIONS = ["n", "q", "s"] as const;
export type BudgetOption = (typeof BUDGET_OPTIONS)[number];
export type WorkerPhase = "idle" | "running" | "ready" | "failed" | "cancelled";
export function workerTransition(phase: WorkerPhase, event: "start" | "result" | "failure" | "cancelled"): WorkerPhase {
  if (event === "start") return "running";
  if (phase !== "running") return phase;
  return event === "result" ? "ready" : event === "failure" ? "failed" : "cancelled";
}

export interface Controls {
  parameters: UiParameters;
  duration: number;
  start: StartOption;
  budget: BudgetOption;
  playbackSpeed: number;
}

export const figure4Preset: Controls = {
  parameters: canonicalUiParameters,
  duration: DEFAULT_INTEGRATION_DURATION_SECONDS,
  start: "paper",
  budget: "n",
  playbackSpeed: 1,
};

export function validateControls(controls: Controls): void {
  environmentFromUi(controls.parameters);
  if (!START_OPTIONS.includes(controls.start)) throw new RangeError("Choose a supported initial condition.");
  if (!BUDGET_OPTIONS.includes(controls.budget)) throw new RangeError("Choose a supported process-budget component.");
  if (!Number.isFinite(controls.duration) || controls.duration <= 0) {
    throw new RangeError("Integration duration must be a finite number greater than zero seconds.");
  }
  if (!Number.isFinite(controls.playbackSpeed) || controls.playbackSpeed <= 0) {
    throw new RangeError("Playback speed must be a finite number greater than zero.");
  }
}

/** Derive an equilibrium-relative start only after the worker has found equilibrium. */
export function initialStateFor(equilibrium: State, start: StartOption): State {
  switch (start) {
    case "paper": return { n: equilibrium.n * 0.99, q: equilibrium.q * 0.99, s: equilibrium.s * 0.99 };
    case "n": return { ...equilibrium, n: equilibrium.n * 1.01 };
    case "q": return { ...equilibrium, q: equilibrium.q * 1.01 };
  }
}

export const PLAYBACK_SIM_SECONDS_PER_WALL_SECOND = 750;
/** Advance a physical trajectory clock independently of irregular sample density. */
export function advancePlaybackTime(currentTime: number, elapsedMilliseconds: number, speed: number, endTime: number): number {
  return Math.min(endTime, currentTime + elapsedMilliseconds * PLAYBACK_SIM_SECONDS_PER_WALL_SECOND * speed / 1_000);
}
/** Fixed five-cycle window following the current time at its right edge when needed. */
export function timeWindowRange(currentTime: number): [number, number] {
  const start = Math.max(0, currentTime - DEFAULT_TIME_WINDOW_SECONDS);
  return [start, start + DEFAULT_TIME_WINDOW_SECONDS];
}

export function stepLimitRecovery(message: string): string {
  return /Accepted-step limit|outputSamples|maxOutputSamples/.test(message)
    ? `${message} Reduce the integration duration, then run again.`
    : message;
}
