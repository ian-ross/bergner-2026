---
id: TASK-050
title: Remove unsupported Episode 007 initial and advanced controls
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:43'
updated_date: '2026-07-21 20:45'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove the non-working s +1% initial condition and the Advanced controls section, fixing pressure and layer depth at their Figure 4 defaults.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The s +1% initial-condition option is absent and rejected by control validation
- [x] #2 The Advanced controls section is absent
- [x] #3 Pressure and layer depth remain fixed at 300 hPa and 100 m
- [x] #4 Documentation and tests reflect the reduced control surface
- [x] #5 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Remove the s-start and advanced-control markup.
2. Narrow start-option types and bind p/Delta z to canonical defaults.
3. Update tests and Episode 007 documentation.
4. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Removed the s +1% radio option and narrowed start-option types/validation to paper, n, and q.
- Removed the Advanced controls markup and fixed p=300 hPa and Delta z=100 m in browser control collection.
- Updated accessibility assertions, README, and planning decisions.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Reduced the Episode 007 control surface by removing the unsupported s +1% initial condition and the complete Advanced controls section. Browser runs now fix pressure and layer depth at the Figure 4 defaults (300 hPa and 100 m), while supported initial conditions are paper, n +1%, and q +1%. Updated types, validation, tests, and documentation; all 27 tests and the offline build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
