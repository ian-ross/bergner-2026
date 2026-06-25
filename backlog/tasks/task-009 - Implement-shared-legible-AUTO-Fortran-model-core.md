---
id: TASK-009
title: Implement shared legible AUTO Fortran model core
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a top-level shared AUTO Fortran implementation of the Bergner & Spichtinger model core, organized for legibility and cross-comparison with the Python code before episode-specific AUTO continuation runs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Top-level auto/ shared source files define constants, environment parameters, coefficient calculations, process terms, vector field, and log-coordinate equilibrium residuals.
- [ ] #2 Fortran comments and naming cross-reference the Python implementation and paper equations to the same documentation standard as the Python model core.
- [ ] #3 The shared Fortran model exposes a small driver or callable path that can evaluate selected model quantities without running AUTO continuation.
- [ ] #4 Build/run instructions for the shared Fortran model work with /usr/local/bin/auto and gfortran available on the system.
<!-- AC:END -->
