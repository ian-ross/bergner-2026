---
id: TASK-007
title: Create Episode 3 scaffold and AUTO planning docs
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:16'
labels: []
dependencies:
  - TASK-006
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up Episode 3 for Figure 1 AUTO continuation as the first explicit backend-comparison episode against the Episode 2 Python continuation results.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 3 directory exists with README and docs/, scripts/, auto/, outputs/, and notebooks/ structure following the revised repository organization guidance.
- [ ] #2 Episode 3 planning documentation records the goal of comparing Python-native continuation, AUTO, and later LOCA backends on the same model.
- [ ] #3 The planning docs define the initial backend-neutral branch schema and comparison outputs for Figure 1.
- [ ] #4 Episode 3 README links to Episode 2 source outputs, digitized Figure 1 artifacts, and TASK-005 testing guidance when available.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/003-figure1-auto-continuation/ with README plus docs/, scripts/, auto/, outputs/, and notebooks/ placeholders.
2. Draft Episode 3 README with the goal: reproduce Figure 1 using AUTO as an independent backend and compare against Episode 2 Python outputs.
3. Add docs/planning-decisions.md summarizing the grill-session decisions: log_w continuation, transformed state coordinates, shared auto/ code, Python orchestration, and backend-neutral schema.
4. Define the provisional branch schema and expected comparison artifacts in the docs.
5. Link Episode 2 continuation/digitization/reproduction outputs and note that TASK-005/docs/testing.md will provide testing-domain guidance when complete.
<!-- SECTION:PLAN:END -->
