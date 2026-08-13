---
id: TASK-065
title: Implement C++ higher-order sparse orbit correction and parity
status: Done
assignee:
  - '@iross'
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 21:00'
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
- [x] #1 The one-rank Tpetra layout and retained sparse graph support explicit one-, two-, and three-stage Gauss systems with 3N(r+1)+1 square base dimensions, cyclic updates, log-period column, and one phase row
- [x] #2 C++ residuals, analytic Jacobian actions, phase rows, log-period columns, and normalized rho/T-hat parameter columns match every upstream accepted converged fixture covered by the language-neutral bundle plus its nonsolution higher-order fixtures within versioned parity tolerances
- [x] #3 Thyra/NOX with Amesos2 KLU2 corrects at minimum the canonical two-stage N=64 and three-stage N=32 fixtures plus all three T=210 K guard three-stage N=32 fixtures when those upstream fixtures are accepted, and independently enforces residual, phase, positivity, phase-energy, and linear-solve gates; an upstream fixture rejection is propagated explicitly rather than silently excluded
- [x] #4 For every upstream accepted fixture covered by the parity bundle, corrected periods and phase-aligned weighted orbits match the corresponding Python fixed-mesh solutions within the versioned 1e-8 fixed-mesh parity tolerance
- [x] #5 Artifacts and CLI output record rule/order, mesh/layout/graph dimensions, coefficient checksum, block diagnostics, KLU2 counters, source/runtime provenance, upstream fixture status, and deterministic fixture regeneration
- [x] #6 Focused integration tests preserve midpoint behavior and cover higher-order indexing/sparsity, wraparound, retained-graph reuse, finite-difference derivative checks, correction acceptance/rejection, explicit fixture-rejection propagation, and Python/C++ parity
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

- Implemented a rule-driven serial Tpetra layout and retained sparse graph for one-, two-, and three-stage Gauss--Legendre systems with square 3N(r+1)+1 dimensions, cyclic updates, explicit stage indexing, log-period coordinate/column, and one quadrature-normalized phase row. Midpoint compatibility entry points remain, while midpoint-only LOCA helpers explicitly reject higher-order layouts for TASK-066.
- Generalized residual, analytic sparse Jacobian, phase energy/row, log-period and normalized rho/T-hat columns, diagnostics, physical checks, Thyra model, and NOX/Amesos2-KLU2 correction using local Sacado derivatives. Hardened zero-iteration and failed-solver handling so independent acceptance gates remain truthful and failure output never presents a synthetic residual as computed.
- Added deterministic C++ fixture and correction-result generators/artifacts. Coverage includes exact TASK-064 g2-N64/g3-N64 accepted and nonsolution parity cases, canonical g3-N32, all three accepted T=210 K g3-N32 guards, and explicit canonical g3-N16 upstream rejection propagation. CLI/artifacts record rule/order, mesh/layout/block/graph dimensions, coefficient checksum, residual diagnostics, KLU2 counters, source/runtime/executable provenance, status, acceptance reasons, and correction parity.
- Added focused integration coverage for r=1/2/3 indexing/sparsity/wraparound, retained graph reuse, exact frozen residual replay, Jv/log-period/parameter columns, centered differences, correction acceptance, every independent gate, stable failure output, malformed/trailing fixture rejection, upstream rejection/nonsolution semantics, 1e-8 fixed-mesh parity, deterministic regeneration, and midpoint/native regressions.
- Correction parity (period relative, phase-aligned weighted orbit): g2-N64 (5.35e-15, 3.69e-13), g3-N32 (4.97e-14, 7.90e-13), g3-N64 (8.52e-14, 2.77e-13), guard rho=0 (1.03e-13, 3.84e-13), guard rho=-0.15 (4.09e-14, 2.80e-13), guard rho=+0.15 (5.18e-15, 1.23e-12). Every accepted correction recorded real KLU2 symbolic/numeric factorization and solve activity.
- Validation: clean Release CMake/Ninja build with no compiler warnings; focused C++/midpoint/native suite 63 passed; final higher-order focused suite 29 passed after exact-fixture derivative expansion; full suite 237 passed, 1 skipped (three pre-existing overflow warnings in unrelated Episode 005/006/Hopf tests); all TASK-065 fixture/correction, midpoint, native LOCA, TASK-064 qualification, and coefficient --check commands passed; py_compile and git diff --check passed; no staged files. Independent final correctness review found no blocker/high-severity issues; final contract review gap was resolved by extending exact language-neutral derivative/parameter parity checks.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented C++ higher-order sparse fixed-parameter orbit correction and Python parity for Episode 008.

Changes:
- Generalized the one-rank Tpetra layout, retained graph, residual, analytic Jacobian, phase row, log-period and normalized parameter columns from midpoint to frozen one-/two-/three-stage Gauss rules while preserving the square 3N(r+1)+1 base system and midpoint compatibility.
- Generalized Thyra/NOX/Amesos2-KLU2 correction with independent residual, phase, positivity/finiteness, phase-energy, and real linear-solve activity gates; made zero-iteration and failure reporting stable and truthful.
- Added deterministic C++ fixture and correction-result artifacts with explicit accepted, nonsolution, and rejected-upstream semantics, complete source/runtime/coefficient provenance, graph/block diagnostics, KLU2 counters, and correction parity.
- Covered canonical g2-N64, g3-N32, g3-N64, all three T=210 K g3-N32 guards, exact TASK-064 nonsolutions, and propagated canonical g3-N16 rejection without invoking NOX.
- Added focused C++/Python integration tests for dimensions/indexing/sparsity/wraparound, retained graph reuse, exact frozen residual/Jacobian/parameter parity, finite differences, correction and rejection gates, malformed fixtures, 1e-8 fixed-mesh parity, regeneration, and midpoint/native regressions.
- Updated Episode 008 documentation and regenerated source-bound midpoint/native artifacts.

Validation:
- Clean Release CMake/Ninja build, no compiler warnings.
- Full suite: 237 passed, 1 skipped; only three pre-existing unrelated overflow warnings.
- All relevant artifact --check commands, py_compile, git diff --check, and independent correctness/contract reviews passed.

Scope:
- Higher-order native LOCA continuation remains explicitly deferred to TASK-066.
<!-- SECTION:FINAL_SUMMARY:END -->
