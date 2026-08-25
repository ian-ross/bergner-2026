# Episode 008: Figure 5 periodic-orbit continuation

Goal: reproduce both panels of Bergner & Spichtinger (2026) Figure 5 by performing genuine continuation of periodic orbits with collocation, first in Python and then with NOX/LOCA in Trilinos.

This episode follows the conservative prototype-to-Trilinos path documented in the periodic-orbit continuation learning material: begin with implicit midpoint collocation on a fixed mesh, establish layout/residual/Jacobian and continuation parity, then add higher-order fixed-mesh collocation and adaptive remeshing before producing the final period map.

## Current documentation

- [`docs/collocation-phase-decisions.md`](docs/collocation-phase-decisions.md) records the binding initial-run decisions and the production questions explicitly deferred until the post-run evidence review.
- [`docs/task068-final-evidence-reconciliation.md`](docs/task068-final-evidence-reconciliation.md) summarizes the completed TASK-068 native adaptive evidence, failures, resource-cost boundaries, and TASK-069 handoff.
- [`docs/task069-evidence-review-and-next-stage-design.md`](docs/task069-evidence-review-and-next-stage-design.md) records the TASK-069 post-run review, TASK-062 hypothesis dispositions, unsupported near-Hopf fit status, and approved downstream production task boundary.
- [`docs/production-schemas.md`](docs/production-schemas.md) defines the TASK-070 `episode8-figure5-production-v1` schema and validation boundary for downstream production, orbit-vector, T=210 K linearized-period, and browser/display artifacts.
- [`docs/task071-resource-profile.md`](docs/task071-resource-profile.md) records the TASK-071 measured native adaptive resource profile and KLU2/iterative-solver review.
- [`docs/task072-measured-native-adaptive-pilot.md`](docs/task072-measured-native-adaptive-pilot.md) records the TASK-072 measured native adaptive pilot over the 210--226 K skeleton and its explicit unresolved-gap ledger.
- [`docs/task073-native-adaptive-pilot-reconciliation.md`](docs/task073-native-adaptive-pilot-reconciliation.md) records the TASK-073 validation review and production go/no-go decision for the measured pilot.
- [`docs/task081-native-adaptive-pilot-gate-followup.md`](docs/task081-native-adaptive-pilot-gate-followup.md) records the TASK-081 follow-up gate that accepts the exact `spine-210K` post-remesh restart point and authorizes TASK-075 under the retained v1 method.
- [`docs/task075-full-domain-native-adaptive-continuation.md`](docs/task075-full-domain-native-adaptive-continuation.md) documents the TASK-075 full-domain native adaptive target ledger, accepted production point, explicit gaps, sampling-refinement status, and production-v1 artifacts.
- [`docs/task076-near-hopf-approach-policy.md`](docs/task076-near-hopf-approach-policy.md) documents the TASK-076 near-Hopf evidence review, skipped fit prerequisites, and explicit-gap policy records.
- [`docs/task077-floquet-postprocessing.md`](docs/task077-floquet-postprocessing.md) documents the TASK-077 Floquet multiplier postprocessing diagnostics for accepted native production orbits.
- [`docs/task078-stratified-ivp-validation.md`](docs/task078-stratified-ivp-validation.md) documents the TASK-078 stratified independent IVP validation for accepted native production orbits.
- [`docs/task074-t210-linearized-period-curve.md`](docs/task074-t210-linearized-period-curve.md) documents the native C++ T=210 K equilibrium-linearized period curve for the lower Figure 5 panel.

## Production schema boundary

TASK-070 freezes the `episode8-figure5-production-v1` contract before new authoritative Figure 5 production data are generated. The machine-readable contract is [`schemas/episode8-figure5-production-v1.contract.json`](schemas/episode8-figure5-production-v1.contract.json), and the validation command is:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py <artifact.json>
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py --print-contract
```

The validator requires explicit provenance, SHA-256 checksums, schema/method versions, coordinate conventions, units, validity/source flags, and unambiguous gap/unresolved/interpolated-source policy. Digitized paper Figure 5 data remain non-authoritative external comparison evidence only.

## Native adaptive resource profile

TASK-071 replaces the TASK-068 zero resource placeholders with measured wall-clock, CPU-time, max-RSS, NOX-iteration, KLU2 factorization, and linear-solve evidence for representative current seams. The profiling artifacts are:

- [`outputs/native_adaptive_resource_profile.json`](outputs/native_adaptive_resource_profile.json)
- [`outputs/native_adaptive_resource_profile_run_metadata.json`](outputs/native_adaptive_resource_profile_run_metadata.json)

Check them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_resource_profile_run_metadata.json
```

The measured profile is cost evidence only, not scientific acceptance of continuation points. It preserves the TASK-068 failed/pending target boundary. Its KLU2 review concludes that serial KLU2 remains acceptable for the current native adaptive pilot seams; the documented iterative-solver trigger thresholds are not met by available measured evidence.

## Measured native adaptive pilot

TASK-072 runs the measured native adaptive pilot over all 31 provisional `210--226 K` skeleton targets. The artifacts are:

- [`outputs/native_adaptive_measured_pilot.json`](outputs/native_adaptive_measured_pilot.json)
- [`outputs/native_adaptive_measured_pilot_events.json`](outputs/native_adaptive_measured_pilot_events.json)
- [`outputs/native_adaptive_measured_pilot_run_metadata.json`](outputs/native_adaptive_measured_pilot_run_metadata.json)

Check them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_run_metadata.json
```

The pilot records all 31 targets as backend-emitted `resolution_unresolved` explicit gaps with reasons. The measured `spine-210K` remesh/restart seam passes residual, phase, positivity, finite-change, tangent, and KLU2 linear-solve gates, but its exact native restart vector does not yet have backend-bound independent defect and period/orbit convergence gates, so it is not accepted. No interpolation, Python substitution, fixed-mesh relabeling, or digitized-paper evidence fills those gaps.

## Native adaptive pilot reconciliation

TASK-073 reviews the measured pilot before any full-domain production continuation. The reconciliation artifact is:

- [`outputs/native_adaptive_pilot_reconciliation.json`](outputs/native_adaptive_pilot_reconciliation.json)

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_reconciliation.py --check
```

The review preserves the TASK-072 terminal ledger exactly: `accepted=0`, `resolution_unresolved=31`, `failed=0`, `near_hopf_stop=0`, and `tripwire_stop=0`. No IVP subset is justified because no accepted native adaptive pilot point exists. Full-domain continuation is **not authorized** from this pilot gate; the retained v1 method is not falsified, but TASK-081 follow-up gate work is required before TASK-075 can be treated as production-authorized.

## Native adaptive pilot gate follow-up

TASK-081 resolves the TASK-073 blocker without rewriting TASK-072/TASK-073 history. The follow-up artifacts are:

- [`outputs/native_adaptive_pilot_gate_followup.json`](outputs/native_adaptive_pilot_gate_followup.json)
- [`outputs/native_adaptive_pilot_gate_followup_events.json`](outputs/native_adaptive_pilot_gate_followup_events.json)
- [`outputs/native_adaptive_pilot_gate_followup_run_metadata.json`](outputs/native_adaptive_pilot_gate_followup_run_metadata.json)
- [`outputs/native_adaptive_pilot_gate_followup_exact_restart_fixture.txt`](outputs/native_adaptive_pilot_gate_followup_exact_restart_fixture.txt)

Check them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_gate_followup.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_run_metadata.json
```

The revised pilot gate records `accepted=1` (`spine-210K`) and `resolution_unresolved=30`. The accepted point is the exact native post-remesh restart vector, with backend-bound defect and period/orbit convergence gates plus same-coordinate Python and DOP853 one-period IVP validation. TASK-075 may proceed under the retained `external-gauss3-hr-adaptive-v1` method. The remaining pilot targets stay explicit unresolved gaps; no interpolation, fixed-mesh relabeling, Python-only substitution, or digitized-paper evidence fills them.

## Full-domain native adaptive continuation

TASK-075 applies the TASK-081 authorization to the full Figure 5 native adaptive target skeleton. The artifacts are:

- [`outputs/native_adaptive_full_domain_run.json`](outputs/native_adaptive_full_domain_run.json)
- [`outputs/native_adaptive_full_domain_points.json`](outputs/native_adaptive_full_domain_points.json)
- [`outputs/native_adaptive_full_domain_events.json`](outputs/native_adaptive_full_domain_events.json)
- [`outputs/native_adaptive_full_domain_run_metadata.json`](outputs/native_adaptive_full_domain_run_metadata.json)
- [`outputs/native_adaptive_full_domain_orbit_manifest.json`](outputs/native_adaptive_full_domain_orbit_manifest.json)
- [`outputs/native_adaptive_full_domain_orbits.npz`](outputs/native_adaptive_full_domain_orbits.npz)

Check them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_full_domain_run.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_run_metadata.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json
```

The full-domain ledger covers `T = 190--240 K`, exact `T = 225 K` anchor lineage, spine points, `rho = 0, +/-0.25, +/-0.50, +/-0.75, +/-0.90, +/-0.97` anchors, and accepted-evidence refinement-neighborhood targets. Current production gates accept only `spine-210K` from TASK-081 native-backend evidence; all other requested targets are explicit `resolution_unresolved` policy gaps rather than claimed native C++ solves. Holdout-driven sampling refinement records along-slice and between-slice log-period errors as `not_evaluated` because interpolation requires more accepted points and must not cross unresolved gaps.

## Near-Hopf approach review

TASK-076 reviews the lower and upper T=210 K Hopf-side approaches from production native adaptive records only. The artifacts are:

- [`outputs/native_adaptive_near_hopf_review.json`](outputs/native_adaptive_near_hopf_review.json)
- [`outputs/native_adaptive_near_hopf_policy_records.json`](outputs/native_adaptive_near_hopf_policy_records.json)

Check them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_near_hopf_review.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_near_hopf_policy_records.json
```

Current production evidence has zero reliable near-Hopf approach points on either side. The requested T=210 K targets at `rho=+/-0.25`, `+/-0.50`, `+/-0.75`, `+/-0.90`, and `+/-0.97` are all `resolution_unresolved`; therefore quadratic/quartic `P(A)` fits, leave-one-out intercept checks, residual checks, and Episode 006 Hopf-period comparisons are not performed. The production-v1 policy records encode both Hopf-limit connections as explicit gaps with null display periods and no invented regular-orbit amplitude or period at the Hopf boundaries.

## Floquet postprocessing diagnostics

TASK-077 computes Floquet multipliers as postprocessing for schema-valid accepted native production orbits. The artifact is:

- [`outputs/native_adaptive_floquet_diagnostics.json`](outputs/native_adaptive_floquet_diagnostics.json)

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_floquet_diagnostics.py --check
```

The current diagnostic set contains only the accepted `spine-210K` TASK-075 orbit. DOP853 variational integrations over the native piecewise collocation polynomial record the autonomous trivial multiplier, nontrivial multipliers, tolerance-refinement comparisons, and stability classification. Implicit Radau is run as a comparison for the canonical accepted point; near-Hopf/long-period and suspected nontrivial unit-circle crossing strata are explicitly recorded as unavailable until schema-valid accepted production points exist. Unresolved targets, failed targets, Hopf-limit policy records, interpolation, and digitized-paper evidence are not relabeled as regular orbits.

## Stratified independent IVP validation

TASK-078 validates the deduplicated accepted native production orbit set selected from twelve documented categories. The artifact is:

- [`outputs/native_adaptive_ivp_validation.json`](outputs/native_adaptive_ivp_validation.json)

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_ivp_validation.py --check
```

The current TASK-075 ledger has one accepted native production orbit, `spine-210K`, so category deduplication selects that point for DOP853 one-period return and phase-aligned trajectory validation. The DOP853 gates pass. Radau agreement is run for the available headline point; near-Hopf, low/high-temperature interior, worst-holdout, and additional headline/attractor strata are recorded as unavailable or insufficient production evidence rather than filled from unresolved, interpolated, qualification-only, Hopf-limit, or digitized-paper records. TASK-078 does not tune or overwrite native continuation periods.

## T=210 K equilibrium-linearized period curve

TASK-074 generates the lower-panel red equilibrium-linearized curve independently from periodic-orbit continuation. The production-v1 artifact is:

- [`outputs/t210_linearized_period_curve.json`](outputs/t210_linearized_period_curve.json)

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_t210_linearized_period_curve.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/t210_linearized_period_curve.json
```

The generator uses native C++ `bs2026_loca_model nox-loca-continue` equilibrium continuation over `w=5e-4..2 m s^-1` at `T=210 K`, inserts the exact Episode 006 native-LOCA Hopf anchors, tracks the physical-Jacobian complex pair continuously, and computes `P_lin = 2*pi/abs(Im(lambda))` only when the pair is genuinely complex above the `1e-8 s^-1` frequency floor. The current 403-row artifact has no gaps, passes the documented shape-preserving log-period holdout rule without extra refinement, and passes stratified independent Python physical-Jacobian parity plus exact Hopf-anchor frequency checks at relative `1e-8`. Periods are never clipped or invented for display.

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

## Serial sparse Tpetra midpoint assembler

[`loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp`](../../loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp) implements the fixed-mesh midpoint base system directly with `Tpetra::Map`, `Tpetra::Vector`, `Tpetra::CrsGraph`, and `Tpetra::CrsMatrix`. The current `OrbitLayout` deliberately accepts only a one-rank communicator and owns all endpoint, explicit-stage, `log(P)`, stage-row, update-row, and normalized-phase-row global indices through square Tpetra maps. It stores no duplicate terminal endpoint and uses cyclic indexing for the last update row.

The assembler fill-completes one graph at construction and reuses that graph for every Jacobian while the layout is fixed. The graph includes local endpoint/stage couplings, periodic wraparound, the global `log(P)` column, and the stage-only normalized phase row. Values and small local derivatives come from the shared Sacado model evaluator; packed-orbit automatic differentiation and a dense/Epetra fallback are intentionally absent. The base residual remains square and contains only stage equations, endpoint updates, and the phase condition. NOX solving and Thyra wrapping remain TASK-060 scope.

The focused `bs2026_midpoint_orbit` executable reads a simple language-neutral text fixture and exposes layout/graph, component residuals, an assembled Jacobian action, normalized rho/T-hat parameter columns, and block diagnostics. [`scripts/generate_tpetra_midpoint_fixtures.py`](scripts/generate_tpetra_midpoint_fixtures.py) creates accepted and deterministic nonsolution `N=8` fixtures and translates the frozen TASK-056 accepted/nonsolution `N=64` vectors without changing those prior artifacts:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_tpetra_midpoint_fixtures.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_tpetra_midpoint_fixtures.py --check
```

Python-driven integration tests require component parity at relative tolerance `1e-11` with an explicit `1e-13` absolute floor, verify stable retained-graph reuse and wraparound/global couplings at both `N=8` and `N=64`, and check assembled Jacobian actions and normalized parameter columns against centered finite differences at the versioned `1e-6` directional tolerance. The Jacobian action is checked against a centered residual difference evaluated independently through the C++ assembler as well as against Python. Diagnostics use global-ID-to-local-ID map lookups rather than assuming a distributed local ordering and report block max/RMS values, normalized phase magnitude and energy, fixed state scaling, and the exact interval/component identifiers of the largest stage and update residuals. Generate fixtures through `uv run` using the committed `uv.lock`; the manifest records Python, NumPy, and SciPy versions plus the lockfile checksum because the deterministic `N=8` accepted vector is produced by the versioned SciPy correction path.

[`outputs/tpetra_midpoint_fixtures/manifest.json`](outputs/tpetra_midpoint_fixtures/manifest.json) records the matching C++/Python formulation and tolerance constants, case meanings and shapes, fixture byte hashes, runtime versions, and source/upstream paths and hashes. The `N=64` fixture boundaries, phase samples, unknowns, and residual semantics are translated directly from the frozen TASK-056 NPZ arrays; regeneration asserts byte-level array agreement before emitting fixtures. `--check` validates every fixture and manifest byte.

## Sparse Thyra/NOX fixed-parameter correction

[`loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp`](../../loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp) exposes the existing square `6N+1` Tpetra base system through a `Thyra::StateFuncModelEvaluatorBase<double>`. Its Thyra `x` and `f` spaces wrap the assembler's square domain/range maps, `log(P)` remains the last solution coordinate, and every `W_op` wraps a matrix built from the assembler's retained sparse graph. The fixed-parameter corrector constructs a `NOX::Thyra::Group` with an explicitly selected `Thyra::Amesos2LinearOpWithSolveFactory<double>` using KLU2. It reports the real Amesos2 backend and status counters for symbolic factorizations, numeric factorizations, and solves; it does not report an unavailable condition estimate.

The language-neutral fixture set now also includes `n64_seed.txt`, the exact Episode 007 periodic Hermite seed sampled into the Python `N=64` midpoint layout, and `n64_perturbed.txt`. The perturbation is versioned in the manifest:

```text
x[k]    += 1e-4 sin(k + 0.375),  k < 6N,
log(P)  += 1e-5 sin(6N + 0.375).
```

Run either correction with:

```bash
loca-build/bs2026_midpoint_orbit solve \
  episodes/008-figure5-periodic-orbit-continuation/outputs/tpetra_midpoint_fixtures/n64_seed.txt
loca-build/bs2026_midpoint_orbit solve \
  episodes/008-figure5-periodic-orbit-continuation/outputs/tpetra_midpoint_fixtures/n64_perturbed.txt
```

The stable line-oriented output records solver version, square Thyra dimensions and `log(P)`/phase indices, NOX status and iterations, KLU2 status counters, corrected vector, residual vector, period, block diagnostics, physical positivity/finiteness, acceptance, and rejection reasons. Acceptance is centralized and requires NOX convergence; stage/update maximum and RMS at most `1e-9`; normalized phase residual at most `1e-10`; positive finite physical `n`, `q`, and `P`; positive finite phase energy; and successful reported KLU2 symbolic/numeric factorization and solve diagnostics. A nominal NOX success therefore cannot bypass any orbit or linear diagnostic. The corrected period and fixed-metric weighted orbit must match the frozen Python solution within the versioned `1e-8` tolerance.

This correction establishes sparse Thyra/NOX/KLU2 migration parity only. The uniform midpoint `N=64` period remains more than 12% above the Episode 007 reference period, so the result is not production Figure 5 accuracy.

## Native LOCA fixed-mesh continuation

[`loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp`](../../loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp) adds the native continuation layer. Its Thyra model has exactly one scalar parameter vector (`rho` or `temperature_hat`) and keeps the base residual square at `6N+1`: midpoint stages, cyclic endpoint updates, and one normalized phase row, with `log(P)` still in the solution vector. The base model does not append an arclength equation; the `LOCA::Stepper` creates the one-row `Arc Length` extension and owns the pseudo-arclength constraint, predictor, tangent, adaptive step-size changes, rejected attempts, and retries.

The group overrides LOCA's default dimension-normalized Thyra dot product with the binding endpoint/stage half-weighted metric. Endpoint and stage representations each receive half of the orbit weight, the exact frozen state scales are used, and `log(P)` and the normalized active coordinate have unit weight. LOCA arc-length parameter rescaling is disabled so this metric is not silently changed. `DfDp` is the existing analytic rho or T-hat parameter column, including the spine chain rule. The corrected bootstrap neighbor is still created separately by fixed-parameter NOX with deterministic halving and excessive-weighted-change rejection; it is recorded as `branch_bootstrap`, not a native accepted step.

The validation manifest retains the five required `N=64` branches: the `T=225 K` move to the exact spine, short positive and negative T-hat spine segments (including the exact `T=210 K` spine point), and both signed `T=210 K` rho slices. The two phase-reference refreshes are controlled restart boundaries: they preserve physical coordinates, verify the refreshed base orbit, and rebuild the native group/stepper. Generate or check the versioned artifacts after building the C++ executable:

```bash
cmake -S loca -B loca-build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build loca-build --parallel 2
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_midpoint_results.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_midpoint_results.py --check
```

[`outputs/native_loca_midpoint_results.json`](outputs/native_loca_midpoint_results.json) records independently executed native Secant/Adaptive LOCA replays of all five branches, including every corrected native vector, fixed-parameter bootstrap attempt, authoritative LOCA callback partition (separate initial, regular attempted/retried, and final saves with finite coordinates and explicitly labeled coordinate deltas), exact target landing, immutable segment reference ID, and both full-stack controlled refreshes. A deterministic smoke-only fault injection rejects the first converged native corrector and verifies LOCA retries with a smaller active-coordinate delta. Raw LOCA iterator counters are stored under `raw_loca_*` names separately from the fully reconcilable `derived_*` callback/save counts. Each refresh is accepted only after fixed-parameter NOX/KLU2 verification beneath the newly frozen phase row; its residuals, physical-coordinate preservation, and concrete rebuild lineage are stored. [`outputs/native_loca_midpoint_vectors.npz`](outputs/native_loca_midpoint_vectors.npz) contains only vectors emitted by the native C++ recorder; it no longer copies the Python NPZ. The Python artifact remains an independent reference. Every native accepted point is independently corrected by the Python base formulation at the identical physical coordinate, initialized from the nearest frozen Python branch point rather than the native vector, and compared in the frozen weighted metric and period relative error against the versioned `2e-7` tolerance. Adaptive interior points additionally retain nearest transparent-Python-branch diagnostics because the two pseudo-arclength steppers choose different grids. The generator binds the emitting executable to current transitive source fingerprints, including the NOX adapter and collocation-coefficient header, and records source/runtime/Trilinos provenance; native vector hashes must be disjoint from every frozen Python point hash. The former second-step NaN was traced to two orchestration errors rather than an installed-LOCA defect: Predictor and Step Size were placed under `LOCA/Stepper` instead of the parser's sibling `LOCA/Predictor` and `LOCA/Step Size` sublists, and a standalone MaxIters status test bypassed LOCA's parameter-bound stopping logic so `finish()` targeted its zero sentinel.

**This is still a fixed `N=64` midpoint continuation-machinery milestone, not production Figure 5 data.** Native LOCA ownership does not repair the already measured midpoint discretization error.

## Shared C++ local model derivatives

[`loca/include/bergner_spichtinger_2026_loca/model.hpp`](../../loca/include/bergner_spichtinger_2026_loca/model.hpp) now scalar-templates the transformed no-evaporation dynamics through all temperature-dependent coefficients and the physical mapping `w = exp(log_w)`. `local_derivatives` seeds only the three local transformed-state variables, physical temperature, and `log_w`; one five-direction Sacado evaluation returns `g`, `D_x g`, `g_T`, and `g_log_w`. It never differentiates an orbit-layout vector.

The same header supplies the normalized continuation columns

```text
g_rho   = 0.5 (log_w_upper - log_w_lower) g_log_w,
g_T_hat = 25 [g_T + (d log_w_spine / dT) g_log_w].
```

The existing value, physical-Jacobian, equilibrium, and Hopf interfaces remain wrappers over the generalized evaluator. Focused C++/Python tests expose local results through deterministic `local-derivatives` and `parameter-columns` CLI test seams and compare values and every derivative column with centered differences. Local environmental derivatives deliberately reject the discontinuous optional evaporation switch.

## Python higher-order fixed-mesh qualification

[`src/bergner_spichtinger_2026/periodic_orbits.py`](../../src/bergner_spichtinger_2026/periodic_orbits.py) now provides a rule-driven `GaussCollocationAssembler` for the frozen one-, two-, and three-stage Gauss--Legendre rules. It retains the midpoint class and correction API as exact compatibility wrappers, while adding generic residual/Jacobian assembly, collocation-polynomial evaluation, fixed-mesh/rule transfer, phase-reference transfer, stage-count-independent comparisons, and the versioned two-grid independent-defect diagnostic.

Generate or verify the complete TASK-064 evidence with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_higher_order_fixed_mesh_qualification.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_higher_order_fixed_mesh_qualification.py --check
```

[`outputs/higher_order_fixed_mesh_qualification.json`](outputs/higher_order_fixed_mesh_qualification.json) and its deterministic NPZ retain the prescribed canonical and `T=210 K` guard ladders, every nonlinear outcome, component gates, two-grid defects, phase-aligned same-rule refinement, and canonical DOP853 evidence. The four language-neutral accepted/nonsolution two-/three-stage fixtures live under [`outputs/higher_order_parity_fixtures/`](outputs/higher_order_parity_fixtures/).

The canonical three-stage `N=16` solve is deliberately retained as rejected after exhausting 1000 evaluations. All other requested higher-order systems converge discretely. The best canonical result is three-stage `N=64`, with period `2461.617474 s`. A versioned DOP853 run integrates for `2.1` collocation periods, independently locates and refines two successive saturation maxima, and obtains period `2461.617092 s` (relative difference `1.55e-7`), scaled return error `1.48e-6`, and phase-aligned weighted dense-orbit error `2.39e-5`; all pass the `1e-3` contract. However, no prescribed same-rule higher-order refinement pair passes both `1e-3` period and weighted-orbit checks, and every independent defect remains above `1e-4` (best canonical maximum approximately `7.38e-3`). The `T=210 K` guard pairs likewise miss the refinement gates. These misses are qualification evidence, not tuned away.

The artifact explicitly separates nonlinear acceptance from discretization qualification: 20 cases satisfy the finite-dimensional residual gates, one is rejected, and zero fixed-uniform cases are qualified because defect and/or same-rule refinement evidence misses. Cross-order comparisons are retained separately. Accordingly, fixed uniform meshes are not production-qualified. The non-Floquet Radau triggers based on defect/convergence stagnation are not yet active because their contract applies only after two adaptive remesh cycles. Finite-positive physical mapping of endpoints/stages is checked; polynomial ringing is `not_evaluated` because TASK-064 defines no versioned ringing metric. Floquet remains `not_evaluated` through TASK-068.

## C++ sparse higher-order fixed-parameter correction

The serial Tpetra base assembler now consumes the frozen one-, two-, and three-stage Gauss tables. Its square layout has `3N(r+1)+1` unknowns/residuals, interval-major explicit stages, cyclic endpoint updates, `log(P)`, and one quadrature-normalized phase row. The fill-completed sparse graph is retained for each fixed mesh/rule; Jacobian values and normalized rho/T-hat columns use local Sacado model derivatives. Midpoint constructors/index overloads remain compatibility entry points. The same square groups now feed native LOCA for every frozen Gauss rule; LOCA alone adds the continuation coordinate/arclength extension.

The generalized Thyra/NOX/Amesos2-KLU2 corrector preserves independent nonlinear, residual-block, phase, physical positivity/finiteness, phase-energy, and concrete factorization/solve gates. Exact upstream solutions receive a small deterministic solve perturbation so each required correction exercises KLU2 instead of terminating at iteration zero. Missing early/zero-iteration linear diagnostics remain stably unreported and therefore fail the independent linear gate.

[`scripts/generate_cpp_higher_order_fixtures.py`](scripts/generate_cpp_higher_order_fixtures.py) projects TASK-064 vectors into versioned text fixtures under [`outputs/cpp_higher_order_fixtures/`](outputs/cpp_higher_order_fixtures/). The explicit bundle contains canonical two-stage `N=64`, canonical three-stage `N=32` and `N=64`, all three accepted `T=210 K` three-stage `N=32` guards, the upstream-rejected canonical three-stage `N=16` case, and the exact versioned two-/three-stage `N=64` nonsolutions from the language-neutral bundle. Its manifest records nonlinear-accepted semantics separately from scientific qualification, exact projection linkage, seed/reference lineage, the canonical coefficient checksum, source/runtime hashes, perturbations, and parity tolerances. Regenerate or check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_fixtures.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_fixtures.py --check
```

All six accepted bundle seeds correct with real KLU2 activity and match corresponding Python periods and phase-aligned weighted orbits within `1e-8`. The rejected TASK-064 case returns `upstream_fixture_rejected` without attempting NOX; nonsolutions instead return `fixture_not_correction_input`, so neither status is silently omitted or mislabeled.

[`outputs/cpp_higher_order_correction_results.json`](outputs/cpp_higher_order_correction_results.json) freezes the executed C++ evidence for all accepted, rejected, and nonsolution fixture paths. It records rule/mesh/layout/block/retained-graph dimensions, compiled coefficient and source fingerprints, NOX/KLU2 counters, residual diagnostics, correction parity, executable/runtime provenance, and explicit rejection reasons. Its generator rejects stale binaries whose compiled fingerprints do not match current sources:

```bash
BS2026_MIDPOINT_EXECUTABLE=loca-build/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_correction_results.py
BS2026_MIDPOINT_EXECUTABLE=loca-build/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_correction_results.py --check
```

## Native higher-order fixed-mesh LOCA continuation

The native Thyra/LOCA family is rule-aware for one-, two-, and three-stage Gauss layouts. The base group remains square (`3N(r+1)+1`) and has no repository-owned arclength row. Endpoint storage receives half of the orbit metric; stage `j` receives `0.5 Delta theta_i b_j S_x^2`, so the summed endpoint and stage weights are each `0.5 S_x^2` for every rule. `log(P)` and the normalized coordinate retain unit weights. Analytic normalized `DfDp`, signed fixed-parameter bootstrap, Secant/Restart prediction, Arc Length continuation, Adaptive stepping, and rejection/retry ownership remain native LOCA contracts.

The curated three-stage `N=32` run replays exactly five segments: `T=225 K` to the spine, both spine directions (including exact `T=210 K`), and both signed `T=210 K` rho guards. Every recorded native point passes a perturbed fixed-parameter NOX/KLU2 residual, phase, physical-positivity, period, and linear-solve validation. The two phase changes rebuild the assembler/model/group/stepper stack and record old/new physical-coordinate equality plus zero stage/derivative-to-refreshed-reference identity error. Two- and three-stage Thyra seams request `OUT_ARG_DfDp` for both rho and normalized temperature, restore the center environment after shared-model trials, and measure centered-residual relative errors from `1.10e-10` to `1.55e-9` against a `2e-6` gate. A two-stage `N=64` smoke run freezes the same dimensions, metric, bootstrap, and forced native rejection/reduced-retry behavior.

Generate or byte-check the source-bound native-only artifacts after configuring the executable (re-run CMake configuration after source edits so its compiled fingerprints are current):

```bash
BS2026_MIDPOINT_EXECUTABLE=loca-build/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_higher_order_results.py
BS2026_MIDPOINT_EXECUTABLE=loca-build/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_higher_order_results.py --check
```

[`outputs/native_loca_higher_order_results.json`](outputs/native_loca_higher_order_results.json) stores rule/mesh/metric/base/extended dimensions, signed bootstrap and injected-Restart orientation/norms, refresh lineage, raw and callback-derived event accounting, exact targets, source/runtime fingerprints, native validation gates, and independent Python all-point parity. Generator invariants reconcile contiguous callbacks, one initial/final save, regular attempts, saved points, rejected retry adjacency/linkage, and raw failed/total counts. Runtime provenance binds the exact executable SHA-256, emitted compiler/Trilinos identity, Release build type, CMake source/configuration hash, and six compiled sources. Consequently `--check` must use the exact recorded build; regenerate intentionally when another environment produces a different executable digest. Each Python comparison is a separate three-stage fixed-parameter correction at the identical native coordinate, seeded only from frozen or Python-derived higher-order vectors—never from the native vector. Maximum observed relative period and weighted-orbit errors are about `1.58e-12` and `2.84e-12`, below the versioned `2e-7` limits. [`outputs/native_loca_higher_order_vectors.npz`](outputs/native_loca_higher_order_vectors.npz) contains only C++ recorder vectors and is checksum-disjoint from frozen Python arrays. This remains fixed-mesh continuation evidence, not production Figure 5 accuracy.

## Native adaptive remesh/restart manifest

[`scripts/generate_native_adaptive_loca_manifest.py`](scripts/generate_native_adaptive_loca_manifest.py) creates the initial TASK-068 remesh/restart manifest by reconciling the frozen TASK-067 Python adaptive fixtures with the executed native three-stage fixed-mesh LOCA evidence. Regenerate or check it with:

```bash
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_restart_smoke.py
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_restart_smoke.py --check
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_one_branch_segment.py
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_one_branch_segment.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py --check
```

[`outputs/native_adaptive_restart_smoke.json`](outputs/native_adaptive_restart_smoke.json) records native C++ smoke evidence for the adaptive-controller and remesh/restart seams on final nonuniform fixtures. It is not the full spine-and-slices run: it freezes controller intermediates for all projected fixtures and representative h+r transfer/rebuild/fixed-parameter NOX/KLU2 restart corrections with gate and vector hashes. [`outputs/native_adaptive_one_branch_segment.json`](outputs/native_adaptive_one_branch_segment.json) is the first integrated TASK-068.01 slice: it reruns the native three-stage `spine-negative-T-hat-to-210` LOCA segment, stops for remeshing only at the accepted final point, applies the TASK-067 controller to the matching `adaptive-guard-rho-0-g3-n32` fixture, records transferred solution/phase-reference/tangent vectors, rebuilds and corrects the remeshed stack with NOX/KLU2, and cross-checks the restart solution against the existing restart-smoke parity artifact. It explicitly records that the full adaptive spine-and-slices run is not claimed. [`outputs/native_adaptive_loca_manifest.json`](outputs/native_adaptive_loca_manifest.json) records the structural v1 native segment contract: LOCA-owned fixed-mesh segments stop only at accepted points before remeshing; remesh restarts rebuild Tpetra/Thyra/NOX/KLU2/LOCA state; post-transfer gates include residual, phase, positivity, finite-change, linear-solve, and tangent checks; and the exact TASK-067 h+r, pure-r, and tangent-only retry orders are embedded. It also includes a deterministic segment/restart ledger summarizing native LOCA event partitions, the one-branch native adaptive segment, adaptive mesh histories, restart-smoke gates, phase lineage, terminal target statuses, and the runtime/memory fields required for the full adaptive run. Its TASK-068.05 failure-policy ledger records synthetic/native-driver coverage for failed h+r restart attempts, pure-r retry order, mesh-cap escalation, phase-refresh trigger preservation, single-valued tripwires, interruption/resume, stale checkpoint rejection, and fixed-mesh regression safety; it also summarizes TASK-067 aliasing/Radau-trigger evidence and preserves near-Hopf fixture absence as explicit `not_evaluated`. [`outputs/native_adaptive_loca_manifest_vectors.npz`](outputs/native_adaptive_loca_manifest_vectors.npz) stores first/last native fixed-mesh checkpoints for each completed branch plus final Python adaptive meshes/unknowns/defects for resumability checks.

[`scripts/generate_cpp_adaptive_nonuniform_fixtures.py`](scripts/generate_cpp_adaptive_nonuniform_fixtures.py) additionally projects the final TASK-067 nonuniform adaptive meshes into C++ text fixtures under [`outputs/cpp_adaptive_nonuniform_fixtures/`](outputs/cpp_adaptive_nonuniform_fixtures/). Focused tests compare native C++ residuals, analytic Jacobian actions, normalized parameter columns, continuation metric weights, collocation-polynomial solution/phase/tangent transfer, independent defect grids/probe escalation, composite r monitors, h marking, bounded global-beta r movement, controller decisions, restart retry order, remesh rebuild identity, post-transfer NOX/KLU2 correction, nonuniform phase quadrature, and fixed-parameter NOX/KLU2 correction gates against independent Python assembly for the final adaptive qualification meshes.

This manifest is intentionally truthful preparatory evidence, not a claim that native adaptive remeshing has already run. It enumerates the provisional `210--226 K` spine skeleton (including exact `T=210 K` and `T=225 K` anchors), the `T=225 K` move to the spine, both temperature directions, and signed `rho=+-0.15` slice targets for every skeleton temperature. Targets already supported by native fixed-mesh checkpoints are marked `accepted`; targets awaiting native adaptive execution are explicit `failed` terminal statuses with reasons rather than interpolated or hidden points. Broader IVP-based and all Floquet-dependent evidence remain `not_evaluated`, and near-Hopf fitting remains deferred to TASK-069.

## Generalized adaptive driver and resumability

[`src/bergner_spichtinger_2026/native_adaptive_driver.py`](../../src/bergner_spichtinger_2026/native_adaptive_driver.py) now provides the reusable TASK-068.02 orchestration layer for native adaptive continuation. The driver keeps the numerical backend pluggable: a production backend executes fixed-mesh LOCA segments, adaptive remesh decisions, and fixed-parameter restart corrections, while the shared driver owns segment lifecycle states, accepted-point remesh boundaries, deterministic `h+r`/`pure-r` retry orders, tangent renormalization/rebootstrap policy recording, event partitioning, checkpoint manifests, runtime/resource counters, and normalized failure-policy diagnostic channels.

Run directories contain an atomic `manifest.json` plus per-segment `checkpoints/<segment>/checkpoint.json` files. Resume validates schema, source hashes, executable identity, vector fingerprints, configuration fingerprints, and target-manifest fingerprints before any completed segment can be reused; incompatible or stale state raises `StaleCheckpointError` instead of silently mixing artifacts. Focused tests use the included scripted backend to verify interruption/resume, stale rejection, event accounting, remesh rebuild identity, deterministic retry ordering, pure-r paths, failed h+r restarts with preserved reasons, cap/alias/Radau/single-valued tripwire diagnostics, and fixed-mesh no-remesh behavior. The single-valued tripwire follows the documented v1 policy: stop slice automation on active-coordinate tangent sign changes, normalized-coordinate reversals above `1e-4`, or duplicate normalized coordinates with incompatible period/orbit evidence.

## Provisional adaptive spine-and-slices run

[`scripts/generate_native_adaptive_spine_slices_run.py`](scripts/generate_native_adaptive_spine_slices_run.py) executes the complete TASK-068.03 provisional target manifest through the generalized driver using curated native fixed-mesh and one-branch remesh/restart evidence. The output run directory is [`outputs/native_adaptive_spine_slices_run/`](outputs/native_adaptive_spine_slices_run/) with a resumable driver `manifest.json` and one checkpoint per completed segment; [`outputs/native_adaptive_spine_slices_run.json`](outputs/native_adaptive_spine_slices_run.json) is the deterministic summary.

Regenerate or verify with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_spine_slices_run.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_spine_slices_run.py --check
```

The provisional manifest covers the exact `T=225 K` move to the spine, both temperature directions over the `210--226 K` skeleton, exact `T=210 K` and `T=225 K` anchors, and signed `rho = +/-0.15` slices for every skeleton temperature. It records six accepted targets from existing native fixed-mesh/restart evidence and twenty-five explicit failed terminal targets with reasons. Accepted native points pass residual, phase, positivity, period, linear, and independent Python same-coordinate gates; the selected `T=210 K` remesh restart also passes residual, phase, finite-change, KLU2/linear, and tangent gates. The deterministic summary records that every segment has cap-escalation, aliasing, Radau-trigger, single-valued-tripwire, rejection-reason, and TASK-068 `not_evaluated` IVP/Floquet diagnostic channels, so failed targets and unresolved evidence cannot disappear behind later successful retries. Near-Hopf approach points are not reached in this provisional run, so amplitude/period/coordinate evidence remains empty with the five-reliable-point target and fit/connection policy deferred to TASK-069.

This artifact is intentionally not a production C++ adaptive-backend run and does not relabel Python or fixed-mesh evidence as full native adaptive completion.

## Independent Python validation of native adaptive points

[`scripts/generate_native_adaptive_python_validation.py`](scripts/generate_native_adaptive_python_validation.py) freezes the TASK-068.04 same-coordinate validation ledger for accepted provisional native adaptive points:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_python_validation.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_python_validation.py --check
```

[`outputs/native_adaptive_python_validation.json`](outputs/native_adaptive_python_validation.json) deterministically selects the unique accepted native points from the provisional driver across branch starts/midpoints/finals, spine/slice/anchor contexts, and the accepted pre-remesh boundary. Near-Hopf approach points are explicitly absent because the provisional run did not reach them. Each selected point records the independent Python same-coordinate correction contract, seed provenance, period relative error, weighted orbit distance, residual/phase/positivity/linear gates, mesh comparison, tolerance version, native vector fingerprint, and source fingerprints. [`outputs/native_adaptive_python_validation_vectors.npz`](outputs/native_adaptive_python_validation_vectors.npz) stores only selected native recorder vectors for checksum/provenance; those vectors are not used as Python correction seeds.

All 32 selected fixed-mesh native points pass the versioned `2e-7` period and weighted-orbit tolerances by a wide margin (maximum observed errors approximately `1.58e-12` and `2.84e-12`). The post-remesh restart point is recorded separately as native C++ NOX/KLU2 restart evidence without relabeling it as independent Python validation. This artifact is a TASK-068 evidence-ledger supplement for TASK-069 review, not a claim that failed provisional targets have become native adaptive successes.

## TASK-068 final native adaptive evidence reconciliation

[`scripts/generate_native_adaptive_final_reconciliation.py`](scripts/generate_native_adaptive_final_reconciliation.py) creates the final TASK-068 sink manifest:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_final_reconciliation.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_final_reconciliation.py --check
```

[`outputs/native_adaptive_final_reconciliation.json`](outputs/native_adaptive_final_reconciliation.json) reconciles the structural remesh/restart manifest, restart smoke, one-branch integrated remesh, provisional spine-and-slices run manifest and checkpoints, independent Python validation, vector artifacts, source fingerprints, terminal target ledger, resume state, and parent TASK-068 acceptance-criteria review. It is a sink artifact, so upstream manifests do not reference it and the provenance graph remains acyclic.

The final evidence remains intentionally bounded. The provisional target ledger covers the `T=225 K` move to the spine, both temperature directions over the `210--226 K` skeleton, exact `T=210 K` and `T=225 K` anchors, and signed `rho = +/-0.15` slices for every skeleton temperature. Six targets are accepted and twenty-five retain explicit failed terminal statuses with reasons. Adaptive reference meshes converge below the `1e-4` defect gate, accepted native points/restarts pass the recorded residual/phase/positivity/linear/restart gates, and all selected same-coordinate Python validations pass their `2e-7` tolerances. Near-Hopf approach points are not reached; amplitude/period/coordinate diagnostics, fit/connection policy, production runtime profiling, broader IVP checks, and Floquet-dependent evidence remain TASK-069 scope.

## TASK-062 higher-order/adaptive design

TASK-062 reviewed the completed midpoint evidence before selecting the next numerical stage. TASK-056 showed that tiny discrete residuals do not imply period accuracy: the canonical `N=64` midpoint period is more than 12% above the Episode 007 reference, while refinement reduces the discrepancy substantially. TASK-057 through TASK-061 then established transparent Python continuation, sparse Tpetra/NOX correction, and genuine native LOCA ownership with close Python/C++ parity. The remaining problem is therefore orbit resolution, not continuation ownership.

The initial higher-order/adaptive contract uses globally fixed three-stage Gauss--Legendre collocation with external `h/r` remesh-and-restart adaptation. Two-stage Gauss supplies an order check. Independent defect on both next-higher Gauss and staggered dyadic check grids controls acceptance and `h` marking; a bounded defect/speed/curvature/nucleation monitor controls only `r` redistribution. V1 includes explicit movement, split, mesh-budget, restart, phase-refresh, and near-Hopf diagnostic thresholds. These constants are operational hypotheses for an informative run, not prematurely frozen production policy. Floquet postprocessing and its associated gates are not implemented or evaluated through TASK-068; they remain downstream design direction for TASK-069. Coarsening, local `hp`, explicit landmark snapping, Radau, and iterative solvers remain evidence-triggered.

The next stage is deliberately continuation-first:

1. TASK-064 qualifies Python higher-order fixed-mesh orbits;
2. TASK-065 establishes C++ sparse higher-order correction/parity;
3. TASK-066 continues the higher-order fixed-mesh branches with native LOCA;
4. TASK-067 implements the Python `h/r` adaptation reference;
5. TASK-068 implements and runs native adaptive LOCA with structural remesh restarts; and
6. TASK-069 reviews the resulting convergence, meshes, continuation coverage, failures, and cost before defining downstream production tasks.

TASK-063 paper digitization is independent external comparison evidence. It does not block implementing or running continuation and must not be used to tune or accept the numerical method.

See [`docs/collocation-phase-decisions.md`](docs/collocation-phase-decisions.md) for the full v1 contract, thresholds, and deferred decisions.

## TASK-069 evidence-review outcome

The post-run review concludes that Episode 008 has strong formulation, fixed-mesh native LOCA, Python adaptive, nonuniform parity, and remesh/restart-seam evidence, but it is not yet final Figure 5 production data. Fixed-uniform meshes remain diagnostic only; Python h/r adaptive qualification converges at the four required points; one native remesh/restart boundary and 32 native fixed-mesh points pass the recorded gates/parity checks. The provisional native adaptive target ledger still contains six accepted targets and twenty-five explicit failed/pending targets, runtime/resource fields are placeholders, TASK-063 digitization is unavailable, and no near-Hopf approach points were reached. The documented quadratic/quartic Hopf fits are therefore not supported yet; unresolved regions must remain explicit gaps rather than interpolated values.

See [`docs/task069-evidence-review-and-next-stage-design.md`](docs/task069-evidence-review-and-next-stage-design.md) for the disposition matrix and downstream task graph.

## Scope boundary

The episode will produce a schema-versioned browser-consumable Figure 5 dataset, but integrating that dataset into the Episode 007 web widget is deferred to follow-up work. TASK-069 now freezes the next-stage boundary: production schemas, profiling, measured native adaptive pilot/full-domain runs, T=210 K linearized periods, Floquet/IVP validation, interpolation, and final paper/browser artifacts must proceed through downstream tasks that depend on TASK-069.
