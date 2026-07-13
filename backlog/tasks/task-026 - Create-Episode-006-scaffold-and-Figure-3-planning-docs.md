---
id: TASK-026
title: Create Episode 006 scaffold and Figure 3 planning docs
status: To Do
assignee: []
created_date: '2026-07-13 16:04'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the Episode 006 workspace for reproducing Bergner & Spichtinger (2026) Figure 3 Hopf bifurcation loci. Document agreed scope: p=300 hPa, F=1, T=190--240 K, lower/upper Hopf branches in vertical velocity, backend comparison across Python augmented Hopf continuation, AUTO native Hopf continuation, and NOX/LOCA Hopf continuation, with Table II fit curves as reference.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 006 directory exists with README, docs/planning-decisions.md, scripts/notebooks/outputs placeholders as appropriate.
- [ ] #2 Planning docs capture the agreed Figure 3 target, temperature/w ranges, backend responsibilities, output schema, and dependency on TASK-025 for the LOCA path.
- [ ] #3 The episode README links to relevant prior episodes and shared infrastructure without duplicating backend-specific implementation details.
- [ ] #4 No episode-specific artifacts are placed in top-level scripts/notebooks/outputs directories.
<!-- AC:END -->
