---
id: TASK-010
title: Add Python-driven Fortran model equivalence tests
status: Done
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:54'
labels: []
dependencies:
  - TASK-005
  - TASK-009
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use Python-side tests, preferably Hypothesis-guided per docs/testing.md, to compare the shared AUTO Fortran model core against the Python model before trusting AUTO continuation outputs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Tests generate physically valid environments and states using the documented property-based input domains.
- [x] #2 Tests compare Python and Fortran coefficients, process terms, vector field values, and log-coordinate residuals within documented tolerances.
- [x] #3 The test harness can build or invoke the Fortran evaluation driver reproducibly from the repository root.
- [x] #4 Fixed smoke cases are included alongside property-based examples to simplify diagnosis of failures.
- [x] #5 uv run pytest includes the cross-language tests or documents any opt-in marker required for local compiler/AUTO availability.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use docs/testing.md from TASK-005 to choose Hypothesis strategies, tolerances, example counts, and any pytest markers for compiler-dependent tests.
2. Add a Python test harness that builds or invokes the shared Fortran evaluation driver from TASK-009.
3. Start with fixed smoke cases matching Figure 1 environments to make failures easy to diagnose.
4. Add property-based generated cases over conservative physical ranges for T, p, w, F, N_a, n, q, and s.
5. Compare Python and Fortran coefficients, process terms, vector-field outputs, and log-coordinate residuals with documented absolute/relative tolerances.
6. Ensure uv run pytest either runs these tests directly or clearly marks/skips them when gfortran/AUTO prerequisites are unavailable.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added Hypothesis as a project test dependency.
- Expanded tests/test_fortran_model_core.py with shared smoke/property equivalence cases for coefficients, terms, RHS, and log residuals.
- Verified full suite with uv run pytest (21 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added Python-driven equivalence coverage for the shared AUTO Fortran evaluator.

Changes:
- Added Hypothesis to the project dependencies for documented property-based tests.
- Reworked Fortran model-core tests around reusable fixed and generated equivalence cases.
- Covered coefficients, process terms, vector-field outputs, log-coordinate residuals, optional environment fields, evaporation switch behavior, evaluator build-from-root, and invalid unregularized cloud-state rejection.

Tests:
- uv run pytest
<!-- SECTION:FINAL_SUMMARY:END -->
