---
id: TASK-020
title: Add shared physical Jacobian and eigenvalue infrastructure
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
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
