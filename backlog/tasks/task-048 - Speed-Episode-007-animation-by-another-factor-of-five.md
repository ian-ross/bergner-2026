---
id: TASK-048
title: Speed Episode 007 animation by another factor of five
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:23'
updated_date: '2026-07-21 20:25'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Increase the corrected Episode 007 physical-time animation clock by a further factor of five.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The 1x animation rate is 750 model seconds per wall second and other settings scale proportionally
- [x] #2 Interface help, tests, and documentation state the new rate
- [x] #3 Web tests, production build, and browser timing check pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Increase the physical-time playback constant by 5x.
2. Update tests and user-facing documentation.
3. Run tests, build, and browser timing validation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Increased the physical-time rate from 150 to 750 model seconds per wall second.
- Updated UI help, tests, README, and planning decisions.
- Headless Chromium measured exactly 1500 model seconds over 2 wall seconds at 1x.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Increased the Episode 007 animation clock by another factor of five. The explicit 1x rate is now 750 model seconds per wall second, with other speed settings scaling proportionally. Updated tests and documentation; all 27 tests and the offline build pass. Headless Chromium confirmed exactly 750 model seconds per wall second.
<!-- SECTION:FINAL_SUMMARY:END -->
