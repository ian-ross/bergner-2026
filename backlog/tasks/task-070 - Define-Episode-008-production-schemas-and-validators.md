---
id: TASK-070
title: Define Episode 008 production schemas and validators
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 14:21'
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
- [ ] #1 Schemas cover continuation points, continuation events, run metadata, curated orbit NPZ manifests, T=210 K linearized-period rows, and browser/display dataset records with units, coordinate conventions, validity/source flags, and method/schema versions
- [ ] #2 Validation tooling rejects missing provenance, unresolved/gap/interpolated-source ambiguity, checksum drift, schema-version mismatch, and incompatible coordinate or unit fields
- [ ] #3 Documentation links schemas to TASK-069 decisions and preserves digitized paper data as external comparison evidence only
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
