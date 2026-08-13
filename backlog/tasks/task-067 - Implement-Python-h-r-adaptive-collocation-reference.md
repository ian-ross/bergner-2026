---
id: TASK-067
title: Implement Python h/r adaptive collocation reference
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 16:05'
labels:
  - episode-008
  - python
  - numerics
  - adaptivity
dependencies:
  - TASK-066
references:
  - src/bergner_spichtinger_2026/periodic_orbits.py
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the transparent Python reference for TASK-062 v1 external h/r adaptation on globally fixed three-stage Gauss--Legendre orbits. The reference owns two-grid defect evaluation, defect-driven splitting, bounded monitor redistribution, collocation-polynomial transfer, fixed-parameter correction, and reproducible remesh diagnostics; it does not emulate native LOCA remesh ownership.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The independent defect implementation evaluates next-higher Gauss and staggered dyadic grids, applies the material-disagreement, fixed-128-bin recurrence, and 16-point probe rules, and exposes per-element/max defects plus endpoint/jump/grid-disagreement diagnostics
- [ ] #2 Old collocation polynomials transfer solution, phase reference, and tangent to the new mesh; fixed-parameter correction and v1 restart gates implement the exact three-attempt retry order and deterministic rebootstrap for tangent-only failure
- [ ] #3 Curated artifacts emit deterministic language-neutral adaptive/remesh fixtures consumed by TASK-068, including inputs and intermediate expected results for defect grids, probe escalation, monitor construction, marking, movement, transfer, restart/retry, schemas, and checksums; focused tests cover those contracts and fixed-mesh compatibility
- [ ] #4 The v1 r monitor evaluates all four densities at 16 equal subcell midpoints per current element, uses documented weighted deterministic normalization, builds and inverts the piecewise-constant cumulative monitor with the stated tolerance, and applies simultaneous global-beta feasibility retries through 2^-20 with r_movement_stalled fallback
- [ ] #5 The deterministic adaptation cycle distinguishes ordinary h+r, pure-r, forced single-split h+r after stagnation, convergence stop, N=256 soft-cap escalation, and N=512/cycle-budget resolution_unresolved outcomes
- [ ] #6 Adaptive qualification runs start from N=32 at the four fixed qualification points and record convergence, meshes, defects, period/orbit changes, phase refreshes, unresolved budgets, aliasing, and active defect/convergence/ringing/nonphysical-value Radau triggers without hiding failures; broader IVP-based and all Floquet-dependent evidence are not_evaluated through TASK-068
<!-- AC:END -->
