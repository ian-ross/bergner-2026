---
id: TASK-056
title: Validate Python fixed-mesh midpoint periodic-orbit solves
status: To Do
assignee: []
created_date: '2026-08-12 12:52'
labels:
  - episode-008
  - python
  - numerics
dependencies:
  - TASK-055
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Demonstrate fixed-parameter periodic-orbit correction from the frozen seed and quantify midpoint period/orbit convergence on uniform meshes without claiming production accuracy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 SciPy sparse least-squares corrects the canonical orbit at N=64 with independently accepted stage, update, and phase residual blocks
- [ ] #2 Uniform N=32, 64, 128, and 256 midpoint results report period, weighted orbit change, residuals, phase energy, solver evaluations, and comparison with the Episode 007 reference cycle
- [ ] #3 The results explicitly distinguish discrete nonlinear convergence from period and continuous-orbit accuracy
- [ ] #4 Failed or nominally successful SciPy solves that miss block tolerances are rejected with diagnostics
- [ ] #5 Curated fixed-mesh reference vectors and residuals are frozen for later Python-to-C++ parity tests
<!-- AC:END -->
