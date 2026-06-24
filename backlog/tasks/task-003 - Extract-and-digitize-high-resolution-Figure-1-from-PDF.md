---
id: TASK-003
title: Extract and digitize high-resolution Figure 1 from PDF
status: In Progress
assignee:
  - '@pi'
created_date: '2026-06-24 16:38'
updated_date: '2026-06-24 17:01'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extract the high-resolution Figure 1 raster from the saved publisher PDF and digitize the rendered equilibrium curves for comparison with generated results.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducible Episode 2 script extracts the high-resolution Figure 1 image from sources/original/bergner-spichtinger-2026.pdf into episode outputs.
- [x] #2 Digitization calibration metadata is stored with axis bounds, panel regions, log-axis transforms, and source-image provenance.
- [x] #3 Digitized curve CSV includes panel, T_K, w_m_s, value, pixel coordinates or equivalent trace diagnostics, and source/provenance fields.
- [x] #4 Digitization quality is checked by overlaying extracted points on the source image or calibrated axes.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use pdfimages or an equivalent reproducible PDF-image extraction workflow to extract the high-resolution Figure 1 raster from sources/original/bergner-spichtinger-2026.pdf.
2. Store the extracted source image under Episode 2 outputs with provenance metadata.
3. Define panel crop boxes and axis calibration metadata for all three panels, including log(w) x-axis transforms and linear/log y-axis transforms as appropriate.
4. Digitize the rendered curves for T=190, 210, 230 K in each panel, treating co-located colored/black lines as the paper-rendered curve.
5. Save digitized CSV plus overlay/QA artifacts showing extracted points against the source image or calibrated axes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented Episode 2 Figure 1 extraction/digitization script. The PDF does not expose Figure 1 as a pdfimages raster, so the script records pdfimages output and reproducibly renders/crops page 12 at 600 dpi with pdftoppm. Generated source crop, metadata YAML/JSON, digitized CSV, and overlay QA artifacts under episodes/002-figure1-python-continuation/outputs/figure1_digitized/.

Verification run:
- uv run python episodes/002-figure1-python-continuation/scripts/extract_digitize_figure1.py
- python -m py_compile episodes/002-figure1-python-continuation/scripts/extract_digitize_figure1.py
- CSV has 1547 digitized points plus header; overlay visually confirms points track rendered curves.
<!-- SECTION:NOTES:END -->
