---
id: TASK-006
title: Update repository guidance for shared backend directories
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
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
