---
id: TASK-050
title: Remove unsupported Episode 007 initial and advanced controls
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-21 20:43'
updated_date: '2026-07-21 20:43'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Remove the non-working s +1% initial condition and the Advanced controls section, fixing pressure and layer depth at their Figure 4 defaults.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The s +1% initial-condition option is absent and rejected by control validation
- [ ] #2 The Advanced controls section is absent
- [ ] #3 Pressure and layer depth remain fixed at 300 hPa and 100 m
- [ ] #4 Documentation and tests reflect the reduced control surface
- [ ] #5 Web tests and production build pass
<!-- AC:END -->
