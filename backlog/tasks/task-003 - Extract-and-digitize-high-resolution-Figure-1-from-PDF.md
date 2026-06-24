---
id: TASK-003
title: Extract and digitize high-resolution Figure 1 from PDF
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract the high-resolution Figure 1 raster from the saved publisher PDF and digitize the rendered equilibrium curves for comparison with generated results.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A reproducible Episode 2 script extracts the high-resolution Figure 1 image from sources/original/bergner-spichtinger-2026.pdf into episode outputs.
- [ ] #2 Digitization calibration metadata is stored with axis bounds, panel regions, log-axis transforms, and source-image provenance.
- [ ] #3 Digitized curve CSV includes panel, T_K, w_m_s, value, pixel coordinates or equivalent trace diagnostics, and source/provenance fields.
- [ ] #4 Digitization quality is checked by overlaying extracted points on the source image or calibrated axes.
<!-- AC:END -->
