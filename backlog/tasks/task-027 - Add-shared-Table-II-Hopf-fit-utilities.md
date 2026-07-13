---
id: TASK-027
title: Add shared Table II Hopf fit utilities
status: To Do
assignee: []
created_date: '2026-07-13 16:04'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement reusable package utilities for the Bergner & Spichtinger (2026) Table II quadratic-exponential Hopf bifurcation fits w_a(T) and w_b(T). These functions provide paper reference curves for Figure 3 Hopf-locus plots and future bifurcation/scaling work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Shared package code exposes lower/upper or w_a/w_b Hopf fit functions using SI inputs/outputs and documented Table II coefficients.
- [ ] #2 Unit tests verify coefficient values, expected values at representative temperatures, vectorized or array behavior if supported, and positive m/s outputs over T=190--240 K.
- [ ] #3 Figure 3 planning docs or package docstrings clearly state that these are paper fit references, not backend-computed Hopf loci.
- [ ] #4 The utilities are available to episode plotting/comparison scripts without duplicating coefficient literals there.
<!-- AC:END -->
