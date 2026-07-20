---
id: TASK-037
title: Build the interactive limit-cycle visualization and controls
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:02'
labels:
  - episode-007
  - typescript
  - plotly
  - ui
dependencies:
  - TASK-036
references:
  - episodes/007-limit-cycle-interactive-widget/docs/planning-decisions.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the vanilla TypeScript and locally bundled Plotly interface around the validated worker. Users can set supported parameters, solve and integrate a fresh trajectory in-browser, and replay it through synchronized state, process-budget, and orbit views.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Controls expose T, w, F, and N_a prominently; p and Delta z as advanced controls; logarithmic controls for w and N_a; physical integration duration; run, cancel, reset, play/pause, scrub, and playback speed
- [ ] #2 A Figure 4 limit-cycle preset restores T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=10000 cm^-3, Delta z=100 m, the paper-style 0.99-equilibrium start, and the notebook-derived long duration
- [ ] #3 Users can select the paper-style start or the approved n-, q-, and s-perturbed equilibrium starts, while the computed equilibrium is displayed with units
- [ ] #4 Synchronized Plotly views show n, q, s time series with a moving cursor; selectable n/q/s process budgets; and a log10(n)-s orbit with a moving marker and recent trail
- [ ] #5 Integration completes before replay, worker progress and errors are visible, cancellation remains responsive, and step-limit warnings explain how to recover
- [ ] #6 UI tests cover parameter validation, preset restoration, worker-state transitions, budget selection, and animation controls
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Build semantic HTML and responsive CSS for primary/advanced parameter controls, duration and initial-condition selection, run status, transport controls, and three visualization regions.
2. Connect validated controls to the worker, including logarithmic w/N_a behavior, unit conversion, the canonical Figure 4 preset, equilibrium display, progress, cancellation, reset, and actionable failures.
3. Implement the four equilibrium-relative initial-condition choices and ensure each parameter change invalidates stale trajectories before a new solve.
4. Create locally bundled Plotly state-series, selectable process-budget, and log10(n)-s orbit views with shared time selection.
5. Implement replay after integration with play/pause, scrubbing, speed control, moving cursors/markers, and a bounded recent orbit trail independent of solver speed.
6. Add UI tests for validation, presets, worker-state transitions, stale-result protection, budget selection, and animation state; manually inspect responsive layout and labels.
<!-- SECTION:PLAN:END -->
