# Episode 008 production schemas and validators

TASK-070 defines the formal `episode8-figure5-production-v1` boundary approved by the TASK-069 review. These schemas are a gate for downstream authoritative Figure 5 production artifacts; they do not create new production continuation data.

## Contract files and commands

The machine-readable contract is:

- [`../schemas/episode8-figure5-production-v1.contract.json`](../schemas/episode8-figure5-production-v1.contract.json)

The reusable validator is implemented in:

- [`../../../src/bergner_spichtinger_2026/episode8_production_schema.py`](../../../src/bergner_spichtinger_2026/episode8_production_schema.py)

Validate future production JSON artifacts or print the contract with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/<artifact>.json
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py --print-contract
```

By default the validator verifies recorded SHA-256 checksums for provenance inputs and curated NPZ files relative to the repository root. Use `--no-checksums` only for schema-shape debugging, not for accepting production artifacts.

## Artifact kinds covered

All production-v1 JSON artifacts must use `schema_version: episode8-figure5-production-v1`, carry method/schema versions, use the frozen coordinate conventions, include non-empty provenance with source paths and SHA-256 digests, and preserve `digitized_paper_data_policy: external-comparison-only`.

The approved artifact kinds are:

| Artifact kind | Payload key | Purpose |
| --- | --- | --- |
| `continuation-points` | `continuation_points` | Authoritative solved or explicitly terminal periodic-orbit continuation records, including coordinates, nonlinear period in seconds, validity/source flags, method versions, diagnostics, and orbit-vector references. |
| `continuation-events` | `continuation_events` | Accepted/rejected step, bootstrap, phase-refresh, remesh/restart, near-Hopf, tripwire, gap, and interpolation events with coordinates and unambiguous status/source flags. |
| `run-metadata` | `run_metadata` | Native adaptive run identity, coordinate domain, terminal-status counts, executable/build identity, and measured resource accounting with `s` and `KiB` units. |
| `curated-orbit-npz-manifest` | `orbit_vector_manifest` | Manifest for retained periodic-orbit vector NPZ files, including NPZ SHA-256, float64 little-endian array schemas, shapes, roles, units, and coordinate conventions. |
| `linearized-period-curve` | `linearized_period_rows` | T = 210 K equilibrium-linearized rows for the lower Figure 5 panel, including `2*pi/Im(lambda)` period in seconds, eigenvalue imaginary part in `rad s^-1`, and explicit null-period gap/invalid rows when no genuine complex pair is available. |
| `browser-display-dataset` | `browser_records` | Browser/display records derived from authoritative solved points, validated interpolation, explicit gaps, invalid-domain records, Hopf-limit display records, or non-authoritative external comparison overlays. |

## Coordinate, state, unit, and version conventions

Production-v1 artifacts must declare the following conventions exactly:

```text
parameter_coordinates = temperature-log_w-rho-spine-slices-v1
orbit_state           = transformed-state-log_n-log_q-s-v1
phase                 = normalized-phase-theta-in-[0,1]-periodic-v1
period                = physical-period-seconds-logP-internal-v1
```

Per-record coordinates are represented by quantities with explicit units:

- temperature: `K`
- vertical velocity `w`: `m s^-1`
- `log_w`: `ln(m s^-1)`
- `rho` and `temperature_hat`: `dimensionless`
- periods and wall/cpu time: `s`
- eigenvalue imaginary part: `rad s^-1`
- memory: `KiB`

The period reported to paper/browser consumers is the physical period in seconds. `log(P)` remains an internal continuation unknown and may appear only as an auxiliary logged value.

## Validity/source flag policy

Each record must carry exactly one `validity.status` and exactly one compatible `validity.source`. Lists such as `sources: [...]` are rejected because they make unresolved/gap/interpolated records ambiguous.

Key compatibility rules include:

- `accepted` records may come only from `computed_native_adaptive` or `computed_linearized_equilibrium`.
- `resolution_unresolved` records must use `unresolved_native_adaptive` and include a reason.
- `gap` records must use `explicit_gap`, be non-authoritative, and include a reason.
- `interpolated` browser records must use `interpolated_holdout_validated` and include interpolation provenance plus passed holdout validation.
- `external_comparison` records must use `external_digitized_paper_comparison`, be non-authoritative, and be display overlays only.
- `linearized-period-curve` rows may carry null period/frequency only with non-accepted gap/invalid/unresolved validity and an explicit reason; accepted linearized-equilibrium rows require positive finite period and positive finite imaginary frequency.

The validator rejects schema-version mismatches, missing provenance, checksum drift, incompatible coordinate/unit fields, ambiguous source lists, status/source mismatches, and interpolated records without holdout/source-point provenance.

## Relationship to TASK-069 and digitized paper data

TASK-069 concluded that the native adaptive approach is promising but not yet final-production sufficient. It also forbids filling the 25 pending/failed provisional targets with undocumented interpolation and states that TASK-063 digitized Figure 5 pixels, when available, are image-derived external comparison evidence only.

This schema boundary implements those decisions: production artifacts must distinguish accepted computed data, unresolved native-adaptive outcomes, explicit gaps, validated interpolation, invalid-domain records, not-evaluated evidence, and non-authoritative digitized-paper overlays. Digitized paper data can help compare a final plot, but they must not override convergence, defect, Python/native parity, IVP/Floquet diagnostics, or native adaptive terminal statuses.
