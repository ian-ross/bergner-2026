#!/usr/bin/env python3
"""Produce integrated Figure 2 backend-comparison artifacts.

The script reads curated Python, AUTO, and LOCA Figure 2 branch-point CSVs,
preserves those raw grids, interpolates tracked eigenvalue branches onto a
canonical log-w comparison grid, computes cross-backend summaries, and writes a
paper-facing two-panel Figure 2 reproduction plot.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "005-figure2-eigenvalues"
EPISODE_OUTPUTS = EPISODE_DIR / "outputs"
DEFAULT_INPUTS = {
    "python": EPISODE_OUTPUTS / "figure2_python_eigenvalues" / "python_figure2_branch_points.csv",
    "auto": EPISODE_OUTPUTS / "figure2_auto_eigenvalues" / "auto_figure2_branch_points.csv",
    "loca": EPISODE_OUTPUTS / "figure2_loca_eigenvalues" / "loca_figure2_branch_points.csv",
}
DEFAULT_OUTPUT_DIR = EPISODE_OUTPUTS / "figure2_backend_comparison"
DEFAULT_CANONICAL_POINTS = 801
DEFAULT_REFERENCE_BACKEND = "python"
BACKEND_ORDER = ("python", "auto", "loca")
HOPF_IMAG_TOL = 1.0e-10


@dataclass(frozen=True)
class BackendSeries:
    backend: str
    raw_points: pd.DataFrame
    tracked_spectra: np.ndarray


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def track_eigenvalue_branches(canonical_spectra: np.ndarray) -> np.ndarray:
    """Track adjacent eigenvalues by minimum complex-plane motion."""
    spectra = np.asarray(canonical_spectra, dtype=complex)
    if spectra.ndim != 2 or spectra.shape[1] != 3:
        raise ValueError("canonical_spectra must have shape (n_points, 3).")
    tracked = np.empty_like(spectra)
    tracked[0] = spectra[0]
    for i in range(1, len(spectra)):
        best_cost = np.inf
        best_values = spectra[i]
        for permutation in itertools.permutations(range(3)):
            candidate = spectra[i, list(permutation)]
            cost = float(np.sum(np.abs(candidate - tracked[i - 1])))
            if cost < best_cost:
                best_cost = cost
                best_values = candidate
        tracked[i] = best_values
    return tracked


def _spectra_from_columns(points: pd.DataFrame, prefix: str) -> np.ndarray:
    return np.column_stack(
        [points[f"{prefix}{i}_real"].to_numpy(dtype=float) + 1j * points[f"{prefix}{i}_imag"].to_numpy(dtype=float) for i in (1, 2, 3)]
    )


def load_backend_series(backend: str, path: Path) -> BackendSeries:
    points = pd.read_csv(path).sort_values("log_w").reset_index(drop=True)
    required = {"log_w", "w_m_s", "lambda1_real", "lambda1_imag", "lambda2_real", "lambda2_imag", "lambda3_real", "lambda3_imag"}
    missing = sorted(required - set(points.columns))
    if missing:
        raise ValueError(f"{backend} branch table is missing required columns: {missing}")
    if not np.all(np.diff(points["log_w"].to_numpy(dtype=float)) > 0):
        raise ValueError(f"{backend} log_w grid must be strictly increasing for interpolation.")
    if all(f"tracked_lambda{i}_real" in points.columns and f"tracked_lambda{i}_imag" in points.columns for i in (1, 2, 3)):
        tracked = _spectra_from_columns(points, "tracked_lambda")
    else:
        tracked = track_eigenvalue_branches(_spectra_from_columns(points, "lambda"))
    return BackendSeries(backend=backend, raw_points=points, tracked_spectra=tracked)


def canonical_log_grid(series: dict[str, BackendSeries], points: int, reference_backend: str) -> np.ndarray:
    """Return a documented canonical log-w grid within all backend coverages."""
    starts = [float(item.raw_points["log_w"].min()) for item in series.values()]
    stops = [float(item.raw_points["log_w"].max()) for item in series.values()]
    start = max(starts)
    stop = min(stops)
    if start >= stop:
        raise ValueError("Backend log-w ranges do not overlap.")
    ref_grid = series[reference_backend].raw_points["log_w"].to_numpy(dtype=float)
    overlap_ref = ref_grid[(ref_grid >= start) & (ref_grid <= stop)]
    if len(overlap_ref) == points and np.isclose(overlap_ref[0], start) and np.isclose(overlap_ref[-1], stop):
        return overlap_ref
    return np.linspace(start, stop, points)


def interpolate_series(series: BackendSeries, grid: np.ndarray) -> pd.DataFrame:
    source_log_w = series.raw_points["log_w"].to_numpy(dtype=float)
    out: dict[str, Any] = {"backend": series.backend, "canonical_index": np.arange(len(grid)), "log_w": grid, "w_m_s": np.exp(grid)}
    for branch in (1, 2, 3):
        values = series.tracked_spectra[:, branch - 1]
        out[f"tracked_lambda{branch}_real"] = np.interp(grid, source_log_w, values.real)
        out[f"tracked_lambda{branch}_imag"] = np.interp(grid, source_log_w, values.imag)
    # A few physical-state quantities are helpful diagnostics; do not require all backends to have more than these.
    for column in ("n", "q", "s"):
        if column in series.raw_points.columns:
            out[column] = np.interp(grid, source_log_w, series.raw_points[column].to_numpy(dtype=float))
    return pd.DataFrame(out)


def pairwise_backend_differences(aligned: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    indexed = {backend: frame.set_index("canonical_index") for backend, frame in aligned.groupby("backend")}
    for backend_a, backend_b in itertools.combinations(BACKEND_ORDER, 2):
        if backend_a not in indexed or backend_b not in indexed:
            continue
        left = indexed[backend_a]
        right = indexed[backend_b]
        for canonical_index in left.index.intersection(right.index):
            row: dict[str, Any] = {
                "backend_a": backend_a,
                "backend_b": backend_b,
                "canonical_index": int(canonical_index),
                "log_w": float(left.loc[canonical_index, "log_w"]),
                "w_m_s": float(left.loc[canonical_index, "w_m_s"]),
            }
            for branch in (1, 2, 3):
                a = complex(left.loc[canonical_index, f"tracked_lambda{branch}_real"], left.loc[canonical_index, f"tracked_lambda{branch}_imag"])
                b = complex(right.loc[canonical_index, f"tracked_lambda{branch}_real"], right.loc[canonical_index, f"tracked_lambda{branch}_imag"])
                delta = a - b
                row[f"tracked_lambda{branch}_delta_real"] = float(delta.real)
                row[f"tracked_lambda{branch}_delta_imag"] = float(delta.imag)
                row[f"tracked_lambda{branch}_abs_delta"] = float(abs(delta))
            rows.append(row)
    return pd.DataFrame(rows)


def estimate_hopf_crossings(points: pd.DataFrame, tracked_spectra: np.ndarray, imag_tol: float = HOPF_IMAG_TOL) -> list[dict[str, Any]]:
    log_w = points["log_w"].to_numpy(dtype=float)
    crossings: list[dict[str, Any]] = []
    for branch in range(3):
        values = tracked_spectra[:, branch]
        real = values.real
        imag_abs = np.abs(values.imag)
        for i in range(len(log_w) - 1):
            if imag_abs[i] <= imag_tol or imag_abs[i + 1] <= imag_tol:
                continue
            if real[i] == 0.0:
                frac = 0.0
            elif real[i] * real[i + 1] > 0.0:
                continue
            else:
                frac = -real[i] / (real[i + 1] - real[i])
            crossing_log_w = float(log_w[i] + frac * (log_w[i + 1] - log_w[i]))
            crossing_imag = float(values[i].imag + frac * (values[i + 1].imag - values[i].imag))
            crossings.append(
                {
                    "branch": branch + 1,
                    "log_w": crossing_log_w,
                    "w_m_s": float(np.exp(crossing_log_w)),
                    "imag_at_crossing": crossing_imag,
                    "left_index": i,
                    "right_index": i + 1,
                }
            )
    # The complex conjugate branch duplicates the same Hopf point; merge near-identical estimates.
    merged: list[dict[str, Any]] = []
    for crossing in sorted(crossings, key=lambda item: item["w_m_s"]):
        if merged and abs(crossing["w_m_s"] - merged[-1]["w_m_s"]) <= 1.0e-8:
            merged[-1]["branches"] = f"{merged[-1]['branches']},{crossing['branch']}"
            merged[-1]["imag_at_crossing_abs_max"] = max(merged[-1]["imag_at_crossing_abs_max"], abs(crossing["imag_at_crossing"]))
        else:
            item = dict(crossing)
            item["branches"] = str(crossing["branch"])
            item["imag_at_crossing_abs_max"] = abs(crossing["imag_at_crossing"])
            item.pop("branch")
            item.pop("imag_at_crossing")
            merged.append(item)
    return merged


def three_real_intervals(points: pd.DataFrame) -> list[dict[str, Any]]:
    if "eigenvalue_regime" not in points.columns:
        return []
    mask = points["eigenvalue_regime"].astype(str).eq("three_real").to_numpy()
    intervals: list[dict[str, Any]] = []
    start: int | None = None
    for i, active in enumerate(mask):
        if active and start is None:
            start = i
        if start is not None and (not active or i == len(mask) - 1):
            end = i - 1 if not active else i
            intervals.append(
                {
                    "start_index": int(start),
                    "end_index": int(end),
                    "start_log_w": float(points.iloc[start]["log_w"]),
                    "end_log_w": float(points.iloc[end]["log_w"]),
                    "start_w_m_s": float(points.iloc[start]["w_m_s"]),
                    "end_w_m_s": float(points.iloc[end]["w_m_s"]),
                    "point_count": int(end - start + 1),
                }
            )
            start = None
    return intervals


def summary_records(series: dict[str, BackendSeries], differences: pd.DataFrame) -> dict[str, Any]:
    backend_summary: dict[str, Any] = {}
    hopf_rows: list[dict[str, Any]] = []
    three_real_rows: list[dict[str, Any]] = []
    for backend, item in series.items():
        points = item.raw_points
        crossings = estimate_hopf_crossings(points, item.tracked_spectra)
        intervals = three_real_intervals(points)
        for crossing in crossings:
            hopf_rows.append({"backend": backend, **crossing})
        for interval in intervals:
            three_real_rows.append({"backend": backend, **interval})
        backend_summary[backend] = {
            "raw_point_count": int(len(points)),
            "w_min_m_s": float(points["w_m_s"].min()),
            "w_max_m_s": float(points["w_m_s"].max()),
            "log_w_min": float(points["log_w"].min()),
            "log_w_max": float(points["log_w"].max()),
            "regime_counts": points.get("eigenvalue_regime", pd.Series(dtype=object)).value_counts().to_dict(),
            "stability_counts": points.get("stability_classification", pd.Series(dtype=object)).value_counts().to_dict(),
            "hopf_crossings": crossings,
            "three_real_intervals": intervals,
            "jacobian_method": str(points["jacobian_method"].iloc[0]) if "jacobian_method" in points.columns and len(points) else "unknown",
            "eigenvalue_source": str(points["eigenvalue_source"].iloc[0]) if "eigenvalue_source" in points.columns and len(points) else "unknown",
        }
    pairwise_summary: dict[str, Any] = {}
    for (a, b), group in differences.groupby(["backend_a", "backend_b"]):
        entry: dict[str, Any] = {"point_count": int(len(group))}
        for branch in (1, 2, 3):
            abs_delta = group[f"tracked_lambda{branch}_abs_delta"]
            entry[f"tracked_lambda{branch}_max_abs_delta"] = float(abs_delta.max())
            entry[f"tracked_lambda{branch}_median_abs_delta"] = float(abs_delta.median())
        pairwise_summary[f"{a}_vs_{b}"] = entry
    return {
        "backends": backend_summary,
        "pairwise_backend_differences": pairwise_summary,
        "hopf_crossings": hopf_rows,
        "three_real_intervals": three_real_rows,
        "digitized_paper": {
            "status": "deferred",
            "rationale": "No robust, reproducible digitization was attempted in this pass; the saved publisher PDF/HTML are available, but extracting the imaginary-part curves from the rasterized/overplotted Figure 2 would require manual calibration and would be secondary evidence.",
            "uncertainty_note": "Any future digitized paper markers should be labeled as visual, secondary evidence with axis-calibration and curve-identification uncertainty, especially for the imaginary-part panel and overlapping eigenvalue branches.",
        },
    }


def write_plot(aligned: pd.DataFrame, hopf_table: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 7.5), sharex=True, constrained_layout=True)
    backend_styles = {
        "python": {"color": "tab:blue", "linestyle": "-"},
        "auto": {"color": "tab:orange", "linestyle": "--"},
        "loca": {"color": "tab:green", "linestyle": ":"},
    }
    branch_alpha = {1: 1.0, 2: 0.75, 3: 0.55}
    for backend in BACKEND_ORDER:
        frame = aligned[aligned["backend"] == backend].sort_values("log_w")
        if frame.empty:
            continue
        style = backend_styles[backend]
        for branch in (1, 2, 3):
            label = f"{backend.upper()} tracked λ{branch}" if branch == 1 else None
            axes[0].plot(frame["w_m_s"], frame[f"tracked_lambda{branch}_real"], alpha=branch_alpha[branch], label=label, **style)
            axes[1].plot(frame["w_m_s"], frame[f"tracked_lambda{branch}_imag"], alpha=branch_alpha[branch], label=label, **style)
    for ax in axes:
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.65)
        ax.grid(True, which="both", alpha=0.25)
    if not hopf_table.empty:
        for _, row in hopf_table.iterrows():
            color = backend_styles.get(row["backend"], {}).get("color", "0.5")
            axes[0].axvline(row["w_m_s"], color=color, linewidth=0.8, alpha=0.25)
    axes[1].set_xscale("log")
    axes[0].set_ylabel("Re(λ) [s$^{-1}$]")
    axes[1].set_ylabel("Im(λ) [s$^{-1}$]")
    axes[1].set_xlabel("w [m s$^{-1}$]")
    axes[0].set_title("Figure 2 reproduction: physical-Jacobian eigenvalues at p=300 hPa, T=230 K, F=1, N$_a$=10$^{10}$ m$^{-3}$")
    axes[0].legend(loc="best", ncols=3, fontsize="small")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--canonical-points", type=int, default=DEFAULT_CANONICAL_POINTS)
    parser.add_argument("--reference-backend", choices=BACKEND_ORDER, default=DEFAULT_REFERENCE_BACKEND)
    for backend, path in DEFAULT_INPUTS.items():
        parser.add_argument(f"--{backend}-input", type=Path, default=path)
    args = parser.parse_args(argv)

    input_paths = {backend: getattr(args, f"{backend}_input") for backend in BACKEND_ORDER}
    series = {backend: load_backend_series(backend, path) for backend, path in input_paths.items()}
    grid = canonical_log_grid(series, args.canonical_points, args.reference_backend)
    aligned = pd.concat([interpolate_series(item, grid) for item in series.values()], ignore_index=True)
    differences = pairwise_backend_differences(aligned)
    summary = summary_records(series, differences)

    hopf_table = pd.DataFrame(summary["hopf_crossings"])
    three_real_table = pd.DataFrame(summary["three_real_intervals"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    aligned_csv = args.output_dir / "figure2_backend_aligned_eigenvalues.csv"
    differences_csv = args.output_dir / "figure2_backend_pairwise_differences.csv"
    hopf_csv = args.output_dir / "figure2_backend_hopf_estimates.csv"
    three_real_csv = args.output_dir / "figure2_backend_three_real_intervals.csv"
    summary_json = args.output_dir / "figure2_backend_comparison_summary.json"
    metadata_json = args.output_dir / "run_metadata.json"
    plot_png = args.output_dir / "figure2_reproduction_backend_comparison.png"

    aligned.to_csv(aligned_csv, index=False)
    differences.to_csv(differences_csv, index=False)
    hopf_table.to_csv(hopf_csv, index=False)
    three_real_table.to_csv(three_real_csv, index=False)
    write_plot(aligned, hopf_table, plot_png)

    summary.update(
        {
            "canonical_grid": {
                "coordinate": "log_w = natural log(w_m_s)",
                "selection": f"{args.canonical_points} uniformly spaced samples on the common overlap of all raw backend log-w ranges, using {args.reference_backend} raw grid directly when it exactly matches the overlap contract.",
                "point_count": int(len(grid)),
                "log_w_min": float(grid.min()),
                "log_w_max": float(grid.max()),
                "w_min_m_s": float(np.exp(grid.min())),
                "w_max_m_s": float(np.exp(grid.max())),
                "raw_backend_grids_preserved": {backend: _relative_path(path) for backend, path in input_paths.items()},
            },
            "outputs": [_relative_path(path) for path in [aligned_csv, differences_csv, hopf_csv, three_real_csv, summary_json, metadata_json, plot_png]],
        }
    )
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metadata = {
        "commands": {
            "invocation": " ".join([sys.executable, *sys.argv]),
            "recommended": "uv run python episodes/005-figure2-eigenvalues/scripts/compare_figure2_eigenvalues.py",
        },
        "inputs": {backend: _relative_path(path) for backend, path in input_paths.items()},
        "interpolation": {
            "coordinate": "log_w",
            "method": "numpy.interp linear interpolation of tracked eigenvalue branch real and imaginary parts",
            "reason": "AUTO, Python, and LOCA use different raw grid densities; comparison artifacts align only derived copies and do not modify or discard raw backend grids.",
        },
        "paper_digitization": summary["digitized_paper"],
        "software": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__},
        "outputs": summary["outputs"],
    }
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote integrated Figure 2 backend comparison artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
