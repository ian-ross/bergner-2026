---
id: TASK-025
title: Implement full NOX/LOCA backend for validated C++ model
status: To Do
assignee: []
created_date: '2026-07-13 14:48'
updated_date: '2026-07-13 16:06'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory available Trilinos/NOX/LOCA headers, libraries, examples, and current CMake configuration; document skip conditions for environments without full LOCA support.
2. Design a minimal NOX/LOCA problem wrapper around the validated C++ model, preserving the existing equations, log-state/log-w parameterization, and physical-state conversion conventions.
3. Implement NOX residual/Jacobian interfaces and parameter plumbing for log_w, T, and other fixed environment fields without changing existing lightweight CLI behavior.
4. Validate equilibrium continuation first against an existing curated artifact, preferably a Figure 1 or Figure 2 branch, and write normalized outputs compatible with current schemas.
5. Add residual/Jacobian consistency checks and opt-in smoke tests that skip cleanly when NOX/LOCA dependencies are unavailable.
6. Document what the full NOX/LOCA backend adds relative to the lightweight C++ backend, including API complexity, diagnostics, and remaining limitations for Hopf continuation.
<!-- SECTION:PLAN:END -->
