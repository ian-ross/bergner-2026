---
id: TASK-004
title: Produce Figure 1 reproduction plot and comparison summary
status: Done
assignee:
  - '@pi'
created_date: '2026-06-24 16:38'
updated_date: '2026-06-25 07:40'
labels: []
dependencies:
  - TASK-001
  - TASK-002
  - TASK-003
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Assemble the Episode 2 final reproduction artifact: generated Figure 1-style plot, overlays/comparisons against digitized paper curves, and a concise interpretation note.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Curated reproduction plot matches Figure 1 layout with n, q, and s panels, log-scaled w axis, and T=190/210/230 K color mapping.
- [x] #2 Generated continuation, analytic approximation, and digitized paper curves are compared in plots or residual/error panels.
- [x] #3 Episode 2 README/doc note describes source provenance, numerical method, digitization method, outputs, and known limitations.
- [x] #4 All relevant tests and reproduction scripts run successfully via documented uv commands.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Load Episode 2 continuation, root-solve, analytic approximation, and digitized Figure 1 outputs.
2. Generate a Figure 1-style three-panel reproduction using the paper color mapping and log-scaled w axis.
3. Add comparison overlays or error summaries between generated continuation, analytic approximation, and digitized paper curves.
4. Write a concise Episode 2 README/doc note covering provenance, numerical method, digitization method, outputs, commands, and limitations.
5. Run tests and documented reproduction commands, then record results in the task final summary when implementation is complete.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added scripts/plot_figure1_reproduction.py to assemble the final Figure 1 overlay and residual artifacts.
- Generated outputs/figure1_reproduction/ with reproduction PNG, digitized residual PNG, comparison CSVs, and run metadata.
- Updated Episode 2 README with provenance, methods, outputs, limitations, and uv reproduction commands.
- Verified documented commands: continuation generation, digitization, reproduction plotting, and uv run pytest (11 passed).

- Follow-up: diagnosed saturation-ratio offset as an undeclared Figure 1 aerosol assumption. Updated Episode 2 Figure 1 generation to use `N_a = 1.0e10 m^-3` (`10000 cm^-3`) explicitly, regenerated continuation/reproduction outputs, and added `docs/REPRODUCTION_NOTES.md` linked from `AGENTS.md`.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Produced the Episode 2 Figure 1 reproduction artifact and documentation.

Changes:
- Added `episodes/002-figure1-python-continuation/scripts/plot_figure1_reproduction.py`, which overlays Python continuation, Eq. 92--94 analytic approximation, independent root-solve checks, and digitized paper curves in the three-panel Figure 1 layout.
- Wrote curated outputs under `episodes/002-figure1-python-continuation/outputs/figure1_reproduction/`: `figure1_reproduction.png`, `figure1_digitized_residuals.png`, comparison detail/summary CSVs, and run metadata.
- Expanded the Episode 2 README with uv reproduction commands, source provenance, numerical and digitization methods, output descriptions, and known limitations.

Verification:
- `uv run python episodes/002-figure1-python-continuation/scripts/generate_figure1_continuation.py`
- `uv run python episodes/002-figure1-python-continuation/scripts/extract_digitize_figure1.py`
- `uv run python episodes/002-figure1-python-continuation/scripts/plot_figure1_reproduction.py`
- `uv run pytest` (11 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
