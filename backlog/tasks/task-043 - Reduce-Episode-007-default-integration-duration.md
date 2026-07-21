---
id: TASK-043
title: Reduce Episode 007 default integration duration
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:03'
updated_date: '2026-07-21 20:03'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set the Episode 007 widget's default and Figure 4 preset integration duration to 60000 seconds.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The widget initializes and resets the Figure 4 preset duration to 60000 seconds
- [ ] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Change the preset duration constant to 60000 seconds.
2. Update the preset regression expectation.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->
