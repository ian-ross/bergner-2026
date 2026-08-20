---
id: TASK-067
title: Implement Python h/r adaptive collocation reference
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-13 15:35'
updated_date: '2026-08-20 15:57'
labels:
  - episode-008
  - python
  - numerics
  - adaptivity
dependencies:
  - TASK-066
references:
  - src/bergner_spichtinger_2026/periodic_orbits.py
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the transparent Python reference for TASK-062 v1 external h/r adaptation on globally fixed three-stage Gauss--Legendre orbits. The reference owns two-grid defect evaluation, defect-driven splitting, bounded monitor redistribution, collocation-polynomial transfer, fixed-parameter correction, and reproducible remesh diagnostics; it does not emulate native LOCA remesh ownership.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The independent defect implementation evaluates next-higher Gauss and staggered dyadic grids, applies the material-disagreement, fixed-128-bin recurrence, and 16-point probe rules, and exposes per-element/max defects plus endpoint/jump/grid-disagreement diagnostics
- [ ] #2 Old collocation polynomials transfer solution, phase reference, and tangent to the new mesh; fixed-parameter correction and v1 restart gates implement the exact three-attempt retry order and deterministic rebootstrap for tangent-only failure
- [ ] #3 Curated artifacts emit deterministic language-neutral adaptive/remesh fixtures consumed by TASK-068, including inputs and intermediate expected results for defect grids, probe escalation, monitor construction, marking, movement, transfer, restart/retry, schemas, and checksums; focused tests cover those contracts and fixed-mesh compatibility
- [ ] #4 The v1 r monitor evaluates all four densities at 16 equal subcell midpoints per current element, uses documented weighted deterministic normalization, builds and inverts the piecewise-constant cumulative monitor with the stated tolerance, and applies simultaneous global-beta feasibility retries through 2^-20 with r_movement_stalled fallback
- [ ] #5 The deterministic adaptation cycle distinguishes ordinary h+r, pure-r, forced single-split h+r after stagnation, convergence stop, N=256 soft-cap escalation, and N=512/cycle-budget resolution_unresolved outcomes
- [ ] #6 Adaptive qualification runs start from N=32 at the four fixed qualification points and record convergence, meshes, defects, period/orbit changes, phase refreshes, unresolved budgets, aliasing, and active defect/convergence/ringing/nonphysical-value Radau triggers without hiding failures; broader IVP-based and all Floquet-dependent evidence are not_evaluated through TASK-068
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use TASK-064's generic Python collocation polynomial and TASK-066's accepted three-stage fixed-mesh points as the baseline. Define versioned adaptive-state, remesh-event, terminal-status, and language-neutral fixture schemas; record Floquet and broader IVP/Radau evidence as not_evaluated in this task.
2. Implement the two-grid independent defect pipeline exactly as documented: next-higher Gauss and dyadic evaluations, scaled per-component and per-element maxima, endpoint/jump diagnostics, material disagreement, 16-point local probes, periodic 128-bin recurrence, stable tie-breaking, and defect-only scientific/h-marking authority.
3. Implement the deterministic composite r monitor. Sample D,V,C,A_nuc at 16 equal subcell midpoints per old element; apply ordered weighted max-rescaling, zero handling, phase-average normalization, winsorization, and renormalization; build the piecewise-constant CDF and invert targets with the specified binary64 tolerance.
4. Implement the complete deterministic adaptation controller: ordinary defect-driven h+r marking, pure-r movement while convergence is outstanding, forced maximum-defect single split after stagnant pure-r cycles, convergence stop, 50% growth limit, N=256 soft-cap escalation, N=512 hard cap, eight-cycle budget, and explicit resolution_unresolved/r_movement_stalled outcomes.
5. Implement globally relaxed r movement without coordinate-wise projection. Form simultaneous targets, halve beta through 2^-20 until displacement, width, and cyclic adjacent-ratio bounds pass, otherwise retain the old mesh and record the stalled outcome.
6. Implement collocation-polynomial transfer of solution, phase reference, and tangent followed by fixed-parameter correction on the new mesh. Enforce restart residual/phase/positivity/change/tangent gates, the exact k>0 and pure-r three-attempt retry sequences, full phase refresh on remesh, and deterministic two-point rebootstrap for tangent-only failure.
7. Run adaptive qualification from N=32 at the four fixed points. Persist every cycle's mesh, monitor, marked set, transfer correction, period/orbit convergence, defects, phase diagnostics, caps, aliasing, retries, terminal status, and active defect/convergence/ringing/nonphysical-value Radau evidence without hiding failures.
8. Emit deterministic curated adaptive artifacts plus language-neutral remesh fixtures for TASK-068. Include raw inputs and intermediate expected outputs for checks/probes, normalization/CDF inversion, marking, movement feasibility, transfer, correction, retry/rebootstrap, phase refresh, schemas, and checksums, with synthetic localized and edge cases.
9. Add focused tests for all deterministic rules, zero/nonfinite densities, circular recurrence, tie-breaking, cap transitions, pure-r and h+r retries, transfer order accuracy, restart acceptance/rejection, fixed-mesh compatibility, fixture regeneration, and terminal evidence preservation.
10. Update documentation with observed adaptive qualification behavior; run focused/full Python tests, artifact --check, py_compile, numerical invariants, diff checks, self-review, and independent numerical/test review before completion.
<!-- SECTION:PLAN:END -->
