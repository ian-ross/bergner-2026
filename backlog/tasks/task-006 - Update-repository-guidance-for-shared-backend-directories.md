---
id: TASK-006
title: Update repository guidance for shared backend directories
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:42'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Refine repository organization guidance so shared backend code can live in top-level backend directories such as auto/ while episode-specific experiments remain under episodes/.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AGENTS.md explicitly permits a top-level auto/ directory for shared AUTO-07p model/backend assets used by multiple episodes.
- [ ] #2 AGENTS.md distinguishes shared backend code from episode-specific auto/ directories, scripts, notebooks, and outputs.
- [ ] #3 Guidance notes that future shared LOCA/Trilinos backend code may use an analogous top-level directory or documented convention.
- [ ] #4 The revised guidance preserves the episodic organization rule for episode-specific research artifacts.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Re-read AGENTS.md repository organization guidance and identify the exact wording that currently excludes top-level auto/ directories.
2. Revise the guidance to permit top-level auto/ only for shared AUTO-07p backend/model assets used by multiple episodes.
3. Clarify that episode-specific AUTO run files, scripts, generated outputs, notebooks, and one-off variants still belong under the relevant episode.
4. Add a forward-looking note that shared LOCA/Trilinos backend code may use an analogous documented convention.
5. Self-review the updated guidance for consistency with the existing episodic organization rule.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-006. Reviewing repository guidance and applying the documented plan.

Updated AGENTS.md repository guidance and ran the full test suite with `uv run pytest` (11 passed). No new code paths were introduced; this is documentation-only.
<!-- SECTION:NOTES:END -->
