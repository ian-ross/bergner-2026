import { C } from "./constants";
import type { Environment } from "./parameters";

export interface Coefficients {
  rho: number; D: number; pSi: number; p1e: number; p2: number;
  A_n: number; A_q: number; A_s: number; B_q: number; B_s: number; C_n: number; C_q: number;
}
export interface State { n: number; q: number; s: number; }
export interface ProcessTerms {
  Nuc_n: number; Nuc_q: number; Nuc_s: number; Dep_q: number; Dep_s: number;
  Evap_n: number; Sed_n: number; Sed_q: number; Cool: number;
}

export const rhoAir = (p: number, T: number) => p / (C.R_d * T);
export const latentHeat = (T: number) =>
  (C.l0 + C.l1 * T + C.l2 * T ** 2 + C.l3 * Math.exp(-((T / C.T_l) ** 2))) / C.M_mol_v;
export const saturationVapourPressure = (T: number) => Math.exp(C.b0 + C.b1 / T + C.b2 * Math.log(T) + C.b3 * T);
export const vapourDiffusivity = (T: number, p: number) => C.D_v0 * (T / C.T0) ** 2 * C.p0 / p;
export const thermalConductivity = (T: number) => C.a_K * T ** C.b_K / (T + C.T_K * 10 ** (C.c_K / T));
export const growthFactor = (T: number, p: number) => {
  const L = latentHeat(T);
  return 1 / (((L / (C.R_v * T) - 1) * L * vapourDiffusivity(T, p) / (T * thermalConductivity(T))) + C.R_v * T / saturationVapourPressure(T));
};
export const coolingCoefficient = (T: number) => ((latentHeat(T) / (C.c_p * C.R_v * T ** 2)) - 1 / (C.R_d * T)) * C.g;
export const nucleationSteepness = (T: number) => Math.LN10 * (C.p1_a0 + C.p1_a1 * T);
export const criticalSaturation = (T: number) => C.p2_as2 * T ** 2 + C.p2_as1 * T + C.p2_as0;
const solutionVolume = () => 4 * Math.PI / 3 * C.r_sol ** 3 * Math.exp(4.5 * Math.log(C.sigma_r) ** 2);
const radiusCoefficient = () => (3 / (4 * Math.PI * C.rho_b)) ** (1 / 3);
const fallCorrection = (p: number, T: number) => (p / C.p_c) ** C.a_c * (T / C.T_c) ** C.b_c;

/** Eqs. (4)--(6) coefficients; all inputs and outputs use SI units. */
export function coefficients(env: Environment): Coefficients {
  const rho = rhoAir(env.p, env.T), pSi = saturationVapourPressure(env.T);
  const A_n = env.N_a / rho * solutionVolume() * C.J0, A_q = C.m_nuc * A_n;
  const ratio = env.p / (C.epsilon * pSi), B_q = 4 * Math.PI * growthFactor(env.T, env.p) * vapourDiffusivity(env.T, env.p) * radiusCoefficient() * C.r0 ** (-1 / 9);
  const sedimentation = fallCorrection(env.p, env.T) * C.a_sed / env.deltaZ;
  return { rho, D: coolingCoefficient(env.T), pSi, p1e: nucleationSteepness(env.T), p2: criticalSaturation(env.T),
    A_n, A_q, A_s: A_q * ratio, B_q, B_s: B_q * ratio, C_n: sedimentation * C.r0 ** (-1 / 9), C_q: sedimentation * C.r0 ** (5 / 9) };
}

function positiveCloud(state: State): void {
  if (!Number.isFinite(state.n) || !Number.isFinite(state.q) || state.n <= 0 || state.q <= 0) {
    throw new RangeError("The unregularized model requires finite, strictly positive n and q.");
  }
}

/** Individual physical terms. The browser canonical model explicitly has Evap_n disabled. */
export function processTerms(state: State, env: Environment, c = coefficients(env)): ProcessTerms {
  positiveCloud(state);
  const expo = Math.exp(c.p1e * (state.s - c.p2));
  if (!Number.isFinite(expo)) throw new RangeError("Nucleation exponent is not finite for this state.");
  const massFactor = state.n ** (2 / 3) * state.q ** (1 / 3) * (state.s - 1);
  const Dep_q = c.B_q * massFactor;
  return {
    Nuc_n: c.A_n * expo, Nuc_q: c.A_q * expo, Nuc_s: -c.A_s * expo,
    Dep_q, Dep_s: -c.B_s * massFactor, Evap_n: 0,
    Sed_n: -env.F * c.C_n * state.n ** (1 / 3) * state.q ** (2 / 3),
    Sed_q: -env.F * c.C_q * state.n ** (-2 / 3) * state.q ** (5 / 3), Cool: c.D * env.w * state.s,
  };
}

export function vectorField(state: State, env: Environment, c = coefficients(env)): State {
  const t = processTerms(state, env, c);
  return { n: t.Nuc_n + t.Evap_n + t.Sed_n, q: t.Nuc_q + t.Dep_q + t.Sed_q, s: t.Cool + t.Nuc_s + t.Dep_s };
}
