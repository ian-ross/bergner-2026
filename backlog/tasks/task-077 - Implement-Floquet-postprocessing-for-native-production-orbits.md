---
id: TASK-077
title: Implement Floquet postprocessing for native production orbits
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 12:20'
labels:
  - episode-008
  - floquet
  - validation
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Compute Floquet multiplier diagnostics from saved native collocation orbits as postprocessing, not as nonlinear unknowns or TASK-068 acceptance evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 DOP853 variational integration over native piecewise collocation polynomials records trivial and nontrivial multipliers, tolerance-refinement comparisons, stability classifications, and provenance for schema-valid accepted production points
- [ ] #2 Implicit Radau comparisons are run at stratified difficult points and suspected unit-circle crossings, with ambiguous or unstable classifications recorded rather than suppressed
- [ ] #3 Floquet diagnostics link to continuation records and do not relabel failed/unresolved targets or Hopf-limit equilibrium records as regular orbits
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify the TASK-070/TASK-075 dependency boundary before implementing: run the existing full-domain generation/check and production-schema validators, then freeze the accepted-point/orbit inputs so Floquet work only processes schema-valid accepted native production orbits and treats unresolved/failed/Hopf-limit records as non-orbits.
2. Inspect the curated orbit NPZ/manifest, continuation-point/event records, and model/collocation utilities; implement or reuse helpers to evaluate the native piecewise Gauss collocation polynomial and the Bergner-Spichtinger variational RHS in the recorded state/phase/period conventions.
3. Add a TASK-077 Floquet postprocessing generator under Episode 008 that integrates the augmented state-transition system over each accepted orbit with a DOP853 tolerance ladder, records monodromy matrices, trivial and nontrivial multipliers, tolerance-refinement deltas, stability/ambiguity classifications, continuation-record links, and complete provenance without making multipliers nonlinear unknowns or acceptance gates.
4. Add implicit Radau comparison handling for stratified difficult points and suspected unit-circle crossings. With the current production ledger, select the canonical accepted point and explicitly record when near-Hopf/crossing strata are unavailable; preserve ambiguous or unstable classifications rather than filtering them out.
5. Add focused pytest coverage and documentation: verify accepted-only processing, continuation/orbit-manifest linkage, unresolved/Hopf-limit non-relabeling, DOP853/Radau diagnostic fields, classification behavior near unit-circle tolerances, schema/provenance checks, and regenerated README/source-hash-dependent artifacts as needed.
6. Run the TASK-077 generator in write and --check modes, production validators for upstream artifacts, focused tests, the relevant Episode 008 regression subset, full pytest as feasible, and git diff --check; then update TASK-077 acceptance criteria, implementation notes, final summary, and status through the Backlog CLI.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-077: moved task to In Progress, assigned to @iross, reviewed dependencies TASK-069/TASK-070/TASK-075 and Episode 008 documentation/artifacts. No implementation changes have been made yet; pausing for plan confirmation.
<!-- SECTION:NOTES:END -->
