---
id: TASK-068.03
title: 'TASK-068 slice: provisional spine-and-slices native adaptive run'
status: To Do
assignee: []
created_date: '2026-08-24 10:52'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - adaptivity
dependencies: []
parent_task_id: TASK-68
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Execute the planned provisional native adaptive spine-and-slices continuation using the generalized driver, preserving truthful terminal statuses and run evidence rather than assuming production Figure 5 success.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run manifest covers the T=225 K move to the spine, both temperature directions over the provisional spine range, and signed rho slices for every target on the 2 K skeleton while retaining exact T=210 K and T=225 K anchors
- [ ] #2 Every target has exactly one terminal status: accepted, resolution_unresolved, near_hopf_stop, tripwire_stop, or failed with a reason
- [ ] #3 Accepted segment points and remesh restarts pass independent residual, phase, positivity, linear, finite-change, and restart gates; unresolved/rejected/capped/tripwire outcomes are recorded rather than suppressed
- [ ] #4 Near-Hopf approach evidence records amplitude, period, coordinates, diagnostics, and terminal statuses when reached, targeting at least five reliable points where reachable while deferring fit/connection policy to TASK-069
<!-- AC:END -->
