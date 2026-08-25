---
id: TASK-077
title: Implement Floquet postprocessing for native production orbits
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 12:19'
labels:
  - episode-008
  - floquet
  - validation
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Compute Floquet multiplier diagnostics from saved native collocation orbits as postprocessing, not as nonlinear unknowns or TASK-068 acceptance evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 DOP853 variational integration over native piecewise collocation polynomials records trivial and nontrivial multipliers, tolerance-refinement comparisons, stability classifications, and provenance for schema-valid accepted production points
- [ ] #2 Implicit Radau comparisons are run at stratified difficult points and suspected unit-circle crossings, with ambiguous or unstable classifications recorded rather than suppressed
- [ ] #3 Floquet diagnostics link to continuation records and do not relabel failed/unresolved targets or Hopf-limit equilibrium records as regular orbits
<!-- AC:END -->
