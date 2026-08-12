---
id: TASK-057
title: Implement Python fixed-mesh pseudo-arclength orbit continuation
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 21:00'
labels:
  - episode-008
  - python
  - continuation
dependencies:
  - TASK-056
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the transparent Python reference continuation path on an unchanged midpoint mesh, including normalized coordinates, weighted arclength, deterministic two-point branch bootstrap, and segmented phase references.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The augmented Python corrector uses the discretization-independent weighted metric for secants, tangents, predictors, and arclength
- [ ] #2 Every direction starts from a deterministic fixed-parameter corrected neighbor with step-halving recovery and branch-bootstrap provenance
- [ ] #3 A fixed-temperature branch continues from the Episode 007 point to the exact T=225 K spine coordinate
- [ ] #4 Short T-hat spine and T=210 K rho slice segments converge in both requested directions on a fixed midpoint mesh
- [ ] #5 Phase references remain frozen within segments and refresh only through recorded controlled restarts
- [ ] #6 Continuation outputs include accepted/rejected steps, block residuals, physical and normalized coordinates, period, phase diagnostics, and branch orientation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the reusable fixed-mesh orbit core with normalized path adapters for fixed-T rho and spine T-hat coordinates, using the validated Episode 006 lower/upper Hopf loci and recording both normalized and physical T/log(w)/w values. Add a versioned continuation metric whose endpoint/stage quadrature weights, frozen exact seed-derived state scales, log-period weight, and active-coordinate weight define one inner product used for distances, secants, tangent normalization, predictors, and the pseudo-arclength row.
2. Implement the transparent Python augmented pseudo-arclength corrector around the midpoint base equations: append the active normalized coordinate and weighted arclength constraint, assemble the state Jacobian plus parameter and arclength rows as sparse CSR, independently gate stage/update/phase/arclength residuals and finite physical values, and preserve SciPy termination/evaluation diagnostics for rejection records.
3. Implement deterministic branch orchestration on an unchanged midpoint mesh. Bootstrap each signed direction with a fixed-parameter corrected neighbor, halve failed or excessive startup steps, record every attempt and the accepted two-point secant/orientation, then perform adaptive accepted/rejected predictor-corrector steps with exact-target landing where required. Keep each phase reference immutable for a segment and make refreshes explicit controlled restart events with new reference IDs and restart provenance.
4. Add an Episode 008 standalone generator that starts from the accepted Episode 007 N=64 midpoint orbit, reaches the exact T=225 K spine coordinate at fixed temperature, runs short signed T-hat spine validation segments, obtains the exact T=210 K spine seed, and runs short signed rho slice segments. Emit deterministic curated JSON/NPZ continuation artifacts containing branch orientation, bootstrap/restart lineage, accepted and rejected steps, block and arclength residuals, physical/normalized coordinates, period, phase energy/alignment/distance diagnostics, and frozen vectors needed for later Python-to-LOCA parity; support --check regeneration.
5. Add focused tests for metric mesh independence and use in every continuation operation, sparse augmented Jacobian/parameter-column directional checks, deterministic step-halving bootstrap and orientation, exact spine landing, bidirectional spine/slice convergence, fixed reference IDs within segments, controlled refresh semantics, rejection diagnostics, artifact schema/checksums, and byte-for-byte regeneration.
6. Update the Episode 008 README and collocation decision record with the fixed-mesh continuation method, calibrated short-branch evidence, commands, and the explicit warning that this remains a midpoint machinery/parity milestone rather than a production-accuracy result. Run focused and full tests, generator checks, py_compile, whitespace checks, and self-review before completing the acceptance criteria.
<!-- SECTION:PLAN:END -->
