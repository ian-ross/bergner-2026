---
id: TASK-068.01
title: 'TASK-068 slice: native adaptive one-branch segment runner'
status: To Do
assignee: []
created_date: '2026-08-24 10:51'
updated_date: '2026-08-24 10:53'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review current TASK-068 C++ seams and artifacts: adaptive-controller, adaptive-transfer, adaptive-restart, native higher-order LOCA branch replay, restart-smoke generator, and manifest ledger. Identify the smallest branch/target that can exercise one accepted LOCA segment followed by one remesh/restart.
2. Define a one-branch native adaptive runner schema for segment state, remesh event, checkpoint vector keys, controller output, transfer/correction diagnostics, restart gates, source/build fingerprints, and terminal status. Keep the scope explicit: smoke slice only, not the full spine-and-slices run.
3. Implement the orchestration path around the existing native three-stage LOCA stack: run a fixed-mesh segment to an accepted point, stop only at that point, compute defect/controller output, choose the deterministic remesh action, and prepare transfer/restart inputs.
4. Reuse and harden the native transfer/restart code path to transfer solution/reference/tangent, rebuild Tpetra/Thyra/NOX/KLU2/LOCA objects, fixed-parameter correct, renormalize or rebootstrap tangent according to the v1 retry contract, and restart or record failure.
5. Emit deterministic one-branch artifacts and vectors with truthful completion state, accepted/rejected events, mesh history, transfer/correction diagnostics, gates, and provenance.
6. Add focused tests comparing the one-branch runner to existing Python expectations and restart-smoke outputs, including gate enforcement and no false full-run claims.
7. Regenerate/check artifacts, run focused tests and relevant fixed-mesh regression tests, then update TASK-068 parent manifest/README references to the one-branch evidence.
<!-- SECTION:PLAN:END -->
