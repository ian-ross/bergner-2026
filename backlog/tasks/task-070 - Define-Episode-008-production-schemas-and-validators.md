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
