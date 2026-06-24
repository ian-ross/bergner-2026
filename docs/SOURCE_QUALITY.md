# Source quality report

## Registered sources

- `sources/original/bergner-spichtinger-2026.html`: saved AIP publisher HTML for Bergner & Spichtinger (2026), **Ice clouds as nonlinear oscillators**, DOI `10.1063/5.0297531`.
- `sources/original/bergner-spichtinger-2026_files/`: ancillary files from the saved HTML, including MathJax assets and 13 JPEG figure images.
- `sources/original/bergner-spichtinger-2026.pdf`: publisher PDF, used as visual ground truth and fallback text source.

The original user-provided files remain at the project root as well.

## Tools and commands run

- `uv init --package --name bergner-spichtinger-2026 --vcs none .`
- `pdftotext -layout bergner-spichtinger-2026.pdf sources/extracted/raw/bergner-spichtinger-2026.layout.txt`
- `pdftotext -raw bergner-spichtinger-2026.pdf sources/extracted/raw/bergner-spichtinger-2026.raw.txt`
- `uv run python episodes/001-figure4-time-series/scripts/inspect_html.py`
- `uv run python episodes/001-figure4-time-series/scripts/build_extraction_manifest.py`

No cloud/API extraction tools were used. No document or snippet was uploaded externally.

## HTML quality

The publisher HTML is the primary extraction source. Automated inspection found:

- article metadata present via `citation_*` meta tags;
- 982 `<math>` tags and 1028 MathJax mentions;
- 2187 equation/formula-like blocks discovered by broad CSS-class scanning;
- 4 HTML `<table>` elements;
- section headings and appendix headings preserved;
- figure captions are visible in extracted PDF text, while the saved HTML does not use semantic `<figure>` tags in a way detected by the first-pass script; figure JPEGs are present in ancillary files.

Assessment: **high** quality for locating equations and text, **medium** quality for fully automatic equation inventory because display equations, inline equations, repeated MathJax renderings, and publisher UI markup need filtering.

## PDF quality

The PDF appears born digital. `pdftotext` produced layout and raw text outputs. Prose, captions, section headings, and many displayed equations are readable. However, mathematical notation, fractions, superscripts/subscripts, and two-column layout can be corrupted or split across columns. PDF text should not be the sole source for implementation-critical formulas.

## Equation/table/figure extraction quality

- Main ODE system, parameter ranges, and many appendix formulas are legible in `sources/extracted/raw/bergner-spichtinger-2026.layout.txt` and cross-checkable against the semantic HTML/PDF.
- Table I parameter ranges and Table II bifurcation fit coefficients are readable in PDF text.
- Figure images are present as JPEGs, but underlying numeric data for model-output figures were not found locally. The Data Availability statement points to B2SHARE DOI `10.34730/266ca2a41f4946ff97d874bfa458254c` for comparison data; this workspace has not downloaded it.

## Manual checks performed

Spot-checked key material in PDF text:

- Sec. II.D main model equations (4)--(6) and process terms (7)--(15);
- Table I parameter ranges;
- Sec. III.E derivations for cooling, nucleation, deposition/growth, evaporation, and sedimentation;
- Appendix A constants/functions including nucleation polynomials, saturation vapor pressure, latent heat, diffusivity, sedimentation constants;
- Data Availability statement.

## Known risks

- The HTML equation extractor is intentionally broad and overcounts; curated equation extraction is still needed before code is written.
- Several formulas include symbols that need careful unit interpretation (`n` per dry-air mass vs per volume, `p` in Pa vs hPa, `q` kg/kg dry air, `ρ` dry-air density).
- Model-critical constants/functions (`K_T`, `G_v`, `c` for radius, `n_a=N_a/ρ`, `A_s`, `B_s`) should be verified visually against the rendered HTML/PDF before Phase 2.
- Figure reproduction is blocked until underlying data, parameter grids, initial conditions, and solver settings are curated or obtained.

## Cloud/API tools

None used; no permission requested or needed in Phase 1.
