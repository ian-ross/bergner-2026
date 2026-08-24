---
id: TASK-076
title: Acquire near-Hopf approach evidence and decide gap policy
status: To Do
assignee: []
created_date: '2026-08-24 13:19'
labels:
  - episode-008
  - hopf
  - analysis
dependencies:
  - TASK-069
  - TASK-070
  - TASK-075
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use production native adaptive continuation results to collect reliable near-Hopf approach evidence where reachable, perform the documented quadratic/quartic period-amplitude review, and decide connection or explicit-gap policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each Hopf side under review has either at least five reliable monotone approach points with amplitude, period, coordinates, diagnostics, and terminal statuses, or a documented reason why the approach remains an explicit gap
- [ ] #2 Quadratic and quartic P(A) fits, leave-one-out intercept checks, residual checks, and comparison with Episode 006 Hopf periods are performed only where the evidence prerequisites are met
- [ ] #3 The resulting connection/gap policy is encoded in schema-valid production records and never invents regular-orbit values at Hopf boundaries
<!-- AC:END -->
