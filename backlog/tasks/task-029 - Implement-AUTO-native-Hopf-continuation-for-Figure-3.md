---
id: TASK-029
title: Implement AUTO native Hopf continuation for Figure 3
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-13 16:05'
updated_date: '2026-07-13 16:57'
labels: []
dependencies:
  - TASK-026
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use AUTO-07p native bifurcation tooling to detect the two Hopf points at T=230 K and continue them in the two-parameter space (log_w, T) for the Figure 3 domain. AUTO should exercise native Hopf detection/restart/continuation rather than merely generating equilibrium branches for external eigenvalue post-processing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AUTO run files/templates enable Hopf bifurcation detection from equilibrium continuation at T=230 K and label the lower and upper Hopf points.
- [ ] #2 AUTO workflows restart from each Hopf label and continue the Hopf loci over T=190--240 K with log_w and T as active continuation parameters.
- [ ] #3 Normalized AUTO outputs conform to the Episode 006 Hopf-locus schema and include raw AUTO artifacts, label provenance, convergence diagnostics, and method metadata.
- [ ] #4 Tests or opt-in smoke checks verify AUTO outputs include both Hopf branches, cover the requested temperature range, and agree near T=230 K with Python/reference landmarks within documented tolerance.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review AUTO-07p documentation/examples already available in the project environment for equilibrium Hopf detection and two-parameter Hopf continuation settings.
2. Create Episode 006 AUTO templates by adapting the Figure 2 equilibrium problem while enabling native Hopf detection at T=230 K and keeping log_w/T parameter conventions explicit.
3. Run equilibrium continuation at T=230 K, identify the two Hopf labels, and record label/provenance diagnostics.
4. Restart from each Hopf label and continue in active parameters log_w and T across 190--240 K, handling direction changes and branch naming consistently.
5. Normalize AUTO outputs into the Episode 006 Hopf-locus schema and preserve raw AUTO b/s/d files plus run metadata.
6. Add tests or opt-in smoke checks for raw-label detection, normalized schema, both branch labels, T-domain coverage, and T=230 K agreement with Python/reference anchors.
<!-- SECTION:PLAN:END -->
