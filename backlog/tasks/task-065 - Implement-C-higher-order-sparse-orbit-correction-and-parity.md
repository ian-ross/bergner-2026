---
id: TASK-065
title: Implement C++ higher-order sparse orbit correction and parity
status: To Do
assignee: []
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 16:11'
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
1. Review TASK-064's accepted/rejected case manifest and language-neutral parity bundle, then freeze the C++ higher-order formulation and fixture-reader versions. Preserve the existing one-rank Tpetra, local-Sacado, Thyra/NOX, KLU2, and midpoint CLI contracts while identifying names that can be generalized without breaking regressions.
2. Generalize OrbitLayout and retained Tpetra graph construction to r explicit stages with square dimension 3N(r+1)+1. Own endpoint, per-stage, update, log-period, and phase indices; preserve cyclic wraparound and stable graph reuse for a fixed rule/mesh.
3. Generalize residual and sparse Jacobian value assembly to the shared Gauss tables. Assemble every stage equation, endpoint update, log-period column, quadrature phase row, and analytic normalized rho/T-hat parameter column from small local Sacado derivatives without differentiating the packed orbit.
4. Generalize the Thyra model evaluator and NOX/KLU2 fixed-parameter corrector to rule-driven layouts while retaining independent acceptance gates for stage/update/phase residuals, physical positivity/finiteness, phase energy, and actual Amesos2 factorization/solve activity.
5. Extend the language-neutral fixture/CLI seams to read TASK-064 two-/three-stage converged and nonsolution cases and report rule, order, mesh/layout/graph dimensions, coefficient checksum, residual blocks, Jacobian actions, parameter columns, solver counters, source fingerprints, and explicit propagation of upstream rejected fixtures.
6. Establish component-level C++/Python parity for every accepted fixture in the bundle and all nonsolution fixtures. Check residuals, phase rows, log-period/parameter columns, and Jacobian actions against both Python values and centered differences using versioned tolerances.
7. Run NOX/KLU2 correction at minimum for canonical two-stage N=64, canonical three-stage N=32, and every accepted T=210 K guard three-stage N=32 fixture. Compare corrected periods and phase-aligned weighted orbits with every corresponding accepted Python fixture to 1e-8; preserve explicit upstream rejection status instead of inventing a substitute case.
8. Emit deterministic higher-order C++ fixture/correction artifacts and add integration tests for indexing, dimensions, sparsity/wraparound, retained graph identity, derivative columns, acceptance/rejection, KLU2 diagnostics, all-fixture parity, midpoint regressions, stale-build/source guards, and regeneration.
9. Update Episode 008 documentation, run clean CMake/Ninja builds, focused executable and Python-driven integration tests, artifact --check commands, the full applicable suite, compiler diagnostics, diff checks, self-review, and independent correctness/test review before completion.
<!-- SECTION:PLAN:END -->
