---
id: TASK-032
title: Create Episode 007 scaffold and record limit-cycle widget decisions
status: Done
assignee:
  - '@pi'
created_date: '2026-07-20 20:53'
updated_date: '2026-07-20 21:10'
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
- [x] #1 Episode 007 has a README and episode-local notebooks, docs, web, and outputs structure consistent with repository organization rules
- [x] #2 Planning documentation records the canonical Figure 4 center case: T=225 K, p=300 hPa, w=0.1 m/s, F=1, N_a=10000 cm^-3, Delta z=100 m, with Evap_n disabled
- [x] #3 Planning documentation records the four initial-condition protocol, final-20-cycle convergence thresholds, three curated figures, and reference-data contract
- [x] #4 Planning documentation records the static vanilla TypeScript/Vite/Plotly architecture, supported parameter ranges, client-side equilibrium solve, log-state RK45 integration, and Web Worker boundary
- [x] #5 The episode README documents intended rerun, build, test, and static-serving commands without claiming unimplemented outputs exist
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Review repository episode conventions and the Episode 001/006 documentation patterns.
2. Create the Episode 007 directory skeleton for docs, notebooks, outputs, and the browser application without adding generated artifacts prematurely.
3. Write planning decisions covering the canonical high-aerosol Figure 4 case, initial conditions, convergence criteria, figure set, reference-data schema, supported widget parameters, numerical methods, worker boundary, and static architecture.
4. Write the episode README with scope, artifact layout, cross-episode references, and clearly marked planned rerun/build/test/serve commands.
5. Validate the scaffold against AGENTS.md and self-review the documentation for consistency with all approved decisions.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Added the Episode 007 README, planning-decision record, and episode-local placeholders.
- Added scaffold-contract tests; `uv run pytest -q` passed (92 tests).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the Episode 007 planning scaffold and recorded the scientific, numerical, reference-data, and offline-widget contracts needed by follow-on work.

Changes:
- Added the episode-local README, planning decisions, and notebooks/web/outputs placeholders.
- Documented the canonical Figure 4 center case, convergence/reference-data contracts, supported browser domain, and static Worker-based architecture.
- Added repository tests that lock down the scaffold and required documentation contracts.

Tests:
- `uv run pytest -q tests/test_episode7_scaffold.py`
- `uv run pytest -q` (92 passed; 3 existing numerical overflow warnings)
<!-- SECTION:FINAL_SUMMARY:END -->
