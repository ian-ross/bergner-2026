import { coefficients, vectorField, type Coefficients, type State } from "./model";
import type { Environment } from "./parameters";

export interface EquilibriumResult {
  state: State;
  residual: State;
  scaledResidualNorm: number;
  scalarIterations: number;
  refinementIterations: number;
}

const norm = (v: State) => Math.max(Math.abs(v.n), Math.abs(v.q), Math.abs(v.s));
const scaledResidual = (state: State, env: Environment, c: Coefficients): State => {
  const f = vectorField(state, env, c);
  // These are the RHS values in (log(n), log(q), s) coordinates.
  return { n: f.n / state.n, q: f.q / state.q, s: f.s };
};

function solveLinear3(a: number[][], b: number[]): number[] {
  const augmented = a.map((row, i) => [...row, b[i]]);
  for (let column = 0; column < 3; column += 1) {
    let pivot = column;
    for (let row = column + 1; row < 3; row += 1) if (Math.abs(augmented[row][column]) > Math.abs(augmented[pivot][column])) pivot = row;
    if (Math.abs(augmented[pivot][column]) < 1e-20) throw new Error("Equilibrium Jacobian is singular.");
    [augmented[column], augmented[pivot]] = [augmented[pivot], augmented[column]];
    for (let row = column + 1; row < 3; row += 1) {
      const factor = augmented[row][column] / augmented[column][column];
      for (let k = column; k < 4; k += 1) augmented[row][k] -= factor * augmented[column][k];
    }
  }
  const result = [0, 0, 0];
  for (let row = 2; row >= 0; row -= 1) result[row] = (augmented[row][3] - augmented[row].slice(row + 1, 3).reduce((sum, value, column) => sum + value * result[row + 1 + column], 0)) / augmented[row][row];
  return result;
}

function refine(seed: State, env: Environment, c: Coefficients): [State, number] {
  let coordinates = [Math.log(seed.n), Math.log(seed.q), seed.s];
  const stateAt = (x: number[]): State => ({ n: Math.exp(x[0]), q: Math.exp(x[1]), s: x[2] });
  for (let iteration = 0; iteration < 8; iteration += 1) {
    const base = scaledResidual(stateAt(coordinates), env, c);
    if (norm(base) < 1e-12) return [stateAt(coordinates), iteration];
    const baseArray = [base.n, base.q, base.s];
    const jacobian = Array.from({ length: 3 }, () => [0, 0, 0]);
    for (let column = 0; column < 3; column += 1) {
      const h = 1e-5;
      const plus = [...coordinates], minus = [...coordinates]; plus[column] += h; minus[column] -= h;
      const fp = scaledResidual(stateAt(plus), env, c), fm = scaledResidual(stateAt(minus), env, c);
      [fp.n, fp.q, fp.s].forEach((value, row) => { jacobian[row][column] = (value - [fm.n, fm.q, fm.s][row]) / (2 * h); });
    }
    const step = solveLinear3(jacobian, baseArray.map((value) => -value));
    let accepted = false;
    for (let damping = 1; damping >= 1 / 128; damping /= 2) {
      const candidate = coordinates.map((value, i) => value + damping * step[i]);
      if (candidate[2] <= 1) continue;
      if (norm(scaledResidual(stateAt(candidate), env, c)) < norm(base)) { coordinates = candidate; accepted = true; break; }
    }
    if (!accepted) break;
  }
  return [stateAt(coordinates), 8];
}

/** Appendix B relations: an exactly positive seed parameterised by s > 1. */
function seedFromS(s: number, env: Environment, c: Coefficients): State {
  const meanMass = (c.B_q * (s - 1) / (env.F * c.C_q)) ** (3 / 4);
  const n = c.A_n * Math.exp(c.p1e * (s - c.p2)) / (env.F * c.C_n * meanMass ** (2 / 3));
  return { n, q: n * meanMass, s };
}

function scalarResidual(s: number, env: Environment, c: Coefficients): number {
  return vectorField(seedFromS(s, env, c), env, c).s;
}

/** Bracket the saturation root without allowing the physical s > 1 boundary to be crossed. */
function bracketRoot(env: Environment, c: Coefficients): [number, number] {
  let previousS = 1.000001, previous = scalarResidual(previousS, env, c);
  for (let i = 1; i <= 1024; i += 1) {
    const s = 1.000001 + i * (2 - 1.000001) / 1024;
    const value = scalarResidual(s, env, c);
    if (Number.isFinite(previous) && Number.isFinite(value) && (previous === 0 || previous * value < 0)) return [previousS, s];
    previousS = s; previous = value;
  }
  throw new Error("Could not bracket a positive equilibrium saturation ratio in 1 < s <= 2.");
}

/** Bisection is deliberately used as the safeguarded scalar stage. */
function bisect(env: Environment, c: Coefficients): [number, number] {
  let [lo, hi] = bracketRoot(env, c), flo = scalarResidual(lo, env, c);
  for (let iteration = 1; iteration <= 100; iteration += 1) {
    const mid = (lo + hi) / 2, fm = scalarResidual(mid, env, c);
    // The nucleation exponential makes n sensitive to s: terminate on the
    // bracket width, not merely a small (dimensionful) scalar residual.
    if (hi - lo < 1e-13) return [mid, iteration];
    if (flo * fm <= 0) hi = mid;
    else { lo = mid; flo = fm; }
  }
  return [(lo + hi) / 2, 100];
}

/**
 * Solve the no-Evap_n equilibrium in log(n), log(q), s coordinates.
 * The Appendix-B bisection seed enforces positivity; its full RHS residual is
 * checked before return. It is already a root to floating-point precision, so
 * no unguarded Newton update is needed to turn a reliable scalar solve unstable.
 */
export function solveEquilibrium(env: Environment, tolerance = 1e-10): EquilibriumResult {
  const c = coefficients(env);
  const [s, scalarIterations] = bisect(env, c);
  const [state, refinementIterations] = refine(seedFromS(s, env, c), env, c);
  const residual = scaledResidual(state, env, c), scaledResidualNorm = norm(residual);
  if (!Number.isFinite(scaledResidualNorm) || scaledResidualNorm > tolerance) {
    throw new Error(`Equilibrium refinement in log(n), log(q), s failed: scaled residual ${scaledResidualNorm}.`);
  }
  return { state, residual, scaledResidualNorm, scalarIterations, refinementIterations };
}
