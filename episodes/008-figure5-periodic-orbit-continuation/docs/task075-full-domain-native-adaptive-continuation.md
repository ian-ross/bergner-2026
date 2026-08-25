# TASK-075 full-domain native adaptive continuation

TASK-075 starts only after the TASK-081 pilot gate authorizes full-domain work under the retained `external-gauss3-hr-adaptive-v1` method. The resulting artifacts are deliberately conservative: every requested Figure 5 target receives one terminal status, but only targets with a complete exact native adaptive gate bundle are accepted as authoritative production points.

## Artifacts

- `outputs/native_adaptive_full_domain_run.json` — TASK-075 summary, requested-target manifest, terminal ledger, accepted-gate summary, sampling-refinement ledger, measured resource accounting, provenance, and validation commands.
- `outputs/native_adaptive_full_domain_points.json` — production-v1 accepted continuation point records.
- `outputs/native_adaptive_full_domain_events.json` — production-v1 terminal event ledger for all requested targets.
- `outputs/native_adaptive_full_domain_run_metadata.json` — production-v1 run metadata and measured resource record.
- `outputs/native_adaptive_full_domain_orbit_manifest.json` and `outputs/native_adaptive_full_domain_orbits.npz` — restartable curated vectors for accepted orbits only.

## Requested target domain

The requested full-domain skeleton follows the documented provisional v1 Figure 5 policy:

- temperature domain `T = 190--240 K`;
- exact slices at `T = 190, 192, ..., 240 K` plus the exact `225 K` slice;
- the exact `225 K` spine-move anchor lineage;
- each slice requests `rho = 0, +/-0.25, +/-0.50, +/-0.75, +/-0.90, +/-0.97`;
- accepted-evidence refinement requests near the `spine-210K` accepted/unresolved interfaces are included as authoritative requested targets.

This yields `298` requested targets. Each target has exactly one terminal status in `native_adaptive_full_domain_run.json` and in the production-v1 event artifact. The accepted status is native-backend evidence inherited from TASK-081; unresolved statuses are explicit policy gap records where no authorized native route can solve the target without crossing existing gaps.

## Terminal ledger and acceptance gates

The current TASK-075 ledger records:

- `accepted=1`: `spine-210K`;
- `resolution_unresolved=297`;
- `failed=0`, `near_hopf_stop=0`, `tripwire_stop=0`.

The accepted `spine-210K` point is the exact TASK-081 native post-remesh restart vector. It passes the required production residual, phase, positivity, KLU2/linear, independent defect, period/orbit convergence, remesh/restart, restartability, and provenance gates. It also has same-coordinate Python correction and DOP853 one-period IVP validation from TASK-081.

All other requested targets remain explicit unresolved gaps. No interpolation, fixed-mesh relabeling, Python-only substitution, or digitized-paper evidence fills them.

## Sampling refinement

Holdout-driven sampling refinement is recorded on accepted data only. Because the current full-domain accepted set contains one point, along-slice and between-slice log-period holdout errors are `not_evaluated` rather than fabricated. Refinement-neighborhood target requests (`spine-208K`, `spine-212K`, `slice-210K-rho--0.25`, and `slice-210K-rho-+0.25`) are present in the terminal ledger, but each remains `resolution_unresolved` as a policy gap rather than a native C++ solve; no interpolation crosses Hopf boundaries, tripwires, instability checkpoints, or unresolved gaps.

## Validation commands

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_full_domain_run.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_run_metadata.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json
uv run pytest tests/test_episode8_native_adaptive_full_domain_run.py -q
```
