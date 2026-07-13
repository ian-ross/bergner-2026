---
id: TASK-029
title: Implement AUTO native Hopf continuation for Figure 3
status: To Do
assignee: []
created_date: '2026-07-13 16:05'
labels: []
dependencies: []
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
