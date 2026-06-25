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

# Run repository tests, including LOCA residual/Jacobian and branch-output checks.
uv run pytest
```

Curated branch outputs are written under `outputs/figure1_loca_branches/`, including normalized per-temperature branch CSVs, `branches_all.csv`, `run_metadata.json`, `run_diagnostics.json`, and raw C++ continuation CSV/log artifacts. Future comparison work should write pointwise comparison details, summary tables, and plots under `outputs/figure1_loca_backend_comparison/`.

## Scope boundaries

Keep Figure 1 LOCA experiments, generated files, run logs, and curated outputs inside this episode. Do not promote C++/Trilinos code to a top-level backend directory unless it becomes documented shared infrastructure reused by more than one episode.

Python remains the semantic model reference at this stage. LOCA should consume or mirror that model deliberately, with tests comparing coefficients, residuals, Jacobians, branch-schema invariants, and final backend outputs before claiming scientific equivalence.
