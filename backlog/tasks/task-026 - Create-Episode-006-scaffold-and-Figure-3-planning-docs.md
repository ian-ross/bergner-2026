---
id: TASK-026
title: Create Episode 006 scaffold and Figure 3 planning docs
status: Done
assignee:
  - '@pi'
created_date: '2026-07-13 16:04'
updated_date: '2026-07-13 16:09'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the Episode 006 workspace for reproducing Bergner & Spichtinger (2026) Figure 3 Hopf bifurcation loci. Document agreed scope: p=300 hPa, F=1, T=190--240 K, lower/upper Hopf branches in vertical velocity, backend comparison across Python augmented Hopf continuation, AUTO native Hopf continuation, and NOX/LOCA Hopf continuation, with Table II fit curves as reference.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Episode 006 directory exists with README, docs/planning-decisions.md, scripts/notebooks/outputs placeholders as appropriate.
- [x] #2 Planning docs capture the agreed Figure 3 target, temperature/w ranges, backend responsibilities, output schema, and dependency on TASK-025 for the LOCA path.
- [x] #3 The episode README links to relevant prior episodes and shared infrastructure without duplicating backend-specific implementation details.
- [x] #4 No episode-specific artifacts are placed in top-level scripts/notebooks/outputs directories.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Create episodes/006-figure3-hopf-bifurcation/ with README, docs/, scripts/, notebooks/, outputs/, and any placeholder files needed for empty directories.
2. Draft the episode README with the Figure 3 goal, target parameters p=300 hPa and F=1, temperature range 190--240 K, backend strategy, and expected workflow commands at a high level.
3. Draft docs/planning-decisions.md recording agreed decisions: true bifurcation continuation rather than scan/interpolation, Python augmented Hopf system, AUTO native Hopf continuation, LOCA dependency on TASK-025, Table II fit references, and output contracts.
4. Link prior episodes and reusable infrastructure: Figure 2 eigenvalue utilities, AUTO templates, current C++ backend, docs/REPRODUCTION_NOTES.md, and Table II source notes.
5. Verify the scaffold respects repository organization rules and does not create top-level episode-specific artifacts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Created `episodes/006-figure3-hopf-bifurcation/` with README, `docs/planning-decisions.md`, and `.gitkeep` placeholders under scripts/notebooks/outputs.
- README links prior episodes, shared AUTO/loca/src infrastructure, and source/reproduction docs while keeping backend details in planning docs.
- Planning docs capture Figure 3 target (`p=300 hPa`, `F=1`, `T=190--240 K`), lower/upper Hopf branches, Table II fit coefficients, backend responsibilities, output schema, TASK-025 LOCA dependency, and scope boundaries.
- Verified no top-level episode-specific scripts/notebooks/outputs artifacts were created.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Created the Episode 006 scaffold for Figure 3 Hopf bifurcation-locus reproduction.

Changes:
- Added `episodes/006-figure3-hopf-bifurcation/README.md` describing the Figure 3 goal, target parameter range, upstream references, and high-level backend strategy.
- Added `episodes/006-figure3-hopf-bifurcation/docs/planning-decisions.md` documenting the agreed scope, true Hopf-locus continuation method, Table II reference fits, backend responsibilities, provisional output schema, TASK-025 dependency for NOX/LOCA, and scope boundaries.
- Added `.gitkeep` placeholders for episode-local `scripts/`, `notebooks/`, and `outputs/`.

Verification:
- Inspected the new episode file layout with `find`.
- Checked repository status/diff to confirm no top-level episode-specific artifacts were added.
<!-- SECTION:FINAL_SUMMARY:END -->
