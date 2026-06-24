---
id: TASK-002
title: Implement Figure 1 Python continuation and analytic approximation comparison
status: Done
assignee:
  - '@pi'
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:50'
labels: []
dependencies:
  - TASK-001
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the reusable continuation layer to reproduce Figure 1 equilibrium branches for p=300 hPa, F=1, T in {190,210,230} K, and w in [0.005,2.0] m/s, with independent root-solve and Eq. 92--94 checks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Episode 2 script generates continuation branch CSVs containing T_K, p_Pa, F, log_w, w_m_s, n, q, s, convergence diagnostics, and residual norms.
- [x] #2 Independent root-solve checks are computed at sampled w values and compared against continuation output.
- [x] #3 Analytic approximation values from Eqs. 92--94 are computed from package-level formulas and compared against continuation output.
- [x] #4 Comparison summary tables report maximum/typical discrepancies for continuation vs root solves and continuation vs analytic approximation.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add package-level Figure 1 analytic approximation helpers implementing Eqs. 92--94 from existing coefficient functions.
2. Write an Episode 2 script that runs log(w) continuation for T=190, 210, 230 K at p=300 hPa and F=1 over w in [0.005, 2.0] m/s.
3. Save branch points and continuation diagnostics to episode outputs.
4. Run independent equilibrium root solves at sampled w values and compare them to continuation points.
5. Compare continuation values to Eq. 92--94 approximations and write summary CSV/JSON tables.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added src/bergner_spichtinger_2026/approximations.py with Eq. 84 and Eqs. 92--94 package-level helpers.
- Added Episode 2 generate_figure1_continuation.py script producing branch CSVs, root-solve checks, analytic comparisons, and summary CSV/JSON outputs.
- Generated curated outputs under episodes/002-figure1-python-continuation/outputs/figure1_continuation/.
- Added approximation tests; uv run pytest passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the Figure 1 Python continuation and analytic-approximation comparison workflow.

Changes:
- Added package-level Eq. 84 / Eqs. 92--94 analytic equilibrium helpers.
- Added an Episode 2 generation script for p=300 hPa, F=1, T={190,210,230} K, and w in [0.005,2.0] m/s.
- Generated branch CSVs with physical state, log-state/control, convergence diagnostics, and residual norms.
- Added sampled independent root-solve checks and analytic Eq. 92--94 comparisons with detailed and summary CSV/JSON outputs.
- Updated the Episode 2 README and added tests for the approximation helpers.

Tests:
- uv run pytest
- uv run python episodes/002-figure1-python-continuation/scripts/generate_figure1_continuation.py
<!-- SECTION:FINAL_SUMMARY:END -->
