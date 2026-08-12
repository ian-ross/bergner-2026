# Episode 007 planning decisions

Episode 007 studies and visualizes the attracting limit cycle at the center case of Bergner & Spichtinger (2026) Figure 4. The authoritative scientific path is a clean Python notebook run; its compact, high-precision artifacts validate a separate browser implementation rather than being replayed in place of a browser calculation.

## Canonical scientific case

The Figure 4 center case is fixed as:

| Quantity | Value | Internal representation |
| --- | ---: | --- |
| temperature `T` | `225 K` | kelvin |
| pressure `p` | `300 hPa` | `30000 Pa` |
| vertical velocity `w` | `0.1 m s^-1` | `m s^-1` |
| sedimentation factor `F` | `1` | dimensionless |
| aerosol number `N_a` | `10000 cm^-3` | `1.0e10 m^-3` |
| layer depth `Delta z` | `100 m` | metres |
| evaporation number term | disabled | `include_evaporation=False` |

All numerical cores use SI units. The browser fixes `N_a` at `10000 cm^-3` and converts it to `m^-3` at the browser-model boundary before evaluation. As in the shared Python model, `n` is ice-particle number concentration per dry-air mass; the unregularized no-evaporation equations require strictly positive `n` and `q`.

## Long-integration and convergence contract

Equilibrium and time integration use `(log(n), log(q), s)` coordinates. Compute a positive equilibrium first, estimate the linearized oscillation period from its stability eigenvalues, and integrate each start for approximately 300 of those periods. A different horizon is permitted only if its documented physical duration produces at least as strong a late-cycle convergence assessment.

The four starts are equilibrium-relative and must be retained in metadata:

1. the paper-style all-state perturbation, `0.99 * (n_eq, q_eq, s_eq)`;
2. an independent `n` perturbation, `(1.01 n_eq, q_eq, s_eq)`;
3. an independent `q` perturbation, `(n_eq, 1.01 q_eq, s_eq)`;
4. an independent `s` perturbation, `(n_eq, q_eq, 1.01 s_eq)`.

Identify complete cycles from successive saturation-ratio extrema, excluding incomplete endpoint segments. For every one of the final 20 complete cycles, the relative drift from its preceding complete cycle in both period and `s` peak-to-peak amplitude must be below `0.1%` (`1e-3`). The four late-cycle attractors must also agree under a phase-independent, normalized orbit-geometry distance of at most `1e-3`; a phase shift alone must not count as disagreement. The implemented metric and normalization must be recorded in reference metadata.

## Curated figures and reference-data contract

The authoritative notebook will produce exactly these curated scientific figures:

1. long-run limit-cycle stability diagnostics;
2. all-start attractor convergence in the `log10(n)`--`s` plane;
3. a representative one-cycle state and full process-budget figure.

The one-cycle process figure must show:

- `Nuc_n`, `Sed_n`, and total `dn/dt`;
- `Nuc_q`, `Dep_q`, `Sed_q`, and total `dq/dt`;
- `Cool`, `Nuc_s`, `Dep_s`, and total `ds/dt`.

`outputs/reference_trajectory.csv` will contain an early transient plus the final three complete cycles at 17 significant digits. A full-run per-cycle-summary CSV will retain cycle boundaries, periods, extrema, amplitudes, and drift metrics. `outputs/reference_metadata.json` will be schema-versioned and include canonical parameters and units, initial conditions, solver settings, cycle boundaries, convergence metrics, figure/reference provenance, and the orbit-distance definition. These files are validation fixtures for fresh browser computation, not a substitute for it.

## Widget parameter and numerical contract

The supported browser domain is the conservative tested physical domain in `docs/testing.md`:

| UI control | Supported range | Control behavior |
| --- | ---: | --- |
| `T` | `190`--`235 K` | linear |
| `w` | `0.005`--`2.0 m s^-1` | logarithmic |
| `F` | `0.05`--`1.0` | linear |

The primary controls are `T`, `w`, and `F`. Pressure, layer depth, and aerosol concentration are fixed at the canonical `p=300 hPa`, `Delta z=100 m`, and `N_a=10000 cm^-3`. The UI also exposes physical integration duration, three initial-condition choices (`paper`, `n`, and `q`), and a Figure 4 preset. The preset restores the canonical case and the paper-style `0.99` start.

The browser solves the positive equilibrium client-side with a safeguarded method in log-state coordinates. It then uses adaptive Dormand--Prince RK45 in `(log(n), log(q), s)`, component-wise error scaling, a production maximum trial step of 15 s, cubic Hermite dense output, and explicit accepted-step and output-size limits. Production plotting samples include accepted-step endpoints and saturation stationary points in addition to a sparse uniform baseline, so narrow exponential nucleation peaks do not alias against a fixed output cadence. It evaluates and returns all process terms and total tendencies at every plotting sample. Short-horizon state and process-rate checks target roughly `1e-4` relative agreement with Python before material phase drift; the production browser profile itself must satisfy the long-run period, extrema, amplitudes, and orbit-geometry target of roughly `1e-3` relative agreement and a canonical late-cycle nucleation-peak target of `1e-4` relative variation.

## Static browser architecture

The application will be a static, vanilla TypeScript/Vite application with Plotly bundled locally. It must not use a CDN, backend, Python process, or notebook kernel at runtime. The main thread owns controls, status, Plotly rendering, and replay. A cancellable Web Worker owns the equilibrium solve and integration so a long run does not block interaction.

The worker protocol is typed and has `start`, `equilibrium`, batched `samples`, `progress`, `result`, `failure`, and `cancel` messages. Equilibrium and completed sample batches are buffered while integration continues; cancellation and numerical failure are explicit outcomes. A separate main-thread physical-time clock reveals buffered samples and updates the synchronized state, process-budget, and orbit cursor, so fast worker computation cannot accelerate the visible animation. The 1× rate is 750 model seconds per wall second, scaled directly by the speed selector. Replay follows the cursor with a fixed time window equal to five canonical late-cycle periods and uses initial orbit bounds that already contain the Figure 4 trajectory rather than rebuilding and autoranging every plot.

## Scope boundary

Episode-specific notebook code, web assets, generated reference data, figures, and static bundles remain in `episodes/007-limit-cycle-interactive-widget/`. Do not move Episode 007 experiments into top-level `scripts/`, `notebooks/`, or `outputs/`. Promote only genuinely reusable model/numerical infrastructure to `src/bergner_spichtinger_2026/`.
