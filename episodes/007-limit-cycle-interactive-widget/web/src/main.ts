import { solveEquilibrium } from "./equilibrium";
import { canonicalUiParameters, environmentFromUi } from "./parameters";

// UI/worker wiring arrives in later tasks; keep this entry point buildable now.
const app = document.querySelector<HTMLDivElement>("#app");
if (app) {
  const equilibrium = solveEquilibrium(environmentFromUi(canonicalUiParameters));
  app.textContent = `Canonical equilibrium: n=${equilibrium.state.n}, q=${equilibrium.state.q}, s=${equilibrium.state.s}`;
}
