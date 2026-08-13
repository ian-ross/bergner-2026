# Episode 008: Figure 5 periodic-orbit continuation

Goal: reproduce both panels of Bergner & Spichtinger (2026) Figure 5 by performing genuine continuation of periodic orbits with collocation, first in Python and then with NOX/LOCA in Trilinos.

This episode follows the conservative prototype-to-Trilinos path documented in the periodic-orbit continuation learning material: begin with implicit midpoint collocation on a fixed mesh, establish layout/residual/Jacobian and continuation parity, then add higher-order fixed-mesh collocation and adaptive remeshing before producing the final period map.

## Current documentation

- [`docs/collocation-phase-decisions.md`](docs/collocation-phase-decisions.md) records the binding decisions and unresolved questions for the initial collocation phase.

## Frozen Episode 007 bootstrap seed

[`outputs/bootstrap_seed.json`](outputs/bootstrap_seed.json) freezes the final complete `paper_0.99` saturation-maximum-to-maximum cycle from the committed Episode 007 reference trajectory. It contains normalized phase knots, `(log(n), log(q), s)`, `log(P)`, transformed model-field phase slopes, canonical parameters, source checksums, and extraction provenance. The reusable [`PeriodicHermiteSeed`](../../src/bergner_spichtinger_2026/periodic_seed.py) loader and cubic-Hermite evaluator can sample arbitrary endpoint or collocation-stage phases without rerunning the roughly 300-period IVP. The standalone [`scripts/generate_bootstrap_seed.py`](scripts/generate_bootstrap_seed.py) remains responsible only for Episode 007 extraction, provenance, deterministic serialization, and its CLI.

Regenerate the artifact or verify that it is current with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_bootstrap_seed.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_bootstrap_seed.py --check
```

The generator records that the final cycle's first event time is present in Episode 007 metadata but is bracketed rather than stored as an exact trajectory row. It therefore verifies source-cycle closure and reuses the terminal saturation-maximum event state at both periodic endpoints. Downstream Python code can load and verify the language-neutral artifact without importing an episode script:

```python
from bergner_spichtinger_2026.periodic_seed import PeriodicHermiteSeed

seed = PeriodicHermiteSeed.from_json(seed_path, verify_upstream_root=repo_root)
states = seed.evaluate(endpoint_or_stage_phases)
```

## Shared Gauss collocation coefficients

[`outputs/collocation_coefficients.json`](outputs/collocation_coefficients.json) is the canonical, language-neutral coefficient artifact for the one-, two-, and three-stage Gauss--Legendre rules (formal orders 2, 4, and 6). The SymPy derivation records exact symbolic forms and 17-significant-digit binary64 literals for the nodes, Runge--Kutta stage matrix, quadrature weights, integrated Lagrange transfer polynomials, and independent defect-check data. Each rule uses the nodes of the next higher Gauss rule as off-collocation check points and stores both Lagrange and integrated-Lagrange evaluation matrices.

The same generator emits the runtime-only standard-library tables used by Python and C++:

- [`src/bergner_spichtinger_2026/collocation_coefficients.py`](../../src/bergner_spichtinger_2026/collocation_coefficients.py)
- [`loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp`](../../loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp)

Python callers select a rule by stage count without loading the JSON artifact:

```python
from bergner_spichtinger_2026 import gauss_legendre_rule

rule = gauss_legendre_rule(3)
```

Matrices use `[evaluation_point][stage]` indexing. `transfer_coefficients[stage][power]` stores coefficients in ascending powers of the element-local coordinate `tau`; the two defect matrices use `[check_point][stage]` indexing.

Regenerate all three outputs or verify byte-for-byte reproducibility with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_collocation_coefficients.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_collocation_coefficients.py --check
```

The generated Python and C++ table modules are standard-library-only and neither import SymPy nor parse the JSON artifact at runtime. SymPy is used only by the coefficient generator and by pre-existing symbolic-analysis utilities elsewhere in the Python package. The artifact checksum is SHA-256 over canonical sorted-key compact UTF-8 JSON excluding the self-referential `checksum` member.

## Fixed-mesh midpoint reference core

[`src/bergner_spichtinger_2026/periodic_orbits.py`](../../src/bergner_spichtinger_2026/periodic_orbits.py) provides the reusable Python reference formulation for fixed-parameter midpoint collocation. `OrbitLayout` stores `N` transformed endpoint blocks, `N` explicit midpoint-stage blocks, and `log(P)` without duplicating the terminal endpoint. `FixedMesh` supports uniform or nonuniform normalized interval boundaries, while `FrozenPhaseReference` samples and defensively freezes the reference orbit, phase tangent, state scaling, quadrature weights, and normalized phase energy.

The `MidpointCollocationAssembler` evaluates component-scaled explicit-stage equations, cyclic endpoint updates, and the quadrature-normalized integral phase condition. Its analytic `scipy.sparse.csr_matrix` Jacobian contains the local endpoint/stage blocks, global `log(P)` column, periodic wraparound, and stage-based phase row. The formulation and centered-difference acceptance threshold are identified by `MIDPOINT_FORMULATION_VERSION` and `JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE`.

A frozen Episode 008 seed can initialize the reusable core without introducing episode paths into package code:

```python
from bergner_spichtinger_2026 import (
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    gauss_legendre_rule,
)

mesh = FixedMesh.uniform(8)
rule = gauss_legendre_rule(1)
reference = FrozenPhaseReference.from_evaluator(
    mesh, rule, seed.evaluate, seed.derivative, state_scaling=(1.0, 1.0, 1.0)
)
assembler = MidpointCollocationAssembler(mesh, environment, reference)
residual = assembler.residual(unknowns)
jacobian = assembler.jacobian(unknowns)
```

Episode-specific seed loading, fixture construction, solver orchestration, and curated outputs remain under this episode; the numerical layout and assembly contract remains reusable package code.

## Uniform fixed-mesh midpoint validation

[`scripts/generate_fixed_mesh_midpoint_results.py`](scripts/generate_fixed_mesh_midpoint_results.py) uses `scipy.optimize.least_squares(method="trf")` with the analytic CSR Jacobian to correct the frozen seed at `N = 32, 64, 128, 256`. Reproduce or verify the curated artifacts with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_fixed_mesh_midpoint_results.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_fixed_mesh_midpoint_results.py --check
```

[`outputs/fixed_mesh_midpoint_results.json`](outputs/fixed_mesh_midpoint_results.json) reports SciPy termination, evaluation counts, independent stage/update/phase block norms, phase energy, period, quadrature-weighted correction from the seed, and phase-aligned comparison to the Episode 007 Hermite cycle. [`outputs/fixed_mesh_midpoint_vectors.npz`](outputs/fixed_mesh_midpoint_vectors.npz) freezes little-endian float64 meshes, packed unknowns, independently recomputed packed residuals, and phase-reference samples for later Python-to-C++ parity. It includes both the accepted `N = 64` solution and a deterministic non-solution whose stage, update, and phase residual blocks are nontrivial. The JSON manifest defines every array shape, ordering, runtime/source provenance, and raw-array SHA-256 checksum.

The `N = 64, 128, 256` systems converge discretely under the versioned `1e-9` stage/update and `1e-10` phase thresholds. The `N = 32` solve is deliberately retained as a rejected diagnostic case: it exhausts 1000 function evaluations and misses all three block gates. The accepted periods decrease from `2768.51 s` (`N = 64`) through `2531.46 s` (`N = 128`) to `2478.67 s` (`N = 256`), compared with the Episode 007 reference `2461.61 s`; the corresponding weighted continuous-reference orbit errors are approximately `0.173`, `0.0390`, and `0.00951`.

**These results separate two questions.** A small collocation residual establishes convergence of the finite-dimensional midpoint equations only. Period error and phase-aligned continuous-orbit error remain separate discretization diagnostics. In particular, the accepted `N = 64` period is still more than 12% above the Episode 007 reference. No fixed uniform midpoint case here is claimed to meet production accuracy.

## Fixed-mesh pseudo-arclength continuation

[`src/bergner_spichtinger_2026/periodic_continuation.py`](../../src/bergner_spichtinger_2026/periodic_continuation.py) adds the transparent Python continuation reference on the unchanged uniform `N = 64` midpoint mesh. The augmented corrector appends one normalized active coordinate (`rho` for fixed-temperature slices or `T_hat = (T - 215 K)/25 K` for the spine) to the square midpoint system and adds one pseudo-arclength row. It builds a fresh parameter-aware midpoint assembler at every trial coordinate, uses analytic local `g_T` and `g_log(w)` derivatives with the documented path chain rules, and keeps centered parameter differences as tests only.

A single diagonal weighted metric is used for secants, tangent normalization, predictors, the arclength row, and reported step lengths. Endpoint and explicit-stage representations each receive half of the orbit weight; state scales are the exact frozen Episode 007 peak-to-peak reciprocals, while `log(P)` and the active normalized coordinate retain unit weights. Every signed branch begins with a fixed-parameter corrected neighbor. Failed or excessively large neighbors are rejected and the requested coordinate step is halved deterministically before forming the oriented two-point secant.

Generate or verify the curated continuation artifacts with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_fixed_mesh_continuation_results.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_fixed_mesh_continuation_results.py --check
```

[`outputs/fixed_mesh_continuation_results.json`](outputs/fixed_mesh_continuation_results.json) records accepted/rejected bootstrap and pseudo-arclength events, independent stage/update/phase/arclength diagnostics, physical and normalized coordinates, periods, branch orientation, phase energies/alignment/distance, and controlled restart lineage. [`outputs/fixed_mesh_continuation_vectors.npz`](outputs/fixed_mesh_continuation_vectors.npz) freezes the metric diagonals, all accepted point vectors, and all three phase references with checksums.

The reference branch starts at the Episode 007 `T = 225 K`, `w = 0.1 m s^-1` orbit (`rho = -0.2639524255`) and lands exactly on the validated Episode 006 spine at `w = 0.1445622537 m s^-1` (`rho = 0`). After one recorded phase-reference refresh it converges along the spine in both directions: a short positive segment reaches `T = 226 K`, while the negative segment genuinely traverses `Delta T_hat = -0.6` to the exact `T = 210 K` spine point. A second controlled refresh then seeds fixed-`T = 210 K` slice segments that reach `rho = -0.15` and `rho = +0.15`. References are immutable within each segment and change only in the two `phase_reference_refresh` records. The stricter bootstrap cap deliberately freezes one rejected excessive startup attempt and its deterministic halving recovery.

**This remains a continuation-machinery and Python-to-LOCA parity milestone.** The accepted `N = 64` midpoint periods range from roughly `2452 s` at `226 K` to `7144 s` on the lower `T = 210 K` slice segment, but the preceding mesh study already showed that `N = 64` can have large period error despite tiny discrete residuals. These values are not production Figure 5 data.

## Shared C++ local model derivatives

[`loca/include/bergner_spichtinger_2026_loca/model.hpp`](../../loca/include/bergner_spichtinger_2026_loca/model.hpp) now scalar-templates the transformed no-evaporation dynamics through all temperature-dependent coefficients and the physical mapping `w = exp(log_w)`. `local_derivatives` seeds only the three local transformed-state variables, physical temperature, and `log_w`; one five-direction Sacado evaluation returns `g`, `D_x g`, `g_T`, and `g_log_w`. It never differentiates an orbit-layout vector.

The same header supplies the normalized continuation columns

```text
g_rho   = 0.5 (log_w_upper - log_w_lower) g_log_w,
g_T_hat = 25 [g_T + (d log_w_spine / dT) g_log_w].
```

The existing value, physical-Jacobian, equilibrium, and Hopf interfaces remain wrappers over the generalized evaluator. Focused C++/Python tests expose local results through deterministic `local-derivatives` and `parameter-columns` CLI test seams and compare values and every derivative column with centered differences. Local environmental derivatives deliberately reject the discontinuous optional evaporation switch.

## Scope boundary

The episode will produce a schema-versioned browser-consumable Figure 5 dataset, but integrating that dataset into the Episode 007 web widget is deferred to follow-up work.
