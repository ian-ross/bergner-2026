---
id: TASK-060
title: Solve a fixed-parameter periodic orbit with sparse NOX
status: Done
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 11:26'
labels:
  - episode-008
  - cpp
  - trilinos
  - nox
dependencies:
  - TASK-059
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Expose the sparse Tpetra periodic-orbit base system through Thyra/NOX and correct the canonical midpoint orbit at fixed parameters using Amesos2 KLU2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Thyra/NOX group exposes the square collocation-plus-phase residual with log period in the solution vector
- [x] #2 Amesos2 KLU2 solves the assembled sparse Newton systems with reported factorization and solve status
- [x] #3 NOX corrects the Python N=64 canonical seed and a documented perturbation while satisfying all accepted-orbit block tolerances
- [x] #4 The corrected period and weighted orbit agree with the Python fixed-mesh reference within the versioned parity tolerance
- [x] #5 Nominal solver success is rejected when block residual, phase, positivity, or linear-solve diagnostics fail
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a reusable sparse periodic-orbit Thyra adapter under `loca/include/bergner_spichtinger_2026_loca/` that wraps the existing one-rank Tpetra maps/vectors/matrices as Thyra spaces and operators, implements the square `6N+1` `ModelEvaluator` contract for residual and Jacobian evaluation, and preserves the fixed collocation graph and `log(P)` solution coordinate.
2. Add a NOX fixed-parameter solve layer using `NOX::Thyra::Group` and an explicitly selected `Thyra::Amesos2LinearOpWithSolveFactory<double>` with KLU2. Retain NOX nonlinear/iteration statistics and extract the Amesos2 solver status so symbolic factorization, numeric factorization, solve counts, backend name, and failures are reported rather than inferred.
3. Add a single post-solve acceptance evaluator that requires NOX convergence, accepted stage/update max and RMS residuals, accepted normalized phase residual, finite positive physical `n`, `q`, and `P`, adequate finite phase energy, and successful reported KLU2 factorization/solve status; return stable rejection reasons so nominal solver success can never bypass the scientific and linear gates.
4. Extend the Episode 008 language-neutral fixture pipeline with the true Python N=64 Hermite/bootstrap seed and one deterministic documented perturbation, while preserving direct provenance to the frozen TASK-056 reference solution. Extend `bs2026_midpoint_orbit` with a machine-readable solve command that emits the corrected vector, period, diagnostics, NOX/KLU2 status, acceptance decision, and rejection reasons.
5. Add Python-driven integration tests that solve both N=64 starts, assert the Thyra model remains the square collocation-plus-phase system, verify KLU2 symbolic/numeric/solve completion, independently recompute every accepted-orbit gate, and compare corrected period and the fixed-metric weighted orbit to the frozen Python solution at the binding `1e-8` parity tolerance. Add focused guard tests proving individually that block, phase, positivity/finite, phase-energy, and linear-diagnostic failures reject an otherwise nominally converged result.
6. Version and document the NOX/KLU2 solver settings, deterministic perturbation, output/status contract, parity comparison, and distinction between discrete N=64 convergence and production orbit accuracy in the Episode 008 README/design notes and fixture manifest.
7. Validate fixture regeneration/`--check`, focused TASK-060 and existing TASK-059/model/backend tests, direct canonical and perturbed CLI solves, a clean CMake build, the full Python suite, LSP/compiler diagnostics, and whitespace checks; then self-review and obtain independent correctness/test-quality review before completing the task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-060, assigned it to @pi, and reviewed TASK-059, the Episode 008 README, and the binding collocation/phase decisions.
- Confirmed a clean worktree; CMake, CTest, Ninja, g++, uv, and Backlog are available. The installed Trilinos package list includes Tpetra, Thyra/Tpetra adapters, NOX, Amesos2, Belos, Ifpack2, and Sacado; Amesos2 KLU2 support is enabled.
- Reconnaissance confirmed the existing assembler already supplies the square `6N+1` residual/Jacobian and block diagnostics. TASK-060 is therefore a thin reusable Thyra/NOX/KLU2 solve and acceptance layer plus true-seed/perturbation fixtures, parity tests, and documentation.

- Implemented a reusable `Thyra::StateFuncModelEvaluatorBase<double>` for the square one-rank Tpetra midpoint system, retained-graph in-place Jacobian updates, and a fixed-parameter `NOX::Thyra::Group` corrector with explicitly selected Amesos2 KLU2.
- Added centralized acceptance with stable rejection reasons for NOX status, stage/update max and RMS, normalized phase, physical-state and period positivity/finiteness, phase energy, and reported KLU2 symbolic/numeric/solve completion.
- Added exact N=64 Hermite/bootstrap and deterministic sinusoidally perturbed language-neutral fixtures, versioned solver settings and 1e-8 corrected-solution parity tolerance, machine-readable solve output, manifest provenance, documentation, and independent Python parity/guard tests.
- Independent review identified Tpetra fill-state, period-guard, positivity-recomputation, tolerance-linkage, and CLI-arity gaps; all were fixed. A final two-angle review found no remaining blockers or fixes worth doing now.
- Final validation: both N=64 starts converged in 5 NOX iterations with KLU2 symbolic=1, numeric=1, solves=1 and accepted block diagnostics; focused backend/model suite passed 48 tests; full suite passed 184 tests with 1 explicit pre-existing skip and three known exploratory overflow warnings; clean Debug CMake/Ninja build, all relevant fixture --check commands, py_compile, and git diff --check passed. Compiler validation supersedes stale LSP diagnostics caused by the repository compilation-database discovery path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented sparse fixed-parameter periodic-orbit correction through Thyra, NOX, and Amesos2 KLU2.

Changes:
- Added a reusable Thyra model exposing the existing square `6N+1` Tpetra collocation-plus-normalized-phase system, retaining `log(P)` as the final solution coordinate and reusing the fixed sparse graph safely across Jacobian fills.
- Added NOX Newton/backtracking correction with an explicitly selected KLU2 direct solver and real Amesos2 symbolic-factorization, numeric-factorization, and solve counters/status.
- Centralized accepted-orbit validation so nominal NOX success is rejected for block residual, phase, physical positivity/finiteness, period positivity/finiteness, phase-energy, or linear-diagnostic failures.
- Added exact canonical N=64 Hermite/bootstrap and deterministic perturbed fixtures with versioned solver configuration, provenance, byte-reproducible generation, and a 1e-8 corrected period/weighted-orbit parity contract.
- Extended the midpoint CLI with machine-readable solve diagnostics and failure-guard seams; added behavior-driven integration tests that independently recompute all scientific gates and compare against the frozen Python fixed-mesh reference.
- Updated Episode 008 documentation while preserving the one-rank midpoint machinery scope; native LOCA continuation remains follow-up work.

Validation:
- Full suite: 184 passed, 1 pre-existing explicit skip; three known exploratory overflow warnings.
- Focused TASK-060/TASK-059 plus backend/model/Hopf/build regressions: 48 passed.
- Canonical and perturbed N=64 solves: both converged in 5 NOX iterations, reported KLU2 symbolic=1/numeric=1/solve=1, and passed all acceptance gates.
- Clean Debug CMake/Ninja build, Episode 008 artifact --check commands, py_compile, and git diff --check passed.
- Two independent final reviewers found no remaining blockers or fixes worth doing now.
<!-- SECTION:FINAL_SUMMARY:END -->
