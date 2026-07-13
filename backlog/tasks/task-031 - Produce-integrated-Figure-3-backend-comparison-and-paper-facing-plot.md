---
id: TASK-031
title: Produce integrated Figure 3 backend comparison and paper-facing plot
status: To Do
assignee: []
created_date: '2026-07-13 16:05'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Combine Python augmented Hopf, AUTO native Hopf, and LOCA Hopf outputs into integrated Figure 3 comparison artifacts. Produce a paper-facing T--w Hopf-locus plot with backend overlays and Table II fit curves, plus numeric backend-to-backend and backend-to-fit diagnostics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Integrated comparison reads normalized outputs from all available Figure 3 backends and preserves backend/method provenance in merged CSV/JSON artifacts.
- [ ] #2 Paper-facing plot shows lower and upper Hopf loci over T=190--240 K on a log-w axis, overlays Table II fit curves, and distinguishes backend-computed loci from paper fit references.
- [ ] #3 Summary artifacts report backend-to-backend differences, backend-to-Table-II-fit differences, T=230 K anchor comparisons, missing/failed points, and known caveats.
- [ ] #4 Tests or smoke checks verify comparison artifacts and plot are generated from representative backend outputs and that schema assumptions are enforced.
<!-- AC:END -->
