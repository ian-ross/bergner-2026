---
id: TASK-062
title: Complete higher-order and adaptive-mesh design for Episode 008
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 14:17'
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

- Design interview decision: fixed-mesh higher-order qualification will use four reproducibly seeded points: T=225 K, w=0.1 m/s; T=210 K at rho=0; and T=210 K at rho=-0.15 and +0.15. The canonical point receives the fullest order/mesh ladder and independent IVP comparison; the other points guard against single-orbit tuning. Near-Hopf and full-slice qualification waits for adaptive continuation.

- Design interview decision: higher-order uniform qualification ladder: canonical 225 K/0.1 m s^-1 retains midpoint N=64,128,256, runs two-stage Gauss N=32,64,128 and three-stage Gauss N=16,32,64; each T=210 K guard point runs two-stage N=64,128 and three-stage N=32,64. Coarse failures remain diagnostic evidence. Qualification checks same-order refinement, order improvement at comparable system size, 1e-3 best-solution period/orbit convergence, independent defect reduction, canonical independent-IVP agreement to 1e-3, and Python/C++ parity.

- Design interview decision: Radau IIA remains evidence-triggered, not routine. Trigger a whole-orbit three-stage Radau comparison if, after two adaptive Gauss refinement/remesh cycles, any qualification point has: defect <1e-4 but period/orbit change >1e-3; Gauss-vs-IVP error >1e-3 while DOP853 and IVP Radau agree; persistent resolved-layer polynomial ringing/nonphysical stage values; convergence stagnation before the mesh cap despite targeted refinement; or trivial Floquet error >1e-3 with residual/defect gates passing. NOX difficulty alone is insufficient until scaling, mesh placement, and transfer are ruled out.
<!-- SECTION:NOTES:END -->
