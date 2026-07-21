---
id: TASK-041
title: Improve Episode 007 live widget numerics and layout
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 16:38'
updated_date: '2026-07-21 16:48'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Improve the Episode 007 browser widget so its numerical trajectory is reliable at production settings, integration is visible while running, controls are compact, and the orbit view remains geometrically stable during replay.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The production widget uses a validated adaptive integration profile and accurate interpolation rather than coarse duration-scaled stepping
- [x] #2 Trajectory samples stream to the plots during integration and remain available for replay after completion
- [x] #3 Form controls use compact single-line variable/unit labels without expanding across excessive width
- [x] #4 The orbit plot has a stable near-square panel and does not change ranges or size during replay
- [x] #5 Web tests and offline production build pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a shared, production-tested adaptive integration profile and higher-order output interpolation.
2. Extend the worker protocol to stream equilibrium and sample batches, and render those batches live.
3. Separate full plot updates from lightweight replay cursor updates; fix orbit ranges and panel geometry.
4. Compact control markup and responsive CSS.
5. Add regression tests, run the web suite/build, update Episode 007 documentation, and record completion.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Replaced the coarse duration/100 production step cap with a shared 15 s adaptive profile and cubic Hermite dense output.
- Added equilibrium/sample-batch worker messages and live plot rendering while integration runs.
- Split full plot rendering from lightweight replay cursor updates; fixed orbit ranges on completed data and made the orbit panel square.
- Compacted form labels and control widths; updated Episode 007 numerical/architecture documentation.
- Web tests pass (27 tests) and the offline Vite build verifies local assets.

- Headless Chromium smoke test observed 37 distinct live-progress states, completed the 15,943-sample preset, and confirmed orbit dimensions and axis ranges were identical before and during replay.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Improved the Episode 007 browser explorer so the trajectory is both numerically tighter and visible during computation.

Changes:
- Added a shared production RK45 profile with a 15 s maximum step and cubic Hermite dense output; the production profile now passes the Python late-cycle period, amplitude, and orbit-distance checks.
- Streamed equilibrium and completed sample batches from the worker so all three plots grow during integration, while retaining full replay after completion.
- Replaced replay-time full Plotly rebuilds with lightweight cursor/marker updates and fixed completed-orbit ranges in a square panel.
- Compacted control widths and combined variable names, units, and live values into single-line labels.
- Updated Episode 007 architecture and validation documentation.

Tests:
- `npm test` (27 passed)
- `npm run build` (TypeScript, Vite, offline asset verification)
- Headless Chromium live-integration and replay geometry smoke test
<!-- SECTION:FINAL_SUMMARY:END -->
