---
id: TASK-058
title: Generalize the C++ model for periodic-orbit local derivatives
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 04:49'
labels:
  - episode-008
  - cpp
  - trilinos
dependencies:
  - TASK-057
references:
  - loca/include/bergner_spichtinger_2026_loca/model.hpp
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the validated shared C++ model evaluator to provide value-equivalent transformed dynamics and small local Sacado derivatives with respect to state, temperature, and log vertical velocity.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The generalized evaluator preserves value-level parity with the existing validated no-evaporation C++ and Python model over representative physical states
- [ ] #2 Local Sacado evaluation supplies D_x g, g_T, and g_log_w without differentiating the packed orbit vector
- [ ] #3 T-hat spine and rho slice parameter derivatives apply the documented mappings and chain rules
- [ ] #4 Centered finite-difference tests cover state derivatives, temperature-dependent coefficients, physical control derivatives, and normalized parameter columns
- [ ] #5 Existing equilibrium and Hopf backend behavior remains regression-tested
<!-- AC:END -->
