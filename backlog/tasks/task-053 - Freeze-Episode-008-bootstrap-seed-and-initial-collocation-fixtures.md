---
id: TASK-053
title: Freeze Episode 008 bootstrap seed and initial collocation fixtures
status: In Progress
assignee:
  - '@myself'
created_date: '2026-08-12 12:51'
updated_date: '2026-08-12 12:54'
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
- [ ] #1 An Episode 008 script deterministically extracts the final complete saturation-maximum-to-maximum cycle from the committed Episode 007 reference artifacts
- [ ] #2 The frozen seed stores normalized phase, transformed state, log period, canonical parameter values, upstream checksums, and extraction provenance
- [ ] #3 Periodic cubic-Hermite evaluation uses transformed model-field slopes and reproduces matching values and slopes at the cycle boundary
- [ ] #4 The seed can be evaluated at arbitrary endpoint and collocation-stage locations without rerunning the long IVP
- [ ] #5 Tests detect upstream artifact drift, malformed cycle boundaries, and nonperiodic seed construction
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
<!-- SECTION:NOTES:END -->
