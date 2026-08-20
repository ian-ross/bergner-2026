---
id: TASK-066
title: Implement native higher-order fixed-mesh LOCA continuation
status: Done
assignee:
  - '@iross'
created_date: '2026-08-13 15:35'
updated_date: '2026-08-20 15:32'
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
- [x] #1 Native LOCA supports two- and three-stage fixed-mesh Gauss base groups with no duplicate arclength row, the frozen discretization-independent metric, and analytic normalized parameter columns
- [x] #2 Deterministic signed fixed-parameter bootstrap, native predictor/tangent/arclength/adaptive-step ownership, accepted/rejected/retry events, and controlled phase-reference rebuild semantics are preserved for higher-order layouts
- [x] #3 Three-stage native LOCA replays the T=225 K move to the spine, both short spine directions including exact T=210 K, and both signed T=210 K rho guard segments with exact target landing
- [x] #4 Native accepted points pass fixed-parameter residual/phase/positivity/linear gates and match independent Python higher-order corrections at identical coordinates within versioned period and weighted-orbit tolerances
- [x] #5 Curated artifacts contain native-emitted higher-order vectors, rule/mesh/metric dimensions, branch/bootstrap/refresh lineage, truthful LOCA event accounting, checksums, and stale-executable guards
- [x] #6 Focused tests cover dimensions, metric semantics, DfDp, bootstrap orientation, native rejection/retry, phase refresh, exact endpoints, vector provenance, deterministic regeneration, and midpoint regression
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

- Generalized native fixed-mesh LOCA from midpoint to frozen one-/two-/three-stage Gauss layouts. The base model remains square at 3N(r+1)+1 and LOCA alone owns the one-coordinate Arc Length extension. The weighted Thyra group now gives endpoints and all quadrature-weighted stages one half of the orbit weight each, independent of N and r; log-period and active-coordinate weights remain one.
- Preserved analytic normalized rho/T-hat DfDp through ContinuationModelEvaluator and added direct Thyra OUT_ARG_DfDp centered-difference evidence for r=2 and r=3. Relative errors range from 1.10e-10 to 1.55e-9 against a 2e-6 gate, with explicit restoration of the center environment after trial evaluations.
- Generalized signed deterministic bootstrap, Restart tangent injection, native Secant/Arc Length/Adaptive ownership, and all-stage phase-reference refresh. Native evidence records signed/canonicalized tangent orientation and norm, initial step direction, bootstrap halving, controlled full-stack rebuild identity, physical-coordinate preservation, source-stage/reference identity, and semantic refresh-before-consumer chronology.
- Replayed all five three-stage N=32 branches: T=225 K to exact spine, positive spine to T_hat=0.44, negative spine to exact T_hat=-0.2/T=210 K, and exact rho=-0.15/+0.15 T=210 K guards. The artifact contains 32 C++-emitted accepted vectors, two controlled refreshes, truthful callback/save/raw-counter reconciliation, and deterministic forced rejection/reduced-retry evidence.
- Independently corrected every native coordinate with Python three-stage fixed-mesh solves from deterministic Python-only seed banks. Maximum native/Python period relative error is 1.58e-12 and weighted-orbit error is 2.83e-12, both below 2e-7. Maximum native stage/update/phase residuals are 2.99e-12, 3.13e-12, and 1.73e-17; maximum perturbed NOX/KLU2 recorrection distance is 2.73e-12.
- Added deterministic native higher-order JSON/NPZ generation with native-only vector provenance, source/CMake/runtime/compiler/Trilinos identities, exact executable SHA-256, Release-build guard, and stale source/executable tests. Regenerated all transitive source-bound midpoint and TASK-065 manifests.
- Validation: clean Release CMake/Ninja build with no compiler warnings; focused C++/native/Tpetra suite 74 passed; final full suite 248 passed, 1 skipped with only three pre-existing unrelated overflow warnings; all affected artifact --check commands, py_compile, git diff --check, and no-staged-files check passed. Independent correctness/contract reviews were resolved and final re-review reported no findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented native higher-order fixed-mesh LOCA continuation for Episode 008.

Changes:
- Generalized the square one-parameter Thyra/LOCA family and weighted group to one-, two-, and three-stage Gauss layouts without adding a duplicate arclength row.
- Added a discretization-independent endpoint/stage quadrature metric, analytic normalized rho/T-hat DfDp plumbing, signed deterministic bootstrap and Restart tangent evidence, and all-stage controlled phase-reference refreshes.
- Replayed all five required three-stage N=32 branches with native Secant/Arc Length/Adaptive ownership and exact landing at the spine, T=226 K, T=210 K, and rho=-0.15/+0.15 targets.
- Enforced accepted-point residual, phase, positivity/finiteness, phase-energy, and real KLU2 activity gates; recorded truthful native callback/save/rejection/retry/raw-counter accounting.
- Added independent Python correction at every native coordinate, using deterministic Python-only seeds rather than native vectors. All 32 points pass the 2e-7 period and weighted-orbit parity contract by several orders of magnitude.
- Added deterministic native higher-order JSON/NPZ artifacts containing only C++-emitted vectors, rule/mesh/metric dimensions, branch/bootstrap/refresh lineage, exact executable and source/build/runtime provenance, and stale-binary guards.
- Added focused tests for dimensions, metric semantics, Thyra DfDp, bootstrap orientation and halving, native retry, phase refresh, exact endpoints, event accounting, vector provenance, regeneration, and midpoint compatibility.
- Updated Episode 008 documentation and regenerated transitive source-bound artifacts.

Validation:
- Clean Release CMake/Ninja build without compiler warnings.
- Full suite: 248 passed, 1 skipped; three pre-existing unrelated overflow warnings.
- All affected artifact checks, py_compile, git diff --check, and independent final reviews passed.

Scope:
- Results remain fixed-mesh continuation evidence; adaptive h/r reference work proceeds in TASK-067.
<!-- SECTION:FINAL_SUMMARY:END -->
