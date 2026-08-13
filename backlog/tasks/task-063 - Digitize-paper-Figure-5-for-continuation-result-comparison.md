---
id: TASK-063
title: Digitize paper Figure 5 for continuation-result comparison
status: To Do
assignee: []
created_date: '2026-08-13 04:20'
labels:
  - episode-008
  - digitization
  - validation
dependencies: []
references:
  - sources/original/bergner-spichtinger-2026.pdf
  - >-
    sources/original/bergner-spichtinger-2026_files/m_043115_1_5.0297531.figures.online.f5.jpeg
documentation:
  - >-
    episodes/008-figure5-periodic-orbit-continuation/docs/collocation-phase-decisions.md
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract and digitize both panels of Bergner & Spichtinger (2026) Figure 5 as a reproducible Episode 008 paper-reference dataset. The digitization will provide an independent comparison target for our computed periodic-orbit period map and the T=210 K nonlinear/linearized-period slice; it must remain clearly labeled as image-derived evidence rather than backend-computed data.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducible Episode 008 digitization workflow reads the saved source PDF or publisher Figure 5 image without modifying source originals and records source checksums and extraction provenance
- [ ] #2 The upper panel digitization captures the plotted temperature/log-w domain, both Hopf boundaries, and paper period-color information at documented physical coordinates with an explicit calibration method
- [ ] #3 The lower panel digitization captures the T=210 K nonlinear periodic-orbit and equilibrium-linearized period curves, including documented handling of axes, curve identity, gaps, and boundary endpoints
- [ ] #4 Committed machine-readable outputs define schemas, units, coordinates, uncertainty or resolution limits, validity flags, and distinguish directly digitized samples from any derived interpolation
- [ ] #5 Validation overlays or residual plots align digitized data with the source figure and quantify extraction/calibration error sufficiently to detect transcription or axis-mapping mistakes
- [ ] #6 Episode 008 documentation explains how to compare the digitized reference with Python and LOCA continuation results without treating agreement with digitized pixels as stronger evidence than numerical convergence and independent IVP validation
<!-- AC:END -->
