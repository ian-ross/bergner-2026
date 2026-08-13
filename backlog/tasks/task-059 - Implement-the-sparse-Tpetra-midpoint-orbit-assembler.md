---
id: TASK-059
title: Implement the sparse Tpetra midpoint orbit assembler
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 10:26'
labels:
  - episode-008
  - cpp
  - trilinos
  - numerics
dependencies:
  - TASK-054
  - TASK-056
  - TASK-058
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the serial one-rank Tpetra layout, residual, sparse graph, and Jacobian assembly for the fixed-mesh midpoint periodic-orbit base system, matching frozen Python fixtures before adding NOX solves.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A serial OrbitLayout owns all endpoint, stage, log-period, and residual-row indices through Tpetra maps
- [x] #2 The fixed graph represents local stage/update couplings, periodic wraparound, the global log-period column, and normalized phase row and is reused while the layout is fixed
- [x] #3 Residuals match Python component-by-component on converged and nonsolution N=8 and N=64 fixtures within the versioned parity tolerance
- [x] #4 The assembled Tpetra Jacobian and normalized parameter columns pass directional finite-difference checks
- [x] #5 Diagnostics report residuals by block, phase energy, scaling, and interval identifiers without assuming distributed ownership
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add a reusable C++ midpoint-orbit core under `loca/include/bergner_spichtinger_2026_loca/` with a serial one-rank `OrbitLayout` that constructs square Tpetra domain/range maps and owns endpoint, stage, log-period, stage-row, update-row, and phase-row global indices, including cyclic endpoint access and explicit ownership validation.
2. Implement immutable fixed-mesh/phase-reference inputs and a midpoint assembler that constructs and fill-completes the Tpetra sparsity graph once, then reuses it for residual and Jacobian fills. Assemble scaled stage/update equations, periodic wraparound, normalized phase row, global log-period column, and rho/T-hat normalized parameter columns from the existing local Sacado derivatives.
3. Add ownership-safe diagnostic summaries that derive stage/update/phase maxima and RMS values, phase energy, state/residual scaling, and offending interval/component identifiers from Tpetra map lookups rather than contiguous distributed-local assumptions.
4. Add an Episode 008 deterministic parity-fixture generator for accepted and nonsolution N=8 cases while reusing the frozen TASK-056 N=64 vectors; expose a focused C++ parity executable/test seam that accepts language-neutral fixture data and emits layout, graph, residual, Jacobian-action, parameter-column, and diagnostic results without adding NOX solving.
5. Add Python-driven integration tests that build the configured Trilinos target and verify N=8/N=64 layout and fixed-graph structure, component-wise residual parity within 1e-11, graph reuse, cyclic/global couplings, Jacobian-vector and normalized rho/T-hat parameter-column centered differences within 1e-6, and diagnostics/interval identifiers for accepted and nonsolution fixtures.
6. Document the Tpetra assembly and fixture-regeneration contracts in the Episode 008 README/design notes, then run fixture checks, focused C++ parity/model/backend regressions, the full Python suite, CMake rebuild, LSP/compile diagnostics, and whitespace checks before self-review and task completion.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-059, assigned it to @pi, and reviewed the completed dependencies TASK-054/TASK-056/TASK-058 plus the binding Episode 008 README and collocation decisions.
- Confirmed a clean worktree and availability of CMake, CTest, Python/uv, Backlog CLI, and the configured Trilinos installation with Tpetra, Thyra adapters, NOX/LOCA, Amesos2, Belos, Ifpack2, and Sacado.
- Verified the existing Python midpoint corrector produces an accepted N=8 discrete solution (17 function evaluations, residual blocks near machine precision), so accepted and nonsolution N=8 fixtures are feasible alongside the frozen N=64 parity vectors.

- Implemented the serial one-rank Tpetra midpoint core: map-owned layout indices, reusable fill-completed graph, scaled residual/Jacobian assembly, periodic wraparound, global log-period coupling, normalized phase row, Sacado-based rho/T-hat columns, finite-input guards, and ownership-safe diagnostics with exact interval/component identifiers.
- Added the `bs2026_midpoint_orbit` parity CLI, deterministic accepted/nonsolution N=8 fixtures, direct translation of frozen TASK-056 N=64 arrays, and a checksummed manifest recording formulation/tolerances, runtime versions, lockfile, upstream artifacts, and source hashes. The generator has a byte-level --check mode.
- Added focused tests for N=8/N=64 layout and graph structure/reuse, all four component-wise residual parity cases, converged/nonsolution semantics, exact diagnostic argmax IDs, direct C++ centered-difference Jv, Python Jv parity, normalized parameter columns, invalid-input guards, frozen N=64 translation, and manifest regeneration.
- Multi-angle independent review found lifetime, N=1 duplicate-column, period-validation, direct-FD, diagnostic, and provenance gaps in the first pass; all were fixed. A final fresh review found no remaining blockers or fixes worth doing now.
- Final validation: fixture generation and --check passed; 12 focused TASK-059 tests passed; 30 combined TASK-059/model/backend/Hopf tests passed; full suite passed with 170 passed / 1 explicit pre-existing skip and three known exploratory-solver overflow warnings. Clean Debug CMake configure/build compiled both C++ targets. py_compile and git diff --check passed. LSP retained stale diagnostics from the previously missing compilation-database link, but the link was repaired and a clean compiler build succeeded. C++ integration tests exercised the configured Trilinos installation without skips.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the serial sparse Tpetra midpoint periodic-orbit assembler and Python migration parity contract.

Changes:
- Added a one-rank `OrbitLayout` with square Tpetra maps owning endpoint, explicit-stage, log-period, stage-row, update-row, and phase-row indices, with cyclic endpoint indexing and explicit ownership checks.
- Added a retained fill-completed sparse graph reused by every Jacobian on the fixed layout, covering local endpoint/stage blocks, periodic wraparound, the global log-period column, and the normalized stage-only phase row.
- Added scaled Tpetra residual and analytic Jacobian assembly using the shared local Sacado evaluator, plus normalized rho and T-hat parameter columns without packed-orbit AD.
- Added checked finite-input handling and ownership-safe diagnostics for stage/update max and RMS values, normalized phase residual/energy, state scaling, and exact largest-residual interval/component identifiers.
- Added a dedicated C++ parity CLI and deterministic, checksummed accepted/nonsolution fixtures for N=8 and N=64. N=64 directly translates and verifies the frozen TASK-056 arrays; the manifest records method/tolerance, runtime, lockfile, source, and upstream provenance.
- Added focused integration tests for component parity, graph structure/reuse, cyclic/global couplings, direct C++ and Python Jacobian directional checks, normalized parameter finite differences, diagnostics, invalid-input guards, frozen-vector translation, and byte-level regeneration.
- Updated Episode 008 documentation with the Tpetra assembly, tolerance, fixture, and scope contracts. NOX/Thyra solving remains TASK-060 scope.

Validation:
- Full suite: 170 passed, 1 pre-existing explicit skip; three known exploratory-solver overflow warnings.
- Focused TASK-059: 12 passed.
- Combined TASK-059 plus C++ model/backend/Hopf regressions: 30 passed.
- Clean Debug CMake configure/build passed for `bs2026_midpoint_orbit` and `bs2026_loca_model`.
- Fixture generation/--check, py_compile, and git diff whitespace checks passed.
- Two independent review rounds found no remaining blocker after fixes.
<!-- SECTION:FINAL_SUMMARY:END -->
