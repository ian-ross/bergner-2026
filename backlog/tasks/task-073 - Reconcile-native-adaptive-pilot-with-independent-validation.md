---
id: TASK-073
title: Reconcile native adaptive pilot with independent validation
status: To Do
assignee: []
created_date: '2026-08-24 13:18'
labels:
  - episode-008
  - validation
  - review
dependencies:
  - TASK-069
  - TASK-070
  - TASK-072
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Review the measured 210--226 K native adaptive pilot and validate accepted backend points independently before authorizing full-domain production. This task is a gate between pilot execution and broader Figure 5 continuation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every accepted pilot point, including post-remesh points, receives independent same-coordinate Python correction or an explicit validation-unavailable reason that blocks production use
- [ ] #2 A stratified subset receives independent IVP one-period validation where justified by TASK-069, with DOP853 and Radau used according to documented difficulty triggers
- [ ] #3 The pilot review decides whether full-domain continuation can proceed under the retained v1 method or whether a documented method-version revision/follow-up is required
- [ ] #4 Documentation records accepted, unresolved, failed, near-Hopf, and tripwire outcomes without changing terminal statuses through interpolation
<!-- AC:END -->
