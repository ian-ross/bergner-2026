---
id: TASK-076
title: Acquire near-Hopf approach evidence and decide gap policy
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 12:03'
labels:
  - episode-008
  - hopf
  - analysis
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use production native adaptive continuation results to collect reliable near-Hopf approach evidence where reachable, perform the documented quadratic/quartic period-amplitude review, and decide connection or explicit-gap policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each Hopf side under review has either at least five reliable monotone approach points with amplitude, period, coordinates, diagnostics, and terminal statuses, or a documented reason why the approach remains an explicit gap
- [ ] #2 Quadratic and quartic P(A) fits, leave-one-out intercept checks, residual checks, and comparison with Episode 006 Hopf periods are performed only where the evidence prerequisites are met
- [ ] #3 The resulting connection/gap policy is encoded in schema-valid production records and never invents regular-orbit values at Hopf boundaries
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reconfirm TASK-075 production evidence, schema constraints, and Hopf-limit policy from the full-domain artifacts, TASK-069/TASK-075 docs, and Episode 006 Hopf loci/period artifacts. Define the exact Hopf sides under review from the accepted/unresolved production target ledger rather than from paper/digitized data.
2. Build a reproducible TASK-076 review artifact/script that extracts any reliable near-Hopf approach candidates from production native adaptive records only, including amplitude, period, coordinates, gate diagnostics, monotonicity, provenance, and terminal status for each candidate.
3. Apply the five-point evidence prerequisite side-by-side for each lower/upper Hopf approach side. If a side lacks enough reliable monotone accepted approach points, record an explicit-gap reason with the nearest accepted/unresolved terminal statuses and do not run fits for that side.
4. Where and only where prerequisites are met, run quadratic and quartic P(A) fits, leave-one-out intercept checks, residual checks, and compare intercepts with Episode 006 Hopf periods using documented provenance and units.
5. Encode the resulting connection/gap policy in schema-valid production-v1 records/events with unambiguous validity/source flags, ensuring no regular-orbit period or amplitude is invented at a Hopf boundary.
6. Document the TASK-076 decision and validation commands in Episode 008 docs/README, add focused regression tests for sufficient-evidence gating and no-fit/no-invented-boundary behavior, regenerate/check affected artifacts, and run validators, focused tests, full pytest as feasible, and git diff --check.
7. Update TASK-076 acceptance criteria, implementation notes, final summary, and status through the Backlog CLI only after validation passes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-076: moved task to In Progress, assigned to @pi, reviewed dependencies TASK-069/TASK-070/TASK-075 and Episode 008 production documentation. Current TASK-075 evidence accepts only spine-210K and leaves the rest of the full-domain ledger as explicit resolution_unresolved policy gaps, so the implementation will gate near-Hopf fits strictly on production native adaptive evidence.

Assignee normalized to @iross to match repository Backlog convention and local working identity.
<!-- SECTION:NOTES:END -->
