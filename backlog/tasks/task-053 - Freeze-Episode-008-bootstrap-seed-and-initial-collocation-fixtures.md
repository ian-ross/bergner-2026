---
id: TASK-053
title: Freeze Episode 008 bootstrap seed and initial collocation fixtures
status: In Progress
assignee:
  - '@myself'
created_date: '2026-08-12 12:51'
updated_date: '2026-08-12 13:07'
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
- [ ] #6 The stale Episode 007 planning-contract test is explicitly disabled so it no longer blocks the repository suite
- [ ] #7 All current tracked Episode 006 and Episode 007 edits are reviewed, validated where practical, and committed together with the disabled Episode 007 test
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Define the Episode 008 seed schema and strict source-validation rules around the committed Episode 007 trajectory/metadata, including canonical parameters, SHA-256 checksums, the final paper_0.99 saturation-maximum interval, monotone samples, and periodic boundary tolerances.
2. Add a standalone Episode 008 bootstrap-seed script that extracts that interval, converts samples to (log(n), log(q), s), computes log(P) and transformed model-field phase slopes P*g(x), and writes a deterministic frozen JSON seed with extraction provenance.
3. Implement a periodic cubic-Hermite seed loader/evaluator that supports arbitrary normalized phases (including endpoint and collocation-stage locations) without invoking solve_ivp, while enforcing identical value and slope data at theta=0 and theta=1.
4. Generate and curate the frozen seed artifact under the Episode 008 outputs directory, then document its regeneration and downstream evaluation contract in the episode README.
5. Add repository-level tests for deterministic regeneration/evaluation, arbitrary endpoint/stage sampling, transformed-field slope semantics, boundary continuity, upstream checksum drift, malformed boundaries, and rejection of nonperiodic seed data; run focused and relevant regression tests.
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
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Established the reproducible Episode 007-to-008 periodic-orbit bootstrap without rerunning the long IVP.

Changes:
- Added a standalone deterministic seed generator with strict trajectory, metadata, canonical-parameter, cycle-boundary, and source-closure validation.
- Added a validated periodic cubic-Hermite evaluator for arbitrary endpoint and stage phases using transformed model-field slopes.
- Frozen the final paper_0.99 saturation-maximum cycle as a schema-versioned JSON artifact containing normalized phase, transformed state, log period, canonical parameters, checksums, and extraction provenance.
- Documented regeneration and checksum-verifying loading in the Episode 008 README.
- Added tests covering deterministic regeneration, all-knot slope semantics, periodic value/slope continuity, arbitrary sampling, upstream drift, malformed boundaries, and nonperiodic seed rejection.

Validation:
- Focused Episode 007/008 and residual tests: 11 passed.
- Deterministic generator check and Python compilation passed.
- Independent review found no blockers.
- Full suite: 111 passed, 1 unrelated pre-existing Episode 007 planning-contract failure caused by other working-tree changes.
<!-- SECTION:FINAL_SUMMARY:END -->
