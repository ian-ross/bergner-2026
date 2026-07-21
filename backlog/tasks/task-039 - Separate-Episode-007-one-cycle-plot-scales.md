---
id: TASK-039
title: Separate Episode 007 one-cycle plot scales
status: To Do
assignee: []
created_date: '2026-07-21 10:33'
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
Revise the Episode 007 representative-cycle state and process-budget figure so variables and process terms with very different magnitudes remain visible without implying that unlike physical quantities share one meaningful vertical scale.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The one-cycle figure gives n, q, and s independently scaled vertical axes with explicit units
- [ ] #2 Every required n, q, and s process term and total tendency remains visible on an independently appropriate vertical scale with explicit units
- [ ] #3 All state and budget views retain a synchronized one-cycle time axis and clear grouping by governing equation
- [ ] #4 A clean notebook execution regenerates the curated figure and existing Episode 007 reference artifacts without changing numerical results
<!-- AC:END -->
