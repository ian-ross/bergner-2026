---
id: TASK-036
title: Implement adaptive browser integration and worker execution
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:02'
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
- [ ] #1 The adaptive RK45 implementation uses component-wise error scaling, preserves positive n and q through log coordinates, supports configurable tolerances and duration, and enforces accepted-step and output-size limits
- [ ] #2 Worker messages are typed and support start, progress, successful result, numerical failure, and cancellation without blocking the main UI thread
- [ ] #3 Returned samples include n, q, s, all individual process rates, and total tendencies on a documented output grid suitable for plotting and animation
- [ ] #4 Short-horizon browser results agree with the Python reference states and process rates to about 1e-4 relative error before material phase drift
- [ ] #5 Canonical long-run period, extrema, amplitudes, and orbit geometry agree with Python reference statistics to about 1e-3 relative error
- [ ] #6 Tests cover cancellation, invalid states/parameters, step-limit exhaustion, positivity, canonical integration, and at least one damped-regime trajectory
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
