---
id: TASK-064
title: Qualify Python higher-order fixed-mesh periodic orbits
status: To Do
assignee: []
created_date: '2026-08-13 15:34'
labels:
  - episode-008
  - python
  - numerics
  - collocation
dependencies:
  - TASK-062
references:
  - src/bergner_spichtinger_2026/periodic_orbits.py
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generalize the Python periodic-orbit reference from one-stage midpoint to explicit two- and three-stage Gauss--Legendre collocation, then execute the TASK-062 fixed-mesh qualification ladder at the canonical and three T=210 K guard points. This task establishes higher-order layout/residual/Jacobian/transfer behavior and numerical evidence before native migration; it does not implement adaptive remeshing or production Figure 5 sampling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reusable Python layout, residual, analytic sparse Jacobian, phase condition, and collocation-polynomial evaluator support one-, two-, and three-stage Gauss rules on uniform fixed meshes without midpoint-specific assumptions
- [ ] #2 The canonical T=225 K, w=0.1 m/s ladder runs midpoint N=64/128/256, two-stage Gauss N=32/64/128, and three-stage Gauss N=16/32/64; failed coarse cases are retained with rejection diagnostics
- [ ] #3 The T=210 K rho=0 and rho=+/-0.15 guard points run two-stage N=64/128 and three-stage N=32/64 from reproducible TASK-061-derived seeds
- [ ] #4 Curated artifacts report component residual gates, period and phase-aligned weighted-orbit refinement, two-grid independent defects, solver provenance, and the versioned qualification decisions at every case
- [ ] #5 Best successive solutions meet the TASK-062 1e-3 period/orbit checks where supported, the canonical point is compared with an independent IVP to 1e-3, and any miss is preserved as evidence rather than tuned away
- [ ] #6 Focused tests cover pack/unpack, residual/Jacobian directional checks, coefficient use, collocation transfer/evaluation, defect grids, deterministic regeneration, and existing midpoint compatibility
<!-- AC:END -->
