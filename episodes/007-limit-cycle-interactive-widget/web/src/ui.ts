import type { State } from "./model";
import { canonicalUiParameters, environmentFromUi, type UiParameters } from "./parameters";

export const FIGURE4_DURATION_SECONDS = 239_118.05830323207;
export const START_OPTIONS = ["paper", "n", "q", "s"] as const;
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
  duration: FIGURE4_DURATION_SECONDS,
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
    case "s": return { ...equilibrium, s: equilibrium.s * 1.01 };
  }
}

export interface ReplayState { index: number; playing: boolean; speed: number; }
export function clampReplayIndex(index: number, sampleCount: number): number {
  return Math.max(0, Math.min(sampleCount - 1, Math.round(index)));
}
export function advanceReplay(state: ReplayState, sampleCount: number, samples: number): ReplayState {
  if (!state.playing) return state;
  const index = clampReplayIndex(state.index + samples, sampleCount);
  return { ...state, index, playing: index < sampleCount - 1 };
}

export function stepLimitRecovery(message: string): string {
  return /Accepted-step limit|outputSamples|maxOutputSamples/.test(message)
    ? `${message} Reduce the integration duration, then run again.`
    : message;
}
