---
id: TASK-019
title: Create Episode 5 scaffold for Figure 2 eigenvalue reproduction
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 11:18'
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
- [x] #1 Episode directory episodes/005-figure2-eigenvalues/ exists with README and appropriate docs/scripts/outputs/notebooks placeholders.
- [x] #2 README or planning notes record the agreed Figure 2 parameter set, paper w range, and N_a assumption.
- [x] #3 Planning notes state that Python, AUTO, and LOCA generate independent equilibrium/eigenvalue outputs for comparison.
- [x] #4 Planning notes state that LOCA must compute physical Jacobian/eigenvalues backend-side using Sacado plus Teuchos/LAPACK where available, while AUTO may fall back to Python analytic eigenvalues after documenting native options.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/005-figure2-eigenvalues/ with README plus docs/, scripts/, outputs/, and notebooks/ placeholders following existing episode conventions.
2. Draft planning notes summarizing the Figure 2 target parameters, paper range, N_a assumption, and physical-Jacobian scope decisions from the grill session.
3. Cross-reference upstream Figure 1 Python/AUTO/LOCA artifacts and reusable backend directories that Episode 5 will depend on.
4. Document backend responsibilities: independent branch generation for Python/AUTO/LOCA, strict LOCA backend-side physical eigenvalues, and documented AUTO fallback policy.
5. Add minimal reproduction-command placeholders and known-open-items section so later tasks can fill in concrete commands and outputs.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Created Episode 5 scaffold at episodes/005-figure2-eigenvalues/ with README, docs/planning-decisions.md, and .gitkeep placeholders for scripts/outputs/notebooks.
- Documented agreed Figure 2 target parameters, physical-ODE eigenvalue semantics, backend independence requirements, LOCA Sacado/Teuchos/LAPACK responsibility, and AUTO fallback policy.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Created the Episode 5 scaffold for Figure 2 eigenvalue reproduction.

Changes:
- Added episodes/005-figure2-eigenvalues/ with README plus docs/, scripts/, outputs/, and notebooks/ placeholders.
- Added planning notes covering the agreed p/T/F/N_a/w target, physical-ODE Jacobian eigenvalue scope, Python/AUTO/LOCA independent output expectations, LOCA backend-side Sacado plus Teuchos/LAPACK requirement, and documented AUTO fallback policy.
- Cross-referenced existing Figure 1 Python, AUTO, LOCA, shared backend, and testing/reproduction notes for later implementation tasks.

Tests:
- Not run; scaffold/documentation-only change.
<!-- SECTION:FINAL_SUMMARY:END -->
