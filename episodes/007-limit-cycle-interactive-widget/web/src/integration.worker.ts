/// <reference lib="webworker" />
import { solveEquilibrium } from "./equilibrium";
import { IntegrationCancelled, integrateTrajectoryAsync, type TrajectorySample } from "./integrator";
import type { MainToWorkerMessage, WorkerToMainMessage } from "./worker-protocol";
import { initialStateFor } from "./ui";

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
      post({ type: "equilibrium", jobId: message.jobId, equilibrium });
      const initialState = message.initialState ?? (message.start ? initialStateFor(equilibrium.state, message.start) : equilibrium.state);
      let pendingSamples: TrajectorySample[] = [];
      const flushSamples = () => {
        if (!pendingSamples.length) return;
        post({ type: "samples", jobId: message.jobId, samples: pendingSamples });
        pendingSamples = [];
      };
      const trajectory = await integrateTrajectoryAsync(initialState, message.environment, message.integration, {
        isCancelled: () => cancelled.has(message.jobId),
        onProgress: ({ time, acceptedSteps }) => {
          if (acceptedSteps % 32 === 0) post({ type: "progress", jobId: message.jobId, time, acceptedSteps });
        },
        onSamples: (samples) => {
          pendingSamples.push(...samples);
          if (samples[0]?.time === 0 || pendingSamples.length >= 64) flushSamples();
        },
      });
      flushSamples();
      cancelled.delete(message.jobId);
      post({ type: "result", jobId: message.jobId, equilibrium, trajectory });
    } catch (error) {
      cancelled.delete(message.jobId);
      if (error instanceof IntegrationCancelled) post({ type: "cancelled", jobId: message.jobId });
      else post({ type: "failure", jobId: message.jobId, message: error instanceof Error ? error.message : String(error) });
    }
  }, 0);
};
