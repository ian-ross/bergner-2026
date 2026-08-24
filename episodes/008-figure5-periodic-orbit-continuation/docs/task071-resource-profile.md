# TASK-071 native adaptive resource profile

TASK-071 replaces the TASK-068 deterministic zero resource placeholders with measured cost evidence for the current native adaptive continuation seams. The measurements are **profiling evidence only**: they do not accept continuation points scientifically, do not hide failed or pending provisional targets, and do not turn the TASK-068 pilot ledger into final Figure 5 production data.

## Artifacts and commands

Measured profile artifact:

- [`../outputs/native_adaptive_resource_profile.json`](../outputs/native_adaptive_resource_profile.json)

Production-v1 run-metadata companion:

- [`../outputs/native_adaptive_resource_profile_run_metadata.json`](../outputs/native_adaptive_resource_profile_run_metadata.json)

Regenerate the measured profile with the current native executable:

```bash
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py
```

Check the committed artifacts without re-measuring timing:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_resource_profile_run_metadata.json
```

## Representative seams measured

The profile uses `/usr/bin/time` to record wall-clock time, user+system CPU time, and max RSS, and it extracts NOX/KLU2 counters from current native output/artifact seams:

| Segment | Source seam | Counter evidence |
| --- | --- | --- |
| `fixed-mesh-gauss3-n32-correction` | `bs2026_midpoint_orbit solve` on the canonical three-stage `N=32` fixture | NOX iterations plus KLU2 symbolic/numeric factorization and solve counts from line-oriented native output |
| `one-branch-remesh-restart` | `generate_native_adaptive_one_branch_segment.py --check` | h+r transfer/rebuild/restart correction counters from `native_adaptive_one_branch_segment.json` |
| `pilot-style-spine-slices-driver-check` | `generate_native_adaptive_spine_slices_run.py --check` | measured driver/checkpoint seam resources plus an explicit lower-bound aggregate from the fixed-mesh and remesh/restart NOX/KLU2 seams |

The pilot-style row deliberately ignores TASK-068 driver-internal placeholder resource fields and records that the production C++ full adaptive backend was not executed.

## KLU2 review outcome

The measured profile records positive non-placeholder wall/RSS values and completed KLU2 activity for all representative rows. The maximum measured RSS is below the documented 4 GiB iterative-solver trigger, and all measured KLU2 solves complete. The backend still does not expose factorization/solve timing splits, so the `30 s per nonlinear iteration` and `>70% runtime in linear algebra` trigger channels remain explicitly `not_evaluated` rather than inferred.

Decision: **serial KLU2 remains acceptable for the current native adaptive pilot seams**. TASK-071 does not justify Belos/Ifpack2 implementation; KLU2 remains the serial oracle/reference pending larger production profiling.
