---
id: TASK-023
title: Implement LOCA Sacado physical Jacobian and eigenvalue workflow for Figure 2
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 12:25'
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
- [x] #1 C++ model exposes/evaluates the physical vector field separately from the log-coordinate continuation residual.
- [x] #2 Sacado computes the physical 3x3 Jacobian with respect to physical (n, q, s), distinct from the existing log-residual state Jacobian.
- [x] #3 LOCA-side executable computes physical eigenvalues backend-side, preferring Teuchos::LAPACK GEEV and documenting any direct LAPACK fallback.
- [x] #4 LOCA Figure 2 branch output includes backend-computed canonical physical eigenvalues, eigenvalue regime, and stability classification for at least 400 finite converged points across w = 0.0005--2.0 m s^-1 or documents a justified alternative sampling strategy.
- [x] #5 Diagnostic artifacts expose physical Jacobian entries for verification without cluttering the primary normalized branch CSV.
- [x] #6 Tests compare LOCA Sacado physical Jacobian and eigenvalues against the Python reference at representative states.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the current LOCA C++ model, Sacado residual Jacobian path, CMake/Trilinos configuration, and Teuchos availability.
2. Add a physical vector-field function in C++ that mirrors the Python physical ODE RHS separately from the log-coordinate continuation residual.
3. Add a Sacado physical Jacobian path differentiating the physical vector field with respect to physical (n,q,s), and expose CLI diagnostics for residual/Jacobian/eigenvalue checks.
4. Implement backend-side dense eigenvalue computation, preferring Teuchos::LAPACK GEEV and documenting/directly testing any fallback to LAPACK dgeev.
5. Extend the LOCA continuation output path for Figure 2 so each branch point includes backend-computed canonical eigenvalues, regime, stability classification, and separate raw physical-Jacobian diagnostics.
6. Add Python-side tests comparing LOCA physical Jacobian/eigenvalues to the shared Python reference at representative states and smoke-test the Figure 2 LOCA output schema/range.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added C++ physical_vector_field and physical-rhs/physical-jacobian/eigenvalues CLI commands.
- Added Sacado physical Jacobian d(dn/dt,dq/dt,ds/dt)/d(n,q,s), separate from log-coordinate state_jacobian.
- Added Teuchos::LAPACK GEEV physical eigenvalues, canonical ordering, eigenvalue regime, and stability classification to CLI and continuation raw output.
- Added Episode 5 LOCA Figure 2 orchestration script that writes dense branch/eigenvalue outputs plus a separate physical-Jacobian diagnostics CSV.
- Added tests comparing C++ RHS/Jacobian/eigenvalues to Python references and smoke-testing 400-point LOCA Figure 2 output.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the LOCA-side physical stability workflow for Figure 2.

Changes:
- Split the C++ model into a reusable physical vector field and the existing log-coordinate continuation residual.
- Added Sacado differentiation of the physical ODE Jacobian with respect to (n, q, s), exposed through CLI diagnostics and continuation raw output.
- Added Teuchos::LAPACK GEEV eigenvalue computation with canonical ordering, eigenvalue regime, and stability classification. No direct dgeev fallback was required for the configured Trilinos build.
- Added an Episode 5 LOCA orchestration script that generates at least 400 finite converged Figure 2 points over w=0.0005--2.0 m s^-1, primary branch/eigenvalue CSVs, metadata, summary JSON, and a separate physical-Jacobian diagnostics CSV.
- Added C++/Python comparison tests for physical RHS, Jacobian, and eigenvalues, plus smoke tests for the dense LOCA Figure 2 output contract.

Tests:
- uv run pytest -q

Result: 70 passed, 1 pre-existing RuntimeWarning from Python Figure 2 continuation overflow probing.
<!-- SECTION:FINAL_SUMMARY:END -->
