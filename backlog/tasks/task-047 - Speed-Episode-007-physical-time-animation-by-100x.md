---
id: TASK-047
title: Speed Episode 007 physical-time animation by 100x
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:21'
updated_date: '2026-07-21 20:21'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Increase the corrected Episode 007 physical-time animation clock by a factor of 100.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The 1x animation rate is 150 model seconds per wall second and other settings scale proportionally
- [ ] #2 Interface help and Episode 007 documentation state the corrected rate
- [ ] #3 Web tests, production build, and browser timing check pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Increase the physical-time playback constant by 100x.
2. Update rate tests and user-facing documentation.
3. Run tests, build, and a browser timing check.
<!-- SECTION:PLAN:END -->
