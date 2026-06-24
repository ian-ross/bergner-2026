---
id: TASK-001
title: Create Episode 2 scaffold and reusable continuation primitives
status: Done
assignee:
  - '@pi'
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:44'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up Episode 2 for Figure 1 equilibrium reproduction and add reusable package-level continuation/residual utilities for future Python/AUTO/LOCA comparison work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Episode 2 directory exists with README and scripts/outputs/docs structure following repository episode organization.
- [x] #2 Package exposes reusable continuation primitives operating on log-state coordinates (log n, log q, s) and log(w) control without Figure-1-specific file paths or plotting.
- [x] #3 Package exposes reusable equilibrium residual adapters using [dn/dt/n, dq/dt/q, ds/dt] with optional row scaling.
- [x] #4 Package tests cover residual evaluation, positivity handling, and at least one short continuation smoke case.
- [x] #5 Episode-specific planning decisions from the grill session are moved out of root CONTEXT.md into Episode 2 documentation, leaving root CONTEXT.md absent or limited to genuinely project-wide glossary terms.
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

- Created Episode 2 scaffold under episodes/002-figure1-python-continuation with README, docs, scripts, outputs, and notebooks placeholders.
- Added reusable residual adapters in src/bergner_spichtinger_2026/residuals.py for (log n, log q, s) state and log(w) control.
- Added reusable predictor-corrector continuation primitives in src/bergner_spichtinger_2026/continuation.py.
- Moved Figure 1 planning language from root CONTEXT.md into Episode 2 docs and removed root CONTEXT.md.
- Added residual, positivity, row-scaling, and short continuation smoke tests; uv run pytest passes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Created the Episode 2 Figure 1 continuation scaffold and moved episode-specific planning language out of the repository root.

Changes:
- Added episodes/002-figure1-python-continuation/ with README, docs/planning-decisions.md, and placeholder scripts/outputs/notebooks directories.
- Added package-level residual adapters for (log n, log q, s) state coordinates and log(w) control, returning [dn/dt/n, dq/dt/q, ds/dt] with optional row scaling.
- Added a reusable fixed-control predictor-corrector continuation utility with convergence diagnostics.
- Exported the new continuation/residual helpers from the package root.
- Added tests covering residual evaluation, row scaling, positivity handling, and a short log(w) continuation smoke case.

Tests:
- uv run pytest
<!-- SECTION:FINAL_SUMMARY:END -->
