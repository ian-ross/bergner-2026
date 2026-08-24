---
id: TASK-068.05
title: 'TASK-068 slice: adaptive tripwires and recovery coverage'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory all documented TASK-067/TASK-068 failure policies and tripwires: failed transfer/correction, pure-r and h+r retry escalation, tangent-only rebootstrap, phase refresh, cap escalation, aliasing, defect/convergence stagnation, ringing/nonphysical-value triggers, near-Hopf diagnostics, and single-valuedness checks.
2. Add synthetic fixtures or controlled branch-smoke cases that deterministically exercise each policy without contaminating the production run artifacts.
3. Implement or expose any missing native diagnostics needed to record the policies, preserving broader IVP-based and Floquet-dependent evidence as not_evaluated through TASK-068.
4. Extend manifests so unresolved points, rejections, cap escalations, Radau-trigger evidence, tripwire stops, and failed restarts are recorded with explicit reasons and cannot be suppressed by later successful retries.
5. Add focused tests for failed transfer/correction, pure-r path, h+r retries, tangent rebootstrap, phase refresh triggers, process interruption/resume edge cases, stale checkpoint rejection, cap/tripwire status recording, and fixed-mesh regression safety.
6. Compare native diagnostics against TASK-067 Python fixture intermediates where fixtures exist; otherwise record not_evaluated or fixture_missing explicitly.
7. Regenerate/check affected artifacts and update documentation with failure-policy coverage and remaining deferred evidence.
<!-- SECTION:PLAN:END -->
