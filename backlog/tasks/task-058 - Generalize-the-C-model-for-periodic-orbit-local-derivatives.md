---
id: TASK-058
title: Generalize the C++ model for periodic-orbit local derivatives
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 04:58'
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
- [ ] #1 The generalized evaluator preserves value-level parity with the existing validated no-evaporation C++ and Python model over representative physical states
- [ ] #2 Local Sacado evaluation supplies D_x g, g_T, and g_log_w without differentiating the packed orbit vector
- [ ] #3 T-hat spine and rho slice parameter derivatives apply the documented mappings and chain rules
- [ ] #4 Centered finite-difference tests cover state derivatives, temperature-dependent coefficients, physical control derivatives, and normalized parameter columns
- [ ] #5 Existing equilibrium and Hopf backend behavior remains regression-tested
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
<!-- SECTION:NOTES:END -->
