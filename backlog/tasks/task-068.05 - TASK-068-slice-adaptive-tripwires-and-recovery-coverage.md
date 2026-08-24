---
id: TASK-068.05
title: 'TASK-068 slice: adaptive tripwires and recovery coverage'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - adaptivity
  - tests
dependencies: []
parent_task_id: TASK-68
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Complete the remaining failure-policy and edge-case coverage for native adaptive continuation, including tripwires, cap escalation, restart failures, pure-r paths, tangent rebootstrap, phase refresh triggers, and truthful preservation of not_evaluated evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Synthetic or branch-smoke tests cover failed transfer/correction, pure-r restart, h+r retry escalation, tangent-only deterministic rebootstrap, phase refresh triggers, process interruption/resume, and stale checkpoint rejection
- [ ] #2 Native adaptive diagnostics record cap escalations, aliasing, defect/convergence/ringing/nonphysical-value Radau triggers, single-valued tripwires, and rejection reasons without suppressing failed or unresolved points
- [ ] #3 Near-Hopf diagnostics and single-valued tripwires match the documented Python/reference policy where fixtures exist, and otherwise record not_evaluated or explicit reasons
- [ ] #4 Broader IVP-based and all Floquet-dependent evidence remain explicitly not_evaluated through TASK-068
<!-- AC:END -->
