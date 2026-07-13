# Episode 6 planning decisions

Episode 6 targets Bergner & Spichtinger (2026) Figure 3: the Hopf bifurcation diagram in the `T`--`w` parameter plane at `p = 300 hPa` and `F = 1`. The primary objective is to compare true bifurcation-locus computations across Python, AUTO-07p, and NOX/LOCA, using the paper's Table II fits as reference curves.

## Reproduction target

The agreed Figure 3 scope is:

- pressure `p = 300 hPa` (`30000 Pa` in normalized outputs)
- sedimentation factor `F = 1`
- temperature interval `T = 190--240 K`
- vertical velocity coordinate `w_m_s` in `m s^-1`; backends may use `log_w = log(w_m_s)` internally
- two Hopf loci in vertical velocity:
  - lower-`w` branch: Table II coefficient values place `w_b(T)` below `w_a(T)` over `190--240 K`
  - upper-`w` branch: Table II coefficient values place `w_a(T)` above `w_b(T)` over `190--240 K`

Table II gives empirical reference fits

```text
w_a(T) = w_bar * exp(a2*T^2 + a1*T + a0)
w_b(T) = w_bar * exp(b2*T^2 + b1*T + b0)
w_bar = 1 m s^-1
```

with coefficients from the extracted source text:

| coefficient | k=0 | k=1 | k=2 |
| --- | ---: | ---: | ---: |
| `a_k` | `-38.30947` | `0.278555 K^-1` | `-0.00049191 K^-2` |
| `b_k` | `-36.15046` | `0.229111 K^-1` | `-0.00036997 K^-2` |

These fits should be plotted and tabulated as paper-reference curves. They should not replace backend-computed Hopf continuation results. Shared package utilities in `bergner_spichtinger_2026.approximations` expose both the paper names (`table_ii_hopf_w_a`, `table_ii_hopf_w_b`) and branch aliases (`table_ii_lower_hopf_w`, `table_ii_upper_hopf_w`) so episode scripts do not duplicate Table II coefficient literals.

## Method decision: continue Hopf loci, do not only scan

Figure 2-style one-dimensional sweeps and eigenvalue sign-change interpolation are useful for seeds and sanity checks, but Episode 6's main comparison should use actual bifurcation-locus continuation in `(T, w)`. A scan/interpolation path may be retained as a diagnostic or fallback artifact if labeled clearly, but it is not sufficient for the headline backend-comparison claim.

Initial seeds can come from:

- Episode 5 Hopf estimates at `T = 230 K`, approximately `w = 0.04853 m s^-1` and `w = 0.7687 m s^-1`.
- Table II fit values over `T = 190--240 K` as approximate branch guides.
- Local root solves of the augmented Hopf conditions near selected temperatures.

## Backend responsibilities

### Python augmented Hopf continuation

Python is the semantic reference path. It should solve an augmented Hopf system for equilibrium state, parameters, and crossing frequency using package-level physical ODE residual/Jacobian semantics. The augmented equations should enforce equilibrium and the Hopf crossing condition for the physical ODE Jacobian, with implementation details documented before claiming reproduction quality.

Expected role:

- generate seed Hopf points and a transparent reference locus for both branches;
- use physical state variables in curated outputs, even if transformed coordinates are used internally;
- record solver residuals, Jacobian coordinate conventions, and branch orientation.

### AUTO-07p native Hopf continuation

AUTO should provide an independent continuation backend. Unlike Episode 5, where AUTO-generated equilibria were post-processed with Python physical eigenvalues, Episode 6 should prefer AUTO-native Hopf detection and Hopf-branch continuation in the two-parameter plane.

Expected role:

- detect Hopf points along one-parameter equilibrium continuations or start from externally supplied seeds;
- continue lower and upper Hopf branches in `(T, log_w)` or equivalent parameters;
- normalize outputs into the shared Episode 6 schema with enough raw AUTO provenance to audit labels and parameter mappings.

### NOX/LOCA Hopf continuation

The NOX/LOCA path depends on TASK-025. TASK-025 must first establish a full NOX/LOCA backend for the already validated small C++ model and reproduce an existing curated continuation/eigenvalue artifact. Episode 6 should not claim native LOCA Hopf-continuation results until that prerequisite exists.

Expected role after TASK-025:

- add Figure 3-specific LOCA Hopf continuation orchestration;
- preserve the same physical equations and normalized output semantics as Python and AUTO;
- document what LOCA contributes beyond the current lightweight Trilinos-side C++ executable.

## Provisional output schema

Curated per-backend Hopf-locus rows should include at minimum:

| Field | Meaning |
| --- | --- |
| `backend` | `python`, `auto`, or `loca` |
| `branch_id` | stable branch name such as `lower_hopf` or `upper_hopf` |
| `paper_fit_branch` | `wa` for lower/blue or `wb` for upper/red |
| `T_K` | temperature in kelvin |
| `p_Pa` | pressure in pascals |
| `F` | sedimentation factor |
| `log_w` | natural log of physical vertical velocity |
| `w_m_s` | physical vertical velocity |
| `n` | physical ice crystal number concentration at equilibrium |
| `q` | physical ice crystal mass mixing ratio at equilibrium |
| `s` | saturation ratio at equilibrium |
| `hopf_frequency` | imaginary eigenvalue magnitude at the crossing, if available |
| `eigenvalue_real` | real part of the crossing pair, expected near zero |
| `eigenvalue_imag` | imaginary part of one crossing eigenvalue, if available |
| `jacobian_coordinate_system` | expected Figure 3 comparison value: `physical_ode_state` |
| `continuation_parameterization` | e.g. `T_log_w`, `T_w`, or backend-specific normalized parameters |
| `residual_norm` | backend-normalized augmented/equilibrium residual norm |
| `converged` | whether the continuation point converged |
| `source_file` | relative path to raw or normalized source artifact |

Comparison artifacts should also include Table II reference samples with fields such as `paper_fit_branch`, `T_K`, `w_fit_m_s`, and coefficient provenance.

## Planned outputs

Expected curated output groups are:

- `outputs/figure3_python_hopf_loci/` — Python augmented-system Hopf loci, seeds, diagnostics, and metadata.
- `outputs/figure3_auto_hopf_loci/` — AUTO-native Hopf continuation outputs, normalized loci, raw run files, diagnostics, and metadata.
- `outputs/figure3_loca_hopf_loci/` — NOX/LOCA Hopf continuation outputs after TASK-025 and Figure 3-specific LOCA orchestration.
- `outputs/figure3_backend_comparison/` — aligned comparison tables, Table II fit overlays, summary JSON, and Figure 3-style plot.

## Scope boundaries

Keep Episode 6 scripts, notebooks, generated run files, and curated outputs under `episodes/006-figure3-hopf-bifurcation/`. Do not add Figure 3-specific artifacts to top-level `scripts/`, `notebooks/`, or `outputs/` directories. Promote code to top-level `auto/`, `loca/`, or `src/bergner_spichtinger_2026/` only when it is reusable backend/model infrastructure rather than an episode-local experiment.

Open implementation questions include the precise augmented Hopf equations, branch-matching tolerances, whether to digitize Figure 3 dots separately from Table II fits, and how much of AUTO/LOCA solver-internal stability information should be preserved as diagnostics but excluded from backend-neutral physical comparisons.
