---
id: TASK-046
title: Diagnose Episode 007 animation speed control
status: Done
assignee:
  - '@pi'
created_date: '2026-07-21 20:12'
updated_date: '2026-07-21 20:19'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Diagnose why repeated replay-rate reductions are not producing the expected perceived slowdown and make animation pacing explicit and reliable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The cause of the apparent replay-rate mismatch is reproduced and documented
- [x] #2 Animation speed is based on physical trajectory time rather than sample count
- [x] #3 The visible animated mode obeys the selected speed without worker-throughput jumps
- [x] #4 Web tests, production build, and browser timing checks pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Measure built-browser live and replay cursor rates.
2. Identify whether worker streaming, sample-index pacing, caching, or Plotly queuing causes the mismatch.
3. Replace ambiguous sample-count pacing with a physical-time animation clock and align visible animation behavior.
4. Add timing regressions and run browser/build validation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reproduced the mismatch in the built browser: worker-driven live rendering jumped from 0 to 57732 model seconds in about 0.5 wall seconds, while the repeatedly slowed post-completion replay moved 0 model seconds in 5 wall seconds. The user-visible fast animation was therefore a separate, unthrottled path.
- Replaced sample-index pacing with a physical-time clock: 1x is now explicitly 1.5 model seconds per wall second, independent of sample density.
- Worker samples are buffered and revealed by the same presentation clock during and after integration, so solver throughput cannot accelerate animation.
- Added smooth interpolation between irregular samples and explicit UI help text for the rate.
- Headless Chromium measured 6.00 model seconds over 4 wall seconds at 1x and 11.88 model seconds over 2 wall seconds at 4x.
- `npm test` passes 27 tests; TypeScript, Vite, and offline verification pass.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed the Episode 007 animation-speed mismatch by separating numerical throughput from presentation time.

Root cause:
- The speed reductions applied only to post-completion replay. During integration, each worker batch moved the visible cursor immediately, traversing almost 60,000 model seconds in roughly half a wall-clock second.

Changes:
- Buffer streamed samples instead of displaying them at worker throughput.
- Drive both live and completed animation from one physical-time clock.
- Define 1x explicitly as 1.5 model seconds per wall second; 0.25x and 4x scale that rate directly.
- Interpolate the orbit marker smoothly between irregular adaptive samples.
- Document the rate in the interface and Episode 007 architecture notes.

Validation:
- Browser timing: 6.00 model seconds / 4 wall seconds at 1x; 11.88 model seconds / 2 wall seconds at 4x.
- `npm test`: 27 passed.
- `npm run build`: TypeScript, Vite, and offline verification passed.
<!-- SECTION:FINAL_SUMMARY:END -->
