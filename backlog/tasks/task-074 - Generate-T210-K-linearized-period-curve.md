---
id: TASK-074
title: Generate T=210 K linearized-period curve
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-25 10:46'
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
- [x] #1 Native C++ equilibrium continuation over w=5e-4..2 m/s records complex-pair eigenvalues, P_lin=2*pi/abs(Im(lambda)), invalid/gap reasons, and exact Episode 006 Hopf anchors
- [x] #2 The artifact follows the production schema, tracks eigenpair continuity, refines samples by the documented log-period holdout rule, and never clips or invents finite periods
- [x] #3 Stratified Python physical-Jacobian parity and exact Hopf-frequency checks meet the documented tolerances
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review the documented exact-T=210 K linearized-period contract, TASK-070 production schema requirements, Episode 006 native LOCA Hopf anchors, and existing C++ equilibrium/eigenvalue interfaces; confirm the available uv/cmake/ninja/C++ executable toolchain.
2. Implement a reproducible Episode 008 generator for the T=210 K linearized-period artifact that drives native C++ equilibrium continuation over w=5e-4..2 m/s, includes the initial 401 log-spaced grid plus exact Episode 006 Hopf anchors, records physical-Jacobian eigenvalues, P_lin=2*pi/abs(Im(lambda)), validity/gap reasons, provenance/checksums, and --check mode.
3. Add or extend C++/Python seams as needed so eigenpair continuity is explicit: track the conjugate pair by continuation distance/eigenvector overlap, preserve invalid rows for real-pair or frequency-floor cases, and avoid clipping or fabricating finite periods.
4. Implement the documented shape-preserving log(P_lin) holdout refinement loop, inserting additional native C++ samples until max |Delta log(P_lin)| <= 2e-3 on valid continuous segments while never interpolating across invalid/gap/Hopf-boundary rows.
5. Add stratified validation: compare selected native rows against independent Python physical-Jacobian/eigenvalue calculations and check exact T=210 K Hopf-anchor frequencies against Episode 006 native LOCA anchors at relative tolerance 1e-8.
6. Document the artifact and command in Episode 008 docs/README, add focused pytest coverage for schema validity, continuity/refinement/no-clipping, Hopf-frequency parity, and Python parity, then run the generator --check, production validator, focused tests, relevant C++ build/tests, full pytest as feasible, and git diff --check before closing TASK-074.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-074: moved task to In Progress, assigned to @iross, reviewed dependencies TASK-069/TASK-070 and Episode 008 schema/decision docs, confirmed uv/cmake/ninja and existing C++ model executable are available, and drafted the implementation plan. Pausing before coding pending plan approval.

Implemented TASK-074 linearized-period production artifact and validation path. Added `generate_t210_linearized_period_curve.py`, `outputs/t210_linearized_period_curve.json`, `docs/task074-t210-linearized-period-curve.md`, focused tests, and a small schema-validator allowance for explicit linearized-period gap rows with null period/frequency. Updated Episode 008 docs and regenerated dependent provenance/check artifacts after documentation hashes changed.

Validation run:
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_t210_linearized_period_curve.py --check`: current
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/t210_linearized_period_curve.json`: valid
- TASK-071/TASK-072/TASK-073/TASK-068 reconciliation generators `--check`: current after provenance regeneration
- `uv run pytest tests/test_episode8_t210_linearized_period_curve.py tests/test_episode8_production_schema.py -q`: 20 passed
- `uv run pytest -q`: 357 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed
<!-- SECTION:NOTES:END -->
