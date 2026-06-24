---
id: TASK-001
title: Create Episode 2 scaffold and reusable continuation primitives
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up Episode 2 for Figure 1 equilibrium reproduction and add reusable package-level continuation/residual utilities for future Python/AUTO/LOCA comparison work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 2 directory exists with README and scripts/outputs/docs structure following repository episode organization.
- [ ] #2 Package exposes reusable continuation primitives operating on log-state coordinates (log n, log q, s) and log(w) control without Figure-1-specific file paths or plotting.
- [ ] #3 Package exposes reusable equilibrium residual adapters using [dn/dt/n, dq/dt/q, ds/dt] with optional row scaling.
- [ ] #4 Package tests cover residual evaluation, positivity handling, and at least one short continuation smoke case.
<!-- AC:END -->
