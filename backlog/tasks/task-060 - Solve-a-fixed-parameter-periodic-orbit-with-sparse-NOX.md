---
id: TASK-060
title: Solve a fixed-parameter periodic orbit with sparse NOX
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 10:36'
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
