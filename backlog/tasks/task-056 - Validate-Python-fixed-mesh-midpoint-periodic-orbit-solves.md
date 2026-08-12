---
id: TASK-056
title: Validate Python fixed-mesh midpoint periodic-orbit solves
status: Done
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 20:46'
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
- [x] #1 SciPy sparse least-squares corrects the canonical orbit at N=64 with independently accepted stage, update, and phase residual blocks
- [x] #2 Uniform N=32, 64, 128, and 256 midpoint results report period, weighted orbit change, residuals, phase energy, solver evaluations, and comparison with the Episode 007 reference cycle
- [x] #3 The results explicitly distinguish discrete nonlinear convergence from period and continuous-orbit accuracy
- [x] #4 Failed or nominally successful SciPy solves that miss block tolerances are rejected with diagnostics
- [x] #5 Curated fixed-mesh reference vectors and residuals are frozen for later Python-to-C++ parity tests
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Plan approved; implementation started with Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, and a clean worktree.
- Added reusable strict SciPy TRF correction with the analytic CSR Jacobian, versioned independent stage/update/phase block gates, finite/positivity validation, structured rejection diagnostics, and quadrature-weighted seed/reference orbit comparisons.
- Added the Episode 008 fixed-mesh generator and curated JSON/NPZ artifacts for N=32, 64, 128, and 256. The N=64 migration fixture includes both the accepted solution and a deterministic nonsolution with nontrivial stage, update, and phase residual blocks, documented order/shapes/checksums/provenance, and deterministic byte-for-byte regeneration checks.
- Observed results: N=32 rejected after 1000 evaluations; N=64 accepted at P=2768.508882 s with weighted Episode 007 orbit error 0.172603 and 9 evaluations; N=128 accepted at P=2531.464910 s with error 0.0389869 and 8 evaluations; N=256 accepted at P=2478.674760 s with error 0.00950588 and 8 evaluations. The Episode 007 period is 2461.611268 s, so N=64 remains 12.47% high despite near-machine discrete residuals.
- Independent numerical/artifact/API review found solver-output and generator-check blockers plus parity-fixture weaknesses. These were fixed by safe nonfinite/overflow rejection, unified exact artifact checks, runtime/source provenance, a nontrivial N=64 parity vector, and stronger gate/check tests. A fresh final review found no blockers or fixes worth doing now.
- Final validation: 21 focused midpoint tests passed; full suite passed with 141 passed / 1 pre-existing explicit skip and three known exploratory-solver overflow warnings. Fixed-mesh --check and direct generate(check=True), bootstrap/coefficient regeneration checks, py_compile, and git diff whitespace checks passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Validated the Episode 008 Python fixed-uniform-mesh midpoint periodic-orbit baseline and froze migration fixtures.

Changes:
- Added reusable SciPy TRF correction around the explicit-stage midpoint assembler, using its analytic sparse CSR Jacobian and independently recomputed stage, update, and normalized-phase acceptance gates.
- Added robust diagnostics that reject SciPy failures, nominal successes missing any block tolerance, and malformed/nonfinite physical states or periods without mistaking solver termination for numerical acceptance.
- Added a discretization-independent quadrature-weighted orbit metric and phase-aligned comparison with the frozen Episode 007 Hermite cycle.
- Added a deterministic Episode 008 generator and curated JSON/NPZ outputs for uniform N=32, 64, 128, and 256 cases, including solver evaluations, residual blocks, phase energy, period and orbit errors, runtime/source provenance, array ordering, and checksums.
- Froze accepted and deterministic nonsolution N=64 vectors/residuals for later Python-to-C++ parity.
- Documented that N=64/128/256 solve the discrete equations while period/orbit accuracy converges separately; N=32 is retained as a diagnosed rejection, and no production-accuracy claim is made.

Results:
- N=64: P=2768.508882 s, weighted reference error=0.172603, 9 function evaluations, accepted residual blocks.
- N=128: P=2531.464910 s, weighted reference error=0.0389869, 8 evaluations.
- N=256: P=2478.674760 s, weighted reference error=0.00950588, 8 evaluations.
- Episode 007 reference: P=2461.611268 s; the accepted N=64 period remains 12.47% high.
- N=32: rejected after 1000 evaluations with explicit SciPy and block-tolerance diagnostics.

Validation:
- Focused tests: 21 passed.
- Full suite: 141 passed, 1 explicitly skipped; three known warnings remain in pre-existing exploratory solver paths.
- Deterministic artifact checks, bootstrap/coefficient regeneration, py_compile, whitespace checks, and independent final review passed.
<!-- SECTION:FINAL_SUMMARY:END -->
