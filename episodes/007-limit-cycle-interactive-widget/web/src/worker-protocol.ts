import type { EquilibriumResult } from "./equilibrium";
import type { IntegrationOptions, IntegrationResult, TrajectorySample } from "./integrator";
import type { State } from "./model";
import type { Environment } from "./parameters";

export interface StartMessage {
  type: "start";
  jobId: string;
  environment: Environment;
  /** Omit to begin at equilibrium; otherwise the worker derives this from its computed equilibrium. */
  initialState?: State;
  /** Equilibrium-relative perturbation selected by the UI. */
  start?: "paper" | "n" | "q";
  integration: IntegrationOptions;
}
export interface CancelMessage { type: "cancel"; jobId: string; }
export type MainToWorkerMessage = StartMessage | CancelMessage;

export interface EquilibriumMessage {
  type: "equilibrium";
  jobId: string;
  equilibrium: EquilibriumResult;
}
export interface SamplesMessage {
  type: "samples";
  jobId: string;
  samples: TrajectorySample[];
}
export interface ProgressMessage {
  type: "progress";
  jobId: string;
  time: number;
  acceptedSteps: number;
}
export interface ResultMessage {
  type: "result";
  jobId: string;
  equilibrium: EquilibriumResult;
  trajectory: IntegrationResult;
}
export interface FailureMessage {
  type: "failure";
  jobId: string;
  /** A user-displayable numerical or input-validation error; never a raw Error object. */
  message: string;
}
export interface CancelledMessage { type: "cancelled"; jobId: string; }
export type WorkerToMainMessage = EquilibriumMessage | SamplesMessage | ProgressMessage | ResultMessage | FailureMessage | CancelledMessage;
