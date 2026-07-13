# Episode 005: Figure 2 eigenvalues

Goal: reproduce Bergner & Spichtinger (2026) Figure 2 eigenvalue curves using three independently generated equilibrium/eigenvalue output paths: Python, AUTO-07p, and LOCA/Trilinos.

This episode shifts from Figure 1 branch reproduction to the linear stability information shown in Figure 2. The comparison target is the physical ODE Jacobian evaluated at physical equilibria, not eigenvalues of transformed continuation residuals or solver-internal continuation systems.

## Contents

- `docs/planning-decisions.md` — Episode 5 scope, agreed Figure 2 parameter set, backend responsibilities, eigenvalue semantics, and open implementation questions.
- `scripts/` — future Python orchestration, normalization, comparison, and plotting scripts for Figure 2 eigenvalue runs.
- `outputs/` — curated Python, AUTO, LOCA, and cross-backend comparison artifacts produced by later tasks.
- `notebooks/` — exploratory notebooks for eigenvalue diagnostics, source inspection, and backend comparison.

Empty directories are retained with `.gitkeep` placeholders until implementation tasks add concrete files.

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

## Planned workflow placeholders

Later implementation tasks should replace these placeholders with concrete commands and output paths:

```bash
# Generate Python equilibrium/eigenvalue outputs for Figure 2.
uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py

# Generate/normalize AUTO Figure 2 outputs and eigenvalue metadata.
# uv run python episodes/005-figure2-eigenvalues/scripts/run_auto_figure2_eigenvalues.py

# Generate/normalize LOCA Figure 2 outputs with backend-side physical eigenvalues.
# uv run python episodes/005-figure2-eigenvalues/scripts/run_loca_figure2_eigenvalues.py

# Compare backends and produce Figure 2-style plots.
# uv run python episodes/005-figure2-eigenvalues/scripts/compare_figure2_eigenvalues.py
```

Expected curated output groups are provisionally:

- `outputs/figure2_python_eigenvalues/` — implemented Python-native branch/eigenvalue CSVs, Hopf crossing tables, run metadata, and draft Figure 2-style plot.
- `outputs/figure2_auto_eigenvalues/`
- `outputs/figure2_loca_eigenvalues/`
- `outputs/figure2_backend_comparison/`

## Scope boundaries

Python, AUTO, and LOCA should each generate their own equilibrium/eigenvalue outputs for comparison. Shared package/backend code may be reused, but Episode 5 comparison claims should not come from copying one backend's final eigenvalue table into another backend's output.

LOCA must compute the physical Jacobian and physical eigenvalues backend-side, using Sacado for derivatives and Teuchos/LAPACK where available for dense eigenvalue calculations. AUTO may fall back to Python analytic physical-Jacobian eigenvalues after native AUTO eigenvalue options have been investigated and the fallback is documented in Episode 5 planning notes and run metadata.
