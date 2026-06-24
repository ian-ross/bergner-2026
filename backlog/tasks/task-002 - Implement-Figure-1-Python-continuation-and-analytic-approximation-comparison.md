---
id: TASK-002
title: Implement Figure 1 Python continuation and analytic approximation comparison
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:46'
labels: []
dependencies:
  - TASK-001
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add package-level Figure 1 analytic approximation helpers implementing Eqs. 92--94 from existing coefficient functions.
2. Write an Episode 2 script that runs log(w) continuation for T=190, 210, 230 K at p=300 hPa and F=1 over w in [0.005, 2.0] m/s.
3. Save branch points and continuation diagnostics to episode outputs.
4. Run independent equilibrium root solves at sampled w values and compare them to continuation points.
5. Compare continuation values to Eq. 92--94 approximations and write summary CSV/JSON tables.
<!-- SECTION:PLAN:END -->
