---
id: TASK-022
title: Implement AUTO Figure 2 continuation and eigenvalue workflow
status: To Do
assignee: []
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 11:15'
labels:
  - episode-005
  - figure2
  - eigenvalues
  - auto
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run an independent AUTO-based equilibrium continuation for the Figure 2 parameter slice and produce normalized eigenvalue outputs. Investigate AUTO-native stability/eigenvalue support, but allow fallback to the shared Python analytic physical eigenvalue calculator if native output proves awkward.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AUTO workflow generates an independent equilibrium branch over w = 0.0005--2.0 m s^-1 with adequate coverage for Figure 2 comparison.
- [ ] #2 Normalized AUTO output includes equilibrium state, residual/convergence diagnostics, canonical physical eigenvalues, eigenvalue regime, and stability classification.
- [ ] #3 The task documents what AUTO-native eigenvalue or stability output was investigated and why the chosen production path was used.
- [ ] #4 If Python analytic eigenvalues are used as fallback, metadata clearly labels them as post-processed from AUTO equilibria rather than AUTO-native eigenvalues.
- [ ] #5 AUTO Hopf zero-crossing estimates are computed from the produced eigenvalue data and included in summary artifacts.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review Episode 3 AUTO Figure 1 run files and scripts to clone/adapt the log-w equilibrium continuation setup for the single Figure 2 parameter slice and extended w range.
2. Investigate AUTO-native stability/eigenvalue output options for this equilibrium problem and record findings in Episode 5 docs/metadata.
3. Implement the AUTO run/normalization script to generate an independent branch with residual/convergence diagnostics and adequate range coverage.
4. If AUTO-native eigenvalues are not practical, post-process AUTO equilibria with the shared Python physical_jacobian/physical_eigenvalues APIs and clearly label the method as fallback.
5. Compute AUTO zero-crossing estimates, write normalized CSV/summary/metadata, and add tests or smoke checks for schema, fallback labeling, and range coverage.
<!-- SECTION:PLAN:END -->
