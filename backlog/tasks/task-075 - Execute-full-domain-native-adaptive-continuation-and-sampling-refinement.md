---
id: TASK-075
title: Execute full-domain native adaptive continuation and sampling refinement
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 11:26'
labels:
  - episode-008
  - loca
  - adaptivity
  - production
dependencies:
  - TASK-069
  - TASK-070
  - TASK-071
  - TASK-073
  - TASK-081
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After the measured pilot gate passes, run authoritative native adaptive continuation over the Figure 5 temperature/rho domain and refine canonical scientific sampling from observed errors and terminal statuses.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run covers the approved T=190--240 K domain, exact 225 K anchor, spine points, rho anchors, and any additional solves required by accepted pilot/full-domain evidence, with one terminal status per requested target
- [ ] #2 Accepted points pass production residual, phase, positivity, linear, defect, period/orbit convergence, remesh/restart, and provenance gates; unresolved or failed regions remain explicit gaps
- [ ] #3 Holdout-driven sampling refinement records along-slice and between-slice log-period errors and adds authoritative solves near failures without crossing Hopf boundaries, tripwires, instability checkpoints, or unresolved gaps
- [ ] #4 Curated scalar/event/checkpoint/orbit artifacts are schema-valid, restartable, measured, and linked from Episode 008 documentation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Gate dependency check: verify TASK-069/070/071/073/081 outputs and documentation, with TASK-081 required to be Done and to explicitly authorize TASK-075 before any full-domain production continuation or production artifact generation. If the gate is not satisfied, stop and report TASK-075 as blocked rather than filling gaps with provisional/interpolated evidence.
2. Once authorized, freeze the production input set: current Episode 008 schemas, measured resource profile, revised accepted pilot/full-domain gate evidence, executable/source/build/runtime identities, target-domain policy, and validation commands.
3. Define the full-domain requested-target manifest for T=190--240 K, the exact 225 K anchor, spine points, rho anchors, and any additional solves justified by accepted pilot/full-domain evidence; require exactly one backend-emitted terminal status per requested target.
4. Execute or extend the native adaptive continuation driver for authoritative full-domain runs with checkpointing, remesh/restart provenance, measured resource counters, production-v1 scalar/event/run-metadata artifacts, and curated orbit-vector manifests for accepted points only.
5. Apply acceptance gates point-by-point: production residual, phase, positivity, KLU2/linear diagnostics, independent defect, period/orbit convergence, remesh/restart validity, restartability, and provenance/schema checks; leave unresolved/failed/near-Hopf/tripwire regions as explicit gaps.
6. Run holdout-driven sampling refinement on accepted data only: record along-slice and between-slice log-period errors, add authoritative solves near eligible high-error/failure neighborhoods, and do not cross Hopf boundaries, tripwires, instability checkpoints, or unresolved gaps.
7. Update Episode 008 documentation with the terminal ledger, sampling-refinement evidence, gap policy, artifact links, and validation commands; then run schema validators, focused Episode 008 tests/check commands, full pytest as feasible, and git diff --check before closing the task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-075 by assigning it to @iross and reviewing dependencies plus Episode 008 gate documentation. TASK-081 is still To Do, and TASK-073 explicitly states full-domain continuation is not authorized until TASK-081 resolves the pilot acceptance blockers. No full-domain continuation or production artifact generation has been started.

Paused TASK-075 before implementation because TASK-081 gate work must be completed first per TASK-073. User approved switching to TASK-081.
<!-- SECTION:NOTES:END -->
