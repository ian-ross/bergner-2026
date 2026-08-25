---
id: TASK-063
title: Digitize paper Figure 5 for continuation-result comparison
status: Done
assignee:
  - '@pi'
created_date: '2026-08-13 04:20'
updated_date: '2026-08-25 13:57'
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
- [x] #1 A reproducible Episode 008 digitization workflow reads the saved source PDF or publisher Figure 5 image without modifying source originals and records source checksums and extraction provenance
- [x] #2 The upper panel digitization captures the plotted temperature/log-w domain, both Hopf boundaries, and paper period-color information at documented physical coordinates with an explicit calibration method
- [x] #3 The lower panel digitization captures the T=210 K nonlinear periodic-orbit and equilibrium-linearized period curves, including documented handling of axes, curve identity, gaps, and boundary endpoints
- [x] #4 Committed machine-readable outputs define schemas, units, coordinates, uncertainty or resolution limits, validity flags, and distinguish directly digitized samples from any derived interpolation
- [x] #5 Validation overlays or residual plots align digitized data with the source figure and quantify extraction/calibration error sufficiently to detect transcription or axis-mapping mistakes
- [x] #6 Episode 008 documentation explains how to compare the digitized reference with Python and LOCA continuation results without treating agreement with digitized pixels as stronger evidence than numerical convergence and independent IVP validation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inventory existing Episode 008 conventions and Figure 5 source assets; use the publisher Figure 5 JPEG as the primary immutable source, with the PDF retained as an additional provenance/checksum input.
2. Add a standalone Episode 008 digitization generator that records SHA-256/source metadata, fixed image dimensions, manual calibration control points, panel bounding boxes, axes/colorbar mappings, and deterministic extraction logic.
3. Digitize the upper panel into machine-readable paper-reference samples: calibrated T/log_w coordinates, Hopf boundary traces, period-color samples, validity flags, direct-vs-derived source labels, and explicit pixel/color resolution limits.
4. Digitize the lower T=210 K panel into machine-readable nonlinear and linearized period curves with calibrated log_w/period axes, curve identity metadata, endpoint/gap handling, and uncertainty/resolution annotations.
5. Emit validation artifacts (overlay/residual figures and JSON diagnostics) that compare sampled/calibrated points back to the source image and quantify mapping/color/curve residuals.
6. Document the dataset schema, calibration method, limitations, and comparison policy in Episode 008 docs, emphasizing that the digitized paper data are image-derived comparison evidence rather than authoritative backend results.
7. Run the generator in normal and --check modes plus targeted tests/validation, then mark acceptance criteria complete only for the verified deliverables.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- Started TASK-063; reviewed the task, Episode 008 README, and collocation-phase decisions.
- Confirmed source Figure 5 JPEG is present (520x760 RGB) alongside the saved PDF.
- Confirmed the uv environment has Pillow, NumPy, Matplotlib, SciPy, and pandas available for a reproducible digitization workflow; scikit-image/OpenCV are not installed, so the plan avoids relying on them.

- Implemented `generate_paper_figure5_digitization.py` with deterministic manual calibration, source-image/PDF checksum provenance, upper-panel boundary/color extraction, lower-panel red/black curve extraction, and --check support.
- Generated TASK-063 machine-readable artifacts under Episode 008 outputs: JSON schema/provenance summary, upper Hopf-boundary CSV, upper color-sample CSV, lower-curve CSV, overlay PNG, and residual diagnostic PNG.
- Added `docs/task063-paper-figure5-digitization.md`, updated the Episode 008 README, refreshed TASK-079 wording/placeholders, and regenerated `figure5_browser_interpolation_dataset.json` so source hashes remain current.
- Added focused tests in `tests/test_episode8_paper_figure5_digitization.py` and adjusted TASK-079 documentation test for the completed digitization state.
- Verification: `uv run pytest tests/test_episode8_paper_figure5_digitization.py tests/test_episode8_figure5_browser_interpolation_dataset.py` (11 passed).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented reproducible Episode 008 paper Figure 5 digitization as non-authoritative external comparison evidence.

Changes:
- Added `generate_paper_figure5_digitization.py` with deterministic `--check`, source JPEG/PDF SHA-256 provenance, calibrated upper/lower panel axes, empirical colorbar lookup, and connected-component curve extraction.
- Committed machine-readable digitization outputs for upper Hopf boundaries, upper color-derived period samples, and lower T=210 K red/black curves, plus JSON schema/provenance/validation metadata.
- Added overlay and residual diagnostic PNGs to verify extraction alignment and calibration/colorbar residuals.
- Documented calibration, uncertainty limits, comparison policy, and non-authoritative status in `docs/task063-paper-figure5-digitization.md` and the Episode 008 README.
- Refreshed TASK-079 documentation/hash-bound browser artifact to describe the pre-TASK-063 placeholder state accurately.
- Added focused tests covering reproducibility, source hashes, schemas, digitized sample counts, curve identities/endpoints, validation outputs, and docs.

Tests:
- `uv run pytest tests/test_episode8_paper_figure5_digitization.py tests/test_episode8_figure5_browser_interpolation_dataset.py`
<!-- SECTION:FINAL_SUMMARY:END -->
