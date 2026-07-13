---
id: TASK-025
title: Implement full NOX/LOCA backend for validated C++ model
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 14:48'
updated_date: '2026-07-13 20:28'
labels:
  - backend
  - loca
  - nox
  - trilinos
  - episode-006
  - prerequisite
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create a backend that wraps the already-validated small Bergner-Spichtinger C++ residual/Jacobian problem in NOX/LOCA continuation APIs. This is now an explicit Episode 006 prerequisite for the Figure 3 LOCA path: first validate NOX/LOCA equilibrium continuation against an existing artifact, then provide the foundation needed for native LOCA Hopf continuation. Keep this task focused on generic NOX/LOCA backend infrastructure; Figure 3-specific Hopf-locus orchestration belongs in TASK-030.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 NOX/LOCA residual, parameter-continuation, and solver interfaces are implemented for the validated small model without changing the physical equations or curated output schema semantics.
- [x] #2 The full NOX/LOCA backend reproduces at least one existing Python/AUTO/Trilinos-side C++ curated continuation/eigenvalue artifact within documented tolerances.
- [x] #3 Documentation clearly compares the lightweight Trilinos-side C++ backend with the full NOX/LOCA backend, including API complexity, diagnostics, and what LOCA adds for this problem.
- [x] #4 Tests or opt-in smoke checks cover build availability, residual/Jacobian consistency, and normalized output compatibility while skipping cleanly when NOX/LOCA dependencies are unavailable.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory available Trilinos/NOX/LOCA headers, libraries, examples, and current CMake configuration; document skip conditions for environments without full LOCA support.
2. Design a minimal NOX/LOCA problem wrapper around the validated C++ model, preserving the existing equations, log-state/log-w parameterization, and physical-state conversion conventions.
3. Implement NOX residual/Jacobian interfaces and parameter plumbing for log_w, T, and other fixed environment fields without changing existing lightweight CLI behavior.
4. Validate equilibrium continuation first against an existing curated artifact, preferably a Figure 1 or Figure 2 branch, and write normalized outputs compatible with current schemas.
5. Add residual/Jacobian consistency checks and opt-in smoke tests that skip cleanly when NOX/LOCA dependencies are unavailable.
6. Document what the full NOX/LOCA backend adds relative to the lightweight C++ backend, including API complexity, diagnostics, and remaining limitations for Hopf continuation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added `NoxLocaProblem`, a dense `LOCA::LAPACK::Interface` adapter for the validated C++ residual/Jacobian with `LOCA::ParameterVector` plumbing for `log_w`, `T`, `p`, `F`, `N_a`, and `dz`.
- Added CLI commands `nox-loca-smoke` and `nox-loca-continue`; the latter preserves normalized Figure 1 branch schema via `run_nox_loca_figure1.py` and labels rows with `nox_loca_lapack_parameter_continuation`.
- Documented lightweight-vs-NOX/LOCA backend tradeoffs in `docs/NOX_LOCA_BACKEND.md` and linked it from Episode 004.
- Added opt-in pytest coverage for build availability, callback smoke checks, short continuation equivalence against the existing lightweight C++ artifact, and normalized schema compatibility.
- Verification: `uv run pytest -q` (85 passed, 3 existing overflow warnings in Hopf/Figure 2 paths).

- Correction: user correctly identified that `nox-loca-continue` only exercised the LOCA LAPACK callback once and then reused the lightweight small-system `newton_correct` continuation. This does not satisfy the full NOX/LOCA continuation requirement. Reopening TASK-025 to replace or clearly demote that path and implement an actual NOX/LOCA solver/stepper-backed path.

- Corrected `nox-loca-continue` so it no longer reuses the lightweight `newton_correct` path. It now solves each continuation correction through `LOCA::LAPACK::Group` and `NOX::Solver::Generic` (`NOX::Solver::buildSolver`) using the `NoxLocaProblem` callback adapter.
- Updated tests to assert the NOX/LOCA command dispatches to `write_nox_loca_continuation_csv`, uses `NOX::Solver::buildSolver`, and emits `loca_continuation_mode=nox_loca_lapack_group_nox_solver`.
- Updated documentation to state the precise boundary: LOCA group + NOX nonlinear solves on a repository-chosen validation `log_w` grid; native LOCA Hopf/Stepper orchestration remains TASK-030.
- Verification after correction: `uv run pytest tests/test_nox_loca_backend.py tests/test_loca_model_core.py tests/test_episode4_loca_continuation.py -q` (18 passed) and `uv run pytest -q` (85 passed, 3 existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and corrected the TASK-025 NOX/LOCA backend prerequisite for the validated C++ model.

Changes:
- Added `NoxLocaProblem`, a dense `LOCA::LAPACK::Interface` adapter over the existing residual and Sacado Jacobian with parameter plumbing for `log_w`, `T`, `p`, `F`, `N_a`, and `dz`.
- Extended `bs2026_loca_model` with `nox-loca-smoke` and a corrected `nox-loca-continue` path. The continuation path now solves each correction through `LOCA::LAPACK::Group` and `NOX::Solver::Generic` rather than reusing the lightweight `newton_correct` helper.
- Added `episodes/004-figure1-loca-continuation/scripts/run_nox_loca_figure1.py` plus reusable backend-command/backend-label options in the existing Figure 1 runner so NOX/LOCA rows keep the backend-neutral schema.
- Documented the backend boundary precisely in `docs/NOX_LOCA_BACKEND.md`: LOCA supplies the dense problem group and parameter plumbing, NOX supplies nonlinear solves, and the repository still chooses the validation log-w grid; native LOCA Hopf/Stepper orchestration remains TASK-030.
- Added pytest coverage for source/API presence, callback smoke checks, NOX/LOCA-backed short continuation equivalence against the lightweight C++ branch, and normalized output compatibility.

Tests:
- `uv run pytest tests/test_nox_loca_backend.py tests/test_loca_model_core.py tests/test_episode4_loca_continuation.py -q` → 18 passed.
- `uv run pytest -q` → 85 passed, with 3 pre-existing RuntimeWarning overflow warnings in Figure 2/Hopf paths.
<!-- SECTION:FINAL_SUMMARY:END -->
