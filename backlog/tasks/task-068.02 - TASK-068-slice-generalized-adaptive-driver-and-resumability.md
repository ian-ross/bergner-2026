---
id: TASK-068.02
title: 'TASK-068 slice: generalized adaptive driver and resumability'
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 10:52'
updated_date: '2026-08-24 11:20'
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
- [x] #1 Driver supports repeated native fixed-mesh LOCA segment execution, accepted-point remesh boundaries, h+r and pure-r restart paths, tangent renormalization/rebootstrap policy, and deterministic retry ordering
- [x] #2 Run manifests and checkpoint directories are resumable and reject stale or incompatible checkpoints using schema, source, executable, vector, and configuration fingerprints
- [x] #3 Every segment records accepted/rejected LOCA callbacks, mesh history, transfer/correction details, defects, convergence diagnostics, phase lineage, runtime, and memory/resource fields
- [x] #4 Focused tests cover resume after interruption, stale checkpoint rejection, event partitioning, remesh rebuild identity, and fixed-mesh regression behavior
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added reusable `native_adaptive_driver.py` orchestration module with pluggable backend, lifecycle states, deterministic h+r/pure-r retry policies, atomic manifests/checkpoints, resume validation, event partitioning, and resource accounting.
- Added focused Episode 008 tests for interruption/resume, stale source/config rejection, event partitioning, remesh rebuild/retry identity, and fixed-mesh no-remesh regression.
- Updated Episode 008 README with the generalized driver/resumability contract.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented a reusable native adaptive continuation driver/resumability layer for TASK-068.02.

Changes:
- Added `src/bergner_spichtinger_2026/native_adaptive_driver.py` with a pluggable native backend protocol, versioned segment lifecycle states, repeated fixed-mesh segment orchestration, accepted-point remesh boundaries, h+r and pure-r restart paths, deterministic TASK-067 retry ordering, tangent policy recording, event partitioning, atomic manifest/checkpoint writes, resume validation, and runtime/resource accounting.
- Exported the driver API from the package.
- Added focused tests covering interruption/resume without rerunning completed checkpoints, stale source/config fingerprint rejection, event partitioning, remesh rebuild/retry identity, and fixed-mesh no-remesh behavior.
- Updated the Episode 008 README with driver contracts and resume/stale-checkpoint behavior.

Tests:
- `uv run pytest tests/test_episode8_native_adaptive_driver.py tests/test_episode8_native_adaptive_loca_manifest.py -q`
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check`
<!-- SECTION:FINAL_SUMMARY:END -->
