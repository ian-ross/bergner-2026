#!/usr/bin/env python3
"""Compare Episode 3 AUTO Figure 1 branches against Episode 2 benchmarks.

The comparison uses the normalized AUTO branch schema from
``outputs/figure1_auto_branches`` and the Episode 2 Python continuation,
Eq. 92--94 approximation, independent root-solve checks, and digitized Figure 1
artifacts.  Outputs are deterministic CSV/JSON/PNG artifacts intended to be
curated with the Episode 3 backend comparison.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bergner_spichtinger_2026.approximations import approximate_equilibrium
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "003-figure1-auto-continuation"
EPISODE2_DIR = REPO_ROOT / "episodes" / "002-figure1-python-continuation"
DEFAULT_AUTO_DIR = EPISODE_DIR / "outputs" / "figure1_auto_branches"
DEFAULT_PYTHON_DIR = EPISODE2_DIR / "outputs" / "figure1_continuation"
DEFAULT_DIGITIZED_DIR = EPISODE2_DIR / "outputs" / "figure1_digitized"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure1_backend_comparison"

PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0
VARIABLES = ("n", "q", "s")
LOG_INTERP_VARIABLES = {"n", "q"}
TEMPERATURE_COLORS = {190.0: "#1f77ff", 210.0: "#7f7f7f", 230.0: "#d62728"}
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


def _relative_error(value: float, reference: float) -> float:
    denom = max(abs(float(value)), abs(float(reference)), np.finfo(float).tiny)
    return abs(float(value) - float(reference)) / denom


def _read_inputs(auto_dir: Path, python_dir: Path, digitized_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    auto = pd.read_csv(auto_dir / "branches_all.csv")
    python = pd.read_csv(python_dir / "branches_all.csv")
    python_checks = pd.read_csv(python_dir / "comparison_details.csv")
    digitized = pd.read_csv(digitized_dir / "figure1_digitized_curves.csv")
    return auto, python, python_checks, digitized


def _interp_branch_at_log_w(branch: pd.DataFrame, variable: str, log_w: Iterable[float]) -> np.ndarray:
    """Interpolate a branch variable at requested log-w values.

    Positive concentration variables are interpolated in log-value space; the
    saturation ratio is interpolated linearly.  Input points outside the branch
    log-w range are intentionally rejected to avoid hidden extrapolation.
    """
    if variable not in VARIABLES:
        raise ValueError(f"unsupported variable {variable!r}")
    branch = branch.sort_values("log_w")
    x = branch["log_w"].to_numpy(dtype=float)
    x_new = np.asarray(list(log_w), dtype=float)
    if len(x) < 2:
        raise ValueError("at least two branch points are required for interpolation")
    tolerance = 1.0e-8
    if x_new.min(initial=x[0]) < x.min() - tolerance or x_new.max(initial=x[-1]) > x.max() + tolerance:
        raise ValueError("requested interpolation point falls outside branch log_w range")
    x_new = np.clip(x_new, x.min(), x.max())
    y = branch[variable].to_numpy(dtype=float)
    if variable in LOG_INTERP_VARIABLES:
        if np.any(y <= 0):
            raise ValueError(f"{variable} must be positive for log-space interpolation")
        return np.exp(np.interp(x_new, x, np.log(y)))
    return np.interp(x_new, x, y)


def _analytic_frame(auto: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for row in auto.itertuples(index=False):
        aerosol_n_a = float(getattr(row, "N_a_m3", N_a_figure1_high))
        env = Environment(p=PRESSURE_PA, T=float(row.T_K), w=float(row.w_m_s), F=SEDIMENTATION_F, N_a=aerosol_n_a)
        n, q, s = approximate_equilibrium(env)
        rows.append({"T_K": float(row.T_K), "log_w": float(row.log_w), "w_m_s": float(row.w_m_s), "n": float(n), "q": float(q), "s": float(s)})
    return pd.DataFrame(rows)


def _detail_row(
    *,
    comparison: str,
    reference: str,
    variable: str,
    T: float,
    log_w: float,
    w_m_s: float,
    auto_value: float,
    reference_value: float,
    auto_residual_norm: float | None = None,
    reference_residual_norm: float | None = None,
    reference_converged: bool | None = None,
) -> dict[str, object]:
    signed = float(auto_value) - float(reference_value)
    return {
        "comparison": comparison,
        "reference": reference,
        "variable": variable,
        "T_K": float(T),
        "log_w": float(log_w),
        "w_m_s": float(w_m_s),
        "auto_value": float(auto_value),
        "reference_value": float(reference_value),
        "signed_diff": signed,
        "abs_diff": abs(signed),
        "rel_diff": _relative_error(auto_value, reference_value),
        "auto_residual_norm": auto_residual_norm,
        "reference_residual_norm": reference_residual_norm,
        "reference_converged": reference_converged,
    }


def _auto_vs_python(auto: pd.DataFrame, python: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for T, auto_t in auto.groupby("T_K", sort=True):
        python_t = python[python["T_K"] == float(T)]
        log_ws = auto_t["log_w"].to_numpy(dtype=float)
        for variable in VARIABLES:
            python_values = _interp_branch_at_log_w(python_t, variable, log_ws)
            for source_row, reference_value in zip(auto_t.itertuples(index=False), python_values, strict=True):
                rows.append(
                    _detail_row(
                        comparison="auto_vs_python_continuation",
                        reference="python_continuation_interpolated_on_auto_log_w",
                        variable=variable,
                        T=float(T),
                        log_w=float(source_row.log_w),
                        w_m_s=float(source_row.w_m_s),
                        auto_value=float(getattr(source_row, variable)),
                        reference_value=float(reference_value),
                        auto_residual_norm=float(getattr(source_row, "residual_norm", np.nan)),
                        reference_converged=True,
                    )
                )
    return pd.DataFrame(rows, columns=DETAIL_COLUMNS)


def _auto_vs_eq(auto: pd.DataFrame, analytic: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for source_row, analytic_row in zip(auto.sort_values(["T_K", "log_w"]).itertuples(index=False), analytic.sort_values(["T_K", "log_w"]).itertuples(index=False), strict=True):
        for variable in VARIABLES:
            rows.append(
                _detail_row(
                    comparison="auto_vs_eq92_94",
                    reference="analytic_eq92_94_at_auto_log_w",
                    variable=variable,
                    T=float(source_row.T_K),
                    log_w=float(source_row.log_w),
                    w_m_s=float(source_row.w_m_s),
                    auto_value=float(getattr(source_row, variable)),
                    reference_value=float(getattr(analytic_row, variable)),
                    auto_residual_norm=float(getattr(source_row, "residual_norm", np.nan)),
                    reference_converged=True,
                )
            )
    return pd.DataFrame(rows, columns=DETAIL_COLUMNS)


def _auto_vs_python_root_checks(auto: pd.DataFrame, checks: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    root_checks = checks[checks["source"] == "root_solve"]
    for T, checks_t in root_checks.groupby("T_K", sort=True):
        auto_t = auto[auto["T_K"] == float(T)]
        log_ws = checks_t["log_w"].to_numpy(dtype=float)
        for variable in VARIABLES:
            auto_values = _interp_branch_at_log_w(auto_t, variable, log_ws)
            for source_row, auto_value in zip(checks_t.itertuples(index=False), auto_values, strict=True):
                rows.append(
                    _detail_row(
                        comparison="auto_vs_python_root_solve",
                        reference="python_independent_root_solve_checks",
                        variable=variable,
                        T=float(T),
                        log_w=float(source_row.log_w),
                        w_m_s=float(source_row.w_m_s),
                        auto_value=float(auto_value),
                        reference_value=float(getattr(source_row, f"{variable}_check")),
                        reference_residual_norm=float(getattr(source_row, "check_residual_norm", np.nan)),
                        reference_converged=bool(getattr(source_row, "check_converged", True)),
                    )
                )
    return pd.DataFrame(rows, columns=DETAIL_COLUMNS)


def _auto_vs_digitized(auto: pd.DataFrame, digitized: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for variable, spec in PANEL_SPECS.items():
        panel = spec["digitized_panel"]
        panel_rows = digitized[digitized["panel"] == panel]
        for T, digitized_t in panel_rows.groupby("T_K", sort=True):
            auto_t = auto[auto["T_K"] == float(T)]
            log_ws = np.log(digitized_t["w_m_s"].to_numpy(dtype=float))
            auto_values = _interp_branch_at_log_w(auto_t, variable, log_ws)
            for source_row, auto_value in zip(digitized_t.itertuples(index=False), auto_values, strict=True):
                rows.append(
                    _detail_row(
                        comparison="auto_vs_digitized_figure1",
                        reference=f"digitized_paper_{panel}",
                        variable=variable,
                        T=float(T),
                        log_w=float(np.log(source_row.w_m_s)),
                        w_m_s=float(source_row.w_m_s),
                        auto_value=float(auto_value),
                        reference_value=float(source_row.value),
                    )
                )
    return pd.DataFrame(rows, columns=DETAIL_COLUMNS)


def _comparison_frames(auto: pd.DataFrame, python: pd.DataFrame, python_checks: pd.DataFrame, digitized: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    analytic = _analytic_frame(auto)
    details = pd.concat(
        [
            _auto_vs_python(auto, python),
            _auto_vs_eq(auto, analytic),
            _auto_vs_python_root_checks(auto, python_checks),
            _auto_vs_digitized(auto, digitized),
        ],
        ignore_index=True,
    )
    summary_rows: list[dict[str, object]] = []
    for (comparison, reference, variable, T), group in details.groupby(["comparison", "reference", "variable", "T_K"], sort=True):
        summary_rows.append(
            {
                "comparison": comparison,
                "reference": reference,
                "variable": variable,
                "T_K": float(T),
                "sample_count": int(len(group)),
                "median_signed_diff": float(group["signed_diff"].median()),
                "median_abs_diff": float(group["abs_diff"].median()),
                "max_abs_diff": float(group["abs_diff"].max()),
                "median_rel_diff": float(group["rel_diff"].median()),
                "max_rel_diff": float(group["rel_diff"].max()),
                "max_auto_residual_norm": float(group["auto_residual_norm"].max(skipna=True)) if group["auto_residual_norm"].notna().any() else None,
                "max_reference_residual_norm": float(group["reference_residual_norm"].max(skipna=True)) if group["reference_residual_norm"].notna().any() else None,
                "all_reference_converged": bool(group["reference_converged"].dropna().all()) if group["reference_converged"].notna().any() else None,
            }
        )
    return details, pd.DataFrame(summary_rows), analytic


def _plot_backend_comparison(auto: pd.DataFrame, python: pd.DataFrame, analytic: pd.DataFrame, digitized: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.5), sharex=True)
    for ax, (variable, spec) in zip(axes, PANEL_SPECS.items(), strict=True):
        for T, color in TEMPERATURE_COLORS.items():
            auto_t = auto[auto["T_K"] == T].sort_values("w_m_s")
            python_t = python[python["T_K"] == T].sort_values("w_m_s")
            analytic_t = analytic[analytic["T_K"] == T].sort_values("w_m_s")
            paper_t = digitized[(digitized["T_K"] == int(T)) & (digitized["panel"] == spec["digitized_panel"])]
            ax.plot(auto_t["w_m_s"], auto_t[variable], color=color, lw=2.2, label=f"{int(T)} K AUTO")
            ax.plot(python_t["w_m_s"], python_t[variable], color=color, lw=1.25, ls=":", alpha=0.9, label=f"{int(T)} K Python")
            ax.plot(analytic_t["w_m_s"], analytic_t[variable], color=color, lw=1.0, ls="--", alpha=0.8, label=f"{int(T)} K Eq. 92--94")
            if not paper_t.empty:
                ax.scatter(paper_t["w_m_s"], paper_t["value"], s=8, marker="x", color=color, alpha=0.4, linewidths=0.7, zorder=3)
        ax.set_xscale("log")
        ax.set_yscale(str(spec["yscale"]))
        ax.set_xlim(0.005, 2.0)
        ax.set_ylim(*spec["ylim"])
        ax.set_xlabel(r"vertical velocity $w$ (m s$^{-1}$)")
        ax.set_ylabel(str(spec["ylabel"]))
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.55)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles[:9], labels[:9], loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle("Figure 1 backend comparison: solid=AUTO, dotted=Python, dashed=Eq. 92--94, x=digitized paper", y=1.15)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_residuals(details: pd.DataFrame, output_path: Path) -> None:
    selected = details[details["comparison"] == "auto_vs_python_continuation"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharex=True)
    for ax, variable in zip(axes, VARIABLES, strict=True):
        for T, color in TEMPERATURE_COLORS.items():
            group = selected[(selected["variable"] == variable) & (selected["T_K"] == T)].sort_values("w_m_s")
            ax.axhline(0.0, color="black", lw=0.8, alpha=0.5)
            ax.plot(group["w_m_s"], 100.0 * group["rel_diff"], color=color, lw=1.4, label=f"{int(T)} K")
        ax.set_xscale("log")
        ax.set_xlim(0.005, 2.0)
        ax.set_xlabel(r"vertical velocity $w$ (m s$^{-1}$)")
        ax.set_ylabel(f"{variable}: |AUTO-Python| / max (%)")
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.55)
    axes[-1].legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


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
            "auto_dir": str(args.auto_dir.relative_to(REPO_ROOT)),
            "python_dir": str(args.python_dir.relative_to(REPO_ROOT)),
            "digitized_dir": str(args.digitized_dir.relative_to(REPO_ROOT)),
        },
        "method": {
            "auto_vs_python": "Python continuation n, q, and s are interpolated onto AUTO log_w points; n and q use log-value interpolation.",
            "auto_vs_eq92_94": "Eq. 92--94 approximations are evaluated at each AUTO branch point.",
            "auto_vs_digitized": "AUTO n, q, and s are interpolated onto digitized paper Figure 1 w points; n and q use log-value interpolation.",
            "relative_error": "abs(a-b) / max(abs(a), abs(b), tiny)",
        },
        "outputs": [
            "backend_comparison_details.csv",
            "backend_comparison_summary.csv",
            "backend_comparison_summary.json",
            "figure1_backend_comparison.png",
            "figure1_backend_residuals.png",
        ],
    }
    (args.output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote Figure 1 backend comparison artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
