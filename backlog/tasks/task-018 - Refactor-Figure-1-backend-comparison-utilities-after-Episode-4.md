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
1. Compare Episode 3 and Episode 4 comparison scripts after both are complete and identify duplicated interpolation, error-summary, metadata, and plotting logic.
2. Design a small shared utility or generic script around the backend-neutral branch schema without changing curated artifacts.
3. Refactor incrementally so Episode 3 and Episode 4 documented commands still regenerate their outputs.
4. Add tests/checks for representative multi-backend comparisons and schema compatibility.
5. Update documentation to explain the shared comparison workflow and migration path for future backends.
<!-- SECTION:PLAN:END -->
