---
id: TASK-041
title: Improve Episode 007 live widget numerics and layout
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 16:38'
updated_date: '2026-07-21 16:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Improve the Episode 007 browser widget so its numerical trajectory is reliable at production settings, integration is visible while running, controls are compact, and the orbit view remains geometrically stable during replay.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The production widget uses a validated adaptive integration profile and accurate interpolation rather than coarse duration-scaled stepping
- [ ] #2 Trajectory samples stream to the plots during integration and remain available for replay after completion
- [ ] #3 Form controls use compact single-line variable/unit labels without expanding across excessive width
- [ ] #4 The orbit plot has a stable near-square panel and does not change ranges or size during replay
- [ ] #5 Web tests and offline production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a shared, production-tested adaptive integration profile and higher-order output interpolation.
2. Extend the worker protocol to stream equilibrium and sample batches, and render those batches live.
3. Separate full plot updates from lightweight replay cursor updates; fix orbit ranges and panel geometry.
4. Compact control markup and responsive CSS.
5. Add regression tests, run the web suite/build, update Episode 007 documentation, and record completion.
<!-- SECTION:PLAN:END -->
