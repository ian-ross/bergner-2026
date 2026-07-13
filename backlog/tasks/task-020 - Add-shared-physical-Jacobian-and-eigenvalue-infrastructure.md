---
id: TASK-020
title: Add shared physical Jacobian and eigenvalue infrastructure
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 11:15'
labels:
  - shared-infra
  - figure2
  - eigenvalues
  - python
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add reusable package-level support for Figure 2 physical stability analysis. The Jacobian must represent the physical ODE vector field with respect to physical state variables (n, q, s), not the log-coordinate continuation residual. Use SymPy for derivation/provenance and expose efficient numerical evaluation for scripts and tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Package code exposes physical_jacobian and physical_eigenvalues APIs for the Bergner & Spichtinger ODE vector field.
- [ ] #2 The physical Jacobian implementation is derived or generated via SymPy, with reproducible derivation/provenance documented in code or script form.
- [ ] #3 Tests compare the analytic physical Jacobian against finite differences of vector_field at representative Figure 2 states.
- [ ] #4 Shared utilities canonicalize eigenvalue ordering, classify complex-pair versus three-real regimes, and record the real/imaginary tolerance.
- [ ] #5 Shared utilities detect simple Hopf zero crossings of Re(lambda_pair) over log_w and report crossing estimates.
- [ ] #6 Existing Figure 1 episode tests and workflows remain compatible after any shared-code refactor.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect current vector_field/residual implementations and existing Figure 1 comparison utilities to identify reusable interpolation/summary pieces that can move safely into src/.
2. Add a SymPy-backed derivation/generation path for the physical ODE Jacobian d(vector_field)/d(n,q,s), excluding evaporation for the Figure 2 s>1 equilibrium regime unless explicitly parameterized.
3. Implement efficient package APIs for physical_jacobian, physical_eigenvalues, canonical eigenvalue ordering, regime/stability classification, and Hopf zero-crossing detection.
4. Add tests comparing the analytic Jacobian to finite differences of vector_field at representative Figure 2 and nearby states, plus tests for eigenvalue ordering/classification and crossing detection.
5. If refactoring shared Figure 1 comparison helpers, update Episode 3/4 scripts minimally and run the existing Figure 1 tests to confirm no regression.
<!-- SECTION:PLAN:END -->
