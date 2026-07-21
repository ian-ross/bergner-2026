---
id: TASK-044
title: Slow Episode 007 replay by another factor of five
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:05'
updated_date: '2026-07-21 20:05'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce the Episode 007 replay rate to one fifth of its current speed at every playback setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every replay speed setting advances five times more slowly than before
- [ ] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reduce the shared replay increment by a factor of five.
2. Update replay-rate regression expectations.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->
