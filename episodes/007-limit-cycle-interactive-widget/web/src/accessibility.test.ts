import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const index = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const stylesheet = readFileSync(new URL("./style.css", import.meta.url), "utf8");

describe("widget accessibility and responsive contract", () => {
  it("uses labelled native controls and announces computation status", () => {
    expect(index).toContain('role="status" aria-atomic="true"');
    expect(index).toContain('id="run" type="button"');
    expect(index).toContain('id="cancel" type="button"');
    expect(index).toContain('id="scrub" type="range"');
    expect(index).toContain('id="w" type="range"');
    expect(index).toContain("m s⁻¹");
    expect(index).not.toContain('id="nAcm3"');
    expect(index).not.toContain('name="start" value="s"');
    expect(index).not.toContain("Advanced controls");
    expect(index).not.toContain('id="pHpa"');
    expect(index).not.toContain('id="deltaZ"');
    expect(index).not.toContain("Integration complete");
    expect(index).not.toContain("Equilibrium:");
  });

  it("keeps a narrow layout, visible keyboard focus, and reduced-motion behavior", () => {
    expect(stylesheet).toContain("button:focus-visible");
    expect(stylesheet).toContain("@media (max-width: 760px)");
    expect(stylesheet).toContain("@media (prefers-reduced-motion: reduce)");
    expect(stylesheet).toContain("grid-template-columns: auto minmax(14rem, 58rem) auto");
    expect(stylesheet).toContain("#replay-help { grid-column: 2 / 4; grid-row: 2;");
  });
});
