---
id: TASK-068.02
title: 'TASK-068 slice: generalized adaptive driver and resumability'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
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
Generalize the one-branch slice into a reusable native adaptive continuation driver with explicit segment lifecycle, remesh/restart orchestration, checkpointing, resume, stale-checkpoint rejection, target bookkeeping, and runtime/resource accounting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Driver supports repeated native fixed-mesh LOCA segment execution, accepted-point remesh boundaries, h+r and pure-r restart paths, tangent renormalization/rebootstrap policy, and deterministic retry ordering
- [ ] #2 Run manifests and checkpoint directories are resumable and reject stale or incompatible checkpoints using schema, source, executable, vector, and configuration fingerprints
- [ ] #3 Every segment records accepted/rejected LOCA callbacks, mesh history, transfer/correction details, defects, convergence diagnostics, phase lineage, runtime, and memory/resource fields
- [ ] #4 Focused tests cover resume after interruption, stale checkpoint rejection, event partitioning, remesh rebuild identity, and fixed-mesh regression behavior
<!-- AC:END -->
