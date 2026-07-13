# Episode 5 planning decisions

Episode 5 targets the Figure 2 eigenvalue reproduction from Bergner & Spichtinger (2026). It builds on the Figure 1 Python, AUTO, and Trilinos-side C++ branch work but changes the primary observable from equilibrium state variables to linearized physical-ODE eigenvalues along a one-temperature vertical-velocity sweep. The current C++ backend lives under `loca/` for historical reasons, but it does not yet use full NOX/LOCA continuation APIs.

## Reproduction target

The agreed Figure 2 parameter set is:

- pressure `p = 300 hPa`
- temperature `T = 230 K`
- sedimentation factor `F = 1`
- aerosol number concentration `N_a = 1.0e10 m^-3` (`10000 cm^-3`)
- paper vertical-velocity range `w = 0.0005--2.0 m s^-1`

The `N_a` value is an explicit Episode 5 assumption inherited from the Figure 1 debugging trail: the paper's Figure 1 caption does not state `N_a`, but the reproduced saturation-ratio panel is consistent with the Appendix A2 high-aerosol reference value rather than a typical lower aerosol concentration.

Continuation and plotting code may use `log_w = log(w_m_s)` for numerical conditioning, but curated artifacts must include physical `w_m_s` and enough metadata to reconstruct the paper range.

## Eigenvalue semantics

Figure 2 should be interpreted as physical linear stability information for the model ODEs evaluated at equilibrium states. The target eigenvalues are therefore eigenvalues of the physical ODE Jacobian with respect to the physical state variables.

Do not compare against, or label as Figure 2 reproduction data, eigenvalues of:

- transformed residuals in coordinates such as `log_n` or `log_q`;
- continuation-corrector systems that include the continuation parameter;
- row-scaled or solver-preconditioned residual systems;
- AUTO, NOX/LOCA, or other solver-internal matrices unless their relationship to the physical ODE Jacobian is explicitly derived and normalized back to physical units.

Backend outputs may include solver-internal eigenvalue diagnostics for debugging, but cross-backend Figure 2 comparison artifacts should use physical-Jacobian eigenvalues only.

## Backend independence requirements

Python, AUTO, and the Trilinos-side C++ backend should produce independent equilibrium/eigenvalue outputs for comparison.

- Python is the semantic reference implementation and should compute equilibria and physical analytic or finite-difference Jacobian eigenvalues directly from package-level model utilities.
- AUTO should independently generate or verify the equilibrium branch over the Figure 2 `w` range. If native AUTO stability/eigenvalue output is practical and can be normalized to physical ODE Jacobian eigenvalues, prefer that path. If not, AUTO may fall back to computing physical analytic eigenvalues in Python at AUTO-generated equilibria, after documenting investigated native options and the fallback rationale in run metadata.
- The current Trilinos-side C++ backend should independently generate the equilibrium branch and compute the physical Jacobian/eigenvalues backend-side, not by post-processing C++ equilibria with Python eigenvalue code. It may use a simple hand-rolled continuation/Newton path while the problem remains small and the goal is to validate C++ equations and backend-side eigenvalue semantics.

The comparison should distinguish branch-generation agreement from eigenvalue-calculation agreement. For example, an AUTO fallback that uses Python analytic eigenvalues at AUTO equilibria is still useful for testing AUTO branch generation, but it is not an independent AUTO-native eigenvalue calculation.

## Trilinos-side C++ physical eigenvalue requirement

The current C++/Trilinos backend must compute the physical Jacobian/eigenvalues in C++ when Episode 5 C++ outputs are produced. This is intentionally a lightweight Trilinos-side backend using Sacado and Teuchos/LAPACK rather than full NOX/LOCA. A later task will wrap the same simple, validated problem in NOX/LOCA to learn the framework interface before scaling to larger problems.

Required design constraints:

- Use Sacado automatic differentiation to differentiate the physical ODE right-hand side or an explicitly documented physical residual with respect to physical state variables.
- Convert any transformed internal continuation state back to physical variables before assembling the physical Jacobian.
- Use Teuchos/LAPACK dense eigensolver facilities where available. The Figure 2 state dimension is small, so a dense serial path is appropriate.
- Record whether Sacado, Teuchos, and LAPACK were available, the exact matrix being diagonalized, and the state-coordinate convention in metadata.
- Keep solver-internal transformed Jacobians separate from curated physical eigenvalue outputs.

## AUTO eigenvalue policy

AUTO may expose native stability information depending on the problem formulation and run files. Episode 5 should investigate native AUTO options before settling on a fallback.

Acceptable fallback policy:

1. AUTO generates the equilibrium branch independently over `w = 0.0005--2.0 m s^-1`.
2. The script normalizes AUTO equilibria into physical `n`, `q`, `s`, `w_m_s`, and environment fields.
3. Python package-level physical-Jacobian eigenvalue code evaluates eigenvalues at those AUTO equilibrium points.
4. Run metadata and planning notes state clearly that AUTO contributed independent equilibria but not independent native eigenvalues.

This fallback is acceptable only if native AUTO options are documented as unavailable, unsuitable, or not yet implemented for the physical-Jacobian target.

## Provisional output contract

Curated per-backend eigenvalue rows should include, at minimum:

| Field | Meaning |
| --- | --- |
| `backend` | `python`, `auto`, or `loca` for historical output compatibility; `loca` currently means the Trilinos-side C++ backend, not full NOX/LOCA. |
| `branch_id` | Stable branch name, e.g. `figure2_T230K`. |
| `T_K` | Temperature in kelvin. |
| `p_Pa` | Pressure in pascals. |
| `F` | Sedimentation factor. |
| `N_a_m3` | Aerosol number concentration. |
| `log_w` | Natural log of physical vertical velocity. |
| `w_m_s` | Physical vertical velocity. |
| `n` | Physical ice crystal number concentration. |
| `q` | Physical ice crystal mass mixing ratio. |
| `s` | Saturation ratio. |
| `eigen_index` | Stable eigenvalue ordering within a branch point. |
| `eigenvalue_real` | Real part of the physical-Jacobian eigenvalue. |
| `eigenvalue_imag` | Imaginary part of the physical-Jacobian eigenvalue. |
| `jacobian_coordinate_system` | Expected value: `physical_ode_state`. |
| `eigenvalue_source` | e.g. `python_analytic`, `auto_native`, `python_at_auto_equilibrium`, or `loca_sacado_lapack` where `loca_sacado_lapack` denotes the current Trilinos-side C++ path. |
| `residual_norm` | Backend-normalized equilibrium residual norm where available. |
| `converged` | Whether the equilibrium solve/continuation point converged. |
| `source_file` | Relative path to the raw or normalized source artifact. |

Metadata should record command provenance, package/backend versions, solver tolerances, eigenvalue sorting conventions, matrix definitions, and known caveats.

## AUTO Figure 2 implementation decision

TASK-022 implemented the AUTO path as an independent AUTO-07p equilibrium continuation followed by labeled Python analytic eigenvalue post-processing of the AUTO equilibria.

Native AUTO stability/eigenvalue output was investigated at the run-file and artifact level. The Episode 5 AUTO problem uses `IPS=1` equilibrium continuation in log-state coordinates with `PAR(1)=log_w`; AUTO produces the expected `b.*`, `s.*`, and `d.*` branch/stability artifacts and labels, but this setup does not directly emit normalized columns for the physical ODE Jacobian spectrum `d(dn/dt,dq/dt,ds/dt)/d(n,q,s)`. AUTO bifurcation/stability diagnostics are tied to the continuation problem formulation and solver coordinates/scaling, whereas Figure 2 comparison requires eigenvalues in physical `(n, q, s)` units.

The production path therefore uses AUTO only to generate the equilibrium branch, then evaluates the already verified shared Python physical-Jacobian eigenvalue routine at each parsed AUTO point. The curated AUTO eigenvalue metadata labels this as `python_analytic_postprocessed_from_auto_equilibria`, not AUTO-native eigenvalues. This preserves backend independence for branch generation while avoiding an unverified duplicate Fortran/LAPACK physical eigensolver inside the AUTO template.

Current curated outputs live under `episodes/005-figure2-eigenvalues/outputs/figure2_auto_eigenvalues/`. The generated branch covers `w = 0.0005--2.0 m s^-1` with 411 normalized points; AUTO raw continuation overran the upper endpoint before stopping, so normalized CSVs are clipped to the requested Figure 2 interval. Post-processed Hopf estimates from the AUTO equilibria are approximately `w = 0.04853` and `w = 0.76864 m s^-1`, within the documented Figure 2 landmark tolerance.

## Known open items

- Confirm the exact Figure 2 panel encoding and whether the paper plots all eigenvalue real parts, selected branches, or derived timescales.
- Decide whether to digitize Figure 2 for paper-level comparison or first focus on backend-to-backend reproduction.
- Define eigenvalue ordering and branch matching conventions across real/complex pairs.
- Decide whether package-level physical-Jacobian utilities should live in `src/bergner_spichtinger_2026/` before Episode 5 scripts are implemented.
- Add a full NOX/LOCA backend after more tasks have validated the simple Python/AUTO/Trilinos-side C++ comparison workflow, then compare the framework implementation against the already-understood small problem.

## Scope boundaries

Keep Episode 5 scripts, notebooks, generated files, and curated outputs under `episodes/005-figure2-eigenvalues/` unless a later task explicitly promotes a component as shared infrastructure. Shared backend directories such as `auto/` and `loca/` should contain reusable model/backend assets only, not one-off Figure 2 run artifacts. The `loca/` name is retained for continuity, but documentation should distinguish the present Trilinos-side C++ backend from the deferred full NOX/LOCA backend.
