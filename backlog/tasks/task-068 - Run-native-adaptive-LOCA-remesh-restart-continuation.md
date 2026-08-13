---
id: TASK-068
title: Run native adaptive LOCA remesh/restart continuation
status: To Do
assignee: []
created_date: '2026-08-13 15:35'
updated_date: '2026-08-13 16:11'
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
