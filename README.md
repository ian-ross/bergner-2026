# Bergner & Spichtinger 2026 model extraction

Reproducible extraction workspace for Hannah Bergner and Peter Spichtinger (2026), "Ice clouds as nonlinear oscillators," DOI `10.1063/5.0297531`.

Current work is organized into episodes under `episodes/`.

Key artifacts:

- `episodes/001-figure4-time-series/` — first episode: Figure 4 time-series reproduction.
- `episodes/001-figure4-time-series/outputs/figure4_reproduction.png` — curated generated plot.
- `episodes/007-limit-cycle-interactive-widget/` — offline, browser-based Figure 4 center-case limit-cycle explorer.
- `episodes/007-limit-cycle-interactive-widget/outputs/limit_cycle_stability.png` — curated long-run stability diagnostics.
- `episodes/007-limit-cycle-interactive-widget/outputs/attractor_convergence_log10n_s.png` — curated all-start convergence figure.
- `episodes/007-limit-cycle-interactive-widget/outputs/one_cycle_state_process_budgets.png` — curated representative-cycle state and process budgets.
- `episodes/007-limit-cycle-interactive-widget/web/index.html` — widget entry point; build to `web/dist/` and serve as static files.
- `docs/SOURCE_QUALITY.md` — source quality and extraction notes.
- `sources/extracted/provenance.yaml` — provenance manifest.
- `docs/MODEL_EXTRACTION.md` — implementation specification and ambiguity list.
- `sources/extracted/raw/` — reproducible raw extraction outputs.

Useful commands:

```bash
uv run python episodes/001-figure4-time-series/scripts/reproduce_figure4.py
uv run python episodes/001-figure4-time-series/scripts/extract_pdf_text.py
uv run python episodes/001-figure4-time-series/scripts/inspect_html.py
uv run python episodes/001-figure4-time-series/scripts/build_extraction_manifest.py
```
