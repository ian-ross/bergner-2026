---
id: TASK-011
title: Implement AUTO Figure 1 log-w continuation
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 10:01'
labels: []
dependencies:
  - TASK-009
  - TASK-010
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the shared Fortran model core to run AUTO-07p equilibrium continuation for the Figure 1 branch family, continuing log(w) for p=300 hPa, F=1, T in {190,210,230} K, and high Figure 1 aerosol concentration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Episode 3 AUTO problem/run files use the shared Fortran model core and represent equilibria of the transformed ODE system in (log n, log q, s).
- [x] #2 AUTO continues log_w over the full w range [0.005, 2.0] m/s for T=190, 210, and 230 K.
- [x] #3 Python orchestration records AUTO path/version, gfortran version, command lines, run files, and raw AUTO outputs under Episode 3 outputs.
- [x] #4 Run diagnostics make branch truncation, convergence failures, or unexpected AUTO labels visible rather than silently ignored.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review AUTO-07p expectations for equilibrium continuation problem files and identify the minimal run-file structure needed for IPS=1 steady-state continuation.
2. Add Episode 3 AUTO problem/run files under episodes/003-figure1-auto-continuation/auto/ that call the shared Fortran model core rather than duplicating physics.
3. Represent the AUTO state as (log_n, log_q, s) and use PAR(log_w) as the continuation parameter, computing w=exp(log_w) internally.
4. Write Python orchestration to run /usr/local/bin/auto for T=190, 210, and 230 K with p=300 hPa, F=1, N_a=1e10 m^-3, and log_w spanning the Figure 1 range.
5. Capture raw AUTO outputs, command lines, AUTO/gfortran version information, and run metadata in Episode 3 outputs.
6. Add diagnostic checks for branch coverage, convergence labels, and silent truncation before downstream parsing.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added Episode 3 AUTO templates and Python orchestration for log_w continuation using the shared Fortran model core.
- Generated curated Episode 3 AUTO outputs for T=190, 210, and 230 K over w=[0.005, 2.0] m/s with raw AUTO b/s/d files and run diagnostics.
- Added tests covering template semantics, diagnostics/range clipping, and an AUTO smoke run; full uv run pytest passes (24 passed).
<!-- SECTION:NOTES:END -->
