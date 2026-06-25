---
id: TASK-018
title: Refactor Figure 1 backend comparison utilities after Episode 4
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 16:48'
updated_date: '2026-06-25 17:12'
labels:
  - post-episode-004
  - refactor
  - comparison
dependencies:
  - TASK-017
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After both AUTO and LOCA Figure 1 comparison scripts exist, extract shared comparison utilities or a generic backend-comparison script to reduce duplication while preserving curated Episode 3 and Episode 4 artifacts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Common interpolation, relative-error, summary, and plotting logic from Episodes 3 and 4 is identified and documented.
- [ ] #2 Shared utility code or a generic script supports Python/AUTO/LOCA branch inputs using the backend-neutral schema without changing curated scientific results.
- [ ] #3 Episode 3 and Episode 4 comparison commands continue to regenerate their documented artifacts.
- [ ] #4 Tests or checks cover schema compatibility and representative multi-backend comparison output.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect Episode 3 and Episode 4 comparison scripts/tests/docs to identify duplicated interpolation, error-summary, metadata, and plotting code.
2. Add a shared comparison utility module or generic script around the backend-neutral branch schema while keeping episode command interfaces stable.
3. Refactor Episode 3 and Episode 4 scripts to use the shared path and regenerate/verify curated artifacts remain scientifically unchanged.
4. Add or update tests covering schema compatibility and representative multi-backend comparison outputs.
5. Run the full test suite, update task metadata, commit the resolved work with TASK-018 in the message, and close the task.
<!-- SECTION:PLAN:END -->
