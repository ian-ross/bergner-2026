---
id: TASK-059
title: Implement the sparse Tpetra midpoint orbit assembler
status: In Progress
assignee:
  - '@pi'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 09:37'
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
- [ ] #1 A serial OrbitLayout owns all endpoint, stage, log-period, and residual-row indices through Tpetra maps
- [ ] #2 The fixed graph represents local stage/update couplings, periodic wraparound, the global log-period column, and normalized phase row and is reused while the layout is fixed
- [ ] #3 Residuals match Python component-by-component on converged and nonsolution N=8 and N=64 fixtures within the versioned parity tolerance
- [ ] #4 The assembled Tpetra Jacobian and normalized parameter columns pass directional finite-difference checks
- [ ] #5 Diagnostics report residuals by block, phase energy, scaling, and interval identifiers without assuming distributed ownership
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
<!-- SECTION:NOTES:END -->
