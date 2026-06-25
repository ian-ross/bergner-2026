---
id: TASK-013
title: Compare AUTO Figure 1 results against Python and paper benchmarks
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:16'
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
- [ ] #1 Comparison tables report AUTO-vs-Python differences for n, q, and s after interpolation onto a common log_w grid or sampled points.
- [ ] #2 Comparison outputs include AUTO-vs-Eq. 92--94 and AUTO-vs-digitized Figure 1 summaries where the Episode 2 artifacts are available.
- [ ] #3 Curated Episode 3 plots show AUTO branches in the Figure 1 three-panel layout and make backend comparisons visually inspectable.
- [ ] #4 Episode 3 README documents commands, source provenance, AUTO method, comparison results, tolerances, limitations, and implications for later AUTO/LOCA work.
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
