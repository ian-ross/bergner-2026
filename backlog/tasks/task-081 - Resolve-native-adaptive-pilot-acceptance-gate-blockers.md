---
id: TASK-081
title: Resolve native adaptive pilot acceptance gate blockers
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 16:16'
updated_date: '2026-08-25 10:51'
labels:
  - episode-008
  - loca
  - validation
  - production
dependencies:
  - TASK-073
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/task073-native-adaptive-pilot-reconciliation.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up required by TASK-073 before full-domain Figure 5 continuation can be production-authorized. Complete the exact native restart-vector defect and period/orbit convergence gate bundle, rerun or revise the measured native adaptive pilot, and ensure accepted targets either pass independent validation or remain explicit gaps.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Exact native restart-vector independent defect and period/orbit convergence gates are backend-bound for post-remesh and accepted pilot targets
- [ ] #2 A revised measured pilot over the 210--226 K skeleton records exactly one backend-emitted terminal status per target without interpolation or evidence relabeling
- [ ] #3 Any accepted pilot target has same-coordinate independent Python validation and justified IVP validation, or is downgraded to an explicit unresolved/gap record with a blocking reason
- [ ] #4 The follow-up review explicitly states whether TASK-075 may proceed under the retained v1 method or requires a method-version revision
<!-- AC:END -->
