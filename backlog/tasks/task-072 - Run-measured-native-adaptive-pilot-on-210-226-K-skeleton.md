---
id: TASK-072
title: Run measured native adaptive pilot on 210-226 K skeleton
status: To Do
assignee: []
created_date: '2026-08-24 13:18'
labels:
  - episode-008
  - loca
  - adaptivity
  - production
dependencies:
  - TASK-069
  - TASK-070
  - TASK-071
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Execute a real measured native adaptive pilot over the TASK-068 provisional 210--226 K spine-and-slices skeleton. The pilot replaces pending provisional statuses with backend-emitted accepted, resolution_unresolved, near_hopf_stop, tripwire_stop, or failed statuses and preserves explicit gaps.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 31 provisional skeleton targets have exactly one backend-emitted terminal status with reasons, not relabeled fixed-mesh or Python evidence
- [ ] #2 Accepted points and remesh restarts pass residual, phase, positivity, finite-change, tangent, linear-solve, defect, and period/orbit convergence gates required by the schemas
- [ ] #3 Runtime/resource fields are measured, source/build/checkpoint identities are recorded, and the run can be regenerated, checked, or safely resumed without stale checkpoint reuse
- [ ] #4 Unaccepted targets remain explicit unresolved/gap records and no interpolation is used to fill them
<!-- AC:END -->
