---
id: TASK-068.03
title: 'TASK-068 slice: provisional spine-and-slices native adaptive run'
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-24 10:52'
updated_date: '2026-08-24 11:36'
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
Execute the planned provisional native adaptive spine-and-slices continuation using the generalized driver, preserving truthful terminal statuses and run evidence rather than assuming production Figure 5 success.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run manifest covers the T=225 K move to the spine, both temperature directions over the provisional spine range, and signed rho slices for every target on the 2 K skeleton while retaining exact T=210 K and T=225 K anchors
- [ ] #2 Every target has exactly one terminal status: accepted, resolution_unresolved, near_hopf_stop, tripwire_stop, or failed with a reason
- [ ] #3 Accepted segment points and remesh restarts pass independent residual, phase, positivity, linear, finite-change, and restart gates; unresolved/rejected/capped/tripwire outcomes are recorded rather than suppressed
- [ ] #4 Near-Hopf approach evidence records amplitude, period, coordinates, diagnostics, and terminal statuses when reached, targeting at least five reliable points where reachable while deferring fit/connection policy to TASK-069
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the executable/configuration and planned target manifest for the provisional native adaptive run: T=225 K move to the spine, both temperature directions over the provisional spine range, and signed rho slices for every 2 K skeleton target with exact T=210 K and T=225 K anchors.
2. Run the generalized native adaptive driver from the validated anchors and record every segment, remesh/restart, accepted/rejected LOCA event, checkpoint, defect/controller decision, phase refresh, and terminal target status.
3. Enforce independent gates at each accepted point and remesh restart: residual, phase, positivity, finite-change, KLU2/linear diagnostics, tangent/restart validity, mesh/cycle budget, and tripwire checks.
4. Preserve all non-accepted outcomes truthfully as resolution_unresolved, near_hopf_stop, tripwire_stop, or failed with explicit reasons. Do not interpolate missing targets or relabel Python/fixed-mesh evidence as native adaptive completion.
5. Near Hopf, record approach coordinates, amplitude, period, diagnostics, mesh state, and terminal reasons, targeting at least five reliable points where reachable while leaving fit/connection policy to TASK-069.
6. Emit curated run artifacts and vectors with deterministic manifests, source/build/runtime/resource provenance, and resumable completion state.
7. Run generator --check, resume/check commands, focused driver tests, and full relevant test suites. Update Episode 008 documentation with observed coverage, failures, cost, and scope boundaries.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-068.03: moved to In Progress and assigned @pi.
- Reviewed parent TASK-068, completed TASK-068.02 driver/resumability slice, and Episode 008 README/native adaptive context. No implementation changes started yet; awaiting plan confirmation.
<!-- SECTION:NOTES:END -->
