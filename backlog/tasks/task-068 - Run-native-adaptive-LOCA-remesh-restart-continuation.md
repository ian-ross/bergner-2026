---
id: TASK-068
title: Run native adaptive LOCA remesh/restart continuation
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 15:49'
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
- [ ] #1 Native fixed-mesh LOCA segments stop only at accepted points for remeshing; solution/reference/tangent transfer, full Tpetra/Thyra/NOX/LOCA reconstruction, fixed-parameter NOX/KLU2 correction, tangent renormalization or deterministic rebootstrap, and native restart follow the v1 contract
- [ ] #2 C++ defect, monitor, h marking, bounded r movement, mesh/cycle budgets, restart retries, phase-refresh triggers, near-Hopf stopping diagnostics, and single-valued tripwires match the Python reference on frozen remesh fixtures
- [ ] #3 The adaptive run covers the T=225 K move to the spine, both temperature directions over the planned spine range, and signed rho slices on the provisional 2 K skeleton where v1 reliability permits, while retaining exact T=210 K and T=225 K anchors
- [ ] #4 Every accepted segment point and remesh restart passes independent residual/phase/positivity/linear/restart gates; unresolved points, rejected steps, cap escalations, aliasing, Radau triggers, and tripwires are recorded rather than interpolated or suppressed
- [ ] #5 Deterministic per-segment artifacts and restart manifests record native vectors or checkpoints, accepted/rejected LOCA events, mesh histories, transfer corrections, defects, period/orbit convergence, phase lineage, runtime/memory profiles, source fingerprints, and resumable completion state
- [ ] #6 Stratified native points match independent Python adaptive corrections within versioned tolerances, the planned run can be regenerated or checked, and focused tests cover remesh rebuild identity, event partitioning, restart recovery, resume behavior, and fixed-mesh regressions
- [ ] #7 Stratified native points match independent Python adaptive corrections within versioned tolerances, the planned run can be regenerated or checked, and focused tests cover nonuniform parity, remesh rebuild identity, event partitioning, restart recovery, resume behavior, terminal manifest coverage, and fixed-mesh regressions
<!-- AC:END -->
