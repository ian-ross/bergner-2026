---
id: TASK-068.01
title: 'TASK-068 slice: native adaptive one-branch segment runner'
status: To Do
assignee: []
created_date: '2026-08-24 10:51'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - adaptivity
dependencies: []
parent_task_id: TASK-68
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the first real integrated native adaptive LOCA slice for one branch/smoke target. This should move beyond component seams by running a fixed-mesh native LOCA segment to an accepted remesh boundary, applying the TASK-067 adaptive controller, rebuilding the sparse stack after h/r transfer, correcting with fixed-parameter NOX/KLU2, and restarting with truthful artifacts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One selected native three-stage branch runs through at least one accepted fixed-mesh LOCA segment and stops for remeshing only at an accepted point
- [ ] #2 The remesh path transfers solution, refreshed phase reference, and tangent; rebuilds Tpetra/Thyra/NOX/KLU2/LOCA objects; applies fixed-parameter correction; and enforces residual, phase, positivity, linear, finite-change, and tangent gates
- [ ] #3 Per-segment artifacts record native checkpoints, accepted/rejected events, mesh/transfer history, defect/controller output, correction diagnostics, source fingerprints, and resumable state without claiming full spine-and-slices completion
- [ ] #4 Focused tests verify the one-branch runner against independent Python expectations and existing restart-smoke parity
<!-- AC:END -->
