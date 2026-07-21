---
id: TASK-052
title: Reposition Episode 007 replay help text
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:49'
updated_date: '2026-07-21 20:50'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Move the Arrow keys scrub help text below the playback timeline and speed selector without increasing the timeline's maximum width.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Replay help appears below both the timeline and speed selector
- [x] #2 The timeline does not grow beyond its current desktop length
- [x] #3 The replay layout remains single-column on narrow screens
- [x] #4 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reorder replay help markup after the speed selector.
2. Define a two-row replay grid with the existing timeline width capped.
3. Preserve the narrow-screen single-column layout.
4. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reordered replay markup so help follows the timeline and speed selector.
- Added a second replay-grid row spanning the timeline and speed columns.
- Capped the desktop timeline column at 58rem (928 px) and restored normal flow in the narrow layout.
- Headless Chromium at 1440 px measured a 928 px timeline and confirmed help begins below both controls.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Moved the Episode 007 “Arrow keys scrub…” help below the playback timeline and speed selector. The desktop timeline remains capped at its previous 58rem/928px length, while the mobile layout returns all replay elements to a single column. Headless Chromium verified the geometry; all 27 tests and the offline build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
