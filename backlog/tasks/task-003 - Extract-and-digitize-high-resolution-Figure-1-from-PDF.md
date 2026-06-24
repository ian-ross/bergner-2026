---
id: TASK-003
title: Extract and digitize high-resolution Figure 1 from PDF
status: To Do
assignee: []
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 16:38'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use pdfimages or an equivalent reproducible PDF-image extraction workflow to extract the high-resolution Figure 1 raster from sources/original/bergner-spichtinger-2026.pdf.
2. Store the extracted source image under Episode 2 outputs with provenance metadata.
3. Define panel crop boxes and axis calibration metadata for all three panels, including log(w) x-axis transforms and linear/log y-axis transforms as appropriate.
4. Digitize the rendered curves for T=190, 210, 230 K in each panel, treating co-located colored/black lines as the paper-rendered curve.
5. Save digitized CSV plus overlay/QA artifacts showing extracted points against the source image or calibrated axes.
<!-- SECTION:PLAN:END -->
