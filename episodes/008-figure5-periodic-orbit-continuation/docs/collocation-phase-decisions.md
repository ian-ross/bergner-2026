# Episode 008 collocation-phase decisions

This document records decisions made while designing the first periodic-orbit collocation phase for the Figure 5 reproduction. It is expected to grow as the design interview resolves the remaining numerical and software-architecture questions.

## Scientific target

Reproduce both panels of Bergner & Spichtinger (2026) Figure 5:

1. the period map over the temperature–vertical-velocity parameter plane inside the two Hopf loci; and
2. the fixed-temperature slice at `T = 210 K`, comparing the nonlinear periodic-orbit period with the equilibrium linearized period `2*pi/Im(lambda)`.

The lower panel is a required validation artifact, not an optional presentation detail. In particular, the nonlinear and linearized periods should meet at the Hopf boundaries.

The fixed environmental/model settings are inherited from the already validated Episode 005--007 Figure 2--4 workflows and upstream boundary/seed artifacts:

```text
p                   = 30000 Pa,
F                   = 1,
N_a                 = 1e10 m^-3 (10000 cm^-3),
Delta z             = 100 m,
include_evaporation = false.
```

Temperature and vertical velocity vary over the Figure 5 domain recorded below. The no-evaporation choice is binding: the existing physical Jacobian, Episode 006 Hopf boundaries, Episode 007 seed, browser model, and differentiable C++ core all share it. Introducing the discontinuous optional evaporation-number switch would define a different continuation problem and requires separate future work.

## Relationship to the browser widget

The eventual product is intended to support an extension of the Episode 007 widget in which selecting a point on the period map chooses `(T, w)` for fresh IVP integration and updates the displayed temperature slice.

Browser UI integration is explicitly deferred from Episode 008. Episode 008 will instead emit a schema-versioned, browser-consumable dataset with enough parameter, period, boundary, provenance, and validity information for that later integration. The continuation and discretization work must not depend on browser runtime concerns.

## Continuation topology over `(T, log(w))`

Use a **spine-and-slices** traversal rather than a serpentine scan between nearly zero-amplitude Hopf endpoints:

1. use `log_w = log(w)` as the vertical-velocity continuation coordinate;
2. define an interior spine initially halfway between the lower and upper Figure 3 Hopf loci in `log_w`;
3. bootstrap a periodic orbit from the validated Episode 007 case at `T = 225 K`, `w = 0.1 m s^-1`;
4. continue an interior periodic orbit along the spine in temperature;
5. at each selected temperature, use the corresponding spine orbit as a seed and continue outward in both `log_w` directions toward the two Hopf boundaries.

This topology avoids using small-amplitude, poorly conditioned endpoint orbits as the seeds for temperature continuation and makes individual temperature slices independently reproducible.

Define the spine precisely as the midpoint of the validated native LOCA Figure 3 Hopf loci in `log_w`:

```text
log_w_spine(T) = (log_w_lower(T) + log_w_upper(T)) / 2,
w_spine(T) = sqrt(w_lower(T) w_upper(T)).
```

Construct smooth interpolants of the lower and upper loci. At `T = 225 K`, first obtain the Episode 007 orbit at `w = 0.1 m s^-1`, then use fixed-temperature periodic-orbit continuation to reach the exact spine value if necessary.

Treat temperature as the scalar spine path parameter `sigma`:

```text
T = sigma,
log_w = log_w_spine(sigma).
```

Implement the same mapping in Python and Trilinos. Its parameter derivative combines both environmental changes:

```text
F_sigma = F_T + (d log_w_spine / dT) F_log_w.
```

The spine is therefore a genuine one-parameter continuation path, not a sequence of unrelated fixed-temperature solves.

## Staged numerical scope

All of the following stages belong to Episode 008:

1. Python implicit-midpoint collocation on a fixed mesh, including a mesh-convergence study;
2. Trilinos layout/residual/Jacobian parity, a fixed-parameter NOX solve, and a short LOCA branch;
3. higher-order collocation on a fixed mesh;
4. adaptive remeshing implemented as solution/reference transfer followed by continuation restart;
5. production Figure 5 generation only after period convergence has been demonstrated.

Implicit midpoint on a non-adaptive fixed mesh is a machinery and migration baseline, not the expected production discretization. The first implementations will deliberately keep the mesh fixed even though their period estimates are expected to be inaccurate. Adaptivity is introduced only after layout, assembly, derivatives, nonlinear solves, and continuation work correctly. A small discrete collocation residual is not sufficient evidence that the stiff orbit or its period is accurately represented.

## State, parameter, and period coordinates

Use the transformed orbit state

```text
x = (log(n), log(q), s)
```

and define its transformed vector field as

```text
g(x) = (dn/dt / n, dq/dt / q, ds/dt).
```

This preserves positivity of `n` and `q` and matches the existing Python, browser, and shared C++/LOCA model semantics.

Use normalized phase `theta in [0, 1]` and represent the physical period by the unknown

```text
ell_P = log(P),   P = exp(ell_P) > 0.
```

The continuous orbit equation is

```text
x'(theta) = exp(ell_P) g(x(theta); parameters).
```

Use explicit collocation-stage unknowns from the outset. For `N` intervals and `r` stages per interval, the fixed-parameter solution layout is

```text
y = (x_0, ..., x_{N-1}, {X_i,j}, ell_P),
```

with no duplicated terminal endpoint and periodic indexing `x_N = x_0`. Assemble the stage and endpoint-update residuals

```text
S_i,j = X_i,j - x_i
        - Delta theta_i P sum_k a_j,k g(X_i,k) = 0,

U_i = x_{i+1} - x_i
      - Delta theta_i P sum_j b_j g(X_i,j) = 0.
```

Implicit midpoint is represented as one-stage Gauss collocation:

```text
r = 1, c_1 = 1/2, a_1,1 = 1/2, b_1 = 1.
```

Eliminating its stage recovers the condensed midpoint equation

```text
x_{i+1} - x_i
- Delta theta_i P g((x_i + x_{i+1}) / 2) = 0.
```

The explicit-stage representation costs three additional unknowns per interval for this model, but higher order then changes the collocation coefficients and stage count rather than the residual architecture. Static condensation may be considered only later if profiling justifies it.

All stage and update derivatives with respect to `ell_P` contain the corresponding `-Delta theta_i P` weighted vector-field sum. Physical outputs report `P` in seconds; `log(P)` is an internal positivity and scaling choice.

## Phase condition

Remove the autonomous time-shift null direction with a weighted integral phase condition against a reference orbit:

```text
psi(x) = integral_0^1 < S(x(theta) - x_ref(theta)),
                          S x_ref'(theta) > dtheta = 0.
```

Its discrete form uses the quadrature associated with the active collocation method. For midpoint collocation, interval-midpoint values use:

```text
psi = sum_i Delta theta_i
      < S(x_{i+1/2} - x_ref,i+1/2),
        S x_ref,i+1/2' >.
```

On a uniform midpoint mesh, `Delta theta_i = 1/N`. On a nonuniform mesh, the normalized interval widths supply the weights. Higher-order elements use their corresponding quadrature weights.

`S` is a diagonal state-scaling/nondimensionalization matrix for the phase inner product. Start conservatively with `S = I`. If phase diagnostics show that one state component dominates, introduce documented scales based on the reference orbit's RMS or peak-to-peak variations, with fixed lower floors near Hopf points. `S` remains fixed during each nonlinear solve.

Normalize the phase equation by the reference-orbit phase energy:

```text
E_ref = integral_0^1 ||S_x x_ref'(theta)||^2 dtheta,

psi_hat(x) = [integral_0^1
              <S_x (x - x_ref), S_x x_ref'> dtheta]
             / E_ref = 0.
```

For a small normalized phase displacement `delta`, `psi_hat` is approximately `delta`, so the phase residual is interpretable in cycles and its directional derivative along the reference time-shift direction is approximately one.

Compute numerator and denominator with the active collocation quadrature. Freeze `x_ref`, `S_x`, `E_ref`, and therefore the base phase row throughout each uninterrupted native LOCA segment, not merely each nonlinear solve. Mutating the reference after every accepted point would change `F(y; lambda)` while LOCA retains previous groups, tangents, and predictor history.

Record `E_ref` and monitor the phase-row angle with the current time-shift direction, accumulated weighted distance from the reference, and nonlinear-iteration deterioration. The v1 controlled-refresh triggers are: alignment cosine below `0.90`; weighted reference distance above `0.75`; current/reference phase-energy ratio outside `[1/4, 4]`; at least eight nonlinear iterations and more than twice the median of the preceding five accepted points; 20 accepted continuation steps since the last refresh; or any remesh. Record every active trigger. Stop the regular-orbit approach to Hopf when the separate amplitude/transversality limits below are reached. A refresh proceeds as follows:

1. stop at an accepted orbit;
2. choose it as the new reference and recompute `E_ref`;
3. verify that it satisfies the new normalized phase equation exactly;
4. rebuild/reinitialize the relevant group and tangent state; and
5. restart native LOCA.

Remeshing automatically includes a phase-reference refresh. Use the same segmented-reference policy in Python validation branches. Record a `phase_reference_id` on every point and every refresh event.

For the first IVP-derived seed only, use the already validated Episode 007 trajectory at `T = 225 K`, `w = 0.1 m s^-1`, `p = 30000 Pa`, `F = 1`, `N_a = 1e10 m^-3`, `Delta z = 100 m`, with evaporation disabled. An Episode 008 seed-generation script will:

1. read the committed Episode 007 reference trajectory and metadata;
2. extract its final complete saturation-maximum-to-maximum cycle;
3. declare the first maximum to be `theta = 0` and normalize the cycle to `theta in [0, 1]`;
4. convert it to `(log(n), log(q), s, log(P))`;
5. interpolate it onto a requested collocation mesh;
6. write a frozen Episode 008 reference seed with provenance back to Episode 007; and
7. provide optional fresh-IVP regeneration as verification, without making routine collocation tests repeat a roughly 300-period integration.

This maximum detection is seed alignment, not the phase equation used by the nonlinear solve or continuation.

## Fixed-mesh midpoint baselines

Use uniform normalized-phase meshes `theta_i = i/N` with explicit one-stage midpoint unknowns in the following roles:

- `N = 8`: small deterministic layout, pack/unpack, sparsity, residual, and Jacobian fixture tests;
- `N = 64`: first complete fixed-parameter midpoint orbit and primary Python-to-Trilinos parity case;
- `N = 32, 64, 128, 256`: fixed-uniform-mesh convergence study that explicitly demonstrates the distinction between discrete residual convergence and period accuracy.

The frozen IVP orbit supplies interpolated endpoint and stage initial guesses. The `N = 64` case is a machinery milestone only and is not required to meet the eventual scientific period tolerance.

### Observed fixed-mesh baseline (TASK-056)

The versioned SciPy TRF baseline with the analytic sparse Jacobian accepted `N = 64, 128, 256` against independently recomputed stage/update maximum and RMS thresholds of `1e-9` and phase threshold `1e-10`. It rejected `N = 32` after 1000 function evaluations: SciPy did not terminate successfully and the stage (`8.45e-4`), update (`8.12e-4`), and phase (`8.62e-4`) maxima all missed their gates. This failure is frozen rather than hidden so nominal or unsuccessful solver outcomes remain distinguishable from accepted nonlinear solutions.

The accepted periods were `2768.508882 s`, `2531.464910 s`, and `2478.674760 s` for `N = 64, 128, 256`, respectively, versus the Episode 007 Hermite reference period `2461.611268 s`. Phase-aligned, quadrature-weighted orbit errors versus that continuous reference decreased from `0.172603` to `0.0389869` and `0.00950588`. Thus the baseline demonstrates midpoint mesh convergence but also makes the limitation concrete: the `N = 64` finite-dimensional equations converge to near machine residual while their period is still over 12% from the reference. These artifacts are migration/parity fixtures and do not assert production accuracy.

### Observed fixed-mesh continuation baseline (TASK-057)

The transparent Python reference now performs genuine augmented pseudo-arclength correction on the unchanged uniform `N = 64` midpoint mesh. A parameter-aware family rebuilds the environment and temperature-dependent coefficients at each trial coordinate. The augmented sparse Jacobian uses analytic local `g_T` and `g_log_w` columns, with `g_rho = 0.5(log_w_upper-log_w_lower) g_log_w` and `g_T_hat = 25[g_T + (d log_w_spine/dT)g_log_w]`; centered parameter differences remain validation checks only.

The diagonal continuation metric implements the agreed half endpoint/half stage quadrature weighting plus unit `log(P)` and normalized-coordinate weights. Its exact gradient `W t` supplies the arclength row, and the same inner product supplies every secant, normalized tangent, predictor, and reported step. Every signed direction begins with a fixed-parameter corrected neighbor. A deliberately strict bootstrap-change cap freezes an excessive first `T = 225 K` startup attempt and its deterministic halving recovery before the oriented secant is accepted.

The fixed-temperature branch starts from the Episode 007 point at `rho = -0.2639524255` and lands exactly at the Episode 006 `T = 225 K` spine coordinate (`rho = 0`, `w = 0.1445622537 m s^-1`). A recorded controlled phase-reference refresh then starts the spine segment. The positive branch reaches `T = 226 K`; the negative branch takes multiple accepted pseudo-arclength steps across `Delta T_hat = -0.6` to the exact `T = 210 K` spine. A second recorded refresh starts the `T = 210 K` slice, whose two signed branches reach `rho = -0.15` and `rho = +0.15`. Phase references remain byte-identical within each segment and change only at these explicit restart records.

The curated JSON/NPZ artifacts include accepted and rejected events, all residual blocks including arclength, both physical and normalized coordinates, period, phase energy/alignment/distance, orientation, restart lineage, metric diagonals, phase references, and accepted vectors. This is still an `N = 64` midpoint machinery/parity result; it makes no production period-accuracy claim.

## Higher-order family and stiffness qualification

Use Gauss--Legendre as the primary order progression:

1. one-stage Gauss / implicit midpoint, order 2;
2. two-stage Gauss, order 4;
3. three-stage Gauss, order 6.

The initial-run candidate is globally fixed three-stage Gauss--Legendre with external `h/r` adaptation. Midpoint remains the baseline, and two-stage Gauss is the order-convergence cross-check. Local or orbit-varying `hp` adaptation is deferred so that mesh-placement error can be distinguished from order-selection error.

Gauss methods are A-stable but not L-stable. In this global periodic boundary-value setting they can represent the stiff orbit, but only when the short nucleation layer is resolved by the mesh. Higher polynomial order does not make an element that spans an unresolved transition scientifically accurate. The Episode 007 canonical orbit has a period near `2458 s`, while the sampled 10--90% increase in `n` takes roughly `38 s` (about `1.6%` of the period). A uniform 64-element mesh therefore places only about one element across this transition; even 128 uniform elements provide only about two. Other Figure 5 points may be more severe.

### Fixed-mesh qualification sequence (TASK-062 v1)

Qualify the higher-order formulation at four reproducibly seeded points:

- `T = 225 K`, `w = 0.1 m s^-1`;
- `T = 210 K`, `rho = 0`;
- `T = 210 K`, `rho = -0.15`; and
- `T = 210 K`, `rho = +0.15`.

The canonical `225 K` point retains midpoint `N = 64, 128, 256`, adds two-stage Gauss `N = 32, 64, 128`, and adds three-stage Gauss `N = 16, 32, 64`. Each `210 K` guard point uses two-stage `N = 64, 128` and three-stage `N = 32, 64`. Coarse failures are retained as diagnostic evidence rather than removed. Qualification requires same-order refinement, improvement with order at broadly comparable system sizes, successive best-solution relative period and phase-independent weighted-orbit changes below `1e-3`, independent defect reduction, Python/C++ formulation parity, and canonical-point agreement with an independent IVP below `1e-3`.

Three-stage Radau IIA is evidence-triggered, not a routine second family. Through TASK-068, the active triggers after two adaptive Gauss refinement/remesh cycles are limited to:

- independent defect below `1e-4` but period or weighted-orbit change above `1e-3`;
- persistent polynomial ringing or nonphysical interior values in the resolved layer; or
- period/defect convergence stagnation before the mesh cap despite targeted refinement.

NOX difficulty alone is not a Radau trigger until scaling, transfer, and mesh placement have been ruled out. TASK-064 performs only the canonical DOP853 comparison already required by its fixed-mesh qualification contract. The broader IVP-based Radau trigger, production cross-method validation, and Floquet-derived trigger are downstream and recorded as `not_evaluated` through TASK-068. TASK-069 decides later IVP/Radau and Floquet scope.

### Observed fixed-mesh higher-order qualification (TASK-064)

The reusable Python formulation now consumes the frozen `CollocationRule` tables directly for one-, two-, and three-stage Gauss rules. The square `3N(r+1)+1` layout, scaled stage/update residuals, normalized quadrature phase row, and analytic sparse Jacobian are stage-generic. Collocation-polynomial evaluation uses the generated integrated-Lagrange coefficients in ascending powers; mesh/rule and phase-reference transfer evaluate that polynomial rather than reshaping or independently interpolating stages. The established midpoint public API remains a compatibility wrapper and reproduces its frozen vectors and residuals.

The complete prescribed ladder is frozen in `higher_order_fixed_mesh_qualification.json` and its NPZ/parity bundle. Canonical two-stage periods at `N=32,64,128` are approximately `2841.227`, `2466.548`, and `2461.911 s`; three-stage periods at `N=32,64` are `2450.318` and `2461.617 s`. Three-stage `N=16` exhausts 1000 evaluations and is retained with every failed residual gate. Every requested `T=210 K` two-/three-stage guard solve converges discretely from the exact TASK-061 target vector transferred through its midpoint collocation polynomial.

The run does **not** qualify the fixed uniform meshes at the `1e-3` discretization contract. No consecutive higher-order same-rule pair passes both period and phase-independent weighted-orbit gates. The canonical three-stage `N=32 -> 64` changes are about `4.59e-3` in period and `6.37e-3` in weighted orbit; guard-pair misses range similarly or larger. The independent two-grid defect also remains above `1e-4` everywhere, with best canonical maximum about `7.38e-3`. These misses are preserved as evidence supporting the planned adaptive stage.

The canonical best higher-order orbit does pass its independent DOP853 contract. A deterministic run extends through `2.1` collocation periods, scans and bounded-refines successive saturation maxima, and obtains an IVP-derived period of about `2461.617092 s`, a relative collocation/IVP period difference of `1.55e-7`, a scaled return error of `1.48e-6`, and a phase-aligned weighted dense-orbit error of `2.39e-5`. Thus the cross-method trajectory evidence is encouraging while the explicit same-rule/defect evidence still blocks a fixed-uniform production claim.

The curated decision records distinguish finite-dimensional nonlinear acceptance from scientific discretization qualification. Twenty cases pass residual gates and one coarse case fails, but zero fixed-uniform cases qualify under the combined defect and applicable same-rule refinement evidence. Broadly comparable cross-order comparisons are separate evidence and show improvement without overriding those mandatory gates.

The finite-positive physical mapping check passes for accepted endpoint/stage vectors. Polynomial ringing remains `not_evaluated`: TASK-064 defines no versioned ringing metric, so the run makes no unsupported visual/ringing claim. The defect/convergence-stagnation Radau triggers remain inactive/not-yet-applicable because their definition requires evidence after two adaptive Gauss remesh cycles. Floquet and Floquet-derived triggers remain `not_evaluated` through TASK-068.

### Observed native higher-order continuation (TASK-066)

Native LOCA now accepts the same fixed one-, two-, and three-stage Gauss base systems. For all rules, the base residual remains square with no duplicate arclength row. The binding continuation metric assigns `0.5` of the quadrature-normalized orbit weight to cyclic endpoint storage and `0.5 Delta theta_i b_j` to each explicit stage; summed component weights are therefore rule- and mesh-invariant. The existing analytic normalized rho/T-hat parameter columns are supplied as `DfDp`. LOCA owns Arc Length, Secant prediction, the injected first-step Restart tangent, Adaptive step sizing, and rejection/retry behavior.

The three-stage `N=32` evidence executes exactly the approved five segments and exact endpoints. Signed fixed-parameter bootstrap provides each unit weighted-norm first tangent; the artifact separately records its signed parameter component and LOCA's injected positive-component Restart orientation, while the signed adaptive step selects direction. References remain immutable inside a segment; the `225 K` spine and `210 K` slice boundaries preserve both physical coordinates, obtain zero stage/derivative reference-identity error, and report the actually executed assembler/model/group/stepper rebuild after fixed-parameter verification. Every native recorder point also passes direct stage/update residual gates (maxima below `3.2e-12`) plus a separate perturbed NOX/KLU2 validation with positive finite mapped states and period, completed linear activity, and weighted recorrection distance below `2.8e-12`.

Python corrects every native coordinate through the independent three-stage formulation without using native vectors as seeds. Maximum all-point native/Python differences are approximately `1.58e-12` relative in period and `2.84e-12` in the binding weighted metric, against `2e-7` limits. Native two-/three-stage model-evaluator tests request rho and temperature `OUT_ARG_DfDp` columns and compare them with centered residual trials; measured relative errors are at most `1.56e-9` against `2e-6`, with the shared assembler restored to the center environment. A deterministic forced two-/three-stage smoke rejection records one LOCA-owned failure followed by an adjacent, linked smaller-coordinate-delta retry. Generator invariants independently reconcile contiguous callbacks, exactly one initial/final save, regular attempts, saved points, and raw failed/total counts. The artifact is bound to the exact executable SHA-256, emitted compiler/Trilinos identity, Release CMake source/config hash, and compiled source fingerprints; exact `--check` therefore uses that build or requires intentional regeneration. These results validate fixed-mesh continuation ownership and parity only; TASK-064's defect/refinement failures still require the planned adaptive stage.

## Adaptive mesh design

TASK-062 specifies operational **v1 hypotheses** for the first adaptive implementation. They make the implementation and run reproducible, but they are not claims that production policy is settled before evidence exists. The mandatory post-run review may tighten or replace them; any later change must cite evidence and revise the method version.

Use a combined external `h/r` remesh-and-restart design on globally fixed three-stage Gauss elements. The orbit is smooth and its rapid nucleation segment is an internal layer, so dissipative shock-capturing schemes and nonlinear mesh-coordinate unknowns are out of scope.

### Independent defect and `h` refinement

Scientific defect acceptance and `h` marking are controlled only by an independent scaled relative defect. Evaluate it on two off-collocation grids in every element:

1. the existing `r+1` Gauss check nodes; and
2. staggered dyadic points `tau = {1/8, 3/8, 5/8, 7/8}`.

Use the combined maximum. Record one-sided endpoint defects, inter-element polynomial-derivative jumps, and disagreement between the two grids separately. Grid disagreement is material only when the larger maximum exceeds `1e-5` and their relative difference (with the larger maximum as denominator) exceeds `0.5`. A materially flagged element receives a 16-point uniform local probe, whose maximum joins the acceptance and marking defect for that cycle.

Define recurrence deterministically with a fixed periodic partition of normalized phase into 128 half-open bins. Map the local-probe argmax phase to `floor(128 * (theta mod 1))`. Two successive adapted meshes identify the same phase region when their argmax bins are identical or adjacent under circular bin distance, including bins `127` and `0`. Such recurrence records `defect_aliasing_persistent` and triggers later consideration of denser checks or landmark alignment.

Let `eta_i` be the resulting maximum defect for element `i`. When `max eta_i >= 1e-4`, split the smallest descending-defect set accounting for 70% of `sum eta_i^2`, and also every element with `eta_i >= 0.5 max eta`. Cap growth at 50% per remesh and prioritize the highest-defect elements if the marking set exceeds the budget. Bisect marked elements before redistribution. Initial qualification has no coarsening.

### Composite `r` monitor

The composite monitor controls only `r` redistribution and cannot make an orbit pass its defect gate. Define:

- `D`: combined two-grid relative defect;
- `V = ||S_x p'||`: scaled phase speed;
- `C = ||S_x p''||`: scaled polynomial curvature; and
- `A_nuc`: norm of the scaled transformed-state contribution from homogeneous nucleation alone.

For redistribution, evaluate `D`, `V`, `C`, and `A_nuc` at the midpoints of 16 equal phase subcells in every pre-`r` element. A sample in element `i` has quadrature weight `Delta theta_i / 16`. Scan raw-sample maxima and accumulate weighted phase averages in ascending old-element index and then ascending subcell index. Reject any density containing a nonfinite or negative sample. Normalize each valid nonnegative density deterministically using stable max-rescaling. If its maximum is zero, its normalized contribution is identically zero. Otherwise divide by its maximum, divide by the resulting weighted phase average, winsorize pointwise at `20`, and divide once more by the weighted phase average after winsorization. Use

```text
m(theta) = 0.20
         + 0.80 (0.50 D_tilde + 0.20 V_tilde
                 + 0.20 C_tilde + 0.10 A_nuc_tilde).
```

Represent this composite monitor as piecewise constant on the same subcells. Accumulate its mass in the same deterministic order. For target boundary `j/N`, `j=1,...,N-1`, multiply by total monitor mass and choose the first subcell whose closed upper cumulative bound reaches the target, treating `upper + 64*epsilon64*max(1,total_mass) >= target` as reached, where `epsilon64 = 2^-52`. Linearly interpolate within that positive-mass subcell and clamp the interpolation fraction to `[0,1]`. The `0.20` floor guarantees positive subcell and total mass.

The floor protects slow regions while defect retains half of redistribution authority. Saturation extrema, nucleation maxima, and pulse-rise locations are diagnostics only in v1: there is no boundary snapping or landmark protection. Add such machinery only if persistent defect aliasing or same-region convergence stagnation survives targeted `h/r` adaptation.

Apply the mesh constraints without coordinate-by-coordinate clipping or projection. Starting with global relaxation `beta=0.5`, form every candidate interior boundary simultaneously as the old boundary plus `beta` times its displacement toward the equidistributed target. Accept the candidate only if every boundary displacement is at most half the smaller adjacent old interval, every new width satisfies `1/(20N) <= Delta theta_i <= 5/N`, and every cyclic adjacent-width ratio, including the last/first pair, lies in `[1/3,3]`. Otherwise halve `beta` globally and retry through `beta=2^-20`. If no candidate passes, retain the old boundaries and record `r_movement_stalled`.

### Adaptation cycle and mesh budgets

Start three-stage adaptation at `N = 32` from a qualified transferred orbit. At each corrected accepted mesh:

1. if `max eta_i >= 1e-4`, apply ordinary defect-driven `h` marking and then the bounded `r` move;
2. if the defect gate passes but successive accepted-mesh period or weighted-orbit convergence has not passed, apply a pure `r` move;
3. after three consecutive pure-`r` cycles with less than 25% reduction in maximum defect, force exactly one split of the maximum-defect old element, breaking ties by lowest old element index, then apply the bounded `r` move; or
4. if defect, period, and orbit-convergence gates all pass, stop rather than remesh.

Ordinary marking is truncated deterministically in descending defect order, with lower old element index breaking ties, so `N_new <= 256`. At or after reaching `N=256`, if one corrected cycle still fails the defect or period/orbit-convergence gates, emit `mesh_cap_escalation` and permit the same deterministic marking up to `N=512`. Never exceed `N=512`. Allow at most eight remesh/correct cycles per point; exhaustion of either the cycle or hard mesh budget without all gates records `resolution_unresolved` rather than silently accepting the point.

Coarsening, local `hp`, landmark alignment, and Shishkin/Bakhvalov meshes are not part of the first implementation. Serial Amesos2/KLU2 remains the reference linear solver. Consider Belos/Ifpack2 only if realistic `N = 256--512` profiling shows factorization memory above 4 GiB, median factorization/solve time above 30 s per nonlinear iteration, more than 70% of runtime in linear algebra, or inability to meet the recorded run budget; any iterative path must preserve KLU2 as an oracle and explicitly handle the phase row and `log(P)` column.

### Observed Python adaptive qualification (TASK-067)

The transparent Python reference now implements the external three-stage Gauss `h/r` cycle as a remesh-and-restart operation, not as native continuation ownership. The independent defect pipeline from TASK-064 remains the scientific gate and h-marking authority. The new v1 r monitor samples defect, phase speed, polynomial curvature, and homogeneous-nucleation transformed-state contribution at 16 equal subcell midpoints per current element, applies the documented deterministic max/average/winsorized normalization, inverts the piecewise-constant monitor CDF, and accepts only simultaneous global-beta mesh motion satisfying displacement, width, and cyclic adjacent-ratio bounds. Collocation-polynomial transfer refreshes the solution and phase reference on every remesh; tangent transfer and the three-attempt h+r/pure-r/tangent-only restart plans are emitted as language-neutral contracts for TASK-068.

The frozen adaptive qualification artifact starts all four required points from the accepted `N=32` fixed three-stage Gauss vectors: the canonical `225 K, w=0.1 m s^-1` point and the three `T=210 K` guard points at `rho=0, -0.15, +0.15`. All four converge within the eight-remesh budget without reaching the `N=256` soft cap. Final meshes have `N=72, 75, 81, 75`, respectively. Final maximum independent defects are approximately `8.05e-5`, `6.53e-5`, `5.12e-5`, and `7.32e-5`; final period/orbit changes are below the `1e-3` gates. The corresponding final periods are approximately `2461.604468 s`, `5718.140412 s`, `6183.898590 s`, and `5109.345769 s`.

The artifact preserves every corrected cycle's mesh, unknown vector, defect maxima, endpoint and jump diagnostics, monitor/movement intermediates, marked elements, fixed-parameter correction status, phase-refresh reason, period/orbit changes, aliasing records, and active Radau-trigger evidence. One guard point records persistent adjacent-bin defect aliasing, but it still converges under targeted h/r adaptation; this remains diagnostic evidence rather than a v1 failure. Broader IVP-based/Radau evidence and all Floquet-dependent evidence remain explicitly `not_evaluated_through_TASK_068`.

## Python nonlinear solver

Use `scipy.optimize.least_squares(method="trf")` for the initial Python prototype. Supply an explicitly assembled sparse CSR Jacobian rather than production finite differences. The same collocation assembler will support fixed-parameter and Python pseudo-arclength residuals.

Treat SciPy's `success` flag as necessary but not sufficient. Independently reject a result unless component-scaled stage, endpoint-update, and phase block norms satisfy explicit thresholds. Record residual, step, evaluation, and termination diagnostics. Finite-difference directional `Jv` and parameter-column checks are tests for the assembled derivatives, not the production derivative path.

A small damped sparse-Newton driver may be added later for closer behavioral comparison with NOX, but it does not block the first midpoint milestone.

## Continuation metric and arclength scaling

Do not use the raw Euclidean norm of the packed unknown vector for continuation. It changes with mesh size, stage count, and representation. Define a quadrature-weighted, discretization-independent metric approximating an `L2` norm of the represented orbit perturbation:

```text
||delta y||_W^2 = orbit_endpoint_term
                + orbit_stage_term
                + alpha_P^2 (delta ell_P)^2
                + alpha_lambda^2 (delta lambda)^2,
```

with representative orbit terms

```text
orbit_endpoint_term = (1/2) sum_i Delta theta_i
    (||S_x delta x_i||^2 + ||S_x delta x_{i+1}||^2),

orbit_stage_term = sum_i Delta theta_i sum_j b_j
    ||S_x delta X_i,j||^2.
```

Normalize the combined endpoint and stage weights so storing both representations does not double-count the orbit and total orbit weight remains independent of `N` and stage count. `S_x` scales state components, `alpha_P` scales changes in `log(P)`, and `alpha_lambda` scales the active continuation coordinate such as `log(w)` or spine temperature.

Use the same metric for secants, tangent normalization, predictors, arclength constraints, reported step sizes, and transfer diagnostics. Record all metric scales in branch metadata. After remeshing, transfer the tangent and renormalize it in the new mesh's metric.

Freeze continuation and production scaling globally rather than recomputing it from each orbit, because orbit-amplitude-derived scales become singular near Hopf points and would make step sizes incomparable.

The canonical Episode 007 final cycle has transformed-state peak-to-peak ranges approximately

```text
Delta log(n) = 3.34,
Delta log(q) = 2.47,
Delta s      = 0.121.
```

After the initial `S = I` parity milestone, freeze

```text
S_x = diag(1/3.34, 1/2.47, 1/0.121)
```

from the exact frozen-seed values rather than the rounded documentation values. Use this same state scaling for orbit norms, phase alignment, defect normalization, and state residual rows. Keep `ell_P = log(P)` unscaled initially, so a unit change retains its interpretation as a factor `e` in physical period.

Use normalized continuation coordinates. Parameterize the spine by

```text
T_hat = (T - 215 K) / (25 K),
```

so `T = 190--240 K` maps to `[-1, 1]`. At fixed temperature parameterize each slice by

```text
rho = (log_w - log_w_spine(T))
      / (0.5 (log_w_upper(T) - log_w_lower(T))).
```

The spine is `rho = 0` and the Hopf limits are approximately `rho = -1` and `rho = +1`. LOCA continues in `T_hat` or `rho`; the parameter adapter maps these coordinates to physical `T` and `log_w`, including the required chain-rule derivatives. Use unit weights for `T_hat`, `rho`, and initially `ell_P` in the arclength metric.

Record both normalized and physical coordinates. Scaling changes require an explicit method/schema revision rather than adaptive updates within a run.

## Hopf-boundary treatment

Do not solve the exact Hopf endpoints as regular collocation orbits. At zero amplitude the orbit collapses to the equilibrium, the time-shift direction vanishes, the integral phase condition loses transversality, and the period is not uniquely defined by the constant orbit.

For each fixed-temperature slice:

1. continue toward `rho = -1` and `rho = +1` with decreasing continuation step size;
2. measure orbit amplitude with the fixed weighted norm

   ```text
   A = [integral_0^1 ||S_x (x(theta) - x_eq)||^2 dtheta]^(1/2);
   ```

3. stop v1 regular-orbit continuation if `A < 1e-3`, current scaled phase energy is below `1e-4`, phase/time-shift alignment remains below `0.50` after one refresh, NOX requires at least 20 iterations at two consecutive accepted points, or LOCA has two consecutive rejections at normalized-coordinate step `1e-5`;
4. retain each exact Episode 006 Hopf boundary as a separate `hopf_linear_limit` record with `P_H = 2*pi/omega_H`, not as a collocation orbit;
5. through TASK-068, record amplitude, period, reliability diagnostics, and terminal status while targeting at least five reliable approach points with monotonically decreasing amplitude spanning a factor of at least three when v1 continuation reaches them; and
6. in TASK-069, perform or review both `P=P_0+c_2 A^2` and `P=P_0+c_2 A^2+c_4 A^4` fits, compare the intercept evidence with `P_H`, and decide the justified downstream connection or explicit-gap policy.

TASK-068 never invents values at the boundary and does not make the final connection/gap decision. The downstream policy considered by TASK-069 should require both intercepts to agree with `P_H` within 1%, differ from one another by less than 0.5%, leave-one-out linear intercepts to span less than 1%, maximum relative fit residual below 1%, and `A^2` to approach zero consistently with signed Hopf-coordinate distance.

## Parameter domain and sampling artifacts

Match the saved original Figure 5 domain and presentation:

- `T = 190--240 K` on a linear axis;
- `w = 5e-4--2 m s^-1` on a logarithmic axis;
- logarithmic period color normalization from `1e2` to `1e5 s` in the top panel;
- the two Episode 006 Hopf curves bounding the colored periodic-orbit domain; and
- a bottom `T = 210 K` slice over the full logarithmic physical-`w` axis.

Separate numerical continuation from presentation sampling:

1. **Authoritative continuation points:** retain irregular adaptive accepted spine/slice points with full solver, mesh, defect, amplitude, phase, and provenance diagnostics.
2. **Canonical scientific sampling:** use an irregular, error-controlled set of temperature slices seeded primarily from actual accepted spine points. Represent each converged slice as a monotone parameter sequence over its reliable `rho` range plus separate Hopf-limit records.
3. **Browser/plot display grid:** use shape-preserving interpolation of `log(P)` first along each slice in `rho`, then between irregular temperatures at fixed `rho`. Map display points to physical `log(w)`, never interpolate across either Hopf boundary, and attach validity/source flags to every displayed value.

The provisional v1 sampling skeleton uses exact slices at `T = 190, 192, ..., 240 K` plus `225 K`, while retaining every native spine point separately. On each reliable slice request exact anchors at `rho = 0, +/-0.25, +/-0.50, +/-0.75, +/-0.90, +/-0.97`, retain additional native accepted points, and add the approach points needed by the Hopf check. These are initial run targets, not a claim that production completion policy is settled.

Estimate interpolation error with shape-preserving interpolation of `log(P)`: withhold solved points along each slice in `rho`, and withhold whole temperature slices at fixed `rho`. Require maximum `|Delta log(P)| < 2e-3` in each test and add authoritative solves near the worst failure. Keep maximum temperature separation at `2 K`; never interpolate across a Hopf boundary, unresolved run point, stability checkpoint, or multivalued tripwire. A provisional browser grid uses `0.5 K` by `0.01 rho`, with solved/interpolated/invalid provenance on every value.

The lower panel uses authoritative exact-`T = 210 K` slice data rather than values sampled back from a heatmap raster. Whether the first continuation run is sufficient for the final production artifact is decided only at the post-run evidence-review checkpoint.

## Exact `T = 210 K` linearized-period curve

Generate the lower panel's red equilibrium-linearized curve independently from the periodic-orbit continuation. Over `w = 5e-4--2 m s^-1`, compute a high-resolution `T = 210 K` equilibrium branch with the validated C++ model and NOX equilibrium corrector, using `log(w)` continuation for robust predictors.

At every equilibrium evaluate the physical-coordinate Jacobian

```text
d(dn/dt, dq/dt, ds/dt) / d(n, q, s),
```

not the transformed collocation Jacobian. Track the conjugate eigenpair continuously and compute `P_lin = 2*pi/abs(Im(lambda))`. Where the pair becomes real or `abs(Im(lambda))` falls below a declared threshold, store the period as invalid/divergent and break the plot rather than clipping or inventing a finite value.

Use an initial 401-point log-spaced `w` grid and insert the exact Episode 006 Hopf points/frequencies as anchors. Track the conjugate pair by continuation distance, using eigenvector overlap to resolve ambiguity. Store `P_lin` only for a genuinely complex pair with `|Im(lambda)| > 1e-8 s^-1`; otherwise invalidate the row with `real_pair` or `frequency_below_floor` and create a plot gap. Add samples when shape-preserving `log(P_lin)` holdout error exceeds `2e-3`. Require exact Hopf-frequency and stratified Python physical-Jacobian parity to relative `1e-8`, and never clip periods to the paper plot range. Label this artifact as a C++ equilibrium/eigenvalue calculation distinct from native LOCA periodic-orbit continuation; it does not require long IVP integration.

## Backend authority and validation roles

Trilinos/NOX/LOCA is the authoritative backend candidate for eventual production. TASK-064 through TASK-068 generate qualification and continuation-run evidence; TASK-069 decides the justified downstream production scope. Any final production temperature slices and headline Figure 5 period map will be sourced from the native backend rather than Python.

Python is the executable numerical specification and exploration environment. Use it to develop the formulation, generate higher-order collocation coefficient tables with reproducible SymPy derivations where appropriate, and validate:

- the frozen fixed-parameter seed;
- all fixed-mesh migration fixtures;
- short spine and `T = 210 K` continuation segments; and
- a stratified set of production points covering both Hopf neighborhoods, interior period maxima, low/high temperatures, and easy/difficult meshes.

Independent IVP integration validates selected Python and LOCA orbits and periods. Python may generate a coarse full-domain exploratory map, but it need not duplicate every production LOCA orbit. AUTO periodic-orbit continuation is outside the required Episode 008 backend scope; Episode 006's native LOCA Hopf loci remain boundary inputs.

Final figure and browser-facing artifacts must label native LOCA periodic-orbit values, separate `hopf_linear_limit` records, and derived/interpolated display values distinctly.

## Trilinos algebra and NOX/LOCA interface stack

Do not enlarge the existing dense `LOCA::LAPACK` three-equilibrium-unknown adapter into the periodic-orbit implementation. Keep it intact as Episode 006 equilibrium/Hopf infrastructure.

Build the periodic-orbit path with the installed modern sparse stack:

- `Tpetra::Map`, `Tpetra::Vector`, and `Tpetra::CrsMatrix`;
- Thyra/Tpetra adapters into NOX and LOCA;
- an `OrbitLayout` that owns all global indexing and interval-ownership rules;
- a one-rank Tpetra communicator for the initial serial milestones, rather than a temporary dense vector/matrix implementation;
- a sparse graph constructed from the layout and reused while mesh topology and collocation order are fixed; and
- complete map, graph, group, linear-solver, and preconditioner reconstruction at remesh restarts.

The current Trilinos installation provides Tpetra, Thyra, NOX/LOCA Thyra interfaces, Belos, Amesos2, and Ifpack2; Epetra is not in its configured package list. Starting serially with Tpetra preserves the path to later interval distribution without another algebra-layer rewrite.

### Observed serial Tpetra midpoint assembly (TASK-059)

The midpoint migration core now uses square one-rank Tpetra domain/range maps and rejects communicators whose size is not one. `OrbitLayout` owns every global endpoint, explicit midpoint stage, `log(P)`, stage-row, cyclic update-row, and phase-row index. A fill-completed `Tpetra::CrsGraph` is retained by the assembler and supplied to every `Tpetra::CrsMatrix`; graph identity is therefore stable while the fixed layout is unchanged.

The graph and value assembly cover the local endpoint/stage blocks, final-to-first periodic wraparound, global `log(P)` derivatives, and stage-only normalized phase row. Small local Sacado evaluations provide transformed dynamics, state Jacobians, and physical/normalized parameter columns without differentiating the packed orbit. Ownership-safe diagnostics resolve global residual IDs through the range map and retain block max/RMS, phase magnitude/energy, state scaling, and largest-residual interval/component IDs. No Thyra group, NOX solve, pseudo-arclength row, Epetra path, or dense fallback is part of this milestone.

Language-neutral accepted and nonsolution fixtures cover `N=8` and translate the frozen TASK-056 `N=64` boundaries, phase samples, unknowns, and residual semantics. A deterministic manifest records source and fixture hashes plus matching formulation/tolerance constants. Focused parity checks compare all residual components at relative `1e-11` with a `1e-13` absolute floor and test assembled Jacobian actions plus rho/T-hat parameter columns against centered differences at `1e-6`; the C++ Jacobian action is independently checked against centered residual evaluations through the C++ assembler.

### Observed sparse Thyra/NOX fixed-parameter solve (TASK-060)

The fixed-parameter midpoint corrector now wraps the existing square one-rank Tpetra maps, residual, and retained-graph Jacobian in a Thyra state-function model. `NOX::Thyra::Group` owns the Newton correction while `log(P)` remains the final solution coordinate and the normalized phase condition remains the final residual row; no continuation or pseudo-arclength row is added. The linear solve factory explicitly selects Amesos2 KLU2 with repivoting on refactorization. Output reports the actual Amesos2 backend plus symbolic-factorization, numeric-factorization, and solve counters/status; no condition metric is claimed because this installed adapter does not expose one.

Solver contract `thyra-nox-amesos2-klu2-v1` uses an unscaled NOX residual-norm target of `1e-11`, at most 40 nonlinear iterations, Newton direction, and backtracking line search. Both the exact Python `N=64` periodic-Hermite/bootstrap sample and its manifest-versioned sinusoidal perturbation correct to the frozen TASK-056 solution. Corrected period and the fixed endpoint/stage weighted orbit metric use the binding `1e-8` Python-to-C++ tolerance.

Final acceptance remains independent of nominal NOX status. It requires stage/update maximum and RMS no greater than `1e-9`, phase no greater than `1e-10`, finite positive physical `n`, `q`, and `P`, finite positive phase energy, and reported successful KLU2 symbolic factorization, numeric factorization, and solve activity. Every failed gate produces a stable rejection reason. This is a fixed-uniform-mesh machinery milestone; its tiny discrete residual does not resolve the already documented `N=64` period discretization error. Native LOCA continuation remains TASK-061 scope.

## Newton linear solves and preconditioning

Use Amesos2 sparse direct factorization, preferably KLU2, for the initial serial midpoint, higher-order, and remeshing milestones. The expected systems remain modest (`385` unknowns for midpoint `N = 64`; `3073` for three-stage `N = 256`) and direct solves provide a correctness reference while residual/Jacobian behavior is still being established.

Retain factorization and conditioning diagnostics where the backend exposes them. Continue using KLU2 for the serial production Figure 5 workflow unless profiling demonstrates unacceptable memory or runtime.

Only after correctness and profiling justify it, add Belos GMRES with Ifpack2 while preserving the direct solver as a test oracle. A later distributed implementation should use a bordered/block preconditioner that explicitly handles the global phase row and `log(P)` column rather than relying only on an interval-local generic preconditioner. Iterative-solver development does not block adaptive higher-order scientific validation unless direct factorization becomes the measured bottleneck.

## Model derivatives and global Jacobian assembly

Use Sacado for small local model derivatives and explicitly assemble the known global collocation sparsity. Generalize the C++ model evaluator so transformed state and environmental controls can use Sacado scalar types. A local forward-AD evaluation should provide

```text
D_x g, g_T, g_log_w.
```

Apply normalized-parameter chain rules in the parameter adapter. Along the spine,

```text
g_T_hat = 25 [g_T + (d log_w_spine/dT) g_log_w].
```

At fixed temperature along a slice,

```text
g_rho = 0.5 (log_w_upper - log_w_lower) g_log_w.
```

Use these local values to assemble stage, endpoint-update, phase, and `log(P)` blocks explicitly into `Tpetra::CrsMatrix`. Do not apply AD to the entire packed orbit vector, which would discard the known sparse structure and scale poorly.

Validate `D_x g`, both physical-control derivatives, the normalized chain-rule columns, and all temperature-dependent coefficient effects against centered finite differences. Preserve value-level parity with the existing validated C++ model before switching the periodic-orbit path to the generalized evaluator.

### Observed local C++ derivative implementation (TASK-058)

The shared C++ header now promotes the environment and every temperature-dependent coefficient to the active scalar type. Its local Sacado path seeds exactly five directions, `(log(n), log(q), s, T, log(w))`, in one model evaluation and returns the transformed value plus `D_x g`, `g_T`, and `g_log_w`. Existing value-level, physical-Jacobian, equilibrium, and Hopf APIs remain compatible wrappers; no orbit layout is present in or differentiated by this local evaluator.

The parameter helpers implement the formulas above directly. C++/Python parity tests cover representative physical states, and centered differences independently check all three state directions, physical temperature, physical `log(w)`, the temperature-dependent coefficient contributions, and both normalized columns. The differentiable API rejects `include_evaporation=true`, preserving the binding smooth no-evaporation scope rather than silently differentiating through its state-dependent switch.

## Generated collocation coefficients

Add an Episode 008 SymPy generator for each supported collocation rule. Derive:

- collocation nodes `c_j`;
- Runge--Kutta stage coefficients `a_jk = integral_0^c_j ell_k(xi) dxi`;
- update/quadrature weights `b_j = integral_0^1 ell_j(xi) dxi`;
- integrated Lagrange transfer polynomials `L_j(tau) = integral_0^tau ell_j(xi) dxi`; and
- independent defect-check nodes and evaluation matrices.

Emit one canonical machine-readable artifact containing symbolic expressions where practical, 17-digit floating values, family, stage count, formal order, and checksum. Generate both Python and C++ source tables from that artifact. Commit the generator, canonical artifact, and generated sources; runtime use must not require SymPy.

A regeneration test must fail on generated-file drift. Algebraic tests include `sum_j b_j = 1`, `sum_k a_jk = c_j`, and exactness through the expected polynomial degrees. The initial artifact contains one-, two-, and three-stage Gauss--Legendre rules. Any later Radau rule must enter through the same pipeline.

## Seed interpolation and mesh transfer

Use two explicit interpolation paths.

For the Episode 007 IVP seed, construct a periodic cubic Hermite interpolant in transformed coordinates `(log(n), log(q), s)` over the selected final complete cycle. At each irregular IVP sample, evaluate the transformed model field and use

```text
dx/dtheta = P g(x)
```

as the Hermite slope. Enforce periodic endpoint matching and evaluate this interpolant at every initial endpoint and collocation-stage location. This avoids independent component splines whose slopes are unrelated to the ODE.

For collocation-to-collocation transfer, evaluate the old element's actual collocation polynomial. With local coordinate `tau in [0,1]`,

```text
p_i(tau) = x_i + Delta theta_i P sum_j
           [integral_0^tau ell_j(xi) dxi] g(X_i,j),
```

where `ell_j` are Lagrange basis polynomials through the old collocation nodes. Use this representation to transfer endpoint values, stage values, the phase-reference orbit, and secant/tangent orbit components. Midpoint transfer reduces to a linear element segment.

Transfer `log(P)` directly and renormalize transferred tangents in the new continuation metric. After every transfer, run nonlinear correction and record pre/post-correction residuals and orbit changes. Generate integrated Lagrange coefficient tables reproducibly with SymPy for shared Python/C++ fixtures.

## Native LOCA continuation and remesh restarts

Use LOCA's native pseudo-arclength stepper on every fixed mesh/layout. This applies to continuation from the Episode 007 bootstrap point to the exact spine, continuation along the spine in `T_hat`, and both `rho` directions of every fixed-temperature slice.

Expose only the square base system

```text
F(y; lambda) = 0
```

containing stage equations, endpoint updates, and the normalized phase condition, with `log(P)` inside `y`. LOCA owns predictor construction, tangent calculation, arclength constraint, adaptive continuation step size, rejection, and retry while the layout is unchanged. Do not substitute a repository-owned parameter grid with NOX correction and call it LOCA continuation.

Bootstrap every new continuation direction with an explicit two-point secant. From the accepted origin orbit, take a small signed step in the active normalized coordinate (`rho` for fixed-temperature moves/slices or `T_hat` for the spine), use the origin orbit as predictor and phase reference, and run fixed-parameter NOX correction. If correction fails or the weighted orbit change is excessive, halve the startup step and retry. Normalize the resulting secant in the agreed continuation metric and pass its orientation to LOCA. Record these corrected neighbors as `branch_bootstrap`, not ordinary native-LOCA steps. Use the same startup rule in Python.

Treat remeshing as a structural continuation boundary:

1. stop the current LOCA stepper at an accepted point;
2. transfer the solution, phase reference, and tangent with the old piecewise collocation polynomial;
3. rebuild Tpetra/Thyra/NOX/LOCA maps, graphs, groups, solver objects, and preconditioners;
4. perform fixed-parameter NOX/KLU2 correction on the new mesh;
5. renormalize the transferred tangent in the new metric; and
6. restart the native LOCA stepper.

Accept the v1 restart only when the established residual, phase, positivity, and linear-solve gates pass; transferred values are finite and physically positive where required; phase-aligned old/new weighted-orbit change is at most `0.25`; `|Delta log(P)| <= 0.20`; the new reference has positive finite energy and phase residual at most `1e-10`; and the renormalized tangent has cosine at least `0.5` with the transferred old tangent while preserving active-coordinate orientation.

For `k>0` originally marked elements, retry in exactly this order:

1. full marked `h` set plus the requested `r` move;
2. the same full marked `h` set plus half the requested `r` move; and
3. the first `ceil(k/2)` marked elements sorted by descending defect, breaking ties by lower old element index, plus half the requested `r` move (`k=1` retains that one element).

For a pure-`r` remesh (`k=0`), attempts 1 through 3 use the requested, half, and quarter `r` displacement, respectively. After failure of attempt 3, record `remesh_restart_failed`. A tangent-only failure uses the established deterministic two-point bootstrap instead of rejecting an otherwise valid corrected orbit.

Python retains an explicit augmented pseudo-arclength equation as the transparent reference implementation, but the LOCA base group never duplicates that row. Output diagnostics must distinguish accepted/rejected continuation steps, remesh restarts, and uninterrupted branch steps.

## Serial solve and coarse-grained production concurrency

Assume serial execution within every nonlinear, linear, continuation, variational, and remeshing solve throughout Episode 008. Use a one-rank Tpetra communicator, but do not add generalized MPI interval ownership where it complicates the implementation. Scientific and implementation clarity take precedence over latent within-solve parallel capability.

Exploit only coarse-grained process/job concurrency after the interior spine is complete:

- the two temperature directions along the spine can be run independently from the bootstrap point;
- each temperature slice is independent once its spine seed exists; and
- the lower- and upper-`rho` directions of each slice can run independently from that seed.

Write deterministic per-branch/per-slice artifacts and restart manifests so interrupted or partially failed production can resume without recomputing completed work. Distributed interval assembly, bordered parallel preconditioning, and MPI remesh transfer are follow-up infrastructure outside Episode 008.

## Python-to-Trilinos migration contract

Follow gated behavioral migration rather than a monolithic C++ rewrite:

1. freeze small Python reference cases;
2. establish unknown-layout and pack/unpack parity;
3. compare residuals component-by-component on converged and nonsolution vectors;
4. validate state Jacobian-vector products, the `log(P)` column, phase row, and parameter derivatives;
5. solve one fixed-parameter orbit with NOX;
6. continue a short `log_w` branch with LOCA, allowing LOCA—not the base residual—to own pseudo-arclength;
7. preserve diagnostics while adding higher order and remeshing.

The square fixed-parameter residual exposed to NOX/LOCA contains collocation equations plus the phase condition, with `log(P)` in the solution vector. The active continuation parameter is exposed through LOCA's parameter interface. No duplicate pseudo-arclength equation is appended to the base group.

### Observed C++ higher-order fixed-parameter migration (TASK-065)

The one-rank sparse Tpetra base system now selects the frozen one-, two-, or three-stage Gauss rule while retaining the square `3N(r+1)+1` contract. Stage rows couple each interval endpoint to all local stages, update rows retain cyclic wraparound, and every row includes the analytic `log(P)` contribution where required. The quadrature phase energy/row and normalized rho/T-hat columns use the same rule weights and local Sacado derivatives as residual/Jacobian assembly. The fill-completed graph remains stable for a fixed rule/mesh.

The Thyra/NOX fixed-parameter seam remains backed by Amesos2 KLU2 and independently enforces NOX convergence, stage/update maximum and RMS gates, normalized phase, physical positivity/finiteness, phase energy, and reported symbolic/numeric factorization and solve activity. Exact Python solutions are perturbed deterministically before correction so required fixtures exercise a real KLU2 solve. Missing early-solve diagnostics no longer throw; they remain unreported and fail acceptance. TASK-066 subsequently removed the temporary higher-order LOCA guard and generalized the continuation helpers while retaining midpoint compatibility.

The versioned C++ bundle contains the canonical two-stage `N=64`, canonical three-stage `N=32` and `N=64`, all three `T=210 K` three-stage `N=32` guard corrections, the upstream-rejected canonical three-stage `N=16` case, and exact projections of both TASK-064 language-neutral `N=64` nonsolutions. Fixture status means TASK-064 finite-dimensional nonlinear acceptance, not scientific fixed-uniform qualification. All six accepted corrections match Python periods and phase-aligned weighted orbits within `1e-8`; the rejected case propagates `upstream_fixture_rejected` without invoking NOX, while nonsolutions report `fixture_not_correction_input`.

The curated `cpp_higher_order_correction_results.json` is generated by actually executing the current C++ binary across the complete correction/status bundle. It binds the binary's six compiled source fingerprints to current files and records rule, mesh, layout/block and retained-graph dimensions, coefficient checksum, NOX/KLU2 counters, residual diagnostics, rejection reasons, executable/runtime provenance, and corrected Python parity. Failed correctors explicitly mark the final residual unavailable rather than serializing a synthetic zero residual.

### Observed native fixed-mesh LOCA continuation (TASK-061)

The C++ midpoint family now exposes exactly one scalar Thyra/LOCA parameter vector named `rho` or `temperature_hat`; the base x/f spaces remain square `6N+1`, and only LOCA's `Arc Length` continuation wrapper has dimension `6N+2`. The model supplies the analytic normalized `DfDp` column and retains the fixed sparse Jacobian graph. A weighted Thyra group replaces LOCA's default dimension-normalized state dot product with the binding endpoint/stage half-weighted metric, while arc-length parameter rescaling is disabled. Consequently native LOCA owns its predictor, tangent, arclength constraint, adaptive step sizing, failed attempts, and retry policy without changing the globally frozen metric.

Every signed direction is initialized by a separately recorded fixed-parameter NOX neighbor. Failed or excessive weighted bootstrap changes halve deterministically before the accepted neighbor defines the oriented metric-normalized secant. Bootstrap records are never counted as native accepted continuation steps. The two controlled phase-reference refreshes remain structural boundaries: preserve physical `(T, log(w))`, verify all fixed-parameter residual gates under the refreshed normalized phase row, rebuild the model/group/stepper, and record old/new reference lineage.

The versioned validation artifact independently replays the multi-step `T=225 K` exact-spine move, both spine directions (including exact `T=210 K`), and both signed `T=210 K` rho slices through C++ `LOCA::Stepper`. Its NPZ contains the vectors emitted by native save callbacks rather than copied Python vectors, and generation fails if any native vector digest equals any frozen Python point digest. Callback records distinguish the initial solve, each attempted/retried corrector, and final target solve with finite attempted/accepted coordinates and active-coordinate deltas; these are not presented as LOCA arclength step sizes. Raw LOCA iterator counters are separately named from derived regular attempt/accepted/rejected and initial/final save partitions. A deterministic smoke fault forces one native rejection, confirms a reduced-coordinate-delta retry, and is persisted in the curated contract. Every native accepted point satisfies the versioned `2e-7` period-relative and weighted-orbit tolerance against an independent Python fixed-parameter correction at the identical coordinate, seeded from the nearest frozen Python branch vector rather than the native result. Interior adaptive points also retain nearest transparent-Python-branch diagnostic differences because the native and Python pseudo-arclength steppers select different grids. Five separately corrected signed bootstrap secants are injected through LOCA's Restart first-step predictor. At both refreshes, a strict fixed-parameter NOX/KLU2 solve under the refreshed phase row supplies the accepted restart origin, and the artifact records residual gates, unchanged physical coordinates, chronology, and rebuilt assembler/model/weighted-group/stepper lineage. Executable transitive source fingerprints (including the NOX adapter and collocation coefficients) plus source, fixture, seed, Hopf-locus, runtime, Trilinos, and lockfile hashes prevent stale arbitrary builds from satisfying artifact checks. The previously observed second-step NaN came from misnested Predictor/Step Size sublists plus a MaxIters status test that bypassed parameter-bound stopping and left the finish target at zero; it was not an installed-LOCA defect. These remain `N=64` midpoint machinery results and do not supersede the production discretization requirements.

## Fold, multistability, and secondary-bifurcation tripwire

The physical expectation, supported by all evidence through TASK-061, is one unique attracting periodic orbit at each point inside the Hopf loci. The first adaptive implementation therefore provides a cheap tripwire rather than speculative multibranch infrastructure.

Always record active-coordinate tangent signs and the accepted coordinate sequence. Flag a candidate on a tangent sign change, a normalized-coordinate reversal above `1e-4`, or two accepted points within `1e-4` in normalized coordinate whose relative periods differ by more than `1e-3` or whose phase-aligned weighted orbits differ by more than `1e-2`. If no trigger occurs, record `single_valued_observed`. If one occurs, stop automatic processing for that slice and defer exact-coordinate confirmation, multibranch artifacts, and display policy to the mandatory evidence-review checkpoint. Do not implement branch selection or multiple display values in v1.

## Downstream Floquet stability direction

Floquet postprocessing is outside TASK-064 through TASK-068. Those tasks must record Floquet-dependent evidence and gates as `not_evaluated`; they must not reject an initial-run orbit or activate a Floquet-derived Radau trigger. TASK-069 reviews the continuation evidence and decides whether to create and require this downstream capability.

If approved downstream, native LOCA owns the orbit and an independent Python/SciPy postprocessor computes all three Floquet multipliers from saved native piecewise collocation polynomials. They remain post-solve diagnostics, not nonlinear collocation unknowns. Integrate the transformed variational equation over normalized phase,

```text
Phi'(theta) = P D_x g(x_coll(theta)) Phi(theta),
Phi(0) = I,
```

evaluating `x_coll` from the accepted piecewise collocation polynomial. Use DOP853 at `rtol=1e-10`, `atol=1e-12`, repeating at `1e-11`/`1e-13` near or beyond a threshold. Require implicit-Radau comparison at stratified difficult points and every suspected unit-circle crossing. Record the mixed C++-orbit/Python-postprocessor provenance.

Identify the trivial multiplier as the one nearest `1` and require `|mu_trivial-1| < 1e-3`. Matched multipliers must agree under DOP853 tolerance refinement to `|Delta mu|/max(1,|mu|) < 1e-5`, and DOP853/Radau comparisons to `1e-4`. Classify nontrivial multipliers as attracting when all magnitudes are below `1-1e-3`, unstable when any exceeds `1+1e-3`, and otherwise near-unit ambiguous. A crossing candidate requires consecutive points beyond opposite sides of the ambiguity band and confirmation by both integrators. Selected finite-difference or Poincare-return multiplier magnitudes must agree within 1%.

If this downstream direction is approved, store Floquet data in authoritative periodic-orbit branch records; browser display is not required in Episode 008. `hopf_linear_limit` records retain equilibrium eigenvalues and frequency rather than regular-orbit Floquet multipliers.

## Downstream independent IVP validation direction

Except for TASK-064's canonical DOP853 comparison, IVP integration and IVP-based Radau decisions are outside TASK-064 through TASK-068 and are recorded as `not_evaluated`. TASK-069 decides the later IVP/Radau validation scope. If approved downstream, IVP integration is a selected validation method, never the period-generation algorithm. The authoritative Figure 5 surface remains based on native LOCA periodic-orbit continuation; do not reproduce the paper's long-integration period extraction at every parameter point.

At stratified validation points, perform two complementary checks:

1. **One-period return:** start from phase-aligned `x_coll(0)`, integrate the transformed IVP for collocation period `P`, report

   ```text
   R_flow = ||S_x [phi_P(x_coll(0)) - x_coll(0)]||,
   ```

   and compare the dense IVP trajectory over that period with the collocation polynomial after phase alignment.
2. **Attractor check:** start from the paper-style perturbed equilibrium, integrate only at selected points until the established cycle period/amplitude drift criterion passes, then compare the final cycle and period against the collocation orbit.

Use a high-accuracy adaptive IVP solver independent of collocation. At the most difficult selected points, require an explicit high-order method such as DOP853 and implicit Radau to agree before treating the IVP result as reference.

The downstream validation direction uses at least 12 unique points after deduplication: the four fixed higher-order qualification points; both `210 K` Hopf sides; low/high-temperature interiors; largest/shortest accepted periods; worst accepted defect; worst trivial-multiplier error; and worst interpolation holdout. Every selected point receives transformed-state DOP853 one-period integration at `rtol=1e-10`, `atol=1e-12`, with period, phase-aligned weighted-trajectory, and weighted return errors below `1e-3`. The six hardest or headline points also require IVP Radau agreement below `1e-3`; at least four, including both Hopf sides and the largest-period case, receive perturbed-equilibrium attractor checks. This selection is applied after the adaptive run exposes the actual worst cases.

## Versioned numerical acceptance hierarchy

Use staged acceptance criteria. These are initial versioned tolerances. They may be tightened from evidence, but loosening requires documented scientific justification and a method-version change. All relative comparisons use explicit recorded absolute floors.

### Python-to-C++ formulation parity

On identical packed vectors, meshes, coefficient tables, and phase references:

- residual component relative error at most `1e-11`;
- centered-difference assembled-Jacobian and parameter-column directional error

  ```text
  ||Jv - FD(v)|| / max(1, ||Jv||) <= 1e-6;
  ```

- fixed-mesh corrected period and weighted-orbit agreement at most `1e-8` away from Hopf degeneracy.

### Accepted nonlinear orbit

Require:

- scaled stage/update residual maximum and RMS below explicit thresholds, initially `1e-9`;
- normalized phase residual below `1e-10`;
- positive finite physical `n`, `q`, and `P`;
- no failed or unreported linear solve; and
- acceptable phase energy and phase-row conditioning.

### Initial-run discretization evidence

Two successive adapted/order-refined solutions must satisfy:

- relative period change below `1e-3`;
- phase-independent weighted orbit difference below `1e-3`;
- maximum independent relative defect

  ```text
  eta_inf = max_check_points
      ||S_x (p' - P g(p))|| / [1 + ||S_x P g(p)||]
      < 1e-4;
  ```

A future production method that includes the downstream Floquet stage also requires trivial Floquet multiplier error `|mu_trivial - 1| < 1e-3`. This criterion is `not_evaluated` and is not an initial-run acceptance gate in TASK-064 through TASK-068.

Period and orbit-convergence checks remain mandatory even when the defect passes.

### Downstream cross-method validation

TASK-064 requires its canonical DOP853 comparison. Broader stratified collocation-to-IVP validation is `not_evaluated` through TASK-068. If TASK-069 approves that downstream scope, require LOCA-to-Python and collocation-to-independent-IVP period/orbit differences below `1e-3` at the selected points.

### Hopf approach evidence and ownership

TASK-068 records amplitude, period, diagnostics, and terminal status for near-Hopf approach points, targeting at least five reliable points when v1 continuation reaches them. It does not decide whether to connect the nonlinear curve to the Hopf limit or preserve a final gap. TASK-069 performs or reviews the documented quadratic and quartic fits, compares them with `2*pi/omega_H`, and decides the justified downstream connection/gap policy.

## Schema-versioned output direction

The eventual production contract uses identifier `episode8-figure5-production-v1` and formal schemas under `episodes/008-figure5-periodic-orbit-continuation/schemas/`. JSON/JSONL use JSON Schema; CSV and NPZ manifests use explicit column/array schema JSON. Stable IDs, method/schema version, backend/source class, units and coordinate conventions, validity, and reason codes are mandatory. Incompatible changes increment the schema version.

The six intended artifact layers are:

1. **`continuation_points.csv`:** one row per authoritative accepted periodic orbit or Hopf-limit record, with scientific scalars and Floquet diagnostics.
2. **`orbits/<point_id>.npz`:** curated full vectors for canonical samples, reliable Hopf-approach points, phase/remesh anchors, and IVP/Floquet/worst-defect/interpolation fixtures, with a checksummed manifest. Intermediate native vectors remain restart/checkpoint artifacts; an absent `orbit_artifact_id` never implies interpolation.
3. **`continuation_events.jsonl`:** append-only accepted/rejected LOCA steps, NOX and linear-solve diagnostics, step-size changes, remesh decisions, transfers, and restarts.
4. **`run_metadata.json`:** method/schema versions, model parameters, coefficient-table checksums, tolerances, commands, Trilinos configuration, source commits, upstream checksums, and completion summaries.
5. **`linearized_period_210.csv`:** the authoritative C++ equilibrium/eigenvalue lower-panel curve and validity reasons.
6. **`figure5_browser_dataset.json`:** compact display coordinates, periods, validity/source flags, Hopf curves, authoritative lower-panel samples, interpolation method, and authoritative-point links, without full orbit vectors.

These schemas are a recorded downstream direction, not part of the first continuation implementation tasks. Exact fields and downstream production tasks are defined after the adaptive run has been inspected.

## Required diagnostics already agreed in principle

At minimum, retain enough information to distinguish discrete convergence from orbit-resolution quality:

- residual norms by collocation and phase blocks;
- phase transversality/sanity information;
- period and continuation step information;
- nonlinear and linear iteration counts;
- Jacobian directional-check results when enabled;
- state and residual scaling metadata;
- mesh-resolution/defect indicators;
- transfer/restart provenance after remeshing;
- comparison against an independent IVP-derived orbit/period at selected points;
- comparison of nonlinear period with `2*pi/Im(lambda)` near Hopf boundaries.

The v1 adaptation, phase, Hopf, interpolation, and tripwire thresholds above are implementable operational hypotheses for the initial adaptive run. Their retention or revision as production tolerances remains a decision for the post-run checkpoint. Floquet thresholds are downstream direction only and are `not_evaluated` through TASK-068.

## TASK-062 continuation-first staging and backlog boundary

TASK-053 through TASK-061 completed the conservative midpoint migration: frozen seed and coefficient tables, Python fixed-parameter and pseudo-arclength references, Sacado local derivatives, sparse Tpetra assembly, fixed-parameter NOX/KLU2 correction, and native LOCA continuation. The evidence is internally consistent: Python and C++ agree closely on identical midpoint problems, native LOCA genuinely owns continuation, and the discrete midpoint residual can be tiny while period error remains scientifically large. In particular, the canonical `N=64` midpoint period is over 12% above the Episode 007 reference, while midpoint refinement reduces that error to about 0.7% at `N=256`. TASK-061's native/Python parity therefore validates machinery, not Figure 5 periods.

The approved next stage deliberately stops short of planning every exceptional production outcome. Execute six atomic tasks in order:

1. TASK-064: Python higher-order fixed-mesh qualification;
2. TASK-065: C++ higher-order sparse fixed-parameter correction and parity;
3. TASK-066: native higher-order fixed-mesh LOCA continuation;
4. TASK-067: Python `h/r` adaptation reference;
5. TASK-068: native adaptive LOCA remesh/restart continuation and the planned run; and
6. TASK-069: mandatory post-run evidence review and next-stage design checkpoint.

Only the checkpoint may define downstream production tasks after inspecting period/order convergence, defects, mesh distributions, restart behavior, continuation coverage, failure modes, and cost. TASK-063 digitization may proceed independently and supplies external image-derived comparison evidence; it does not block implementing or running continuation and is never a numerical tuning target. Flag later paper discrepancies when `|Delta log(P)| > max(3 sigma_digitized_logP, 0.02)`, but internal convergence and independent IVP validation remain authoritative.

## Deferred decisions for the post-run checkpoint

The operational constants above are v1 hypotheses for an informative run. The checkpoint must decide, from evidence, whether to:

- retain or revise monitor weights, mesh caps, and phase/Hopf thresholds;
- add Radau, coarsening, landmark alignment, local `hp`, or iterative linear solvers;
- implement multibranch confirmation or secondary-bifurcation policy after a tripwire;
- freeze exact production schema fields and curated-vector retention in code;
- accept or revise the provisional sampling/interpolation skeleton;
- create tasks for Floquet production postprocessing, the `210 K` linearized curve, full-domain production continuation, IVP validation, paper comparison, and final Figure 5/browser artifacts; and
- define exceptional-gap and final scientific-completion policies based on observed rather than hypothetical failures.

Until then, do not interpret a v1 unresolved point as permission to interpolate over it or as proof that elaborate exceptional handling is needed.

## TASK-069 post-run checkpoint decisions

The mandatory checkpoint is now recorded in [`task069-evidence-review-and-next-stage-design.md`](task069-evidence-review-and-next-stage-design.md). It reviews TASK-064 through TASK-068 evidence and concludes that the method is structurally promising but not production-sufficient for final Figure 5 artifacts.

Key dispositions:

- fixed-uniform higher-order meshes are rejected as production data and retained only as diagnostics/parity fixtures;
- three-stage Gauss with external `h/r` adaptation, the two-grid defect gate, the composite r monitor, restart gates, phase refresh policy, fixed scaling, KLU2 oracle role, and single-valued tripwire channels are retained as v1 production-candidate hypotheses;
- Radau collocation, coarsening, landmark alignment, local `hp`, iterative solvers, and multibranch confirmation are not warranted by current evidence and remain trigger-only;
- Floquet postprocessing, broader selected IVP validation, the T=210 K linearized-period curve, production schemas, measured runtime/resource profiling, full-domain native adaptive continuation, interpolation/holdout artifacts, and final paper/browser outputs are approved as downstream work depending on TASK-069;
- TASK-063 digitization is unavailable and remains external image-derived evidence only when completed; and
- near-Hopf quadratic/quartic fits are not performed because TASK-068 reached zero approach points, so the current policy is an explicit unresolved gap until later evidence supplies sufficient approach points or justified stop reasons.

The TASK-068 provisional ledger's twenty-five pending/failed targets must remain explicit terminal statuses. They are not permission to interpolate across unresolved regions and they are not evidence for speculative exceptional machinery.

## TASK-070 production schema boundary

TASK-070 implements the first approved downstream item from TASK-069: a formal `episode8-figure5-production-v1` schema and validator boundary before new production data are generated. The contract and command are documented in [`production-schemas.md`](production-schemas.md), with the machine-readable schema contract at [`../schemas/episode8-figure5-production-v1.contract.json`](../schemas/episode8-figure5-production-v1.contract.json).

The schema requires provenance and checksum records, exact temperature/`log_w`/`rho` coordinate conventions, transformed orbit-state and normalized-phase conventions, period and resource units, method/schema versions, unambiguous validity/source flags, curated NPZ vector manifests, T=210 K linearized-period rows, and browser/display records that distinguish solved, unresolved, explicit-gap, invalid, validated-interpolated, and external-comparison evidence. Digitized paper data remain non-authoritative external comparison overlays only.

## TASK-072/TASK-073 measured pilot gate

TASK-072 replaced the provisional 210--226 K pilot ledger with measured backend-emitted terminal statuses, but all 31 targets remain `resolution_unresolved` explicit gaps. The measured `spine-210K` remesh/restart seam is retained as backend evidence, not accepted production data, because the exact native restart vector lacks backend-bound independent defect and period/orbit convergence gates.

TASK-073 is recorded in [`task073-native-adaptive-pilot-reconciliation.md`](task073-native-adaptive-pilot-reconciliation.md). It preserves the TASK-072 status counts (`accepted=0`, `resolution_unresolved=31`, `failed=0`, `near_hopf_stop=0`, `tripwire_stop=0`), selects no IVP subset because no accepted pilot point exists, and does not use interpolation or external digitized evidence to change terminal statuses. The retained v1 adaptive method is not falsified, so no method-version revision is required now, but full-domain production continuation is not authorized until TASK-081 follow-up gate work supplies accepted native adaptive pilot points with independent Python/IVP validation or explicit gap decisions.

## TASK-081 follow-up gate

TASK-081 is recorded in [`task081-native-adaptive-pilot-gate-followup.md`](task081-native-adaptive-pilot-gate-followup.md). It binds the exact `spine-210K` post-remesh native restart vector to the missing backend defect and period/orbit convergence gates, then validates that accepted point with same-coordinate Python correction and DOP853 one-period IVP evidence. The revised pilot gate is `accepted=1`, `resolution_unresolved=30`, `failed=0`, `near_hopf_stop=0`, and `tripwire_stop=0`.

TASK-075 may proceed under the retained `external-gauss3-hr-adaptive-v1` method, and no method-version revision is required now. This does not authorize interpolation across the remaining 30 unresolved pilot targets; each later full-domain target must still receive one recorded terminal status, using native-backend-emitted status for attempted/accepted solves and explicit policy-gap status when no authorized route exists without crossing unresolved regions, while preserving Hopf, tripwire, instability, and unresolved-gap boundaries.
