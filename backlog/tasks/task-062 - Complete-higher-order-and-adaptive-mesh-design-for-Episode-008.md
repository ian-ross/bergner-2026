---
id: TASK-062
title: Complete higher-order and adaptive-mesh design for Episode 008
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 14:09'
labels:
  - episode-008
  - design
  - numerics
dependencies:
  - TASK-061
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resume the numerical design interview after fixed-mesh native LOCA continuation works, calibrating the deferred production details for higher-order Gauss collocation, defect-driven h/r adaptation, Floquet diagnostics, Hopf approach, and error-controlled Figure 5 sampling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fixed-mesh midpoint evidence is reviewed before production adaptation constants are chosen
- [ ] #2 The higher-order fixed-mesh validation sequence and criteria for adding a Radau comparison are finalized
- [ ] #3 Composite monitor normalization, independent defect checks, r-movement bounds, h-marking policy, mesh caps, and remesh restart acceptance are calibrated and documented
- [ ] #4 Phase refresh, Hopf stopping/extrapolation, Floquet, interpolation-error, and multivalued-branch thresholds are finalized with evidence
- [ ] #5 The production artifact schemas and remaining implementation tasks are decomposed into atomic verifiable backlog tasks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Design interview decision: TASK-062 will specify operational, versioned v1 numerical constants. They are final for the initial implementation contract but must be reassessed against higher-order/adaptive calibration evidence; subsequent changes require documented evidence and a method-version revision.

- Design interview decision: initial production uses globally fixed three-stage Gauss--Legendre collocation with external h/r adaptation. One-stage midpoint remains the baseline and two-stage Gauss an order-convergence cross-check. Local or orbit-varying hp adaptation is deferred; Radau, if triggered by evidence, is a whole-orbit comparison.
<!-- SECTION:NOTES:END -->
