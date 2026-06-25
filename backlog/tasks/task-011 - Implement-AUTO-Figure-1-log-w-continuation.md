---
id: TASK-011
title: Implement AUTO Figure 1 log-w continuation
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the shared Fortran model core to run AUTO-07p equilibrium continuation for the Figure 1 branch family, continuing log(w) for p=300 hPa, F=1, T in {190,210,230} K, and high Figure 1 aerosol concentration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 3 AUTO problem/run files use the shared Fortran model core and represent equilibria of the transformed ODE system in (log n, log q, s).
- [ ] #2 AUTO continues log_w over the full w range [0.005, 2.0] m/s for T=190, 210, and 230 K.
- [ ] #3 Python orchestration records AUTO path/version, gfortran version, command lines, run files, and raw AUTO outputs under Episode 3 outputs.
- [ ] #4 Run diagnostics make branch truncation, convergence failures, or unexpected AUTO labels visible rather than silently ignored.
<!-- AC:END -->
