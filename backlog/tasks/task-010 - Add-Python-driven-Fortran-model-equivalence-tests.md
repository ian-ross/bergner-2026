---
id: TASK-010
title: Add Python-driven Fortran model equivalence tests
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use Python-side tests, preferably Hypothesis-guided per docs/testing.md, to compare the shared AUTO Fortran model core against the Python model before trusting AUTO continuation outputs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Tests generate physically valid environments and states using the documented property-based input domains.
- [ ] #2 Tests compare Python and Fortran coefficients, process terms, vector field values, and log-coordinate residuals within documented tolerances.
- [ ] #3 The test harness can build or invoke the Fortran evaluation driver reproducibly from the repository root.
- [ ] #4 Fixed smoke cases are included alongside property-based examples to simplify diagnosis of failures.
- [ ] #5 uv run pytest includes the cross-language tests or documents any opt-in marker required for local compiler/AUTO availability.
<!-- AC:END -->
