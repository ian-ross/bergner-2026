---
id: TASK-068.04
title: 'TASK-068 slice: independent Python validation of native adaptive points'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
updated_date: '2026-08-24 10:53'
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
1. Define a deterministic stratification policy for selecting accepted native adaptive points across branch types, anchors, remesh generations, mesh sizes, endpoint/interior events, slices, and near-Hopf approach regions when present.
2. Build independent Python validation inputs at identical physical coordinates using the frozen adaptive/Python formulation and documented seeding policy. Do not seed validation from native vectors unless the contract explicitly records and permits that diagnostic.
3. Correct or evaluate each selected point with Python and compute versioned comparison diagnostics: period relative error, weighted orbit distance, residual blocks, phase residual, positivity, mesh/phase-reference checks, and correction status.
4. Emit validation JSON/NPZ artifacts with selected point provenance, native source checkpoint IDs, Python solver provenance, tolerance versions, pass/fail gates, and explicit reasons for any nonvalidated point.
5. Add tests for stratification determinism, identical-coordinate enforcement, tolerance failure behavior, source/vector checksums, --check regeneration, and truthfulness boundaries between Python validation and native adaptive execution.
6. Feed validation summaries back into the TASK-068 native adaptive manifest and parent evidence ledger.
7. Run focused validation tests plus relevant adaptive/native manifest checks and document the validation results for TASK-069 review.
<!-- SECTION:PLAN:END -->
