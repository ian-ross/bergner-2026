# Browser model core validation

`web/src/` is a direct TypeScript translation of the no-`Evap_n` Python model in `src/bergner_spichtinger_2026/core.py`. Model inputs and outputs are SI; `environmentFromUi()` converts UI pressure from hPa and the widget's fixed canonical aerosol concentration from `cm^-3` exactly once.

`web/src/fixtures/python-model-reference.json` is generated, rather than hand-maintained, with:

```bash
uv run python episodes/007-limit-cycle-interactive-widget/scripts/generate_browser_model_fixture.py
```

It compares three deterministic environments: the Figure 4 canonical case and the low/high corners of the supported browser domain. Coefficients, process terms, and vector-field arithmetic use relative tolerance `1e-10`. The positivity-preserving equilibrium solver first brackets `s` using Appendix-B relations, bisects it, then accepts only damped improvements in `(log(n), log(q), s)`. Its state is compared with SciPy's fixture at `1e-6` relative tolerance because the finite-difference refinement differs; its independent log-coordinate RHS residual must be below `1e-10`.

`web/src/integrator.ts` applies Dormand--Prince 5(4) to `(log(n), log(q), s)` with a per-component scale of `atol + rtol * max(abs(previous), abs(candidate))`. Reconstruction from those coordinates keeps `n` and `q` strictly positive. Endpoint derivatives provide cubic Hermite dense output; every output sample re-evaluates all process terms and physical total tendencies. The production `browserIntegrationOptions()` profile uses `rtol=1e-8`, `atol=1e-10`, a 15 s maximum trial step, a sparse 1,001-point baseline grid, every adaptive accepted-step endpoint, and interpolated saturation stationary points. The latter samples capture exponentially narrow `Nuc_n` peaks without fixed-grid aliasing: the canonical final-20-cycle peak range is below `1e-4` relative and its mean agrees with a SciPy dense-output reference maximum at `1e-5` relative. Generic callers retain explicit accepted-step and output-size limits.

`integration.worker.ts` owns the equilibrium solve and the asynchronous RK45 state machine. Its shared discriminated protocol has `start`, `cancel`, `equilibrium`, `samples`, `progress`, `result`, `failure`, and `cancelled` variants. Completed plotting samples are sent in bounded batches to a main-thread buffer. A separate physical-time presentation clock reveals them at the selected speed rather than at worker throughput; the final result remains available for deterministic scrubbing and replay. The integrator yields to the worker event loop after bounded accepted-step batches, allowing a queued cancellation message to take effect without blocking the UI thread.

After dependencies have been installed, no network access is needed for the workspace commands:

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm ci --offline
npm test
npm run build
```
