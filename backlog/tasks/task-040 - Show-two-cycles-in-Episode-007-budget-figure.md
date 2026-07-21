---
id: TASK-040
title: Show two cycles in Episode 007 budget figure
status: To Do
assignee: []
created_date: '2026-07-21 10:44'
labels:
  - episode-007
  - science
  - notebook
  - visualization
dependencies: []
references:
  - >-
    episodes/007-limit-cycle-interactive-widget/notebooks/01_limit_cycle_diagnostics.ipynb
  - >-
    episodes/007-limit-cycle-interactive-widget/outputs/one_cycle_state_process_budgets.png
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the Episode 007 representative state and process-budget figure from one complete late limit cycle to two consecutive complete cycles so the rapid cycle-boundary transition appears within the plotted time window.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The curated state/process-budget figure displays two consecutive complete late cycles on one synchronized time axis
- [ ] #2 The rapid transition appears at the internal cycle boundary rather than only being split across the plot edges
- [ ] #3 The separate color-coded n, q, and s axes and shared per-equation budget scales are preserved
- [ ] #4 A clean notebook execution regenerates the figure without changing numerical CSV or JSON reference artifacts
<!-- AC:END -->
