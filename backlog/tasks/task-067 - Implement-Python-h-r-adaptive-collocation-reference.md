---
id: TASK-067
title: Implement Python h/r adaptive collocation reference
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 15:50'
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
- [ ] #2 The v1 r monitor rejects negative/nonfinite densities and implements documented stable max-rescaling, zero-density handling, phase-average normalization, winsorization, and renormalization for defect, scaled speed, curvature, and nucleation densities with the 0.20 floor and 0.50/0.20/0.20/0.10 weights, without landmark snapping
- [ ] #3 Defect-driven h marking, 50% growth cap, bounded 50%-relaxed r movement, interval width/ratio constraints, N=256 soft and N=512 hard caps, cycle budgets, and forced-h stagnation rule are deterministic and tested
- [ ] #4 Old collocation polynomials transfer solution, phase reference, and tangent to the new mesh; fixed-parameter correction and v1 restart gates implement the exact three-attempt retry order and deterministic rebootstrap for tangent-only failure
- [ ] #5 Adaptive qualification runs start from N=32 at the four fixed qualification points and record convergence, mesh distributions, defects, period/orbit changes, phase refreshes, unresolved budgets, aliasing triggers, and active non-Floquet Radau-trigger evidence without hiding failures; Floquet-dependent evidence is recorded as not_evaluated
- [ ] #6 Curated artifacts emit deterministic language-neutral adaptive/remesh fixtures consumed by TASK-068, including inputs and intermediate expected results for defect grids, probe escalation, monitor construction, marking, movement, transfer, restart/retry, schemas, and checksums; focused tests cover those contracts and fixed-mesh compatibility
<!-- AC:END -->
