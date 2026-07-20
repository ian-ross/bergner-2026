import { canonicalUiParameters, environmentFromUi } from "./parameters";
import type { MainToWorkerMessage, WorkerToMainMessage } from "./worker-protocol";

const app = document.querySelector<HTMLDivElement>("#app");
const worker = new Worker(new URL("./integration.worker.ts", import.meta.url), { type: "module" });
const jobId = crypto.randomUUID();

function send(message: MainToWorkerMessage): void { worker.postMessage(message); }
worker.onmessage = (event: MessageEvent<WorkerToMainMessage>) => {
  const message = event.data;
  if (message.jobId !== jobId || !app) return;
  switch (message.type) {
    case "progress":
      app.textContent = `Integrating: ${message.time.toFixed(1)} s (${message.acceptedSteps} accepted steps)`;
      break;
    case "result":
      app.textContent = `Canonical equilibrium: n=${message.equilibrium.state.n}, q=${message.equilibrium.state.q}, s=${message.equilibrium.state.s}; ${message.trajectory.samples.length} plot samples ready.`;
      break;
    case "failure":
      app.textContent = `Numerical failure: ${message.message}`;
      break;
    case "cancelled":
      app.textContent = "Trajectory integration cancelled.";
      break;
  }
};

if (app) {
  app.textContent = "Computing canonical equilibrium in a worker…";
  send({
    type: "start", jobId, environment: environmentFromUi(canonicalUiParameters),
    // A short default is intentionally responsive; controls can request a longer physical duration.
    integration: { duration: 60, outputSamples: 121 },
  });
  window.addEventListener("beforeunload", () => send({ type: "cancel", jobId }), { once: true });
}
