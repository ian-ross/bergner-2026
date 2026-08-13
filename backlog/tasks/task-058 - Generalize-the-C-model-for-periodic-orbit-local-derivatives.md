---
id: TASK-058
title: Generalize the C++ model for periodic-orbit local derivatives
status: Done
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 05:05'
labels:
  - episode-008
  - cpp
  - trilinos
dependencies:
  - TASK-057
references:
  - loca/include/bergner_spichtinger_2026_loca/model.hpp
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the validated shared C++ model evaluator to provide value-equivalent transformed dynamics and small local Sacado derivatives with respect to state, temperature, and log vertical velocity.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The generalized evaluator preserves value-level parity with the existing validated no-evaporation C++ and Python model over representative physical states
- [x] #2 Local Sacado evaluation supplies D_x g, g_T, and g_log_w without differentiating the packed orbit vector
- [x] #3 T-hat spine and rho slice parameter derivatives apply the documented mappings and chain rules
- [x] #4 Centered finite-difference tests cover state derivatives, temperature-dependent coefficients, physical control derivatives, and normalized parameter columns
- [x] #5 Existing equilibrium and Hopf backend behavior remains regression-tested
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refactor the shared C++ model internals so temperature and log vertical velocity can be scalar-templated alongside the transformed three-state input, while retaining the existing Environment, residual_values, physical RHS/Jacobian, equilibrium, and Hopf-facing APIs as value-compatible wrappers. Keep the no-evaporation differentiable path explicit and preserve the existing discontinuous evaporation behavior only for value evaluation.
2. Add a compact local Sacado evaluation API that seeds exactly five independent variables (three transformed-state components, T, and log(w)) and returns g, D_x g, g_T, and g_log_w from one local model evaluation. Add normalized rho-slice and T-hat-spine column helpers implementing g_rho = 0.5(log_w_upper-log_w_lower)g_log_w and g_T_hat = 25[g_T + (d log_w_spine/dT)g_log_w], without introducing packed-orbit AD.
3. Extend the C++ model CLI only as needed to expose the local derivative/value result and normalized parameter columns as deterministic test seams, leaving existing command output contracts unchanged.
4. Expand tests/test_loca_model_core.py with representative no-evaporation value-parity cases against both the legacy C++ wrappers and Python transformed dynamics; centered finite-difference checks for D_x g, physical T and log(w) derivatives across states/temperatures; targeted checks that temperature-dependent coefficients contribute correctly; and rho/T-hat chain-rule column checks.
5. Run the focused C++ model tests and existing NOX/LOCA equilibrium/Hopf regression suites, then the full Python suite, compile/whitespace checks, and self-review. Record validation and any residual risks in the task before checking acceptance criteria and completing it.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Plan approved; implementation started from a clean worktree. Confirmed cmake, g++, uv, pytest, Backlog CLI, and the configured Trilinos installation are available.

- Generalized the shared C++ model internals so the environment and all temperature-dependent coefficients use the active scalar type. Added a five-direction local Sacado evaluator for (log(n), log(q), s, T, log(w)) returning g, D_x g, g_T, and g_log_w; the differentiable path explicitly rejects the discontinuous evaporation switch.
- Added rho and T-hat parameter-column helpers with the documented chain rules, plus deterministic CLI test seams. Existing residual, state/physical Jacobian, equilibrium, and Hopf APIs remain intact.
- Added representative C++/Python value and analytic-derivative parity tests, centered checks for state/T/log(w) and both normalized coordinates, and documentation of the implemented local derivative contract. Focused model plus equilibrium/Hopf backend regression suite currently passes (32 focused model tests after the final added case; prior combined backend run passed 31 tests before that case was added).

- Final validation: full suite passed with 158 passed / 1 explicit pre-existing skip and three known exploratory-solver overflow warnings. CMake rebuild, py_compile, git diff whitespace checks, and C++ LSP diagnostics passed; Python LSP reports only the repository's existing src-layout import-resolution warnings.
- Two independent fresh-context reviewers found no blockers or fixes worth doing now. One noted only the existing infrastructure risk that C++/Hopf tests skip on runners without the hard-coded Trilinos toolchain; this runner had Trilinos and exercised them.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Generalized the validated shared C++ model for periodic-orbit local derivatives while preserving existing equilibrium and Hopf behavior.

Changes:
- Scalar-templated the model environment, coefficients, and transformed dynamics so Sacado propagates through every temperature-dependent coefficient and w = exp(log(w)).
- Added a compact five-direction local evaluator returning g, D_x g, g_T, and g_log_w without any packed-orbit dependency.
- Added rho-slice and T-hat-spine derivative helpers implementing the documented normalized-coordinate chain rules.
- Added deterministic CLI test seams while retaining all existing command contracts and value/Jacobian wrappers.
- Added representative C++/Python value and derivative parity tests, centered finite differences for state/T/log(w)/normalized columns, evaporation rejection coverage, and Episode 008 documentation.

Validation:
- uv run pytest -q: 158 passed, 1 pre-existing skip; three known exploratory-solver overflow warnings.
- Focused C++ model and NOX/LOCA equilibrium/Hopf regression tests passed with the configured Trilinos toolchain.
- CMake rebuild, py_compile, git diff --check, C++ LSP diagnostics, and two independent review passes succeeded.

Risk:
- As before, C++/Hopf tests skip on runners lacking the configured /opt/Trilinos installation; they ran successfully in this environment.
<!-- SECTION:FINAL_SUMMARY:END -->
