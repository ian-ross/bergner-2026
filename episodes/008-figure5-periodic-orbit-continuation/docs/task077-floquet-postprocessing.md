# TASK-077 Floquet postprocessing diagnostics

TASK-077 computes Floquet multipliers from saved native adaptive production collocation orbits as **postprocessing diagnostics only**. The multipliers are not nonlinear unknowns, are not TASK-068 acceptance evidence, and are not acceptance gates for the TASK-075 continuation ledger.

## Artifacts

- `outputs/native_adaptive_floquet_diagnostics.json` — DOP853 tolerance-ladder variational integrations, implicit Radau comparisons, multiplier classifications, continuation-record links, and non-orbit policy records for schema-valid accepted production points.

Check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_floquet_diagnostics.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json
```

## Current production scope

The TASK-075 full-domain ledger currently has exactly one schema-valid accepted native adaptive production orbit: `spine-210K`. TASK-077 processes that saved native three-stage Gauss collocation polynomial from `native_adaptive_full_domain_orbits.npz` and links the diagnostic row back to:

- continuation point `task075-point-spine-210K`;
- terminal event `task075-terminal-spine-210K`;
- curated orbit manifest `native_adaptive_full_domain_orbit_manifest.json`;
- source restart-vector checksum `795cd6ea64e3de0e5c47803ac98f0d3f38ab0b9fc15eab467c1e6e0ac12a85c9`.

The other `297` TASK-075 requested targets remain explicit `resolution_unresolved` policy gaps. Hopf-limit records from TASK-076 remain gap/display-policy records, not regular periodic orbits. No failed, unresolved, interpolated, digitized-paper, or Hopf-limit equilibrium record is relabeled for Floquet processing.

## Numerical method

For each accepted orbit, the generator evaluates the native piecewise collocation polynomial `x_collocation(theta)` in transformed coordinates and integrates the autonomous variational equation over normalized phase:

```text
dPhi/dtheta = P * Dg(x_collocation(theta)) * Phi,    Phi(0) = I,    theta in [0, 1].
```

The DOP853 tolerance ladder records coarse, production, and refined solves. The production monodromy matrix is eigendecomposed into one autonomous trivial multiplier near `+1` and the two nontrivial multipliers. Stability classifications are recorded even when ambiguous or unstable; they are never filtered out for display convenience.

Implicit Radau is run for the current canonical accepted production point as a headline/stiff comparison and trivial-unit-multiplier consistency check. The artifact also records that no schema-valid accepted near-Hopf/long-period approach point and no suspected nontrivial unit-circle crossing candidate currently exists; those strata remain explicit `not_available` records rather than invented comparisons.
