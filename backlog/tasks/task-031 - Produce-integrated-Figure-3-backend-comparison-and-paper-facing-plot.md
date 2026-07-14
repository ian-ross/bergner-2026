---
id: TASK-031
title: Produce integrated Figure 3 backend comparison and paper-facing plot
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-14 14:53'
labels: []
dependencies:
  - TASK-028
  - TASK-029
  - TASK-030
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Combine Python augmented Hopf, AUTO native Hopf, and LOCA Hopf outputs into integrated Figure 3 comparison artifacts. Produce a paper-facing T--w Hopf-locus plot with backend overlays and Table II fit curves, plus numeric backend-to-backend and backend-to-fit diagnostics.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Integrated comparison reads normalized outputs from all available Figure 3 backends and preserves backend/method provenance in merged CSV/JSON artifacts.
- [x] #2 Paper-facing plot shows lower and upper Hopf loci over T=190--240 K on a log-w axis, overlays Table II fit curves, and distinguishes backend-computed loci from paper fit references.
- [x] #3 Summary artifacts report backend-to-backend differences, backend-to-Table-II-fit differences, T=230 K anchor comparisons, missing/failed points, and known caveats.
- [x] #4 Tests or smoke checks verify comparison artifacts and plot are generated from representative backend outputs and that schema assumptions are enforced.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define the integrated comparison input contract and locate the normalized Python, AUTO, and LOCA Hopf-locus artifacts produced by earlier Episode 006 tasks.
2. Load backend outputs, validate required schema fields, preserve provenance, and merge lower/upper branch data into backend-comparison CSV/JSON artifacts.
3. Evaluate shared Table II Hopf fit utilities on the canonical 190--240 K grid and join fit-reference values to backend-computed loci for diagnostics.
4. Compute backend-to-backend and backend-to-fit differences in log_w and w_m_s, T=230 K anchor comparisons, missing/failure summaries, and branch coverage statistics.
5. Generate the paper-facing Figure 3 reproduction plot with log vertical velocity, lower/upper Hopf branches, backend overlays, Table II fit curves, and clear legend labels distinguishing fits from computed loci.
6. Write run metadata and tests/smoke checks using representative normalized inputs to verify schema validation, artifact generation, and plot existence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added scripts/compare_figure3_hopf_loci.py to merge available Python/AUTO/LOCA Figure 3 Hopf loci, preserve provenance columns, compute Table II fit deltas, pairwise backend differences, T=230 K anchors, caveats, metadata, and paper-facing plot.
- Added tests/test_episode6_backend_comparison.py for representative backend outputs and schema validation.
- Generated curated comparison artifacts under episodes/006-figure3-hopf-bifurcation/outputs/figure3_backend_comparison/.
- Updated Episode 006 README to document the integrated comparison workflow and outputs.
- Verification: uv run pytest tests/test_episode6_backend_comparison.py tests/test_episode6_python_hopf.py tests/test_episode6_auto_hopf.py tests/test_episode6_loca_hopf.py -q; uv run python episodes/006-figure3-hopf-bifurcation/scripts/compare_figure3_hopf_loci.py --require-all.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the integrated Figure 3 backend-comparison workflow.

Changes:
- Added `episodes/006-figure3-hopf-bifurcation/scripts/compare_figure3_hopf_loci.py` to read available Python/AUTO/LOCA normalized Hopf-locus outputs, validate schema assumptions, preserve backend/method provenance, and write merged CSV/JSON artifacts.
- Added Table II reference sampling, backend-to-fit diagnostics, backend-to-backend log_w/w differences on a canonical T grid, T=230 K anchor comparisons, missing/failed-point summaries, caveats, run metadata, and a paper-facing log-w Figure 3 overlay plot.
- Generated curated artifacts in `episodes/006-figure3-hopf-bifurcation/outputs/figure3_backend_comparison/`.
- Added focused tests covering representative backend outputs and schema validation, and documented the workflow in the Episode 006 README.

Verification:
- `uv run python episodes/006-figure3-hopf-bifurcation/scripts/compare_figure3_hopf_loci.py --require-all`
- `uv run pytest tests/test_episode6_backend_comparison.py tests/test_episode6_python_hopf.py tests/test_episode6_auto_hopf.py tests/test_episode6_loca_hopf.py -q`
<!-- SECTION:FINAL_SUMMARY:END -->
