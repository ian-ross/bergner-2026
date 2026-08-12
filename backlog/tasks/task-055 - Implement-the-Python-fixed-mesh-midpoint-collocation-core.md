---
id: TASK-055
title: Implement the Python fixed-mesh midpoint collocation core
status: Done
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 16:41'
labels:
  - episode-008
  - python
  - numerics
dependencies:
  - TASK-053
  - TASK-054
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the transparent Python reference formulation for fixed-parameter periodic orbits using explicit one-stage Gauss midpoint stages, log-state/log-period coordinates, and the normalized integral phase condition.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 OrbitLayout packs and unpacks endpoint blocks, explicit stage blocks, and log period for arbitrary fixed meshes without a duplicated terminal endpoint
- [x] #2 The assembler evaluates scaled stage equations, cyclic endpoint updates, and the normalized integral phase condition with a frozen phase reference
- [x] #3 The assembler returns an explicit sparse CSR Jacobian including state blocks, log-period column, and phase row
- [x] #4 The N=8 midpoint fixtures cover layout indices, sparsity, residual blocks, phase normalization, and nonsolution vectors deterministically
- [x] #5 Centered finite-difference directional checks satisfy the versioned Jacobian tolerances
- [x] #6 The implementation is reusable package code while Episode 008 orchestration remains episode-local
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add reusable package-level fixed-mesh collocation primitives: a validated OrbitLayout with deterministic endpoint/stage/log-period and residual-row indexing, plus pack/unpack helpers that support arbitrary interval counts and normalized nonuniform meshes without storing a duplicate terminal endpoint.
2. Implement the transformed vector field g=(dn/dt/n,dq/dt/q,ds/dt) and its analytic log-state Jacobian by applying chain and quotient rules to the existing validated physical model/Jacobian, rejecting the unsupported discontinuous evaporation mode.
3. Implement an immutable frozen phase-reference contract and midpoint assembler using the generated one-stage Gauss rule. Assemble component-scaled stage equations, cyclic endpoint updates, and the quadrature-normalized integral phase equation; expose residual block views and phase energy while keeping the reference, scaling, and energy fixed.
4. Assemble the full analytic Jacobian directly as scipy.sparse.csr_matrix, including local endpoint/stage blocks, periodic wraparound, log-period derivatives, and the dense-in-stage phase row. Define explicit method/tolerance version constants for deterministic parity and centered-difference checks.
5. Add deterministic N=8 fixtures and focused tests covering exact layout/index contracts, pack/unpack round trips, arbitrary/nonuniform meshes, CSR shape/pattern/wraparound, independently calculated residual blocks, exact reference-phase normalization, controlled nonsolution vectors, analytic transformed-model derivatives, and centered finite-difference Jv agreement at the versioned <=1e-6 relative tolerance.
6. Export and document the reusable package API while keeping seed loading and fixture/orchestration paths episode-local; run focused tests, the full Python suite, compilation/diff checks, and self-review before updating task notes, acceptance criteria, and final summary.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Plan approved; implementation started.
- Confirmed Python 3.11, NumPy 2.4.6, SciPy 1.17.1, pytest 9.1.1, generated midpoint coefficients, reusable periodic seed interpolation, and the validated physical Jacobian are available.
- The worktree was clean before TASK-055 implementation.

- Added reusable periodic_orbits package primitives: arbitrary fixed normalized meshes, deterministic OrbitLayout indexing/pack-unpack, frozen stage-sampled phase references, transformed vector field/Jacobian, scaled midpoint residual blocks, and an explicitly assembled CSR Jacobian.
- Added deterministic N=8 and nonuniform-mesh tests covering layout indices, no duplicated terminal endpoint, sparsity and cyclic wraparound, independently evaluated stage/update residuals, exact normalized phase displacement, deterministic nonsolution vectors, and state/log-period/mixed centered directional checks. Measured N=8 relative errors were 2.82e-9, 1.51e-9, and 2.75e-9 versus the versioned 1e-6 tolerance.
- Independent review found no mathematical or acceptance blocker. Its one medium finding was addressed by freezing collocation nodes in the phase-reference contract and rejecting one-stage references sampled away from the midpoint; regression coverage was added.
- Final validation: 24 focused Episode 008 tests passed; the full suite passed with 130 passed / 1 pre-existing explicit skip and three known exploratory-solver overflow warnings. Bootstrap/coefficient regeneration checks, py_compile, git diff whitespace checks, package exports, and an N=1 directional smoke check also passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the reusable Python fixed-mesh explicit-stage midpoint collocation core for Episode 008.

Changes:
- Added OrbitLayout and FixedMesh contracts for arbitrary uniform/nonuniform meshes, explicit stages, cyclic endpoints without terminal duplication, and log-period coordinates.
- Added the transformed model field and analytic log-state Jacobian using the validated physical model/Jacobian.
- Added immutable phase-reference sampling with frozen midpoint nodes, quadrature, scaling, phase tangent, and normalized phase energy.
- Added scaled midpoint stage/update residual assembly and a complete analytic SciPy CSR Jacobian with endpoint/stage blocks, periodic wraparound, log-period column, and phase row.
- Exported and documented the reusable package API while leaving Episode 008 seed/fixture orchestration episode-local.
- Added deterministic N=8 and nonuniform fixtures covering indices, pack/unpack, residual blocks, phase normalization, sparse structure, nonsolution vectors, and versioned centered finite-difference checks.

Validation:
- Full Python suite: 130 passed, 1 explicitly skipped; three known warnings remain in pre-existing exploratory solver paths.
- Focused Episode 008 suite: 24 passed.
- Directional Jacobian errors: 2.82e-9 state, 1.51e-9 log-period, 2.75e-9 mixed (tolerance 1e-6).
- Bootstrap/coefficient regeneration, py_compile, whitespace, and N=1 smoke checks passed.
- Independent review found no remaining blocker after midpoint-node compatibility hardening.
<!-- SECTION:FINAL_SUMMARY:END -->
