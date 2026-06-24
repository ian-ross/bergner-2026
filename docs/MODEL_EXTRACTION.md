# Model extraction specification: Bergner & Spichtinger (2026)

Status: **Phase 1 complete; implementation not started.** Do not implement equations until the user approves Phase 2.

## 1. Paper/source citation

- Hannah Bergner and Peter Spichtinger (2026). "Ice clouds as nonlinear oscillators." *Chaos: An Interdisciplinary Journal of Nonlinear Science* 36, 043115. DOI: `10.1063/5.0297531`.
- Primary local source: `sources/original/bergner-spichtinger-2026.html` plus `sources/original/bergner-spichtinger-2026_files/`.
- Visual/fallback source: `sources/original/bergner-spichtinger-2026.pdf`.

## 2. Source quality summary

Primary equations should be extracted from publisher HTML/MathJax and checked against the rendered paper/PDF. The PDF text extraction is useful but not authoritative for mathematical notation. See `docs/SOURCE_QUALITY.md` and `sources/extracted/provenance.yaml`.

Known extraction risks: broad HTML equation scan overcounts, PDF text may split fractions/exponents, and implementation-critical constants in Appendix A need final visual checking.

## 3. Implementation goal

Implement the paper-faithful 3D autonomous ODE model for a pure ice cloud parcel/box in the low-temperature upper troposphere, with variables:

- ice crystal number concentration `n`,
- ice crystal mass concentration `q`,
- saturation ratio over ice `s`.

The intended high-level output is the vector field `(dn/dt, dq/dt, ds/dt)` and optional integration helpers for reproducing equilibrium, bifurcation, and time-series examples.

## 4. Domain of validity and assumptions

Stated/spot-checked assumptions:

- Low-temperature ice-cloud regime, approximately `190 K <= T <= 240 K`, `200 hPa <= p <= 300 hPa`.
- Homogeneous nucleation of solution droplets; heterogeneous nucleation omitted.
- Supersaturated regime emphasized (`s > 1`); evaporation number sink is optional/ad hoc for `s <= 1`.
- Two-moment bulk model with lognormal ice-particle mass distribution and fixed `r0 = 3`.
- Spherical small ice particles; ventilation and kinetic corrections neglected.
- Sedimentation represented by a single box/layer with vertical extension `Δz = 100 m` and parameter `F = 1 - f_sed`, `0 < F <= 1`.
- Collision/aggregation neglected.

Implementation-inferred assumptions to confirm:

- Numeric core will use SI units: pressure Pa, temperature K, velocity m/s, time s, `q` kg/kg dry air, `n` kg_dry_air^-1 unless otherwise documented.
- Use dry-air density `ρ = p/(R_d T)` for converting aerosol number concentration per volume to `n_a` per dry-air mass.

## 5. Unit strategy

- `core.py`: plain numeric SI values with units documented in each docstring/comment.
- `units.py`: Pint wrappers validating pressure, temperature, velocity, concentrations, and time.
- Avoid Pint inside the vector field so equations remain visually close to the paper.
- Public examples/notebooks may use Pint for clarity.

## 6. Symbol table

| Paper | Python | Units/dimensions | Meaning | Source | Confidence |
|---|---|---:|---|---|---|
| `n` | `n` | kg_dry_air^-1 | ice crystal number concentration | Sec. II.D | high |
| `q` | `q` | kg kg_dry_air^-1 | ice crystal mass concentration | Sec. II.D | high |
| `s`, `S_i` | `s` | 1 | saturation ratio over ice | Sec. III.B | high |
| `T` | `T` | K | temperature, fixed environmental parameter | Table I | high |
| `p` | `p` | Pa | pressure, fixed environmental parameter | Table I | high; table displayed in hPa |
| `w` | `w` | m s^-1 | vertical velocity | Table I | high |
| `F` | `F` | 1 | sedimentation parameter `1 - f_sed` | Eq. (68)--(70) | high |
| `D` | `D` | m^-1? | cooling coefficient in `Cool = D w s` | Eq. (15)/(30)/(38) | medium; dimensional check required |
| `p1e(T)` | `p1e` | 1 | nucleation steepness, `log(10) p1(T)` | App. A Eq. (A18) | high |
| `p2(T)` | `p2` | 1 | critical saturation fit | Eq. (42), App. A Eq. (A19) | high |
| `A_n,A_q,A_s` | `A_n,A_q,A_s` | variable rates | nucleation coefficients | Eq. (43)--(45) | medium |
| `B_q,B_s` | `B_q,B_s` | variable rates | growth/deposition coefficients | Eq. (51)--(53) | medium |
| `C_n,C_q` | `C_n,C_q` | variable rates | sedimentation coefficients | Eq. (66) | medium |
| `H` | `H` | 1 | Heaviside function | Eq. (12)/(54) | high |
| `ψ_i` | `p_si` | Pa | saturation vapor pressure over hexagonal ice | App. A Eq. (A30) | high |
| `ρ` | `ρ` | kg m^-3 | air density from ideal gas law | App. A | medium |

## 7. Constants and parameters

Initial inventory, to verify visually before implementation:

- Table I: `p` 200--300 hPa; `T` 190--240 K; `w` 0.0005--2 m/s; `F` 0.01--1.
- `m_nuc = 1e-16 kg`; `N_a ≈ 300 cm^-3 = 3e8 m^-3`; reference alternative `N_a = 10000 cm^-3`.
- `r_sol = 75e-9 m`, `σ_r = 1.5`, `V_sol = 4/3 π r_sol^3 exp(9/2 log(σ_r)^2)`.
- `J0 = 1e16 m^-3 s^-1`.
- `p1(T)=a0+a1 T`, `p1e=log(10)p1`, `a0=-50.4085`, `a1=0.9368 K^-1`.
- `p2(T)=as2 T^2 + as1 T + as0`, `as2=-1.36989e-5 K^-2`, `as1=0.00228 K^-1`, `as0=1.67469`.
- `R_d=287.058 J kg^-1 K^-1`, `R_v=461.553 J kg^-1 K^-1`, `g=9.81 m/s^2`.
- Latent heat `L(T)=L_mol(T)/M_mol,v` with coefficients in App. A Eq. (A24)--(A29).
- `ψ_i(T)=p_unit exp(b0+b1/T+b2 log(T/T_unit)+b3 T)` with App. A coefficients.
- `D_v=D_v0 (T/T0)^2 (p0/p)`, `D_v0=2.1422e-5 m^2/s`, `T0=273.15 K`, `p0=101325 Pa`.
- `K_T(T)` heat conduction formula App. A Eq. (A34)--(A36); PDF text requires visual confirmation of denominator/exponent formatting.
- `ρ_b=810 kg/m^3`, `r0=3`, `a_s=6e5 m s^-1 kg^-2/3`, `Δz=100 m`.

## 8. Equation inventory

| Ref | Expression/meaning | Proposed function | Inputs -> outputs | Confidence |
|---|---|---|---|---|
| Eq. (4)--(6) | full ODE system for `dn/dt,dq/dt,ds/dt` | `rhs(t, y, params)` / `vector_field(n,q,s,params)` | state + params -> rates | medium until curated |
| Eq. (7)--(9), (43)--(45) | nucleation terms `Nuc_n,Nuc_q,Nuc_s` | `Nuc_n`, `Nuc_q`, `Nuc_s` | `s,T,p,...` -> rates | medium |
| Eq. (12)/(54) | ad hoc evaporation number sink using Heaviside | `Evap_n` | `n,q,s,B_q` -> rate | medium; only needed for `s<=1` |
| Eq. (51)--(53) | deposition/growth mass source and saturation sink | `Dep_q`, `Dep_s` | `n,q,s,T,p` -> rates | medium |
| Eq. (13)--(14), (69)--(70) | sedimentation sinks | `Sed_n`, `Sed_q` | `n,q,F,T,p,Δz` -> rates | high |
| Eq. (15)/(30)/(38) | cooling source `Cool = D w s` | `Cool`, `D` | `T,w,s` -> rate | medium; dimensions to check |
| Eq. (16) | optional singularity regularization | optional flag/parameter | `n,n_small` | medium; not default unless requested |
| Eq. (55)--(57) | fall-speed correction `c(p,T)` | `c_fall` | `p,T` -> 1 | high |
| Eq. (A17)--(A22) | nucleation rate polynomials | `J`, `p1e`, `p2` | `s,T` -> rate | high |
| Eq. (A23)--(A40) | thermodynamic/material functions | `L`, `p_si`, `D_v`, `K_T`, `G_v`, `B_q` | `T,p` -> constants | medium |
| Eq. (77)--(85) | equilibrium approximations | later `equilibrium_approx` | params -> `(n,q,s)` | medium; Phase 2 optional |
| Eq. (95), (100)--(103) | Jacobian/eigenvalue analysis | later `jacobian` | state+params -> matrix | medium; Phase 2 optional |
| Eq. (108)--(109), Table II | Hopf bifurcation fits | `w_a_fit`, `w_b_fit` | `T` -> `w` | high |

## 9. Evaluation order / algorithm

For each state `(n,q,s)` and fixed environment `(p,T,w,F)`:

1. Compute thermodynamic functions: `ρ`, `ψ_i(T)`, `L(T)`, `D_v(T,p)`, `K_T(T)`, `G_v(T,p)`, `D(T)`.
2. Compute nucleation fits `p1e(T)`, `p2(T)`, aerosol-derived `A_n`, `A_q`, `A_s`.
3. Compute growth constants `B_q`, `B_s`.
4. Compute sedimentation constants `C_n`, `C_q`.
5. Evaluate process terms in paper order: nucleation, deposition/growth, optional evaporation, sedimentation, cooling.
6. Assemble Eq. (4)--(6).

## 10. Numerical methods

- RHS is an ODE vector field with singular terms `n^-2/3` and `q^-2/3`; integration should avoid zero initial `n,q` unless optional regularization Eq. (16) is explicitly enabled.
- Use `scipy.integrate.solve_ivp`; solver choice/tolerances for paper figures are not yet curated.
- Equilibrium and bifurcation analyses may require root finding/eigenvalues (`scipy.optimize`, `numpy.linalg`). These are not required for the first RHS implementation unless Phase 2 scope includes reproducing Figs. 3--8.

## 11. Ambiguities / required user decisions

1. Confirm Phase 2 scope: implement only the core ODE RHS first, or also equilibrium, Jacobian, bifurcation fits, and figure-reproduction workflows?
2. Confirm canonical interpretation of `n`: paper alternates between per dry-air mass and measured per-volume values; implementation should use per dry-air mass internally and provide conversion helpers.
3. Confirm whether to implement the `s<=1` evaporation number sink and/or regularization Eq. (16) in the first pass.
4. `K_T(T)` formula formatting in extracted PDF needs visual verification against HTML/PDF before coding.
5. Figure reproduction is blocked without downloading/requesting B2SHARE data and curating solver settings/initial conditions.

No item appears completely blocked for implementing the main RHS, but several constants are **medium confidence** pending final visual check.

## 12. Proposed file layout

- `src/bergner_spichtinger_2026/constants.py`: constants and parameter dataclasses, with source references.
- `src/bergner_spichtinger_2026/core.py`: paper-faithful numeric formulas and RHS.
- `src/bergner_spichtinger_2026/units.py`: Pint wrappers and unit conversions.
- `tests/test_constants.py`, `tests/test_core_smoke.py`, `tests/test_units.py`.
- `episodes/001-figure4-time-series/notebooks/00_source_inspection.ipynb`, `episodes/001-figure4-time-series/notebooks/01_reproduce_key_figures.ipynb`.

## 13. Test plan

- Unit/dimensional tests for Pint wrappers: Pa/hPa, K, m/s, kg/kg, per-volume/per-mass number concentrations.
- Equation smoke tests for helper formulas with hand-checkable positivity and simple values.
- Regression tests only from paper tables/figures or downloaded data; none invented.
- Physical sanity tests justified by the paper: positive rates/constants, `Nuc_n` increasing with `s`, sedimentation sinks non-positive for positive state, growth sign follows `s-1`.

## 14. Verification inventory

| Target | Required data/parameters | Availability | Artifact | Status |
|---|---|---|---|---|
| Table I ranges | paper | available | tests/README checks | not started |
| Fig. 3 bifurcation diagram | numerical continuation/grid over `T,w`, p=300 hPa, F=1 | parameters partly available; method details incomplete | notebook plot | blocked/curation needed |
| Fig. 4 time series at T=225 K, p=300 hPa, F=1, w=0.01/0.1/1 | initial conditions/solver settings need curation | partly available | notebook plot | blocked/curation needed |
| Appendix D full example simulations/Figs. 11--13 | same as Fig. 4 plus all variables | partly available | notebook plot | blocked/curation needed |
| Measurement comparison Fig. 9 | B2SHARE DOI data | not downloaded | notebook plot | blocked |
| Hopf fit Table II | paper table | available | unit test for fit function | not started |

## 15. Example plan

- Minimal non-validation run: evaluate RHS at a positive synthetic state within paper parameter ranges, clearly labeled as a smoke example.
- Paper scenario: after curating initial conditions, reproduce Fig. 4 saturation-ratio time series for `T=225 K`, `p=300 hPa`, `F=1`, and `w in {0.01, 0.1, 1} m/s`.
- Verification notebook should explicitly mark missing data and non-validation synthetic examples.
