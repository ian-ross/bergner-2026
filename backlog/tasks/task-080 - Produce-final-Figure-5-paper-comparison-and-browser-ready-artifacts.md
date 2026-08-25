---
id: TASK-080
title: Produce final Figure 5 paper comparison and browser-ready artifacts
status: In Progress
assignee:
  - '@iross'
created_date: '2026-08-24 13:19'
updated_date: '2026-08-25 14:00'
labels:
  - episode-008
  - figures
  - browser
  - paper-comparison
dependencies:
  - TASK-069
  - TASK-063
  - TASK-070
  - TASK-074
  - TASK-079
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Assemble final Episode 008 Figure 5 reproduction outputs after production continuation, validation, interpolation, linearized-period, and paper-digitization evidence are available.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Final plots and machine-readable artifacts reproduce the Figure 5 upper period map and lower T=210 K nonlinear/linearized slice with solved/interpolated/invalid/gap provenance and links to production records
- [ ] #2 TASK-063 digitized paper evidence is compared as image-derived external evidence with documented uncertainty; discrepancies follow the TASK-062/TASK-069 rule and do not override numerical convergence or IVP validation
- [ ] #3 Browser-ready artifacts are schema-valid, compact, documented, and clearly separated from Episode 007 widget integration code
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Freeze and verify upstream inputs: TASK-063 paper digitization, TASK-070 production schema/validator, TASK-074 T=210 K linearized curve, TASK-075 nonlinear production ledger/orbits, TASK-076 Hopf-gap policy records, TASK-077 Floquet diagnostics, TASK-078 IVP validation, and TASK-079 browser/interpolation dataset; run their --check/validator commands before deriving final artifacts.
2. Inspect existing Episode 008 generator/test/documentation conventions and define the final TASK-080 artifact set: paper-facing Figure 5 reproduction plots, a compact browser-ready final dataset/manifest, and a paper-comparison report that links every plotted/browser value to solved/interpolated/invalid/gap/image-derived provenance.
3. Implement a reproducible Episode 008 final-artifact generator with write/check modes. It will assemble the upper period map and lower T=210 K nonlinear/linearized slice from authoritative production/browser records, preserve explicit unresolved/Hopf/invalid gaps, attach production-record links, and incorporate TASK-063 digitized paper evidence only as a separate comparison channel with documented pixel/calibration uncertainty.
4. Generate final plot outputs and machine-readable artifacts under Episode 008 outputs, keeping browser-ready records schema-valid/compact/documented and strictly separated from any Episode 007 widget integration code. Do not fabricate interpolation or override convergence/IVP/Floquet status based on paper-image agreement.
5. Add/extend Episode 008 documentation and README links explaining the final artifact schema, plot interpretation, comparison/discrepancy policy, uncertainty limits, validation commands, and current scientific outcome.
6. Add focused pytest coverage for final artifact reproducibility/check mode, production-v1 schema validity, source/provenance distinctions, lower-panel source separation, paper comparison uncertainty/discrepancy policy, compact browser payload boundaries, and absence of Episode 007 integration coupling.
7. Run the final generator --check, production validators, upstream dependency checks affected by README/source hashes, focused tests, full pytest as feasible, and git diff --check; then update TASK-080 acceptance criteria, implementation notes, final summary, and status through the Backlog CLI only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started TASK-080: moved task to In Progress, assigned to @iross, reviewed the task and dependency summaries for TASK-063/069/070/074/075/076/077/078/079 plus the Episode 008 README/artifact inventory. No implementation changes have been made yet; pausing for plan confirmation.
<!-- SECTION:NOTES:END -->
