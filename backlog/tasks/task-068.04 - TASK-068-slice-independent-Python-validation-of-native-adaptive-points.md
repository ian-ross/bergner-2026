---
id: TASK-068.04
title: 'TASK-068 slice: independent Python validation of native adaptive points'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
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
