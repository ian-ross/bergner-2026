import Plotly from "plotly.js-dist-min";
import "./style.css";
import { environmentFromUi, type UiParameters } from "./parameters";
import type { IntegrationResult, TrajectorySample } from "./integrator";
import type { MainToWorkerMessage, WorkerToMainMessage } from "./worker-protocol";
import { advanceReplay, figure4Preset, stepLimitRecovery, type BudgetOption, type Controls, type StartOption, validateControls } from "./ui";

const $ = <T extends HTMLElement>(id: string) => document.querySelector<T>(`#${id}`)!;
const inputs = ["T", "pHpa", "w", "F", "nAcm3", "deltaZ", "duration"] as const;
const status = $("status"), equilibrium = $("equilibrium");
const worker = new Worker(new URL("./integration.worker.ts", import.meta.url), { type: "module" });
let activeJob: string | undefined, result: IntegrationResult | undefined, index = 0, playing = false, timer: number | undefined;

function log10(value: number): number { return Math.log10(value); }
function setStatus(message: string, error = false): void { status.textContent = message; status.dataset.error = String(error); }
function numeric(id: string): number { return ($(id) as HTMLInputElement).valueAsNumber; }
function controlValues(): Controls {
  return {
    parameters: { T: numeric("T"), pHpa: numeric("pHpa"), w: 10 ** numeric("w"), F: numeric("F"), nAcm3: 10 ** numeric("nAcm3"), deltaZ: numeric("deltaZ") },
    duration: numeric("duration"), start: document.querySelector<HTMLInputElement>("input[name=start]:checked")!.value as StartOption,
    budget: ($("budget") as HTMLSelectElement).value as BudgetOption,
    playbackSpeed: Number(($("speed") as HTMLSelectElement).value),
  };
}
function setInput(id: string, value: number): void { ($(id) as HTMLInputElement).value = String(value); }
function refreshLogLabels(): void {
  $("w-value").textContent = `${(10 ** numeric("w")).toPrecision(4)} m s⁻¹`;
  $("nAcm3-value").textContent = `${(10 ** numeric("nAcm3")).toPrecision(5)} cm⁻³`;
}
function applyPreset(): void {
  const { parameters, duration, start, budget, playbackSpeed } = figure4Preset;
  setInput("T", parameters.T); setInput("pHpa", parameters.pHpa); setInput("w", log10(parameters.w)); setInput("F", parameters.F); setInput("nAcm3", log10(parameters.nAcm3)); setInput("deltaZ", parameters.deltaZ); setInput("duration", duration);
  document.querySelector<HTMLInputElement>(`input[name=start][value=${start}]`)!.checked = true;
  ($("budget") as HTMLSelectElement).value = budget; ($("speed") as HTMLSelectElement).value = String(playbackSpeed); refreshLogLabels(); invalidate();
}
function setRunning(value: boolean): void { $("run").toggleAttribute("disabled", value); $("cancel").toggleAttribute("disabled", !value); }
function setReplayEnabled(value: boolean): void { ["play", "scrub", "speed", "budget"].forEach((id) => ($(id) as HTMLInputElement).disabled = !value); }
function invalidate(): void { if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage); activeJob = undefined; result = undefined; stopPlayback(); setRunning(false); setReplayEnabled(false); equilibrium.textContent = "Equilibrium: not computed for these controls."; }
function samples(): TrajectorySample[] { return result?.samples ?? []; }

function render(): void {
  const data = samples(); if (!data.length) return;
  const current = data[index], times = data.map((sample) => sample.time);
  Plotly.react("state-plot", [
    { x: times, y: data.map((s) => s.state.n), name: "n", mode: "lines" }, { x: times, y: data.map((s) => s.state.q), name: "q", mode: "lines", yaxis: "y2" }, { x: times, y: data.map((s) => s.state.s), name: "s", mode: "lines", yaxis: "y3" },
  ], { margin: { t: 10 }, xaxis: { title: { text: "time [s]" } }, yaxis: { title: { text: "n [kg dry-air⁻¹]" } }, yaxis2: { title: { text: "q" }, overlaying: "y", side: "right" }, yaxis3: { title: { text: "s" }, anchor: "free", overlaying: "y", side: "right", position: .92 }, shapes: [{ type: "line", x0: current.time, x1: current.time, y0: 0, y1: 1, yref: "paper", line: { dash: "dot" } }] }, { responsive: true });
  const budget = ($("budget") as HTMLSelectElement).value as BudgetOption;
  const terms: Record<BudgetOption, string[]> = { n: ["Nuc_n", "Sed_n"], q: ["Nuc_q", "Dep_q", "Sed_q"], s: ["Cool", "Nuc_s", "Dep_s"] };
  const budgetData = terms[budget].map((term) => ({ x: times, y: data.map((sample) => sample.terms[term as keyof typeof sample.terms]), name: term, mode: "lines" }));
  budgetData.push({ x: times, y: data.map((sample) => sample.tendency[budget]), name: `d${budget}/dt`, mode: "lines" });
  Plotly.react("budget-plot", budgetData, { margin: { t: 10 }, xaxis: { title: { text: "time [s]" } }, yaxis: { title: { text: `${budget} tendency [s⁻¹]` } }, shapes: [{ type: "line", x0: current.time, x1: current.time, y0: 0, y1: 1, yref: "paper", line: { dash: "dot" } }] }, { responsive: true });
  const trail = data.slice(Math.max(0, index - 100), index + 1);
  Plotly.react("orbit-plot", [{ x: data.map((sample) => log10(sample.state.n)), y: data.map((sample) => sample.state.s), name: "orbit", mode: "lines" }, { x: trail.map((sample) => log10(sample.state.n)), y: trail.map((sample) => sample.state.s), name: "recent trail", mode: "lines", line: { width: 4 } }, { x: [log10(current.state.n)], y: [current.state.s], name: "current", mode: "markers", marker: { size: 10 } }], { margin: { t: 10 }, xaxis: { title: { text: "log10(n)" } }, yaxis: { title: { text: "s" } } }, { responsive: true });
}
function stopPlayback(): void { playing = false; if (timer !== undefined) window.clearInterval(timer); timer = undefined; $("play").textContent = "Play"; }
function togglePlayback(): void { if (!result) return; playing = !playing; $("play").textContent = playing ? "Pause" : "Play"; if (!playing) return; timer = window.setInterval(() => { const next = advanceReplay({ index, playing, speed: controlValues().playbackSpeed }, samples().length, Math.max(1, Math.round(controlValues().playbackSpeed))); index = next.index; playing = next.playing; ($("scrub") as HTMLInputElement).value = String(index); render(); if (!playing) stopPlayback(); }, 80); }

worker.onmessage = (event: MessageEvent<WorkerToMainMessage>) => {
  const message = event.data; if (message.jobId !== activeJob) return;
  if (message.type === "progress") setStatus(`Integrating: ${message.time.toFixed(1)} s (${message.acceptedSteps} accepted steps)`);
  if (message.type === "result") { result = message.trajectory; activeJob = undefined; setRunning(false); index = 0; const { n, q, s } = message.equilibrium.state; equilibrium.textContent = `Equilibrium: n=${n.toExponential(5)} kg dry-air⁻¹; q=${q.toExponential(5)} kg kg⁻¹; s=${s.toPrecision(7)} 1.`; const scrub = $("scrub") as HTMLInputElement; scrub.max = String(result.samples.length - 1); scrub.value = "0"; setReplayEnabled(true); setStatus(`Integration complete: ${result.samples.length} samples ready for replay.`); render(); }
  if (message.type === "failure") { activeJob = undefined; setRunning(false); setStatus(`Integration failed: ${stepLimitRecovery(message.message)}`, true); }
  if (message.type === "cancelled") { activeJob = undefined; setRunning(false); setStatus("Trajectory integration cancelled."); }
};

$("preset").addEventListener("click", applyPreset); $("run").addEventListener("click", () => { try { const controls = controlValues(); validateControls(controls); invalidate(); activeJob = crypto.randomUUID(); setRunning(true); setStatus("Computing equilibrium and integrating in worker…"); worker.postMessage({ type: "start", jobId: activeJob, environment: environmentFromUi(controls.parameters), start: controls.start, integration: { duration: controls.duration, outputSamples: 1001 } } satisfies MainToWorkerMessage); } catch (error) { setStatus((error as Error).message, true); } });
$("cancel").addEventListener("click", () => { if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage); }); $("reset").addEventListener("click", () => { invalidate(); setRunning(false); setStatus("Choose parameters and run an integration."); });
$("play").addEventListener("click", togglePlayback); $("scrub").addEventListener("input", () => { index = Number(($("scrub") as HTMLInputElement).value); render(); }); $("budget").addEventListener("change", render); $("speed").addEventListener("change", () => { if (playing) { stopPlayback(); togglePlayback(); } });
inputs.forEach((id) => ($(id) as HTMLInputElement).addEventListener("input", () => { if (id === "w" || id === "nAcm3") refreshLogLabels(); invalidate(); })); document.querySelectorAll("input[name=start]").forEach((input) => input.addEventListener("change", invalidate));
applyPreset(); setReplayEnabled(false); setRunning(false); window.addEventListener("beforeunload", () => { if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage); });
