---
id: TASK-064
title: Qualify Python higher-order fixed-mesh periodic orbits
status: Done
assignee:
  - '@iross'
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 17:34'
labels:
  - episode-008
  - python
  - numerics
  - collocation
dependencies:
  - TASK-062
references:
  - src/bergner_spichtinger_2026/periodic_orbits.py
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generalize the Python periodic-orbit reference from one-stage midpoint to explicit two- and three-stage Gauss--Legendre collocation, then execute the TASK-062 fixed-mesh qualification ladder at the canonical and three T=210 K guard points. This task establishes higher-order layout/residual/Jacobian/transfer behavior and numerical evidence before native migration; it does not implement adaptive remeshing or production Figure 5 sampling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reusable Python layout, residual, analytic sparse Jacobian, phase condition, and collocation-polynomial evaluator support one-, two-, and three-stage Gauss rules on uniform fixed meshes without midpoint-specific assumptions
- [x] #2 The canonical T=225 K, w=0.1 m/s ladder runs midpoint N=64/128/256, two-stage Gauss N=32/64/128, and three-stage Gauss N=16/32/64; failed coarse cases are retained with rejection diagnostics
- [x] #3 The T=210 K rho=0 and rho=+/-0.15 guard points run two-stage N=64/128 and three-stage N=32/64 from reproducible TASK-061-derived seeds
- [x] #4 Curated artifacts report component residual gates, period and phase-aligned weighted-orbit refinement, two-grid independent defects, solver provenance, and the versioned qualification decisions at every case, and emit a versioned language-neutral parity-fixture bundle for converged and nonsolution two-/three-stage cases containing packed vectors, meshes, phase references, expected residual blocks, schemas, and checksums
- [x] #5 Every same-rule pair of consecutive accepted ladder solutions is compared against the TASK-062 1e-3 period/orbit checks; every rejected or missing pair has an explicit terminal reason; the canonical accepted best higher-order result is compared with an independent IVP to 1e-3; every miss is preserved as evidence rather than tuned away
- [x] #6 Focused tests cover pack/unpack, residual/Jacobian directional checks, coefficient use, collocation transfer/evaluation, defect grids, parity-fixture schemas and deterministic regeneration, and existing midpoint compatibility
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Start from the frozen TASK-054 coefficient tables and TASK-056/TASK-061 orbit artifacts. Record the current midpoint regression baseline, verify SciPy/NumPy tooling, and define versioned higher-order formulation, qualification, defect, and artifact constants before changing reusable code.
2. Generalize the reusable Python orbit layout and assembler from one explicit midpoint stage to r explicit Gauss stages. Preserve the 3N(r+1)+1 square fixed-parameter system, cyclic endpoint updates, log-period coordinate, quadrature-normalized phase row, analytic sparse Jacobian, normalized rho/T-hat columns, and existing midpoint API/fixtures.
3. Implement rule-driven collocation-polynomial evaluation and fixed-mesh transfer for endpoints, stages, phase references, and comparison vectors. Add phase-independent weighted comparisons whose endpoint/stage normalization remains discretization-independent across stage counts and mesh sizes.
4. Implement the independent two-grid defect evaluator required by TASK-062: next-higher Gauss checks plus staggered dyadic checks, component-scaled relative defects, endpoint/jump diagnostics, material-disagreement detection, 16-point probe escalation, and deterministic 128-bin recurrence metadata. Keep defect acceptance independent of solver residuals.
5. Build reproducible initial guesses for the canonical T=225 K, w=0.1 m/s point and the T=210 K rho=0,+/-0.15 guards by transferring the frozen midpoint/TASK-061-derived orbits to each requested rule and mesh, with fixed phase references and explicit seed provenance.
6. Execute the complete fixed-mesh ladder. Retain every accepted and rejected case with solver termination, block residual gates, phase energy, period, weighted orbit comparisons, defect diagnostics, and explicit terminal reasons. Compare every consecutive accepted same-rule pair; run the canonical best accepted higher-order orbit against independent DOP853 to the versioned 1e-3 contract.
7. Emit deterministic curated JSON/NPZ qualification artifacts and a language-neutral parity-fixture bundle for accepted converged and deliberately nonsolution two-/three-stage cases. Include packed vectors, meshes, phase references, residual blocks, array schemas, units/orderings, coefficient/upstream checksums, runtime provenance, and --check regeneration.
8. Add focused tests for generic pack/unpack and dimensions, one-/two-/three-stage coefficient use, residual/Jacobian directional checks, phase rows, polynomial evaluation/transfer, both defect grids and escalation, comparison metrics, fixture schemas/checksums, rejected-case preservation, deterministic regeneration, and exact midpoint compatibility.
9. Update Episode 008 documentation with observed qualification evidence and any active non-Floquet Radau trigger. Run focused and full Python validation, py_compile, artifact --check, diff checks, self-review, and independent numerical/test review before completing the task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Resumed TASK-064. Confirmed it is already In Progress and assigned to @iross; TASK-062 is complete. Reviewed the Episode 008 README, the full higher-order fixed-mesh qualification contract in collocation-phase-decisions.md, and the current midpoint-specific periodic_orbits.py implementation. Existing implementation plan remains aligned with the task and is awaiting user approval before code changes.

- Implemented rule-driven one-/two-/three-stage Gauss fixed-mesh assembly, analytic CSR Jacobian, phase condition, collocation-polynomial evaluation/derivatives, mesh/rule/reference transfer, phase-aligned comparisons, and independent two-grid defect diagnostics while preserving midpoint wrappers and frozen numerical behavior.
- Added and ran the complete canonical and T=210 K guard ladders from frozen Episode 007 and exact TASK-061-derived seeds. Retained canonical three-stage N=16 as a rejected nonlinear solve; 20 of 21 cases passed nonlinear residual gates.
- Emitted deterministic qualification JSON/NPZ and four language-neutral two-/three-stage converged/nonsolution fixtures with full model/environment/rule/schema/checksum contracts and truthful source provenance.
- Numerical evidence: canonical three-stage N=64 period is 2461.6174737825213 s. Independently derived DOP853 period is 2461.617091943471 s (relative difference 1.551e-7), weighted return error 1.481e-6, and phase-aligned dense-orbit error 2.389e-5. No fixed-uniform case is scientifically qualified: every prescribed refinement pair and independent defect misses its discretization gate.
- Review fixes separated nonlinear acceptance from scientific qualification, added cross-order evidence, corrected admitted-probe argmax semantics, serialized local defect arrays, strengthened exact guard lineage and fixture residual reconstruction, and replaced misleading historical hashes with current verified provenance. Fresh numerical follow-up found no remaining issues; final artifact blockers were resolved.
- Validation: focused suite 83 passed; full suite 208 passed, 1 skipped; higher-order, midpoint, continuation, Tpetra, and native-LOCA artifact checks passed (native check used the cached TASK-061 executable); py_compile and git diff --check passed. LSP reports only environment-level unresolved SciPy imports outside the uv environment.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and qualified the Python higher-order fixed-mesh periodic-orbit reference for Episode 008.

Changes:
- Generalized the reusable collocation system to frozen one-, two-, and three-stage Gauss--Legendre rules with analytic sparse Jacobians, normalized phase rows, polynomial evaluation, transfer, phase alignment, and independent two-grid defect diagnostics.
- Preserved the existing midpoint APIs and numerical compatibility while updating provenance to truthful current-source hashes.
- Ran the complete canonical and T=210 K guard ladders from reproducible frozen seeds, retaining the rejected canonical three-stage N=16 solve and all failed discretization decisions.
- Added deterministic qualification JSON/NPZ artifacts and language-neutral converged/nonsolution parity fixtures with model, environment, units, ordering, shape, tolerance, coefficient, lineage, and checksum contracts.
- Added focused algebra, transfer, defect, qualification, provenance, fixture, and compatibility tests; documented the observed evidence and Radau/Floquet status.

Scientific outcome:
- Best canonical fixed-mesh result: three-stage N=64, P=2461.6174737825213 s.
- Independent DOP853: P=2461.617091943471 s, relative period difference 1.551e-7, weighted return error 1.481e-6, and phase-aligned dense-orbit error 2.389e-5.
- No prescribed fixed-uniform case meets all refinement and defect qualification gates, so adaptive remeshing remains required.

Validation:
- 83 focused tests passed.
- Full suite: 208 passed, 1 skipped.
- All relevant artifact --check commands, py_compile, git diff --check, and independent numerical review passed.
<!-- SECTION:FINAL_SUMMARY:END -->
