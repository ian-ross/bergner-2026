---
id: TASK-046
title: Diagnose Episode 007 animation speed control
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:12'
updated_date: '2026-07-21 20:12'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Diagnose why repeated replay-rate reductions are not producing the expected perceived slowdown and make animation pacing explicit and reliable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The cause of the apparent replay-rate mismatch is reproduced and documented
- [ ] #2 Animation speed is based on physical trajectory time rather than sample count
- [ ] #3 The visible animated mode obeys the selected speed without worker-throughput jumps
- [ ] #4 Web tests, production build, and browser timing checks pass
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Measure built-browser live and replay cursor rates.
2. Identify whether worker streaming, sample-index pacing, caching, or Plotly queuing causes the mismatch.
3. Replace ambiguous sample-count pacing with a physical-time animation clock and align visible animation behavior.
4. Add timing regressions and run browser/build validation.
<!-- SECTION:PLAN:END -->
