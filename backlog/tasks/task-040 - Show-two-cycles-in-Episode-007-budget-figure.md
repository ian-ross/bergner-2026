---
id: TASK-040
title: Show two cycles in Episode 007 budget figure
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 10:44'
updated_date: '2026-07-21 10:44'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the representative-window extraction from the final complete cycle to the final two consecutive complete cycles, including interpolated boundary samples.
2. Keep the existing four synchronized panels and axis semantics, update the title/x-axis wording to two cycles, and mark the internal cycle boundary with a subtle vertical guide.
3. Update the notebook regression contract to require a two-cycle window and preserve the three state axes plus shared budget scales.
4. Clean-execute the notebook, visually inspect the regenerated figure, verify numerical CSV/JSON hashes are unchanged, and run focused and full tests.
5. Record results and close TASK-040.
<!-- SECTION:PLAN:END -->
