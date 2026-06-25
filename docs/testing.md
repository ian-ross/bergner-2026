# Testing strategy and property-based testing guidance

This repository currently relies on deterministic pytest cases for the Python model core, residual adapters, continuation primitives, unit-boundary checks, and figure-reproduction scripts.  As the project adds a shared AUTO Fortran model core and later a LOCA implementation, deterministic smoke tests should remain the first diagnostic layer, but property-based testing should be added for backend equivalence and domain-invariant checks.

Recommendation: adopt [Hypothesis](https://hypothesis.readthedocs.io/) for Python-driven property tests.  Use it conservatively: generate physically valid inputs, cap example counts, keep tolerances explicit, and pair each property with a small fixed smoke-case test.  Hypothesis is most valuable here as an intercomparison tool for Python, AUTO Fortran, and future LOCA adapters, not as a replacement for curated figure-reproduction artifacts.

## Dependency and maintenance recommendation

Add `hypothesis` as a development/test dependency when implementation starts on backend-equivalence tests such as TASK-010.  A typical configuration should use:

- `@settings(max_examples=50, deadline=None)` for ordinary model/helper properties;
- `@settings(max_examples=20, deadline=None)` for compiler- or subprocess-backed Python-vs-Fortran tests;
- deterministic fixed examples for Figure 1/Figure 4 environments before any generated examples;
- pytest markers only for tests that need optional external tools such as `gfortran`, `/usr/local/bin/auto`, or later LOCA binaries.

Expected maintenance cost is moderate.  Hypothesis failures are highly useful because they shrink to small counterexamples, but the generated domains must be maintained alongside the physical model assumptions.  Avoid broad unconstrained floating-point generation: it will mostly discover overflow, invalid clouds, and solver-conditioning artifacts rather than scientific regressions.  Store failing examples in the normal Hypothesis example database only as a local debugging aid; do not commit cache artifacts.

## Shared generated domains

Use these domains as the initial common strategy set for Python-only properties, Python-vs-AUTO tests, and later Python-vs-LOCA comparisons.  All values are SI unless noted.

### Environment parameters

Conservative default ranges:

| Parameter | Suggested generated range | Constraints and rationale |
| --- | ---: | --- |
| `T` | 190--235 K | Covers Figure 1 temperatures and cold cirrus use cases while staying near the homogeneous-freezing fit domain used by the paper. |
| `p` | 15,000--60,000 Pa | Upper-tropospheric pressures around the reproduced 300 hPa case; avoids very low-pressure coefficient extremes. |
| `w` | 0.005--2.0 m s^-1 | Matches Figure 1 continuation range; generate in `log(w)` for branch/residual tests. |
| `F` | 0.05--1.0 | Keeps sedimentation active and positive; includes the paper's `F = 1` figure cases while avoiding singular `F <= 0` approximations. |
| `N_a` | 3.0e8--1.0e10 m^-3 | Spans Appendix A2 typical aerosol loading through the inferred Figure 1 high-aerosol value; generate logarithmically. |
| `Δz` | 50--500 m | Positive layer depths near the default 100 m; avoid unrealistically thin boxes that amplify sedimentation. |
| `include_evaporation` | usually `False`; explicit paired tests for `True` | Most reproduced equilibrium work uses the unregularized/equilibrium supersaturated regime. |

Generation advice:

- Prefer log-uniform sampling for `w`, `N_a`, and positive state magnitudes.
- Include exact fixed examples for `(p=30000, T in {190, 210, 230}, F=1, w in {0.005, 0.1, 2.0})` and the Figure 4 environment `(p=30000, T=225, w in {0.01, 0.1, 1.0}, F=1)`.
- Reject or avoid non-finite coefficient evaluations.  A generated input that overflows `exp(p1e * (s - p2))` is outside the useful property domain rather than evidence of a backend mismatch.

### State variables

For direct process-term and vector-field properties, generate positive cloud states:

| State | Suggested generated range | Constraints and rationale |
| --- | ---: | --- |
| `n` | 1.0e1--1.0e9 kg_dry_air^-1 | Positive only; log-uniform; broad enough to cover dilute through high-aerosol states without extreme powers. |
| `q` | 1.0e-12--1.0e-3 kg kg_dry_air^-1 | Positive only; log-uniform; avoids the unregularized `q = 0` singularity. |
| `s` | 0.8--1.8 for process terms; 1.000001--1.8 for deposition/approximation checks | Include subsaturated states only when testing evaporation switches; equilibrium and Eq. 92--94 properties require supersaturation. |

Additional constraints:

- The unregularized RHS requires `n > 0` and `q > 0`; generate log coordinates for residual tests as `(log(n), log(q), s)`.
- For Eq. 92--94 approximation tests, require `w > 0`, `F > 0`, and `s > 1` when `s` is supplied explicitly.
- Use `assume(np.isfinite(...))` sparingly after computing coefficients or terms; prefer bounded strategies that make finite values likely.

## Candidate properties

### Thermodynamic and coefficient helpers

Candidate properties for `constants.py` and `core.py` helpers:

- `ρ_air(p, T)` is positive over valid `p, T` and scales linearly with `p` at fixed `T`.
- `p_si(T)`, `D_v(T, p)`, `K_T(T)`, `G_v(T, p)`, `D(T)`, `V_sol()`, `c_radius()`, and `c_fall(p, T)` are finite and positive over the generated environment domain.
- `D_v(T, p)` decreases as `p` increases at fixed `T` and increases with `T` over the tested range at fixed `p`.
- `coefficients(env)` returns finite positive values for `ρ`, `D`, `p_si`, `p1e`, `A_n`, `A_q`, `A_s`, `B_q`, `B_s`, `C_n`, and `C_q`; `p2` remains in a physically plausible supersaturation range for generated `T`.
- Coefficient relationships from the implementation hold exactly within roundoff: `A_q == m_nuc * A_n`, `A_s == A_q * p / (ε * p_si)`, `B_s == B_q * p / (ε * p_si)`, and the sedimentation coefficients scale with `F` only in process terms, not in `coefficients(env)`.

For backend equivalence, compare the full coefficient vector from Python and Fortran/LOCA at the same generated environment before comparing process terms.  Recommended tolerance: `rtol=1e-11, atol=1e-300` for pure coefficient translations in double precision, relaxed only for quantities printed through text drivers with limited precision.

### Process terms and vector field

Candidate properties for `process_terms()` and `vector_field()`:

- Invalid unregularized cloud states (`n <= 0` or `q <= 0`) raise `ValueError` in Python and are rejected by backend test drivers before numerical comparison.
- For `s > 1`, deposition increases ice mass and reduces saturation: `Dep_q > 0` and `Dep_s < 0`.
- For `s < 1` with `include_evaporation=False`, `Evap_n == 0`; with `include_evaporation=True`, the evaporation switch activates only at subsaturation.
- Sedimentation terms are sinks for valid positive states: `Sed_n < 0` and `Sed_q < 0` when `F > 0`.
- Cooling source `Cool == D(T) * w * s` is positive for generated `D`, `w`, and positive `s`.
- `vector_field(n, q, s, env)` equals the component-wise sum of the documented process terms: `dn = Nuc_n + Evap_n + Sed_n`, `dq = Nuc_q + Dep_q + Sed_q`, `ds = Cool + Nuc_s + Dep_s`.
- For matched inputs, Python and AUTO Fortran process terms and vector fields agree within `rtol=1e-10` and an absolute floor scaled by the magnitude of each component.  Use `atol=max(1e-300, 1e-12 * representative_scale)` rather than a single large absolute tolerance.

### Residual adapters

Candidate properties for `residuals.py`:

- `physical_state_from_log_coordinates(log_coordinates_from_physical_state(state))` round-trips generated valid states within floating-point tolerance.
- `log_coordinates_from_physical_state()` rejects non-positive `n` or `q` and rejects incorrectly shaped inputs.
- `equilibrium_residual(log_state, log_w, env)` equals `[dn/dt / n, dq/dt / q, ds/dt]` evaluated by `vector_field()` with `env.w = exp(log_w)`.
- `make_equilibrium_residual(env, coeff=coeff)` is observationally equivalent to calling `equilibrium_residual(..., coeff=coeff)` directly.
- Row scaling is elementwise and shape-checked.
- Coefficients reused along a branch must be independent of `w`; generated tests can compare residuals with a precomputed `coefficients(env)` against residuals that recompute coefficients after replacing `w`.

For Python-vs-Fortran tests, the log-coordinate residual is a high-value end-to-end property because it exercises environment replacement, coefficient reuse, vector-field evaluation, and normalization.  Compare residual vectors at generated `(log(n), log(q), s, log(w))` after first verifying the underlying coefficient and vector-field comparisons for easier diagnosis.

### Continuation utilities

Candidate properties for `continuation.py` should use simple synthetic residuals in addition to the expensive ice-cloud equilibrium residual:

- `continue_branch()` rejects empty or non-one-dimensional `controls` and non-one-dimensional `initial_state`.
- For a synthetic residual such as `state - [control, control**2]`, the corrected states match the analytic branch for generated monotone or non-monotone control arrays.
- `ContinuationResult.controls` preserves the requested controls for converged fixed-control continuation.
- `ContinuationResult.states` has shape `(len(points), state_dim)` and `converged` is true iff all points converged.
- With `stop_on_failure=True`, a deliberately unsolvable residual stops at the first failed point; with `False`, the result records failures without truncating requested controls.
- For the Bergner residual, short generated control paths near a fixed equilibrium should produce finite states with positive `n` and `q`, but keep example counts low because nonlinear solves are slower and failures can indicate conditioning rather than code defects.

### Eq. 92--94 approximation helpers

Candidate properties for `approximations.py`:

- `sigma_equilibrium(env)` is finite for generated valid environments and does not depend on `w`.
- `approximate_equilibrium_s(env)` raises for `w <= 0` or `F <= 0` and otherwise equals `sigma_equilibrium(env) + (L_MIDPOINT + log(w) + 0.75 * log(F)) / p1e(T)`.
- At fixed `T`, `p`, `N_a`, and `F`, `approximate_equilibrium_s` is monotone increasing in `log(w)` because `p1e(T) > 0` over the generated temperature range.
- At fixed `T`, `p`, `N_a`, and `w`, `approximate_equilibrium_s` is monotone increasing in `log(F)` over `F > 0`.
- `approximate_equilibrium(env)` returns positive `n`, positive `q`, and `s > 1` for generated environments where Eq. 92 predicts supersaturation; if Eq. 92 predicts `s <= 1`, the approximation is outside its useful domain and tests should reject that generated example.
- The returned `s` equals an explicitly supplied `s0` and the returned `n, q` follow the Eq. 93--94 scaling: at fixed `s`, `n` scales as `w * F**0.25` and `q` scales as `w * F**-0.5`.

Use moderate tolerances for Eq. 92--94 comparisons to numerical equilibria because these are analytic approximations, not exact residual roots.  For formula identity/scaling properties, use strict double-precision tolerances (`rtol=1e-12`).  For approximation-vs-continuation characterization, record relative errors rather than failing the test unless a documented envelope has been established for a specific figure-reproduction range.

## Python-vs-AUTO Fortran equivalence guidance

TASK-010 should use this document as its input contract.  The shared AUTO Fortran model core should expose a small driver that evaluates quantities without running continuation.  The driver output should be machine-readable, preferably JSON or stable whitespace-delimited records with enough significant digits for double precision.

Recommended TASK-010 structure:

1. Add fixed smoke cases for Figure 1 and Figure 4 environments.  Evaluate coefficients, process terms, vector fields, and log-coordinate residuals in Python and Fortran.
2. Build or locate the Fortran evaluator from pytest using repository-root relative paths.  If `gfortran` or required AUTO tooling is absent, skip only the cross-language tests with an explicit reason; keep pure Python property tests always runnable under `uv run pytest`.
3. Add Hypothesis-generated environments and states from the domains above.  Use `max_examples=20` for subprocess-backed comparisons and print the shrunk counterexample inputs on failure.
4. Compare in layers: coefficients first, then process terms, then vector field, then residual adapter.  This makes failures local rather than a single opaque residual mismatch.
5. Use relative tolerances near `1e-10` for values passed through compiled double precision and text serialization.  Use component-wise absolute floors for very small rates.  If the driver prints fewer than 17 significant decimal digits, relax the tolerance and document the serialization limit in the test.
6. Keep generated tests deterministic in CI by fixing Hypothesis settings in the test module or pytest configuration.  Do not seed Hypothesis globally unless a specific flaky case is being diagnosed.

The Fortran comparison should explicitly check that Python and Fortran agree on these semantic choices:

- `n` is per dry-air mass, while `N_a` is per volume and is converted with `N_a / ρ` in `A_n`.
- Eq. (16) regularization is not enabled; `n` and `q` must remain strictly positive.
- `K_T(T)` uses the user-confirmed Eq. (A34) transcription already implemented in Python.
- Residual coordinates are `(log(n), log(q), s)` and control is `log(w)`.
- `coefficients(env)` do not depend on `w`; the residual adapter replaces only `w` when evaluating the continuation control.

## Later Python-vs-LOCA comparison guidance

When a LOCA implementation is added, reuse the same generated-domain helpers and fixed smoke cases rather than inventing a separate property suite.  LOCA comparisons should have two layers:

- **Model-core equivalence:** compare coefficients, process terms, vector fields, and residuals against Python at generated valid states, just as for AUTO Fortran.
- **Continuation-output equivalence:** compare normalized branch outputs against the backend-neutral branch schema once AUTO/LOCA/Python outputs are available.  Branch-level comparisons should use physical coordinates and metadata (`T`, `p`, `F`, `w`, backend, convergence status) rather than raw solver-internal state.

For branch comparisons, generated property tests should focus on schema invariants and small local branch segments; curated deterministic tests should carry the scientific comparison against Figure 1 and paper benchmarks.  Suggested branch-level properties include positive `n` and `q`, finite `s`, monotone requested `w` grids when applicable, residual norms below the backend-specific tolerance, and agreement with Python continuation within a documented relative error envelope over the Figure 1 range.

## Follow-up implementation tasks

The immediate implementation follow-up is TASK-010, which should add Python-driven Fortran model equivalence tests using the domains, properties, and tolerances above after TASK-009 provides the shared AUTO Fortran evaluator.  Later LOCA backend work should apply the same strategy: keep a Python oracle, reuse generated input domains, compare model-core quantities before continuation branches, and make any backend/tool availability opt-in through explicit pytest skips or markers.
