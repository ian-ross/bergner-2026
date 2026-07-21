---
id: TASK-046
title: Diagnose Episode 007 animation speed control
status: To Do
assignee: []
created_date: '2026-07-21 20:12'
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
