#!/usr/bin/env python3
"""Plot Figure 2-style eigenvalue outputs for Python, AUTO, or LOCA backends."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_OUTPUTS = REPO_ROOT / "episodes" / "005-figure2-eigenvalues" / "outputs"
DEFAULT_INPUTS = {
    "python": EPISODE_OUTPUTS / "figure2_python_eigenvalues" / "python_figure2_branch_points.csv",
    "auto": EPISODE_OUTPUTS / "figure2_auto_eigenvalues" / "auto_figure2_branch_points.csv",
    "loca": EPISODE_OUTPUTS / "figure2_loca_eigenvalues" / "loca_figure2_branch_points.csv",
}
DEFAULT_OUTPUTS = {
    "python": EPISODE_OUTPUTS / "figure2_python_eigenvalues" / "python_figure2_eigenvalues.png",
    "auto": EPISODE_OUTPUTS / "figure2_auto_eigenvalues" / "auto_figure2_eigenvalues.png",
    "loca": EPISODE_OUTPUTS / "figure2_loca_eigenvalues" / "loca_figure2_eigenvalues.png",
}


def track_eigenvalue_branches(canonical_spectra: np.ndarray) -> np.ndarray:
    """Track adjacent eigenvalue identities by minimum complex-plane motion."""
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


def tracked_spectra(point_rows: pd.DataFrame) -> np.ndarray:
    if all(f"tracked_lambda{i}_real" in point_rows.columns and f"tracked_lambda{i}_imag" in point_rows.columns for i in (1, 2, 3)):
        return np.column_stack(
            [point_rows[f"tracked_lambda{i}_real"].to_numpy() + 1j * point_rows[f"tracked_lambda{i}_imag"].to_numpy() for i in (1, 2, 3)]
        )
    canonical = np.column_stack(
        [point_rows[f"lambda{i}_real"].to_numpy() + 1j * point_rows[f"lambda{i}_imag"].to_numpy() for i in (1, 2, 3)]
    )
    return track_eigenvalue_branches(canonical)


def write_plot(point_rows: pd.DataFrame, output_path: Path, *, backend: str) -> None:
    point_rows = point_rows.sort_values("w_m_s").reset_index(drop=True)
    spectra = tracked_spectra(point_rows)
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 7.0), sharex=True, constrained_layout=True)
    colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}
    for eigen_index in (1, 2, 3):
        values = spectra[:, eigen_index - 1]
        axes[0].plot(point_rows["w_m_s"], values.real, color=colors[eigen_index], label=f"tracked λ{eigen_index}")
        axes[1].plot(point_rows["w_m_s"], values.imag, color=colors[eigen_index], label=f"tracked λ{eigen_index}")
    axes[0].axhline(0.0, color="black", linewidth=0.8, alpha=0.6)
    axes[1].axhline(0.0, color="black", linewidth=0.8, alpha=0.6)
    axes[1].set_xscale("log")
    axes[0].set_ylabel("Re(λ) [s$^{-1}$]")
    axes[1].set_ylabel("Im(λ) [s$^{-1}$]")
    axes[1].set_xlabel("w [m s$^{-1}$]")
    axes[0].set_title(f"Draft Figure 2-style {backend.upper()} physical-Jacobian eigenvalues")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=sorted(DEFAULT_INPUTS), help="Backend output to plot.")
    parser.add_argument("--input", type=Path, help="Branch point CSV. Defaults to the episode output for the backend.")
    parser.add_argument("--output", type=Path, help="PNG path. Defaults to the episode output for the backend.")
    args = parser.parse_args(argv)

    input_path = args.input or DEFAULT_INPUTS[args.backend]
    output_path = args.output or DEFAULT_OUTPUTS[args.backend]
    point_rows = pd.read_csv(input_path)
    write_plot(point_rows, output_path, backend=args.backend)
    print(f"Wrote {args.backend.upper()} Figure 2 eigenvalue plot to {output_path}")


if __name__ == "__main__":
    main()
