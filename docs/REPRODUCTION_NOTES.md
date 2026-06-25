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
