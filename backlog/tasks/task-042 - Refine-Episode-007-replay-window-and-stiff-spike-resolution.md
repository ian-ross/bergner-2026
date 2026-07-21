---
id: TASK-042
title: Refine Episode 007 replay window and stiff spike resolution
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 19:51'
updated_date: '2026-07-21 19:58'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refine the improved Episode 007 widget by slowing replay, adding a moving five-period time window, reliably resolving narrow nucleation spikes, and using stable Figure 4 orbit bounds from the start.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Default replay advances approximately ten times more slowly than the current implementation at each displayed speed
- [x] #2 Time-series plots default to a fixed window of approximately five Figure 4 oscillation periods and scroll to follow replay time
- [x] #3 The production browser integration resolves recurring narrow Nuc_n spikes without sampling-beat height modulation
- [x] #4 The orbit plot starts with fixed bounds that contain the Figure 4 preset orbit without rescaling
- [x] #5 Web regression tests, production build, and browser smoke checks pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce and quantify late-cycle Nuc_n peak-height modulation under the production browser profile.
2. Add a spike-aware numerical/output strategy with a regression bound against a high-resolution reference.
3. Slow replay and add a fixed five-period moving time window.
4. Add fixed startup orbit bounds derived from the Figure 4 reference orbit.
5. Run numerical, build, and headless-browser validation; update documentation and task records.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reproduced 2.68% late-cycle Nuc_n peak-height modulation on the former 15 s uniform output grid.
- Confirmed output aliasing, not RK state integration, as the primary cause: accepted-step samples reduced modulation to 0.27%, and adding cubic-Hermite saturation stationary points reduced it to 1.9e-6 relative.
- Verified the mean browser peak (about 1635.895) against independently evaluated SciPy dense-output maxima for the final three cycles at 1e-5 relative.
- Added a five-period (12308.0 s) moving time window, a 10x replay slowdown, fixed Figure 4 startup orbit bounds, and disabled Plotly line simplification for budget spikes.
- Headless Chromium confirmed a square 484 px orbit with unchanged startup/completed bounds, fixed-width scrolling time axes, and rendered Nuc_n peak variation of 1.73e-6.
- `npm test` passes 27 tests; TypeScript, Vite build, and offline asset verification pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Refined the Episode 007 replay and numerical presentation around the canonical limit cycle.

Changes:
- Slowed all replay speed settings by approximately 10x.
- Added a fixed 12,308 s time-series viewport (five canonical late-cycle periods) that follows the current replay time.
- Diagnosed fixed-grid aliasing as the source of nucleation peak beating; production output now retains adaptive accepted endpoints and samples cubic-Hermite saturation stationary points.
- Disabled Plotly line simplification for process budgets so narrow Nuc_n peaks remain visible.
- Added fixed startup orbit bounds that contain the Figure 4 trajectory without rescaling.
- Updated numerical and architecture documentation.

Validation:
- Browser Nuc_n final-20-cycle peak variation: 1.9e-6 relative (previously 2.68e-2).
- Mean peak agrees with an independent SciPy dense-output reference at 1e-5 relative.
- `npm test`: 27 passed.
- `npm run build`: TypeScript, Vite, and offline verification passed.
- Headless Chromium verified scrolling time ranges, fixed orbit geometry/bounds, and rendered spike stability.
<!-- SECTION:FINAL_SUMMARY:END -->
