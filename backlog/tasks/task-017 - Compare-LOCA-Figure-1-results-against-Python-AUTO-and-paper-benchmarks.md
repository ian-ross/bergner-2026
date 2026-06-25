---
id: TASK-017
title: 'Compare LOCA Figure 1 results against Python, AUTO, and paper benchmarks'
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 16:48'
updated_date: '2026-06-25 17:05'
labels:
  - episode-004
  - loca
  - comparison
  - outputs
dependencies:
  - TASK-016
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add Episode 4 comparison artifacts that evaluate normalized LOCA branches against the Episode 2 Python continuation, Episode 3 AUTO continuation, Eq. 92--94 approximation, independent root-solve checks, and digitized Figure 1 curves.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode-local comparison script reads normalized LOCA branches plus existing Episode 2 and Episode 3 artifacts without refactoring the earlier episode scripts.
- [ ] #2 Comparison details include LOCA vs Python continuation, LOCA vs AUTO continuation, LOCA vs Eq. 92--94, LOCA vs Python root-solve checks, and LOCA vs digitized Figure 1.
- [ ] #3 Comparison outputs include backend_comparison_details.csv, backend_comparison_summary.csv, backend_comparison_summary.json, figure1_backend_comparison.png, figure1_backend_residuals.png, and run_metadata.json.
- [ ] #4 Plots clearly distinguish Python, AUTO, LOCA, analytic approximation, and digitized paper curves while preserving Figure 1 variable/temperature semantics.
- [ ] #5 README and/or planning docs summarize backend agreement, tolerances, limitations, and implications for later LOCA continuation experiments.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Adapt Episode 3 comparison logic into an Episode 4 compare_loca_figure1.py without refactoring earlier episode scripts.
2. Read LOCA normalized branches plus Episode 2 Python continuation/root-solve/digitized artifacts and Episode 3 AUTO branches.
3. Compute LOCA-vs-Python, LOCA-vs-AUTO, LOCA-vs-Eq. 92--94, LOCA-vs-root-solve, and LOCA-vs-digitized detail rows using the existing interpolation conventions.
4. Generate summary CSV/JSON and plots overlaying Python, AUTO, LOCA, analytic approximations, and digitized paper curves.
5. Document agreement/tolerances/limitations in Episode 4 README or planning docs and add deterministic checks where practical.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-017 implementation session; dependency TASK-016 is Done and provides normalized LOCA outputs.
<!-- SECTION:NOTES:END -->
