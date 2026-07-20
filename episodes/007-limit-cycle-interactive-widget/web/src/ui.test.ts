import { describe, expect, it } from "vitest";
import { canonicalUiParameters } from "./parameters";
import { advanceReplay, BUDGET_OPTIONS, figure4Preset, initialStateFor, stepLimitRecovery, validateControls, workerTransition } from "./ui";

const controls = { ...figure4Preset, parameters: { ...canonicalUiParameters } };

describe("widget controls", () => {
  it("restores the complete Figure 4 preset", () => {
    expect(figure4Preset).toMatchObject({ parameters: { T: 225, pHpa: 300, w: 0.1, F: 1, nAcm3: 10000, deltaZ: 100 }, duration: 239_118.05830323207, start: "paper" });
  });

  it("uses parameter validation at the UI boundary", () => {
    expect(() => validateControls({ ...controls, parameters: { ...controls.parameters, T: 240 } })).toThrow("T must be between");
    expect(() => validateControls({ ...controls, start: "unknown" as never })).toThrow("initial condition");
    expect(() => validateControls({ ...controls, budget: "unknown" as never })).toThrow("process-budget");
    expect(() => validateControls({ ...controls, duration: 0 })).toThrow("duration");
    expect(() => validateControls(controls)).not.toThrow();
  });

  it("derives every approved initial condition from computed equilibrium", () => {
    const equilibrium = { n: 10, q: 20, s: 2 };
    expect(initialStateFor(equilibrium, "paper")).toEqual({ n: 9.9, q: 19.8, s: 1.98 });
    expect(initialStateFor(equilibrium, "n")).toEqual({ n: 10.1, q: 20, s: 2 });
    expect(initialStateFor(equilibrium, "q")).toEqual({ n: 10, q: 20.2, s: 2 });
    expect(initialStateFor(equilibrium, "s")).toEqual({ n: 10, q: 20, s: 2.02 });
  });

  it("has the three supported process-budget selections and explicit worker transitions", () => {
    expect(BUDGET_OPTIONS).toEqual(["n", "q", "s"]);
    expect(workerTransition("idle", "start")).toBe("running");
    expect(workerTransition("running", "result")).toBe("ready");
    expect(workerTransition("running", "failure")).toBe("failed");
    expect(workerTransition("running", "cancelled")).toBe("cancelled");
  });

  it("keeps animation controls synchronized and stops at the final sample", () => {
    expect(advanceReplay({ index: 0, playing: false, speed: 1 }, 5, 1)).toMatchObject({ index: 0, playing: false });
    expect(advanceReplay({ index: 3, playing: true, speed: 1 }, 5, 2)).toMatchObject({ index: 4, playing: false });
  });

  it("turns step-limit failures into an actionable recovery message", () => {
    expect(stepLimitRecovery("Accepted-step limit (200000) exhausted.")).toContain("Reduce the integration duration");
    expect(stepLimitRecovery("equilibrium failed")).toBe("equilibrium failed");
  });
});
