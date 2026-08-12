---
id: TASK-057
title: Implement Python fixed-mesh pseudo-arclength orbit continuation
status: To Do
assignee: []
created_date: '2026-08-12 12:52'
labels:
  - episode-008
  - python
  - continuation
dependencies:
  - TASK-056
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the transparent Python reference continuation path on an unchanged midpoint mesh, including normalized coordinates, weighted arclength, deterministic two-point branch bootstrap, and segmented phase references.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The augmented Python corrector uses the discretization-independent weighted metric for secants, tangents, predictors, and arclength
- [ ] #2 Every direction starts from a deterministic fixed-parameter corrected neighbor with step-halving recovery and branch-bootstrap provenance
- [ ] #3 A fixed-temperature branch continues from the Episode 007 point to the exact T=225 K spine coordinate
- [ ] #4 Short T-hat spine and T=210 K rho slice segments converge in both requested directions on a fixed midpoint mesh
- [ ] #5 Phase references remain frozen within segments and refresh only through recorded controlled restarts
- [ ] #6 Continuation outputs include accepted/rejected steps, block residuals, physical and normalized coordinates, period, phase diagnostics, and branch orientation
<!-- AC:END -->
