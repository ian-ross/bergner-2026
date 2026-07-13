---
id: TASK-021
title: Implement Python Figure 2 eigenvalue reproduction
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
labels:
  - episode-005
  - figure2
  - eigenvalues
  - python
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the Python-native Figure 2 equilibrium branch and physical eigenvalues over the paper range w = 0.0005--2.0 m s^-1 for p = 300 hPa, T = 230 K, F = 1, N_a = 1.0e10 m^-3. Use the shared physical Jacobian/eigenvalue infrastructure as the semantic reference.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Script generates a dense log-w branch with at least 400 finite converged points across w = 0.0005--2.0 m s^-1.
- [ ] #2 Output CSV includes equilibrium state, residual/convergence diagnostics, canonical physical eigenvalues, eigenvalue regime, and stability classification.
- [ ] #3 Python outputs include simple Hopf crossing estimates near the paper-described crossings around w ≈ 0.048 and w ≈ 0.77 m s^-1, within documented numerical tolerance.
- [ ] #4 A draft Figure 2-style plot shows real eigenvalue parts and imaginary eigenvalue parts versus log-scaled w.
- [ ] #5 Run metadata records parameter values, N_a assumption, grid density, Jacobian method, eigenvalue sorting tolerance, and commands.
<!-- AC:END -->
