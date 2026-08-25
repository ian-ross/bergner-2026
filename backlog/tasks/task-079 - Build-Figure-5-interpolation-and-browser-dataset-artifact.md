---
id: TASK-079
title: Build Figure 5 interpolation and browser dataset artifact
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 13:45'
labels:
  - episode-008
  - interpolation
  - browser
dependencies:
  - TASK-069
  - TASK-070
  - TASK-074
  - TASK-075
  - TASK-076
  - TASK-077
  - TASK-078
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Construct the schema-valid display/interpolation layer from authoritative production continuation, Hopf-limit, linearized-period, Floquet, and validation evidence.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Shape-preserving interpolation of log(P) passes documented along-slice and withheld-slice holdout gates or records invalid/gap regions; no interpolation crosses Hopf boundaries, unresolved targets, instability checkpoints, or multivalued tripwires
- [x] #2 The browser dataset distinguishes solved, interpolated, Hopf-limit, image-derived comparison, invalid, and gap values with links to authoritative records and units/coordinate provenance
- [x] #3 The lower-panel data use authoritative T=210 K nonlinear continuation records and the independent linearized-period curve, not heatmap resampling
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reconfirm dependency state and input artifacts: TASK-069/070/074/075/076/077/078 are Done, TASK-063 is still To Do, and the current upstream --check commands pass. Freeze the exact production-v1 continuation points/events/run metadata/orbit manifest, near-Hopf policy records, T=210 K linearized-period curve, Floquet diagnostics, IVP validation, schema contract, README/doc hashes, and source/provenance rules before deriving display data.
2. Define the interpolation safety topology from authoritative records only: accepted native nonlinear points, explicit unresolved/gap terminals, Hopf-limit policy records, Floquet instability/ambiguity diagnostics, IVP validation outcomes, and coordinate-domain/Hopf-boundary geometry. Split candidate data into connected safe segments and mark regions blocked by Hopf boundaries, unresolved targets, instability checkpoints, tripwire/near-Hopf stops, multivalued evidence, or missing production solves.
3. Implement a reproducible Episode 008 browser/interpolation generator that uses shape-preserving log(P) interpolation only within safe connected segments with enough accepted nonlinear production points. Run along-slice and between/withheld-slice holdout gates when prerequisites exist; otherwise record interpolation as not_evaluated and emit explicit gap/invalid records rather than fabricating values. With the current ledger, expect the nonlinear map to contain the solved spine-210K record and explicit gaps/no interpolation for unresolved regions.
4. Assemble a production-v1 browser-display dataset artifact that separates record roles and source flags for solved native nonlinear values, validated interpolated values if any, Hopf-limit explicit-gap records, T=210 K linearized-period lower-panel values, invalid outside-Hopf-domain values, unresolved/gap values, and the image-derived comparison channel. Because TASK-063 is not complete, do not invent digitized comparison samples; encode comparison availability/pending status so TASK-080 can attach actual external-comparison overlays after TASK-063.
5. Add authoritative links, units, and coordinate provenance to every browser record: continuation point/event/orbit references, linearized-period row IDs, near-Hopf policy IDs, Floquet/IVP diagnostic links, schema/method versions, source checksums, display quantity definitions, and explicit lower-panel provenance showing nonlinear continuation vs independent linearized-period sources rather than heatmap resampling.
6. Document the interpolation gates, no-crossing rules, current gap/no-interpolation outcome, browser dataset structure, image-derived comparison policy, and validation commands in Episode 008 docs/README. Add focused pytest coverage for schema validity, source/validity distinctions, no interpolation across gaps/Hopf/instability/unresolved records, holdout prerequisite behavior, lower-panel source separation, invalid-domain records, and checksum/provenance stability.
7. Run the new generator in write and --check modes, the production artifact validator, upstream dependency checks, focused Episode 008 tests, full pytest as feasible, and git diff --check; then update TASK-079 acceptance criteria, implementation notes, final summary, and status through the Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-079: moved task to In Progress, assigned to @iross, reviewed task dependencies and Episode 008 production docs/artifacts. Confirmed upstream check commands pass for TASK-075 full-domain, TASK-076 near-Hopf policy, TASK-077 Floquet diagnostics, TASK-078 IVP validation, and TASK-074 T=210 K linearized period curve. No implementation changes have been made yet; pausing for plan confirmation.

Plan approved by user; proceeding with TASK-079 browser/interpolation generator, documentation, tests, and validation.

Implemented TASK-079 browser/interpolation artifact. Added `generate_figure5_browser_interpolation_dataset.py`, `outputs/figure5_browser_interpolation_dataset.json`, documentation, README linkage, and focused tests. Current authoritative nonlinear evidence has one accepted native point (`spine-210K`) and 297 unresolved targets, so the generator records no nonlinear interpolation, not_evaluated along-slice/withheld-slice holdout gates, explicit unresolved gaps, Hopf-limit explicit gaps, invalid outside-Hopf-domain mask records, and pending TASK-063 image-derived comparison placeholders rather than fabricated digitized values.

A read-only scientific/code audit found an initial stability/IVP summary parsing bug in the TASK-079 artifact (`null` IVP failure ID). Fixed `stability_review()` to read the current TASK-077/TASK-078 nested schemas and regenerated the artifact; it now records no ambiguous/unstable Floquet targets and no IVP failures.

Updated Episode 008 README/docs and regenerated README/source-hash-dependent upstream artifacts (TASK-071/TASK-072/TASK-073/TASK-081/TASK-075/TASK-076/TASK-077/TASK-078/final reconciliation) so existing check commands remain current.

Validation run:
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_figure5_browser_interpolation_dataset.py --check`: current
- production validator for `figure5_browser_interpolation_dataset.json`: valid
- focused TASK-079 tests: 6 passed
- focused source-hash-dependent Episode 008 regression set: 80 passed
- final reconciliation `--check`: passed
- full `uv run pytest -q`: 394 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed
<!-- SECTION:NOTES:END -->
