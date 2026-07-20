---
id: TASK-038
title: Validate and document the offline Episode 007 widget
status: To Do
assignee: []
created_date: '2026-07-20 20:54'
labels:
  - episode-007
  - validation
  - documentation
dependencies:
  - TASK-037
references:
  - episodes/007-limit-cycle-interactive-widget/README.md
  - README.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Complete the episode by validating the assembled scientific-to-browser workflow, hardening the static widget for offline use and common browsers, and documenting reproducible notebook, test, build, serving, and deployment procedures.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A production build creates a multi-file static bundle with all plotting and runtime dependencies local and no CDN, backend, Python service, or notebook-kernel requirement
- [ ] #2 The built widget performs a fresh canonical equilibrium solve and integration in-browser and reproduces the reference trajectory and cycle statistics within the approved validation tolerances
- [ ] #3 The widget remains usable at desktop and narrow viewport sizes, supports keyboard operation for essential controls, and includes labels, units, status text, and reduced-motion behavior
- [ ] #4 Automated Python and TypeScript tests pass, the production build succeeds, and a documented browser smoke test covers run, cancel, replay, parameter changes, and the canonical preset
- [ ] #5 Episode documentation explains architecture, numerical methods, supported ranges, known limitations, reference-data provenance, offline serving, and static deployment
- [ ] #6 Repository-level README links Episode 007 and its curated scientific figures and widget entry point
<!-- AC:END -->
