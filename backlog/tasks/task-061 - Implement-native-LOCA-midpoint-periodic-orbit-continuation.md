---
id: TASK-061
title: Implement native LOCA midpoint periodic-orbit continuation
status: Done
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 13:44'
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
- [x] #1 LOCA owns predictor, tangent, arclength constraint, adaptive step size, rejection, and retry while the mesh/layout is unchanged
- [x] #2 The base group contains no duplicate arclength row and exposes normalized rho or T-hat through the parameter interface
- [x] #3 Deterministic two-point bootstrap initializes each continuation direction and is recorded separately from native accepted steps
- [x] #4 Native LOCA continues the T=225 K fixed-temperature move to the spine plus short spine and T=210 K slice segments in both directions
- [x] #5 Fixed-mesh LOCA periods and weighted orbits agree with corresponding Python continuation segments within versioned tolerances
- [x] #6 Continuation events distinguish accepted/rejected steps and controlled phase-reference refresh restarts
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-061 and assigned it to @iross. Reviewed completed dependencies TASK-057 and TASK-060, the Episode 008 README, and the binding collocation/phase decisions.
- Confirmed CMake, Ninja, CTest, g++, uv, Backlog, and the installed Trilinos LOCA Thyra/Stepper headers are available. Repository worktree was clean before planning.
- Architecture review confirmed the key seams: TASK-060 currently exposes Np=0 and needs a one-parameter Thyra model; native LOCA must use the frozen weighted continuation metric rather than the stock dimension-normalized Thyra dot product; bootstrap and controlled refreshes remain separate provenance events.

- Plan approved; implementation started.

- Implemented the one-parameter native LOCA Thyra family, binding endpoint/stage weighted metric, analytic normalized DfDp, KLU2-backed native pseudo-arclength Stepper, deterministic signed two-point bootstrap with Restart tangent injection, and truthful accepted/rejected/retry event capture.
- Native C++ LOCA independently executes all five required N=64 branches with exact target landings. Two controlled phase-reference refreshes run strict fixed-parameter NOX/KLU2 verification at unchanged physical coordinates and rebuild the model/group/stepper; reference lineage remains immutable within segments.
- Curated JSON/NPZ artifacts contain 32 native-emitted vectors and no copied Python vectors. Independent Python fixed-parameter corrections start from nearest frozen Python branch vectors at every native coordinate. Maximum period relative error is 1.24e-11 and maximum weighted-orbit error is 2.96e-11 versus the versioned 2e-7 tolerance.
- Added a deterministic native rejected-step/reduced-retry scenario; separated raw LOCA counters from derived callback/save partitions; recorded coordinate deltas without mislabeling them as arclength step sizes; expanded source/build/runtime fingerprints and stale-executable guards.
- Independent correctness and test-quality review findings were fixed across event truthfulness, refresh verification, parity independence, vector-origin guards, metric checks, and provenance. Final targeted review found no blockers or fixes worth doing now.
- Final validation: 7 focused native-LOCA tests passed; full suite passed with 191 passed / 1 explicit pre-existing skip and three known exploratory-solver overflow warnings; clean Debug CMake/Ninja build, native and Tpetra artifact --check commands, py_compile, and git diff whitespace checks passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented genuine native LOCA fixed-mesh midpoint periodic-orbit continuation for Episode 008.

Changes:
- Added a one-parameter Thyra model exposing normalized rho or T-hat and analytic DfDp while preserving the square 6N+1 collocation-plus-phase base system with no duplicate arclength row.
- Added a weighted LOCA Thyra group using the binding endpoint/stage half-weighted orbit metric with unit log-period and active-coordinate weights. Native LOCA owns Secant prediction, tangent construction, pseudo-arclength constraint, adaptive stepping, rejection, and retry.
- Added deterministic signed fixed-parameter bootstrap with step halving and explicit Restart tangent injection for every continuation direction. Bootstrap events remain separate from native continuation attempts.
- Added full native C++ replay of the T=225 K move to the spine, positive/negative spine segments to T=226 K and exact T=210 K, and both T=210 K rho slices. All five branches land exactly on their targets.
- Added two controlled phase-reference refreshes with strict NOX/KLU2 verification, unchanged physical coordinates, immutable segment lineage, and complete model/group/stepper rebuilds.
- Added truthful native continuation event accounting, including a deterministic rejected attempt followed by reduced retry, finite attempted/accepted coordinates, coordinate deltas, and separate raw versus derived counters.
- Added deterministic native JSON/NPZ artifacts containing 32 C++-emitted orbit vectors, branch/bootstrap/restart lineage, diagnostics, source/build/runtime fingerprints, and stale-executable guards.
- Added independent all-point Python parity correction initialized from frozen Python branch vectors rather than native solutions. Maximum relative period error is 1.24e-11 and maximum weighted-orbit error is 2.96e-11, both well below the versioned 2e-7 tolerance.
- Updated Episode 008 documentation and added focused integration tests for native ownership, dimensions, metric semantics, DfDp/interface contracts, bootstrap orientation, rejection/retry, exact endpoints, refresh verification, parity independence, vector provenance, and reproducibility.

Validation:
- Full suite: 191 passed, 1 explicit pre-existing skip; three known exploratory overflow warnings.
- Focused native-LOCA tests: 7 passed.
- Clean Debug CMake/Ninja build passed.
- Native and Tpetra artifact regeneration checks, py_compile, and git diff --check passed.
- Independent final review found no remaining blockers or fixes worth doing now.

Scope:
- This remains an N=64 midpoint continuation machinery/parity milestone, not production Figure 5 period accuracy.
<!-- SECTION:FINAL_SUMMARY:END -->
