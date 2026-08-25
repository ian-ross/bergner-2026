---
id: TASK-078
title: Run stratified independent IVP validation for production points
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 12:46'
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
- [ ] #1 At least the documented twelve unique validation categories are selected after deduplication, including qualification points, T=210 K Hopf sides where available, low/high-temperature interiors, largest/shortest periods, worst accepted defect, worst Floquet trivial multiplier, and worst interpolation holdout
- [ ] #2 Every selected point receives DOP853 one-period return and phase-aligned trajectory validation with period, return, and weighted-orbit errors below the documented gates or explicit failure reasons
- [ ] #3 The six hardest/headline points receive IVP Radau agreement checks and at least four receive perturbed-equilibrium attractor checks as documented
- [ ] #4 Validation outcomes remain independent evidence and cannot tune or overwrite native continuation periods
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
<!-- SECTION:NOTES:END -->
