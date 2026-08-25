---
id: TASK-075
title: Execute full-domain native adaptive continuation and sampling refinement
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 11:57'
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
- [x] #1 The run covers the approved T=190--240 K domain, exact 225 K anchor, spine points, rho anchors, and any additional solves required by accepted pilot/full-domain evidence, with one terminal status per requested target
- [x] #2 Accepted points pass production residual, phase, positivity, linear, defect, period/orbit convergence, remesh/restart, and provenance gates; unresolved or failed regions remain explicit gaps
- [x] #3 Holdout-driven sampling refinement records along-slice and between-slice log-period errors and adds authoritative solves near failures without crossing Hopf boundaries, tripwires, instability checkpoints, or unresolved gaps
- [x] #4 Curated scalar/event/checkpoint/orbit artifacts are schema-valid, restartable, measured, and linked from Episode 008 documentation
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

Resumed TASK-075 after TASK-081 reached Done. Dependency gate is now satisfied: TASK-069/070/071/073/081 are Done, and TASK-081 explicitly authorizes TASK-075 under retained external-gauss3-hr-adaptive-v1 with explicit-gap/tripwire/Hopf-boundary discipline. Pausing before production continuation/artifact changes pending plan confirmation.

Implemented TASK-075 full-domain native adaptive artifacts. Added generator, production-v1 continuation points/events/run metadata/orbit manifest, curated accepted-orbit NPZ, TASK-075 documentation, README links, and focused tests. The full-domain ledger requests 298 targets over T=190--240 K with exact 225 K anchor lineage, spine/rho anchors, and refinement-neighborhood targets; current production gates accept only spine-210K and leave 297 targets as explicit resolution_unresolved gaps. Regenerated README/source-hash-dependent TASK-071, TASK-073, TASK-081, TASK-075, and final reconciliation artifacts after documentation changes.

Read-only scientific audit found an initial overclaim that all unresolved full-domain statuses were native-backend emitted. Fixed by updating TASK-075 truthfulness fields and TASK-081 authorization wording/docs: only accepted statuses claim native backend emission, while unresolved full-domain targets are recorded as explicit policy gaps when no authorized route exists without crossing unresolved regions. Regenerated TASK-071/TASK-072/TASK-073/TASK-081/TASK-075/TASK-074/final source-hash-dependent artifacts. Validation now passes: focused TASK-075 checks, production validators, focused Episode 008 regression set, full uv run pytest -q (370 passed, 1 skipped, 3 known warnings), and git diff --check.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the TASK-075 full-domain native adaptive continuation and sampling-refinement artifact layer under the TASK-081 authorization.

Changes:
- Added `scripts/generate_native_adaptive_full_domain_run.py` with check mode for the full Figure 5 target skeleton (`T=190,192,...,240 K` plus exact 225 K; rho anchors `0, +/-0.25, +/-0.50, +/-0.75, +/-0.90, +/-0.97`; accepted-evidence refinement-neighborhood targets).
- Added production-v1 artifacts: full-domain summary, continuation points, terminal events, run metadata, curated orbit NPZ manifest, and restartable accepted-orbit NPZ.
- Accepted only the TASK-081-backed exact `spine-210K` native post-remesh restart vector; the other 297 requested targets remain explicit `resolution_unresolved` policy gaps with no interpolation, fixed-mesh relabeling, Python substitution, or digitized-paper acceptance.
- Recorded holdout-driven sampling refinement on accepted data only; with one accepted point, along-slice and between-slice log-period errors are `not_evaluated` and interpolation is withheld across gaps/Hopf/tripwire/instability boundaries.
- Added focused tests and TASK-075 documentation, updated Episode 008 README links, and clarified TASK-081 authorization wording to distinguish native-backend accepted statuses from explicit policy-gap records.
- Regenerated source-hash-dependent Episode 008 artifacts after documentation/provenance changes.

Validation:
- TASK-075 check command and production-v1 validators passed.
- Focused Episode 008 regression set passed.
- Full suite: `uv run pytest -q` -> 370 passed, 1 skipped, 3 known overflow warnings.
- `git diff --check` passed.
- Read-only implementation audit reported no blockers after the explicit-gap wording fix.
<!-- SECTION:FINAL_SUMMARY:END -->
