---
id: TASK-034
title: Build the Episode 007 long-integration diagnostics notebook
status: Done
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:28'
labels:
  - episode-007
  - science
  - notebook
dependencies:
  - TASK-032
  - TASK-033
references:
  - episodes/001-figure4-time-series/scripts/reproduce_figure4.py
  - src/bergner_spichtinger_2026/core.py
  - docs/REPRODUCTION_NOTES.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the authoritative Episode 007 notebook for the high-aerosol Figure 4 center case. Demonstrate persistent oscillation and attraction, explain the full three-variable process budgets, produce curated scientific figures, and export compact reference artifacts for browser validation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The notebook uses T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=1e10 m^-3, Delta z=100 m, and Evap_n disabled, with all units and solver settings recorded
- [x] #2 The paper-style 0.99-equilibrium start and the approved independent n, q, and s perturbations are integrated long enough to assess approximately 300 linearized periods or an explicitly justified equivalent horizon
- [x] #3 Over the final 20 complete cycles, period and saturation-amplitude drift are each below 0.1%, and all four trajectories converge to the same orbit within a documented tolerance
- [x] #4 Curated outputs include the approved limit-cycle stability, attractor-convergence log10(n)-s orbit, and one-cycle state/process-budget figures
- [x] #5 The process figure shows Nuc_n, Sed_n, and total dn/dt; Nuc_q, Dep_q, Sed_q, and total dq/dt; and Cool, Nuc_s, Dep_s, and total ds/dt
- [x] #6 Reference outputs include a 17-significant-digit CSV with an early transient and final three cycles, a full-run per-cycle summary CSV, and versioned JSON metadata containing parameters, units, initial conditions, solver settings, cycle boundaries, and convergence metrics
- [x] #7 The notebook runs from a clean checkout through a documented command and regenerates all curated outputs without manual cell state
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Build the notebook around package APIs and the canonical environment T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=1e10 m^-3, Delta z=100 m, with Evap_n disabled.
2. Compute the positive equilibrium and linearized oscillation period, construct the paper-style and three directional perturbations, and integrate all four trajectories for approximately 300 linearized periods with documented tolerances and output sampling.
3. Detect complete cycles, evaluate final-20-cycle period/amplitude drift, and compare converged orbit geometry across all initial conditions against the approved thresholds.
4. Evaluate every process term and total tendency along the trajectories, then select a representative final cycle for mechanistic analysis.
5. Generate the three curated figures: long-run stability diagnostics, multi-start attraction in log10(n)-s space, and synchronized state/process budgets over one cycle.
6. Export the early transient and final three cycles at 17-significant-digit precision, the full per-cycle summary, and schema-versioned JSON metadata with units and provenance.
7. Execute the notebook from a clean state using the documented command, verify regenerated artifacts and metrics, and record numerical limitations.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Implemented and clean-executed the authoritative RK45 log-state notebook for the 300-linear-period center-case integration.
- Generated the three curated figures plus 17-significant-digit trajectory, per-cycle, and schema-versioned metadata artifacts.
- Added notebook/output contract tests; full suite passed (107 tests; 3 pre-existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the authoritative Episode 007 long-integration diagnostics notebook and committed it as 72a90b7.

Changes:
- Added clean-run log-state RK45 integration for the high-aerosol Figure 4 center case, four approved starts, 300 linearized periods, late-cycle drift analysis, and phase-independent all-start orbit convergence checks.
- Generated curated stability, attractor, and one-cycle full process-budget figures plus high-precision browser-validation CSV/JSON fixtures.
- Added tests for notebook solver/process contracts and generated artifact metadata/schema requirements; updated the episode rerun documentation.

Tests:
- uv run jupyter execute episodes/007-limit-cycle-interactive-widget/notebooks/01_limit_cycle_diagnostics.ipynb --inplace
- uv run pytest -q (107 passed; 3 existing numerical overflow warnings)
<!-- SECTION:FINAL_SUMMARY:END -->
