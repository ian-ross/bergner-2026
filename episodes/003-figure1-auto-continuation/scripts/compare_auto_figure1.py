#!/usr/bin/env python3
"""Compare Episode 3 AUTO Figure 1 branches against Episode 2 benchmarks.

The comparison uses the normalized AUTO branch schema from
``outputs/figure1_auto_branches`` and the Episode 2 Python continuation,
Eq. 92--94 approximation, independent root-solve checks, and digitized Figure 1
artifacts. Shared interpolation, relative-error, summary, and plotting logic
lives in :mod:`bergner_spichtinger_2026.figure1_backend_comparison` so later
backend comparisons can reuse the same backend-neutral branch contract.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from bergner_spichtinger_2026.figure1_backend_comparison import (
    PANEL_SPECS,
    VARIABLES,
    comparison_frames,
    interp_branch_at_log_w as _interp_branch_at_log_w,
    plot_backend_comparison,
    plot_residuals,
    relative_error as _relative_error,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "003-figure1-auto-continuation"
EPISODE2_DIR = REPO_ROOT / "episodes" / "002-figure1-python-continuation"
DEFAULT_AUTO_DIR = EPISODE_DIR / "outputs" / "figure1_auto_branches"
DEFAULT_PYTHON_DIR = EPISODE2_DIR / "outputs" / "figure1_continuation"
DEFAULT_DIGITIZED_DIR = EPISODE2_DIR / "outputs" / "figure1_digitized"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure1_backend_comparison"
DETAIL_COLUMNS = [
    "comparison",
    "reference",
    "variable",
    "T_K",
    "log_w",
    "w_m_s",
    "auto_value",
    "reference_value",
    "signed_diff",
    "abs_diff",
    "rel_diff",
    "auto_residual_norm",
    "reference_residual_norm",
    "reference_converged",
]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _read_inputs(auto_dir: Path, python_dir: Path, digitized_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    auto = pd.read_csv(auto_dir / "branches_all.csv")
    python = pd.read_csv(python_dir / "branches_all.csv")
    python_checks = pd.read_csv(python_dir / "comparison_details.csv")
    digitized = pd.read_csv(digitized_dir / "figure1_digitized_curves.csv")
    return auto, python, python_checks, digitized


def _comparison_frames(auto: pd.DataFrame, python: pd.DataFrame, python_checks: pd.DataFrame, digitized: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return comparison_frames(
        auto,
        backend="auto",
        branch_references=[(python, "auto_vs_python_continuation", "python_continuation_interpolated_on_auto_log_w")],
        python_checks=python_checks,
        digitized=digitized,
        eq_comparison="auto_vs_eq92_94",
        eq_reference="analytic_eq92_94_at_auto_log_w",
        root_comparison="auto_vs_python_root_solve",
        digitized_comparison="auto_vs_digitized_figure1",
    )


def _plot_backend_comparison(auto: pd.DataFrame, python: pd.DataFrame, analytic: pd.DataFrame, digitized: pd.DataFrame, output_path: Path) -> None:
    plot_backend_comparison(
        primary=auto,
        primary_backend="auto",
        overlays=[("Python", python, ":", 1.25)],
        analytic=analytic,
        digitized=digitized,
        output_path=output_path,
        title="Figure 1 backend comparison: solid=AUTO, dotted=Python, dashed=Eq. 92--94, x=digitized paper",
        legend_entries=9,
        legend_columns=3,
        figsize=(13.5, 4.5),
    )


def _plot_residuals(details: pd.DataFrame, output_path: Path) -> None:
    plot_residuals(
        details=details,
        primary_label="AUTO",
        comparisons={"auto_vs_python_continuation": ("Python", ":")},
        output_path=output_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto-dir", type=Path, default=DEFAULT_AUTO_DIR)
    parser.add_argument("--python-dir", type=Path, default=DEFAULT_PYTHON_DIR)
    parser.add_argument("--digitized-dir", type=Path, default=DEFAULT_DIGITIZED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    auto, python, python_checks, digitized = _read_inputs(args.auto_dir, args.python_dir, args.digitized_dir)
    details, summary, analytic = _comparison_frames(auto, python, python_checks, digitized)

    details.to_csv(args.output_dir / "backend_comparison_details.csv", index=False)
    summary.to_csv(args.output_dir / "backend_comparison_summary.csv", index=False)
    (args.output_dir / "backend_comparison_summary.json").write_text(json.dumps(summary.to_dict(orient="records"), indent=2), encoding="utf-8")

    _plot_backend_comparison(auto, python, analytic, digitized, args.output_dir / "figure1_backend_comparison.png")
    _plot_residuals(details, args.output_dir / "figure1_backend_residuals.png")

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "auto_dir": _display_path(args.auto_dir),
            "python_dir": _display_path(args.python_dir),
            "digitized_dir": _display_path(args.digitized_dir),
        },
        "method": {
            "shared_utility": "Common interpolation, relative-error, summary, and plotting logic is provided by bergner_spichtinger_2026.figure1_backend_comparison.",
            "auto_vs_python": "Python continuation n, q, and s are interpolated onto AUTO log_w points; n and q use log-value interpolation.",
            "auto_vs_eq92_94": "Eq. 92--94 approximations are evaluated at each AUTO branch point.",
            "auto_vs_python_root_solve": "AUTO n, q, and s are interpolated onto independent Python root-solve check points.",
            "auto_vs_digitized": "AUTO n, q, and s are interpolated onto digitized paper Figure 1 w points; n and q use log-value interpolation.",
            "relative_error": "abs(a-b) / max(abs(a), abs(b), tiny)",
        },
        "outputs": [
            "backend_comparison_details.csv",
            "backend_comparison_summary.csv",
            "backend_comparison_summary.json",
            "figure1_backend_comparison.png",
            "figure1_backend_residuals.png",
            "run_metadata.json",
        ],
    }
    (args.output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote Figure 1 backend comparison artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
