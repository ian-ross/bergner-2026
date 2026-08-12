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

Record `E_ref` and monitor the phase-row angle with the current time-shift direction, accumulated weighted distance from the reference, and nonlinear-iteration deterioration. Stop the regular-orbit approach to Hopf when phase energy or conditioning crosses calibrated reliability thresholds. Trigger a controlled `phase_reference_refresh` restart when alignment diagnostics cross thresholds or after a conservative maximum branch distance:

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

## Higher-order family and stiffness qualification

Use Gauss--Legendre as the primary order progression:

1. one-stage Gauss / implicit midpoint, order 2;
2. two-stage Gauss, order 4;
3. three-stage Gauss, order 6.

Gauss methods are A-stable but not L-stable. In this global periodic boundary-value setting they can represent the stiff orbit, but only when the short nucleation layer is resolved by the mesh. Higher polynomial order does not make an element that spans an unresolved transition scientifically accurate.

The Episode 007 canonical orbit has a period near `2458 s`, while the sampled 10--90% increase in `n` takes roughly `38 s` (about `1.6%` of the period). A uniform 64-element mesh therefore places only about one element across this transition; even 128 uniform elements provide only about two. Other Figure 5 points may be more severe.

Production acceptance requires:

- a mesh concentrated around high scaled speed, curvature, and nucleation activity;
- polynomial defect evaluation at independent off-collocation check points;
- splitting or redistribution where scaled defect is concentrated;
- period convergence across mesh refinement and collocation order; and
- independent IVP comparison at selected easy and difficult points.

Keep the coefficient-table interface general enough to add three-stage Radau IIA as a selected stiff-case comparison if adaptive three-stage Gauss shows poor convergence. Do not implement multiple families before evidence justifies it, and do not declare three-stage Gauss the production method solely from its formal order.

## Adaptive mesh design

This section records the agreed direction for a later phase, not parameters that block the initial fixed-mesh implementation. Exact monitor coefficients, movement/splitting bounds, thresholds, and mesh caps will be designed and calibrated only after native fixed-mesh LOCA continuation works (TASK-062).

After the deliberately uniform, non-adaptive baseline, use a combined external `h/r` remesh-and-restart design. The orbit remains smooth; its rapid nucleation segment is an internal layer rather than a discontinuous shock, so upwind or ENO/WENO-style numerical dissipation is not appropriate for the collocation equations.

The first adaptive implementation will:

1. retain piecewise Gauss collocation on a nonuniform normalized-phase mesh;
2. use `h`-refinement to split difficult elements;
3. use `r`-adaptation to redistribute a fixed set of element boundaries by approximately equidistributing monitor mass;
4. use scaled polynomial defect evaluated at independent off-collocation points as the primary error signal;
5. supplement defect with scaled state-space speed, curvature, and physics landmarks such as saturation extrema, nucleation-rate maxima, and threshold crossings;
6. retain a positive monitor floor so slow orbit segments keep adequate resolution;
7. transfer the old piecewise polynomial solution and phase reference to the new layout, then restart nonlinear correction/continuation; and
8. add coarsening and `hp` decisions only after splitting and redistribution work reliably.

Landmark-aligned element boundaries help prevent the short nucleation pulse from repeatedly falling inside a large element, but landmarks do not replace the integral phase condition. Multiple independent check points and geometric/physics monitors are required because a defect estimator can itself miss a pulse when all check points undersample it.

Do not initially make mesh coordinates nonlinear unknowns. Do not introduce Shishkin/Bakhvalov meshes unless later analysis identifies a useful explicit singular-perturbation parameter and predictable layer width/location.

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

3. stop regular orbit continuation when amplitude, phase transversality, or conditioning crosses documented reliability thresholds rather than relying only on a fixed distance from the Hopf coordinate;
4. retain each exact Episode 006 Hopf boundary as a separate `hopf_linear_limit` record with `P_H = 2*pi/omega_H`, not as a collocation orbit;
5. validate boundary approach over several small-amplitude orbit points with the supercritical-Hopf relation `P(A) = P_H + c A^2 + O(A^4)`;
6. connect the last reliable nonlinear orbit visually to the marked Hopf limit only when this extrapolation agrees with `P_H` within tolerance; and
7. distinguish `periodic_orbit`, `hopf_linear_limit`, and outside-cycle-region cells in browser-facing data.

This prevents a clickable heatmap boundary from being misrepresented as a finite-amplitude periodic orbit.

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

Initially limit maximum accepted spine-point temperature separation to approximately `2 K`, while permitting smaller native LOCA steps. Require dedicated exact anchor slices only at `T = 190 K` and `240 K` to avoid extrapolating at the display-domain boundaries, `T = 210 K` for the required lower panel, and the existing `T = 225 K` bootstrap.

Estimate temperature interpolation error by withholding selected computed slices and reconstructing them from neighboring slices. Where the versioned threshold fails, add a new slice near that temperature, using a fixed-parameter corrected spine predictor if no suitable native accepted spine point exists. Continue until the display dataset passes. Retain irregular authoritative temperatures separately from the regular display grid so interpolated pixels cannot be mistaken for solved orbits.

The lower panel uses authoritative exact-`T = 210 K` slice data rather than values sampled back from a heatmap raster. Select final display `rho` and temperature densities using interpolation-error tests instead of coupling solver steps to heatmap pixels.

## Exact `T = 210 K` linearized-period curve

Generate the lower panel's red equilibrium-linearized curve independently from the periodic-orbit continuation. Over `w = 5e-4--2 m s^-1`, compute a high-resolution `T = 210 K` equilibrium branch with the validated C++ model and NOX equilibrium corrector, using `log(w)` continuation for robust predictors.

At every equilibrium evaluate the physical-coordinate Jacobian

```text
d(dn/dt, dq/dt, ds/dt) / d(n, q, s),
```

not the transformed collocation Jacobian. Track the conjugate eigenpair continuously and compute `P_lin = 2*pi/abs(Im(lambda))`. Where the pair becomes real or `abs(Im(lambda))` falls below a declared threshold, store the period as invalid/divergent and break the plot rather than clipping or inventing a finite value.

Insert the exact Episode 006 Hopf points/frequencies as anchors. Overlay authoritative nonlinear LOCA periods only over their reliable periodic-orbit interval, with separate Hopf-limit records. Validate selected equilibrium/eigenvalue rows against the existing Python physical-Jacobian implementation. Label this artifact as a C++ equilibrium/eigenvalue calculation distinct from native LOCA periodic-orbit continuation; it does not require long IVP integration.

## Backend authority and validation roles

Trilinos/NOX/LOCA is the authoritative production implementation. Every final production temperature slice and the headline Figure 5 period map will be sourced from it.

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
2. transfer the solution, phase reference, and tangent;
3. rebuild Tpetra/Thyra/NOX/LOCA maps, graphs, groups, solver objects, and preconditioners;
4. perform fixed-parameter NOX correction on the new mesh;
5. renormalize the transferred tangent in the new metric; and
6. restart the native LOCA stepper.

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

## Fold, multistability, and secondary-bifurcation policy

The physical expectation is one unique attracting periodic orbit at each parameter point inside the two Hopf loci, but treat this as a hypothesis to test rather than an interpolation assumption.

Allow native pseudo-arclength LOCA to continue through folds in `rho` or `T_hat`. Detect active-parameter tangent sign changes, repeated physical `(T, w)` values with distinct weighted orbit geometry or periods, and Floquet unit-circle crossings associated with cycle folds or secondary bifurcations.

If a branch is multivalued, retain every distinct orbit with a stable branch ID; do not collapse them into one heatmap value. Mark the affected browser/display region `multivalued_requires_policy` and stop automatic production interpolation there pending scientific review. If later evidence shows only one branch is attracting, selecting it for display still requires an explicit documented policy.

Treat discovered multistability or a secondary periodic-orbit bifurcation as a scientific result and scope checkpoint rather than a routine solver failure. Require monotonicity in the active physical parameter only for a final branch segment used as a single-valued Figure 5 slice after these checks pass.

## Floquet stability diagnostics

Compute all three Floquet multipliers for every authoritative production periodic orbit as post-solve diagnostics, not as nonlinear collocation unknowns. Integrate the transformed variational equation over normalized phase,

```text
Phi'(theta) = P D_x g(x_coll(theta)) Phi(theta),
Phi(0) = I,
```

evaluating `x_coll` from the accepted piecewise collocation polynomial. Use a strict high-accuracy variational integrator independent of the collocation residual assembly.

Require and report one trivial multiplier near `1`; its error is an independent orbit-resolution diagnostic. Classify attraction from the remaining multipliers and flag unit-circle crossings or ambiguous near-unit cases. Validate selected multipliers against finite-difference perturbations or a Poincare-return calculation.

Store Floquet data in authoritative periodic-orbit branch records, but browser display is not required in Episode 008. `hopf_linear_limit` records retain equilibrium eigenvalues and frequency rather than regular-orbit Floquet multipliers.

## Independent IVP validation scope

IVP integration is a selected validation method, never the production period-generation algorithm. The authoritative Figure 5 surface comes from native LOCA periodic-orbit continuation. Do not reproduce the paper's long-integration period extraction at every parameter point.

At stratified validation points, perform two complementary checks:

1. **One-period return:** start from phase-aligned `x_coll(0)`, integrate the transformed IVP for collocation period `P`, report

   ```text
   R_flow = ||S_x [phi_P(x_coll(0)) - x_coll(0)]||,
   ```

   and compare the dense IVP trajectory over that period with the collocation polynomial after phase alignment.
2. **Attractor check:** start from the paper-style perturbed equilibrium, integrate only at selected points until the established cycle period/amplitude drift criterion passes, then compare the final cycle and period against the collocation orbit.

Use a high-accuracy adaptive IVP solver independent of collocation. At the most difficult selected points, require an explicit high-order method such as DOP853 and implicit Radau to agree before treating the IVP result as reference.

Stratify selected points across the canonical `225 K` case; both sides and the interior period maximum of the `210 K` slice; low/high-temperature interiors; small-amplitude neighborhoods of both Hopf boundaries; largest/shortest interior periods; and worst accepted defect, trivial-multiplier, and interpolation-error cases.

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

### Production discretization

Two successive adapted/order-refined solutions must satisfy:

- relative period change below `1e-3`;
- phase-independent weighted orbit difference below `1e-3`;
- maximum independent relative defect

  ```text
  eta_inf = max_check_points
      ||S_x (p' - P g(p))|| / [1 + ||S_x P g(p)||]
      < 1e-4;
  ```

- trivial Floquet multiplier error `|mu_trivial - 1| < 1e-3`.

Period and orbit-convergence checks remain mandatory even when the defect passes.

### Cross-method validation

At stratified validation points, require both LOCA-to-Python and collocation-to-independent-IVP period/orbit differences below `1e-3`.

### Hopf approach

Initially require the small-amplitude `P(A)` extrapolation to agree with `2*pi/omega_H` within `1%`, tightening this threshold if observed convergence supports it.

## Schema-versioned output contract

Produce five artifact layers. The curated Figure 5 image must be regenerated from normalized artifacts rather than transient solver memory.

1. **`continuation_points.csv`:** one row per authoritative accepted periodic orbit or Hopf-limit record. Include stable point/branch IDs, parent/restart IDs, physical and normalized parameters, period, amplitude, collocation order, mesh size, residual/defect/phase/conditioning/convergence fields, Floquet multipliers, stability classification, record type, and backend provenance.
2. **`orbits/<point_id>.npz`:** full normalized mesh, endpoints, stages, `log(P)`, collocation coefficients, and phase reference for every canonical production point and validation fixture. Accompany these with a JSON manifest defining shapes, units, coordinates, and checksums.
3. **`continuation_events.jsonl`:** append-only accepted/rejected LOCA steps, NOX and linear-solve diagnostics, step-size changes, remesh decisions, transfers, and restarts.
4. **`run_metadata.json`:** method/schema versions, model parameters, coefficient-table checksums, tolerances, reproduction commands, Trilinos configuration, source commits, upstream Episode 006/007 checksums, and completion summaries.
5. **`figure5_browser_dataset.json`:** compact browser-facing display `T`, `rho`, and physical-`w` coordinates; periods and validity/source flags; Hopf curves; authoritative `T = 210 K` nonlinear and linearized slice samples; units; color range; interpolation method; and links to authoritative point IDs. Do not include full orbit vectors.

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

Exact acceptance tolerances and the stability/Floquet scope remain unresolved.

## Implementation staging and backlog boundary

The design is sufficient to begin the conservative fixed-mesh phase. Work is staged as:

- TASK-053: freeze the Episode 007 bootstrap cycle and interpolation fixture;
- TASK-054: generate shared Gauss coefficient tables;
- TASK-055: implement the Python explicit-stage midpoint layout, residual, phase equation, and sparse Jacobian;
- TASK-056: correct and study fixed-mesh midpoint orbits;
- TASK-057: implement Python fixed-mesh pseudo-arclength continuation;
- TASK-058: generalize local C++ model derivatives with Sacado;
- TASK-059: implement the serial sparse Tpetra midpoint assembler and Python parity;
- TASK-060: solve a fixed-parameter orbit through sparse Thyra/NOX with KLU2;
- TASK-061: perform genuine native LOCA fixed-mesh midpoint continuation; and
- TASK-062: resume higher-order/adaptive/Figure 5 production design using evidence from the fixed-mesh implementation and create the remaining atomic implementation tasks.

No adaptive-mesh implementation, production Floquet workflow, or full Figure 5 surface generation is required by TASK-053 through TASK-061. Minor operational constants needed by those tasks may be calibrated within their versioned tests, but changes to the mathematical contracts in this document require an explicit recorded decision.

## Open design questions

The interview still needs to resolve at least:

- exact monitor normalization, split/redistribution thresholds, coarsening policy, and restart acceptance criteria;
- whether later evidence requires a non-unit fixed weight for `log(P)` or residual-block-specific scaling beyond the frozen state scales;
- profiling criteria that would trigger Belos/Ifpack2 and the exact later bordered preconditioner;
- numerical amplitude, phase-transversality, conditioning, and Hopf-extrapolation acceptance thresholds;
- final display-`rho` density and its interpolation-error threshold;
- explicit absolute floors for relative comparisons and calibrated phase-energy/conditioning cutoffs;
- exact schema field names, JSON Schema definitions, and binary-array manifest conventions;
- task breakdown and implementation order.
