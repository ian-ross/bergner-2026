---
id: TASK-002
title: Implement Figure 1 Python continuation and analytic approximation comparison
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the reusable continuation layer to reproduce Figure 1 equilibrium branches for p=300 hPa, F=1, T in {190,210,230} K, and w in [0.005,2.0] m/s, with independent root-solve and Eq. 92--94 checks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Episode 2 script generates continuation branch CSVs containing T_K, p_Pa, F, log_w, w_m_s, n, q, s, convergence diagnostics, and residual norms.
- [ ] #2 Independent root-solve checks are computed at sampled w values and compared against continuation output.
- [ ] #3 Analytic approximation values from Eqs. 92--94 are computed from package-level formulas and compared against continuation output.
- [ ] #4 Comparison summary tables report maximum/typical discrepancies for continuation vs root solves and continuation vs analytic approximation.
<!-- AC:END -->
