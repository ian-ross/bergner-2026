---
id: TASK-038
title: Validate and document the offline Episode 007 widget
status: In Progress
assignee:
  - '@pi'
created_date: '2026-07-20 20:54'
updated_date: '2026-07-20 21:02'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Audit the production bundle and runtime requests to ensure all code and Plotly assets are local and the widget requires no CDN, backend, Python process, or notebook kernel.
2. Run the complete Python and TypeScript suites, production build, and an end-to-end canonical browser integration; compare short-horizon and cycle-level results with reference tolerances.
3. Exercise the documented smoke-test matrix across representative Chromium and Firefox-family browsers, including run, cancellation, replay, parameter changes, damped behavior, and the canonical preset.
4. Harden responsive behavior, keyboard access, labels, units, status/error announcements, and reduced-motion handling without expanding the visualization scope.
5. Document architecture, equations and numerical methods, supported ranges, reference provenance, known limitations, development commands, offline serving, and static deployment.
6. Update the repository README with Episode 007 links, perform a final self-review of generated versus curated artifacts, and verify all acceptance criteria and documentation claims.
<!-- SECTION:PLAN:END -->
