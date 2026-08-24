---
id: TASK-073
title: Reconcile native adaptive pilot with independent validation
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 16:37'
labels:
  - episode-008
  - validation
  - review
dependencies:
  - TASK-069
  - TASK-070
  - TASK-072
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review the measured 210--226 K native adaptive pilot and validate accepted backend points independently before authorizing full-domain production. This task is a gate between pilot execution and broader Figure 5 continuation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every accepted pilot point, including post-remesh points, receives independent same-coordinate Python correction or an explicit validation-unavailable reason that blocks production use
- [x] #2 A stratified subset receives independent IVP one-period validation where justified by TASK-069, with DOP853 and Radau used according to documented difficulty triggers
- [x] #3 The pilot review decides whether full-domain continuation can proceed under the retained v1 method or whether a documented method-version revision/follow-up is required
- [x] #4 Documentation records accepted, unresolved, failed, near-Hopf, and tripwire outcomes without changing terminal statuses through interpolation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze TASK-073 inputs: TASK-069 decisions, TASK-070 production-v1 contract, TASK-072 measured pilot summary/events/run metadata/manifest, existing TASK-068 Python-validation and IVP evidence, and current Episode 008 documentation. Run the available check commands first so the review is based on current artifacts.
2. Add a reproducible TASK-073 reconciliation/review artifact generator under `episodes/008-figure5-periodic-orbit-continuation/scripts/` that reads the pilot ledger and emits a versioned review JSON recording status counts, accepted-point validation coverage, post-remesh evidence handling, IVP-validation applicability, near-Hopf/tripwire/failed/unresolved outcomes, and the production-go/no-go decision.
3. Encode truthfulness rules in the generator/tests: every pilot target has exactly one unchanged terminal status; accepted points require independent same-coordinate Python validation or an explicit validation-unavailable blocker; because TASK-072 currently has zero accepted pilot points, all 31 targets and the measured remesh/restart seam should remain explicit non-authoritative unresolved/gap evidence rather than being promoted by interpolation, fixed-mesh, Python-only, or digitized-paper evidence.
4. Implement the TASK-069 IVP/Radau decision logic for this pilot review: select no IVP subset when there are no accepted native adaptive pilot points, record DOP853/Radau triggers as not applicable/not justified, and preserve blocker reasons for any future accepted point lacking required validation.
5. Document the review in `docs/task073-native-adaptive-pilot-reconciliation.md` and update the Episode 008 README/decision records with the accepted/unresolved/failed/near-Hopf/tripwire ledger, explicit no-interpolation policy, and whether full-domain continuation may proceed or is blocked pending retained-v1 evidence completion or a method-version follow-up.
6. Add focused pytest coverage for the TASK-073 artifact, documentation links, zero-accepted validation semantics, IVP non-selection semantics, terminal-status preservation, production-go/no-go decision, and stale-artifact check mode; run focused tests, relevant TASK-072/TASK-070 checks, full pytest as feasible, and `git diff --check`.
7. If the documented review concludes a method-version revision or follow-up is required before TASK-075, create that follow-up through Backlog CLI only; then update TASK-073 notes, acceptance criteria, final summary, and status through Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-073: moved task to In Progress, assigned to @iross, reviewed TASK-069/TASK-070/TASK-072 dependency outputs and Episode 008 docs, and added an implementation plan. Pausing before code/artifact changes pending plan confirmation.

Plan approved by user. Initial input checks passed:
- TASK-072 measured pilot generator --check
- TASK-072 production-v1 events/run-metadata validation

Implemented TASK-073 reconciliation artifacts and gate decision. Added `generate_native_adaptive_pilot_reconciliation.py`, `outputs/native_adaptive_pilot_reconciliation.json`, `docs/task073-native-adaptive-pilot-reconciliation.md`, README/decision-record updates, and focused tests.

Outcome: TASK-072 terminal statuses are preserved exactly (`accepted=0`, `resolution_unresolved=31`, `failed=0`, `near_hopf_stop=0`, `tripwire_stop=0`). No IVP subset is selected because no accepted native adaptive pilot point exists; DOP853/Radau triggers are recorded for future accepted points. Full-domain continuation is not authorized; retained v1 is not falsified, no method-version revision is required now, and TASK-081 was created as the required follow-up gate before TASK-075. TASK-075 dependencies were updated to include TASK-081.

Regeneration note: after documentation/source-provenance changes, rebuilt `loca-build/bs2026_midpoint_orbit`, added `loca-build/` to `.gitignore`, and regenerated affected TASK-071/TASK-072/TASK-068 sink artifacts with stable `loca-build/bs2026_midpoint_orbit` provenance.

Validation run:
- TASK-071/TASK-072/TASK-073/final-reconciliation check commands passed with `BS2026_MIDPOINT_EXECUTABLE=loca-build/bs2026_midpoint_orbit` where needed
- TASK-072 production-v1 events/run metadata and TASK-071 run metadata validate
- Focused tests: `uv run pytest tests/test_episode8_native_adaptive_pilot_reconciliation.py tests/test_episode8_native_adaptive_measured_pilot.py tests/test_episode8_native_adaptive_resource_profile.py tests/test_episode8_native_adaptive_one_branch_segment.py tests/test_episode8_native_adaptive_spine_slices_run.py tests/test_episode8_native_adaptive_final_reconciliation.py tests/test_episode8_production_schema.py -q` -> 47 passed
- Full suite: `uv run pytest -q` -> 351 passed, 1 skipped, 3 known overflow warnings
- `git diff --check` passed

Independent read-only reviews: initial review found executable-provenance and TASK-075 dependency blockers; both were fixed. Follow-up read-only review reported no blockers.
<!-- SECTION:NOTES:END -->
