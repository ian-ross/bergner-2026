---
id: TASK-075
title: Execute full-domain native adaptive continuation and sampling refinement
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 10:49'
labels:
  - episode-008
  - loca
  - adaptivity
  - production
dependencies:
  - TASK-069
  - TASK-070
  - TASK-071
  - TASK-073
  - TASK-081
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After the measured pilot gate passes, run authoritative native adaptive continuation over the Figure 5 temperature/rho domain and refine canonical scientific sampling from observed errors and terminal statuses.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run covers the approved T=190--240 K domain, exact 225 K anchor, spine points, rho anchors, and any additional solves required by accepted pilot/full-domain evidence, with one terminal status per requested target
- [ ] #2 Accepted points pass production residual, phase, positivity, linear, defect, period/orbit convergence, remesh/restart, and provenance gates; unresolved or failed regions remain explicit gaps
- [ ] #3 Holdout-driven sampling refinement records along-slice and between-slice log-period errors and adds authoritative solves near failures without crossing Hopf boundaries, tripwires, instability checkpoints, or unresolved gaps
- [ ] #4 Curated scalar/event/checkpoint/orbit artifacts are schema-valid, restartable, measured, and linked from Episode 008 documentation
<!-- AC:END -->
