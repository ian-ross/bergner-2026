---
id: TASK-035
title: Implement the browser model core and equilibrium solver
status: Done
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:36'
labels:
  - episode-007
  - typescript
  - numerics
dependencies:
  - TASK-032
  - TASK-034
references:
  - src/bergner_spichtinger_2026/core.py
  - src/bergner_spichtinger_2026/constants.py
  - episodes/007-limit-cycle-interactive-widget/outputs/reference_metadata.json
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement a readable TypeScript translation of the paper model and a dependency-light client-side positive-equilibrium solver. Establish units, parameter validation, and numerical equivalence against Episode 007 reference fixtures before adding time integration or UI behavior.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TypeScript modules implement coefficients, process terms, the full vector field, and the no-Evap_n canonical model with notation traceable to the Python core
- [x] #2 Inputs support the approved T, p, w, F, N_a, and Delta z ranges, convert N_a from cm^-3 at the UI boundary, and reject invalid values clearly
- [x] #3 The equilibrium solver works in positivity-preserving coordinates, uses a safeguarded strategy, and returns a positive low-residual equilibrium across deterministic canonical and boundary test cases
- [x] #4 Automated tests compare coefficients, process terms, vector fields, and equilibria with Python-generated fixtures at approximately 1e-10 where direct arithmetic permits and with documented solver tolerances otherwise
- [x] #5 The Vite/TypeScript test and build commands run without network access after dependencies are installed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Scaffold the episode-local vanilla TypeScript/Vite test workspace and establish module boundaries for units, parameters, constants, coefficients, process terms, vector field, and equilibrium solving.
2. Port the Python constants and no-Evap_n model equations into readable TypeScript with explicit SI internals and boundary conversion of N_a from cm^-3.
3. Add parameter-domain validation for the approved T, p, w, F, N_a, and Delta z ranges and precise errors for invalid numerical inputs.
4. Implement the positive equilibrium solve in log(n), log(q), s coordinates using a bracketed scalar seed followed by safeguarded residual refinement and convergence diagnostics.
5. Derive deterministic fixtures from the Episode 007 reference artifacts and compare constants, terms, vector fields, residuals, and equilibria with Python at arithmetic-appropriate tolerances.
6. Run TypeScript tests and a production build offline after dependency installation; document any deliberate numerical differences.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Implemented the episode-local Vite/TypeScript browser model core, validation boundary, Python-derived fixtures, and safeguarded log-coordinate equilibrium solver.
- Verified npm test/build both normally and offline after installation; ran the full Python pytest suite (107 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the Episode 007 browser model core and positive-equilibrium solver.

Changes:
- Added an episode-local Vite/TypeScript workspace with SI model constants, coefficients, no-Evap_n process terms, vector field, UI-boundary validation, and a safeguarded log-coordinate equilibrium solve.
- Added reproducible Python fixture generation plus deterministic canonical and supported-domain-boundary equivalence tests.
- Documented arithmetic and solver tolerances and offline workspace verification.

Validation:
- npm test (14 passed)
- npm run build
- npm ci --offline, npm test, npm run build
- uv run pytest (107 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
