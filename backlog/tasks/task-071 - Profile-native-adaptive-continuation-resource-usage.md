---
id: TASK-071
title: Profile native adaptive continuation resource usage
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 14:56'
labels:
  - episode-008
  - profiling
  - numerics
dependencies:
  - TASK-069
  - TASK-070
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace TASK-068 deterministic zero resource placeholders with measured native adaptive continuation cost evidence. The profile must use the current native adaptive backend seams and production-schema metadata without interpreting cost measurements as scientific acceptance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Measured wall-clock time, CPU time, max RSS, nonlinear iterations, KLU2 symbolic/numeric factorization counts, linear solves, and source/build/runtime identities are recorded for representative fixed-mesh, remesh/restart, and pilot-style native adaptive segments
- [ ] #2 The review determines whether serial KLU2 remains acceptable or whether the documented iterative-solver trigger thresholds are met
- [ ] #3 Resource artifacts are reproducible or checkable and are linked from Episode 008 documentation without leaving placeholder values in production-policy decisions
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm the TASK-069/TASK-070 boundaries, then inspect the native adaptive driver, existing TASK-068 artifacts, C++ CLI seams, and production-v1 run-metadata schema so the profiling output records cost evidence only and does not promote cost as scientific acceptance.
2. Add a reproducible Episode 008 profiling artifact generator under the episode scripts directory. It will build or require the native executable identity, run representative current seams for fixed-mesh LOCA, remesh/restart, and pilot-style native adaptive segments, wrap each measured command/driver segment with wall-clock, CPU, and max-RSS measurement, and extract nonlinear-iteration plus KLU2 symbolic/numeric factorization and solve counters from existing native outputs.
3. Emit schema/versioned JSON artifacts under the Episode 008 outputs directory with source/build/runtime identities, command provenance, measured resource rows, aggregate run metadata compatible with TASK-070 production-v1 conventions, and an explicit policy field stating that profiling evidence is not a continuation-accuracy acceptance gate.
4. Implement the KLU2 review logic against the documented TASK-069/TASK-062 trigger policy: summarize serial KLU2 acceptability, total/max solves and factorization counts, elapsed/RSS bounds, and whether any iterative-solver threshold is met; keep unsupported iterative-solver work out of scope if triggers are not met.
5. Add focused tests/validator checks for non-placeholder positive wall/RSS measurements, nonnegative CPU time, required nonlinear/KLU2 counters, source/build identity coverage, check-mode reproducibility semantics, and documentation links.
6. Update Episode 008 documentation to link the profiling artifacts and replace the TASK-068 placeholder-cost production-policy decision with the measured-profile review outcome, while preserving failed/unresolved target truthfulness and explicit-gap policy.
7. Run the focused profiling/schema tests, relevant existing Episode 008 artifact checks, `uv run pytest -q` as feasible, and `git diff --check`; then update TASK-071 implementation notes, acceptance criteria, final summary, and status through the Backlog CLI only.
<!-- SECTION:PLAN:END -->
