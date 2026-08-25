---
id: TASK-079
title: Build Figure 5 interpolation and browser dataset artifact
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 13:21'
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
- [ ] #1 Shape-preserving interpolation of log(P) passes documented along-slice and withheld-slice holdout gates or records invalid/gap regions; no interpolation crosses Hopf boundaries, unresolved targets, instability checkpoints, or multivalued tripwires
- [ ] #2 The browser dataset distinguishes solved, interpolated, Hopf-limit, image-derived comparison, invalid, and gap values with links to authoritative records and units/coordinate provenance
- [ ] #3 The lower-panel data use authoritative T=210 K nonlinear continuation records and the independent linearized-period curve, not heatmap resampling
<!-- AC:END -->
