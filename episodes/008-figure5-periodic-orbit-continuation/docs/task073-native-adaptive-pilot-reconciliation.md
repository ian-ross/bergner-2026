# TASK-073 native adaptive pilot reconciliation

TASK-073 reviews the measured TASK-072 native adaptive pilot before authorizing any broader Figure 5 continuation. It is a gate review, not a new period-surface artifact.

## Artifacts and commands

Reconciliation artifact:

- [`../outputs/native_adaptive_pilot_reconciliation.json`](../outputs/native_adaptive_pilot_reconciliation.json)

Regenerate or check it with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_reconciliation.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_reconciliation.py --check
```

The review also checks the TASK-072 pilot and production-v1 companion artifacts:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_measured_pilot_run_metadata.json
```

## Terminal outcome ledger

TASK-073 preserves the TASK-072 terminal statuses exactly. It does not turn unresolved, failed, fixed-mesh-only, Python-only, interpolated, or digitized-paper evidence into accepted native adaptive pilot points.

| Status | Count | TASK-073 interpretation |
| --- | ---: | --- |
| `accepted` | 0 | no target is available for production use or independent IVP validation |
| `resolution_unresolved` | 31 | all pilot targets remain explicit non-authoritative gaps with reasons |
| `failed` | 0 | no hard backend failures are introduced by this review |
| `near_hopf_stop` | 0 | no near-Hopf approach evidence or fit support is present |
| `tripwire_stop` | 0 | no single-valued tripwire stop is present |

The measured `spine-210K` remesh/restart seam remains important backend evidence, but it is not an accepted TASK-072 pilot point: the exact native restart vector lacks backend-bound independent defect and period/orbit convergence gates. Its validation-unavailable reason blocks production use.

## Independent Python validation review

Every accepted pilot point must have an independent same-coordinate Python correction or an explicit validation-unavailable reason that blocks production use. The current pilot has zero accepted points, so there is no accepted point to validate. The review still records the blocking policy for future accepted points and records `spine-210K` as `not_accepted_validation_unavailable_blocks_production_use`.

The earlier TASK-068 Python-validation artifact remains background evidence only. It validated provisional/fixed-mesh native points and must not be rebranded as same-coordinate validation of accepted TASK-072 native adaptive pilot points.

## IVP, DOP853, and Radau review

TASK-069 approved selected IVP validation only after accepted native adaptive production/pilot points exist. Because TASK-072 accepted no targets, TASK-073 selects no IVP subset.

When accepted pilot or production points exist later, the retained rule is:

- use DOP853 for regular accepted stratified points and headline/canonical checks without difficulty triggers;
- use Radau when DOP853 fails or is excessive, event locations are ambiguous, near-Hopf/long-period approach points are selected, persistent ringing or nonphysical diagnostics appear, mesh-cap stagnation occurs, or a defect-passing/Gauss-failing trigger is observed.

## Production gate decision

Full-domain native adaptive continuation is **not authorized** from this pilot gate.

The retained v1 method (`external-gauss3-hr-adaptive-v1`) is not falsified by the all-unresolved pilot. A method-version revision is not required now. However, TASK-081 is required before TASK-075 may be treated as production-authorized: complete the backend-bound exact restart-vector defect and period/orbit convergence gate bundle, rerun or revise the native adaptive pilot, and require accepted targets to pass independent Python/IVP validation or remain explicit gaps.

No interpolation, terminal-status relabeling, or digitized-paper comparison may fill the 210--226 K gaps.
