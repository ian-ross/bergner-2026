---
id: TASK-025
title: Implement full NOX/LOCA backend for validated C++ model
status: To Do
assignee: []
created_date: '2026-07-13 14:48'
updated_date: '2026-07-13 16:05'
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
- [ ] #1 NOX/LOCA residual, parameter-continuation, and solver interfaces are implemented for the validated small model without changing the physical equations or curated output schema semantics.
- [ ] #2 The full NOX/LOCA backend reproduces at least one existing Python/AUTO/Trilinos-side C++ curated continuation/eigenvalue artifact within documented tolerances.
- [ ] #3 Documentation clearly compares the lightweight Trilinos-side C++ backend with the full NOX/LOCA backend, including API complexity, diagnostics, and what LOCA adds for this problem.
- [ ] #4 Tests or opt-in smoke checks cover build availability, residual/Jacobian consistency, and normalized output compatibility while skipping cleanly when NOX/LOCA dependencies are unavailable.
<!-- AC:END -->
