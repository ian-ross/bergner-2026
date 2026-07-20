import { describe, expect, it } from "vitest";
import fixture from "./fixtures/python-model-reference.json";
import metadata from "../../outputs/reference_metadata.json";
import { coefficients, processTerms, vectorField, type Coefficients, type ProcessTerms, type State } from "./model";
import { canonicalUiParameters, environmentFromUi } from "./parameters";
import { solveEquilibrium } from "./equilibrium";

type ReferenceCase = {
  environment: { T: number; p: number; w: number; F: number; N_a: number; deltaZ: number };
  state: State; coefficients: Coefficients; terms: ProcessTerms; vectorField: State; equilibrium: State;
};
const cases = fixture.cases as Record<string, ReferenceCase>;

function expectClose(actual: number, expected: number, relative = 1e-10): void {
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(Math.max(1e-300, Math.abs(expected) * relative));
}
function expectRecordClose(actual: object, expected: object, relative = 1e-10): void {
  const values = actual as Record<string, number>;
  for (const [key, expectedValue] of Object.entries(expected)) expectClose(values[key], expectedValue as number, relative);
}

for (const [name, reference] of Object.entries(cases)) {
  describe(`${name} Python fixture equivalence`, () => {
    const environment = { ...reference.environment, includeEvaporation: false as const };
    it("matches coefficients, process terms, and full vector field to Python arithmetic", () => {
      const c = coefficients(environment);
      expectRecordClose(c, reference.coefficients);
      const terms = processTerms(reference.state, environment, c);
      expectRecordClose(terms, reference.terms);
      expectRecordClose(vectorField(reference.state, environment, c), reference.vectorField);
    });

    it("finds a positive low-residual equilibrium", () => {
      const result = solveEquilibrium(environment);
      expect(result.state.n).toBeGreaterThan(0);
      expect(result.state.q).toBeGreaterThan(0);
      expect(result.state.s).toBeGreaterThan(1);
      // The safeguarded browser solver and SciPy use different finite-difference
      // refinements. Boundary state agreement is therefore 1e-6 relative; the
      // independently checked log-coordinate RHS residual remains below 1e-10.
      expectRecordClose(result.state, reference.equilibrium, 1e-6);
      expect(result.scaledResidualNorm).toBeLessThan(1e-10);
    });
  });
}

describe("browser parameter boundary", () => {
  it("converts cm^-3 aerosol and hPa pressure to SI exactly once", () => {
    expect(environmentFromUi(canonicalUiParameters)).toEqual({
      T: 225, p: 30000, w: 0.1, F: 1, N_a: 1e10, deltaZ: 100, includeEvaporation: false,
    });
  });

  it.each([
    ["T", { ...canonicalUiParameters, T: 189 }], ["pHpa", { ...canonicalUiParameters, pHpa: 601 }],
    ["w", { ...canonicalUiParameters, w: 0 }], ["F", { ...canonicalUiParameters, F: 1.01 }],
    ["nAcm3", { ...canonicalUiParameters, nAcm3: 299 }], ["deltaZ", { ...canonicalUiParameters, deltaZ: Number.NaN }],
  ])("rejects invalid %s with a clear error", (_name, input) => {
    expect(() => environmentFromUi(input)).toThrow(/must be/);
  });

  it("matches the published canonical equilibrium metadata", () => {
    const result = solveEquilibrium(environmentFromUi(canonicalUiParameters));
    const expected = metadata.equilibrium;
    expectRecordClose(result.state, expected, 1e-6);
  });
});
