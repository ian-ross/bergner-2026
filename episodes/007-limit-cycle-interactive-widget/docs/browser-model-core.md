# Browser model core validation

`web/src/` is a direct TypeScript translation of the no-`Evap_n` Python model in `src/bergner_spichtinger_2026/core.py`. Model inputs and outputs are SI; only `environmentFromUi()` accepts UI pressure in hPa and aerosol concentration in `cm^-3` and converts them once.

`web/src/fixtures/python-model-reference.json` is generated, rather than hand-maintained, with:

```bash
uv run python episodes/007-limit-cycle-interactive-widget/scripts/generate_browser_model_fixture.py
```

It compares three deterministic environments: the Figure 4 canonical case and the low/high corners of the supported browser domain. Coefficients, process terms, and vector-field arithmetic use relative tolerance `1e-10`. The positivity-preserving equilibrium solver first brackets `s` using Appendix-B relations, bisects it, then accepts only damped improvements in `(log(n), log(q), s)`. Its state is compared with SciPy's fixture at `1e-6` relative tolerance because the finite-difference refinement differs; its independent log-coordinate RHS residual must be below `1e-10`.

After dependencies have been installed, no network access is needed for the workspace commands:

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm ci --offline
npm test
npm run build
```
