import type { EquilibriumResult } from "./equilibrium";
import type { IntegrationOptions, IntegrationResult } from "./integrator";
import type { State } from "./model";
import type { Environment } from "./parameters";

export interface StartMessage {
  type: "start";
  jobId: string;
  environment: Environment;
  /** Omit to begin at the worker-computed positive equilibrium. */
  initialState?: State;
  integration: IntegrationOptions;
}
export interface CancelMessage { type: "cancel"; jobId: string; }
export type MainToWorkerMessage = StartMessage | CancelMessage;

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
export type WorkerToMainMessage = ProgressMessage | ResultMessage | FailureMessage | CancelledMessage;
