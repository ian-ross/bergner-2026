---
id: TASK-005
title: Explore property-based tests for model and continuation utilities
status: Done
assignee:
  - '@pi'
created_date: '2026-06-24 16:53'
updated_date: '2026-06-25 09:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Assess and document property-based testing for the Bergner & Spichtinger model extraction workspace, with particular emphasis on Hypothesis-driven model/backend intercomparison for Python, shared AUTO Fortran, and later LOCA implementations.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Candidate properties are documented for core thermodynamic/coefficient helpers, vector-field/process-term behavior, residual adapters, continuation utilities, and Eq. 92--94 approximations where appropriate.
- [x] #2 Recommended input generation domains and constraints are documented with attention to physical validity and numerical stability.
- [x] #3 A recommendation is made on whether to adopt Hypothesis or another property-based testing approach, including likely dependencies and maintenance costs.
- [x] #4 If adoption is recommended, follow-up implementation tasks are proposed with clear scope; if not, rationale and alternative test improvements are documented.
- [x] #5 Candidate properties are documented in docs/testing.md for core thermodynamic/coefficient helpers, vector-field/process-term behavior, residual adapters, continuation utilities, and Eq. 92--94 approximations where appropriate.
- [x] #6 Recommended input generation domains and constraints are documented in docs/testing.md with attention to physical validity and numerical stability.
- [x] #7 A recommendation is made in docs/testing.md on whether to adopt Hypothesis or another property-based testing approach, including likely dependencies, example counts, tolerances, and maintenance costs.
- [x] #8 docs/testing.md gives explicit implementation advice for Python-vs-Fortran AUTO model equivalence tests and later Python-vs-LOCA comparisons.
- [x] #9 Follow-up implementation tasks are referenced explicitly from the notes or final summary so later backend tasks can apply the guidance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review existing unit tests, Episode 2 continuation/residual code, and planned AUTO/LOCA comparison needs.
2. Identify high-value properties and invariants for constants/coefficient helpers, process terms, vector field, residual adapters, continuation utilities, and analytic approximations.
3. Define conservative Hypothesis strategies for physical environments and states, including ranges, exclusions, and numerical-stability constraints.
4. Recommend whether to adopt Hypothesis and document dependencies, tolerances, example counts, markers, and maintenance risks in docs/testing.md.
5. Add explicit implementation guidance for TASK-010 and later LOCA equivalence tests, then update TASK-005 notes/final summary with follow-up references.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Created docs/testing.md with conservative Hypothesis adoption guidance, generated domains, candidate properties, and backend-equivalence advice for TASK-010 and later LOCA work.

Verification: uv run pytest (11 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Documented the property-based testing strategy in docs/testing.md for TASK-005.

Changes:
- Added candidate properties for coefficient/thermodynamic helpers, process terms, vector field behavior, residual adapters, continuation utilities, and Eq. 92--94 approximation helpers.
- Documented physically valid Hypothesis input domains, constraints, tolerances, example counts, dependencies, and maintenance costs.
- Added explicit Python-vs-AUTO Fortran guidance for TASK-010 and reusable advice for later Python-vs-LOCA comparisons.

Tests:
- uv run pytest (11 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
