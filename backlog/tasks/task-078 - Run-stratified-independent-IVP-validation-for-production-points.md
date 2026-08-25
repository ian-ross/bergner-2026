---
id: TASK-078
title: Run stratified independent IVP validation for production points
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 13:12'
labels:
  - episode-008
  - ivp
  - validation
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
  - TASK-077
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate selected accepted native production periodic orbits with independent IVP integrations after full-domain continuation exposes the actual worst cases.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 At least the documented twelve unique validation categories are selected after deduplication, including qualification points, T=210 K Hopf sides where available, low/high-temperature interiors, largest/shortest periods, worst accepted defect, worst Floquet trivial multiplier, and worst interpolation holdout
- [x] #2 Every selected point receives DOP853 one-period return and phase-aligned trajectory validation with period, return, and weighted-orbit errors below the documented gates or explicit failure reasons
- [x] #3 The six hardest/headline points receive IVP Radau agreement checks and at least four receive perturbed-equilibrium attractor checks as documented
- [x] #4 Validation outcomes remain independent evidence and cannot tune or overwrite native continuation periods
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the TASK-075/TASK-077 production inputs and schema boundary: verify upstream generator --check commands, production-v1 validators, accepted continuation-point/orbit-manifest hashes, Floquet diagnostics, and current explicit-gap ledger before selecting any IVP cases.
2. Define the TASK-078 stratification contract from the task ACs and current evidence: enumerate the twelve documented validation categories, deduplicate selected accepted native production point IDs across categories, and explicitly record unavailable strata when current production evidence has no accepted point (near-Hopf sides, high/low-temperature interiors, worst holdout, etc.) rather than using unresolved, interpolated, qualification-only, Hopf-limit, or digitized-paper records as production orbits.
3. Implement an Episode 008 TASK-078 validation generator/artifact that loads only schema-valid accepted TASK-075 orbits, reconstructs/evaluates the saved native Gauss collocation polynomial, and runs independent one-period DOP853 return plus phase-aligned trajectory checks with documented period, return, weighted-orbit, solver, and provenance gates.
4. Add headline/difficulty checks: select the six hardest/headline available accepted points after deduplication, run Radau agreement where available, record unavailable strata transparently, and run perturbed-equilibrium attractor checks for at least four available headline points or document an explicit production-evidence insufficiency if fewer accepted points exist.
5. Preserve independence boundaries: validation artifacts may read native periods/orbits for comparison targets and checksums, but must not tune, overwrite, re-fit, or relabel continuation periods/statuses; failures must remain validation failures or explicit unavailable/failure reasons.
6. Add focused pytest coverage and documentation for category selection/deduplication, unavailable-stratum truthfulness, DOP853 and phase-aligned trajectory gates, Radau/attractor availability policy, independence/non-overwrite guarantees, source checksums, and README links.
7. Run the TASK-078 generator in write and --check modes, upstream production validators/checks, focused Episode 008 regression tests, full pytest as feasible, and git diff --check; then update TASK-078 notes, acceptance criteria, final summary, and status through Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by user; proceeding with TASK-078 generator, documentation, tests, and validation.

Implemented TASK-078 stratified independent IVP validation. Added generator, artifact, documentation, README links, and focused tests. Current production evidence has one accepted native orbit (`spine-210K`); twelve validation categories are documented and deduplicated to that point where available, while near-Hopf, low/high-temperature, holdout, and additional headline/attractor unique-point strata remain explicit unavailable/insufficient-evidence records rather than being filled from unresolved/interpolated/nonproduction evidence.

Validation run:
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_ivp_validation.py --check`: passed
- production-v1 validators for TASK-075 points/events/orbit manifest: passed
- focused TASK-078 tests: 6 passed
- focused source-hash-dependent Episode 008 regression set: 37 passed
- full `uv run pytest -q`: 388 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented TASK-078 stratified independent IVP validation for accepted native production orbits.

Changes:
- Added `generate_native_adaptive_ivp_validation.py` and `native_adaptive_ivp_validation.json` with twelve documented validation categories, category deduplication, DOP853 one-period return and phase-aligned trajectory checks, Radau agreement checks, perturbed-equilibrium attractor screening, provenance, and explicit independence policy.
- Added `docs/task078-stratified-ivp-validation.md` and Episode 008 README links.
- Added focused tests for category coverage/deduplication, DOP853 gates, Radau and attractor availability policy, independence boundaries, hashes, and documentation.
- Regenerated source-hash-dependent Episode 008 artifacts after the README/doc update.

Current scientific result:
- TASK-075 currently has one accepted native production orbit, `spine-210K`; it passes DOP853 period/return/phase-aligned weighted-orbit gates and Radau agreement.
- Near-Hopf sides, low/high-temperature interiors, worst holdout, and additional headline/attractor unique-point strata remain unavailable or insufficient production evidence; they are not filled from unresolved, interpolated, qualification-only, Hopf-limit, or digitized-paper records.
- IVP outcomes are recorded as independent evidence only and do not tune or overwrite native continuation periods.

Validation:
- TASK-078 check command and TASK-075 production validators passed.
- Focused TASK-078 tests passed: 6 passed.
- Focused source-hash-dependent Episode 008 regression set passed: 37 passed.
- Full suite: `uv run pytest -q` -> 388 passed, 1 skipped, 3 known overflow warnings.
- `git diff --check` passed.
<!-- SECTION:FINAL_SUMMARY:END -->
