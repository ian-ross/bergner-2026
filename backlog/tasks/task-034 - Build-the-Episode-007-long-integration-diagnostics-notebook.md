---
id: TASK-034
title: Build the Episode 007 long-integration diagnostics notebook
status: To Do
assignee: []
created_date: '2026-07-20 20:54'
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
- [ ] #1 The notebook uses T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=1e10 m^-3, Delta z=100 m, and Evap_n disabled, with all units and solver settings recorded
- [ ] #2 The paper-style 0.99-equilibrium start and the approved independent n, q, and s perturbations are integrated long enough to assess approximately 300 linearized periods or an explicitly justified equivalent horizon
- [ ] #3 Over the final 20 complete cycles, period and saturation-amplitude drift are each below 0.1%, and all four trajectories converge to the same orbit within a documented tolerance
- [ ] #4 Curated outputs include the approved limit-cycle stability, attractor-convergence log10(n)-s orbit, and one-cycle state/process-budget figures
- [ ] #5 The process figure shows Nuc_n, Sed_n, and total dn/dt; Nuc_q, Dep_q, Sed_q, and total dq/dt; and Cool, Nuc_s, Dep_s, and total ds/dt
- [ ] #6 Reference outputs include a 17-significant-digit CSV with an early transient and final three cycles, a full-run per-cycle summary CSV, and versioned JSON metadata containing parameters, units, initial conditions, solver settings, cycle boundaries, and convergence metrics
- [ ] #7 The notebook runs from a clean checkout through a documented command and regenerates all curated outputs without manual cell state
<!-- AC:END -->
