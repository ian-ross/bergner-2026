---
id: TASK-061
title: Implement native LOCA midpoint periodic-orbit continuation
status: To Do
assignee: []
created_date: '2026-08-12 12:52'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
dependencies:
  - TASK-057
  - TASK-060
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use LOCA's native pseudo-arclength stepper around the sparse periodic-orbit base group on a fixed midpoint mesh, rather than a repository-owned parameter grid corrected through NOX.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 LOCA owns predictor, tangent, arclength constraint, adaptive step size, rejection, and retry while the mesh/layout is unchanged
- [ ] #2 The base group contains no duplicate arclength row and exposes normalized rho or T-hat through the parameter interface
- [ ] #3 Deterministic two-point bootstrap initializes each continuation direction and is recorded separately from native accepted steps
- [ ] #4 Native LOCA continues the T=225 K fixed-temperature move to the spine plus short spine and T=210 K slice segments in both directions
- [ ] #5 Fixed-mesh LOCA periods and weighted orbits agree with corresponding Python continuation segments within versioned tolerances
- [ ] #6 Continuation events distinguish accepted/rejected steps and controlled phase-reference refresh restarts
<!-- AC:END -->
