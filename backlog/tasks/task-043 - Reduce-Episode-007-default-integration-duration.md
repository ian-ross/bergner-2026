---
id: TASK-043
title: Reduce Episode 007 default integration duration
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:03'
updated_date: '2026-07-21 20:04'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set the Episode 007 widget's default and Figure 4 preset integration duration to 60000 seconds.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The widget initializes and resets the Figure 4 preset duration to 60000 seconds
- [x] #2 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Change the preset duration constant to 60000 seconds.
2. Update the preset regression expectation.
3. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Changed the Figure 4 preset/default integration duration from 239118.0583 s to 60000 s.
- `npm test` passes 27 tests and `npm run build` passes TypeScript, Vite, and offline verification.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Reduced the Episode 007 widget default and Figure 4 preset integration duration to 60,000 seconds. Updated the preset regression test; all 27 web tests and the offline production build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
