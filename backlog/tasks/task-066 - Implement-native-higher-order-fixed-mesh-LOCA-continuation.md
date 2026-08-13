---
id: TASK-066
title: Implement native higher-order fixed-mesh LOCA continuation
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 16:11'
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
1. Consume the accepted TASK-065 higher-order correction fixtures and review the TASK-061 native-LOCA event, bootstrap, metric, refresh, and provenance contracts. Freeze a rule-aware LOCA formulation version while preserving midpoint behavior and the square base-group/no-duplicate-arclength invariant.
2. Generalize the one-parameter Thyra/LOCA family and weighted group to r-stage fixed meshes. Use the same analytic normalized parameter columns and the frozen discretization-independent continuation metric, with endpoint and all stage representations normalized so changing r or N does not change orbit weight; keep unit log-period and active-coordinate weights.
3. Generalize deterministic signed fixed-parameter bootstrap and Restart tangent injection to higher-order vectors. Preserve requested-step halving, excessive weighted-change rejection, orientation checks, bootstrap/native event separation, and exact target landing.
4. Rebuild native branch orchestration for three-stage Gauss using accepted TASK-065 origins. Replay the T=225 K move to the exact spine, both spine directions including exact T=210 K, and both signed T=210 K rho guard segments. Keep references immutable within each segment and perform controlled full-stack refreshes at the established boundaries.
5. Preserve native LOCA ownership of Secant prediction, tangent construction, pseudo-arclength constraint, adaptive step sizing, rejection, and retry. Record truthful callback/save partitions, raw versus derived counters, attempted/accepted coordinates, reduced retries, phase lineage, and fixed base/extended dimensions.
6. At every native accepted coordinate, run an independent Python higher-order fixed-parameter correction initialized from frozen Python higher-order branch data rather than native vectors. Enforce residual/phase/positivity/linear gates and versioned period/weighted-orbit parity, while retaining nearest transparent-branch diagnostics separately.
7. Emit deterministic native higher-order JSON/NPZ artifacts containing only C++-emitted vectors, rule/mesh/metric metadata, bootstrap/branch/refresh lineage, solver diagnostics, checksums, source/build/runtime fingerprints, and stale-executable/vector-origin guards with --check support.
8. Add focused tests for rule-aware dimensions, metric normalization across r, DfDp, bootstrap orientation/halving, native rejection/retry, immutable reference and refresh rebuilds, exact endpoints, event accounting, Python parity independence, vector provenance, deterministic regeneration, and midpoint regression.
9. Update documentation and validate clean CMake/Ninja builds, all five native branches, focused C++/Python integration tests, artifact checks, the full applicable suite, compiler/diff checks, self-review, and independent correctness/test-quality review.
<!-- SECTION:PLAN:END -->
