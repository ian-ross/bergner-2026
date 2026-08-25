# TASK-074 T=210 K linearized-period curve

TASK-074 generates the lower-panel equilibrium-linearized period curve independently from periodic-orbit continuation. It uses the native C++ `bs2026_loca_model nox-loca-continue` equilibrium corrector over the saved Figure 5 domain `w = 5e-4..2 m s^-1` at `T = 210 K`, then evaluates the physical-coordinate ODE Jacobian

```text
d(dn/dt, dq/dt, ds/dt) / d(n, q, s)
```

and computes `P_lin = 2*pi/abs(Im(lambda))` for the continuously tracked conjugate pair.

## Artifact and commands

Artifact:

- [`../outputs/t210_linearized_period_curve.json`](../outputs/t210_linearized_period_curve.json)

Regenerate or check it after the C++ model executable is built:

```bash
cmake -S loca -B loca-build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build loca-build --parallel 2
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_t210_linearized_period_curve.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_t210_linearized_period_curve.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/t210_linearized_period_curve.json
```

Set `BS2026_MODEL_EXECUTABLE` or pass `--executable` to use a non-default `bs2026_loca_model` build.

## Sampling and validity policy

The generator starts from the documented 401-point log-spaced `w` grid and inserts the exact Episode 006 native-LOCA `T = 210 K` Hopf anchors from `loca_figure3_hopf_loci.csv`. It then applies the documented shape-preserving `log(P_lin)` holdout rule with tolerance `2e-3`; the current artifact passes without additional refinement.

Rows keep explicit validity/source flags under the `episode8-figure5-production-v1` schema. Finite periods are stored only for converged equilibria with a complex pair and `abs(Im(lambda)) > 1e-8 s^-1`. If a future row becomes a real-pair, frequency-floor, or backend gap, the row must carry an explicit reason with null period/frequency rather than a clipped or invented finite value. The current domain has 403 accepted rows and no gaps.

## Validation summary

- Exact Hopf anchors: lower and upper `T = 210 K` Episode 006 native-LOCA physical-Jacobian frequencies pass relative `1e-8` checks.
- Python parity: a stratified set of rows compares native C++ physical-Jacobian matrices, pair frequencies, and periods against independent Python analytic physical-Jacobian evaluation at relative `1e-8` with `1e-12` absolute floor.
- Eigenpair continuity: the artifact records continuation-distance and eigenvector-overlap diagnostics for the tracked positive-imaginary pair; the current minimum stored overlap is above `0.999999`.
- No clipping: the artifact records the policy `never_clip_or_invent_finite_periods`; the maximum accepted period is about `1.73e4 s`, retained as computed rather than clipped to a display range.
