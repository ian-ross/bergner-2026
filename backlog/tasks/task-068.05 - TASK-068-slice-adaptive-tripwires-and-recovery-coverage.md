---
id: TASK-068.05
title: 'TASK-068 slice: adaptive tripwires and recovery coverage'
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 10:52'
updated_date: '2026-08-24 12:40'
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
- [x] #1 Synthetic or branch-smoke tests cover failed transfer/correction, pure-r restart, h+r retry escalation, tangent-only deterministic rebootstrap, phase refresh triggers, process interruption/resume, and stale checkpoint rejection
- [x] #2 Native adaptive diagnostics record cap escalations, aliasing, defect/convergence/ringing/nonphysical-value Radau triggers, single-valued tripwires, and rejection reasons without suppressing failed or unresolved points
- [x] #3 Near-Hopf diagnostics and single-valued tripwires match the documented Python/reference policy where fixtures exist, and otherwise record not_evaluated or explicit reasons
- [x] #4 Broader IVP-based and all Floquet-dependent evidence remain explicitly not_evaluated through TASK-068
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reviewed TASK-068.05 scope against current Episode 008 adaptive artifacts and tests. Existing coverage already handles core h/r transfer/restart smoke, one-branch remesh, provisional scripted spine/slices resumability, and TASK-067 adaptive Radau/aliasing records; remaining gap is explicit native-driver failure-policy diagnostic normalization plus synthetic edge-case coverage for failed restarts/tripwires/cap/reason preservation.

- Implemented TASK-068.05 native-driver diagnostic normalization: cap_escalations, aliasing_events, Radau trigger channels, single-valued tripwire status, rejection reasons, failed/unresolved evidence preservation, and TASK-068 not_evaluated IVP/Floquet boundaries now appear on every driver segment/checkpoint.
- Added synthetic edge-case tests for failed h+r restart/correction reasons, pure-r retry order, cap escalation, phase refresh triggers, single-valued tripwire triggers/observed/not_evaluated paths, plus existing tangent-only rebootstrap, interruption/resume, stale checkpoint, restart-smoke, one-branch, and fixed-mesh regression coverage.
- Extended native adaptive manifest and provisional spine/slices summary with TASK-068.05 failure-policy ledgers; regenerated affected outputs and downstream Python-validation summary after source/provenance hash changes.
- Verification: native adaptive manifest/spine-slices/Python-validation --check; uv run pytest tests/test_episode8_native_adaptive_python_validation.py tests/test_episode8_native_adaptive_driver.py tests/test_episode8_native_adaptive_loca_manifest.py tests/test_episode8_native_adaptive_spine_slices_run.py tests/test_episode8_adaptive_collocation.py -q; uv run pytest -q (314 passed, 1 skipped, 3 warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed TASK-068.05 adaptive tripwire and recovery coverage.

Changes:
- Added native adaptive driver diagnostic normalization for cap escalations, aliasing events, Radau trigger channels, single-valued tripwires, rejection reasons, failed/unresolved evidence preservation, and TASK-068 IVP/Floquet not_evaluated boundaries.
- Implemented/exported the documented single-valued tripwire policy for tangent-sign changes, normalized-coordinate reversals, and incompatible duplicate coordinates.
- Added focused synthetic tests for failed h+r restart/correction, pure-r retry order, cap/alias/Radau/tripwire diagnostics, phase refresh trigger preservation, and no-remesh regression, complementing existing tangent-only rebootstrap, interruption/resume, stale checkpoint, restart-smoke, and one-branch coverage.
- Extended the native adaptive manifest and provisional spine/slices summary with TASK-068.05 failure-policy ledgers and regenerated downstream validation/provenance artifacts.
- Updated Episode 008 README coverage notes.

Tests:
- uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check
- uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_spine_slices_run.py --check
- uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_python_validation.py --check
- uv run pytest tests/test_episode8_native_adaptive_python_validation.py tests/test_episode8_native_adaptive_driver.py tests/test_episode8_native_adaptive_loca_manifest.py tests/test_episode8_native_adaptive_spine_slices_run.py tests/test_episode8_adaptive_collocation.py -q
- uv run pytest -q (314 passed, 1 skipped, 3 warnings)
<!-- SECTION:FINAL_SUMMARY:END -->
