---
id: TASK-066
title: Implement native higher-order fixed-mesh LOCA continuation
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - collocation
dependencies:
  - TASK-065
references:
  - loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the native sparse LOCA periodic-orbit family from midpoint to fixed-mesh two- and three-stage Gauss--Legendre layouts, then replay the established five-branch continuation contract. LOCA must continue to own pseudo-arclength behavior while bootstrap, phase refresh, parity, and event provenance remain explicit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Native LOCA supports two- and three-stage fixed-mesh Gauss base groups with no duplicate arclength row, the frozen discretization-independent metric, and analytic normalized parameter columns
- [ ] #2 Deterministic signed fixed-parameter bootstrap, native predictor/tangent/arclength/adaptive-step ownership, accepted/rejected/retry events, and controlled phase-reference rebuild semantics are preserved for higher-order layouts
- [ ] #3 Three-stage native LOCA replays the T=225 K move to the spine, both short spine directions including exact T=210 K, and both signed T=210 K rho guard segments with exact target landing
- [ ] #4 Native accepted points pass fixed-parameter residual/phase/positivity/linear gates and match independent Python higher-order corrections at identical coordinates within versioned period and weighted-orbit tolerances
- [ ] #5 Curated artifacts contain native-emitted higher-order vectors, rule/mesh/metric dimensions, branch/bootstrap/refresh lineage, truthful LOCA event accounting, checksums, and stale-executable guards
- [ ] #6 Focused tests cover dimensions, metric semantics, DfDp, bootstrap orientation, native rejection/retry, phase refresh, exact endpoints, vector provenance, deterministic regeneration, and midpoint regression
<!-- AC:END -->
