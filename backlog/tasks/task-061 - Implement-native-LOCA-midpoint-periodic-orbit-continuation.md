---
id: TASK-061
title: Implement native LOCA midpoint periodic-orbit continuation
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 11:41'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
dependencies:
  - TASK-057
  - TASK-060
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use LOCA's native pseudo-arclength stepper around the sparse periodic-orbit base group on a fixed midpoint mesh, rather than a repository-owned parameter grid corrected through NOX.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 LOCA owns predictor, tangent, arclength constraint, adaptive step size, rejection, and retry while the mesh/layout is unchanged
- [ ] #2 The base group contains no duplicate arclength row and exposes normalized rho or T-hat through the parameter interface
- [ ] #3 Deterministic two-point bootstrap initializes each continuation direction and is recorded separately from native accepted steps
- [ ] #4 Native LOCA continues the T=225 K fixed-temperature move to the spine plus short spine and T=210 K slice segments in both directions
- [ ] #5 Fixed-mesh LOCA periods and weighted orbits agree with corresponding Python continuation segments within versioned tolerances
- [ ] #6 Continuation events distinguish accepted/rejected steps and controlled phase-reference refresh restarts
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the fixed-mesh midpoint backend with a one-parameter continuation family for normalized rho and T-hat paths. Keep the existing 6N+1 collocation-plus-phase residual square, retain its sparse graph, expose exactly one scalar through the Thyra/LOCA parameter interface, and provide the existing analytic normalized parameter column as DfDp while preserving the TASK-060 fixed-parameter API.
2. Add the native LOCA group/stepper layer with the versioned endpoint-stage weighted orbit metric, unit log-period and active-coordinate weights, KLU2-backed Newton correction, pseudo-arclength continuation, adaptive step sizing, rejection, and retry. Disable LOCA arc-length rescaling that would alter the frozen metric, and verify the base group never contains an arclength row.
3. Implement deterministic signed two-point bootstrap for every direction: fixed-parameter-correct a requested neighbor, reject failed or excessive changes, halve deterministically, form the oriented weighted secant, and pass that initialization to LOCA. Record bootstrap attempts separately from native steps.
4. Add continuation orchestration and event capture for the five required fixed-mesh branches: T=225 K to the exact spine, positive and negative spine branches to T=226 K and exact T=210 K, then negative and positive T=210 K rho slices. Keep phase references immutable inside each segment; at the two controlled refresh boundaries verify the refreshed fixed-parameter orbit, rebuild the group/stepper, and record restart lineage.
5. Add deterministic Episode 008 native-LOCA JSON/NPZ artifact generation and --check support. Record accepted/rejected native attempts, retry/step-size history, bootstrap provenance, phase-reference IDs, normalized and physical coordinates, periods, residual/phase/arclength diagnostics, weighted vectors/tangents, solver status, base/extended dimensions, and backend/method provenance.
6. Add focused Python-driven integration tests for the one-parameter/no-duplicate-row contract, analytic DfDp, exact metric use by LOCA, deterministic bootstrap halving/orientation, native rejection/retry, controlled refresh semantics, exact bidirectional endpoints, event partitioning, and fixed-mesh period/weighted-orbit parity against the versioned Python branches. Update the Episode 008 README and decision record with the implementation, commands, calibrated tolerances, evidence, and non-production-accuracy warning.
7. Validate fixture/artifact regeneration, direct native branch runs, focused TASK-061/TASK-060/backend tests, a clean CMake/Ninja build, the full Python suite, compiler/LSP diagnostics where reliable, py_compile, and git diff whitespace checks; then self-review and obtain independent correctness and test-quality review before completing the acceptance criteria.
<!-- SECTION:PLAN:END -->
