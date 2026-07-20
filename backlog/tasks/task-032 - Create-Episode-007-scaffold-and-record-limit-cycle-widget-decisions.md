---
id: TASK-032
title: Create Episode 007 scaffold and record limit-cycle widget decisions
status: To Do
assignee: []
created_date: '2026-07-20 20:53'
labels:
  - episode-007
  - planning
dependencies: []
references:
  - README.md
  - AGENTS.md
  - episodes/001-figure4-time-series/README.md
  - episodes/006-figure3-hopf-bifurcation/README.md
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create episodes/007-limit-cycle-interactive-widget as the single home for the long-integration investigation and fully client-side interactive widget. Record the approved scientific parameters, numerical contracts, browser architecture, output layout, and cross-episode dependencies before implementation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 007 has a README and episode-local notebooks, docs, web, and outputs structure consistent with repository organization rules
- [ ] #2 Planning documentation records the canonical Figure 4 center case: T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=10000 cm^-3, Delta z=100 m, with Evap_n disabled
- [ ] #3 Planning documentation records the four initial-condition protocol, final-20-cycle convergence thresholds, three curated figures, and reference-data contract
- [ ] #4 Planning documentation records the static vanilla TypeScript/Vite/Plotly architecture, supported parameter ranges, client-side equilibrium solve, log-state RK45 integration, and Web Worker boundary
- [ ] #5 The episode README documents intended rerun, build, test, and static-serving commands without claiming unimplemented outputs exist
<!-- AC:END -->
