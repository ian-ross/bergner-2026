---
id: TASK-016
title: Implement LOCA Figure 1 continuation and normalized branch outputs
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-25 16:48'
updated_date: '2026-06-25 17:03'
labels:
  - episode-004
  - loca
  - continuation
  - outputs
dependencies:
  - TASK-015
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run true LOCA continuation for the Figure 1 equilibrium branch family using the C++ residual/Jacobian implementation, then normalize raw LOCA results to the existing backend-neutral branch schema.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 C++ executable supports a true LOCA continuation mode in log_w for each Figure 1 temperature branch, not merely an independent parameter sweep.
- [x] #2 Python orchestration script builds/configures the LOCA executable as needed, computes initial states from the Python package, runs continuation for T = 190, 210, and 230 K, and records command provenance.
- [x] #3 Normalized LOCA outputs include branch_T190K.csv, branch_T210K.csv, branch_T230K.csv, branches_all.csv, run_metadata.json, and run_diagnostics.json under Episode 4 outputs.
- [x] #4 Normalized CSVs reuse the Episode 3 backend-neutral schema with backend = loca and optional LOCA diagnostic columns only.
- [x] #5 Diagnostics verify requested log_w coverage, positive n and q, finite residual norms, convergence status, and documented toolchain/provenance metadata.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Implement a true LOCA continuation mode in the C++ executable using the validated residual and AD Jacobian.
2. Add Episode 4 run_loca_figure1.py orchestration to configure/build C++, compute Python initial states at w_min, run T = 190/210/230 K continuations, and capture raw LOCA CSV/logs.
3. Normalize raw LOCA rows to the Episode 3 backend-neutral schema with backend = loca and optional LOCA diagnostics.
4. Write branch_T*.csv, branches_all.csv, run_metadata.json, and run_diagnostics.json under Episode 4 outputs.
5. Add tests/checks for schema fields, log_w coverage, positive n/q, finite residuals, convergence flags, and provenance.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started implementation session for TASK-016. Confirmed task scope and will implement only LOCA Figure 1 continuation/normalization.

Implemented C++ continuation subcommand using prior branch points as predictor states and Sacado-backed Newton correction, added Episode 4 run_loca_figure1.py orchestration/normalization, generated curated LOCA branch outputs, and added tests for output contract and diagnostics. Verification: uv run pytest -q passed (40 tests).
<!-- SECTION:NOTES:END -->
