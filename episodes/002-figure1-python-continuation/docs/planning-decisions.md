# Episode 2 planning decisions

These notes were moved out of root `CONTEXT.md` because they are specific to the Figure 1 equilibrium-reproduction episode rather than durable project-wide glossary terms.

## Language

**Python continuation**:
An inspectable Python implementation that follows an equilibrium branch as a control parameter changes, using predictor-corrector continuation rather than independent parameter sweeps alone. In this episode, Python continuation may use independent root solves as checks or fallbacks.
_Avoid_: parameter sweep, root-solve grid

**Continuation parameter**:
The control coordinate used to trace an equilibrium branch. For Episode 2 Figure 1 reproduction, the canonical continuation parameter is `log(w)`, with `w` retained as the physical vertical velocity in outputs and plots.
_Avoid_: x-axis variable, sweep variable

**Figure 1 equilibrium branch family**:
The set of equilibrium branches used to reproduce Figure 1 of Bergner & Spichtinger (2026): `p = 300 hPa`, `F = 1`, `T ∈ {190, 210, 230} K`, continued over vertical velocity `w ∈ [0.005, 2.0] m/s`.
_Avoid_: Figure 1 sweep, temperature cases

**Figure digitization**:
Extraction of numerical curve data from a rendered paper figure image, with calibration and provenance recorded. For Figure 1, the colored data curves and black approximation lines are visually co-located, so the digitized curve is treated as the paper-rendered equilibrium curve rather than as separate data and fit series.
_Avoid_: visual comparison only, manual eyeballing

**Figure 1 comparison standard**:
The four-way evidence set for reproducing Figure 1: Python continuation as the primary generated result, independent root solves as continuation validation, Eqs. 92--94 as paper-formula validation, and digitized Figure 1 curves as the external visual benchmark.
_Avoid_: one-curve match, screenshot-only validation

**Reusable continuation code**:
Package-level continuation support intended to be shared by multiple reproduction episodes and backends. Episode-specific scripts may orchestrate runs and write artifacts, but reusable numerical continuation primitives and paper-domain formulas belong in `src/bergner_spichtinger_2026/`.
_Avoid_: one-off continuation script, copied continuation code
