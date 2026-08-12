---
id: TASK-054
title: Generate shared Gauss collocation coefficient tables
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 15:46'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define a versioned canonical JSON schema for Gauss-Legendre rules with 1–3 stages, including exact/symbolic nodes, Butcher coefficients and weights, integrated Lagrange polynomials, independent off-collocation check nodes/evaluation matrices, 17-digit decimal values, and a deterministic payload checksum.
2. Add an Episode 008 SymPy generator that derives every coefficient from Lagrange polynomials, renders the canonical JSON plus generated Python and C++ tables deterministically, and supports a non-mutating --check mode that reports artifact drift.
3. Commit generated runtime tables in the reusable Python package and shared LOCA C++ include tree, keeping both outputs free of runtime SymPy dependencies; document regeneration and artifact locations in the Episode 008 README.
4. Add focused tests that independently verify schema/checksum integrity, stage/order metadata, Runge–Kutta identities, transfer/defect evaluation data, quadrature and collocation polynomial exactness for orders 2/4/6, generated Python/C++ parity, and byte-for-byte regeneration/drift detection.
5. Run the generator check, focused tests, C++ header compilation smoke check, and full Python suite; review the diff, update task acceptance criteria/notes/final summary, and commit the implementation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reviewed TASK-054, completed dependency TASK-053, the Episode 008 README, and the binding collocation-phase decisions.
- Confirmed uv, Python, SymPy 1.14, pytest 9.1, git, the reusable Python package tree, and the shared LOCA C++ include tree are available.
- The only pre-existing untracked path is `.pi-subagents/`; implementation will leave it untouched.

- Implemented a deterministic SymPy generator for shifted Gauss–Legendre rules with 1–3 stages. It derives exact nodes, Lagrange bases, stage/update integrals, ascending-power transfer coefficients, and off-collocation defect matrices at independently derived (r+1)-point Gauss nodes.
- Generated the canonical checksummed JSON artifact plus standard-library-only Python and C++ tables, exposed the Python rule lookup through the package, and documented regeneration/checksum/runtime behavior.
- Added focused coverage for symbolic derivation parity, 17-significant-digit literals, canonical checksum integrity, row-sum identities, Gauss degree 2r-1 exactness, collocation monomial integration, transfer/defect matrices, byte-for-byte regeneration, deliberate drift failure, and C++17 compilation/metadata parity. Focused result: 7 passed; generator --check, C++ smoke compilation, py_compile, and git diff whitespace checks passed.
<!-- SECTION:NOTES:END -->
