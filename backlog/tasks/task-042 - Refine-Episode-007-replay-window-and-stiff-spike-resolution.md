---
id: TASK-042
title: Refine Episode 007 replay window and stiff spike resolution
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 19:51'
updated_date: '2026-07-21 19:51'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refine the improved Episode 007 widget by slowing replay, adding a moving five-period time window, reliably resolving narrow nucleation spikes, and using stable Figure 4 orbit bounds from the start.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Default replay advances approximately ten times more slowly than the current implementation at each displayed speed
- [ ] #2 Time-series plots default to a fixed window of approximately five Figure 4 oscillation periods and scroll to follow replay time
- [ ] #3 The production browser integration resolves recurring narrow Nuc_n spikes without sampling-beat height modulation
- [ ] #4 The orbit plot starts with fixed bounds that contain the Figure 4 preset orbit without rescaling
- [ ] #5 Web regression tests, production build, and browser smoke checks pass
<!-- AC:END -->
