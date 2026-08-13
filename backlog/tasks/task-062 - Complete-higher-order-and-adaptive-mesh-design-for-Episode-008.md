---
id: TASK-062
title: Complete higher-order and adaptive-mesh design for Episode 008
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-12 12:52'
updated_date: '2026-08-13 15:26'
labels:
  - episode-008
  - design
  - numerics
dependencies:
  - TASK-061
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Resume the numerical design interview after fixed-mesh native LOCA continuation works, calibrating the deferred production details for higher-order Gauss collocation, defect-driven h/r adaptation, Floquet diagnostics, Hopf approach, and error-controlled Figure 5 sampling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Fixed-mesh midpoint evidence is reviewed before production adaptation constants are chosen
- [ ] #2 The higher-order fixed-mesh validation sequence and criteria for adding a Radau comparison are finalized
- [ ] #3 Composite monitor normalization, independent defect checks, r-movement bounds, h-marking policy, mesh caps, and remesh restart acceptance are calibrated and documented
- [ ] #4 Phase refresh, Hopf stopping/extrapolation, Floquet, interpolation-error, and multivalued-branch thresholds are finalized with evidence
- [ ] #5 The production artifact schemas and remaining implementation tasks are decomposed into atomic verifiable backlog tasks
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Design interview decision: TASK-062 will specify operational, versioned v1 numerical constants. They are final for the initial implementation contract but must be reassessed against higher-order/adaptive calibration evidence; subsequent changes require documented evidence and a method-version revision.

- Design interview decision: initial production uses globally fixed three-stage Gauss--Legendre collocation with external h/r adaptation. One-stage midpoint remains the baseline and two-stage Gauss an order-convergence cross-check. Local or orbit-varying hp adaptation is deferred; Radau, if triggered by evidence, is a whole-orbit comparison.

- Design interview decision: fixed-mesh higher-order qualification will use four reproducibly seeded points: T=225 K, w=0.1 m/s; T=210 K at rho=0; and T=210 K at rho=-0.15 and +0.15. The canonical point receives the fullest order/mesh ladder and independent IVP comparison; the other points guard against single-orbit tuning. Near-Hopf and full-slice qualification waits for adaptive continuation.

- Design interview decision: higher-order uniform qualification ladder: canonical 225 K/0.1 m s^-1 retains midpoint N=64,128,256, runs two-stage Gauss N=32,64,128 and three-stage Gauss N=16,32,64; each T=210 K guard point runs two-stage N=64,128 and three-stage N=32,64. Coarse failures remain diagnostic evidence. Qualification checks same-order refinement, order improvement at comparable system size, 1e-3 best-solution period/orbit convergence, independent defect reduction, canonical independent-IVP agreement to 1e-3, and Python/C++ parity.

- Design interview decision: Radau IIA remains evidence-triggered, not routine. Trigger a whole-orbit three-stage Radau comparison if, after two adaptive Gauss refinement/remesh cycles, any qualification point has: defect <1e-4 but period/orbit change >1e-3; Gauss-vs-IVP error >1e-3 while DOP853 and IVP Radau agree; persistent resolved-layer polynomial ringing/nonphysical stage values; convergence stagnation before the mesh cap despite targeted refinement; or trivial Floquet error >1e-3 with residual/defect gates passing. NOX difficulty alone is insufficient until scaling, mesh placement, and transfer are ruled out.

- Design interview decision: independent off-collocation defect exclusively controls scientific defect acceptance and h-refinement marking. The composite defect/speed/curvature/nucleation/landmark monitor controls only r-redistribution. Auxiliary monitor components can attract mesh points to potentially missed layers but cannot make an orbit pass; minimum-resolution protections are explicit rather than hidden in weights.

- Design interview decision: independent defect uses two off-collocation grids per element: the existing r+1 Gauss nodes and staggered dyadic points tau={1/8,3/8,5/8,7/8}. Acceptance and h marking use the combined scaled-relative-defect maximum. One-sided endpoint defects, inter-element polynomial-derivative jumps, and grid-max disagreement are separate diagnostics. Landmark-containing elements with material grid disagreement receive a local recursive diagnostic probe before acceptance.

- Design interview decision: v1 r-monitor normalizes combined defect D, scaled speed V=||S_x p_prime||, scaled polynomial curvature C=||S_x p_double_prime||, and the scaled transformed-state homogeneous-nucleation contribution A to unit phase average. Each is winsorized at 20x mean then renormalized. Use m=0.20+0.80*(0.50 D_tilde+0.20 V_tilde+0.20 C_tilde+0.10 A_tilde). Treat saturation extrema, nucleation maxima, and threshold crossings as explicit boundary-alignment targets rather than another continuous weight.

- Design interview decision: v1 pure-r remesh moves 50% toward exact monitor equidistribution, caps each interior boundary displacement at half the smaller adjacent old interval, enforces adjacent interval-width ratios in [1/3,3] and widths in [1/(20N),5/N], and preserves boundary ordering and N. Landmark snapping is allowed only within all bounds; larger redistribution proceeds through multiple controlled restarts.

- Design interview decision: assign each element eta_i as its maximum combined two-grid relative defect. If max eta_i >=1e-4, split the smallest descending-defect set contributing 70% of sum eta_i^2 and also every element with eta_i >=0.5 max eta. Cap element-count growth per remesh at 50%, prioritizing highest defect; bisect marked elements before bounded r movement. Initial implementation/qualification has no coarsening. A later calibrated production step may merge adjacent elements only after both stay below 1e-6 for two accepted meshes, no protected landmark lies between them, and mesh-ratio bounds remain satisfied.

- Design interview decision: adaptive three-stage Gauss starts at N=32 from a qualified transferred orbit, uses ordinary soft cap N=256 and hard cap N=512 only via recorded mesh_cap_escalation, and allows at most 8 remesh/correct cycles per point. At most 3 consecutive pure-r cycles may occur without >=25% max-defect reduction before h marking is forced. Budget exhaustion without all gates yields resolution_unresolved, triggers Radau-comparison consideration, and blocks production interpolation.

- Design interview decision: remesh restart transfers the old collocation polynomial, phase reference, and tangent, then fixed-parameter NOX/KLU2-corrects on rebuilt infrastructure. Accept only with established residual/phase/positivity/linear gates, phase-aligned weighted old/new orbit change <=0.25, |Delta log(P)|<=0.20, new-reference phase residual <=1e-10 with positive finite energy, finite/positive transfer values, and renormalized tangent cosine >=0.5 with preserved active-coordinate orientation. Retry with half r movement then a smaller highest-defect h subset; after 3 failures record remesh_restart_failed. Tangent-only failure uses deterministic two-point rebootstrap rather than rejecting a valid orbit.

- Design interview decision: controlled phase-reference refresh triggers at an accepted orbit if alignment cosine <0.90, weighted orbit distance from reference >0.75, current/reference scaled phase-energy ratio leaves [1/4,4], nonlinear iterations are >=8 and >2x the median of the preceding five accepted points, 20 accepted steps have elapsed, or any remesh occurs. Record every active trigger and rebuild the full model/group/stepper. Refresh cannot override separate near-Hopf reliability gates.

- Design interview decision: near-Hopf regular-orbit v1 stopping triggers if equilibrium-centered weighted amplitude A<1e-3, current scaled phase energy <1e-4, phase/time-shift alignment cosine <0.50 even after one refresh, NOX uses >=20 iterations at two consecutive accepted points, or LOCA has two consecutive rejected attempts at minimum normalized-coordinate step 1e-5. Tangent/parameter reversal indicating a fold stops automatic single-valued sampling but not scientific branch continuation. Exact Hopf points remain separate hopf_linear_limit records.

- Design interview decision: Hopf connection requires >=5 reliable approach points with monotone decreasing amplitude spanning >=3x, all orbit gates, and no fold/secondary flag. Fit P=P0+c2 A^2 and P=P0+c2 A^2+c4 A^4. Connect only if both P0 values agree with 2pi/omega_H within 1%, intercepts differ <0.5%, leave-one-out linear intercept span <1%, max relative fit residual <1%, and A^2 approaches zero consistently with signed Hopf-coordinate distance. Otherwise preserve an explicit unresolved gap.

- Design interview decision: native LOCA owns production orbits; an independent Python/SciPy postprocessor computes Floquet multipliers from saved native piecewise collocation polynomials. Primary variational integration uses DOP853 over normalized phase at rtol=1e-10, atol=1e-12; rerun at 1e-11/1e-13 near or beyond thresholds. Use implicit Radau at stratified difficult points and every suspected unit-circle crossing. Identify the trivial multiplier nearest 1 and record mixed backend provenance explicitly.

- Design interview decision: Floquet gate |mu_trivial-1|<1e-3. Matched multipliers must agree under DOP853 tolerance refinement to relative-with-unit-floor <1e-5 and DOP853/Radau to <1e-4 at required points. Nontrivial multipliers classify attracting below 1-1e-3, unstable above 1+1e-3, otherwise near-unit ambiguous. A crossing candidate requires consecutive points beyond opposite ambiguity bands and confirmation by both integrators; confirmed crossings block automatic production interpolation. Selected finite-difference/Poincare multiplier magnitudes must agree within 1%.

- Design interview provisional decision: multivalued candidate thresholds are active-coordinate tangent sign change, coordinate reversal >1e-4, or coordinate collision within 1e-4 with period separation >1e-3 or weighted-orbit separation >1e-2. Confirmation would fixed-parameter-correct both candidates at identical coordinates/common phase and require both gates plus retained separation. User notes no current evidence and low physical expectation; implementation scope still to be resolved.

- Design interview decision: multivalued support is trigger-only. Always record tangent signs/coordinate sequence and run cheap candidate checks. If none trigger, record single_valued_observed. Initial production does not implement multibranch matching, multiple display values, or attracting-branch selection. A trigger stops automatic processing for that slice and creates a scientific follow-up for exact-coordinate confirmation and artifact/display policy.

- Design interview decision: Figure 5 display interpolation requires maximum |Delta log(P)|<2e-3 (~0.2%) independently for leave-one-out shape-preserving PCHIP along rho and withheld-slice reconstruction between temperatures at fixed rho. Add authoritative solves near worst failures; retain <=2 K maximum temperature separation. Never test/interpolate across Hopf boundaries, unresolved gaps, instability checkpoints, or multivalued triggers. Exact T=210 K lower-panel data remain authoritative solved values.

- Design interview decision: canonical sampling starts with T=190,192,...,240 K plus exact 225 K; native spine points remain separately authoritative. Each reliable slice requests exact rho anchors 0, +/-0.25, +/-0.50, +/-0.75, +/-0.90, +/-0.97, retains additional native points, and adds required Hopf-approach points. Refine by the 2e-3 holdout rule. Browser grid is fixed at 0.5 K x 0.01 rho with solved/interpolated/invalid provenance per value.

- Design interview decision: commit formal production contracts under episodes/008-figure5-periodic-orbit-continuation/schemas/ with identifier episode8-figure5-production-v1. Retain continuation_points.csv, per-orbit NPZ+manifest, continuation_events.jsonl, run_metadata.json, and figure5_browser_dataset.json; add authoritative linearized_period_210.csv for the equilibrium/eigenvalue lower curve. Use JSON Schema for JSON/JSONL and explicit column/array schema JSON for CSV/NPZ. Require stable IDs, method/schema version, backend/source class, units/conventions, validity, and reason codes; incompatible changes increment version.

- Design interview decision: retention tiers: all attempts/accepted steps retain scalar diagnostics/lineage in continuation_events.jsonl; all production-qualified accepted points retain scientific scalars including Floquet in continuation_points.csv; full committed NPZ vectors are limited to canonical T/rho samples, reliable Hopf-extrapolation points, phase/remesh restart anchors, and IVP/Floquet/worst-defect/interpolation fixtures. Intermediate vectors remain in run restart/checkpoint artifacts. Scalar rows use optional orbit_artifact_id; absence does not imply interpolation.

- Design interview decision: T=210 K linearized curve uses native C++ equilibrium continuation over w=5e-4..2 m/s on an initial 401-point log grid plus exact Episode 006 Hopf anchors. Track the conjugate pair by continuation distance with eigenvector overlap for ambiguity. P_lin=2pi/|Im(lambda)| only for a genuinely complex pair with |Im(lambda)|>1e-8 s^-1; otherwise invalidate with real_pair/frequency_below_floor and a gap. Refine if log-period holdout error exceeds 2e-3. Require Hopf frequency and stratified Python physical-Jacobian parity to relative 1e-8; never clip to plot range.

- Design interview decision: production independent-IVP validation uses >=12 unique points: four fixed qualification points; both T=210 K Hopf sides; low/high-T interiors; largest/shortest periods; worst accepted defect; worst trivial multiplier; worst interpolation holdout, with replacements after deduplication. Every point gets transformed-state DOP853 one-period integration at rtol=1e-10/atol=1e-12 and requires period, phase-aligned trajectory, and weighted return errors <1e-3. Six hardest/headline points also require IVP Radau agreement <1e-3. At least four, including both Hopf sides and largest period, receive perturbed-equilibrium attractor checks.

- Evidence-based design resolution without user question: retain the globally frozen seed-derived state scaling and unit weights for log(P), rho, and T_hat in v1. TASK-061 completed all required native branches and controlled retries with this metric, so there is no evidence supporting a scaling change. Any future change requires conditioning/convergence evidence and a method-version revision.

- Design interview decision: retain serial Amesos2/KLU2 through initial higher-order, adaptive, and production work. Trigger a Belos/Ifpack2 bordered-preconditioner task only if realistic N=256..512 profiling shows >4 GiB factorization memory, >30 s median linear solve/factorization per nonlinear iteration, >70% runtime in linear algebra, or failure to meet the recorded production compute budget. Preserve KLU2 as oracle.

- Design interview revision: v1 has no explicit landmark snapping/protection. Saturation extrema, nucleation maximum, and pulse-rise locations are diagnostics only; the two defect grids plus defect/speed/curvature/nucleation monitor are expected to resolve this smooth problem. Trigger a landmark-alignment follow-up only if material check-grid disagreement or convergence stagnation recurs in the same phase region after targeted h/r adaptation. This supersedes the earlier provisional boundary-alignment-target language.

- Design interview decision: material defect-grid disagreement requires max(eta_Gauss,eta_dyadic)>1e-5 and relative difference over that maximum >0.5. Evaluate a 16-point uniform local probe for flagged elements; its maximum joins acceptance/h-marking defect for that cycle. Recurrence in the same phase region on two successive adapted meshes records defect_aliasing_persistent and triggers denser-check or landmark-alignment consideration.

- Design interview decision: paper digitization is an external discrepancy diagnostic, never a numerical acceptance/tuning target. Flag comparison when |Delta log(P)| > max(3*sigma_digitized_logP,0.02). Investigate model assumptions, parameter mapping, paper method, and digitization without weakening convergence or adjusting periods toward pixels. Internal convergence and IVP validation remain authoritative.
<!-- SECTION:NOTES:END -->
