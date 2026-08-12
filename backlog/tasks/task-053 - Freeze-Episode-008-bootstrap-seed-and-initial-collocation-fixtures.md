---
id: TASK-053
title: Freeze Episode 008 bootstrap seed and initial collocation fixtures
status: In Progress
assignee:
  - '@myself'
created_date: '2026-08-12 12:51'
updated_date: '2026-08-12 15:17'
labels:
  - episode-008
  - python
  - numerics
dependencies: []
references:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
  - episodes/007-limit-cycle-interactive-widget/outputs/reference_trajectory.csv
  - episodes/007-limit-cycle-interactive-widget/outputs/reference_metadata.json
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Establish the reproducible bridge from the validated Episode 007 attracting cycle into Episode 008 fixed-mesh collocation, while keeping the initial implementation independent of long IVP reruns.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An Episode 008 script deterministically extracts the final complete saturation-maximum-to-maximum cycle from the committed Episode 007 reference artifacts
- [x] #2 The frozen seed stores normalized phase, transformed state, log period, canonical parameter values, upstream checksums, and extraction provenance
- [x] #3 Periodic cubic-Hermite evaluation uses transformed model-field slopes and reproduces matching values and slopes at the cycle boundary
- [x] #4 The seed can be evaluated at arbitrary endpoint and collocation-stage locations without rerunning the long IVP
- [x] #5 Tests detect upstream artifact drift, malformed cycle boundaries, and nonperiodic seed construction
- [x] #6 The stale Episode 007 planning-contract test is explicitly disabled so it no longer blocks the repository suite
- [x] #7 All current tracked Episode 006 and Episode 007 edits are reviewed, validated where practical, and committed together with the disabled Episode 007 test
- [x] #8 The periodic seed loader, validator, checksum verification, and Hermite evaluator live in reusable package code rather than the standalone Episode 008 generator script
- [x] #9 The Episode 008 generator and tests consume the packaged API while deterministic seed regeneration remains unchanged
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extract the generic periodic-seed exception, checksum verification, JSON loader/validator, and cubic-Hermite evaluator into src/bergner_spichtinger_2026/periodic_seed.py without episode-specific default paths.
2. Keep Episode 007 source extraction, provenance construction, deterministic rendering, and CLI behavior in the Episode 008 standalone generator; validate generated mappings through the package API explicitly.
3. Update Episode 008 tests and documentation to import the reusable package API, add package-level loader coverage, and verify that the frozen JSON regeneration is byte-identical.
4. Run focused and full Python validation, review the diff, update task records, and commit the refactor.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Reviewed the task references and Episode 008 decisions. The committed Episode 007 canonical trajectory ends on the final paper_0.99 cycle boundary at 238305.99976106847 s; current upstream SHA-256 values are 899476206a26a3d0a43a3ecf6887975e7ebb14e613b06df01e207c54e1a086b2 (trajectory) and 7077f0516090526da3876c2b259d5ca4cf624ea04a2644162a8d4b04452b64d9 (metadata).
- Confirmed Python 3.13, pytest 9, NumPy/SciPy project dependencies, and the reusable physical/log-coordinate model functions are available.
- The worktree already contains unrelated Episode 006/007 modifications and an untracked Episode 008 scaffold; implementation will avoid overwriting those changes.

- Implementation started after plan approval. Source inspection found the final cycle start event time is recorded in metadata but is not an exact CSV row; it is bracketed by rising/falling saturation samples. The final end event is an exact CSV row. The seed will record this explicitly and reuse the converged terminal saturation-maximum state at both periodic endpoints, while retaining only strict-interior source samples and evaluating model-field slopes at every stored knot.

- Added the deterministic Episode 008 generator/evaluator, frozen bootstrap_seed.json artifact, README regeneration instructions, and focused repository tests. The seed uses the final Episode 007 paper_0.99 cycle (P = 2461.6112682421517 s), records both upstream checksums, and evaluates all stored slopes from the transformed model field.
- Validation: `uv run pytest -q tests/test_episode8_bootstrap_seed.py tests/test_episode7_diagnostics_notebook.py tests/test_residuals_continuation.py` passed (11 tests); generator `--check`, py_compile, and git diff whitespace checks passed. Independent review found no correctness or acceptance blockers; its optional all-knot slope-test hardening was applied and revalidated.
- Full suite result: 111 passed and 1 failed. The sole failure is the pre-existing modified Episode 007 planning contract: tests/test_episode7_scaffold.py still expects the old exact worker-message phrase, while the unrelated working-tree edit adds `equilibrium` and `samples` message types. TASK-053 remains In Progress because repository instructions require a green full suite before Done; no unrelated Episode 007 files were changed.

- User explicitly expanded the task to disable the stale Episode 007 planning-contract test and commit the current Episode 006/007 worktree edits. These requirements were added as acceptance criteria before making further changes.

- Disabled the superseded Episode 007 planning-contract test with an explicit pytest skip. The repository suite is now green: 111 passed, 1 skipped. Episode 007 Vitest passed 27 tests and its production build/offline verification passed.
- Reviewed and committed all tracked Episode 006/007 edits plus the disabled Episode 007 test as commit d7b8bd9 (`feat(episode-007): stream integration samples`). TASK-053 Episode 008 changes remain uncommitted because the user specifically requested committing Episode 006/007 edits.

- Reopened after identifying that PeriodicHermiteSeed and checksum validation were incorrectly isolated inside a standalone episode script. User approved moving the reusable JSON loading/evaluation contract into package code while retaining Episode 007 extraction and CLI concerns in the generator.

- Moved PeriodicHermiteSeed, SeedValidationError, generic SHA-256/upstream verification, JSON loading, validation, and interpolation into reusable src/bergner_spichtinger_2026/periodic_seed.py and exported the API from the package. The Episode 008 script now retains only extraction/generation concerns and calls the explicit validate_mapping API.
- Updated tests and README to consume the package API. Independent review found no blocker; addressed its malformed top-level JSON finding, added SciPy cross-checks for between-knot values/derivatives, and made loaded arrays defensive read-only copies. Validation: 6 focused tests passed, deterministic artifact check passed byte-for-byte, py_compile/diff checks passed, and full suite passed with 112 passed / 1 explicitly skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Established a reusable, reproducible Episode 007-to-008 periodic-orbit bootstrap without rerunning the long IVP.

Changes:
- Added an Episode 008 deterministic seed generator with strict source, parameter, boundary, closure, and provenance validation.
- Frozen the final paper_0.99 saturation-maximum cycle as language-neutral JSON containing normalized phase, transformed states, model-field slopes, log period, canonical parameters, and upstream checksums.
- Added reusable package-level PeriodicHermiteSeed loading, schema validation, checksum verification, and periodic cubic-Hermite evaluation; the standalone episode script now owns only extraction and generation.
- Added defensive immutable arrays, explicit malformed top-level JSON handling, and package exports.
- Documented regeneration and downstream package use.
- Added tests for deterministic regeneration, all-knot field slopes, periodic continuity, arbitrary endpoint/stage sampling, SciPy interpolation parity, upstream drift, malformed data, and nonperiodic construction.
- Disabled the superseded Episode 007 planning-contract test and committed the prior Episode 006/007 work as d7b8bd9.

Validation:
- Full Python suite: 112 passed, 1 explicitly skipped.
- Focused bootstrap tests: 6 passed.
- Deterministic generator check and Python compilation passed.
- Episode 007 Vitest/build/offline verification passed for the prior committed edits.
- Independent review found no remaining blocker.
<!-- SECTION:FINAL_SUMMARY:END -->
