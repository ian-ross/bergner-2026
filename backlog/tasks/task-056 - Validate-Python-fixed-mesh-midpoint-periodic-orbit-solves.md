---
id: TASK-056
title: Validate Python fixed-mesh midpoint periodic-orbit solves
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 20:10'
labels:
  - episode-008
  - python
  - numerics
dependencies:
  - TASK-055
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Demonstrate fixed-parameter periodic-orbit correction from the frozen seed and quantify midpoint period/orbit convergence on uniform meshes without claiming production accuracy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 SciPy sparse least-squares corrects the canonical orbit at N=64 with independently accepted stage, update, and phase residual blocks
- [ ] #2 Uniform N=32, 64, 128, and 256 midpoint results report period, weighted orbit change, residuals, phase energy, solver evaluations, and comparison with the Episode 007 reference cycle
- [ ] #3 The results explicitly distinguish discrete nonlinear convergence from period and continuous-orbit accuracy
- [ ] #4 Failed or nominally successful SciPy solves that miss block tolerances are rejected with diagnostics
- [ ] #5 Curated fixed-mesh reference vectors and residuals are frozen for later Python-to-C++ parity tests
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add reusable fixed-mesh solve and diagnostics contracts around MidpointCollocationAssembler: run scipy.optimize.least_squares(method="trf") with the analytic CSR Jacobian, version explicit stage/update/phase tolerances, compute max/RMS block norms and finite/positivity checks independently, and accept only when both SciPy termination and every numerical block criterion pass. Preserve SciPy status/message/cost/optimality/evaluation counts and rejection reasons so nominal successes and failures remain diagnosable.
2. Define the fixed discretization-independent weighted orbit metric from the documented endpoint/stage quadrature with frozen seed-derived state scales, and expose correction-from-initial-guess plus phase-aligned comparison to the Episode 007 Hermite reference. Keep physical period error and continuous-reference orbit error separate from discrete nonlinear residual diagnostics.
3. Add an Episode 008 standalone orchestration script that verifies and loads the frozen seed, constructs uniform midpoint cases at N=32, 64, 128, and 256, corrects each fixed-parameter orbit, records period, weighted orbit changes/comparisons, residual blocks, phase energy, SciPy evaluations/termination, and emits deterministic schema/method metadata. Include a --check path for committed artifact drift.
4. Freeze curated Episode 008 fixed-mesh outputs for migration: a human-readable convergence/diagnostic artifact plus language-neutral packed vectors and independently recomputed residual vectors (including the canonical accepted N=64 parity case), with shapes, ordering, tolerances, provenance, and checksums documented for later Python-to-C++ tests.
5. Add focused tests for N=64 acceptance, all four convergence rows and required diagnostics, weighted metrics/reference comparisons, rejection of failed and nominally successful solves that miss any block tolerance, deterministic artifact regeneration, and exact frozen-vector/residual loading.
6. Update the Episode 008 README/docs to state the observed convergence evidence and explicitly warn that discrete nonlinear convergence does not establish period or continuous-orbit accuracy. Run artifact regeneration checks, focused tests, the full Python suite, compile/whitespace checks, and self-review before checking acceptance criteria and completing the task.
<!-- SECTION:PLAN:END -->
