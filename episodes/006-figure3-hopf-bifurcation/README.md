# Episode 006: Figure 3 Hopf bifurcation loci

Goal: reproduce Bergner & Spichtinger (2026) Figure 3 Hopf bifurcation loci in the `T`--`w` parameter plane for `p = 300 hPa` and `F = 1`, and compare three continuation-oriented backends: Python augmented Hopf continuation, AUTO-07p native Hopf continuation, and full NOX/LOCA Hopf continuation.

This episode moves from one-dimensional branch/eigenvalue sweeps to true two-parameter bifurcation-locus reproduction. Figure 3's Table II fit curves are reference overlays, not the primary computational method: backend outputs should represent numerically continued lower and upper Hopf loci where the physical ODE equilibrium has a conjugate pair crossing the imaginary axis.

## Contents

- `docs/planning-decisions.md` — Episode 6 scope, Figure 3 target, backend responsibilities, output contract, and dependencies.
- `scripts/` — placeholder for Python orchestration, backend runners, normalization, and comparison scripts.
- `notebooks/` — placeholder for exploratory diagnostics and source/plot inspection notebooks.
- `outputs/` — placeholder for curated per-backend Hopf-locus data, comparison tables, metadata, and plots.

Empty directories are retained with `.gitkeep` placeholders until implementation tasks add concrete artifacts.

## Initial Figure 3 reproduction target

Use the paper's Figure 3 setting:

- `p = 300 hPa`
- `F = 1`
- temperature range `T = 190--240 K`
- vertical velocity coordinate `w_m_s` in physical `m s^-1`, with `log_w = log(w_m_s)` allowed internally for conditioning
- two Hopf branches: the lower-`w`/blue branch associated with `w_a(T)` and the upper-`w`/red branch associated with `w_b(T)` in Table II

The headline product should overlay backend-computed Hopf loci and Table II fit curves, plus any explicitly labeled gray/three-real-eigenvalue diagnostic region if implemented later.

## Upstream references and shared infrastructure

Episode 6 should reuse existing model semantics and backend infrastructure while keeping Figure 3-specific scripts, notebooks, generated files, and curated outputs episode-local.

- Python model, equilibrium, and stability utilities: `src/bergner_spichtinger_2026/`
- Figure 1 Python continuation and high-`N_a` provenance: `episodes/002-figure1-python-continuation/`
- Figure 1 AUTO continuation patterns and backend-neutral branch normalization: `episodes/003-figure1-auto-continuation/`
- Figure 1 Trilinos-side C++ backend comparison workflow: `episodes/004-figure1-loca-continuation/`
- Figure 2 physical-eigenvalue semantics and Hopf-crossing estimates: `episodes/005-figure2-eigenvalues/`
- Shared AUTO model/backend assets: `auto/`
- Shared Trilinos-side C++ backend code and future NOX/LOCA infrastructure: `loca/`
- Cross-episode source and reproduction notes: `docs/REPRODUCTION_NOTES.md`, `docs/MODEL_EXTRACTION.md`, and `docs/SOURCE_QUALITY.md`

## Backend strategy

Planned backend roles are documented in `docs/planning-decisions.md`:

1. Python should provide a transparent augmented Hopf system/reference path.
2. AUTO should use native Hopf detection/continuation where possible, rather than only scanning Figure 2-style eigenvalue sign changes.
3. NOX/LOCA should provide the native LOCA Hopf-continuation comparison path after TASK-025 establishes the full NOX/LOCA equilibrium-continuation backend.

The current top-level `loca/` executable remains useful shared infrastructure, but Episode 6's LOCA claims are intentionally dependent on TASK-025 and later Figure 3-specific LOCA orchestration.
