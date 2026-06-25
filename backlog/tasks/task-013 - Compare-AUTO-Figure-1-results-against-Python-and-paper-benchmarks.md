---
id: TASK-013
title: Compare AUTO Figure 1 results against Python and paper benchmarks
status: Done
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 10:11'
labels: []
dependencies:
  - TASK-012
  - TASK-002
  - TASK-003
  - TASK-004
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Produce Episode 3 comparison artifacts showing how AUTO Figure 1 continuation agrees with Episode 2 Python continuation, Eq. 92--94 approximations, independent checks where useful, and digitized paper curves.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Comparison tables report AUTO-vs-Python differences for n, q, and s after interpolation onto a common log_w grid or sampled points.
- [x] #2 Comparison outputs include AUTO-vs-Eq. 92--94 and AUTO-vs-digitized Figure 1 summaries where the Episode 2 artifacts are available.
- [x] #3 Curated Episode 3 plots show AUTO branches in the Figure 1 three-panel layout and make backend comparisons visually inspectable.
- [x] #4 Episode 3 README documents commands, source provenance, AUTO method, comparison results, tolerances, limitations, and implications for later AUTO/LOCA work.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Load Episode 3 normalized AUTO branches plus Episode 2 Python continuation, Eq. 92--94 approximation, and digitized Figure 1 artifacts.
2. Interpolate AUTO and Python branches onto a common log_w grid or compare at sampled AUTO points, using log-space interpolation for positive n and q.
3. Produce detailed and summary tables for AUTO-vs-Python differences in n, q, and s, flagging but not hard-failing first-pass tolerance targets.
4. Produce AUTO-vs-Eq. 92--94 and AUTO-vs-digitized summaries using the Episode 2 comparison conventions where practical.
5. Generate Figure 1-style plots and backend-comparison/residual plots under Episode 3 outputs.
6. Update the Episode 3 README with commands, provenance, AUTO method notes, comparison findings, tolerance interpretation, limitations, and implications for later AUTO/LOCA work.
7. Run documented commands and uv run pytest, then record results in the task final summary when implementation is complete.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-013; existing plan already covers comparison script, curated outputs, README, tests, and full-suite verification.

- Implemented compare_auto_figure1.py, generated curated backend-comparison CSV/JSON/PNG outputs, updated README documentation, and added comparison-unit coverage.
- Verification: uv run python episodes/003-figure1-auto-continuation/scripts/compare_auto_figure1.py; uv run pytest (28 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented Episode 3 Figure 1 AUTO backend comparison artifacts for TASK-013.

Changes:
- Added compare_auto_figure1.py to compare normalized AUTO branches against Episode 2 Python continuation, Eq. 92--94 approximations, independent root-solve checks, and digitized paper Figure 1 curves.
- Generated curated backend comparison detail/summary CSV and JSON files plus Figure 1-style overlay and residual plots under outputs/figure1_backend_comparison/.
- Updated the Episode 3 README with commands, provenance, comparison methods, results, tolerances, limitations, and implications for future LOCA backend work.
- Added tests covering log-space interpolation and comparison-frame coverage across Python, Eq. 92--94, root-solve, and digitized sources.

Tests:
- uv run python episodes/003-figure1-auto-continuation/scripts/compare_auto_figure1.py
- uv run pytest (28 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
