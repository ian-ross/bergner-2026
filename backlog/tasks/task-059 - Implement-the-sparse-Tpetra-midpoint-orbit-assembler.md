---
id: TASK-059
title: Implement the sparse Tpetra midpoint orbit assembler
status: To Do
assignee: []
created_date: '2026-08-12 12:52'
labels:
  - episode-008
  - cpp
  - trilinos
  - numerics
dependencies:
  - TASK-054
  - TASK-056
  - TASK-058
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the serial one-rank Tpetra layout, residual, sparse graph, and Jacobian assembly for the fixed-mesh midpoint periodic-orbit base system, matching frozen Python fixtures before adding NOX solves.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A serial OrbitLayout owns all endpoint, stage, log-period, and residual-row indices through Tpetra maps
- [ ] #2 The fixed graph represents local stage/update couplings, periodic wraparound, the global log-period column, and normalized phase row and is reused while the layout is fixed
- [ ] #3 Residuals match Python component-by-component on converged and nonsolution N=8 and N=64 fixtures within the versioned parity tolerance
- [ ] #4 The assembled Tpetra Jacobian and normalized parameter columns pass directional finite-difference checks
- [ ] #5 Diagnostics report residuals by block, phase energy, scaling, and interval identifiers without assuming distributed ownership
<!-- AC:END -->
