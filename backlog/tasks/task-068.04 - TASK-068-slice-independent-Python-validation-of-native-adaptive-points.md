---
id: TASK-068.04
title: 'TASK-068 slice: independent Python validation of native adaptive points'
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-24 10:52'
updated_date: '2026-08-24 12:10'
labels:
  - episode-008
  - python
  - cpp
  - numerics
  - adaptivity
dependencies: []
parent_task_id: TASK-68
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate a stratified set of accepted native adaptive continuation points against independent Python adaptive/fixed-parameter corrections at identical physical coordinates with versioned tolerances.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A deterministic stratification policy selects representative accepted native adaptive points across spine, slices, remesh events, anchors, and near-Hopf approach regions when present
- [ ] #2 Python validation corrects at identical physical coordinates without seeding from native vectors except as explicitly forbidden/allowed by the validation contract
- [ ] #3 Validation artifacts record period error, weighted orbit distance, residual/phase/positivity gates, mesh comparison, source fingerprints, and tolerance versions
- [ ] #4 Focused tests verify regeneration/check behavior, tolerance enforcement, failure reporting, and no relabeling of Python-only evidence as native adaptive execution
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the TASK-068.03 provisional run schema and accepted-point records in outputs/native_adaptive_spine_slices_run*.json plus the adaptive driver manifest/checkpoints to identify authoritative native accepted points and source fingerprints.
2. Add an episode-local validation generator that deterministically stratifies accepted native adaptive points across segment type, target/anchor status, remesh/restart lineage, mesh generation/size, endpoint/interior position, and near-Hopf approach when present.
3. Implement an explicit validation contract that rebuilds Python corrections/evaluations at the identical physical coordinates using frozen Python/adaptive inputs, records any allowed seed provenance, and forbids native-vector seeding for accepted validation evidence.
4. Emit versioned JSON/NPZ validation artifacts with selected-point provenance, period/weighted-orbit errors, residual/phase/positivity gates, mesh comparisons, checksums, source/runtime fingerprints, tolerance versions, and pass/fail reasons.
5. Wire validation summaries into the native adaptive manifest/evidence ledger without relabeling Python-only validation as native adaptive execution.
6. Add focused tests for deterministic stratification, identical-coordinate enforcement, tolerance failures, source/vector checksum checks, --check byte/regeneration behavior, and truthfulness labels.
7. Run the new focused tests plus relevant native adaptive manifest/spine-slices checks, then update task notes/final summary and mark acceptance criteria complete as they pass.
<!-- SECTION:PLAN:END -->
