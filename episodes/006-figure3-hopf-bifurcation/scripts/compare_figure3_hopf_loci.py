#!/usr/bin/env python3
"""Produce integrated Figure 3 Hopf-locus backend-comparison artifacts.

This script reads normalized Python, AUTO, and LOCA Figure 3 Hopf-locus CSVs,
preserves backend/method provenance in merged artifacts, evaluates the paper's
Table II Hopf-fit references, computes backend-to-backend and backend-to-fit
diagnostics, and writes a paper-facing Figure 3 comparison plot.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bergner_spichtinger_2026.approximations import table_ii_lower_hopf_w, table_ii_upper_hopf_w

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation"
EPISODE_OUTPUTS = EPISODE_DIR / "outputs"
DEFAULT_INPUTS = {
    "python": EPISODE_OUTPUTS / "figure3_python_hopf_loci" / "python_figure3_hopf_loci.csv",
    "auto": EPISODE_OUTPUTS / "figure3_auto_hopf_loci" / "auto_figure3_hopf_loci.csv",
    "loca": EPISODE_OUTPUTS / "figure3_loca_hopf_loci" / "loca_figure3_hopf_loci.csv",
}
DEFAULT_OUTPUT_DIR = EPISODE_OUTPUTS / "figure3_backend_comparison"
BACKEND_ORDER = ("python", "auto", "loca")
BRANCH_ORDER = ("lower_hopf", "upper_hopf")
PAPER_FIT_BY_BRANCH = {"lower_hopf": "wb", "upper_hopf": "wa"}
REQUIRED_COLUMNS = {"branch_id", "T_K", "log_w", "w_m_s"}
PROVENANCE_COLUMNS = (
    "backend",
    "schema_version",
    "method",
    "method_metadata",
    "source_file",
    "continuation_parameterization",
    "jacobian_coordinate_system",
    "state_coordinate_system",
    "raw_auto_run",
    "auto_branch",
    "auto_label",
    "auto_hopf_source_label",
    "raw_loca_run",
    "loca_continuation_mode",
    "loca_native_hopf_stepper",
)


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def table_ii_w(branch_id: str, temperatures: np.ndarray | pd.Series | float) -> np.ndarray | float:
    if branch_id == "lower_hopf":
        return table_ii_lower_hopf_w(temperatures)
    if branch_id == "upper_hopf":
        return table_ii_upper_hopf_w(temperatures)
    raise ValueError(f"unknown Hopf branch_id {branch_id!r}")


def load_backend_frame(backend: str, path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"{backend} Hopf-locus table is missing required columns: {missing}")
    frame = frame.copy()
    if "backend" in frame.columns:
        observed = {str(item) for item in frame["backend"].dropna().unique()}
        if observed and observed != {backend}:
            raise ValueError(f"{backend} input has inconsistent backend labels: {sorted(observed)}")
    frame["backend"] = backend
    frame["input_path"] = _relative_path(path)
    frame["input_row_index"] = np.arange(len(frame), dtype=int)
    frame["available_for_comparison"] = True
    for branch_id in frame["branch_id"].astype(str).unique():
        if branch_id not in BRANCH_ORDER:
            raise ValueError(f"{backend} input has unsupported branch_id {branch_id!r}")
    for column in ("T_K", "log_w", "w_m_s"):
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{backend} {column} contains non-finite values")
    if (frame["w_m_s"].to_numpy(dtype=float) <= 0.0).any():
        raise ValueError(f"{backend} w_m_s must be strictly positive")
    return frame


def load_available_backends(input_paths: dict[str, Path], *, require_all: bool = False) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for backend in BACKEND_ORDER:
        path = input_paths[backend]
        if not path.exists():
            missing.append(backend)
            continue
        frames[backend] = load_backend_frame(backend, path)
    if require_all and missing:
        raise FileNotFoundError(f"Missing required Figure 3 backend inputs: {missing}")
    if not frames:
        raise FileNotFoundError("No Figure 3 backend inputs are available.")
    return frames


def merged_backend_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    merged = pd.concat([frames[backend] for backend in BACKEND_ORDER if backend in frames], ignore_index=True, sort=False)
    merged["paper_fit_branch"] = merged.get("paper_fit_branch", merged["branch_id"].map(PAPER_FIT_BY_BRANCH))
    merged["table_ii_reference_w_m_s"] = [float(table_ii_w(branch, T)) for branch, T in zip(merged["branch_id"], merged["T_K"])]
    merged["table_ii_reference_log_w"] = np.log(merged["table_ii_reference_w_m_s"].to_numpy(dtype=float))
    merged["delta_to_table_ii_w_m_s"] = merged["w_m_s"].to_numpy(dtype=float) - merged["table_ii_reference_w_m_s"].to_numpy(dtype=float)
    merged["delta_to_table_ii_log_w"] = merged["log_w"].to_numpy(dtype=float) - merged["table_ii_reference_log_w"].to_numpy(dtype=float)
    merged["relative_delta_to_table_ii_w"] = merged["delta_to_table_ii_w_m_s"] / merged["table_ii_reference_w_m_s"]
    preferred = [
        "backend",
        "branch_id",
        "paper_fit_branch",
        "input_path",
        "input_row_index",
        "T_K",
        "log_w",
        "w_m_s",
        "table_ii_reference_log_w",
        "table_ii_reference_w_m_s",
        "delta_to_table_ii_log_w",
        "delta_to_table_ii_w_m_s",
        "relative_delta_to_table_ii_w",
        *[c for c in PROVENANCE_COLUMNS if c not in {"backend"}],
    ]
    ordered = [c for c in preferred if c in merged.columns] + [c for c in merged.columns if c not in preferred]
    return merged[ordered].sort_values(["branch_id", "backend", "T_K", "input_row_index"]).reset_index(drop=True)


def table_ii_reference_frame(t_min: float = 190.0, t_max: float = 240.0, points: int = 501) -> pd.DataFrame:
    T = np.linspace(t_min, t_max, points)
    rows: list[dict[str, Any]] = []
    for branch_id in BRANCH_ORDER:
        w = np.asarray(table_ii_w(branch_id, T), dtype=float)
        for i, (T_i, w_i) in enumerate(zip(T, w)):
            rows.append(
                {
                    "reference": "Bergner_Spichtinger_2026_Table_II_fit",
                    "branch_id": branch_id,
                    "paper_fit_branch": PAPER_FIT_BY_BRANCH[branch_id],
                    "point_index": i,
                    "T_K": float(T_i),
                    "log_w": float(np.log(w_i)),
                    "w_m_s": float(w_i),
                    "computed_locus": False,
                }
            )
    return pd.DataFrame(rows)


def _aggregate_for_interpolation(frame: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["backend", "branch_id", "T_K"]
    numeric = frame.groupby(group_cols, dropna=False).agg(log_w=("log_w", "mean"), w_m_s=("w_m_s", "mean"), source_point_count=("log_w", "size")).reset_index()
    if "converged" in frame.columns:
        conv = frame.assign(_converged=frame["converged"].astype(str).str.lower().isin(["true", "1", "yes"])).groupby(group_cols)["_converged"].all().reset_index(name="all_converged_at_T")
        numeric = numeric.merge(conv, on=group_cols, how="left")
    return numeric.sort_values(group_cols).reset_index(drop=True)


def canonical_temperature_grid(merged: pd.DataFrame, points: int) -> np.ndarray:
    t_min = max(190.0, float(merged["T_K"].min()))
    t_max = min(240.0, float(merged["T_K"].max()))
    if t_min >= t_max:
        raise ValueError("Backend temperature ranges do not overlap the Figure 3 interval.")
    return np.linspace(t_min, t_max, points)


def interpolated_backend_table(merged: pd.DataFrame, grid: np.ndarray) -> pd.DataFrame:
    agg = _aggregate_for_interpolation(merged)
    rows: list[dict[str, Any]] = []
    for (backend, branch_id), group in agg.groupby(["backend", "branch_id"]):
        group = group.sort_values("T_K")
        unique = group.drop_duplicates("T_K")
        if len(unique) < 2:
            continue
        t = unique["T_K"].to_numpy(dtype=float)
        inside = grid[(grid >= t.min()) & (grid <= t.max())]
        log_w = np.interp(inside, t, unique["log_w"].to_numpy(dtype=float))
        for i, (T_i, log_w_i) in enumerate(zip(inside, log_w)):
            fit_w = float(table_ii_w(str(branch_id), float(T_i)))
            w_i = float(np.exp(log_w_i))
            rows.append(
                {
                    "backend": backend,
                    "branch_id": branch_id,
                    "canonical_index": int(np.where(np.isclose(grid, T_i, rtol=0.0, atol=1e-12))[0][0]),
                    "T_K": float(T_i),
                    "log_w": float(log_w_i),
                    "w_m_s": w_i,
                    "table_ii_reference_log_w": float(np.log(fit_w)),
                    "table_ii_reference_w_m_s": fit_w,
                    "delta_to_table_ii_log_w": float(log_w_i - np.log(fit_w)),
                    "delta_to_table_ii_w_m_s": float(w_i - fit_w),
                    "relative_delta_to_table_ii_w": float((w_i - fit_w) / fit_w),
                    "interpolation_method": "numpy.interp over backend branch T_K/log_w after averaging duplicate T rows",
                    "raw_T_min_K": float(t.min()),
                    "raw_T_max_K": float(t.max()),
                }
            )
    return pd.DataFrame(rows)


def pairwise_backend_differences(interpolated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    indexed = {(backend, branch): group.set_index("canonical_index") for (backend, branch), group in interpolated.groupby(["backend", "branch_id"])}
    for branch_id in BRANCH_ORDER:
        for backend_a, backend_b in itertools.combinations(BACKEND_ORDER, 2):
            left = indexed.get((backend_a, branch_id))
            right = indexed.get((backend_b, branch_id))
            if left is None or right is None:
                continue
            for canonical_index in left.index.intersection(right.index):
                a = left.loc[canonical_index]
                b = right.loc[canonical_index]
                rows.append(
                    {
                        "branch_id": branch_id,
                        "backend_a": backend_a,
                        "backend_b": backend_b,
                        "canonical_index": int(canonical_index),
                        "T_K": float(a["T_K"]),
                        "log_w_a": float(a["log_w"]),
                        "log_w_b": float(b["log_w"]),
                        "w_m_s_a": float(a["w_m_s"]),
                        "w_m_s_b": float(b["w_m_s"]),
                        "delta_log_w_a_minus_b": float(a["log_w"] - b["log_w"]),
                        "delta_w_m_s_a_minus_b": float(a["w_m_s"] - b["w_m_s"]),
                        "relative_delta_w_a_minus_b": float((a["w_m_s"] - b["w_m_s"]) / b["w_m_s"]),
                    }
                )
    return pd.DataFrame(rows)


def anchor_comparisons(merged: pd.DataFrame, anchor_T_K: float = 230.0, tolerance_K: float = 1.0e-6) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidates = merged[np.isclose(merged["T_K"].to_numpy(dtype=float), anchor_T_K, rtol=0.0, atol=tolerance_K)]
    for (backend, branch_id), group in candidates.groupby(["backend", "branch_id"]):
        fit_w = float(table_ii_w(str(branch_id), anchor_T_K))
        log_w = float(group["log_w"].astype(float).mean())
        w = float(np.exp(log_w))
        rows.append(
            {
                "backend": backend,
                "branch_id": branch_id,
                "T_K": anchor_T_K,
                "source_point_count": int(len(group)),
                "log_w": log_w,
                "w_m_s": w,
                "table_ii_reference_log_w": float(np.log(fit_w)),
                "table_ii_reference_w_m_s": fit_w,
                "delta_to_table_ii_log_w": float(log_w - np.log(fit_w)),
                "delta_to_table_ii_w_m_s": float(w - fit_w),
                "relative_delta_to_table_ii_w": float((w - fit_w) / fit_w),
            }
        )
    return pd.DataFrame(rows).sort_values(["branch_id", "backend"]).reset_index(drop=True) if rows else pd.DataFrame()


def _series_stats(series: pd.Series) -> dict[str, float]:
    values = series.astype(float).abs()
    return {
        "max_abs": float(values.max()),
        "median_abs": float(values.median()),
        "mean_abs": float(values.mean()),
    }


def summary_records(merged: pd.DataFrame, interpolated: pd.DataFrame, differences: pd.DataFrame, anchors: pd.DataFrame, input_paths: dict[str, Path]) -> dict[str, Any]:
    backend_summary: dict[str, Any] = {}
    missing_failed: list[dict[str, Any]] = []
    for backend in BACKEND_ORDER:
        frame = merged[merged["backend"] == backend]
        if frame.empty:
            backend_summary[backend] = {"available": False, "input_path": _relative_path(input_paths[backend])}
            missing_failed.append({"backend": backend, "issue": "input_missing_or_not_loaded", "path": _relative_path(input_paths[backend])})
            continue
        entry: dict[str, Any] = {
            "available": True,
            "input_path": _relative_path(input_paths[backend]),
            "raw_point_count": int(len(frame)),
            "branches": {},
            "provenance_columns_present": [column for column in PROVENANCE_COLUMNS if column in frame.columns],
        }
        if "converged" in frame.columns:
            converged = frame["converged"].astype(str).str.lower().isin(["true", "1", "yes"])
            entry["converged_point_count"] = int(converged.sum())
            if not converged.all():
                for _, row in frame.loc[~converged].iterrows():
                    missing_failed.append({"backend": backend, "branch_id": row["branch_id"], "T_K": float(row["T_K"]), "issue": "converged_false"})
        for branch_id, group in frame.groupby("branch_id"):
            entry["branches"][str(branch_id)] = {
                "point_count": int(len(group)),
                "T_min_K": float(group["T_K"].min()),
                "T_max_K": float(group["T_K"].max()),
                "unique_T_count": int(group["T_K"].nunique()),
                "w_min_m_s": float(group["w_m_s"].min()),
                "w_max_m_s": float(group["w_m_s"].max()),
                "max_abs_log_delta_to_table_ii": float(group["delta_to_table_ii_log_w"].abs().max()),
                "max_abs_relative_w_delta_to_table_ii": float(group["relative_delta_to_table_ii_w"].abs().max()),
            }
        backend_summary[backend] = entry
    pairwise_summary: dict[str, Any] = {}
    if not differences.empty:
        for (a, b, branch_id), group in differences.groupby(["backend_a", "backend_b", "branch_id"]):
            pairwise_summary[f"{a}_vs_{b}:{branch_id}"] = {
                "point_count": int(len(group)),
                "delta_log_w": _series_stats(group["delta_log_w_a_minus_b"]),
                "delta_w_m_s": _series_stats(group["delta_w_m_s_a_minus_b"]),
                "relative_delta_w": _series_stats(group["relative_delta_w_a_minus_b"]),
            }
    fit_summary: dict[str, Any] = {}
    if not interpolated.empty:
        for (backend, branch_id), group in interpolated.groupby(["backend", "branch_id"]):
            fit_summary[f"{backend}:{branch_id}"] = {
                "point_count": int(len(group)),
                "delta_log_w": _series_stats(group["delta_to_table_ii_log_w"]),
                "delta_w_m_s": _series_stats(group["delta_to_table_ii_w_m_s"]),
                "relative_delta_w": _series_stats(group["relative_delta_to_table_ii_w"]),
            }
    return {
        "backends": backend_summary,
        "pairwise_backend_differences": pairwise_summary,
        "backend_to_table_ii_fit_differences": fit_summary,
        "anchor_T230_K": anchors.to_dict(orient="records") if not anchors.empty else [],
        "missing_or_failed_points": missing_failed,
        "known_caveats": [
            "Table II curves are paper fit references and are not substituted for backend-computed Hopf loci.",
            "Pairwise backend diagnostics interpolate log_w as a function of T_K on the common Figure 3 interval; raw backend grids and duplicate AUTO restart rows are preserved separately in the merged artifact.",
            "AUTO native Hopf outputs may include duplicate temperatures from forward/backward restarts; comparison interpolation averages duplicate T rows per backend and branch.",
        ],
    }


def write_plot(merged: pd.DataFrame, output_path: Path, *, t_min: float = 190.0, t_max: float = 240.0) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.9), constrained_layout=True)
    branch_colors = {"lower_hopf": "tab:blue", "upper_hopf": "tab:red"}
    backend_styles = {
        "python": {"marker": "o", "linestyle": "-", "alpha": 0.82},
        "auto": {"marker": "s", "linestyle": "--", "alpha": 0.78},
        "loca": {"marker": "^", "linestyle": ":", "alpha": 0.85},
    }
    T_ref = np.linspace(t_min, t_max, 501)
    for branch_id in BRANCH_ORDER:
        w_ref = np.asarray(table_ii_w(branch_id, T_ref), dtype=float)
        ax.plot(
            T_ref,
            w_ref,
            color=branch_colors[branch_id],
            linewidth=2.0,
            linestyle="-",
            alpha=0.45,
            label=f"Table II {PAPER_FIT_BY_BRANCH[branch_id]} fit ({branch_id.replace('_', ' ')})",
        )
    for backend in BACKEND_ORDER:
        for branch_id in BRANCH_ORDER:
            group = merged[(merged["backend"] == backend) & (merged["branch_id"] == branch_id)].sort_values("T_K")
            if group.empty:
                continue
            style = backend_styles[backend]
            ax.plot(
                group["T_K"],
                group["w_m_s"],
                color=branch_colors[branch_id],
                marker=style["marker"],
                linestyle=style["linestyle"],
                markersize=3.0,
                linewidth=1.3,
                alpha=style["alpha"],
                label=f"{backend.upper()} computed {branch_id.replace('_', ' ')}",
            )
    ax.set_yscale("log")
    ax.set_xlim(t_min, t_max)
    ax.set_xlabel("T [K]")
    ax.set_ylabel("w [m s$^{-1}$]")
    ax.set_title("Figure 3 reproduction: backend Hopf loci and Table II fit references")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="best", fontsize="x-small", ncols=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_json_records(path: Path, records: pd.DataFrame, *, metadata: dict[str, Any]) -> None:
    payload = {"metadata": metadata, "records": records.to_dict(orient="records")}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--canonical-points", type=int, default=51)
    parser.add_argument("--require-all", action="store_true", help="Fail if any default backend input is missing instead of comparing available backends.")
    for backend, path in DEFAULT_INPUTS.items():
        parser.add_argument(f"--{backend}-input", type=Path, default=path)
    args = parser.parse_args(argv)
    if args.canonical_points < 2:
        raise ValueError("--canonical-points must be at least 2")

    input_paths = {backend: getattr(args, f"{backend}_input") for backend in BACKEND_ORDER}
    frames = load_available_backends(input_paths, require_all=args.require_all)
    merged = merged_backend_table(frames)
    grid = canonical_temperature_grid(merged, args.canonical_points)
    interpolated = interpolated_backend_table(merged, grid)
    differences = pairwise_backend_differences(interpolated)
    anchors = anchor_comparisons(merged)
    table_ii = table_ii_reference_frame()
    summary = summary_records(merged, interpolated, differences, anchors, input_paths)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    merged_csv = args.output_dir / "figure3_backend_merged_hopf_loci.csv"
    merged_json = args.output_dir / "figure3_backend_merged_hopf_loci.json"
    table_ii_csv = args.output_dir / "figure3_table_ii_hopf_fit_references.csv"
    interpolated_csv = args.output_dir / "figure3_backend_interpolated_hopf_loci.csv"
    differences_csv = args.output_dir / "figure3_backend_pairwise_differences.csv"
    fit_differences_csv = args.output_dir / "figure3_backend_to_table_ii_differences.csv"
    anchors_csv = args.output_dir / "figure3_backend_T230_anchor_comparisons.csv"
    summary_json = args.output_dir / "figure3_backend_comparison_summary.json"
    metadata_json = args.output_dir / "run_metadata.json"
    plot_png = args.output_dir / "figure3_hopf_backend_comparison.png"

    merged.to_csv(merged_csv, index=False)
    write_json_records(merged_json, merged, metadata={"description": "Merged raw backend Hopf loci with preserved provenance columns and Table II deltas."})
    table_ii.to_csv(table_ii_csv, index=False)
    interpolated.to_csv(interpolated_csv, index=False)
    differences.to_csv(differences_csv, index=False)
    interpolated.to_csv(fit_differences_csv, index=False)
    anchors.to_csv(anchors_csv, index=False)
    write_plot(merged, plot_png)

    summary.update(
        {
            "canonical_grid": {
                "coordinate": "T_K with log_w interpolation",
                "selection": f"{args.canonical_points} uniformly spaced samples on the available overlap of the Figure 3 interval 190--240 K.",
                "point_count": int(len(grid)),
                "T_min_K": float(grid.min()),
                "T_max_K": float(grid.max()),
                "raw_backend_grids_preserved": {backend: _relative_path(path) for backend, path in input_paths.items()},
            },
            "outputs": [_relative_path(path) for path in [merged_csv, merged_json, table_ii_csv, interpolated_csv, differences_csv, fit_differences_csv, anchors_csv, summary_json, metadata_json, plot_png]],
        }
    )
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metadata = {
        "commands": {
            "invocation": " ".join([sys.executable, *sys.argv]),
            "recommended": "uv run python episodes/006-figure3-hopf-bifurcation/scripts/compare_figure3_hopf_loci.py",
        },
        "inputs": {backend: _relative_path(path) for backend, path in input_paths.items()},
        "available_backends": sorted(frames),
        "schema": {
            "required_columns": sorted(REQUIRED_COLUMNS),
            "provenance_columns_preserved_when_present": list(PROVENANCE_COLUMNS),
        },
        "interpolation": {
            "coordinate": "T_K",
            "value": "log_w = natural log(w_m_s)",
            "method": "numpy.interp linear interpolation after averaging duplicate backend/branch/T_K rows",
            "reason": "Backends use different raw temperature grids and AUTO restarts can duplicate temperatures; raw rows remain preserved in merged artifacts.",
        },
        "software": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__},
        "outputs": summary["outputs"],
    }
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote integrated Figure 3 backend comparison artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
