---
id: TASK-054
title: Generate shared Gauss collocation coefficient tables
status: To Do
assignee: []
created_date: '2026-08-12 12:52'
labels:
  - episode-008
  - python
  - cpp
  - numerics
dependencies:
  - TASK-053
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create one reproducible SymPy-derived coefficient source for the one-, two-, and three-stage Gauss-Legendre rules used by the Python and C++ periodic-orbit implementations.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A committed generator derives collocation nodes, stage coefficients, quadrature weights, integrated Lagrange transfer polynomials, and independent defect-check evaluation data
- [ ] #2 A canonical machine-readable artifact records symbolic forms where practical, 17-digit values, family, stage count, formal order, and checksum
- [ ] #3 Generated Python and C++ tables are byte-for-byte reproducible without requiring SymPy at runtime
- [ ] #4 Tests verify coefficient identities and expected polynomial exactness for one-, two-, and three-stage Gauss-Legendre rules
- [ ] #5 Regeneration checks fail when committed generated artifacts drift
<!-- AC:END -->
