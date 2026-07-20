/// <reference lib="webworker" />
import { solveEquilibrium } from "./equilibrium";
import { IntegrationCancelled, integrateTrajectoryAsync } from "./integrator";
import type { MainToWorkerMessage, WorkerToMainMessage } from "./worker-protocol";

const worker = self as unknown as DedicatedWorkerGlobalScope;
const cancelled = new Set<string>();

function post(message: WorkerToMainMessage): void { worker.postMessage(message); }

worker.onmessage = (event: MessageEvent<MainToWorkerMessage>) => {
  const message = event.data;
  if (message.type === "cancel") {
    cancelled.add(message.jobId);
    return;
  }
  // Deferring starts lets a queued cancel be observed before numerical work begins.
  setTimeout(async () => {
    if (cancelled.delete(message.jobId)) { post({ type: "cancelled", jobId: message.jobId }); return; }
    try {
      const equilibrium = solveEquilibrium(message.environment);
      const trajectory = await integrateTrajectoryAsync(message.initialState ?? equilibrium.state, message.environment, message.integration, {
        isCancelled: () => cancelled.has(message.jobId),
        onProgress: ({ time, acceptedSteps }) => post({ type: "progress", jobId: message.jobId, time, acceptedSteps }),
      });
      cancelled.delete(message.jobId);
      post({ type: "result", jobId: message.jobId, equilibrium, trajectory });
    } catch (error) {
      cancelled.delete(message.jobId);
      if (error instanceof IntegrationCancelled) post({ type: "cancelled", jobId: message.jobId });
      else post({ type: "failure", jobId: message.jobId, message: error instanceof Error ? error.message : String(error) });
    }
  }, 0);
};
