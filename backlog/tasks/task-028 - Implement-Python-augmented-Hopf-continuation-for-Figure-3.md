---
id: TASK-028
title: Implement Python augmented Hopf continuation for Figure 3
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 16:44'
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
<!-- SECTION:FINAL_SUMMARY:END -->
