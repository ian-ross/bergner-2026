---
id: TASK-040
title: Show two cycles in Episode 007 budget figure
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 10:44'
updated_date: '2026-07-21 10:47'
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
- [x] #1 The curated state/process-budget figure displays two consecutive complete late cycles on one synchronized time axis
- [x] #2 The rapid transition appears at the internal cycle boundary rather than only being split across the plot edges
- [x] #3 The separate color-coded n, q, and s axes and shared per-equation budget scales are preserved
- [x] #4 A clean notebook execution regenerates the figure without changing numerical CSV or JSON reference artifacts
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the representative-window extraction from the final complete cycle to the final two consecutive complete cycles, including interpolated boundary samples.
2. Keep the existing four synchronized panels and axis semantics, update the title/x-axis wording to two cycles, and mark the internal cycle boundary with a subtle vertical guide.
3. Update the notebook regression contract to require a two-cycle window and preserve the three state axes plus shared budget scales.
4. Clean-execute the notebook, visually inspect the regenerated figure, verify numerical CSV/JSON hashes are unchanged, and run focused and full tests.
5. Record results and close TASK-040.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Combined the final two complete extracted cycles into one continuous representative window, dropping the duplicate shared-boundary sample.
- Updated the title and time-axis wording and added a subtle dotted guide at the internal cycle boundary across all four synchronized panels.
- Preserved the independent color-coded n/q/s axes and common per-equation process-budget scales.
- Clean-executed and visually inspected the regenerated figure. SHA-256 hashes of reference_trajectory.csv, per_cycle_summary.csv, and reference_metadata.json remain unchanged.
- Focused tests pass (2); full repository suite passes (107, with 3 pre-existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended the Episode 007 representative state/process-budget figure from one late limit cycle to two consecutive complete cycles. The rapid activation transition is now visible around the internal cycle boundary rather than split only across the left and right edges; a subtle synchronized guide marks that boundary in every panel.

Preserved the independently scaled, color-coded n/q/s axes and the physically meaningful common scale within each process budget. The clean notebook run regenerated only the figure content; numerical CSV and JSON reference artifacts are byte-for-byte unchanged.

Tests:
- uv run pytest -q tests/test_episode7_diagnostics_notebook.py (2 passed)
- uv run pytest -q (107 passed; 3 pre-existing numerical overflow warnings)
- git diff --check
<!-- SECTION:FINAL_SUMMARY:END -->
