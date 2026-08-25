# TASK-080 final Figure 5 artifacts

TASK-080 assembles the final Episode 008 Figure 5 reproduction outputs from the completed production, validation, browser, and paper-digitization evidence.

## Artifacts and commands

Final outputs:

- [`../outputs/figure5_final_reproduction.png`](../outputs/figure5_final_reproduction.png) — paper-facing two-panel reproduction/overlay plot.
- [`../outputs/figure5_final_browser_dataset.json`](../outputs/figure5_final_browser_dataset.json) — production-v1 schema-valid browser/display payload.
- [`../outputs/figure5_final_paper_comparison.json`](../outputs/figure5_final_paper_comparison.json) — machine-readable paper-comparison report and discrepancy ledger.

Regenerate or verify them with:

```bash
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_figure5_final_artifacts.py
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_figure5_final_artifacts.py --check
uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py \
  episodes/008-figure5-periodic-orbit-continuation/outputs/figure5_final_browser_dataset.json
```

## Evidence assembled

The final browser dataset starts from the TASK-079 browser/display records, removes the pre-TASK-063 pending comparison placeholders, and adds real TASK-063 image-derived comparison overlays:

- upper-panel period-map color samples from `paper_figure5_digitization_upper_period_samples.csv`;
- lower-panel black nonlinear and red equilibrium-linearized curves from `paper_figure5_digitization_lower_curves.csv`;
- all TASK-075/TASK-076/TASK-079 solved, unresolved-gap, Hopf-gap, invalid-domain, and TASK-074 linearized records with production-record source links preserved.

The current numerical outcome remains conservative: only `spine-210K` is an accepted native nonlinear production point; no nonlinear interpolation records are emitted; 297 full-domain targets remain explicit unresolved gaps; and the lower panel uses TASK-075 nonlinear continuation plus the independent TASK-074 linearized curve, not heatmap resampling.

## Paper comparison policy

TASK-063 digitized paper data are lossy JPEG-derived external evidence. The final artifacts encode them with `validity.status = external_comparison`, `validity.source = external_digitized_paper_comparison`, and `authoritative = false`.

The comparison report applies the TASK-062/TASK-069 discrepancy rule:

```text
abs(delta_log_period_natural) <= max(3*sigma_digitized_log_period_natural, 0.02)
```

Rows outside that tolerance are flagged as `discrepancy_requires_investigation`. Such discrepancies do **not** override native continuation convergence, Floquet diagnostics, independent IVP validation, explicit-gap records, or TASK-074 linearized-period validation.

## Browser/data boundary

`figure5_final_browser_dataset.json` is a compact data-only payload: calibrated coordinates, periods, uncertainty summaries, validity/source flags, and source links. It does not include raw raster pixels, notebook state, transient cache files, or Episode 007 widget integration code. Future browser/widget integration should consume this dataset rather than modifying Episode 008 production artifacts.
