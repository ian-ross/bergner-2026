---
id: TASK-001
title: Create Episode 2 scaffold and reusable continuation primitives
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:41'
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
- [ ] #5 Episode-specific planning decisions from the grill session are moved out of root CONTEXT.md into Episode 2 documentation, leaving root CONTEXT.md absent or limited to genuinely project-wide glossary terms.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/002-figure1-python-continuation/ with README plus scripts/, outputs/, docs/, notebooks/ as needed.
2. Inspect existing core.equilibrium and tests to define a minimal reusable continuation API.
3. Add package-level residual adapters for (log n, log q, s) and log(w), including optional row scaling.
4. Add a small generic one-parameter predictor-corrector continuation utility with convergence diagnostics and no episode file-path assumptions.
5. Add tests for residuals, positive-state handling, and a short continuation smoke case.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Grill-session correction: the current root CONTEXT.md entries are episode-specific planning decisions, not durable project-wide glossary terms. During TASK-001, move these decisions into an Episode 2 docs note (for example episodes/002-figure1-python-continuation/docs/planning-decisions.md or README section), then either remove the root CONTEXT.md file if no project-wide glossary terms remain or reduce it to genuinely project-wide domain language only.
<!-- SECTION:NOTES:END -->
