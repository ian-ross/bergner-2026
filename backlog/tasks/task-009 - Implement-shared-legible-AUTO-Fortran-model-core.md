---
id: TASK-009
title: Implement shared legible AUTO Fortran model core
status: Done
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:51'
labels: []
dependencies:
  - TASK-006
  - TASK-007
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a top-level shared AUTO Fortran implementation of the Bergner & Spichtinger model core, organized for legibility and cross-comparison with the Python code before episode-specific AUTO continuation runs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Top-level auto/ shared source files define constants, environment parameters, coefficient calculations, process terms, vector field, and log-coordinate equilibrium residuals.
- [x] #2 Fortran comments and naming cross-reference the Python implementation and paper equations to the same documentation standard as the Python model core.
- [x] #3 The shared Fortran model exposes a small driver or callable path that can evaluate selected model quantities without running AUTO continuation.
- [x] #4 Build/run instructions for the shared Fortran model work with /usr/local/bin/auto and gfortran available on the system.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the Python constants, coefficient helpers, process_terms, vector_field, and residual adapter modules to define the Fortran module boundaries and naming.
2. Create top-level auto/ shared source files after TASK-006 establishes the repository convention.
3. Translate constants and Environment-style parameters into legible double-precision Fortran definitions with comments cross-referencing paper equations and Python names.
4. Translate coefficient, process-term, vector-field, and log-coordinate residual routines in small testable units rather than embedding everything in AUTO callbacks.
5. Add a simple Fortran evaluation driver or command mode that prints machine-readable values for selected quantities, enabling TASK-010 tests before AUTO continuation is used.
6. Document build/run expectations with gfortran and AUTO-07p installed at /usr/local/bin/auto.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added top-level auto/ shared Fortran constants, model core, evaluator, Makefile, and README.
- Added Python-driven pytest coverage that compiles the Fortran evaluator and compares coefficients, process terms, RHS, and log-coordinate residuals against the Python implementation.
- Verified AUTO path and gfortran build/run with make -C auto check-auto && make -C auto smoke.
- Full suite passes with uv run pytest.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the shared legible AUTO Fortran model core for TASK-009.

Changes:
- Added top-level auto/ shared Fortran modules for constants, environment/coefficient calculations, process terms, vector field, and log-coordinate equilibrium residuals.
- Added a standalone bs2026_evaluator driver for machine-readable coefficient, process-term, RHS, and residual evaluation without running AUTO continuation.
- Documented gfortran and /usr/local/bin/auto build/run workflow and added a Makefile smoke path.
- Added pytest coverage that compiles the Fortran evaluator and compares new Fortran code paths against the Python model core.

Validation:
- make -C auto check-auto
- make -C auto smoke
- uv run pytest
<!-- SECTION:FINAL_SUMMARY:END -->
