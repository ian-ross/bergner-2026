---
id: TASK-033
title: Add reusable limit-cycle detection and convergence analysis
status: To Do
assignee: []
created_date: '2026-07-20 20:54'
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
- [ ] #1 A reusable package module detects complete cycles from saturation-ratio extrema and reports cycle boundaries, periods, extrema, and peak-to-peak amplitudes
- [ ] #2 The module computes relative period and amplitude drift over a configurable final-cycle window and evaluates the approved 0.1% thresholds over the final 20 cycles
- [ ] #3 The module compares converged orbits from multiple trajectories using a documented phase-independent distance or equivalent orbit-geometry metric
- [ ] #4 Utilities handle irregular solver output, incomplete edge cycles, insufficient cycles, and invalid/non-finite input with explicit behavior
- [ ] #5 Repository-level tests cover synthetic periodic, damped, drifting, phase-shifted, and failure cases
<!-- AC:END -->
