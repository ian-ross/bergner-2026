import Plotly from "plotly.js-dist-min";
import "./style.css";
import { environmentFromUi } from "./parameters";
import { browserIntegrationOptions, type IntegrationResult, type TrajectorySample } from "./integrator";
import type { MainToWorkerMessage, WorkerToMainMessage } from "./worker-protocol";
import { advancePlaybackTime, figure4Preset, stepLimitRecovery, timeWindowRange, type BudgetOption, type Controls, type StartOption, validateControls } from "./ui";

const $ = <T extends HTMLElement>(id: string) => document.querySelector<T>(`#${id}`)!;
const inputs = ["T", "w", "F", "duration"] as const;
const status = $("status");
const worker = new Worker(new URL("./integration.worker.ts", import.meta.url), { type: "module" });
const plotConfig = { responsive: true, displaylogo: false };
const FIGURE4_ORBIT_X_RANGE: [number, number] = [3.55, 5.28];
const FIGURE4_ORBIT_Y_RANGE: [number, number] = [1.34, 1.495];
let activeJob: string | undefined, result: IntegrationResult | undefined, liveSamples: TrajectorySample[] = [];
let index = 0, replayTime = 0, playing = false, followingLiveRun = false, userPaused = false;
let timer: number | undefined, previousWallTime = 0, plotsReady = false, renderFrame: number | undefined;

function log10(value: number): number { return Math.log10(value); }
function setStatus(message: string, error = false): void { status.textContent = message; status.dataset.error = String(error); }
function numeric(id: string): number { return ($(id) as HTMLInputElement).valueAsNumber; }
function controlValues(): Controls {
  return {
    parameters: { T: numeric("T"), pHpa: figure4Preset.parameters.pHpa, w: 10 ** numeric("w"), F: numeric("F"), nAcm3: figure4Preset.parameters.nAcm3, deltaZ: figure4Preset.parameters.deltaZ },
    duration: numeric("duration"), start: document.querySelector<HTMLInputElement>("input[name=start]:checked")!.value as StartOption,
    budget: ($("budget") as HTMLSelectElement).value as BudgetOption,
    playbackSpeed: Number(($("speed") as HTMLSelectElement).value),
  };
}
function setInput(id: string, value: number): void { ($(id) as HTMLInputElement).value = String(value); }
function refreshLogLabels(): void { $("w-value").textContent = (10 ** numeric("w")).toPrecision(4); }
function applyPreset(): void {
  const { parameters, duration, start, budget, playbackSpeed } = figure4Preset;
  setInput("T", parameters.T); setInput("w", log10(parameters.w)); setInput("F", parameters.F); setInput("duration", duration);
  document.querySelector<HTMLInputElement>(`input[name=start][value=${start}]`)!.checked = true;
  ($("budget") as HTMLSelectElement).value = budget; ($("speed") as HTMLSelectElement).value = String(playbackSpeed); refreshLogLabels(); invalidate();
}
function setRunning(value: boolean): void { $("run").toggleAttribute("disabled", value); $("cancel").toggleAttribute("disabled", !value); }
function setReplayEnabled(value: boolean): void { ["play", "scrub", "speed"].forEach((id) => ($(id) as HTMLInputElement).disabled = !value); }
function clearPlots(): void {
  if (renderFrame !== undefined) cancelAnimationFrame(renderFrame);
  renderFrame = undefined;
  ["state-plot", "budget-plot", "orbit-plot"].forEach((id) => Plotly.purge($(id)));
  plotsReady = false; renderEmptyOrbit();
}
function invalidate(): void {
  if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage);
  activeJob = undefined; result = undefined; liveSamples = []; index = 0; replayTime = 0; followingLiveRun = false; userPaused = false;
  stopPlayback(); setRunning(false); setReplayEnabled(false); clearPlots();
}
function samples(): TrajectorySample[] { return result?.samples ?? liveSamples; }
function sampleIndexAtOrBefore(data: TrajectorySample[], time: number): number {
  let low = 0, high = data.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (data[middle].time <= time) low = middle; else high = middle - 1;
  }
  return low;
}
function cursorState(data: TrajectorySample[], time: number): { time: number; n: number; s: number } {
  const clamped = Math.max(data[0].time, Math.min(time, data.at(-1)!.time));
  index = sampleIndexAtOrBefore(data, clamped);
  const left = data[index], right = data[Math.min(index + 1, data.length - 1)];
  const fraction = right.time === left.time ? 0 : (clamped - left.time) / (right.time - left.time);
  return { time: clamped, n: Math.exp(Math.log(left.state.n) + fraction * (Math.log(right.state.n) - Math.log(left.state.n))), s: left.state.s + fraction * (right.state.s - left.state.s) };
}
function plottedSamples(): TrajectorySample[] {
  const data = samples();
  return followingLiveRun ? data.slice(0, Math.min(data.length, index + 1)) : data;
}
function paddedRange(values: number[], initial: [number, number]): [number, number] {
  if (!values.length) return initial;
  const minimum = Math.min(initial[0], ...values), maximum = Math.max(initial[1], ...values);
  const dataMinimum = Math.min(...values), dataMaximum = Math.max(...values);
  const span = dataMaximum - dataMinimum || Math.max(Math.abs(dataMinimum) * 0.08, 1e-6);
  return [Math.min(initial[0], dataMinimum - span * 0.06), Math.max(initial[1], dataMaximum + span * 0.06, maximum)];
}
function renderEmptyOrbit(): void {
  void Plotly.react($("orbit-plot"), [], { margin: { t: 10 }, xaxis: { title: { text: "log10(n)" }, range: FIGURE4_ORBIT_X_RANGE, autorange: false }, yaxis: { title: { text: "s" }, range: FIGURE4_ORBIT_Y_RANGE, autorange: false } }, plotConfig);
}
function cursorShape(time: number) {
  return { type: "line" as const, x0: time, x1: time, y0: 0, y1: 1, yref: "paper" as const, line: { dash: "dot" as const } };
}
function renderPlots(): void {
  const data = plottedSamples(), available = samples(); if (!data.length) return;
  const current = cursorState(available, replayTime), times = data.map((sample) => sample.time);
  Plotly.react($("state-plot"), [
    { x: times, y: data.map((s) => s.state.n), name: "n", mode: "lines" },
    { x: times, y: data.map((s) => s.state.q), name: "q", mode: "lines", yaxis: "y2" },
    { x: times, y: data.map((s) => s.state.s), name: "s", mode: "lines", yaxis: "y3" },
  ], { margin: { t: 10 }, uirevision: "state", xaxis: { title: { text: "time [s]" }, range: timeWindowRange(current.time), autorange: false }, yaxis: { title: { text: "n [kg dry-air⁻¹]" } }, yaxis2: { title: { text: "q" }, overlaying: "y", side: "right" }, yaxis3: { title: { text: "s" }, anchor: "free", overlaying: "y", side: "right", position: .92 }, shapes: [cursorShape(current.time)] }, plotConfig);
  const budget = ($("budget") as HTMLSelectElement).value as BudgetOption;
  const terms: Record<BudgetOption, string[]> = { n: ["Nuc_n", "Sed_n"], q: ["Nuc_q", "Dep_q", "Sed_q"], s: ["Cool", "Nuc_s", "Dep_s"] };
  const budgetData = terms[budget].map((term) => ({ x: times, y: data.map((sample) => sample.terms[term as keyof typeof sample.terms]), name: term, mode: "lines", line: { simplify: false } }));
  budgetData.push({ x: times, y: data.map((sample) => sample.tendency[budget]), name: `d${budget}/dt`, mode: "lines", line: { simplify: false } });
  Plotly.react($("budget-plot"), budgetData, { margin: { t: 10 }, uirevision: `budget-${budget}`, xaxis: { title: { text: "time [s]" }, range: timeWindowRange(current.time), autorange: false }, yaxis: { title: { text: `${budget} tendency [s⁻¹]` } }, shapes: [cursorShape(current.time)] }, plotConfig);
  const orbitX = data.map((sample) => log10(sample.state.n)), orbitY = data.map((sample) => sample.state.s);
  const trail = available.slice(Math.max(0, index - 100), index + 1);
  Plotly.react($("orbit-plot"), [
    { x: orbitX, y: orbitY, name: "orbit", mode: "lines" },
    { x: trail.map((sample) => log10(sample.state.n)), y: trail.map((sample) => sample.state.s), name: "recent trail", mode: "lines", line: { width: 4 } },
    { x: [log10(current.n)], y: [current.s], name: "current", mode: "markers", marker: { size: 10 } },
  ], { margin: { t: 10 }, uirevision: "orbit", xaxis: { title: { text: "log10(n)" }, range: paddedRange(orbitX, FIGURE4_ORBIT_X_RANGE), autorange: false }, yaxis: { title: { text: "s" }, range: paddedRange(orbitY, FIGURE4_ORBIT_Y_RANGE), autorange: false } }, plotConfig);
  plotsReady = true;
}
function queuePlotRender(): void {
  if (renderFrame !== undefined) return;
  renderFrame = requestAnimationFrame(() => { renderFrame = undefined; renderPlots(); });
}
function renderCursor(): void {
  const data = samples(); if (!plotsReady || !data.length) return;
  const previousIndex = index, current = cursorState(data, replayTime);
  const trail = data.slice(Math.max(0, index - 100), index + 1);
  if (current.time > trail.at(-1)!.time) trail.push({ ...data[index], time: current.time, state: { ...data[index].state, n: current.n, s: current.s } });
  $("time-value").textContent = `${current.time.toFixed(1)} s`;
  ($("scrub") as HTMLInputElement).value = String(index);
  const timeRange = timeWindowRange(current.time);
  void Plotly.relayout($("state-plot"), { "shapes[0].x0": current.time, "shapes[0].x1": current.time, "xaxis.range": timeRange } as never);
  void Plotly.relayout($("budget-plot"), { "shapes[0].x0": current.time, "shapes[0].x1": current.time, "xaxis.range": timeRange } as never);
  void Plotly.restyle($("orbit-plot"), {
    x: [trail.map((sample) => log10(sample.state.n)), [log10(current.n)]],
    y: [trail.map((sample) => sample.state.s), [current.s]],
  }, [1, 2]);
  if (followingLiveRun && index !== previousIndex) queuePlotRender();
}
function stopPlayback(): void { playing = false; if (timer !== undefined) window.clearInterval(timer); timer = undefined; $("play").textContent = "Play"; }
function startPlayback(): void {
  const data = samples(); if (!data.length || playing) return;
  if (!activeJob && replayTime >= data.at(-1)!.time) { replayTime = 0; index = 0; followingLiveRun = false; queuePlotRender(); }
  playing = true; previousWallTime = performance.now(); $("play").textContent = "Pause";
  timer = window.setInterval(() => {
    const available = samples(); if (!available.length) return;
    const now = performance.now(), elapsed = now - previousWallTime; previousWallTime = now;
    replayTime = advancePlaybackTime(replayTime, elapsed, controlValues().playbackSpeed, available.at(-1)!.time);
    renderCursor();
    if (!activeJob && replayTime >= available.at(-1)!.time) { followingLiveRun = false; stopPlayback(); queuePlotRender(); }
  }, 80);
}
function togglePlayback(): void {
  if (playing) { userPaused = true; stopPlayback(); }
  else { userPaused = false; startPlayback(); }
}
worker.onmessage = (event: MessageEvent<WorkerToMainMessage>) => {
  const message = event.data; if (message.jobId !== activeJob) return;
  if (message.type === "samples") {
    liveSamples.push(...message.samples);
    const scrub = $("scrub") as HTMLInputElement; scrub.max = String(liveSamples.length - 1);
    setReplayEnabled(true);
    setStatus(`Integrating trajectory: ${liveSamples.at(-1)!.time.toFixed(1)} s computed; animation follows the selected speed.`);
    if (!playing && !userPaused) startPlayback();
    if (!plotsReady) queuePlotRender();
  }
  if (message.type === "progress") setStatus(`Integrating live trajectory: ${message.time.toFixed(1)} s (${message.acceptedSteps} accepted steps)`);
  if (message.type === "result") {
    result = message.trajectory; liveSamples = []; activeJob = undefined; setRunning(false);
    const scrub = $("scrub") as HTMLInputElement; scrub.max = String(result.samples.length - 1);
    setReplayEnabled(true); setStatus("");
    if (!playing && !userPaused) startPlayback();
  }
  if (message.type === "failure") { activeJob = undefined; setRunning(false); setStatus(`Integration failed: ${stepLimitRecovery(message.message)}`, true); }
  if (message.type === "cancelled") { activeJob = undefined; setRunning(false); setStatus("Trajectory integration cancelled."); }
};

$("preset").addEventListener("click", applyPreset);
$("run").addEventListener("click", () => {
  try {
    const controls = controlValues(); validateControls(controls); invalidate(); followingLiveRun = true; activeJob = crypto.randomUUID(); setRunning(true);
    setStatus("Computing equilibrium; the trajectory will appear as it integrates…");
    worker.postMessage({ type: "start", jobId: activeJob, environment: environmentFromUi(controls.parameters), start: controls.start, integration: browserIntegrationOptions(controls.duration) } satisfies MainToWorkerMessage);
  } catch (error) { setStatus((error as Error).message, true); }
});
$("cancel").addEventListener("click", () => { if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage); });
$("reset").addEventListener("click", () => { invalidate(); setRunning(false); setStatus("Choose parameters and run an integration."); });
$("play").addEventListener("click", togglePlayback);
$("scrub").addEventListener("input", () => {
  const data = samples(); index = Number(($("scrub") as HTMLInputElement).value); replayTime = data[index]?.time ?? 0; followingLiveRun = false; queuePlotRender(); renderCursor();
});
$("budget").addEventListener("change", queuePlotRender);
$("speed").addEventListener("change", () => { previousWallTime = performance.now(); });
inputs.forEach((id) => ($(id) as HTMLInputElement).addEventListener("input", () => { if (id === "w") refreshLogLabels(); invalidate(); }));
document.querySelectorAll("input[name=start]").forEach((input) => input.addEventListener("change", invalidate));
applyPreset(); setReplayEnabled(false); setRunning(false);
window.addEventListener("beforeunload", () => { if (activeJob) worker.postMessage({ type: "cancel", jobId: activeJob } satisfies MainToWorkerMessage); });
