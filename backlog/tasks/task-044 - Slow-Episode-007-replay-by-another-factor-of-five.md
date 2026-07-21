---
id: TASK-044
title: Slow Episode 007 replay by another factor of five
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:05'
updated_date: '2026-07-21 20:06'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce the Episode 007 replay rate to one fifth of its current speed at every playback setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every replay speed setting advances five times more slowly than before
- [x] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reduce the shared replay increment by a factor of five.
2. Update replay-rate regression expectations.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reduced the shared replay increment from 1/10 to 1/50 of the original calibrated rate.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slowed every Episode 007 playback speed setting by a further factor of five. Updated replay-rate regression expectations; all 27 tests and the offline production build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
