---
id: TASK-030
title: Implement LOCA Hopf continuation for Figure 3
status: To Do
assignee: []
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 16:05'
labels: []
dependencies:
  - TASK-025
  - TASK-026
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After the full NOX/LOCA backend prerequisite is validated, use native LOCA bifurcation continuation to track the Figure 3 lower and upper Hopf loci over T=190--240 K. This task is the Figure 3 LOCA application layer, distinct from the generic NOX/LOCA backend infrastructure in TASK-025.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The task explicitly depends on TASK-025 or documents any remaining NOX/LOCA backend limitations before attempting Hopf tracking.
- [ ] #2 LOCA workflows detect or seed the two T=230 K Hopf points and continue the Hopf loci in (log_w, T) over the Figure 3 temperature domain.
- [ ] #3 Normalized LOCA outputs conform to the Episode 006 Hopf-locus schema and include backend diagnostics, continuation settings, convergence status, and raw/derived artifact provenance.
- [ ] #4 Tests or opt-in smoke checks verify both LOCA Hopf branches are present, match T=230 K landmarks within documented tolerance, and are compatible with integrated backend comparison scripts.
<!-- AC:END -->
