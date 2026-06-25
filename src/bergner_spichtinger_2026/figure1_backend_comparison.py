"""Shared Figure 1 backend-comparison utilities.

Episodes 3 and 4 compare normalized backend branch CSV files against the same
Python continuation, Eq. 92--94 approximation, root-solve checks, and digitized
paper curves.  This module centralizes the backend-neutral interpolation,
relative-error, summary, and plotting logic while leaving episode scripts in
charge of their command-line interfaces and curated output locations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bergner_spichtinger_2026.approximations import approximate_equilibrium
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high

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
BASE_DETAIL_COLUMNS = [
    "comparison",
    "reference",
    "variable",
    "T_K",
    "log_w",
    "w_m_s",
    "reference_value",
    "signed_diff",
    "abs_diff",
    "rel_diff",
    "reference_residual_norm",
    "reference_converged",
]


def backend_detail_columns(backend: str) -> list[str]:
    """Return detail CSV columns for a primary backend name."""
    return [*BASE_DETAIL_COLUMNS[:6], f"{backend}_value", *BASE_DETAIL_COLUMNS[6:10], f"{backend}_residual_norm", *BASE_DETAIL_COLUMNS[10:]]


def relative_error(value: float, reference: float) -> float:
    """Relative error convention shared by backend comparison scripts."""
    denom = max(abs(float(value)), abs(float(reference)), np.finfo(float).tiny)
    return abs(float(value) - float(reference)) / denom


def interp_branch_at_log_w(branch: pd.DataFrame, variable: str, log_w: Iterable[float]) -> np.ndarray:
    """Interpolate a backend-neutral branch variable at requested log-w values.

    Positive concentration variables (``n`` and ``q``) are interpolated in
    log-value space; saturation ratio is interpolated linearly.  Requests
    outside branch support are rejected to avoid hidden extrapolation.
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


def analytic_frame(primary: pd.DataFrame) -> pd.DataFrame:
    """Evaluate Eq. 92--94 approximation at each primary branch point."""
    rows: list[dict[str, float]] = []
    for row in primary.itertuples(index=False):
        aerosol_n_a = float(getattr(row, "N_a_m3", N_a_figure1_high))
        env = Environment(p=PRESSURE_PA, T=float(row.T_K), w=float(row.w_m_s), F=SEDIMENTATION_F, N_a=aerosol_n_a)
        n, q, s = approximate_equilibrium(env)
        rows.append({"T_K": float(row.T_K), "log_w": float(row.log_w), "w_m_s": float(row.w_m_s), "n": float(n), "q": float(q), "s": float(s)})
    return pd.DataFrame(rows)


def _detail_row(
    *,
    backend: str,
    comparison: str,
    reference: str,
    variable: str,
    T: float,
    log_w: float,
    w_m_s: float,
    backend_value: float,
    reference_value: float,
    backend_residual_norm: float | None = None,
    reference_residual_norm: float | None = None,
    reference_converged: bool | None = None,
) -> dict[str, object]:
    signed = float(backend_value) - float(reference_value)
    return {
        "comparison": comparison,
        "reference": reference,
        "variable": variable,
        "T_K": float(T),
        "log_w": float(log_w),
        "w_m_s": float(w_m_s),
        f"{backend}_value": float(backend_value),
        "reference_value": float(reference_value),
        "signed_diff": signed,
        "abs_diff": abs(signed),
        "rel_diff": relative_error(backend_value, reference_value),
        f"{backend}_residual_norm": backend_residual_norm,
        "reference_residual_norm": reference_residual_norm,
        "reference_converged": reference_converged,
    }


def compare_primary_to_branch(primary: pd.DataFrame, reference_branch: pd.DataFrame, *, backend: str, comparison: str, reference: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for T, primary_t in primary.groupby("T_K", sort=True):
        ref_t = reference_branch[reference_branch["T_K"] == float(T)]
        log_ws = primary_t["log_w"].to_numpy(dtype=float)
        for variable in VARIABLES:
            reference_values = interp_branch_at_log_w(ref_t, variable, log_ws)
            for source_row, reference_value in zip(primary_t.itertuples(index=False), reference_values, strict=True):
                rows.append(
                    _detail_row(
                        backend=backend,
                        comparison=comparison,
                        reference=reference,
                        variable=variable,
                        T=float(T),
                        log_w=float(source_row.log_w),
                        w_m_s=float(source_row.w_m_s),
                        backend_value=float(getattr(source_row, variable)),
                        reference_value=float(reference_value),
                        backend_residual_norm=float(getattr(source_row, "residual_norm", np.nan)),
                        reference_converged=True,
                    )
                )
    return pd.DataFrame(rows, columns=backend_detail_columns(backend))


def compare_primary_to_eq(primary: pd.DataFrame, analytic: pd.DataFrame, *, backend: str, comparison: str, reference: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    primary_sorted = primary.sort_values(["T_K", "log_w"])
    analytic_sorted = analytic.sort_values(["T_K", "log_w"])
    for source_row, analytic_row in zip(primary_sorted.itertuples(index=False), analytic_sorted.itertuples(index=False), strict=True):
        for variable in VARIABLES:
            rows.append(
                _detail_row(
                    backend=backend,
                    comparison=comparison,
                    reference=reference,
                    variable=variable,
                    T=float(source_row.T_K),
                    log_w=float(source_row.log_w),
                    w_m_s=float(source_row.w_m_s),
                    backend_value=float(getattr(source_row, variable)),
                    reference_value=float(getattr(analytic_row, variable)),
                    backend_residual_norm=float(getattr(source_row, "residual_norm", np.nan)),
                    reference_converged=True,
                )
            )
    return pd.DataFrame(rows, columns=backend_detail_columns(backend))


def compare_primary_to_root_checks(primary: pd.DataFrame, checks: pd.DataFrame, *, backend: str, comparison: str, reference: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    root_checks = checks[checks["source"] == "root_solve"]
    for T, checks_t in root_checks.groupby("T_K", sort=True):
        primary_t = primary[primary["T_K"] == float(T)]
        log_ws = checks_t["log_w"].to_numpy(dtype=float)
        for variable in VARIABLES:
            backend_values = interp_branch_at_log_w(primary_t, variable, log_ws)
            for source_row, backend_value in zip(checks_t.itertuples(index=False), backend_values, strict=True):
                rows.append(
                    _detail_row(
                        backend=backend,
                        comparison=comparison,
                        reference=reference,
                        variable=variable,
                        T=float(T),
                        log_w=float(source_row.log_w),
                        w_m_s=float(source_row.w_m_s),
                        backend_value=float(backend_value),
                        reference_value=float(getattr(source_row, f"{variable}_check")),
                        reference_residual_norm=float(getattr(source_row, "check_residual_norm", np.nan)),
                        reference_converged=bool(getattr(source_row, "check_converged", True)),
                    )
                )
    return pd.DataFrame(rows, columns=backend_detail_columns(backend))


def compare_primary_to_digitized(primary: pd.DataFrame, digitized: pd.DataFrame, *, backend: str, comparison: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for variable, spec in PANEL_SPECS.items():
        panel = str(spec["digitized_panel"])
        panel_rows = digitized[digitized["panel"] == panel]
        for T, digitized_t in panel_rows.groupby("T_K", sort=True):
            primary_t = primary[primary["T_K"] == float(T)]
            log_ws = np.log(digitized_t["w_m_s"].to_numpy(dtype=float))
            backend_values = interp_branch_at_log_w(primary_t, variable, log_ws)
            for source_row, backend_value in zip(digitized_t.itertuples(index=False), backend_values, strict=True):
                rows.append(
                    _detail_row(
                        backend=backend,
                        comparison=comparison,
                        reference=f"digitized_paper_{panel}",
                        variable=variable,
                        T=float(T),
                        log_w=float(np.log(source_row.w_m_s)),
                        w_m_s=float(source_row.w_m_s),
                        backend_value=float(backend_value),
                        reference_value=float(source_row.value),
                    )
                )
    return pd.DataFrame(rows, columns=backend_detail_columns(backend))


def summarize_details(details: pd.DataFrame, *, backend: str) -> pd.DataFrame:
    """Summarize detail rows by comparison, reference, variable, and T."""
    residual_col = f"{backend}_residual_norm"
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
                f"max_{backend}_residual_norm": float(group[residual_col].max(skipna=True)) if group[residual_col].notna().any() else None,
                "max_reference_residual_norm": float(group["reference_residual_norm"].max(skipna=True)) if group["reference_residual_norm"].notna().any() else None,
                "all_reference_converged": bool(group["reference_converged"].dropna().all()) if group["reference_converged"].notna().any() else None,
            }
        )
    return pd.DataFrame(summary_rows)


def comparison_frames(
    primary: pd.DataFrame,
    *,
    backend: str,
    branch_references: Sequence[tuple[pd.DataFrame, str, str]],
    python_checks: pd.DataFrame,
    digitized: pd.DataFrame,
    eq_comparison: str,
    eq_reference: str,
    root_comparison: str,
    root_reference: str = "python_independent_root_solve_checks",
    digitized_comparison: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build detail, summary, and analytic frames for a primary backend."""
    analytic = analytic_frame(primary)
    frames = [
        *(compare_primary_to_branch(primary, frame, backend=backend, comparison=comparison, reference=reference) for frame, comparison, reference in branch_references),
        compare_primary_to_eq(primary, analytic, backend=backend, comparison=eq_comparison, reference=eq_reference),
        compare_primary_to_root_checks(primary, python_checks, backend=backend, comparison=root_comparison, reference=root_reference),
        compare_primary_to_digitized(primary, digitized, backend=backend, comparison=digitized_comparison),
    ]
    details = pd.concat(frames, ignore_index=True)
    return details, summarize_details(details, backend=backend), analytic


def plot_backend_comparison(
    *,
    primary: pd.DataFrame,
    primary_backend: str,
    overlays: Sequence[tuple[str, pd.DataFrame, str, float]],
    analytic: pd.DataFrame,
    digitized: pd.DataFrame,
    output_path: Path,
    title: str,
    legend_entries: int,
    legend_columns: int,
    figsize: tuple[float, float] = (13.5, 4.5),
) -> None:
    """Plot Figure 1 backend overlays using shared panel semantics."""
    fig, axes = plt.subplots(1, 3, figsize=figsize, sharex=True)
    for ax, (variable, spec) in zip(axes, PANEL_SPECS.items(), strict=True):
        for T, color in TEMPERATURE_COLORS.items():
            primary_t = primary[primary["T_K"] == T].sort_values("w_m_s")
            analytic_t = analytic[analytic["T_K"] == T].sort_values("w_m_s")
            paper_t = digitized[(digitized["T_K"] == int(T)) & (digitized["panel"] == spec["digitized_panel"])]
            ax.plot(primary_t["w_m_s"], primary_t[variable], color=color, lw=2.4, label=f"{int(T)} K {primary_backend.upper()}")
            for label, frame, linestyle, linewidth in overlays:
                overlay_t = frame[frame["T_K"] == T].sort_values("w_m_s")
                ax.plot(overlay_t["w_m_s"], overlay_t[variable], color=color, lw=linewidth, ls=linestyle, alpha=0.9, label=f"{int(T)} K {label}")
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
    fig.legend(handles[:legend_entries], labels[:legend_entries], loc="upper center", ncol=legend_columns, frameon=False, bbox_to_anchor=(0.5, 1.08))
    fig.suptitle(title, y=1.18)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_residuals(
    *,
    details: pd.DataFrame,
    primary_label: str,
    comparisons: Mapping[str, tuple[str, str]],
    output_path: Path,
) -> None:
    """Plot percent relative residuals for selected comparison rows."""
    selected = details[details["comparison"].isin(comparisons.keys())]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.8), sharex=True)
    for ax, variable in zip(axes, VARIABLES, strict=True):
        ax.axhline(0.0, color="black", lw=0.8, alpha=0.5)
        for comparison, (label, style) in comparisons.items():
            for T, color in TEMPERATURE_COLORS.items():
                group = selected[(selected["comparison"] == comparison) & (selected["variable"] == variable) & (selected["T_K"] == T)].sort_values("w_m_s")
                if not group.empty:
                    ax.plot(group["w_m_s"], 100.0 * group["rel_diff"], color=color, lw=1.1, ls=style, alpha=0.9, label=f"{int(T)} K vs {label}")
        ax.set_xscale("log")
        ax.set_xlim(0.005, 2.0)
        ax.set_xlabel(r"vertical velocity $w$ (m s$^{-1}$)")
        ax.set_ylabel(f"{variable}: |{primary_label}-ref| / max (%)")
        ax.grid(True, which="both", ls=":", lw=0.6, alpha=0.55)
    handles, labels = axes[-1].get_legend_handles_labels()
    axes[-1].legend(handles[:9], labels[:9], frameon=False, loc="best", fontsize="small")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
