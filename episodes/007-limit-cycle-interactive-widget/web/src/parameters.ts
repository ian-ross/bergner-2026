/** Values consumed by the model; every field is SI. */
export interface Environment {
  T: number;
  p: number;
  w: number;
  F: number;
  N_a: number;
  deltaZ: number;
  includeEvaporation: false;
}

/** Values at the browser/UI boundary. Pressure is hPa and aerosol is cm^-3. */
export interface UiParameters {
  T: number;
  pHpa: number;
  w: number;
  F: number;
  nAcm3: number;
  deltaZ: number;
}

const ranges = {
  T: [190, 235], pHpa: [150, 600], w: [0.005, 2], F: [0.05, 1],
  nAcm3: [300, 10000], deltaZ: [50, 500],
} as const;

function validate(name: keyof UiParameters, value: number): void {
  const [minimum, maximum] = ranges[name];
  if (!Number.isFinite(value)) throw new RangeError(`${name} must be a finite number.`);
  if (value < minimum || value > maximum) {
    throw new RangeError(`${name} must be between ${minimum} and ${maximum}; received ${value}.`);
  }
}

/** Validate browser controls and convert their units exactly once into SI. */
export function environmentFromUi(input: UiParameters): Environment {
  (Object.keys(ranges) as Array<keyof UiParameters>).forEach((name) => validate(name, input[name]));
  return {
    T: input.T, p: input.pHpa * 100, w: input.w, F: input.F,
    N_a: input.nAcm3 * 1e6, deltaZ: input.deltaZ, includeEvaporation: false,
  };
}

export const canonicalUiParameters: UiParameters = {
  T: 225, pHpa: 300, w: 0.1, F: 1, nAcm3: 10000, deltaZ: 100,
};
