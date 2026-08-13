---
id: TASK-068
title: Run native adaptive LOCA remesh/restart continuation
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 16:04'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - adaptivity
dependencies:
  - TASK-067
references:
  - loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement structural h/r remesh boundaries around native three-stage Gauss LOCA continuation, migrate the TASK-067 reference behavior into the sparse Tpetra/Thyra/NOX/LOCA stack, and execute the planned spine-and-slices adaptive run. The task produces truthful evidence for review rather than presuming that the first run is final Figure 5 production data.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Native fixed-mesh LOCA segments stop only at accepted points for remeshing; solution/reference/tangent transfer, full Tpetra/Thyra/NOX/LOCA reconstruction, fixed-parameter NOX/KLU2 correction, tangent renormalization or deterministic rebootstrap, exact retry order, and native restart follow the v1 contract
- [ ] #2 Before the adaptive run, frozen TASK-067 nonuniform fixtures pass component-level Python/C++ parity for base residuals, analytic Jacobian and normalized parameter columns, nonuniform phase quadrature, continuation metric, collocation-polynomial transfer, and fixed-parameter correction; C++ defect, probe escalation, monitor, h marking, bounded r movement, mesh/cycle budgets, restart retries, phase-refresh triggers, near-Hopf diagnostics, and single-valued tripwires also match the Python intermediate results
- [ ] #3 Every accepted segment point and remesh restart passes independent residual/phase/positivity/linear/restart gates; unresolved points, rejected steps, cap escalations, aliasing, active non-Floquet Radau triggers, and tripwires are recorded rather than interpolated or suppressed; Floquet-dependent evidence is recorded as not_evaluated
- [ ] #4 Deterministic per-segment artifacts and restart manifests record native vectors or checkpoints, accepted/rejected LOCA events, mesh histories, transfer corrections, defects, period/orbit convergence, phase lineage, terminal target statuses, runtime/memory profiles, source fingerprints, and resumable completion state
- [ ] #5 Stratified native points match independent Python adaptive corrections within versioned tolerances, the planned run can be regenerated or checked, and focused tests cover nonuniform parity, remesh rebuild identity, event partitioning, restart recovery, resume behavior, terminal manifest coverage, and fixed-mesh regressions
- [ ] #6 The adaptive run records near-Hopf amplitude/period approach points and terminal statuses, targeting at least five reliable points when reached, but leaves quadratic/quartic fit review and final connection/gap policy to TASK-069
<!-- AC:END -->
