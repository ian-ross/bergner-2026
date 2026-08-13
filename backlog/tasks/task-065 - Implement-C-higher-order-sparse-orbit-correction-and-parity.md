---
id: TASK-065
title: Implement C++ higher-order sparse orbit correction and parity
status: To Do
assignee: []
created_date: '2026-08-13 15:34'
updated_date: '2026-08-13 15:50'
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
