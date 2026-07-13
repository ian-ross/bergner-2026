---
id: TASK-020
title: Add shared physical Jacobian and eigenvalue infrastructure
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 11:33'
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
- [x] #1 Package code exposes physical_jacobian and physical_eigenvalues APIs for the Bergner & Spichtinger ODE vector field.
- [x] #2 The physical Jacobian implementation is derived or generated via SymPy, with reproducible derivation/provenance documented in code or script form.
- [x] #3 Tests compare the analytic physical Jacobian against finite differences of vector_field at representative Figure 2 states.
- [x] #4 Shared utilities canonicalize eigenvalue ordering, classify complex-pair versus three-real regimes, and record the real/imaginary tolerance.
- [x] #5 Shared utilities detect simple Hopf zero crossings of Re(lambda_pair) over log_w and report crossing estimates.
- [x] #6 Existing Figure 1 episode tests and workflows remain compatible after any shared-code refactor.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect current vector_field/residual implementations and existing Figure 1 comparison utilities to identify reusable interpolation/summary pieces that can move safely into src/.
2. Add a SymPy-backed derivation/generation path for the physical ODE Jacobian d(vector_field)/d(n,q,s), excluding evaporation for the Figure 2 s>1 equilibrium regime unless explicitly parameterized.
3. Implement efficient package APIs for physical_jacobian, physical_eigenvalues, canonical eigenvalue ordering, regime/stability classification, and Hopf zero-crossing detection.
4. Add tests comparing the analytic Jacobian to finite differences of vector_field at representative Figure 2 and nearby states, plus tests for eigenvalue ordering/classification and crossing detection.
5. If refactoring shared Figure 1 comparison helpers, update Episode 3/4 scripts minimally and run the existing Figure 1 tests to confirm no regression.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started work: reviewed task scope and existing implementation plan; awaiting confirmation before coding.

Implemented shared stability infrastructure in src/bergner_spichtinger_2026/stability.py. Added SymPy dependency/provenance helper, physical Jacobian/eigenvalue APIs, canonical eigenvalue ordering, regime/stability classification with explicit tolerances, and Hopf crossing detection. Added tests/test_stability.py covering analytic-vs-finite-difference Jacobian checks at Figure 2 p=300 hPa/T=230 K/F=1 states, eigenvalue utilities, SymPy derivation provenance, and evaporation-switch rejection. Verified compatibility with existing workflows via full test suite: uv run pytest (58 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added shared package-level physical stability-analysis infrastructure for Figure 2.

Changes:
- Added bergner_spichtinger_2026.stability with physical_jacobian and physical_eigenvalues APIs for the physical (n, q, s) ODE vector field, distinct from log-coordinate continuation residuals.
- Included a SymPy derivation/provenance helper and added sympy as a project dependency.
- Added canonical eigenvalue ordering, complex-pair/three-real regime classification with recorded tolerances, stability classification, and simple Hopf zero-crossing detection over log(w).
- Exported the new APIs from the package top level.
- Added tests comparing the analytic Jacobian against finite differences at representative Figure 2 states and covering eigenvalue/crossing utilities.

Tests:
- uv run pytest tests/test_stability.py tests/test_residuals_continuation.py tests/test_figure1_backend_comparison.py
- uv run pytest (58 passed)

Risk/follow-up:
- physical_jacobian intentionally rejects include_evaporation=True because the paper evaporation term is discontinuous at s=1 and outside the Figure 2 s>1 equilibrium regime.
<!-- SECTION:FINAL_SUMMARY:END -->
