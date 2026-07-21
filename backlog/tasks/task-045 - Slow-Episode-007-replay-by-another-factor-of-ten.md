---
id: TASK-045
title: Slow Episode 007 replay by another factor of ten
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:07'
updated_date: '2026-07-21 20:08'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Reduce the Episode 007 replay rate to one tenth of its current speed at every playback setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every replay speed setting advances ten times more slowly than before
- [x] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reduce the shared replay increment by a factor of ten.
2. Update replay-rate regression expectations.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reduced the shared replay increment by another factor of ten, from 1/50 to 1/500 of the original calibrated rate.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slowed every Episode 007 playback speed setting by another factor of ten. Updated replay-rate regression expectations; all 27 tests and the offline production build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
