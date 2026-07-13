#!/usr/bin/env python3
"""Plot Figure 3-style Hopf loci for one backend or integrated comparison.

The per-backend plot mirrors Episode 5's convention of storing a PNG next to
that backend's curated CSV outputs.  The comparison mode overlays every
available backend locus with Bergner & Spichtinger (2026) Table II reference
fits and writes to `outputs/figure3_backend_comparison/`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

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
DEFAULT_OUTPUTS = {
    "python": EPISODE_OUTPUTS / "figure3_python_hopf_loci" / "python_figure3_hopf_loci.png",
    "auto": EPISODE_OUTPUTS / "figure3_auto_hopf_loci" / "auto_figure3_hopf_loci.png",
    "loca": EPISODE_OUTPUTS / "figure3_loca_hopf_loci" / "loca_figure3_hopf_loci.png",
}
DEFAULT_COMPARISON_OUTPUT = EPISODE_OUTPUTS / "figure3_backend_comparison" / "figure3_hopf_backend_comparison.png"
BRANCH_COLORS = {"lower_hopf": "tab:blue", "upper_hopf": "tab:red"}
BACKEND_MARKERS = {"python": "o", "auto": "s", "loca": "^"}


def _table_ii_frame(t_min: float, t_max: float, points: int = 300) -> pd.DataFrame:
    temperatures = np.linspace(t_min, t_max, points)
    return pd.DataFrame(
        {
            "T_K": np.r_[temperatures, temperatures],
            "w_m_s": np.r_[table_ii_lower_hopf_w(temperatures), table_ii_upper_hopf_w(temperatures)],
            "branch_id": ["lower_hopf"] * points + ["upper_hopf"] * points,
            "source": ["Table II lower fit"] * points + ["Table II upper fit"] * points,
        }
    )


def _plot_table_ii(ax: plt.Axes, t_min: float, t_max: float) -> None:
    table = _table_ii_frame(t_min, t_max)
    for branch_id, group in table.groupby("branch_id"):
        ax.plot(
            group["T_K"],
            group["w_m_s"],
            color=BRANCH_COLORS.get(branch_id, "0.4"),
            linestyle="--",
            linewidth=1.5,
            alpha=0.85,
            label=f"Table II {branch_id.replace('_', ' ')} fit",
        )


def _format_axes(ax: plt.Axes, title: str) -> None:
    ax.set_yscale("log")
    ax.set_xlabel("T [K]")
    ax.set_ylabel("w [m s$^{-1}$]")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="best", fontsize="small")


def write_backend_plot(loci: pd.DataFrame, output_path: Path, *, backend: str) -> None:
    """Write one Figure 3-style plot for a backend locus table."""
    if loci.empty:
        raise ValueError("loci table is empty")
    fig, ax = plt.subplots(figsize=(8.0, 5.5), constrained_layout=True)
    t_min = float(loci["T_K"].min())
    t_max = float(loci["T_K"].max())
    _plot_table_ii(ax, t_min, t_max)
    for branch_id, group in loci.sort_values("T_K").groupby("branch_id"):
        ax.plot(
            group["T_K"],
            group["w_m_s"],
            marker=BACKEND_MARKERS.get(backend, "o"),
            markersize=3.5,
            linewidth=1.8,
            color=BRANCH_COLORS.get(branch_id, None),
            label=f"{backend.upper()} {branch_id.replace('_', ' ')}",
        )
    _format_axes(ax, f"Draft Figure 3-style {backend.upper()} Hopf loci")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _available_backend_frames(inputs: dict[str, Path]) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for backend, path in inputs.items():
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        frame = frame.copy()
        frame["backend"] = frame.get("backend", backend)
        frames.append(frame)
    return frames


def write_comparison_plot(frames: Iterable[pd.DataFrame], output_path: Path) -> None:
    """Write an integrated Figure 3 comparison plot for available backends."""
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise ValueError("no backend frames supplied for comparison plot")
    combined = pd.concat(frames, ignore_index=True)
    fig, ax = plt.subplots(figsize=(8.5, 5.8), constrained_layout=True)
    t_min = float(combined["T_K"].min())
    t_max = float(combined["T_K"].max())
    _plot_table_ii(ax, t_min, t_max)
    for (backend, branch_id), group in combined.sort_values("T_K").groupby(["backend", "branch_id"]):
        ax.plot(
            group["T_K"],
            group["w_m_s"],
            marker=BACKEND_MARKERS.get(str(backend), "o"),
            markersize=3.2,
            linewidth=1.5,
            color=BRANCH_COLORS.get(str(branch_id), None),
            alpha=0.9,
            label=f"{str(backend).upper()} {str(branch_id).replace('_', ' ')}",
        )
    _format_axes(ax, "Draft Figure 3-style Hopf-locus backend comparison")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backend_parser = subparsers.add_parser("backend", help="Plot one backend's Hopf-locus CSV.")
    backend_parser.add_argument("backend", choices=sorted(DEFAULT_INPUTS))
    backend_parser.add_argument("--input", type=Path, help="Backend Hopf-locus CSV. Defaults to episode output for backend.")
    backend_parser.add_argument("--output", type=Path, help="PNG output path. Defaults next to backend CSV.")

    comparison_parser = subparsers.add_parser("comparison", help="Plot integrated comparison for all available backend CSVs.")
    comparison_parser.add_argument("--python-input", type=Path, default=DEFAULT_INPUTS["python"])
    comparison_parser.add_argument("--auto-input", type=Path, default=DEFAULT_INPUTS["auto"])
    comparison_parser.add_argument("--loca-input", type=Path, default=DEFAULT_INPUTS["loca"])
    comparison_parser.add_argument("--output", type=Path, default=DEFAULT_COMPARISON_OUTPUT)

    args = parser.parse_args(argv)
    if args.command == "backend":
        input_path = args.input or DEFAULT_INPUTS[args.backend]
        output_path = args.output or DEFAULT_OUTPUTS[args.backend]
        write_backend_plot(pd.read_csv(input_path), output_path, backend=args.backend)
        print(f"Wrote {args.backend.upper()} Figure 3 Hopf-locus plot to {output_path}")
    else:
        frames = _available_backend_frames({"python": args.python_input, "auto": args.auto_input, "loca": args.loca_input})
        write_comparison_plot(frames, args.output)
        print(f"Wrote Figure 3 backend comparison plot to {args.output}")


if __name__ == "__main__":
    main()
