---
id: TASK-012
title: Normalize AUTO outputs to backend-neutral branch schema
status: Done
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 10:05'
labels: []
dependencies:
  - TASK-011
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parse Episode 3 AUTO continuation outputs into a backend-neutral branch table compatible with Episode 2 Python continuation outputs and future LOCA comparisons.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AUTO branch CSVs include backend, T_K, p_Pa, F, N_a_m3, log_w, w_m_s, log_n, log_q, n, q, s, and available AUTO diagnostics.
- [x] #2 One combined branches_all.csv is written for all Figure 1 temperatures using the agreed backend-neutral schema.
- [x] #3 Parsing scripts preserve raw AUTO labels and diagnostics while converting transformed coordinates to physical values.
- [x] #4 Run metadata documents schema version, input files, raw AUTO output paths, and any parser assumptions.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect the raw AUTO output files produced by TASK-011 and identify the reliable source for branch labels, parameter values, state values, and diagnostics.
2. Implement a Python parser/normalizer in Episode 3 scripts that reads raw AUTO outputs and converts transformed coordinates to physical n, q, s and w.
3. Write per-temperature branch CSVs and a combined branches_all.csv using the backend-neutral schema defined in Episode 3 planning docs.
4. Preserve AUTO-specific labels and diagnostics in explicit columns rather than discarding them.
5. Write run metadata including schema version, parser assumptions, raw output provenance, and any known limitations.
6. Add lightweight tests or validation checks for required columns, monotonic/log_w coverage, positivity, and finite values.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Implemented backend-neutral AUTO branch schema in Episode 3 run script with AUTO diagnostics preserved as auto_* fields.
- Added combined branches_all.csv generation and run_metadata.json with schema version, parser assumptions, input files, and raw AUTO output paths.
- Added schema/combined CSV tests and regenerated curated Figure 1 AUTO branch outputs.
- Validation: uv run pytest (26 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented backend-neutral AUTO branch normalization for TASK-012.

Changes:
- Updated Episode 3 AUTO orchestration to write backend-neutral per-temperature branch CSVs with backend, physical/environment fields, transformed coordinates, physical n/q/s values, recomputed residual norms, source file paths, and preserved AUTO labels/type/point/L2 diagnostics.
- Added branches_all.csv generation across T=190, 210, and 230 K.
- Added run_metadata.json alongside diagnostics with schema version, normalized columns, parser assumptions, input files, and raw AUTO output paths.
- Regenerated curated Episode 3 AUTO branch outputs under outputs/figure1_auto_branches and documented the new output contract.
- Added pytest coverage for schema records and combined CSV emission.

Validation:
- uv run python episodes/003-figure1-auto-continuation/scripts/run_auto_figure1.py --clean
- uv run pytest (26 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
