---
id: TASK-035
title: Implement the browser model core and equilibrium solver
status: To Do
assignee: []
created_date: '2026-07-20 20:54'
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
- [ ] #1 TypeScript modules implement coefficients, process terms, the full vector field, and the no-Evap_n canonical model with notation traceable to the Python core
- [ ] #2 Inputs support the approved T, p, w, F, N_a, and Delta z ranges, convert N_a from cm^-3 at the UI boundary, and reject invalid values clearly
- [ ] #3 The equilibrium solver works in positivity-preserving coordinates, uses a safeguarded strategy, and returns a positive low-residual equilibrium across deterministic canonical and boundary test cases
- [ ] #4 Automated tests compare coefficients, process terms, vector fields, and equilibria with Python-generated fixtures at approximately 1e-10 where direct arithmetic permits and with documented solver tolerances otherwise
- [ ] #5 The Vite/TypeScript test and build commands run without network access after dependencies are installed
<!-- AC:END -->
