---
id: TASK-081
title: Resolve native adaptive pilot acceptance gate blockers
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 16:16'
updated_date: '2026-08-25 11:25'
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
- [x] #1 Exact native restart-vector independent defect and period/orbit convergence gates are backend-bound for post-remesh and accepted pilot targets
- [x] #2 A revised measured pilot over the 210--226 K skeleton records exactly one backend-emitted terminal status per target without interpolation or evidence relabeling
- [x] #3 Any accepted pilot target has same-coordinate independent Python validation and justified IVP validation, or is downgraded to an explicit unresolved/gap record with a blocking reason
- [x] #4 The follow-up review explicitly states whether TASK-075 may proceed under the retained v1 method or requires a method-version revision
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the TASK-081 input set and baseline checks: TASK-073 review/doc, TASK-072 measured pilot/events/run metadata, TASK-071 resource profile, TASK-070 production schema, native one-branch remesh/restart artifacts/vectors, adaptive fixtures, Python-validation evidence, current native executable identity, and existing validation commands.
2. Add a TASK-081 exact restart-gate generator/artifact rather than relabeling TASK-072 by hand. The generator will bind the exact post-remesh native restart vector and mesh, invoke the native C++ backend seams for independent defect diagnostics, record period/orbit convergence evidence for that exact vector, and report each required gate as passed/failed/not_evaluated with source hashes and vector fingerprints.
3. Build a revised measured-pilot gate artifact for the full 210--226 K skeleton. It will preserve exactly one backend-emitted terminal status per target, accept only targets whose exact native gate bundle passes, and downgrade every unsupported target to `resolution_unresolved` with a blocking reason; it will not use interpolation, fixed-mesh relabeling, Python-only substitution, or digitized-paper evidence.
4. Apply independent validation policy to any accepted revised-pilot target: same-coordinate Python correction must pass, and a stratified IVP decision must either run the justified DOP853/Radau check or explicitly downgrade the target to an unresolved/gap record. If there are no accepted points after exact gate binding, record why no IVP subset is justified.
5. Add a TASK-081 follow-up review artifact and documentation that compares TASK-072/TASK-073 with the revised pilot, summarizes accepted/unresolved/failed/near-Hopf/tripwire counts, explains any blocker or method-version revision trigger, and explicitly states whether TASK-075 may proceed under retained `external-gauss3-hr-adaptive-v1`.
6. Update Episode 008 README/decision docs and production-v1 companion artifacts as needed, with validation commands and artifact links. Keep TASK-072/TASK-073 historical artifacts truthful; TASK-081 artifacts supersede them only as the follow-up gate decision.
7. Add focused tests for exact restart-vector gate binding, revised terminal-ledger uniqueness, no relabeling/interpolation, accepted-point Python/IVP policy, TASK-075 go/no-go decision, schema/provenance freshness, and documentation links. Run focused checks, production validators, existing TASK-071/072/073 checks, full pytest as feasible, and git diff --check before closing.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-081: assigned to @iross, verified required tools/native executable are present, and baseline TASK-072/TASK-073 check commands pass. Prepared implementation plan; pausing before code/artifact changes pending plan confirmation.

Plan approved by user; proceeding with TASK-081 generator/artifact/tests/docs implementation.

Implemented TASK-081 follow-up gate artifacts and documentation. Added `generate_native_adaptive_pilot_gate_followup.py`, production-v1 events/run metadata, exact native restart fixture, docs, and focused tests. The exact `spine-210K` restart vector is now bound to native `adaptive-restart` and exact-fixture `adaptive-controller` evidence; same-coordinate Python correction and DOP853 one-period IVP validation pass. Revised pilot ledger: accepted=1 (`spine-210K`), resolution_unresolved=30, failed=0, near_hopf_stop=0, tripwire_stop=0. TASK-075 is authorized under retained `external-gauss3-hr-adaptive-v1` while remaining pilot targets stay explicit gaps.

Regenerated source-hash-dependent TASK-071, TASK-072, TASK-073, TASK-074, and final reconciliation artifacts after documentation/provenance changes. Validation: focused TASK-081 checks and production validators passed; focused Episode 008 regression set passed (49 passed); full `uv run pytest -q` passed (363 passed, 1 skipped, 3 known overflow warnings); `git diff --check` passed. Two read-only subagent reviews initially found backend-binding wording/status-source concerns; after adding live native `adaptive-restart` binding and explicit TASK-081 gate-backend status source, follow-up reviews reported no blockers.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the TASK-081 native adaptive pilot acceptance-gate follow-up.

Changes:
- Added `scripts/generate_native_adaptive_pilot_gate_followup.py` and curated TASK-081 artifacts: follow-up summary, production-v1 continuation events/run metadata, and an exact C++ fixture for the post-remesh `spine-210K` native restart vector.
- Bound the exact restart vector to native backend evidence: `adaptive-restart` emits the matching corrected vector and restart gates; `adaptive-controller` on the exact restart fixture emits the independent defect diagnostic. Period/orbit convergence is recorded from native restart correction/transfer evidence.
- Added same-coordinate Python correction and DOP853 one-period IVP validation for the accepted `spine-210K` point.
- Revised the 210--226 K pilot gate ledger to `accepted=1`, `resolution_unresolved=30`, `failed=0`, `near_hopf_stop=0`, `tripwire_stop=0`; remaining targets stay explicit gaps without interpolation or evidence relabeling.
- Documented that TASK-075 may proceed under retained `external-gauss3-hr-adaptive-v1` with the same gap/tripwire/Hopf boundary discipline.
- Added focused tests and updated Episode 008 README/decision docs. Regenerated source-hash-dependent Episode 008 artifacts after documentation changes.

Validation:
- TASK-081 check and production-v1 validation passed.
- Focused Episode 008 regression set: 49 passed.
- Full suite: `uv run pytest -q` -> 363 passed, 1 skipped, 3 known overflow warnings.
- `git diff --check` passed.
- Follow-up read-only implementation and numerical/scientific reviews reported no blockers.
<!-- SECTION:FINAL_SUMMARY:END -->
