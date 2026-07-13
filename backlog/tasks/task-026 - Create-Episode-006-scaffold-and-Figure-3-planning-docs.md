---
id: TASK-026
title: Create Episode 006 scaffold and Figure 3 planning docs
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 16:04'
updated_date: '2026-07-13 16:07'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/006-figure3-hopf-bifurcation/ with README, docs/, scripts/, notebooks/, outputs/, and any placeholder files needed for empty directories.
2. Draft the episode README with the Figure 3 goal, target parameters p=300 hPa and F=1, temperature range 190--240 K, backend strategy, and expected workflow commands at a high level.
3. Draft docs/planning-decisions.md recording agreed decisions: true bifurcation continuation rather than scan/interpolation, Python augmented Hopf system, AUTO native Hopf continuation, LOCA dependency on TASK-025, Table II fit references, and output contracts.
4. Link prior episodes and reusable infrastructure: Figure 2 eigenvalue utilities, AUTO templates, current C++ backend, docs/REPRODUCTION_NOTES.md, and Table II source notes.
5. Verify the scaffold respects repository organization rules and does not create top-level episode-specific artifacts.
<!-- SECTION:PLAN:END -->
