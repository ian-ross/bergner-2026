# Browser model core validation

`web/src/` is a direct TypeScript translation of the no-`Evap_n` Python model in `src/bergner_spichtinger_2026/core.py`. Model inputs and outputs are SI; only `environmentFromUi()` accepts UI pressure in hPa and aerosol concentration in `cm^-3` and converts them once.

`web/src/fixtures/python-model-reference.json` is generated, rather than hand-maintained, with:

```bash
uv run python episodes/007-limit-cycle-interactive-widget/scripts/generate_browser_model_fixture.py
```

It compares three deterministic environments: the Figure 4 canonical case and the low/high corners of the supported browser domain. Coefficients, process terms, and vector-field arithmetic use relative tolerance `1e-10`. The positivity-preserving equilibrium solver first brackets `s` using Appendix-B relations, bisects it, then accepts only damped improvements in `(log(n), log(q), s)`. Its state is compared with SciPy's fixture at `1e-6` relative tolerance because the finite-difference refinement differs; its independent log-coordinate RHS residual must be below `1e-10`.

`web/src/integrator.ts` applies Dormand--Prince 5(4) to `(log(n), log(q), s)` with a per-component scale of `atol + rtol * max(abs(previous), abs(candidate))`. Reconstruction from those coordinates keeps `n` and `q` strictly positive. It returns endpoint-inclusive, uniformly spaced plotting samples; every sample re-evaluates all process terms and physical total tendencies. Defaults are `rtol=1e-8`, `atol=1e-10`, 1,001 samples, 200,000 accepted steps, and 20,000 maximum samples; callers may set duration, step, and limit controls explicitly.

`integration.worker.ts` owns the equilibrium solve and the asynchronous RK45 state machine. Its shared discriminated protocol has `start`, `cancel`, `progress`, `result`, `failure`, and `cancelled` variants. The integrator yields to the worker event loop after bounded accepted-step batches, allowing a queued cancellation message to take effect without blocking the UI thread.

After dependencies have been installed, no network access is needed for the workspace commands:

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm ci --offline
npm test
npm run build
```
