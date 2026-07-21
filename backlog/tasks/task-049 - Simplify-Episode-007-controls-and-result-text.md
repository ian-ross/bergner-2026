---
id: TASK-049
title: Simplify Episode 007 controls and result text
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:38'
updated_date: '2026-07-21 20:40'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove the aerosol concentration slider, keep its Figure 4 default fixed internally, and remove completion/equilibrium result text from the widget.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The N_a control is absent and integrations always use the default 10000 cm^-3 value
- [x] #2 The widget does not display Integration complete or Equilibrium result lines
- [x] #3 Relevant documentation and accessibility tests reflect the simplified interface
- [x] #4 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Remove the N_a markup and bind model input to the fixed Figure 4 default.
2. Remove equilibrium display handling and clear/hide completion status.
3. Update tests and Episode 007 control documentation.
4. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Removed the N_a range control and fixed browser runs to the Figure 4 default of 10000 cm^-3.
- Removed the equilibrium result element and clear/hide status text when integration completes.
- Updated accessibility assertions, README, browser-core notes, and planning decisions.
- `npm test` passes 27 tests and the offline production build passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Simplified the Episode 007 interface by removing the aerosol concentration slider and result-summary text. Browser integrations now always use the canonical N_a=10000 cm^-3 value. Equilibrium output is no longer rendered, and the transient status line clears and collapses when integration completes. Updated tests and documentation; all 27 tests and the offline build pass.
<!-- SECTION:FINAL_SUMMARY:END -->
