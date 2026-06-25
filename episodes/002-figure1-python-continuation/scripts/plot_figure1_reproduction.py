#!/usr/bin/env python3
"""Produce the Episode 2 Figure 1 reproduction and comparison artifacts.

The plot overlays three evidence streams for the Figure 1 equilibrium branch
family: generated Python continuation curves, Eq. 92--94 analytic approximation
curves, and digitized curves from the rendered paper figure.  Independent root
solve checks are shown as sampled markers.  A companion residual plot compares
continuation values against the digitized paper curves at the digitized w points.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bergner_spichtinger_2026.approximations import approximate_equilibrium
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "002-figure1-python-continuation"
DEFAULT_CONTINUATION_DIR = EPISODE_DIR / "outputs" / "figure1_continuation"
DEFAULT_DIGITIZED_DIR = EPISODE_DIR / "outputs" / "figure1_digitized"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure1_reproduction"
PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0

TEMPERATURE_COLORS = {
    190.0: "#1f77ff",
    210.0: "#7f7f7f",
    230.0: "#d62728",
}
PANEL_SPECS = {
    "n": {
        "digitized_panel": "number_concentration",
        "ylabel": r"ice crystal number concentration $n$ (kg$^{-1}$)",
        "yscale": "log",
        "ylim": (1e3, 1e7),
    },
    "q": {
        "digitized_panel": "mass_concentration",
        "ylabel": r"ice crystal mass concentration $q$ (kg kg$^{-1}$)",
        "yscale": "log",
        "ylim": (1e-8, 1e-3),
    },
    "s": {
        "digitized_panel": "saturation_ratio",
        "ylabel": r"saturation ratio $s$ (-)",
        "yscale": "linear",
        "ylim": (1.4, 1.6),
    },
}


def _read_inputs(continuation_dir: Path, digitized_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    branches = pd.read_csv(continuation_dir / "branches_all.csv")
    checks = pd.read_csv(continuation_dir / "comparison_details.csv")
    digitized = pd.read_csv(digitized_dir / "figure1_digitized_curves.csv")
    return branches, checks, digitized


def _analytic_frame(branches: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for row in branches.itertuples(index=False):
        aerosol_n_a = float(getattr(row, "N_a_m3", N_a_figure1_high))
        env = Environment(p=PRESSURE_PA, T=float(row.T_K), w=float(row.w_m_s), F=SEDIMENTATION_F, N_a=aerosol_n_a)
        n, q, s = approximate_equilibrium(env)
        rows.append({"T_K": float(row.T_K), "w_m_s": float(row.w_m_s), "n": float(n), "q": float(q), "s": float(s)})
    return pd.DataFrame(rows)


def _interp_generated_at_digitized(branch: pd.DataFrame, variable: str, w: np.ndarray) -> np.ndarray:
    branch = branch.sort_values("w_m_s")
    x = np.log(branch["w_m_s"].to_numpy(dtype=float))
    x_new = np.log(w)
    y = branch[variable].to_numpy(dtype=float)
    if variable in {"n", "q"}:
        return np.exp(np.interp(x_new, x, np.log(y)))
    return np.interp(x_new, x, y)


def _digitized_comparison(branches: pd.DataFrame, digitized: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, float | str]] = []
    for variable, spec in PANEL_SPECS.items():
        panel = spec["digitized_panel"]
        for T, group in digitized[digitized["panel"] == panel].groupby("T_K"):
            branch = branches[branches["T_K"] == float(T)]
            generated = _interp_generated_at_digitized(branch, variable, group["w_m_s"].to_numpy(dtype=float))
            paper = group["value"].to_numpy(dtype=float)
            for source_row, generated_value, paper_value in zip(group.itertuples(index=False), generated, paper, strict=True):
                rows.append(
                    {
                        "variable": variable,
                        "panel": panel,
                        "T_K": float(T),
                        "w_m_s": float(source_row.w_m_s),
                        "continuation_value": float(generated_value),
                        "digitized_value": float(paper_value),
                        "signed_relative_error": float((generated_value - paper_value) / paper_value),
                        "absolute_error": float(abs(generated_value - paper_value)),
                    }
                )
    details = pd.DataFrame(rows)
    summary_rows: list[dict[str, float | str | int]] = []
    for (variable, T), group in details.groupby(["variable", "T_K"], sort=True):
        abs_rel = group["signed_relative_error"].abs()
        summary_rows.append(
            {
                "variable": variable,
                "T_K": float(T),
                "sample_count": int(len(group)),
                "median_abs_relative_error": float(abs_rel.median()),
                "max_abs_relative_error": float(abs_rel.max()),
                "median_absolute_error": float(group["absolute_error"].median()),
                "max_absolute_error": float(group["absolute_error"].max()),
            }
        )
    return details, pd.DataFrame(summary_rows)


def _plot_reproduction(branches: pd.DataFrame, analytic: pd.DataFrame, checks: pd.DataFrame, digitized: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharex=True)
    for ax, (variable, spec) in zip(axes, PANEL_SPECS.items(), strict=True):
        for T, color in TEMPERATURE_COLORS.items():
            branch_t = branches[branches["T_K"] == T].sort_values("w_m_s")
            analytic_t = analytic[analytic["T_K"] == T].sort_values("w_m_s")
            ax.plot(branch_t["w_m_s"], branch_t[variable], color=color, lw=2.2, label=f"{int(T)} K continuation")
            ax.plot(analytic_t["w_m_s"], analytic_t[variable], color=color, lw=1.25, ls="--", alpha=0.9, label=f"{int(T)} K Eq. 92--94")

            root_t = checks[(checks["T_K"] == T) & (checks["source"] == "root_solve")]
            if not root_t.empty:
                ax.scatter(root_t["w_m_s"], root_t[f"{variable}_check"], s=16, marker="o", facecolors="none", edgecolors=color, linewidths=0.9, zorder=4)

            paper_t = digitized[(digitized["T_K"] == int(T)) & (digitized["panel"] == spec["digitized_panel"])]
            if not paper_t.empty:
                ax.scatter(paper_t["w_m_s"], paper_t["value"], s=8, marker="x", color=color, alpha=0.45, linewidths=0.7, zorder=3)

        ax.set_xscale("log")
        ax.set_yscale(str(spec["yscale"]))
        ax.set_xlim(0.005, 2.0)
        ax.set_ylim(*spec["ylim"])
        ax.set_xlabel(r"vertical velocity $w$ (m s$^{-1}$)")
        ax.set_ylabel(str(spec["ylabel"]))
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.55)

    handles, labels = axes[0].get_legend_handles_labels()
    # Keep the legend focused on the line encodings; marker encodings are noted in the title.
    fig.legend(handles[:6], labels[:6], loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.03))
    fig.suptitle("Figure 1 reproduction: solid=Python continuation, dashed=Eq. 92--94, open circles=root checks, x=digitized paper", y=1.12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_residuals(details: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharex=True)
    for ax, variable in zip(axes, PANEL_SPECS, strict=True):
        for T, color in TEMPERATURE_COLORS.items():
            group = details[(details["variable"] == variable) & (details["T_K"] == T)].sort_values("w_m_s")
            ax.axhline(0.0, color="black", lw=0.8, alpha=0.5)
            ax.plot(group["w_m_s"], 100.0 * group["signed_relative_error"], color=color, lw=1.4, label=f"{int(T)} K")
        ax.set_xscale("log")
        ax.set_xlim(0.005, 2.0)
        ax.set_xlabel(r"vertical velocity $w$ (m s$^{-1}$)")
        ax.set_ylabel(f"{variable}: continuation - digitized (%)")
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.55)
    axes[-1].legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuation-dir", type=Path, default=DEFAULT_CONTINUATION_DIR)
    parser.add_argument("--digitized-dir", type=Path, default=DEFAULT_DIGITIZED_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    branches, checks, digitized = _read_inputs(args.continuation_dir, args.digitized_dir)
    analytic = _analytic_frame(branches)
    details, summary = _digitized_comparison(branches, digitized)

    reproduction_png = args.output_dir / "figure1_reproduction.png"
    residuals_png = args.output_dir / "figure1_digitized_residuals.png"
    _plot_reproduction(branches, analytic, checks, digitized, reproduction_png)
    _plot_residuals(details, residuals_png)

    details.to_csv(args.output_dir / "digitized_comparison_details.csv", index=False)
    summary.to_csv(args.output_dir / "digitized_comparison_summary.csv", index=False)
    metadata = {
        "inputs": {
            "continuation_dir": str(args.continuation_dir.relative_to(REPO_ROOT)),
            "digitized_dir": str(args.digitized_dir.relative_to(REPO_ROOT)),
        },
        "outputs": [
            "figure1_reproduction.png",
            "figure1_digitized_residuals.png",
            "digitized_comparison_details.csv",
            "digitized_comparison_summary.csv",
        ],
        "plot_encoding": {
            "temperatures_K": {str(int(k)): v for k, v in TEMPERATURE_COLORS.items()},
            "solid_lines": "Python continuation",
            "dashed_lines": "Eq. 92--94 analytic approximation",
            "open_circles": "independent root-solve checks sampled from comparison_details.csv",
            "x_markers": "digitized paper curves from rendered Figure 1",
        },
    }
    (args.output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote Figure 1 reproduction artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
