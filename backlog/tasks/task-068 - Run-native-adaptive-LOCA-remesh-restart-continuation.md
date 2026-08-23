---
id: TASK-068
title: Run native adaptive LOCA remesh/restart continuation
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-13 15:35'
updated_date: '2026-08-23 17:15'
labels:
  - episode-008
  - cpp
  - trilinos
  - loca
  - adaptivity
dependencies:
  - TASK-067
references:
  - loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement structural h/r remesh boundaries around native three-stage Gauss LOCA continuation, migrate the TASK-067 reference behavior into the sparse Tpetra/Thyra/NOX/LOCA stack, and execute the planned spine-and-slices adaptive run. The task produces truthful evidence for review rather than presuming that the first run is final Figure 5 production data.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Native fixed-mesh LOCA segments stop only at accepted points for remeshing; solution/reference/tangent transfer, full Tpetra/Thyra/NOX/LOCA reconstruction, fixed-parameter NOX/KLU2 correction, tangent renormalization or deterministic rebootstrap, exact retry order, and native restart follow the v1 contract
- [ ] #2 Before the adaptive run, frozen TASK-067 nonuniform fixtures pass component-level Python/C++ parity for base residuals, analytic Jacobian and normalized parameter columns, nonuniform phase quadrature, continuation metric, collocation-polynomial transfer, and fixed-parameter correction; C++ defect, probe escalation, monitor, h marking, bounded r movement, mesh/cycle budgets, restart retries, phase-refresh triggers, near-Hopf diagnostics, and single-valued tripwires also match the Python intermediate results
- [ ] #3 Deterministic per-segment artifacts and restart manifests record native vectors or checkpoints, accepted/rejected LOCA events, mesh histories, transfer corrections, defects, period/orbit convergence, phase lineage, terminal target statuses, runtime/memory profiles, source fingerprints, and resumable completion state
- [ ] #4 Stratified native points match independent Python adaptive corrections within versioned tolerances, the planned run can be regenerated or checked, and focused tests cover nonuniform parity, remesh rebuild identity, event partitioning, restart recovery, resume behavior, terminal manifest coverage, and fixed-mesh regressions
- [ ] #5 The adaptive run records near-Hopf amplitude/period approach points and terminal statuses, targeting at least five reliable points when reached, but leaves quadratic/quartic fit review and final connection/gap policy to TASK-069
- [ ] #6 Every accepted segment point and remesh restart passes independent residual/phase/positivity/linear/restart gates; unresolved points, rejections, cap escalations, aliasing, defect/convergence/ringing/nonphysical-value Radau triggers, and tripwires are recorded rather than suppressed; broader IVP-based and all Floquet-dependent evidence are not_evaluated
- [ ] #7 The planned manifest covers the T=225 K move to the spine, both temperature directions over the provisional spine range, and signed rho slices for every target on the provisional 2 K skeleton while retaining exact T=210 K and T=225 K anchors; every target has exactly one terminal status: accepted, resolution_unresolved, near_hopf_stop, tripwire_stop, or failed with a reason
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Consume TASK-067's complete nonuniform/remesh fixture bundle and TASK-066's native higher-order LOCA implementation. Freeze C++ adaptive formulation, event, checkpoint, and run-manifest versions, preserving serial one-rank Tpetra and KLU2 as the reference stack.
2. Before native adaptive continuation, generalize and qualify the C++ higher-order base system on nonuniform meshes. Establish component parity with Python for residuals, analytic Jacobian and normalized parameter columns, nonuniform phase quadrature, continuation metric, collocation-polynomial transfer, and fixed-parameter correction on every frozen fixture.
3. Port the deterministic defect, probe escalation, monitor sampling/normalization/CDF inversion, h marking, global-beta r movement, cycle/cap controller, retry policy, phase-refresh triggers, near-Hopf diagnostics, and single-valued tripwires. Compare every intermediate result with TASK-067 fixtures before coupling adaptation to LOCA.
4. Implement structural remesh orchestration around native fixed-mesh LOCA segments: stop only at accepted points, transfer solution/reference/tangent, rebuild all Tpetra/Thyra/NOX/LOCA objects and KLU2 state, fixed-parameter-correct, enforce restart gates/retries, renormalize or rebootstrap the tangent, and restart with explicit lineage.
5. Implement deterministic per-segment artifacts, checkpoints, and resumable run manifests. Record accepted/rejected callbacks, mesh and transfer histories, solver/phase diagnostics, defects/convergence, cap/alias/Radau/tripwire events, source/build fingerprints, runtime/memory profiles, and exactly one terminal status for every planned target.
6. Validate remesh identity and recovery with focused synthetic and branch smoke runs, including failed transfer, pure-r and h+r retries, tangent-only rebootstrap, phase refresh, process interruption/resume, stale checkpoint rejection, and fixed-mesh regressions.
7. Execute the provisional adaptive spine-and-slices run: T=225 K to the spine, both temperature directions, and both rho directions for every target on the 2 K temperature skeleton, retaining exact T=210 K and T=225 K anchors. Near Hopf, record amplitude/period approach points and target at least five reliable points when reachable; do not decide the final fit/connection policy here.
8. Enforce acceptance independently at every point/restart. Preserve resolution_unresolved, near_hopf_stop, tripwire_stop, and failed outcomes with reasons; never interpolate or suppress failures. Record broader IVP-based and all Floquet-dependent evidence as not_evaluated through this task.
9. Compare a stratified set of native adaptive points with independent Python adaptive correction at identical physical coordinates and versioned tolerances. Regenerate/check the planned run and reconcile every event, checkpoint, target, and terminal status.
10. Update Episode 008 documentation with observed coverage, mesh behavior, convergence, failures, and cost. Run clean builds, fixture parity, focused/full integration tests, artifact/checkpoint regeneration, resume checks, profiling, compiler/diff checks, self-review, and independent numerical/correctness/test review before completion.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-068: moved to In Progress and assigned @iross.
- Reviewed dependency TASK-067 plus documented references: Episode 008 README, collocation-phase decisions, and midpoint_loca.hpp.
- No code changes started yet; awaiting confirmation of the existing implementation plan.

- Added a truthful TASK-068 preparatory native adaptive LOCA manifest generator and curated outputs: episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py, outputs/native_adaptive_loca_manifest.json, and outputs/native_adaptive_loca_manifest_vectors.npz.
- The manifest reconciles TASK-067 adaptive/remesh fixtures with executed native three-stage fixed-mesh LOCA/C++ correction evidence, embeds the v1 remesh/restart contract and retry order, records source/vector fingerprints, and enumerates the provisional spine-and-slices target manifest with explicit terminal statuses. It deliberately records native_adaptive_remesh_executed=false and marks not-yet-run adaptive targets as failed with reasons rather than relabeling fixed-mesh/Python evidence.
- Updated the Episode 008 README with regeneration/check commands and scope boundaries for the new manifest.
- Added focused tests in tests/test_episode8_native_adaptive_loca_manifest.py for current artifacts, v1 contract/retry capture, planned-target coverage and single terminal statuses, vector/source checksums, parity summaries, and near-Hopf scope.
- Verification: uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check; uv run python -m py_compile episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py; uv run pytest tests/test_episode8_native_adaptive_loca_manifest.py -q; uv run pytest -q (267 passed, 1 skipped, 3 warnings).

- Continued TASK-068 by projecting the final TASK-067 nonuniform adaptive meshes into C++ parity fixtures: added scripts/generate_cpp_adaptive_nonuniform_fixtures.py and outputs/cpp_adaptive_nonuniform_fixtures/. The fixtures use final adaptive nonuniform boundaries, refreshed phase references from accepted orbits, and small deterministic solve perturbations.
- Added tests/test_episode8_cpp_adaptive_nonuniform.py to verify fixture determinism/provenance, C++ vs Python residual parity, analytic Jacobian action parity, normalized rho/T-hat parameter-column finite-difference checks, nonuniform phase quadrature through refreshed references, and fixed-parameter NOX/KLU2 correction gates on all four final adaptive qualification meshes.
- Updated the native adaptive manifest to reference the nonuniform C++ fixture parity bundle, and updated README documentation.
- Verification: uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_adaptive_nonuniform_fixtures.py --check; uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check; uv run python -m py_compile both TASK-068 generators; uv run pytest tests/test_episode8_cpp_adaptive_nonuniform.py tests/test_episode8_native_adaptive_loca_manifest.py -q; uv run pytest -q (276 passed, 1 skipped, 3 warnings).

- Extended native C++ nonuniform support with an adaptive-transfer CLI seam. The C++ Gauss rule now exposes transfer coefficients, and bs2026_midpoint_orbit adaptive-transfer deterministically splits nonuniform meshes, transfers solution values, refreshed phase-reference samples/derivatives, and a finite-difference tangent by collocation-polynomial evaluation, then rebuilds a destination assembler to report phase energy.
- Expanded tests/test_episode8_cpp_adaptive_nonuniform.py to verify native continuation metric weights/group dot products and C++ collocation-polynomial solution/phase/tangent transfer against independent Python on representative TASK-067 final nonuniform adaptive meshes.
- Regenerated source-provenance-sensitive Episode 008 manifests/results after the C++ source change: Tpetra midpoint fixture manifest, C++ higher-order fixture/correction artifacts, native midpoint/native higher-order LOCA artifacts, C++ adaptive nonuniform fixtures, and native adaptive manifest.
- Verification: generator --check commands for affected Episode 008 artifacts; uv run python -m py_compile for TASK-068 generators; uv run pytest tests/test_episode8_cpp_adaptive_nonuniform.py tests/test_episode8_native_adaptive_loca_manifest.py -q (18 passed); uv run pytest -q (280 passed, 1 skipped, 3 warnings).

- Added a native adaptive-controller CLI seam that computes the v1 adaptive intermediates on nonuniform Gauss fixtures: independent two-grid defect diagnostics with material probe escalation, endpoint/jump diagnostics, composite 16-subcell r monitor inversion, h marking, bounded global-beta r movement, controller decisions, and restart retry order.
- Expanded tests/test_episode8_cpp_adaptive_nonuniform.py to compare those native adaptive-controller outputs against independent Python TASK-067 adaptive helper functions on representative final nonuniform meshes. Updated the native adaptive manifest/README to include adaptive-controller coverage.
- Regenerated provenance-sensitive Episode 008 artifacts after the C++ CLI change: Tpetra midpoint fixture manifest, C++ higher-order fixture/correction artifacts, native midpoint/native higher-order LOCA artifacts, C++ adaptive nonuniform fixture manifest, and native adaptive manifest.
- Verification: affected generator --check commands; uv run python -m py_compile for TASK-068 generators; uv run pytest tests/test_episode8_cpp_adaptive_nonuniform.py tests/test_episode8_native_adaptive_loca_manifest.py -q (20 passed); uv run pytest -q (282 passed, 1 skipped, 3 warnings).
<!-- SECTION:NOTES:END -->
