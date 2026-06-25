---
id: TASK-012
title: Normalize AUTO outputs to backend-neutral branch schema
status: To Do
assignee: []
created_date: '2026-06-25 09:15'
updated_date: '2026-06-25 09:15'
labels: []
dependencies:
  - TASK-011
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parse Episode 3 AUTO continuation outputs into a backend-neutral branch table compatible with Episode 2 Python continuation outputs and future LOCA comparisons.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 AUTO branch CSVs include backend, T_K, p_Pa, F, N_a_m3, log_w, w_m_s, log_n, log_q, n, q, s, and available AUTO diagnostics.
- [ ] #2 One combined branches_all.csv is written for all Figure 1 temperatures using the agreed backend-neutral schema.
- [ ] #3 Parsing scripts preserve raw AUTO labels and diagnostics while converting transformed coordinates to physical values.
- [ ] #4 Run metadata documents schema version, input files, raw AUTO output paths, and any parser assumptions.
<!-- AC:END -->
