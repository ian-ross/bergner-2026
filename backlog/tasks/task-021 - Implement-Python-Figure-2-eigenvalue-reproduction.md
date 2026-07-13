---
id: TASK-021
title: Implement Python Figure 2 eigenvalue reproduction
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 12:01'
labels:
  - episode-005
  - figure2
  - eigenvalues
  - python
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the Python-native Figure 2 equilibrium branch and physical eigenvalues over the paper range w = 0.0005--2.0 m s^-1 for p = 300 hPa, T = 230 K, F = 1, N_a = 1.0e10 m^-3. Use the shared physical Jacobian/eigenvalue infrastructure as the semantic reference.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Script generates a dense log-w branch with at least 400 finite converged points across w = 0.0005--2.0 m s^-1.
- [x] #2 Output CSV includes equilibrium state, residual/convergence diagnostics, canonical physical eigenvalues, eigenvalue regime, and stability classification.
- [x] #3 Python outputs include simple Hopf crossing estimates near the paper-described crossings around w ≈ 0.048 and w ≈ 0.77 m s^-1, within documented numerical tolerance.
- [x] #4 A draft Figure 2-style plot shows real eigenvalue parts and imaginary eigenvalue parts versus log-scaled w.
- [x] #5 Run metadata records parameter values, N_a assumption, grid density, Jacobian method, eigenvalue sorting tolerance, and commands.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Build an Episode 5 Python script that uses the shared continuation/residual primitives to generate a dense log-spaced branch for p=300 hPa, T=230 K, F=1, N_a=1e10 over w=0.0005--2.0.
2. For each branch point, compute physical residual diagnostics, the SymPy-derived physical Jacobian, canonical eigenvalues, eigenvalue regime, and stability classification.
3. Compute simple Hopf zero-crossing estimates from Re(lambda_pair) and record comparison to the paper landmarks near w≈0.048 and w≈0.77.
4. Write normalized CSV, summary CSV/JSON, and metadata under episodes/005-figure2-eigenvalues/outputs/.
5. Produce a draft Figure 2-style real/imaginary eigenvalue plot and add tests or smoke checks for schema, point count, finite values, and metadata.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-021: moved to In Progress and assigned to @pi. Reviewing existing implementation plan before coding.

- Implemented episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py for the p=300 hPa, T=230 K, F=1, N_a=1e10 m^-3 Figure 2 sweep.
- Generated curated outputs in episodes/005-figure2-eigenvalues/outputs/figure2_python_eigenvalues/: long eigenvalue CSV, wide branch-point CSV, Hopf crossing tables, summary JSON, metadata JSON, and draft plot.
- Added tests/test_episode5_python_figure2.py smoke coverage for schema, dense finite converged point count, Hopf landmark tolerances, metadata, and plot existence.
- Verification: uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py; uv run pytest tests/test_episode5_python_figure2.py; uv run pytest (60 passed, one existing/runtime overflow warning during root exploration).

- User review identified a likely plotting artifact: connecting per-point canonical eigenvalue labels can create a spurious vertical/branch-jump segment when the spectrum changes identity near a real/complex transition. Reopening task to diagnose and patch plot semantics while preserving canonical CSV output.

- Diagnosed user-reported vertical eigenvalue segment as a plot-labeling artifact: the canonical CSV ordering switches identity across the low-w real/complex transition, so connected canonical λ labels can draw a jump.
- Patched the plot path to preserve canonical lambda columns for tabular comparison while adding tracked_lambda*_real/imag plot-only branches via adjacent minimum-distance matching in the complex plane. The regenerated PNG now uses tracked branches.
- Added a regression test with a synthetic canonical label swap and reran outputs/tests. Validation: uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py; uv run pytest tests/test_episode5_python_figure2.py; uv run pytest (61 passed, one root-exploration overflow warning).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the Python-native Figure 2 equilibrium/eigenvalue reproduction for Episode 5.

Changes:
- Added a generator script that traces 801 log-spaced w points over 0.0005--2.0 m s^-1 for p=300 hPa, T=230 K, F=1, N_a=1.0e10 m^-3.
- Wrote episode-local CSV/JSON/PNG artifacts with equilibrium state, residual diagnostics, canonical physical-Jacobian eigenvalues, regime/stability classification, Hopf crossing estimates, and run metadata.
- Documented the concrete Python command/output group in the Episode 5 README.
- Added smoke tests covering the output contract, dense-grid guard, Hopf landmark tolerance checks, metadata fields, and plot generation.

Validation:
- uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py
- uv run pytest tests/test_episode5_python_figure2.py
- uv run pytest (60 passed; one runtime overflow warning appears during exploratory root evaluation but all generated branch points converge finitely).
<!-- SECTION:FINAL_SUMMARY:END -->
