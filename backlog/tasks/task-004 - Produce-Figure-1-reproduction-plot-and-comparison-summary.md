---
id: TASK-004
title: Produce Figure 1 reproduction plot and comparison summary
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:38'
labels: []
dependencies:
  - TASK-001
  - TASK-002
  - TASK-003
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Assemble the Episode 2 final reproduction artifact: generated Figure 1-style plot, overlays/comparisons against digitized paper curves, and a concise interpretation note.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Curated reproduction plot matches Figure 1 layout with n, q, and s panels, log-scaled w axis, and T=190/210/230 K color mapping.
- [ ] #2 Generated continuation, analytic approximation, and digitized paper curves are compared in plots or residual/error panels.
- [ ] #3 Episode 2 README/doc note describes source provenance, numerical method, digitization method, outputs, and known limitations.
- [ ] #4 All relevant tests and reproduction scripts run successfully via documented uv commands.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Load Episode 2 continuation, root-solve, analytic approximation, and digitized Figure 1 outputs.
2. Generate a Figure 1-style three-panel reproduction using the paper color mapping and log-scaled w axis.
3. Add comparison overlays or error summaries between generated continuation, analytic approximation, and digitized paper curves.
4. Write a concise Episode 2 README/doc note covering provenance, numerical method, digitization method, outputs, commands, and limitations.
5. Run tests and documented reproduction commands, then record results in the task final summary when implementation is complete.
<!-- SECTION:PLAN:END -->
