---
id: TASK-023
title: Implement LOCA Sacado physical Jacobian and eigenvalue workflow for Figure 2
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
labels:
  - episode-005
  - figure2
  - eigenvalues
  - loca
  - cpp
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the LOCA-side C++ executable so transformed-coordinate continuation can still report physical ODE stability data at each branch point. The physical Jacobian must be differentiated backend-side with Sacado with respect to physical variables (n, q, s), and eigenvalues should be computed in the LOCA-side executable using Teuchos/LAPACK if available.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C++ model exposes/evaluates the physical vector field separately from the log-coordinate continuation residual.
- [ ] #2 Sacado computes the physical 3x3 Jacobian with respect to physical (n, q, s), distinct from the existing log-residual state Jacobian.
- [ ] #3 LOCA-side executable computes physical eigenvalues backend-side, preferring Teuchos::LAPACK GEEV and documenting any direct LAPACK fallback.
- [ ] #4 LOCA Figure 2 branch output includes backend-computed canonical physical eigenvalues, eigenvalue regime, and stability classification for at least 400 finite converged points across w = 0.0005--2.0 m s^-1 or documents a justified alternative sampling strategy.
- [ ] #5 Diagnostic artifacts expose physical Jacobian entries for verification without cluttering the primary normalized branch CSV.
- [ ] #6 Tests compare LOCA Sacado physical Jacobian and eigenvalues against the Python reference at representative states.
<!-- AC:END -->
