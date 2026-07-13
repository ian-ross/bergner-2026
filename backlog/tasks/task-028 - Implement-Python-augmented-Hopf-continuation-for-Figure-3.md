---
id: TASK-028
title: Implement Python augmented Hopf continuation for Figure 3
status: To Do
assignee: []
created_date: '2026-07-13 16:05'
labels: []
dependencies: []
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
