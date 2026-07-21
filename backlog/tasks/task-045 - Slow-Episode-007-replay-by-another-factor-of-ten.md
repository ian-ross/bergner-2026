---
id: TASK-045
title: Slow Episode 007 replay by another factor of ten
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:07'
updated_date: '2026-07-21 20:07'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce the Episode 007 replay rate to one tenth of its current speed at every playback setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every replay speed setting advances ten times more slowly than before
- [ ] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reduce the shared replay increment by a factor of ten.
2. Update replay-rate regression expectations.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->
