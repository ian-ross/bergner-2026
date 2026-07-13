---
id: TASK-029
title: Implement AUTO native Hopf continuation for Figure 3
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 17:05'
labels: []
dependencies:
  - TASK-026
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use AUTO-07p native bifurcation tooling to detect the two Hopf points at T=230 K and continue them in the two-parameter space (log_w, T) for the Figure 3 domain. AUTO should exercise native Hopf detection/restart/continuation rather than merely generating equilibrium branches for external eigenvalue post-processing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AUTO run files/templates enable Hopf bifurcation detection from equilibrium continuation at T=230 K and label the lower and upper Hopf points.
- [x] #2 AUTO workflows restart from each Hopf label and continue the Hopf loci over T=190--240 K with log_w and T as active continuation parameters.
- [x] #3 Normalized AUTO outputs conform to the Episode 006 Hopf-locus schema and include raw AUTO artifacts, label provenance, convergence diagnostics, and method metadata.
- [x] #4 Tests or opt-in smoke checks verify AUTO outputs include both Hopf branches, cover the requested temperature range, and agree near T=230 K with Python/reference landmarks within documented tolerance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review AUTO-07p documentation/examples already available in the project environment for equilibrium Hopf detection and two-parameter Hopf continuation settings.
2. Create Episode 006 AUTO templates by adapting the Figure 2 equilibrium problem while enabling native Hopf detection at T=230 K and keeping log_w/T parameter conventions explicit.
3. Run equilibrium continuation at T=230 K, identify the two Hopf labels, and record label/provenance diagnostics.
4. Restart from each Hopf label and continue in active parameters log_w and T across 190--240 K, handling direction changes and branch naming consistently.
5. Normalize AUTO outputs into the Episode 006 Hopf-locus schema and preserve raw AUTO b/s/d files plus run metadata.
6. Add tests or opt-in smoke checks for raw-label detection, normalized schema, both branch labels, T-domain coverage, and T=230 K agreement with Python/reference anchors.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added Episode 006 AUTO problem template/config for transformed ODE Hopf detection (`ISP=2`) at T=230 K.
- Added `run_auto_hopf_loci.py` to restart AUTO HB1/HB2 with `ISW=2`, `ICP=[1,3]`, normalize lower/upper Figure 3 loci, preserve raw AUTO b/s/d files, and write diagnostics/metadata/plots.
- Generated curated AUTO outputs under `episodes/006-figure3-hopf-bifurcation/outputs/figure3_auto_hopf_loci/`; AUTO labels at T=230 K are 13 and 21 with w≈0.0485305 and 0.768690 m s^-1.
- Added smoke-contract coverage in `tests/test_episode6_auto_hopf.py`; full suite passes with `uv run pytest` (81 passed, 3 existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented AUTO-native Hopf detection and continuation for Episode 006 Figure 3.

Changes:
- Added Episode 006 AUTO templates/config that expose the transformed ODE in `(log n, log q, s)` and enable AUTO Hopf labels on the T=230 K equilibrium branch.
- Added `scripts/run_auto_hopf_loci.py`, which runs AUTO, detects lower/upper Hopf labels, restarts HB1/HB2 with `ISW=2` and active parameters `log_w`/`T`, normalizes loci into the Episode 006 schema, and records raw AUTO artifacts, diagnostics, metadata, and plots.
- Generated curated AUTO outputs under `outputs/figure3_auto_hopf_loci/`, including raw `b./s./d.` files, detected label provenance, normalized loci, summary/diagnostics JSON, and an AUTO method plot.
- Updated the Episode 006 README and added `tests/test_episode6_auto_hopf.py` smoke-contract coverage.

Verification:
- `uv run python episodes/006-figure3-hopf-bifurcation/scripts/run_auto_hopf_loci.py --clean`
- `uv run pytest` → 81 passed, 3 known overflow warnings from exploratory nonlinear solves.
<!-- SECTION:FINAL_SUMMARY:END -->
