---
id: TASK-036
title: Implement adaptive browser integration and worker execution
status: Done
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:48'
labels:
  - episode-007
  - typescript
  - numerics
  - web-worker
dependencies:
  - TASK-034
  - TASK-035
references:
  - episodes/007-limit-cycle-interactive-widget/outputs/reference_trajectory.csv
  - episodes/007-limit-cycle-interactive-widget/outputs/reference_metadata.json
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add an adaptive Dormand-Prince RK45 trajectory integrator in log(n), log(q), s coordinates and run equilibrium plus trajectory computations in a cancellable Web Worker. Validate short-horizon trajectories and long-run cycle statistics against the notebook contract.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The adaptive RK45 implementation uses component-wise error scaling, preserves positive n and q through log coordinates, supports configurable tolerances and duration, and enforces accepted-step and output-size limits
- [x] #2 Worker messages are typed and support start, progress, successful result, numerical failure, and cancellation without blocking the main UI thread
- [x] #3 Returned samples include n, q, s, all individual process rates, and total tendencies on a documented output grid suitable for plotting and animation
- [x] #4 Short-horizon browser results agree with the Python reference states and process rates to about 1e-4 relative error before material phase drift
- [x] #5 Canonical long-run period, extrema, amplitudes, and orbit geometry agree with Python reference statistics to about 1e-3 relative error
- [x] #6 Tests cover cancellation, invalid states/parameters, step-limit exhaustion, positivity, canonical integration, and at least one damped-regime trajectory
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Specify the log-state ODE, Dormand-Prince 5(4) tableau, component-wise error norm, adaptive-step rules, output-grid contract, and numerical failure limits.
2. Implement and unit-test adaptive integration in log(n), log(q), s coordinates, including positivity, tolerance handling, accepted-step limits, output-size limits, and dense or interpolated sampling for plots.
3. Define a typed worker protocol and move equilibrium solving plus trajectory integration into a Web Worker with progress, result, failure, and cooperative cancellation messages.
4. Evaluate and return all individual process terms and total tendencies at output samples without coupling the numerical core to Plotly.
5. Validate short-horizon states and rates against the Python reference before phase drift, then validate long-horizon period, extrema, amplitudes, and orbit geometry against the approved tolerances.
6. Add tests for cancellation, invalid inputs, step exhaustion, canonical positivity, deterministic output, and a damped Figure 4 regime; measure canonical runtime to choose safe defaults.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Confirmed the existing task plan and binding Episode 007 numerical/worker contract.
- Implementing the pure RK45 core first, followed by worker protocol/wiring and reference-backed validation tests.

- Implemented adaptive Dormand-Prince RK45 in log coordinates, typed asynchronous worker execution/cancellation, plot-ready samples, and main-thread worker wiring.
- Added Python-reference short-horizon rate/state checks, canonical late-cycle period/amplitude/orbit checks, and cancellation/limit/positivity/damped-regime coverage.
- Validation: `npm test -- --run`, `npm run build`, and `uv run pytest` (107 passed; 3 pre-existing numerical overflow warnings).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented TASK-036 adaptive browser trajectory execution.

Changes:
- Added a positivity-preserving log-coordinate Dormand-Prince RK45 core with configurable tolerances/duration, accepted-step and output limits, uniform plot samples, per-sample process terms, and total tendencies.
- Added typed worker protocol plus cooperative asynchronous worker execution for equilibrium, progress, success, numerical failure, and cancellation; main entry point now delegates canonical work to the worker.
- Added reference-backed short-horizon state/rate validation, late-cycle period/amplitude/orbit-geometry validation, and tests for cancellation, invalid input, limits, positivity, canonical, and damped trajectories.

Tests:
- `npm test -- --run`
- `npm run build`
- `uv run pytest` (107 passed)
<!-- SECTION:FINAL_SUMMARY:END -->
