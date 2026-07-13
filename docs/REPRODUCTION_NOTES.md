# Reproduction notes and hidden assumptions

This file records paper-reproduction assumptions that are not obvious from figure captions or equations, especially details that can save debugging time later. Treat entries here as evidence-backed notes, not as replacements for source provenance in episode outputs.

## Figure 1 aerosol concentration (`N_a`)

**Finding:** Figure 1 is best reproduced with the paper's high aerosol number concentration

```text
N_a = 10000 cm^-3 = 1.0e10 m^-3
```

not the Appendix A2 typical upper-troposphere value

```text
N_a = 300 cm^-3 = 3.0e8 m^-3
```

**Where this comes from:** Appendix A2 states that the authors often use the unrealistically high value `N_a = 10000 cm^-3` for comparison with reference values. The Figure 1 caption gives `p = 300 hPa` and the temperature colors, but does not state `N_a`.

**Debugging symptom:** Using `300 cm^-3` reproduced the shapes of the Figure 1 saturation-ratio curves, but all generated `s` curves sat above the digitized paper curves by a nearly temperature-dependent constant:

- 190 K: about `+0.0115`
- 210 K: about `+0.0101`
- 230 K: about `+0.0089`

Multiplying those offsets by `p1e(T)` gives approximately `ln(30)` for all three temperatures, pointing to a missing multiplicative factor in the nucleation prefactor `A_n = n_a V_sol J0`. The ratio `10000 / 300 = 33.3` is the required factor.

**Resolution in code:** Episode 2 Figure 1 scripts explicitly use `bergner_spichtinger_2026.constants.N_a_figure1_high` (`1.0e10 m^-3`) and write the value into continuation metadata. The package default remains `N_a_typical` so other experiments do not silently inherit the Figure 1-specific inferred assumption.

**Rule of thumb:** If a generated equilibrium saturation branch is vertically offset from a digitized paper curve while `n` and `q` slopes look right, check undeclared multiplicative constants inside the nucleation prefactor before suspecting the continuation method.

## Shared Trilinos-side C++ residual/Jacobian core

TASK-015 promotes the reusable C++/Trilinos residual and Sacado state-Jacobian core to top-level `loca/`. Despite the directory name and early task wording, the current executable is a lightweight Trilinos-side C++ backend, not a full NOX/LOCA continuation implementation. It deliberately uses a small hand-rolled continuation/Newton driver plus Sacado derivatives and Teuchos/LAPACK dense eigenvalue routines so the C++ equations, state conventions, and physical-Jacobian eigenvalues can be validated before adding the full NOX/LOCA abstraction layer.

Episode-local scripts, notebooks, generated outputs, and curated artifacts remain under their episode directories; only the model core and its CMake build are shared so later C++/Trilinos and eventual NOX/LOCA continuation tasks can reuse the same executable contract.

Build the executable with CMake against `/opt/Trilinos/lib64/cmake/Trilinos`. The stable CLI subcommands are:

```text
bs2026_loca_model residual log_n log_q s log_w [--p Pa] [--T K] [--F value] [--N-a m^-3] [--dz m]
bs2026_loca_model jacobian log_n log_q s log_w [same options]
```

The residual output is `[dn/dt / n, dq/dt / q, ds/dt]` in log-state coordinates. The Jacobian is the 3x3 derivative with respect to `[log_n, log_q, s]` computed by Sacado forward-mode AD, not finite differences.
