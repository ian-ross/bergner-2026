# TASK-076 near-Hopf approach evidence and gap policy

TASK-076 reviews near-Hopf approach evidence from production native adaptive records only. It does not use fixed-mesh diagnostics, Python-only substitutions, interpolation, or digitized paper data to create Hopf-boundary regular-orbit values.

## Artifacts

- `outputs/native_adaptive_near_hopf_review.json` — TASK-076 side-by-side evidence review, terminal-status ledger, fit-gating decision, Episode 006 Hopf-period references, and connection/gap policy.
- `outputs/native_adaptive_near_hopf_policy_records.json` — production-v1 browser/display records encoding the lower and upper T=210 K Hopf-limit connections as explicit gaps.

## Evidence under review

The only currently accepted full-domain native adaptive periodic orbit is `spine-210K`. TASK-075 records every other full-domain target as an explicit `resolution_unresolved` policy gap rather than a claimed native C++ solve. TASK-076 therefore reviews the two reachable sides from the accepted T=210 K spine point:

- `lower_hopf_T210K`: decreasing `rho` from `0` toward the lower Hopf locus at `rho=-1`;
- `upper_hopf_T210K`: increasing `rho` from `0` toward the upper Hopf locus at `rho=+1`.

For each side, the requested T=210 K targets at `rho=+/-0.25`, `+/-0.50`, `+/-0.75`, `+/-0.90`, and `+/-0.97` remain `resolution_unresolved`. The nearest requested targets to the Hopf boundaries, `slice-210K-rho--0.97` and `slice-210K-rho-+0.97`, are unresolved policy gaps.

## Fit prerequisite and result

Quadratic and quartic fits of

```text
P = P0 + c2 A^2
P = P0 + c2 A^2 + c4 A^4
```

are permitted only for a Hopf side with at least five reliable monotone accepted approach points, each carrying finite amplitude, period, coordinates, diagnostics, and terminal status. Neither side meets that prerequisite: there are zero reliable near-Hopf approach points. Therefore TASK-076 performs no quadratic or quartic fits, no leave-one-out intercept checks, no residual checks, and no Episode 006 Hopf-period intercept comparison.

Episode 006 native LOCA Hopf periods at T=210 K are retained in the review artifact as reference values for a future fit-intercept comparison only. They are not used to invent nonlinear regular-orbit periods at the Hopf boundary.

## Connection/gap policy

Both reviewed sides are encoded as explicit gaps in the production-v1 policy records. The records use `validity.status = gap`, `validity.source = explicit_gap`, `authoritative = false`, and a null display period. No regular-orbit amplitude or period is fabricated at either Hopf boundary.

## Validation commands

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_near_hopf_review.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_near_hopf_policy_records.json
uv run pytest tests/test_episode8_native_adaptive_near_hopf_review.py -q
```
