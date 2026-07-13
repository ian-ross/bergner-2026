# Episode 005: Figure 2 eigenvalues

Goal: reproduce Bergner & Spichtinger (2026) Figure 2 eigenvalue curves using three independently generated equilibrium/eigenvalue output paths: Python, AUTO-07p, and LOCA/Trilinos.

This episode shifts from Figure 1 branch reproduction to the linear stability information shown in Figure 2. The comparison target is the physical ODE Jacobian evaluated at physical equilibria, not eigenvalues of transformed continuation residuals or solver-internal continuation systems.

## Contents

- `docs/planning-decisions.md` — Episode 5 scope, agreed Figure 2 parameter set, backend responsibilities, eigenvalue semantics, and open implementation questions.
- `scripts/` — Python and AUTO orchestration, normalization, comparison, and plotting scripts for Figure 2 eigenvalue runs.
- `auto/` — Episode-local AUTO Figure 2 problem and constants templates.
- `outputs/` — curated Python, AUTO, LOCA, and cross-backend comparison artifacts.
- `notebooks/` — exploratory notebooks for eigenvalue diagnostics, source inspection, and backend comparison.

## Initial Figure 2 reproduction target

Use the agreed single-environment Figure 2 target:

- `p = 300 hPa`
- `T = 230 K`
- `F = 1`
- `N_a = 1.0e10 m^-3` (`10000 cm^-3`), matching the high-aerosol assumption inferred and documented during Figure 1 reproduction
- paper vertical-velocity range `w = 0.0005--2.0 m s^-1`
- comparison coordinate may use `log_w = log(w_m_s)` internally, but curated outputs must retain physical `w_m_s`

## Upstream references

Episode 5 should reuse model semantics and backend infrastructure deliberately, while keeping Figure 2 artifacts episode-local unless a later task promotes shared infrastructure.

- Python model and residual utilities: `src/bergner_spichtinger_2026/`
- Figure 1 Python continuation and high-`N_a` provenance: `episodes/002-figure1-python-continuation/`
- Figure 1 AUTO backend and branch-normalization patterns: `episodes/003-figure1-auto-continuation/`
- Figure 1 LOCA backend, Sacado residual/Jacobian work, and comparison patterns: `episodes/004-figure1-loca-continuation/`
- Shared AUTO backend/model assets, when reusable: `auto/`
- Shared LOCA/Trilinos backend code, when reusable: `loca/`
- Cross-episode reproduction/debugging notes: `docs/REPRODUCTION_NOTES.md`
- Cross-backend testing guidance: `docs/testing.md`

## Final workflow commands

The curated Figure 2 artifacts can be regenerated with:

```bash
# Generate Python equilibrium/eigenvalue outputs for Figure 2.
uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py

# Generate/normalize AUTO Figure 2 outputs and eigenvalue metadata.
uv run python episodes/005-figure2-eigenvalues/scripts/run_auto_figure2_eigenvalues.py

# Generate/normalize LOCA Figure 2 outputs with backend-side physical eigenvalues.
uv run python episodes/005-figure2-eigenvalues/scripts/run_loca_figure2_eigenvalues.py

# Compare backends and produce the paper-facing Figure 2 reproduction.
uv run python episodes/005-figure2-eigenvalues/scripts/compare_figure2_eigenvalues.py
```

Curated output groups:

- `outputs/figure2_python_eigenvalues/` — Python-native branch/eigenvalue CSVs, Hopf crossing tables, run metadata, and draft Figure 2-style plot.
- `outputs/figure2_auto_eigenvalues/` — AUTO-generated equilibrium branch, Python-postprocessed physical eigenvalue CSVs, Hopf crossing tables, raw AUTO run files, diagnostics, and metadata. AUTO eigenvalues are the physical ODE Jacobian evaluated at AUTO equilibria, not solver-internal continuation eigenvalues.
- `outputs/figure2_loca_eigenvalues/` — LOCA/Trilinos branch/eigenvalue CSVs, backend-side Sacado physical-Jacobian diagnostics, raw LOCA CSV/stderr, summary, metadata, and draft Figure 2-style plot.
- `outputs/figure2_backend_comparison/` — integrated backend-comparison artifacts:
  - `figure2_backend_aligned_eigenvalues.csv` — derived aligned table on the canonical log-`w` comparison grid; raw backend grids remain in their backend output directories.
  - `figure2_backend_pairwise_differences.csv` — pairwise Python/AUTO/LOCA tracked-eigenvalue differences at each canonical grid point.
  - `figure2_backend_hopf_estimates.csv` — simple zero-crossing Hopf estimates from linear interpolation in `log_w`.
  - `figure2_backend_three_real_intervals.csv` — per-backend intervals where all eigenvalues are real.
  - `figure2_backend_comparison_summary.json` and `run_metadata.json` — grid contract, backend method summaries, regime/stability counts, difference summaries, digitization status, commands, and software metadata.
  - `figure2_reproduction_backend_comparison.png` — headline two-panel real/imaginary Figure 2 reproduction with Python, AUTO, and LOCA overlays and Hopf markers.

## Integrated comparison notes

The integrated comparison uses `log_w = ln(w_m_s)` as the canonical coordinate and writes `w_m_s` alongside it. Because the backend runs have different raw grid densities (`python`/`loca`: 801 points; `auto`: 411 points in the curated run), `compare_figure2_eigenvalues.py` creates a derived canonical grid over the common backend overlap and linearly interpolates tracked eigenvalue branch real/imaginary parts onto that grid. This alignment is only for comparison products; no raw backend branch/eigenvalue CSV is modified or discarded.

Current curated Hopf estimates cluster near the paper landmarks at about `w = 0.04853 m s^-1` and `w = 0.7687 m s^-1` for all three backends. The integrated summary JSON contains the exact backend-specific estimates and pairwise difference maxima/medians.

Figure 2 digitization was explicitly deferred for this integrated pass. The source PDF/HTML are available under `sources/original/`, but a robust digitization of the overplotted/rasterized real and especially imaginary panels would require manual axis calibration and curve-identification choices. Any future digitized paper markers should be treated as secondary visual evidence and labeled with calibration/curve uncertainty rather than used as primary numerical validation.

## Scope boundaries

Python, AUTO, and LOCA should each generate their own equilibrium/eigenvalue outputs for comparison. Shared package/backend code may be reused, but Episode 5 comparison claims should not come from copying one backend's final eigenvalue table into another backend's output.

LOCA must compute the physical Jacobian and physical eigenvalues backend-side, using Sacado for derivatives and Teuchos/LAPACK where available for dense eigenvalue calculations. AUTO may fall back to Python analytic physical-Jacobian eigenvalues after native AUTO eigenvalue options have been investigated and the fallback is documented in Episode 5 planning notes and run metadata.
