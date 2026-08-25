---
id: TASK-078
title: Run stratified independent IVP validation for production points
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 12:43'
labels:
  - episode-008
  - ivp
  - validation
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
  - TASK-077
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Validate selected accepted native production periodic orbits with independent IVP integrations after full-domain continuation exposes the actual worst cases.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At least the documented twelve unique validation categories are selected after deduplication, including qualification points, T=210 K Hopf sides where available, low/high-temperature interiors, largest/shortest periods, worst accepted defect, worst Floquet trivial multiplier, and worst interpolation holdout
- [ ] #2 Every selected point receives DOP853 one-period return and phase-aligned trajectory validation with period, return, and weighted-orbit errors below the documented gates or explicit failure reasons
- [ ] #3 The six hardest/headline points receive IVP Radau agreement checks and at least four receive perturbed-equilibrium attractor checks as documented
- [ ] #4 Validation outcomes remain independent evidence and cannot tune or overwrite native continuation periods
<!-- AC:END -->
