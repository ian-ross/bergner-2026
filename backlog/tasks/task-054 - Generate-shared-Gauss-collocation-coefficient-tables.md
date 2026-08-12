---
id: TASK-054
title: Generate shared Gauss collocation coefficient tables
status: Done
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 16:02'
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
- [x] #1 A committed generator derives collocation nodes, stage coefficients, quadrature weights, integrated Lagrange transfer polynomials, and independent defect-check evaluation data
- [x] #2 A canonical machine-readable artifact records symbolic forms where practical, 17-digit values, family, stage count, formal order, and checksum
- [x] #3 Generated Python and C++ tables are byte-for-byte reproducible without requiring SymPy at runtime
- [x] #4 Tests verify coefficient identities and expected polynomial exactness for one-, two-, and three-stage Gauss-Legendre rules
- [x] #5 Regeneration checks fail when committed generated artifacts drift
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

- Independent review found no mathematical defects and identified hardening opportunities. Applied byte-level UTF-8 comparison/writes with CRLF drift coverage, exact all-table C++/Python parity, independent next-order Legendre-root checks, an immutable public registry, and explicit indexing/orientation documentation.
- A proposed move of SymPy to development-only dependencies was tested and then reverted because the existing public derive_physical_jacobian_expressions API legitimately requires SymPy. The narrower acceptance contract is verified instead: generated table loading/lookup does not import SymPy, while the package preserves its existing symbolic API.
- Final validation: full suite 120 passed / 1 pre-existing explicit skip; 8 focused coefficient tests passed; generator --check, py_compile, C++17 -Wall/-Wextra/-pedantic compilation and all-table parity, blocked-SymPy runtime lookup, and git diff whitespace checks passed. The existing numerical suite emits three known overflow warnings in exploratory solver paths.

- Committed the TASK-054 implementation as a733e67 (`feat(episode-008): generate shared collocation tables`).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a single reproducible coefficient pipeline for the one-, two-, and three-stage Gauss–Legendre collocation rules.

Changes:
- Added an Episode 008 SymPy generator deriving exact collocation nodes, stage coefficients, quadrature weights, integrated Lagrange transfer polynomials, and independent next-order Gauss defect-check matrices.
- Added a canonical checksummed JSON artifact with symbolic forms and 17-significant-digit binary64 literals.
- Generated immutable standard-library-only Python tables and C++17 template specializations from the same artifact, and exposed Python rule lookup through the package API.
- Added byte-level regeneration/check mode that detects newline-only and content drift.
- Documented regeneration, checksum semantics, runtime usage, matrix orientation, and transfer coefficient indexing.
- Added tests for exact symbolic construction, coefficient identities, Gauss degree-2r−1 exactness, collocation/transfer identities, independent check nodes, runtime SymPy isolation, complete Python/C++ table parity, deterministic regeneration, and deliberate drift failure.

Validation:
- Full Python suite: 120 passed, 1 explicitly skipped.
- Focused coefficient suite: 8 passed.
- Generator --check, Python compilation, strict C++17 compilation, runtime no-SymPy-import check, and diff whitespace checks passed.
- Two independent review rounds found no remaining mathematical or implementation blocker after the package-wide SymPy dependency regression was avoided.
<!-- SECTION:FINAL_SUMMARY:END -->
