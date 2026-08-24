---
id: TASK-074
title: Generate T=210 K linearized-period curve
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 19:02'
labels:
  - episode-008
  - linearized-period
  - validation
dependencies:
  - TASK-069
  - TASK-070
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Compute the lower-panel equilibrium-linearized period curve independently from periodic-orbit continuation for T=210 K over the saved Figure 5 vertical-velocity domain.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Native C++ equilibrium continuation over w=5e-4..2 m/s records complex-pair eigenvalues, P_lin=2*pi/abs(Im(lambda)), invalid/gap reasons, and exact Episode 006 Hopf anchors
- [ ] #2 The artifact follows the production schema, tracks eigenpair continuity, refines samples by the documented log-period holdout rule, and never clips or invents finite periods
- [ ] #3 Stratified Python physical-Jacobian parity and exact Hopf-frequency checks meet the documented tolerances
<!-- AC:END -->
