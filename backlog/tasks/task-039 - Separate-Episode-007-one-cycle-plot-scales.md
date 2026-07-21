---
id: TASK-039
title: Separate Episode 007 one-cycle plot scales
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 10:33'
updated_date: '2026-07-21 10:38'
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
- [ ] #2 All state and budget views retain a synchronized one-cycle time axis and clear grouping by governing equation
- [ ] #3 A clean notebook execution regenerates the curated figure and existing Episode 007 reference artifacts without changing numerical results
- [ ] #4 The dn/dt, dq/dt, and ds/dt budget panels retain one shared vertical scale per governing equation so component sums remain physically interpretable
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Capture the current failure with a deterministic notebook/source check and quantify the n, q, and s ranges from the existing final-cycle reference data.
2. Keep the synchronized four-panel layout, but give n, q, and s separate color-coded vertical axes in the first panel; position and label the axes so each curve can be read without obscuring the plot.
3. Preserve one shared vertical scale within each dn/dt, dq/dt, and ds/dt budget panel because each total is the physical sum of its displayed components.
4. Add a regression contract for the separate state axes, explicit units, and unchanged shared-scale budget structure.
5. Clean-execute the notebook, verify numerical CSV/JSON outputs are unchanged, run tests, visually inspect the figure, and close TASK-039.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reproduced the issue in the curated PNG and notebook plotting cell: four Matplotlib axes currently combine unlike quantities.
- Existing final-cycle ranges confirm the scale mismatch: n spans about 4.9e3–1.37e5, q 9.1e-7–1.08e-5, and s 1.36–1.48; nucleation mass/saturation terms are also orders of magnitude below other terms in their shared budget axes.

- User clarified the intended design: only the state panel needs separate scales. Budget components must remain on a common scale within each equation because their relative magnitudes and sums are physically meaningful.
- Revised the implementation from small multiples to three color-coded y-axes in the existing state panel.
<!-- SECTION:NOTES:END -->
