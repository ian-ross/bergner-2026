# Episode 5 planning decisions

Episode 5 targets the Figure 2 eigenvalue reproduction from Bergner & Spichtinger (2026). It builds on the Figure 1 Python, AUTO, and LOCA branch work but changes the primary observable from equilibrium state variables to linearized physical-ODE eigenvalues along a one-temperature vertical-velocity sweep.

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
- AUTO/LOCA internal matrices unless their relationship to the physical ODE Jacobian is explicitly derived and normalized back to physical units.

Backend outputs may include solver-internal eigenvalue diagnostics for debugging, but cross-backend Figure 2 comparison artifacts should use physical-Jacobian eigenvalues only.

## Backend independence requirements

Python, AUTO, and LOCA should produce independent equilibrium/eigenvalue outputs for comparison.

- Python is the semantic reference implementation and should compute equilibria and physical analytic or finite-difference Jacobian eigenvalues directly from package-level model utilities.
- AUTO should independently generate or verify the equilibrium branch over the Figure 2 `w` range. If native AUTO stability/eigenvalue output is practical and can be normalized to physical ODE Jacobian eigenvalues, prefer that path. If not, AUTO may fall back to computing physical analytic eigenvalues in Python at AUTO-generated equilibria, after documenting investigated native options and the fallback rationale in run metadata.
- LOCA should independently generate the equilibrium branch and compute the physical Jacobian/eigenvalues backend-side, not by post-processing LOCA equilibria with Python eigenvalue code.

The comparison should distinguish branch-generation agreement from eigenvalue-calculation agreement. For example, an AUTO fallback that uses Python analytic eigenvalues at AUTO equilibria is still useful for testing AUTO branch generation, but it is not an independent AUTO-native eigenvalue calculation.

## LOCA physical eigenvalue requirement

LOCA must compute the physical Jacobian/eigenvalues in the C++/Trilinos backend when Episode 5 LOCA outputs are produced.

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
| `backend` | `python`, `auto`, or `loca`. |
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
| `eigenvalue_source` | e.g. `python_analytic`, `auto_native`, `python_at_auto_equilibrium`, or `loca_sacado_lapack`. |
| `residual_norm` | Backend-normalized equilibrium residual norm where available. |
| `converged` | Whether the equilibrium solve/continuation point converged. |
| `source_file` | Relative path to the raw or normalized source artifact. |

Metadata should record command provenance, package/backend versions, solver tolerances, eigenvalue sorting conventions, matrix definitions, and known caveats.

## Known open items

- Confirm the exact Figure 2 panel encoding and whether the paper plots all eigenvalue real parts, selected branches, or derived timescales.
- Decide whether to digitize Figure 2 for paper-level comparison or first focus on backend-to-backend reproduction.
- Define eigenvalue ordering and branch matching conventions across real/complex pairs.
- Decide whether package-level physical-Jacobian utilities should live in `src/bergner_spichtinger_2026/` before Episode 5 scripts are implemented.
- Determine how much of the LOCA physical-eigenvalue code belongs in shared top-level `loca/` versus episode-local drivers.

## Scope boundaries

Keep Episode 5 scripts, notebooks, generated files, and curated outputs under `episodes/005-figure2-eigenvalues/` unless a later task explicitly promotes a component as shared infrastructure. Shared backend directories such as `auto/` and `loca/` should contain reusable model/backend assets only, not one-off Figure 2 run artifacts.
