---
id: TASK-060
title: Solve a fixed-parameter periodic orbit with sparse NOX
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 10:39'
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
- [ ] #1 The Thyra/NOX group exposes the square collocation-plus-phase residual with log period in the solution vector
- [ ] #2 Amesos2 KLU2 solves the assembled sparse Newton systems with reported factorization and solve status
- [ ] #3 NOX corrects the Python N=64 canonical seed and a documented perturbation while satisfying all accepted-orbit block tolerances
- [ ] #4 The corrected period and weighted orbit agree with the Python fixed-mesh reference within the versioned parity tolerance
- [ ] #5 Nominal solver success is rejected when block residual, phase, positivity, or linear-solve diagnostics fail
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
<!-- SECTION:NOTES:END -->
