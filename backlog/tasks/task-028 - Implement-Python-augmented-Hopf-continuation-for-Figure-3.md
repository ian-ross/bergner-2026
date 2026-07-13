---
id: TASK-028
title: Implement Python augmented Hopf continuation for Figure 3
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 16:55'
labels: []
dependencies:
  - TASK-026
  - TASK-027
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build reusable Python augmented Hopf continuation infrastructure and use it to compute the Figure 3 lower and upper Hopf loci over T=190--240 K. The nonlinear continuation variables should use log-state/log-w coordinates for conditioning while Hopf conditions use the physical ODE Jacobian in physical state coordinates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reusable package infrastructure represents the augmented Hopf unknowns, residual equations, normalization, and previous-eigenvector phase condition with clear coordinate-system documentation.
- [x] #2 Python workflow seeds both Hopf branches at T=230 K from the known Episode 005 crossings, then continues downward to 190 K and upward to 240 K.
- [x] #3 Curated Python outputs include lower/upper Hopf rows with T_K, log_w, w_m_s, state, frequency, residual diagnostics, branch labels, convergence status, and method metadata.
- [x] #4 Regression tests or smoke tests verify the T=230 K Hopf velocities agree with Episode 005 landmarks and that outputs span the requested temperature domain.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Design reusable Hopf data structures for packed unknowns: log_n, log_q, s, log_w, omega, real eigenvector, imaginary eigenvector, plus branch/phase metadata.
2. Implement augmented residual equations using the existing log-coordinate equilibrium residual and the physical ODE Jacobian evaluated after converting to physical state coordinates.
3. Implement initialization at T=230 K from existing Figure 2 Hopf estimates: solve equilibrium near each w, compute the physical eigenpair, rotate/normalize the eigenvector, and solve the initial augmented system.
4. Implement temperature continuation in both directions from T=230 K using predictor-corrector solves and previous-eigenvector phase alignment.
5. Add Episode 006 Python orchestration that writes normalized lower/upper Hopf locus CSV/JSON artifacts with residuals, frequency, state, convergence, and metadata.
6. Add tests for residual packing/unpacking, phase normalization, T=230 K anchor agreement, schema fields, and coverage of the 190--240 K domain.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added reusable `bergner_spichtinger_2026.hopf` augmented Hopf infrastructure with packed log-state/log-w unknowns, physical-coordinate Jacobian Hopf rows, eigenvector normalization, and previous-eigenvector phase condition.
- Added Episode 006 Python workflow `scripts/generate_python_hopf_loci.py` seeding lower/upper Hopf branches at T=230 K from Episode 005 landmarks and continuing over T=190--240 K.
- Generated curated outputs under `episodes/006-figure3-hopf-bifurcation/outputs/figure3_python_hopf_loci/` with loci, seed rows, diagnostics, and metadata.
- Added regression/smoke tests for packing/phase normalization, T=230 K landmark agreement, output schema, and 190--240 K domain coverage.
- Verification: `uv run pytest` (80 passed; 3 existing/expected overflow warnings from solver probes).

- Added `scripts/plot_figure3_hopf_loci.py` for Episode 5-style per-backend Figure 3 plots and integrated backend-comparison plots.
- Updated the Python generator to emit `python_figure3_hopf_loci.png` next to Python loci CSVs and `outputs/figure3_backend_comparison/figure3_hopf_backend_comparison.png` overlaying available backend loci with Table II reference fits.
- Extended Episode 006 smoke test to assert plot artifacts are produced.
- Verification after plot addition: `uv run pytest` (80 passed; 3 expected solver-probe overflow warnings).

- Diagnosed bad Figure 3 plot: the explicit physical-coordinate eigenvector augmented solve admitted spurious solutions because the physical eigenvectors are extremely ill-conditioned and nearly collinear/degenerate in Euclidean component scaling; residuals could be tiny while `Re(lambda)` was not zero.
- Replaced the Python workflow solve path with a characteristic-polynomial Hopf condition (`a1*a2-a3=0` for the physical ODE Jacobian) plus log-coordinate equilibrium rows. This preserves physical-Jacobian Hopf semantics without ill-conditioned eigenvector unknowns.
- Regenerated Python loci and figures; maximum relative deviation from Table II reference samples over the curated grid is now below 1%.
- Added a regression assertion that Episode 006 smoke output remains within 2% of Table II reference fits at the smoke-grid temperatures.
- Verification: `uv run pytest` (80 passed; 3 expected solver-probe overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented Python augmented Hopf continuation for Episode 006 Figure 3 loci.

Changes:
- Added reusable `bergner_spichtinger_2026.hopf` infrastructure for packed augmented Hopf unknowns, residual equations, eigenvector normalization, previous-eigenvector phase locking, fixed-temperature Hopf solves, and branch continuation.
- Kept nonlinear equilibrium variables in `log(n)`, `log(q)`, and `log(w)` while evaluating Hopf eigenpair equations with the physical ODE Jacobian in physical `(n, q, s)` coordinates.
- Added `episodes/006-figure3-hopf-bifurcation/scripts/generate_python_hopf_loci.py` to seed both branches at `T=230 K` from Episode 005 Hopf landmarks and continue them over `T=190--240 K`.
- Wrote curated Python outputs under `outputs/figure3_python_hopf_loci/`: loci CSV, seed CSV, diagnostics CSV, and run metadata JSON.
- Updated the Episode 006 README to describe the Python workflow and output location.
- Added tests covering Hopf packing/phase behavior, T=230 K landmark correction, output schema, branch labels, convergence, and requested temperature-domain coverage.

Tests:
- `uv run pytest` (80 passed; 3 overflow warnings from solver trial points during existing/smoke workflows).

Notes/Risks:
- The Python branch labels are seed-based (`lower_hopf` from the lower Episode 005 crossing and `upper_hopf` from the upper crossing); Table II values are included as references, not used as continuation constraints.

Follow-up plotting addition:
- Added reusable Figure 3 plotting utility for method-specific and integrated comparison figures.
- Python generation now writes `python_figure3_hopf_loci.png` and the current integrated comparison figure `figure3_hopf_backend_comparison.png`; the comparison utility is ready to include AUTO/LOCA CSVs when those tasks land.
- Re-ran `uv run pytest` successfully.

Correction after plot review:
- Diagnosed the poor plotted loci as spurious roots of the explicit eigenvector augmented system caused by ill-conditioned physical-coordinate eigenvectors.
- Switched the Python production workflow to a characteristic-polynomial Hopf condition evaluated from the physical ODE Jacobian, while retaining log-state/log-w equilibrium conditioning.
- Regenerated CSV/PNG artifacts; the Python loci now track the Table II reference curves closely over `T=190--240 K` (max relative fit deviation under 1% on the curated grid).
- Added a smoke-test regression guard against this mismatch.
<!-- SECTION:FINAL_SUMMARY:END -->
