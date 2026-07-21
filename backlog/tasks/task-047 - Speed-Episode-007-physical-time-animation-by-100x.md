---
id: TASK-047
title: Speed Episode 007 physical-time animation by 100x
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:21'
updated_date: '2026-07-21 20:22'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Increase the corrected Episode 007 physical-time animation clock by a factor of 100.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The 1x animation rate is 150 model seconds per wall second and other settings scale proportionally
- [x] #2 Interface help and Episode 007 documentation state the corrected rate
- [x] #3 Web tests, production build, and browser timing check pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Increase the physical-time playback constant by 100x.
2. Update rate tests and user-facing documentation.
3. Run tests, build, and a browser timing check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Increased the shared physical-time rate from 1.5 to 150 model seconds per wall second.
- Updated UI help, tests, README, and planning decisions.
- Headless Chromium measured exactly 300 model seconds over 2 wall seconds at 1x.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Increased the corrected Episode 007 animation clock by 100x. The explicit 1x rate is now 150 model seconds per wall second, with 0.25x and 4x scaling proportionally. Updated interface help and documentation; all 27 tests and the offline build pass. Headless Chromium measured exactly 150 model seconds per wall second.
<!-- SECTION:FINAL_SUMMARY:END -->
