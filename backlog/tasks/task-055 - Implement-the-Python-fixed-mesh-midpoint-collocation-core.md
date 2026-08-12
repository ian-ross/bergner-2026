---
id: TASK-055
title: Implement the Python fixed-mesh midpoint collocation core
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 16:22'
labels:
  - episode-008
  - python
  - numerics
dependencies:
  - TASK-053
  - TASK-054
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the transparent Python reference formulation for fixed-parameter periodic orbits using explicit one-stage Gauss midpoint stages, log-state/log-period coordinates, and the normalized integral phase condition.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 OrbitLayout packs and unpacks endpoint blocks, explicit stage blocks, and log period for arbitrary fixed meshes without a duplicated terminal endpoint
- [ ] #2 The assembler evaluates scaled stage equations, cyclic endpoint updates, and the normalized integral phase condition with a frozen phase reference
- [ ] #3 The assembler returns an explicit sparse CSR Jacobian including state blocks, log-period column, and phase row
- [ ] #4 The N=8 midpoint fixtures cover layout indices, sparsity, residual blocks, phase normalization, and nonsolution vectors deterministically
- [ ] #5 Centered finite-difference directional checks satisfy the versioned Jacobian tolerances
- [ ] #6 The implementation is reusable package code while Episode 008 orchestration remains episode-local
<!-- AC:END -->
