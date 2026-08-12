---
id: TASK-053
title: Freeze Episode 008 bootstrap seed and initial collocation fixtures
status: In Progress
assignee:
  - '@myself'
created_date: '2026-08-12 12:51'
updated_date: '2026-08-12 12:53'
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
