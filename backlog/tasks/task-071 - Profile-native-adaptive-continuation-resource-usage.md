---
id: TASK-071
title: Profile native adaptive continuation resource usage
status: Done
assignee:
  - '@iross'
created_date: '2026-08-24 13:18'
updated_date: '2026-08-24 15:22'
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
- [x] #1 Measured wall-clock time, CPU time, max RSS, nonlinear iterations, KLU2 symbolic/numeric factorization counts, linear solves, and source/build/runtime identities are recorded for representative fixed-mesh, remesh/restart, and pilot-style native adaptive segments
- [x] #2 The review determines whether serial KLU2 remains acceptable or whether the documented iterative-solver trigger thresholds are met
- [x] #3 Resource artifacts are reproducible or checkable and are linked from Episode 008 documentation without leaving placeholder values in production-policy decisions
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Plan approved by user; proceeding with profiling generator, artifacts, tests, and documentation.

Implemented TASK-071 measured profiling artifacts and documentation. Added `generate_native_adaptive_resource_profile.py`, generated `outputs/native_adaptive_resource_profile.json` plus production-v1 `outputs/native_adaptive_resource_profile_run_metadata.json`, documented the profile in `docs/task071-resource-profile.md`, linked it from the Episode 008 README, and updated TASK-069 decisions so prior zero-placeholder cost policy is superseded for current pilot seams.

Resource rows cover fixed-mesh, one-branch remesh/restart, and pilot-style driver seams with measured wall-clock, CPU, max RSS, NOX/KLU2 counters, source/build/runtime identity, and explicit truthfulness policy. KLU2 review keeps serial KLU2 acceptable for current pilot seams; documented evaluated triggers are not met, and backend-unexposed timing split triggers remain explicit not_evaluated.

Validation run:
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py --check`
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_resource_profile_run_metadata.json`
- `uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_final_reconciliation.py --check`
- `uv run pytest tests/test_episode8_native_adaptive_resource_profile.py tests/test_episode8_production_schema.py tests/test_episode8_native_adaptive_final_reconciliation.py -q`: 24 passed
- `uv run pytest -q`: 338 passed, 1 skipped, 3 known overflow warnings
- `git diff --check`: passed

Two read-only subagent reviews initially found stale TASK-069 wording, hard-coded trigger semantics, duplicate aggregate counters, and weak check semantics; fixes were applied. Follow-up read-only reviews reported no blockers.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added measured TASK-071 native adaptive resource profiling for current Episode 008 seams.

Changes:
- Added `scripts/generate_native_adaptive_resource_profile.py` to measure representative fixed-mesh, remesh/restart, and pilot-style native adaptive seams with `/usr/bin/time`, extract NOX iteration and KLU2 symbolic/numeric/solve counters, record source/build/runtime identities, and provide check-mode drift validation.
- Added curated outputs `native_adaptive_resource_profile.json` and production-v1 `native_adaptive_resource_profile_run_metadata.json`; the companion metadata validates with the TASK-070 production schema.
- Added focused tests for non-placeholder resource measurements, required counters, KLU2 trigger review, source/check semantics, production metadata, and documentation links.
- Documented the measured profile in `docs/task071-resource-profile.md`, linked it from the Episode 008 README, and updated TASK-069 decision text so pilot-seam resource placeholders are superseded without treating cost as scientific acceptance.
- Regenerated the TASK-068 final reconciliation manifest after README provenance changed.

KLU2 review:
- Serial KLU2 remains acceptable for the current native adaptive pilot seams.
- Evaluated trigger channels are not met; backend-unexposed factorization/solve timing split triggers remain explicitly `not_evaluated`.
- No Belos/Ifpack2 work is justified by TASK-071 evidence.

Validation:
- TASK-071 profile check and production metadata validation passed.
- Final reconciliation check passed.
- Focused tests: 24 passed.
- Full suite: `uv run pytest -q` -> 338 passed, 1 skipped, 3 known overflow warnings.
- `git diff --check` passed.
- Follow-up read-only reviews reported no blockers.
<!-- SECTION:FINAL_SUMMARY:END -->
