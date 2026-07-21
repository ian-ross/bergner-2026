---
id: TASK-049
title: Simplify Episode 007 controls and result text
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:38'
updated_date: '2026-07-21 20:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove the aerosol concentration slider, keep its Figure 4 default fixed internally, and remove completion/equilibrium result text from the widget.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The N_a control is absent and integrations always use the default 10000 cm^-3 value
- [ ] #2 The widget does not display Integration complete or Equilibrium result lines
- [ ] #3 Relevant documentation and accessibility tests reflect the simplified interface
- [ ] #4 Web tests and production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Remove the N_a markup and bind model input to the fixed Figure 4 default.
2. Remove equilibrium display handling and clear/hide completion status.
3. Update tests and Episode 007 control documentation.
4. Run tests and the offline production build.
<!-- SECTION:PLAN:END -->
