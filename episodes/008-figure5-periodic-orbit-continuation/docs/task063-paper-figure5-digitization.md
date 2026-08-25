# TASK-063 paper Figure 5 digitization

TASK-063 creates a reproducible, image-derived reference dataset for both panels of Bergner & Spichtinger (2026) Figure 5. The dataset is an external comparison target only: it is not a native LOCA, Python collocation, IVP, Floquet, or equilibrium-eigenvalue result, and agreement with the digitized pixels must not override numerical convergence or independent validation gates.

## Reproduce or verify

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_paper_figure5_digitization.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_paper_figure5_digitization.py --check
```

The generator reads the saved publisher Figure 5 image under `sources/original/bergner-spichtinger-2026_files/` and records the saved source PDF checksum as provenance. Source originals are read-only inputs and are not modified.

## Artifacts

- `outputs/paper_figure5_digitization.json` — schema, calibration, source checksums, uncertainty limits, validation metrics, and links to all emitted files.
- `outputs/paper_figure5_digitization_upper_hopf_boundaries.csv` — direct upper-panel colored-domain edge samples for the lower and upper Hopf boundaries, calibrated to `temperature_K` and `w_m_s`.
- `outputs/paper_figure5_digitization_upper_period_samples.csv` — direct upper-panel color samples inside the digitized Hopf band. Period values are obtained by matching the sampled RGB color to the saved raster colorbar and are labeled `direct_digitized_color_sample`.
- `outputs/paper_figure5_digitization_lower_curves.csv` — direct lower-panel curve-pixel samples for the red equilibrium-linearized-period curve and the black nonlinear limit-cycle-period curve at `T = 210 K`.
- `outputs/paper_figure5_digitization_overlay.png` — visual overlay of extracted boundaries/curves on the source image.
- `outputs/paper_figure5_digitization_residuals.png` — residual diagnostic plot for colorbar matching plus axis-calibration residual summary.

## Calibration and limits

The upper panel uses a linear temperature axis from `190--240 K` and a log10 vertical-velocity axis from `5e-4--2 m s^-1`. The lower panel uses the same log10 vertical-velocity range and a linear period axis from `0--18000 s`. The colorbar maps log10 period from `10^2--10^5 s`.

Every coordinate inherits at least half-pixel uncertainty. The JSON artifact records the corresponding coordinate limits; for example, the lower-panel period half-pixel limit is about `28.6 s`, and the upper-panel colorbar half-pixel limit is about `0.0044` in `log10(period_s)`. JPEG antialiasing, line thickness, grid lines, and colorbar quantization are additional image-derived limitations.

No interpolation rows are emitted. Boundary rows and lower-curve rows are direct detected image pixels. Upper color rows are direct calibrated pixel samples whose period is looked up against the paper colorbar; they should be used as noisy image evidence, not as reconstructed author data.

## Comparison policy

For future Python/LOCA comparison:

1. compare backend period values in log period space against the digitized paper samples or curves;
2. treat discrepancies larger than `max(3*sigma_digitized_logP, 0.02)` as an investigation trigger, following the Episode 008 decision record;
3. never tune continuation, remeshing, Hopf-limit policy, or interpolation to match digitized pixels; and
4. prefer native convergence/defect gates, Python parity, independent IVP validation, and the independent TASK-074 linearized-period calculation over apparent pixel agreement.

The pre-existing TASK-079 browser dataset still records TASK-063 comparison placeholders because it was generated before this digitization. A later browser/paper-comparison task can incorporate these files as `external_digitized_paper_comparison` overlays while keeping them non-authoritative.
