---
id: TASK-064
title: Qualify Python higher-order fixed-mesh periodic orbits
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 16:11'
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
- [ ] #1 Reusable Python layout, residual, analytic sparse Jacobian, phase condition, and collocation-polynomial evaluator support one-, two-, and three-stage Gauss rules on uniform fixed meshes without midpoint-specific assumptions
- [ ] #2 The canonical T=225 K, w=0.1 m/s ladder runs midpoint N=64/128/256, two-stage Gauss N=32/64/128, and three-stage Gauss N=16/32/64; failed coarse cases are retained with rejection diagnostics
- [ ] #3 The T=210 K rho=0 and rho=+/-0.15 guard points run two-stage N=64/128 and three-stage N=32/64 from reproducible TASK-061-derived seeds
- [ ] #4 Curated artifacts report component residual gates, period and phase-aligned weighted-orbit refinement, two-grid independent defects, solver provenance, and the versioned qualification decisions at every case, and emit a versioned language-neutral parity-fixture bundle for converged and nonsolution two-/three-stage cases containing packed vectors, meshes, phase references, expected residual blocks, schemas, and checksums
- [ ] #5 Every same-rule pair of consecutive accepted ladder solutions is compared against the TASK-062 1e-3 period/orbit checks; every rejected or missing pair has an explicit terminal reason; the canonical accepted best higher-order result is compared with an independent IVP to 1e-3; every miss is preserved as evidence rather than tuned away
- [ ] #6 Focused tests cover pack/unpack, residual/Jacobian directional checks, coefficient use, collocation transfer/evaluation, defect grids, parity-fixture schemas and deterministic regeneration, and existing midpoint compatibility
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
