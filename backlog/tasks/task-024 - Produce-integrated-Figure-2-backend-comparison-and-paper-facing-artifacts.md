---
id: TASK-024
title: Produce integrated Figure 2 backend comparison and paper-facing artifacts
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 11:14'
updated_date: '2026-07-13 14:30'
labels:
  - episode-005
  - figure2
  - eigenvalues
  - comparison
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Combine Python, AUTO, and LOCA Figure 2 eigenvalue outputs into curated backend-comparison artifacts and a paper-style Figure 2 reproduction. Include simple zero-crossing Hopf estimates and optional paper digitization if feasible, while documenting digitization uncertainty.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Combined comparison outputs interpolate or align backend eigenvalues on a documented canonical log-w comparison grid without discarding raw backend grids.
- [ ] #2 Headline figure2_reproduction plot contains real-part and imaginary-part panels versus log-scaled w, clearly distinguishing Python, AUTO, LOCA, and optional digitized paper markers.
- [ ] #3 Summary CSV/JSON reports backend-to-backend eigenvalue differences, Hopf crossing estimates, three-real interval information, and stability/regime counts.
- [ ] #4 Optional Figure 2 digitization is attempted or explicitly deferred with rationale; any digitized comparison is labeled as secondary evidence with uncertainty notes.
- [ ] #5 Episode README documents final commands, curated artifact paths, backend methods, fallback decisions, and known limitations.
- [ ] #6 Repository tests pass after the integrated comparison work.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Load the curated Python, AUTO, and LOCA Figure 2 outputs and validate their schemas, parameter consistency, raw grid coverage, eigenvalue sorting metadata, and backend provenance.
2. Define a canonical log-w comparison grid and interpolate/aligned backend eigenvalue quantities while preserving raw backend outputs.
3. Compute backend-to-backend difference tables, Hopf crossing comparisons, three-real interval summaries, stability/regime counts, and backend method/fallback summaries.
4. Attempt Figure 2 digitization from the source PDF if feasible; otherwise document the deferral and any visual obstacles, especially imaginary-part extraction uncertainty.
5. Generate the headline Figure 2 reproduction plot with real and imaginary panels, backend overlays, Hopf markers, and optional digitized paper markers.
6. Update the Episode 5 README with final commands, artifacts, backend decisions, limitations, and run repository tests.
<!-- SECTION:PLAN:END -->
