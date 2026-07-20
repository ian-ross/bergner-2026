---
id: TASK-033
title: Add reusable limit-cycle detection and convergence analysis
status: Done
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:18'
labels:
  - episode-007
  - python
  - numerics
dependencies:
  - TASK-032
references:
  - src/bergner_spichtinger_2026/core.py
  - docs/testing.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add reusable Python primitives for extracting complete cycles from irregularly sampled trajectories, estimating periods and amplitudes, quantifying late-cycle drift, and comparing attracting orbits. These utilities support the Episode 007 notebook without embedding analysis logic in notebook cells.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reusable package module detects complete cycles from saturation-ratio extrema and reports cycle boundaries, periods, extrema, and peak-to-peak amplitudes
- [x] #2 The module computes relative period and amplitude drift over a configurable final-cycle window and evaluates the approved 0.1% thresholds over the final 20 cycles
- [x] #3 The module compares converged orbits from multiple trajectories using a documented phase-independent distance or equivalent orbit-geometry metric
- [x] #4 Utilities handle irregular solver output, incomplete edge cycles, insufficient cycles, and invalid/non-finite input with explicit behavior
- [x] #5 Repository-level tests cover synthetic periodic, damped, drifting, phase-shifted, and failure cases
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define typed result structures and explicit semantics for extrema, complete cycles, periods, amplitudes, drift windows, convergence outcomes, and orbit-distance results.
2. Implement robust extrema and complete-cycle extraction for irregular time samples, including edge-cycle removal and interpolation/refinement where justified.
3. Implement final-window period and amplitude drift metrics with configurable thresholds and the Episode 007 final-20-cycle convergence check.
4. Implement a documented phase-independent orbit comparison by resampling complete cycles and minimizing cyclic phase mismatch or using an equivalent symmetric geometry metric.
5. Add validation and failure handling for non-finite, non-monotone, incomplete, and insufficient inputs.
6. Add synthetic repository-level tests for periodic, damped, drifting, phase-shifted, irregularly sampled, and invalid trajectories; expose the stable public API from the package as appropriate.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added reusable irregular-sampling cycle extraction, late-cycle drift analysis, and phase-independent normalized orbit distance.
- Added synthetic periodic, damped, drifting, phase-shifted, incomplete, and invalid-input tests.
- Full suite: uv run pytest (105 passed; 3 pre-existing overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented reusable limit-cycle analysis for Episode 007 and future trajectory workflows.

Changes:
- Added typed extrema, cycle extraction, late-window drift, and phase-independent normalized orbit-distance APIs.
- Exported the new package API and documented metric and validation behavior.
- Added synthetic coverage for irregular periodic/damped/drifting trajectories, phase shifts, incomplete cycles, and invalid inputs.

Tests:
- uv run pytest (105 passed; 3 existing overflow warnings)
<!-- SECTION:FINAL_SUMMARY:END -->
