---
id: TASK-071
title: Profile native adaptive continuation resource usage
status: To Do
assignee: []
created_date: '2026-08-24 13:18'
labels:
  - episode-008
  - profiling
  - numerics
dependencies:
  - TASK-069
  - TASK-070
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace TASK-068 deterministic zero resource placeholders with measured native adaptive continuation cost evidence. The profile must use the current native adaptive backend seams and production-schema metadata without interpreting cost measurements as scientific acceptance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Measured wall-clock time, CPU time, max RSS, nonlinear iterations, KLU2 symbolic/numeric factorization counts, linear solves, and source/build/runtime identities are recorded for representative fixed-mesh, remesh/restart, and pilot-style native adaptive segments
- [ ] #2 The review determines whether serial KLU2 remains acceptable or whether the documented iterative-solver trigger thresholds are met
- [ ] #3 Resource artifacts are reproducible or checkable and are linked from Episode 008 documentation without leaving placeholder values in production-policy decisions
<!-- AC:END -->
