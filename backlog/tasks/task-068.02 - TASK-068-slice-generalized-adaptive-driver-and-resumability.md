---
id: TASK-068.02
title: 'TASK-068 slice: generalized adaptive driver and resumability'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
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
Generalize the one-branch slice into a reusable native adaptive continuation driver with explicit segment lifecycle, remesh/restart orchestration, checkpointing, resume, stale-checkpoint rejection, target bookkeeping, and runtime/resource accounting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Driver supports repeated native fixed-mesh LOCA segment execution, accepted-point remesh boundaries, h+r and pure-r restart paths, tangent renormalization/rebootstrap policy, and deterministic retry ordering
- [ ] #2 Run manifests and checkpoint directories are resumable and reject stale or incompatible checkpoints using schema, source, executable, vector, and configuration fingerprints
- [ ] #3 Every segment records accepted/rejected LOCA callbacks, mesh history, transfer/correction details, defects, convergence diagnostics, phase lineage, runtime, and memory/resource fields
- [ ] #4 Focused tests cover resume after interruption, stale checkpoint rejection, event partitioning, remesh rebuild identity, and fixed-mesh regression behavior
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extract the one-branch runner into a reusable native adaptive driver interface with explicit segment lifecycle states: pending, running_fixed_mesh, remesh_pending, restart_pending, accepted, unresolved, tripwire_stop, near_hopf_stop, or failed.
2. Define durable checkpoint and manifest schemas for segments, targets, remesh cycles, vector artifacts, source/build fingerprints, executable identity, runtime/resource counters, and resume state.
3. Implement checkpoint writing, atomic manifest updates, resume from the latest complete state, and stale-checkpoint rejection based on schema version, source fingerprints, executable/build identity, vector checksums, parameters, mesh, rule, and target manifest.
4. Generalize remesh/restart orchestration for repeated h+r and pure-r cycles, including deterministic retry order, tangent renormalization, tangent-only rebootstrap, phase refresh triggers, cap/cycle budgets, and explicit terminal outcomes.
5. Integrate event partitioning and accounting invariants for LOCA callbacks, accepted/rejected attempts, initial/regular/final saves, remesh boundaries, and restart lineage.
6. Add focused tests for process interruption/resume, stale checkpoint rejection, repeated remesh cycles, event partitioning, remesh rebuild identity, and fixed-mesh behavior when no remesh is requested.
7. Regenerate/check driver smoke artifacts and update documentation with driver contracts, resume commands, and known scope boundaries.
<!-- SECTION:PLAN:END -->
