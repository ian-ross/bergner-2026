# Episode 001: Figure 4 time-series reproduction

Goal: replicate/qualitatively reproduce the time-series panels from Figure 4 of Bergner & Spichtinger (2026), using the package implementation of the paper's model equations and the saved source materials.

## Contents

- `scripts/reproduce_figure4.py` — generates the curated Figure 4 qualitative reproduction plot.
- `scripts/extract_pdf_text.py`, `scripts/inspect_html.py`, `scripts/build_extraction_manifest.py` — source-inspection and provenance helpers used during this episode; they read from/write to the repository-level `sources/` tree.
- `notebooks/00_source_inspection.ipynb` — exploratory source inspection.
- `notebooks/01_reproduce_key_figures.ipynb` — exploratory figure reproduction work.
- `outputs/figure4_reproduction.png` — curated generated plot from this episode.

## Re-run

From the repository root:

```bash
uv run python episodes/001-figure4-time-series/scripts/reproduce_figure4.py
```

Source inspection helpers, if needed:

```bash
uv run python episodes/001-figure4-time-series/scripts/extract_pdf_text.py
uv run python episodes/001-figure4-time-series/scripts/inspect_html.py
uv run python episodes/001-figure4-time-series/scripts/build_extraction_manifest.py
```

## Cross-episode references

- Source originals and extracted products: `sources/`
- Cross-episode notes/specification: `docs/`
- Reusable model implementation: `src/bergner_spichtinger_2026/`
