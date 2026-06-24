# Episode 002: Figure 1 Python continuation

Goal: reproduce and validate the Figure 1 equilibrium branch family from Bergner & Spichtinger (2026) using reusable package-level continuation and residual utilities.

## Contents

- `docs/planning-decisions.md` — episode-specific terminology and decisions from the Figure 1 planning/grill session.
- `scripts/generate_figure1_continuation.py` — generates Figure 1 equilibrium branches, independent root-solve checks, and Eq. 92--94 comparison tables.
- `outputs/figure1_continuation/` — curated branch CSVs, comparison detail tables, summary CSV/JSON, and run metadata for TASK-002.
- `scripts/extract_digitize_figure1.py` — reproducibly renders/crops Figure 1 from the saved PDF and digitizes the rendered curves.
- `outputs/figure1_digitized/` — Figure 1 source crop, digitized curve CSV, calibration/provenance metadata, and overlay QA artifacts for TASK-003.
- `notebooks/` — exploratory notebooks for source inspection, continuation diagnostics, and figure comparison.

## Scope

This episode uses reusable numerical primitives from `src/bergner_spichtinger_2026/` rather than embedding continuation algorithms in one-off scripts. Episode scripts should handle orchestration and artifact paths only.

## Cross-episode references

- Source originals and extracted products: `sources/`
- Reusable model implementation: `src/bergner_spichtinger_2026/`
- Episode 1 Figure 4 reproduction: `episodes/001-figure4-time-series/`
