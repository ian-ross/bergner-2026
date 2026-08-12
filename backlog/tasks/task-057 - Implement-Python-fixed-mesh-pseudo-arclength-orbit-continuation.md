---
id: TASK-057
title: Implement Python fixed-mesh pseudo-arclength orbit continuation
status: Done
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-12 21:42'
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
- [x] #1 The augmented Python corrector uses the discretization-independent weighted metric for secants, tangents, predictors, and arclength
- [x] #2 Every direction starts from a deterministic fixed-parameter corrected neighbor with step-halving recovery and branch-bootstrap provenance
- [x] #3 A fixed-temperature branch continues from the Episode 007 point to the exact T=225 K spine coordinate
- [x] #4 Short T-hat spine and T=210 K rho slice segments converge in both requested directions on a fixed midpoint mesh
- [x] #5 Phase references remain frozen within segments and refresh only through recorded controlled restarts
- [x] #6 Continuation outputs include accepted/rejected steps, block residuals, physical and normalized coordinates, period, phase diagnostics, and branch orientation
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Plan approved; implementation started from a clean worktree. Confirmed Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, uv, git, and backlog CLI are available.
- Reviewed the completed TASK-056 midpoint solver/artifacts, Episode 008 contracts, and Episode 006 native LOCA Hopf-locus CSV. Exact locus rows give the T=225 K spine w=0.1445622536840862 m/s (bootstrap rho=-0.2639524255 at w=0.1) and the T=210 K spine w=0.0532671872264416 m/s.

- Added analytic transformed-field derivatives with respect to physical T and log(w), including all temperature-dependent coefficients. The normalized rho and T-hat parameter columns apply the documented chain rules; centered differences are tests only.
- Implemented the fixed-mesh family/path adapters, half-endpoint/half-stage weighted metric, sparse augmented pseudo-arclength corrector, strict independent block gates, deterministic fixed-parameter bootstrap with halving, exact-target landing, and explicit controlled phase-reference restarts.
- Generated curated N=64 continuation JSON/NPZ artifacts. The fixed-T 225 K branch reaches the exact spine; signed spine branches reach 226 K and the exact 210 K spine through a genuine Delta T-hat=-0.6 multi-step segment; signed 210 K rho branches reach -0.15 and +0.15. One excessive bootstrap attempt is frozen as a rejection before deterministic halving recovery.
- Recorded two controlled phase-reference refreshes. Segment points/events retain one immutable reference ID; artifacts include residual blocks, normalized/physical coordinates, periods, phase diagnostics, orientations, vectors, metric diagonals, restart lineage, checksums, and explicit non-production-accuracy scope.

- Independent three-angle review found unsafe generic contracts around target overshoot and path-changing restarts, plus artifact/test gaps. Fixed them by rejecting crossing pseudo-arclength points in favor of exact landing, requiring physical T/log(w) preservation and all residual gates at restarts, enforcing point/family/metric compatibility, safely rejecting malformed optimizer shapes, retaining cost/optimality, hashing the analytic-derivative source, separating accepted/rejected/informational event counts, and independently testing every endpoint/restart/dtype.
- Final validation after fixes: 32 focused Episode 008 midpoint/continuation tests passed; full suite passed with 152 passed / 1 explicit pre-existing skip and three known exploratory-solver overflow warnings. Both midpoint and continuation generators pass byte-for-byte --check, py_compile and git diff whitespace checks pass.

- Follow-up review caught epsilon-scale near-target ambiguity and incomplete artifact acceptance tests. Exact success now requires coordinate equality; near-target and crossing cases route through exact landing or rejection. Tests now prove the event-count partition, both refresh semantics/lineage/residual gates, all five exact endpoints, source provenance, solver diagnostic schema, and stored little-endian dtypes. A final fresh targeted review found no blockers or fixes worth doing now.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented the transparent Python fixed-mesh pseudo-arclength periodic-orbit continuation reference for Episode 008.

Changes:
- Added normalized fixed-temperature rho and spine T-hat path adapters backed by shape-preserving interpolation of the validated Episode 006 native-LOCA Hopf loci.
- Added analytic transformed-field derivatives with respect to T and log(w), including all temperature-dependent model coefficients, and assembled normalized rho/T-hat parameter columns with the documented chain rules.
- Added a discretization-independent continuation metric with half endpoint/half explicit-stage quadrature weighting, exact frozen Episode 007 state scales, and unit log-period/active-coordinate weights. The same metric drives secants, tangent normalization, predictors, arclength constraints, and reported steps.
- Added the sparse augmented SciPy TRF corrector with independent stage/update/phase/arclength acceptance gates, physical finiteness checks, structured rejection diagnostics, and full solver termination/cost/evaluation data.
- Added deterministic signed two-point branch bootstrap with fixed-parameter correction, excessive-change/failure rejection, step halving, oriented secants, and provenance events. Exact target landing is separately corrected and cannot be replaced by overshoot or near-target tolerance.
- Added controlled phase-reference restart support that preserves physical T/log(w), verifies every fixed-parameter residual block, records lineage, and enforces point/family/metric compatibility.
- Added deterministic curated JSON/NPZ generation and checksums for five N=64 validation branches, all accepted vectors, metric diagonals, three phase references, accepted/rejected/informational events, physical/normalized coordinates, periods, phase diagnostics, orientation, and restart provenance.
- Updated the Episode 008 README and design record with method details, observed branches, reproduction commands, and the explicit non-production-accuracy warning.

Results:
- T=225 K fixed-temperature branch: Episode 007 rho=-0.2639524255 to exact spine rho=0, w=0.1445622537 m/s.
- Spine: positive direction to exact T=226 K and negative direction through Delta T-hat=-0.6 to exact T=210 K.
- T=210 K slice: exact spine rho=0 to rho=-0.15 and rho=+0.15.
- Two controlled phase-reference refreshes; references remain immutable within all five segments.
- One excessive bootstrap attempt is deliberately retained as a rejected event before deterministic halving recovery.

Validation:
- 33 focused Episode 008 midpoint/continuation tests passed.
- Full suite: 153 passed, 1 explicit pre-existing skip; three known warnings remain in exploratory solver paths.
- Midpoint and continuation generators pass byte-for-byte --check.
- py_compile, git diff whitespace checks, analytic-column directional checks, and multi-round independent review passed; final review found no blockers or fixes worth doing now.

Scope:
- This is an N=64 midpoint continuation machinery and Python-to-LOCA parity milestone. It does not claim production period or continuous-orbit accuracy.
<!-- SECTION:FINAL_SUMMARY:END -->
