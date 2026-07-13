#!/usr/bin/env python3
"""Generate Python augmented-Hopf continuation artifacts for Figure 3."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover
    package_version = "unknown"

from bergner_spichtinger_2026.approximations import table_ii_lower_hopf_w, table_ii_upper_hopf_w
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.hopf import HopfBranchResult, continue_characteristic_hopf_branch

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure3_python_hopf_loci"
DEFAULT_COMPARISON_DIR = EPISODE_DIR / "outputs" / "figure3_backend_comparison"

BACKEND = "python"
PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
SEED_T_K = 230.0
LOWER_SEED_W_M_S = 0.048531
UPPER_SEED_W_M_S = 0.768680
DEFAULT_T_MIN = 190.0
DEFAULT_T_MAX = 240.0
DEFAULT_T_STEP = 1.0
DEFAULT_TOLERANCE = 1e-8


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def temperature_grid(t_min: float, t_max: float, t_step: float) -> np.ndarray:
    if t_step <= 0.0:
        raise ValueError("--t-step must be positive")
    values = np.arange(t_min, t_max + 0.5 * t_step, t_step, dtype=float)
    if not np.any(np.isclose(values, SEED_T_K, rtol=0.0, atol=1e-12)):
        values = np.sort(np.r_[values, SEED_T_K])
    return values


def branch_rows(result: HopfBranchResult, paper_fit_branch: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for point_index, point in enumerate(result.points):
        n, q, s = point.state
        fit_w = table_ii_lower_hopf_w(point.T_K) if result.branch_id == "lower_hopf" else table_ii_upper_hopf_w(point.T_K)
        rows.append(
            {
                "backend": BACKEND,
                "branch_id": result.branch_id,
                "paper_fit_branch": paper_fit_branch,
                "point_index": point_index,
                "T_K": point.T_K,
                "p_Pa": PRESSURE_PA,
                "F": SEDIMENTATION_F,
                "N_a_m3": AEROSOL_N_A,
                "N_a_cm3": AEROSOL_N_A / 1.0e6,
                "log_w": point.log_w,
                "w_m_s": point.w_m_s,
                "table_ii_reference_w_m_s": float(fit_w),
                "log_n": point.unknowns.log_state[0],
                "log_q": point.unknowns.log_state[1],
                "n": float(n),
                "q": float(q),
                "s": float(s),
                "hopf_frequency": point.frequency,
                "eigenvalue_real": 0.0,
                "eigenvalue_imag": point.frequency,
                "residual_norm": point.residual_norm,
                "equilibrium_residual_norm": point.equilibrium_residual_norm,
                "eigen_residual_norm": point.eigen_residual_norm,
                "physical_residual_norm": point.physical_residual_norm,
                "converged": point.converged,
                "iterations": point.iterations,
                "message": point.message,
                "jacobian_coordinate_system": "physical_ode_state",
                "state_coordinate_system": "log_n_log_q_s_internal__physical_state_output",
                "continuation_parameterization": "fixed_T_augmented_unknown_log_w",
                "normalization": "norm(v_real)^2 + norm(v_imag)^2 = 1",
                "phase_condition": "dot(v_real, previous_v_imag) - dot(v_imag, previous_v_real) = 0",
                "method": "python_characteristic_augmented_hopf_least_squares_predictor_corrector",
                "method_metadata": "equilibrium rows use log-state/log-w residual; Hopf row uses physical ODE Jacobian characteristic-polynomial condition a1*a2-a3=0",
                "source_file": _relative_path(Path(__file__)),
            }
        )
    return rows


def generate_loci(temperatures: np.ndarray, tolerance: float) -> pd.DataFrame:
    base_env = Environment(p=PRESSURE_PA, T=SEED_T_K, w=LOWER_SEED_W_M_S, F=SEDIMENTATION_F, N_a=AEROSOL_N_A)
    lower = continue_characteristic_hopf_branch(
        base_env,
        "lower_hopf",
        SEED_T_K,
        LOWER_SEED_W_M_S,
        temperatures,
        tolerance=tolerance,
    )
    upper = continue_characteristic_hopf_branch(
        base_env,
        "upper_hopf",
        SEED_T_K,
        UPPER_SEED_W_M_S,
        temperatures,
        tolerance=tolerance,
    )
    rows = branch_rows(lower, "wb") + branch_rows(upper, "wa")
    return pd.DataFrame(rows).sort_values(["branch_id", "T_K"]).reset_index(drop=True)


def _load_plotter_module():
    plotter_path = Path(__file__).with_name("plot_figure3_hopf_loci.py")
    spec = importlib.util.spec_from_file_location("plot_figure3_hopf_loci", plotter_path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Could not load plotter module from {plotter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_outputs(frame: pd.DataFrame, output_dir: Path, argv: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    loci_path = output_dir / "python_figure3_hopf_loci.csv"
    backend_plot_path = output_dir / "python_figure3_hopf_loci.png"
    comparison_plot_path = DEFAULT_COMPARISON_DIR / "figure3_hopf_backend_comparison.png"
    frame.to_csv(loci_path, index=False)

    seeds = frame[np.isclose(frame["T_K"], SEED_T_K)].copy()
    seeds.to_csv(output_dir / "python_figure3_hopf_seeds.csv", index=False)

    diagnostics = frame[
        [
            "branch_id",
            "T_K",
            "w_m_s",
            "residual_norm",
            "equilibrium_residual_norm",
            "eigen_residual_norm",
            "physical_residual_norm",
            "converged",
            "iterations",
            "message",
        ]
    ]
    diagnostics.to_csv(output_dir / "python_figure3_hopf_diagnostics.csv", index=False)

    plotter = _load_plotter_module()
    plotter.write_backend_plot(frame, backend_plot_path, backend=BACKEND)
    plotter.write_comparison_plot([frame], comparison_plot_path)

    metadata = {
        "backend": BACKEND,
        "package_version": package_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "command": " ".join([Path(sys.argv[0]).name, *argv]),
        "parameters": {
            "p_Pa": PRESSURE_PA,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "seed_T_K": SEED_T_K,
            "lower_seed_w_m_s": LOWER_SEED_W_M_S,
            "upper_seed_w_m_s": UPPER_SEED_W_M_S,
        },
        "method": {
            "name": "python_characteristic_augmented_hopf_least_squares_predictor_corrector",
            "unknowns": "[log_n, log_q, s, log_w] with frequency recovered from physical Jacobian eigenvalues",
            "equilibrium_coordinates": "log_n_log_q_s_with_log_w",
            "hopf_jacobian_coordinates": "physical_ode_state_n_q_s",
            "hopf_condition": "characteristic polynomial a1*a2-a3=0 for det(lambda I-J)=lambda^3+a1*lambda^2+a2*lambda+a3",
        },
        "outputs": {
            "loci_csv": _relative_path(loci_path),
            "seeds_csv": _relative_path(output_dir / "python_figure3_hopf_seeds.csv"),
            "diagnostics_csv": _relative_path(output_dir / "python_figure3_hopf_diagnostics.csv"),
            "backend_plot_png": _relative_path(backend_plot_path),
            "comparison_plot_png": _relative_path(comparison_plot_path),
        },
        "summary": {
            "rows": int(len(frame)),
            "branches": sorted(frame["branch_id"].unique().tolist()),
            "temperature_min_K": float(frame["T_K"].min()),
            "temperature_max_K": float(frame["T_K"].max()),
            "all_converged": bool(frame["converged"].all()),
            "max_residual_norm": float(frame["residual_norm"].max()),
        },
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--t-min", type=float, default=DEFAULT_T_MIN)
    parser.add_argument("--t-max", type=float, default=DEFAULT_T_MAX)
    parser.add_argument("--t-step", type=float, default=DEFAULT_T_STEP)
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    temperatures = temperature_grid(args.t_min, args.t_max, args.t_step)
    frame = generate_loci(temperatures, args.tolerance)
    write_outputs(frame, args.output_dir, list(argv or []))


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
