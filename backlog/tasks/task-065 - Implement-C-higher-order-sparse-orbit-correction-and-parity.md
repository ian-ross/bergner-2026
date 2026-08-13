---
id: TASK-065
title: Implement C++ higher-order sparse orbit correction and parity
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 19:34'
labels:
  - episode-008
  - cpp
  - trilinos
  - nox
  - collocation
dependencies:
  - TASK-064
references:
  - loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp
  - loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generalize the serial sparse Tpetra/Thyra periodic-orbit base system and NOX/KLU2 fixed-parameter corrector from midpoint to two- and three-stage Gauss--Legendre rules. Migrate the frozen Python higher-order fixtures behaviorally while preserving a square base system, retained sparse graphs, local Sacado derivatives, and the established acceptance diagnostics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The one-rank Tpetra layout and retained sparse graph support explicit one-, two-, and three-stage Gauss systems with 3N(r+1)+1 square base dimensions, cyclic updates, log-period column, and one phase row
- [ ] #2 C++ residuals, analytic Jacobian actions, phase rows, log-period columns, and normalized rho/T-hat parameter columns match every upstream accepted converged fixture covered by the language-neutral bundle plus its nonsolution higher-order fixtures within versioned parity tolerances
- [ ] #3 Thyra/NOX with Amesos2 KLU2 corrects at minimum the canonical two-stage N=64 and three-stage N=32 fixtures plus all three T=210 K guard three-stage N=32 fixtures when those upstream fixtures are accepted, and independently enforces residual, phase, positivity, phase-energy, and linear-solve gates; an upstream fixture rejection is propagated explicitly rather than silently excluded
- [ ] #4 For every upstream accepted fixture covered by the parity bundle, corrected periods and phase-aligned weighted orbits match the corresponding Python fixed-mesh solutions within the versioned 1e-8 fixed-mesh parity tolerance
- [ ] #5 Artifacts and CLI output record rule/order, mesh/layout/graph dimensions, coefficient checksum, block diagnostics, KLU2 counters, source/runtime provenance, upstream fixture status, and deterministic fixture regeneration
- [ ] #6 Focused integration tests preserve midpoint behavior and cover higher-order indexing/sparsity, wraparound, retained-graph reuse, finite-difference derivative checks, correction acceptance/rejection, explicit fixture-rejection propagation, and Python/C++ parity
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the TASK-064 migration contract: inventory all accepted/rejected higher-order cases and the current parity bundle; version the generalized C++ formulation, fixture projection, solver diagnostics, and 1e-11/1e-6/1e-8 tolerances while preserving midpoint CLI and API behavior.
2. Extend deterministic Episode 008 fixture generation so C++ can consume the required canonical two-stage N=64, canonical three-stage N=32, all three T=210 K three-stage N=32 guards, the upstream-rejected canonical case, and representative two-/three-stage nonsolutions, with source/runtime/coefficient checksums and explicit upstream status.
3. Generalize the serial OrbitLayout, phase reference, and retained Tpetra graph from one stage to a selected frozen Gauss rule. Own endpoint, interval/stage/component, update, log-period, and phase indices for the square 3N(r+1)+1 system; retain cyclic wraparound and midpoint-compatible entry points.
4. Generalize residual, sparse Jacobian fill, phase energy/row, log-period column, normalized rho/T-hat columns, diagnostics, and positivity checks using generated Gauss tables and local Sacado derivatives only.
5. Generalize the Thyra model and fixed-parameter NOX/Amesos2-KLU2 corrector without adding continuation scope. Preserve independent convergence, residual-block, phase, positivity/finiteness, phase-energy, and actual factorization/solve gates, including stable propagation of upstream fixture rejection.
6. Extend the C++ CLI/artifact seam to report rule/order, mesh and block dimensions, graph reuse/entries, coefficient and source fingerprints, residual/Jacobian/parameter diagnostics, KLU2 counters, correction parity, and upstream status in deterministic output.
7. Add Python-driven integration tests for one-/two-/three-stage indexing and sparsity, wraparound, retained-graph reuse, residual and derivative parity on accepted/nonsolution fixtures, required NOX corrections, rejected-upstream propagation, all acceptance gates, 1e-8 phase-aligned fixed-mesh parity, and unchanged midpoint behavior.
8. Regenerate/check artifacts, update Episode 008 documentation, run clean CMake/Ninja builds plus focused and full applicable pytest suites, compiler/LSP diagnostics, py_compile, diff checks, self-review, and independent correctness/test review; then record evidence and complete the task criteria.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-065, moved it to In Progress, and assigned it to @iross.
- Confirmed TASK-064 is Done and reviewed its accepted/rejected qualification manifest, language-neutral parity bundle, Episode 008 README/design contract, midpoint Tpetra assembler, Thyra/NOX adapter, CLI, CMake target, and focused integration tests.
- Confirmed required tools are available: cmake, ninja, uv, Python, C++, Backlog CLI, and the configured Trilinos installation path used by the tests. No code changes have been made pending plan approval.
- Key migration constraint: the current parity bundle contains canonical g2-N64/g3-N64 accepted and nonsolution JSON cases, while TASK-065 additionally requires canonical g3-N32, three accepted T=210 K g3-N32 guards, and explicit propagation of TASK-064's rejected canonical g3-N16 case; fixture generation must be extended rather than silently narrowing coverage.

- User approved the implementation plan; beginning implementation.
<!-- SECTION:NOTES:END -->
