---
id: TASK-005
title: Explore property-based tests for model and continuation utilities
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-24 16:53'
updated_date: '2026-06-25 09:18'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Assess and document property-based testing for the Bergner & Spichtinger model extraction workspace, with particular emphasis on Hypothesis-driven model/backend intercomparison for Python, shared AUTO Fortran, and later LOCA implementations.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Candidate properties are documented for core thermodynamic/coefficient helpers, vector-field/process-term behavior, residual adapters, continuation utilities, and Eq. 92--94 approximations where appropriate.
- [ ] #2 Recommended input generation domains and constraints are documented with attention to physical validity and numerical stability.
- [ ] #3 A recommendation is made on whether to adopt Hypothesis or another property-based testing approach, including likely dependencies and maintenance costs.
- [ ] #4 If adoption is recommended, follow-up implementation tasks are proposed with clear scope; if not, rationale and alternative test improvements are documented.
- [ ] #5 Candidate properties are documented in docs/testing.md for core thermodynamic/coefficient helpers, vector-field/process-term behavior, residual adapters, continuation utilities, and Eq. 92--94 approximations where appropriate.
- [ ] #6 Recommended input generation domains and constraints are documented in docs/testing.md with attention to physical validity and numerical stability.
- [ ] #7 A recommendation is made in docs/testing.md on whether to adopt Hypothesis or another property-based testing approach, including likely dependencies, example counts, tolerances, and maintenance costs.
- [ ] #8 docs/testing.md gives explicit implementation advice for Python-vs-Fortran AUTO model equivalence tests and later Python-vs-LOCA comparisons.
- [ ] #9 Follow-up implementation tasks are referenced explicitly from the notes or final summary so later backend tasks can apply the guidance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review existing unit tests, Episode 2 continuation/residual code, and planned AUTO/LOCA comparison needs.
2. Identify high-value properties and invariants for constants/coefficient helpers, process terms, vector field, residual adapters, continuation utilities, and analytic approximations.
3. Define conservative Hypothesis strategies for physical environments and states, including ranges, exclusions, and numerical-stability constraints.
4. Recommend whether to adopt Hypothesis and document dependencies, tolerances, example counts, markers, and maintenance risks in docs/testing.md.
5. Add explicit implementation guidance for TASK-010 and later LOCA equivalence tests, then update TASK-005 notes/final summary with follow-up references.
<!-- SECTION:PLAN:END -->
