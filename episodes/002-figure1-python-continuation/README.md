# Episode 002: Figure 1 Python continuation

Goal: reproduce and validate the Figure 1 equilibrium branch family from Bergner & Spichtinger (2026) using reusable package-level continuation and residual utilities.

## Contents

- `docs/planning-decisions.md` — episode-specific terminology and decisions from the Figure 1 planning/grill session.
- `scripts/generate_figure1_continuation.py` — generates Figure 1 equilibrium branches, independent root-solve checks, and Eq. 92--94 comparison tables.
- `outputs/figure1_continuation/` — curated branch CSVs, comparison detail tables, summary CSV/JSON, and run metadata for TASK-002.
- `scripts/extract_digitize_figure1.py` — reproducibly renders/crops Figure 1 from the saved PDF and digitizes the rendered curves.
- `outputs/figure1_digitized/` — Figure 1 source crop, digitized curve CSV, calibration/provenance metadata, and overlay QA artifacts for TASK-003.
- `scripts/plot_figure1_reproduction.py` — assembles the final Figure 1-style reproduction plot and digitized-curve residual summaries.
- `outputs/figure1_reproduction/` — curated TASK-004 plot, residual plot, continuation-vs-digitized comparison tables, and run metadata.
- `notebooks/` — exploratory notebooks for source inspection, continuation diagnostics, and figure comparison.

## Reproduction commands

Run from the repository root with the uv-managed environment:

```bash
uv run python episodes/002-figure1-python-continuation/scripts/generate_figure1_continuation.py
uv run python episodes/002-figure1-python-continuation/scripts/extract_digitize_figure1.py
uv run python episodes/002-figure1-python-continuation/scripts/plot_figure1_reproduction.py
uv run pytest
```

`extract_digitize_figure1.py` requires Poppler command-line tools (`pdftoppm` and, for image inventory provenance, `pdfimages`) in addition to the Python dependencies managed by uv.

## Final Figure 1 reproduction artifact

The curated reproduction is `outputs/figure1_reproduction/figure1_reproduction.png`. It follows the paper's Figure 1 layout: left panel ice crystal number concentration `n`, middle panel ice crystal mass concentration `q`, right panel saturation ratio `s`; all panels use a logarithmic vertical-velocity axis over `w = 0.005--2.0 m s-1` and map `T = 190, 210, 230 K` to blue, gray, and red curves.

Plot encodings:

- solid curves: Python continuation branch family at `p = 300 hPa`, `F = 1`;
- dashed curves: analytic Eq. 92--94 approximation evaluated on the same `w` grid;
- open circles: independent root-solve checks sampled from the continuation outputs;
- x markers: digitized paper curves extracted from the rendered Figure 1 PDF page.

A companion residual plot is `outputs/figure1_reproduction/figure1_digitized_residuals.png`, with tabular details in `digitized_comparison_details.csv` and per-variable/per-temperature summaries in `digitized_comparison_summary.csv`.

## Source provenance and methods

Source material comes from `sources/original/bergner-spichtinger-2026.pdf`. The digitization script records the PDF SHA-256, rendered page, figure crop, panel calibration, color thresholds, point counts, and overlay QA artifacts under `outputs/figure1_digitized/`. `pdfimages` reports no reusable embedded Figure 1 raster, so digitization uses a reproducible 600-dpi render/crop of PDF page 12.

The numerical reproduction uses reusable package code in `src/bergner_spichtinger_2026/`: continuation follows equilibrium branches in log coordinates using `log(w)` as the continuation parameter, independent root solves validate sampled branch points, and `approximations.py` evaluates Eqs. 92--94. Episode scripts are orchestration only and write inspectable CSV/JSON/PNG artifacts under `outputs/`.

The Figure 1 continuation explicitly uses `N_a = 1.0e10 m^-3` (`10000 cm^-3`), the paper's Appendix A2 "unrealistically high aerosol number concentration" reference value. This is not stated in the Figure 1 caption, but it is inferred from the saturation-ratio panel: using the Appendix A2 typical value (`300 cm^-3`) shifts all generated `s` curves high by about `ln(10000/300) / p1e(T)`, matching the observed offset.

Known limitations:

- Digitized curves inherit uncertainty from rendered-pixel calibration, antialiasing, grid-line suppression, and legend/text interference; the neutral gray `T = 210 K` curves are the lowest-confidence digitized series.
- The paper's colored curves and black approximation strokes are visually co-located in Figure 1, so digitization treats the visible colored curve as the paper-rendered equilibrium benchmark rather than separating paper data from paper fit strokes.
- The Figure 1 caption omits `N_a`; the high-aerosol value is therefore an inferred assumption rather than explicit caption provenance. See `docs/REPRODUCTION_NOTES.md` for the debugging trail.

## Scope

This episode uses reusable numerical primitives from `src/bergner_spichtinger_2026/` rather than embedding continuation algorithms in one-off scripts. Episode scripts should handle orchestration and artifact paths only.

## Cross-episode references

- Source originals and extracted products: `sources/`
- Reusable model implementation: `src/bergner_spichtinger_2026/`
- Episode 1 Figure 4 reproduction: `episodes/001-figure4-time-series/`
