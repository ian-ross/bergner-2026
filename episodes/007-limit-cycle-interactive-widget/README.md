# Episode 007: limit-cycle interactive widget

This episode provides an offline, static browser explorer for the attracting limit cycle in the center case of Bergner & Spichtinger (2026) Figure 4.  It complements—not replaces—the authoritative Python notebook: every browser run solves its equilibrium and integrates a new trajectory locally.

## Curated scientific artifacts

- [Long-run stability diagnostics](outputs/limit_cycle_stability.png)
- [All-start attractor convergence](outputs/attractor_convergence_log10n_s.png)
- [Representative-cycle state and process budgets](outputs/one_cycle_state_process_budgets.png)
- [Reference trajectory](outputs/reference_trajectory.csv) and [metadata/provenance](outputs/reference_metadata.json)
- [Offline widget source and entry point](web/index.html) (build `web/dist/index.html` before serving)

## Architecture and numerical method

`web/src/main.ts` owns native browser controls, status announcements, Plotly rendering, and synchronized replay. A module Web Worker (`web/src/integration.worker.ts`) owns the fresh positive-equilibrium solve and cancellable integration, so a long calculation does not block the page. Plotly and the worker are bundled by Vite into local hashed files; there is no CDN, backend, Python process, or notebook-kernel dependency at runtime.

The browser core is a TypeScript translation of the no-evaporation Python model in `src/bergner_spichtinger_2026/`. It uses SI internally, converts pressure from hPa and aerosol concentration from `cm^-3` exactly once at the UI boundary, finds a positive equilibrium with a bracketed/damped log-state method, and integrates `(log(n), log(q), s)` with adaptive Dormand–Prince RK45. Positivity of `n` and `q`, accepted-step limits, sample limits, failure reporting, and worker cancellation are explicit. Each plotted sample re-evaluates process terms and physical tendencies. See [the browser-core validation note](docs/browser-model-core.md) for tolerances and the fixture-generation command.

The Figure 4 preset is `T=225 K`, `p=300 hPa`, `w=0.1 m s^-1`, `F=1`, `N_a=10000 cm^-3`, and `Delta z=100 m`, with the paper-style `0.99` equilibrium-relative start. The browser tests check its short-horizon state and process terms against the Python reference (relative tolerance `1e-4`) and its late-cycle period, amplitude, and phase-independent orbit distance (each within `1e-3`). The curated reference files were produced by `notebooks/01_limit_cycle_diagnostics.ipynb`; they validate fresh browser computation and are never replayed as a browser result.

## Supported controls, accessibility, and limits

The supported tested input domain is:

| Control | Range | Notes |
| --- | --- | --- |
| Temperature `T` | 190–235 K | primary control |
| Pressure `p` | 150–600 hPa | advanced control |
| Vertical velocity `w` | 0.005–2.0 m s^-1 | logarithmic primary control |
| Sedimentation factor `F` | 0.05–1 | primary control |
| Aerosol concentration `N_a` | 300–10000 cm^-3 | logarithmic primary control |
| Layer depth `Delta z` | 50–500 m | advanced control |

All controls are native focusable elements: Tab/Shift+Tab reaches the run, cancel, reset, preset, initial-condition, replay, and budget controls; Enter/Space activates buttons; and arrow keys operate range controls. Units appear next to inputs and plot axes, status and equilibrium updates are announced with live regions, focus is visibly indicated, and the layout becomes single-column below 760 px. The stylesheet honors `prefers-reduced-motion` by disabling transitions and animations.

This is a numerical exploration tool, not a replacement for the published calculation or a general cloud microphysics simulator. The model deliberately disables evaporation number tendency, requires positive `n` and `q`, only supports the ranges above, and can reject difficult parameter/duration combinations at its explicit integration limits. Long trajectories may take noticeable time on slower devices; Cancel remains available while the worker runs. Browser support targets current evergreen Chrome/Chromium, Firefox, and Safari versions with ES-module Web Worker support.

## Reproduce, test, build, and serve

From the repository root, regenerate the curated Python reference artifacts with a clean notebook execution:

```bash
uv run jupyter execute episodes/007-limit-cycle-interactive-widget/notebooks/01_limit_cycle_diagnostics.ipynb --inplace
uv run pytest -q
```

Then install the already locked web dependencies and validate the browser implementation:

```bash
cd episodes/007-limit-cycle-interactive-widget/web
npm ci --offline
npm test
npm run build
```

`npm run build` type-checks, creates a multi-file `dist/` bundle, and runs `verify:offline`, which rejects remote script/style references and verifies every production runtime asset is present locally. Inspect the resulting HTML to confirm it references only `/assets/...` files. Serve the directory rather than opening `index.html` with `file://`, because module workers require an HTTP origin:

```bash
npm run preview
# or, from web/: python -m http.server --directory dist 8000
```

For static deployment, publish the contents of `web/dist/` unchanged to any HTTPS static host. Configure the host to fall back to `index.html` only if it imposes SPA routing; the widget itself uses no routes, server APIs, environment variables, or runtime network requests. Preserve the `assets/` directory alongside `index.html` and do not replace its hashed JavaScript or CSS files with CDN URLs.

## Browser smoke test

After `npm run build`, serve `web/dist/` and perform this checklist in a current Chromium browser and Firefox; repeat the narrow-layout and keyboard checks in Safari where available.

1. Load the page with DevTools Network set to Offline after the initial local page load. Confirm no request leaves the local origin and that the controls and empty plots render.
2. Click **Figure 4 preset**, then **Run integration**. Confirm progress/status text changes, equilibrium text appears, and state, budget, and orbit plots render after completion.
3. Press **Play**, use the Time slider's arrow keys, change Speed and the budget component, and confirm the three views stay synchronized. Reset and verify replay controls disable.
4. Start a long run and click **Cancel** while progress is reported. Confirm the cancellation status appears and Run becomes available again.
5. Change a primary parameter, run again, and confirm the old result is invalidated before the fresh result appears. Restore the Figure 4 preset and rerun it.
6. At a viewport narrower than 760 px, confirm the controls and all three plots are readable in one column. Navigate with only the keyboard, verify visible focus and status updates, and enable reduced motion in the OS/browser to confirm no decorative motion is required.

## Cross-episode context

- `episodes/001-figure4-time-series/` records the Figure 4 qualitative-reproduction context.
- `episodes/005-figure2-eigenvalues/` provides the stability/eigenvalue context used for period estimation.
- `docs/PHASE2_IMPLEMENTATION.md`, `docs/REPRODUCTION_NOTES.md`, and `docs/testing.md` record shared model semantics, provenance, and tested physical domains.
- [Planning decisions](docs/planning-decisions.md) state the binding scientific and browser contracts for this episode.
