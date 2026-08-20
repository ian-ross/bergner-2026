---
id: TASK-066
title: Implement native higher-order fixed-mesh LOCA continuation
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-13 15:35'
updated_date: '2026-08-20 13:07'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze the TASK-065 higher-order correction inputs and TASK-061 midpoint LOCA behavioral contract, including square base dimensions, no duplicate arclength row, metric normalization, bootstrap, callback accounting, refresh lineage, parity tolerances, and executable fingerprints.
2. Generalize midpoint_loca.hpp to rule-aware fixed meshes: remove midpoint-only guards, make the endpoint/stage continuation metric quadrature-normalized across r, retain analytic DfDp and the weighted Thyra group, and generalize phase-reference refresh over every Gauss stage while preserving midpoint API/output compatibility.
3. Extend the C++ CLI orchestration to consume accepted three-stage TASK-065 fixtures and execute deterministic smoke plus all five native branches with signed fixed-parameter bootstrap, Restart tangent injection, native Arc Length/Secant/Adaptive ownership, exact target landing, rejection/retry evidence, and controlled full-stack phase-reference rebuilds.
4. Add a deterministic higher-order native artifact generator and JSON/NPZ outputs containing only C++-emitted vectors, rule/mesh/metric/base/extended dimensions, branch/bootstrap/refresh/event lineage, fixed-parameter acceptance diagnostics, checksums, and stale-executable/runtime guards.
5. Independently correct every native accepted coordinate through the Python three-stage fixed-mesh formulation using frozen Python higher-order seeds rather than native vectors; enforce residual/phase/positivity/linear gates and versioned period/weighted-orbit parity.
6. Add focused integration tests for r=1/2/3 dimensions and metric invariance, analytic DfDp, bootstrap orientation/halving, native rejection/retry, phase refresh, exact endpoints, truthful event accounting, vector provenance, deterministic regeneration, and unchanged midpoint artifacts/behavior.
7. Update Episode 008 documentation; run clean CMake/Ninja builds, all five branches, focused and full pytest suites, all affected artifact --check commands, py_compile, diagnostics/diff checks, and independent correctness/test review before completing TASK-066.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-066, moved it to In Progress, and assigned it to @iross.
- Reviewed the complete Episode 008 README and collocation decision record, TASK-065 higher-order correction contract/artifacts, TASK-061 midpoint LOCA implementation, native artifact generator/tests, CLI seam, and CMake source-fingerprint setup.
- Confirmed cmake, ninja, uv, C++, Backlog CLI, and /opt/Trilinos are available. The working tree is clean. No code changes have been made pending plan approval.

- User approved the implementation plan; beginning implementation.
<!-- SECTION:NOTES:END -->
