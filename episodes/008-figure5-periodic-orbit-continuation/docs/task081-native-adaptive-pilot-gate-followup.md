# TASK-081 native adaptive pilot gate follow-up

TASK-081 resolves the TASK-073 blocker for the measured native adaptive pilot gate. It does not rewrite TASK-072 or TASK-073 history; it adds a follow-up gate artifact that binds the exact post-remesh native restart vector to the missing defect/convergence gates and then revises the 210--226 K skeleton ledger.

## Artifacts and commands

Follow-up artifacts:

- [`../outputs/native_adaptive_pilot_gate_followup.json`](../outputs/native_adaptive_pilot_gate_followup.json)
- [`../outputs/native_adaptive_pilot_gate_followup_events.json`](../outputs/native_adaptive_pilot_gate_followup_events.json)
- [`../outputs/native_adaptive_pilot_gate_followup_run_metadata.json`](../outputs/native_adaptive_pilot_gate_followup_run_metadata.json)
- [`../outputs/native_adaptive_pilot_gate_followup_exact_restart_fixture.txt`](../outputs/native_adaptive_pilot_gate_followup_exact_restart_fixture.txt)

Regenerate or check with:

```bash
BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit \
  uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_gate_followup.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_gate_followup.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_events.json \
  episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_run_metadata.json
```

## Gate result

TASK-081 accepts exactly one pilot target: `spine-210K`. The revised ledger is emitted by the TASK-081 native exact-restart gate backend and is `accepted=1`, `resolution_unresolved=30`, `failed=0`, `near_hopf_stop=0`, and `tripwire_stop=0`.

The accepted point is the exact native post-remesh restart vector `restart__adaptive-guard-rho-0-g3-n32__corrected_solution` with SHA-256 `795cd6ea64e3de0e5c47803ac98f0d3f38ab0b9fc15eab467c1e6e0ac12a85c9`. The generator invokes the native `adaptive-restart` seam on the recorded adaptive fixture and verifies that the backend-emitted restart solution matches that exact vector. It also writes an exact C++ fixture for the restart vector and invokes the native `adaptive-controller` seam to bind the independent defect gate to the native restart vector itself. Residual, phase, positivity, finite-change, tangent, and KLU2 linear gates come from native restart correction evidence; period/orbit convergence is bound to native restart correction norm, native transferred-seed period change, and weighted orbit change from the transferred seed.

## Independent validation

The accepted `spine-210K` target has same-coordinate Python validation on the exact restart mesh. The Python correction is seeded from the transferred non-solution seed, not from the exact native corrected restart vector, and passes period and weighted-orbit parity.

The accepted point also receives a DOP853 one-period IVP validation. Radau is not required for this point because no near-Hopf, event ambiguity, nonphysical, mesh-cap stagnation, or DOP853 failure trigger is present. The scaled one-period return norm is below the documented tolerance.

## Go/no-go decision

TASK-075 may proceed under the retained `external-gauss3-hr-adaptive-v1` method. No method-version revision is required now.

This authorization is narrow: it permits full-domain TASK-075 continuation to begin from a pilot gate with one accepted post-remesh native adaptive point. TASK-075 must still assign one recorded terminal status per requested target: native-backend-emitted for attempted/accepted solves, and explicit policy-gap status when no authorized route exists without crossing unresolved regions. It must preserve unresolved gaps and stop at Hopf, tripwire, instability, or unresolved boundaries. No interpolation, fixed-mesh relabeling, Python-only substitution, or digitized-paper evidence is used to fill the remaining 30 unresolved pilot targets.
