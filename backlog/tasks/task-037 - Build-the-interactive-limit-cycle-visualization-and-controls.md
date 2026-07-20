---
id: TASK-037
title: Build the interactive limit-cycle visualization and controls
status: To Do
assignee: []
created_date: '2026-07-20 20:54'
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
