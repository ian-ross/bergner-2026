# Episode 004: Figure 1 LOCA continuation

Goal: reproduce the Figure 1 equilibrium branch family with LOCA/Trilinos as a third continuation backend and compare its normalized branch outputs against the Episode 2 Python-native continuation and Episode 3 AUTO-07p backend results.

This episode implements the first LOCA/Trilinos-backed continuation path for the Figure 1 branch family. The intended numerical design is backend equivalence, not a new cloud-microphysics model: LOCA evaluates the same Bergner & Spichtinger (2026) equilibrium residual semantics used by the Python reference and writes the same backend-neutral branch schema used by the AUTO comparison.

## Contents

- `docs/planning-decisions.md` — Episode 4 LOCA/Trilinos design choices, toolchain assumptions, output contract, comparison scope, and shared-vs-episode-local boundaries.
- `loca/` — episode-local LOCA/Trilinos source, CMake/build files, run configurations, and raw solver artifacts when they are specific to the Figure 1 LOCA experiment.
- `scripts/` — future Python orchestration, normalization, and comparison scripts for LOCA runs.
- `outputs/` — curated normalized LOCA branches, comparison tables, metadata, and plots produced by this episode.
- `notebooks/` — exploratory notebooks for LOCA diagnostics and backend-comparison inspection.

Empty directories are retained with `.gitkeep` placeholders until implementation tasks add concrete files.

## Upstream Figure 1 references

Episode 4 should use these existing artifacts as the semantic and comparison references:

- Python-native continuation outputs: `episodes/002-figure1-python-continuation/outputs/figure1_continuation/`
- Episode 2 planning terminology: `episodes/002-figure1-python-continuation/docs/planning-decisions.md`
- AUTO backend outputs: `episodes/003-figure1-auto-continuation/outputs/figure1_auto_branches/`
- AUTO/Python comparison outputs: `episodes/003-figure1-auto-continuation/outputs/figure1_backend_comparison/`
- Episode 3 backend-neutral schema and LOCA implications: `episodes/003-figure1-auto-continuation/docs/planning-decisions.md`
- Cross-episode testing and backend-equivalence guidance: `docs/testing.md`

## Initial LOCA reproduction target

Use the same Figure 1 equilibrium branch family as Episodes 2 and 3:

- `p = 300 hPa`
- `F = 1`
- `T ∈ {190, 210, 230} K`
- `w ∈ [0.005, 2.0] m s^-1`
- continuation coordinate `log_w = log(w_m_s)`
- normalized physical state fields `n`, `q`, and `s`, with positive `n` and `q`

## Commands and artifacts

```bash
# Build/configure the shared top-level C++ executable, run continuation for
# T = 190, 210, and 230 K, and write normalized Episode 4 branch outputs.
uv run python episodes/004-figure1-loca-continuation/scripts/run_loca_figure1.py --clean

# Compare LOCA branches against Python, AUTO, Eq. 92--94, root-solve checks,
# and digitized paper Figure 1 curves.
uv run python episodes/004-figure1-loca-continuation/scripts/compare_loca_figure1.py

# Run repository tests, including LOCA residual/Jacobian, branch-output, and
# backend-comparison checks.
uv run pytest
```

Curated branch outputs are written under `outputs/figure1_loca_branches/`, including normalized per-temperature branch CSVs, `branches_all.csv`, `run_metadata.json`, `run_diagnostics.json`, and raw C++ continuation CSV/log artifacts. Backend comparison artifacts are written under `outputs/figure1_loca_backend_comparison/`, including pointwise details, summary CSV/JSON, overlay plots, residual plots, and run metadata.

## Backend comparison results

`compare_loca_figure1.py` reuses existing Episode 2 Python continuation/root-solve/digitized artifacts and Episode 3 AUTO outputs without refactoring those scripts. The comparison uses LOCA as the target branch: Python and AUTO branches are interpolated onto LOCA `log_w` points, Eq. 92--94 is evaluated at LOCA branch points, and LOCA is interpolated onto independent root-solve and digitized paper points. Positive concentration variables `n` and `q` use log-value interpolation; `s` uses linear interpolation.

Current curated outputs show tight solver-to-solver agreement between LOCA, Python, and AUTO. The largest observed LOCA-vs-AUTO relative differences are below `8e-6` across `n`, `q`, and `s`; LOCA-vs-Python differences are at the same numerical-continuation scale. Eq. 92--94 and digitized Figure 1 comparisons remain looser scientific reproduction checks because the former is an analytic approximation and the latter includes paper-rendering/digitization uncertainty.

These tolerances support using the LOCA continuation as a backend-equivalent branch source for later LOCA experiments, while keeping Python as the semantic reference and preserving AUTO as an independent continuation cross-check.

## Scope boundaries

Keep Figure 1 LOCA experiments, generated files, run logs, and curated outputs inside this episode. Do not promote C++/Trilinos code to a top-level backend directory unless it becomes documented shared infrastructure reused by more than one episode.

Python remains the semantic model reference at this stage. LOCA should consume or mirror that model deliberately, with tests comparing coefficients, residuals, Jacobians, branch-schema invariants, and final backend outputs before claiming scientific equivalence.
