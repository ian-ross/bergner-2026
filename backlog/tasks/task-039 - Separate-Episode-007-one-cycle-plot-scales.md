---
id: TASK-039
title: Separate Episode 007 one-cycle plot scales
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 10:33'
updated_date: '2026-07-21 10:40'
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
- [x] #1 The one-cycle figure gives n, q, and s independently scaled vertical axes with explicit units
- [x] #2 All state and budget views retain a synchronized one-cycle time axis and clear grouping by governing equation
- [x] #3 A clean notebook execution regenerates the curated figure and existing Episode 007 reference artifacts without changing numerical results
- [x] #4 The dn/dt, dq/dt, and ds/dt budget panels retain one shared vertical scale per governing equation so component sums remain physically interpretable
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

- Added two right-side twin axes to the existing state panel: q uses the first right axis and s uses an outward-offset second right axis; n remains on the left. Labels, ticks, offset text, and spines match each curve color.
- Left all three process-budget panels on their original shared per-equation scales.
- Clean-executed the notebook and visually inspected the regenerated 2000x2000 PNG. SHA-256 hashes for reference_trajectory.csv, per_cycle_summary.csv, and reference_metadata.json are unchanged.
- Added a notebook plotting contract regression check. Focused tests pass (2); full repository suite passes (107, with 3 pre-existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Reworked the Episode 007 one-cycle state panel so n, q, and s remain overlaid on the synchronized timeline while each uses an independently scaled, explicitly labeled y-axis. Axis labels, ticks, scientific-notation offset text, and spines are color-coded to their curves; the s axis is offset outward from the q axis for readability.

The dn/dt, dq/dt, and ds/dt panels deliberately retain one common scale per budget so component magnitudes and their sum remain physically interpretable. Regenerated the curated figure without changing any numerical CSV or JSON reference artifact.

Tests:
- uv run pytest -q tests/test_episode7_diagnostics_notebook.py (2 passed)
- uv run pytest -q (107 passed; 3 pre-existing numerical overflow warnings)
- git diff --check
<!-- SECTION:FINAL_SUMMARY:END -->
