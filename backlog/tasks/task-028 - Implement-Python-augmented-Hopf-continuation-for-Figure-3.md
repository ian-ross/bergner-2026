---
id: TASK-028
title: Implement Python augmented Hopf continuation for Figure 3
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 16:35'
labels: []
dependencies:
  - TASK-026
  - TASK-027
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build reusable Python augmented Hopf continuation infrastructure and use it to compute the Figure 3 lower and upper Hopf loci over T=190--240 K. The nonlinear continuation variables should use log-state/log-w coordinates for conditioning while Hopf conditions use the physical ODE Jacobian in physical state coordinates.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reusable package infrastructure represents the augmented Hopf unknowns, residual equations, normalization, and previous-eigenvector phase condition with clear coordinate-system documentation.
- [ ] #2 Python workflow seeds both Hopf branches at T=230 K from the known Episode 005 crossings, then continues downward to 190 K and upward to 240 K.
- [ ] #3 Curated Python outputs include lower/upper Hopf rows with T_K, log_w, w_m_s, state, frequency, residual diagnostics, branch labels, convergence status, and method metadata.
- [ ] #4 Regression tests or smoke tests verify the T=230 K Hopf velocities agree with Episode 005 landmarks and that outputs span the requested temperature domain.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Design reusable Hopf data structures for packed unknowns: log_n, log_q, s, log_w, omega, real eigenvector, imaginary eigenvector, plus branch/phase metadata.
2. Implement augmented residual equations using the existing log-coordinate equilibrium residual and the physical ODE Jacobian evaluated after converting to physical state coordinates.
3. Implement initialization at T=230 K from existing Figure 2 Hopf estimates: solve equilibrium near each w, compute the physical eigenpair, rotate/normalize the eigenvector, and solve the initial augmented system.
4. Implement temperature continuation in both directions from T=230 K using predictor-corrector solves and previous-eigenvector phase alignment.
5. Add Episode 006 Python orchestration that writes normalized lower/upper Hopf locus CSV/JSON artifacts with residuals, frequency, state, convergence, and metadata.
6. Add tests for residual packing/unpacking, phase normalization, T=230 K anchor agreement, schema fields, and coverage of the 190--240 K domain.
<!-- SECTION:PLAN:END -->
