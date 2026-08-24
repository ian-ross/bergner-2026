---
id: TASK-072
title: Run measured native adaptive pilot on 210-226 K skeleton
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 15:28'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the TASK-068 provisional 31-target skeleton, TASK-070 production-v1 schema boundary, and TASK-071 measured-resource artifacts as inputs. Record/check the exact source, generator, executable/build, manifest, and checkpoint identities before producing any pilot outputs.
2. Build or verify the native executable and current Trilinos/LOCA source fingerprints. If `loca-build/bs2026_midpoint_orbit` is absent or stale, configure/build a Release binary, then run the existing native adaptive prerequisite checks so stale binary or checkpoint reuse fails early.
3. Add a TASK-072 measured pilot generator under `episodes/008-figure5-periodic-orbit-continuation/scripts/` that executes the 210--226 K skeleton through the resumable native adaptive driver with measured wall-clock, CPU, RSS, NOX/KLU2 counters, source/build/runtime identity, and explicit regeneration/check/resume semantics. The pilot must emit backend-produced terminal statuses only: accepted, resolution_unresolved, near_hopf_stop, tripwire_stop, or failed.
4. Replace the TASK-068 provisional pending/fixed-mesh-replay ledger with new TASK-072 pilot artifacts under the Episode 008 outputs directory, while preserving explicit gaps/unresolved records and never filling targets by interpolation or Python/fixed-mesh relabeling.
5. Validate every accepted point and remesh restart against the required gates: residual, phase, positivity, finite-change, tangent, linear-solve, defect, and period/orbit convergence. Preserve detailed rejection/unresolved/near-Hopf/tripwire reasons for every unaccepted target.
6. Add production-v1 companion artifacts and focused tests for exactly-one terminal status across all 31 targets, measured non-placeholder resource fields, source/build/checkpoint identity coverage, stale-checkpoint rejection/check-mode behavior, gate coverage, and explicit no-interpolation/gap policy.
7. Update Episode 008 documentation to link the TASK-072 pilot artifacts and explain accepted/unaccepted target coverage, resource identity, resume/check commands, and how this task gates TASK-073 without claiming final full-domain Figure 5 production.
8. Run the generator/check commands, production artifact validation, focused TASK-072 tests plus relevant TASK-070/TASK-071/native-adaptive checks, `uv run pytest -q` as feasible, and `git diff --check`; then update TASK-072 notes, acceptance criteria, final summary, and status through Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-072: moved task to In Progress and assigned to @iross. Reviewed TASK-069/TASK-070/TASK-071 dependencies, Episode 008 README, TASK-069 review, TASK-071 resource profile, the provisional spine-and-slices generator, and the reusable native adaptive driver. Tool check: backlog, uv, cmake, ninja, /usr/bin/time, and Python are available; no `loca-build/bs2026_midpoint_orbit` binary is currently present, so implementation should begin by building or selecting the native executable.
<!-- SECTION:NOTES:END -->
