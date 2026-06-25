# Episode 003: Figure 1 AUTO continuation

Goal: reproduce the Figure 1 equilibrium branch family with AUTO-07p as an independent continuation backend and compare the normalized AUTO results against the Episode 2 Python-native continuation outputs. This episode is the first explicit backend-comparison step for the Figure 1 model; later LOCA/Trilinos work should use the same model semantics and branch-output contract where practical.

## Contents

- `docs/planning-decisions.md` — Episode 3 backend-comparison plan, provisional branch schema, and expected comparison outputs.
- `auto/` — episode-local AUTO run files, constants, starts, and generated AUTO artifacts when they are specific to the Figure 1 AUTO continuation experiment.
- `scripts/` — Python orchestration, normalization, and comparison scripts for AUTO runs.
- `outputs/` — curated normalized branches, comparison tables, metadata, and plots produced by this episode.
- `notebooks/` — exploratory notebooks for AUTO diagnostics and backend comparison.

The repository-level `auto/` directory is reserved for shared AUTO-07p model/backend assets reused across episodes. Keep one-off Figure 1 AUTO experiments and generated AUTO outputs under this episode directory unless they become shared infrastructure.

## Upstream Figure 1 references

Episode 3 should compare against these Episode 2 source artifacts:

- Python-native continuation outputs: `episodes/002-figure1-python-continuation/outputs/figure1_continuation/`
- Digitized paper Figure 1 artifacts: `episodes/002-figure1-python-continuation/outputs/figure1_digitized/`
- Final Episode 2 reproduction and residual summaries: `episodes/002-figure1-python-continuation/outputs/figure1_reproduction/`
- Episode 2 planning terminology: `episodes/002-figure1-python-continuation/docs/planning-decisions.md`
- Testing and backend-equivalence guidance from TASK-005: `docs/testing.md`

## Initial reproduction target

Use the same Figure 1 equilibrium branch family as Episode 2:

- `p = 300 hPa`
- `F = 1`
- `T ∈ {190, 210, 230} K`
- `w ∈ [0.005, 2.0] m s^-1`, represented internally as `log(w)` when convenient for continuation
- state coordinates normalized for comparison as physical `n`, `q`, and `s`, with strictly positive `n` and `q`

## Planned comparison workflow

1. Reuse or introduce shared AUTO model-core assets only when they are backend infrastructure rather than episode-local experiments.
2. Run AUTO continuation for each Figure 1 temperature branch using `log(w)` as the continuation coordinate.
3. Normalize AUTO outputs to the backend-neutral branch schema described in `docs/planning-decisions.md`.
4. Compare normalized AUTO branches with Episode 2 Python continuation, Eq. 92--94 approximations, independent root-solve checks where available, and digitized Figure 1 curves.
5. Record backend/tool versions, command provenance, convergence status, and tolerances with every curated output.

## AUTO Figure 1 continuation

TASK-011 adds the first Episode 3 AUTO run path:

```bash
uv run python episodes/003-figure1-auto-continuation/scripts/run_auto_figure1.py --clean
```

The script generates per-temperature AUTO problem files from `auto/bs2026_figure1_template.f90`, copies the shared top-level Fortran model core into each raw run directory, and continues equilibria in `(log n, log q, s)` with `PAR(1) = log(w)`. Outputs are written under `outputs/figure1_auto_branches/`:

- `branch_T190K.csv`, `branch_T210K.csv`, `branch_T230K.csv` — backend-neutral AUTO branch rows clipped to the requested Figure 1 range `w ∈ [0.005, 2.0] m s^-1`, including physical `w`, `n`, `q`, `s`, transformed coordinates, backend labels, and AUTO diagnostics.
- `branches_all.csv` — combined backend-neutral branch table for all Figure 1 temperatures.
- `run_metadata.json` / `run_diagnostics.json` — schema version, parser assumptions, AUTO path/version probes, gfortran version, command provenance, run files, raw AUTO output paths, endpoint coverage, labels, and visible warnings/errors.
- `raw/bs2026_T*/` — generated AUTO problem/run files and raw `b.*`, `s.*`, and `d.*` AUTO outputs.

## AUTO/Python/Figure 1 backend comparison

TASK-013 adds curated backend-comparison artifacts generated with:

```bash
uv run python episodes/003-figure1-auto-continuation/scripts/compare_auto_figure1.py
```

The script reads normalized AUTO branches from `outputs/figure1_auto_branches/`, Episode 2 Python continuation outputs from `episodes/002-figure1-python-continuation/outputs/figure1_continuation/`, and digitized paper curves from `episodes/002-figure1-python-continuation/outputs/figure1_digitized/`. It writes `outputs/figure1_backend_comparison/`:

- `backend_comparison_details.csv` — pointwise rows for AUTO-vs-Python continuation, AUTO-vs-Eq. 92--94, AUTO-vs-independent Python root-solve checks, and AUTO-vs-digitized Figure 1 curves.
- `backend_comparison_summary.csv` / `.json` — per-temperature and per-variable sample counts, median/max absolute differences, relative differences, residual-norm maxima where available, and convergence summaries.
- `figure1_backend_comparison.png` — Figure 1 three-panel overlay: solid AUTO branches, dotted Python continuation, dashed Eq. 92--94 approximations, and x markers for digitized paper curves.
- `figure1_backend_residuals.png` — AUTO-vs-Python relative-difference residuals for `n`, `q`, and `s`.
- `run_metadata.json` — input paths, interpolation method, relative-error convention, and output inventory.

Comparison method and provenance:

- AUTO-vs-Python uses the AUTO branch points as the common `log_w` grid and interpolates Python continuation values onto those points. Positive `n` and `q` are interpolated in log-value space; `s` is interpolated linearly.
- AUTO-vs-Eq. 92--94 evaluates the reusable `approximate_equilibrium` implementation at each AUTO branch point.
- AUTO-vs-digitized Figure 1 interpolates AUTO values onto the digitized paper `w` locations with the same log-space treatment for positive concentrations.
- AUTO-vs-root-solve compares AUTO values interpolated onto Episode 2 independent root-solve check locations.

Current comparison results show close AUTO/Python agreement across all three Figure 1 branches. In `backend_comparison_summary.csv`, AUTO-vs-Python max relative differences are at approximately `3.9e-6` for `n`, `7.6e-6` for `q`, and `4.9e-9` for `s`, with AUTO residual norms below `4e-9`. Eq. 92--94 remains a close analytic approximation rather than an exact backend target, with maximum relative differences below about `4.9e-4` for `n`, `6.8e-5` for `q`, and `2.2e-4` for `s`. Digitized-paper comparisons are limited by rendered-pixel calibration, color extraction, and antialiasing uncertainty inherited from Episode 2; median relative differences are typically percent-level or better for `n` and `q`, and about `2e-4--3e-4` for `s`.

Implications for later AUTO/LOCA work:

- The normalized branch schema and log-`w` comparison contract are sufficient for backend-level Figure 1 checks.
- Later LOCA outputs should write the same physical fields (`log_w`, `w_m_s`, `n`, `q`, `s`, residual/convergence metadata) so this comparison script can be extended by adding another backend source instead of inventing a new schema.
- Tolerances for future backend equivalence should distinguish solver-to-solver agreement (near machine/continuation tolerance for Python vs AUTO here) from paper/digitization agreement, which has substantially larger observational uncertainty.
