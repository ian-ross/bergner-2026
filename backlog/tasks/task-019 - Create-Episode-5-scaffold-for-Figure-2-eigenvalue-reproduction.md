---
id: TASK-019
title: Create Episode 5 scaffold for Figure 2 eigenvalue reproduction
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
labels:
  - episode-005
  - figure2
  - eigenvalues
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the episode scaffold and planning notes for reproducing Bergner & Spichtinger (2026) Figure 2 eigenvalues across Python, AUTO, and LOCA. Document the agreed target: p = 300 hPa, T = 230 K, F = 1, N_a = 1.0e10 m^-3, w = 0.0005--2.0 m s^-1, and physical ODE Jacobian eigenvalues rather than transformed continuation-residual eigenvalues.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode directory episodes/005-figure2-eigenvalues/ exists with README and appropriate docs/scripts/outputs/notebooks placeholders.
- [ ] #2 README or planning notes record the agreed Figure 2 parameter set, paper w range, and N_a assumption.
- [ ] #3 Planning notes state that Python, AUTO, and LOCA generate independent equilibrium/eigenvalue outputs for comparison.
- [ ] #4 Planning notes state that LOCA must compute physical Jacobian/eigenvalues backend-side using Sacado plus Teuchos/LAPACK where available, while AUTO may fall back to Python analytic eigenvalues after documenting native options.
<!-- AC:END -->
