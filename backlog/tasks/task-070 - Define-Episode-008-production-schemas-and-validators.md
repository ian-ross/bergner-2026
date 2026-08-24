---
id: TASK-070
title: Define Episode 008 production schemas and validators
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 14:37'
labels:
  - episode-008
  - schemas
  - production
dependencies:
  - TASK-069
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define formal episode8-figure5-production-v1 schemas and validation commands for downstream authoritative continuation, event, metadata, orbit-vector, linearized-period, and browser/display artifacts. This task implements the schema boundary approved by TASK-069 before new production data are generated.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Schemas cover continuation points, continuation events, run metadata, curated orbit NPZ manifests, T=210 K linearized-period rows, and browser/display dataset records with units, coordinate conventions, validity/source flags, and method/schema versions
- [x] #2 Validation tooling rejects missing provenance, unresolved/gap/interpolated-source ambiguity, checksum drift, schema-version mismatch, and incompatible coordinate or unit fields
- [x] #3 Documentation links schemas to TASK-069 decisions and preserves digitized paper data as external comparison evidence only
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory TASK-069 decisions, existing Episode 008 artifact conventions, and test patterns to define the exact production-v1 artifact kinds and shared invariants before adding any production data.
2. Add a formal Episode 008 production schema/validator layer using only committed project dependencies: versioned schema constants, allowed artifact kinds, coordinate/unit conventions, source/validity flag enums, provenance/checksum rules, and artifact-kind-specific required fields for continuation points, events, run metadata, curated orbit NPZ manifests, T=210 K linearized-period rows, and browser/display dataset records.
3. Expose reproducible validation commands under the Episode 008 scripts directory so downstream tasks can validate individual JSON/NPZ-manifest artifacts and, where relevant, verify recorded SHA-256 checksums against files.
4. Add focused pytest coverage with passing minimal fixtures plus negative cases for missing provenance, ambiguous unresolved/gap/interpolated source flags, checksum drift, schema-version mismatch, and incompatible coordinate or unit fields.
5. Document the production-v1 schema boundary in Episode 008 docs/README, linking it back to TASK-069 decisions and explicitly preserving digitized paper Figure 5 data as external comparison evidence only, not authoritative production input.
6. Run the new focused tests, schema validation self-checks, relevant existing Episode 008 checks, and git diff --check; then update TASK-070 notes, acceptance criteria, final summary, and status through Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by user; proceeding with schema/validator implementation, tests, and documentation.

Implemented `episode8-figure5-production-v1` schema/validator boundary in `src/bergner_spichtinger_2026/episode8_production_schema.py`, exposed `scripts/validate_production_artifacts.py`, wrote the machine-readable contract under `episodes/008-figure5-periodic-orbit-continuation/schemas/`, documented the TASK-069 linkage, and added focused tests.

Validation run:
- `uv run pytest tests/test_episode8_production_schema.py tests/test_episode8_native_adaptive_final_reconciliation.py -q`: 20 passed
- `uv run pytest -q`: 334 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Defined the Episode 008 `episode8-figure5-production-v1` production schema and validation boundary before downstream production data generation.

Changes:
- Added `episode8_production_schema.py` with schema constants, contract generation, provenance/checksum validation, coordinate/unit checks, validity/source compatibility rules, and artifact-specific validators for continuation points/events, run metadata, curated orbit NPZ manifests, T=210 K linearized-period rows, and browser/display records.
- Added `validate_production_artifacts.py` plus the committed machine-readable contract `schemas/episode8-figure5-production-v1.contract.json`.
- Documented the TASK-069 schema boundary in Episode 008 docs/README, including the rule that digitized paper data remain non-authoritative external comparison evidence only.
- Added focused pytest coverage for valid minimal artifacts and required rejection modes: missing provenance, ambiguous gap/unresolved/interpolated sources, checksum drift, schema mismatch, and incompatible coordinate/unit fields.
- Regenerated the TASK-068 final reconciliation manifest after the Episode 008 README provenance hash changed.

Validation:
- `uv run pytest tests/test_episode8_production_schema.py tests/test_episode8_native_adaptive_final_reconciliation.py -q`: 20 passed
- `uv run pytest -q`: 334 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed
<!-- SECTION:FINAL_SUMMARY:END -->
