# TASK-072 measured native adaptive pilot

TASK-072 executes the current measured native adaptive pilot over the TASK-068 provisional 210--226 K spine-and-slices skeleton. It is a pilot gate before TASK-073 validation and later full-domain work, not final Figure 5 production.

## Artifacts and commands

Pilot summary and resumable driver run:

- [`../outputs/native_adaptive_measured_pilot.json`](../outputs/native_adaptive_measured_pilot.json)
- [`../outputs/native_adaptive_measured_pilot/manifest.json`](../outputs/native_adaptive_measured_pilot/manifest.json)

Production-v1 companion artifacts:

- [`../outputs/native_adaptive_measured_pilot_events.json`](../outputs/native_adaptive_measured_pilot_events.json)
- [`../outputs/native_adaptive_measured_pilot_run_metadata.json`](../outputs/native_adaptive_measured_pilot_run_metadata.json)

Regenerate with the current native executable:

```bash
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py
```

Check committed artifacts without re-measuring timing:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_run_metadata.json
```

## Terminal target outcome

The pilot covers all 31 TASK-068 skeleton targets and records exactly one backend-emitted terminal status with a reason for each target:

| Status | Count | Meaning |
| --- | ---: | --- |
| `accepted` | 0 | no target has the complete exact native restart-vector gate bundle required for TASK-072 acceptance |
| `resolution_unresolved` | 31 | explicit unresolved/gap records with backend reasons |
| `near_hopf_stop` | 0 | not reached in this pilot |
| `tripwire_stop` | 0 | no single-valued tripwire stop in this pilot |
| `failed` | 0 | no hard backend failure after unresolved statuses are preserved |

This intentionally revises the TASK-068 provisional six-accepted/twenty-five-failed ledger. The fixed-mesh-only native checkpoints and the measured `spine-210K` native remesh/restart seam remain input evidence, but they are **not** relabeled as TASK-072 adaptive pilot acceptances. The exact accepted restart vector does not yet have a backend-bound independent defect and period/orbit convergence gate bundle, so `spine-210K` also remains `resolution_unresolved`.

## Gate bundle policy

TASK-072 acceptance requires a complete bundle on the exact native target evidence:

- residual
- phase
- positivity
- finite change
- tangent
- KLU2 linear solve
- independent defect
- period/orbit convergence

The measured `spine-210K` seam records native remesh/restart residual, phase, positivity, finite-change, tangent, and KLU2 linear-solve evidence plus rebuilt graph/state identity and corrected restart vector checksum. It is still unresolved because the independent defect and period/orbit convergence gates are not bound to the exact native restart vector in this pilot. No target is accepted by borrowing fixed-mesh-only or Python-only convergence evidence.

## Resource and resumability policy

The pilot records measured wall-clock time, CPU time, and max RSS from measured native check commands plus driver resource accounting. It records native executable SHA-256, compiled source fingerprints, platform/Python/lockfile identity, run-manifest fingerprint, and checkpoint SHA-256 values.

Resume/checkpoint reuse is guarded by `NativeAdaptiveDriver`: schema, source, executable, vector, configuration, target-manifest, fingerprint, and checkpoint segment hashes must match before completed checkpoint reuse. Stale or incompatible checkpoint state must be rejected rather than silently reused.

## Gap and interpolation policy

No interpolation is used in TASK-072. All records are `resolution_unresolved` with explicit reasons and `unresolved_native_adaptive` source flags in the production-v1 event artifact. These records are non-authoritative gap evidence for downstream review; they are not display interpolation, Python substitutions, fixed-mesh relabeling, or digitized-paper comparisons.
