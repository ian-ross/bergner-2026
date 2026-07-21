---
id: TASK-052
title: Reposition Episode 007 replay help text
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:49'
updated_date: '2026-07-21 20:49'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move the Arrow keys scrub help text below the playback timeline and speed selector without increasing the timeline's maximum width.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Replay help appears below both the timeline and speed selector
- [ ] #2 The timeline does not grow beyond its current desktop length
- [ ] #3 The replay layout remains single-column on narrow screens
- [ ] #4 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reorder replay help markup after the speed selector.
2. Define a two-row replay grid with the existing timeline width capped.
3. Preserve the narrow-screen single-column layout.
4. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->
