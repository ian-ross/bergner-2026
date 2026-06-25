---
id: TASK-014
title: Create Episode 4 scaffold and LOCA planning docs
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 16:48'
updated_date: '2026-06-25 16:52'
labels:
  - episode-004
  - loca
  - docs
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up Episode 4 as the Figure 1 LOCA/Trilinos backend-equivalence episode. Document the agreed design: serial dense LOCA/LAPACK continuation, Sacado AD state Jacobian, Python as the semantic model reference, backend-neutral schema reuse, and episode-local outputs/orchestration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 4 directory structure exists under episodes/004-figure1-loca-continuation with README, docs, scripts, loca, notebooks, and outputs placeholders as appropriate.
- [ ] #2 Planning documentation records the agreed LOCA design choices, build/toolchain assumptions, output contract, and comparison scope.
- [ ] #3 README describes the Episode 4 goal, expected commands/artifacts, and relationship to Episodes 2 and 3.
- [ ] #4 No reusable C++/Trilinos infrastructure is promoted outside the episode unless documented as shared backend infrastructure.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/004-figure1-loca-continuation with README, docs, scripts, loca, notebooks, and outputs placeholders.
2. Draft docs/planning-decisions.md from the grill decisions: serial dense LOCA/LAPACK, Sacado AD state Jacobian, Python semantic reference, schema reuse, output contract, and toolchain assumptions.
3. Draft README with goals, upstream Episode 2/3 references, expected commands/artifacts, and scope boundaries for shared vs episode-local LOCA assets.
4. Verify repository organization follows AGENTS.md and update no generated artifacts beyond placeholders.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Created Episode 4 scaffold under episodes/004-figure1-loca-continuation with README, planning docs, episode-local LOCA placeholder, and directory placeholders.
- Added pytest coverage for the scaffold, planning-document content, README scope, and absence of promoted top-level LOCA infrastructure.
<!-- SECTION:NOTES:END -->
