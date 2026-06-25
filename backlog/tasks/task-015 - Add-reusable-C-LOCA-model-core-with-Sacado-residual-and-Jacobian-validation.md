---
id: TASK-015
title: Add reusable C++ LOCA model core with Sacado residual and Jacobian validation
status: To Do
assignee: []
created_date: '2026-06-25 16:48'
labels:
  - episode-004
  - loca
  - cpp
  - sacado
  - tests
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement a legible independent C++ Bergner-Spichtinger Figure 1 residual core for LOCA, using Sacado forward-mode AD for the 3x3 state Jacobian. Validate residual and Jacobian evaluations against the existing Python package before relying on continuation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Top-level reusable LOCA/C++ source and CMake files build against /opt/Trilinos using g++ and Trilinos CMake config.
- [ ] #2 C++ executable exposes stable residual and jacobian subcommands for x = [log_n, log_q, s] and continuation parameter log_w.
- [ ] #3 Model formulas are translated from the Python package, independent of Python and AUTO at runtime, with clear comments explaining equations and units.
- [ ] #4 Sacado AD supplies the state Jacobian used by the executable; finite differences are not the primary C++ Jacobian implementation.
- [ ] #5 Tests compare C++ residuals and AD Jacobians against Python residuals and central-difference Jacobians, skipping cleanly when Trilinos build tools are unavailable.
<!-- AC:END -->
