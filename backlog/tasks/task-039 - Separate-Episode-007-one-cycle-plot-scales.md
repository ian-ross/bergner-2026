---
id: TASK-039
title: Separate Episode 007 one-cycle plot scales
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 10:33'
updated_date: '2026-07-21 10:33'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Capture the current failure with a deterministic notebook/source check and quantify each plotted series range from the existing final-cycle reference data.
2. Replace the four shared-scale axes with grouped small multiples: one independently scaled axis per state or process/tendency series, while sharing the one-cycle time axis and retaining physical units.
3. Add a regression contract that checks the required series are assigned separate axes and that labels/units remain explicit.
4. Clean-execute the notebook to regenerate the curated PNG and reference artifacts, then verify numerical CSV/JSON outputs are unchanged.
5. Run the focused regression test and repository test suite, visually inspect the regenerated figure, and update TASK-039 acceptance criteria, notes, and final summary.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reproduced the issue in the curated PNG and notebook plotting cell: four Matplotlib axes currently combine unlike quantities.
- Existing final-cycle ranges confirm the scale mismatch: n spans about 4.9e3–1.37e5, q 9.1e-7–1.08e-5, and s 1.36–1.48; nucleation mass/saturation terms are also orders of magnitude below other terms in their shared budget axes.
<!-- SECTION:NOTES:END -->
