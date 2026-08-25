# TASK-078 stratified independent IVP validation

TASK-078 validates accepted native production periodic orbits using independent initial-value integrations. The validation artifact is deliberately conservative: category selection is performed over the TASK-075 production ledger, but only schema-valid accepted native production orbits are integrated. Unresolved targets, Hopf-limit policy records, interpolation, qualification-only records, and digitized-paper evidence are recorded as unavailable strata rather than promoted to regular production orbits.

## Artifact

- `outputs/native_adaptive_ivp_validation.json` — twelve-category stratification ledger, deduplicated accepted production IVP validation set, DOP853 one-period return and phase-aligned trajectory checks, Radau agreement checks for available headline points, perturbed-equilibrium attractor screening, provenance, and independence policy.

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_ivp_validation.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json
uv run pytest tests/test_episode8_native_adaptive_ivp_validation.py -q
```

## Current stratification result

The documented TASK-078 category ledger contains twelve categories: qualification-point lineage, both T=210 K Hopf sides where available, low/high-temperature interiors, largest/shortest accepted periods, worst accepted defect, worst Floquet trivial multiplier, worst interpolation holdout, canonical spine anchor, and remesh/restart boundary coverage.

Current TASK-075 production evidence has exactly one accepted native orbit, `spine-210K`. After category deduplication the selected IVP validation set therefore contains one unique accepted point. Categories requiring accepted near-Hopf, low/high-temperature interior, or holdout-interpolation evidence remain explicit unavailable strata because those targets are TASK-075 `resolution_unresolved` gaps or `not_evaluated` holdout records.

## IVP checks

For every selected accepted point, the generator loads the saved native Gauss collocation orbit only as a read-only validation target. It integrates the transformed ODE from the native orbit initial state with DOP853, compares the one-period return at the native period, locates the closest return in a small period window, and samples the dense IVP solution against the native collocation polynomial over normalized phase. The documented gates are:

- period relative error `<= 1e-5`;
- scaled one-period return norm and max `<= 1e-5`;
- phase-aligned weighted trajectory RMS and max `<= 1e-5`.

The current `spine-210K` DOP853 validation passes all gates.

## Radau and perturbed-equilibrium screening

The hardest/headline selection requests six unique accepted production points. With the current production ledger, only `spine-210K` is available, so Radau agreement is run for that point and the artifact records that production evidence is insufficient for six unique headline points.

The perturbed-equilibrium attractor screen requests four unique headline points when available. Because the current accepted set has one unique point, the artifact records insufficient production evidence for four unique points. It still runs deterministic perturbed-equilibrium trials for the available accepted point and records pass/failure reasons without suppressing nonconvergence or unregularized-RHS failures.

## Independence boundary

TASK-078 is independent validation evidence only. It does not tune or overwrite native continuation periods, and it does not re-fit or relabel accepted/unresolved statuses. IVP failures would remain validation failures or explicit reasons; unavailable production strata remain unavailable until native continuation produces schema-valid accepted points.
