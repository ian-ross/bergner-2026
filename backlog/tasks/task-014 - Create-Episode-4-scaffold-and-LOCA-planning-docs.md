---
id: TASK-014
title: Create Episode 4 scaffold and LOCA planning docs
status: To Do
assignee: []
created_date: '2026-06-25 16:48'
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
