#!/usr/bin/env python3
"""Generate Python-native Figure 2 equilibrium/eigenvalue artifacts.

This script traces the Bergner & Spichtinger (2026) Figure 2 equilibrium branch
for p=300 hPa, T=230 K, F=1, N_a=1e10 m^-3 over w=0.0005--2.0 m s^-1,
then evaluates the physical ODE Jacobian eigenvalues at each converged point.
Outputs are intentionally episode-local.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from dataclasses import asdict
from math import exp, log
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from importlib.metadata import PackageNotFoundError, version

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover - editable/local fallback
    package_version = "unknown"

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.continuation import continue_branch
from bergner_spichtinger_2026.core import coefficients, equilibrium, vector_field
from bergner_spichtinger_2026.residuals import (
    log_coordinates_from_physical_state,
    make_equilibrium_residual,
    physical_state_from_log_coordinates,
)
from bergner_spichtinger_2026.stability import (
    classify_eigenvalues,
    detect_hopf_crossings,
    physical_eigenvalues,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "005-figure2-eigenvalues"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure2_python_eigenvalues"

BACKEND = "python"
BRANCH_ID = "figure2_T230K"
PRESSURE_PA = 30_000.0
TEMPERATURE_K = 230.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
W_MIN = 0.0005
W_MAX = 2.0
EXPECTED_HOPF_W_M_S = (0.048, 0.77)
DEFAULT_POINTS = 801
DEFAULT_TOLERANCE = 1e-9
DEFAULT_MAX_ITERATIONS = 300
DEFAULT_REAL_TOL = 1e-10
DEFAULT_IMAG_TOL = 1e-10
HOPF_LANDMARK_TOLERANCE_M_S = 0.01


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def generate_branch(points: int, tolerance: float, max_iterations: int) -> pd.DataFrame:
    """Generate the dense log-w equilibrium/eigenvalue branch as a long table."""
    if points < 400:
        raise ValueError("--points must be at least 400 for the Figure 2 reproduction contract.")

    controls = np.linspace(log(W_MIN), log(W_MAX), points)
    env0 = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=float(exp(controls[0])), F=SEDIMENTATION_F, N_a=AEROSOL_N_A)
    coeff0 = coefficients(env0)
    initial = log_coordinates_from_physical_state(equilibrium(env0, bracket=(1.000001, 3.0)))
    result = continue_branch(
        make_equilibrium_residual(env0, coeff=coeff0),
        initial,
        controls,
        tolerance=tolerance,
        max_iterations=max_iterations,
        stop_on_failure=False,
    )

    rows: list[dict[str, Any]] = []
    for point_index, point in enumerate(result.points):
        w = float(exp(point.control))
        env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=w, F=SEDIMENTATION_F, N_a=AEROSOL_N_A)
        coeff = coefficients(env)
        n, q, s = physical_state_from_log_coordinates(point.state)
        physical_state = np.array([n, q, s], dtype=float)
        rhs = vector_field(float(n), float(q), float(s), env, coeff)
        physical_residual_norm = float(np.linalg.norm(rhs, ord=2))
        scaled_physical_residual_norm = float(np.linalg.norm(rhs / np.maximum(np.abs(physical_state), 1.0), ord=2))
        eigvals = physical_eigenvalues(physical_state, env=env, coeff=coeff, imag_tol=DEFAULT_IMAG_TOL)
        classification = classify_eigenvalues(eigvals, real_tol=DEFAULT_REAL_TOL, imag_tol=DEFAULT_IMAG_TOL)

        for eigen_index, eigenvalue in enumerate(eigvals, start=1):
            rows.append(
                {
                    "backend": BACKEND,
                    "branch_id": BRANCH_ID,
                    "point_index": point_index,
                    "T_K": TEMPERATURE_K,
                    "p_Pa": PRESSURE_PA,
                    "F": SEDIMENTATION_F,
                    "N_a_m3": AEROSOL_N_A,
                    "N_a_cm3": AEROSOL_N_A / 1.0e6,
                    "log_w": point.control,
                    "w_m_s": w,
                    "log_n": point.state[0],
                    "log_q": point.state[1],
                    "n": n,
                    "q": q,
                    "s": s,
                    "continuation_residual_norm": point.residual_norm,
                    "physical_residual_norm": physical_residual_norm,
                    "scaled_physical_residual_norm": scaled_physical_residual_norm,
                    "converged": point.converged,
                    "iterations": point.iterations,
                    "message": point.message,
                    "eigen_index": eigen_index,
                    "eigenvalue_real": float(eigenvalue.real),
                    "eigenvalue_imag": float(eigenvalue.imag),
                    "eigenvalue_regime": classification.regime,
                    "stability_classification": classification.stability,
                    "jacobian_coordinate_system": "physical_ode_state",
                    "jacobian_method": "analytic_sympy_transcribed_physical_ode_jacobian",
                    "eigenvalue_source": "python_analytic",
                    "eigenvalue_sorting": "canonical_complex_pair_pos_imag_neg_imag_real_else_descending_real",
                    "source_file": _relative_path(Path(__file__)),
                }
            )
    return pd.DataFrame(rows)


def track_eigenvalue_branches(canonical_spectra: np.ndarray) -> np.ndarray:
    """Track adjacent eigenvalue identities by minimum complex-plane motion.

    The CSV's canonical eigenvalue order is useful for deterministic tabular
    comparison, but it is not a continuous branch identity through transitions
    between one-complex-pair and three-real spectra.  Plotting connected lines
    from canonical labels can therefore draw artificial vertical jumps.  This
    helper keeps the canonical values intact and creates plot-only labels that
    minimize adjacent point-to-point movement.
    """
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


def make_point_table(eigenvalue_rows: pd.DataFrame) -> pd.DataFrame:
    """Collapse long eigenvalue rows to one row per branch point with wide eigenvalues."""
    index_cols = [
        "backend",
        "branch_id",
        "point_index",
        "T_K",
        "p_Pa",
        "F",
        "N_a_m3",
        "N_a_cm3",
        "log_w",
        "w_m_s",
        "log_n",
        "log_q",
        "n",
        "q",
        "s",
        "continuation_residual_norm",
        "physical_residual_norm",
        "scaled_physical_residual_norm",
        "converged",
        "iterations",
        "message",
        "eigenvalue_regime",
        "stability_classification",
        "jacobian_coordinate_system",
        "jacobian_method",
        "eigenvalue_source",
    ]
    point_rows = eigenvalue_rows[index_cols].drop_duplicates().sort_values("point_index").reset_index(drop=True)
    canonical_spectra = np.empty((len(point_rows), 3), dtype=complex)
    for eigen_index in (1, 2, 3):
        part = eigenvalue_rows[eigenvalue_rows["eigen_index"] == eigen_index].sort_values("point_index")
        values = part["eigenvalue_real"].to_numpy() + 1j * part["eigenvalue_imag"].to_numpy()
        canonical_spectra[:, eigen_index - 1] = values
        point_rows[f"lambda{eigen_index}_real"] = values.real
        point_rows[f"lambda{eigen_index}_imag"] = values.imag

    tracked_spectra = track_eigenvalue_branches(canonical_spectra)
    for branch_index in (1, 2, 3):
        values = tracked_spectra[:, branch_index - 1]
        point_rows[f"tracked_lambda{branch_index}_real"] = values.real
        point_rows[f"tracked_lambda{branch_index}_imag"] = values.imag
    return point_rows


def estimate_hopf_crossings(point_rows: pd.DataFrame, imag_tol: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    spectra = []
    for _, row in point_rows.iterrows():
        spectra.append(
            np.array(
                [
                    complex(row.lambda1_real, row.lambda1_imag),
                    complex(row.lambda2_real, row.lambda2_imag),
                    complex(row.lambda3_real, row.lambda3_imag),
                ],
                dtype=complex,
            )
        )
    crossings = detect_hopf_crossings(point_rows["log_w"].to_numpy(), spectra, real_tol=0.0, imag_tol=imag_tol)
    crossing_rows = [asdict(crossing) for crossing in crossings]
    crossing_frame = pd.DataFrame(crossing_rows)

    comparison_rows: list[dict[str, Any]] = []
    if crossing_rows:
        crossing_ws = np.array([row["w"] for row in crossing_rows], dtype=float)
        for expected in EXPECTED_HOPF_W_M_S:
            i = int(np.argmin(np.abs(crossing_ws - expected)))
            observed = float(crossing_ws[i])
            comparison_rows.append(
                {
                    "expected_w_m_s": expected,
                    "observed_w_m_s": observed,
                    "abs_error_m_s": abs(observed - expected),
                    "within_documented_tolerance": bool(abs(observed - expected) <= HOPF_LANDMARK_TOLERANCE_M_S),
                    "documented_tolerance_m_s": HOPF_LANDMARK_TOLERANCE_M_S,
                    "crossing_index": i,
                }
            )
    comparison_frame = pd.DataFrame(comparison_rows)
    return crossing_frame, comparison_frame


def write_plot(point_rows: pd.DataFrame, output_path: Path) -> None:
    """Write a draft Figure 2-style real/imaginary eigenvalue plot."""
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 7.0), sharex=True, constrained_layout=True)
    colors = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}
    for eigen_index in (1, 2, 3):
        axes[0].plot(point_rows["w_m_s"], point_rows[f"tracked_lambda{eigen_index}_real"], color=colors[eigen_index], label=f"tracked λ{eigen_index}")
        axes[1].plot(point_rows["w_m_s"], point_rows[f"tracked_lambda{eigen_index}_imag"], color=colors[eigen_index], label=f"tracked λ{eigen_index}")
    axes[0].axhline(0.0, color="black", linewidth=0.8, alpha=0.6)
    axes[1].axhline(0.0, color="black", linewidth=0.8, alpha=0.6)
    axes[1].set_xscale("log")
    axes[0].set_ylabel("Re(λ) [s$^{-1}$]")
    axes[1].set_ylabel("Im(λ) [s$^{-1}$]")
    axes[1].set_xlabel("w [m s$^{-1}$]")
    axes[0].set_title("Draft Figure 2-style Python physical-Jacobian eigenvalues")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--points", type=int, default=DEFAULT_POINTS, help="Number of log-spaced w samples; must be at least 400.")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    args = parser.parse_args(argv)

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    eigenvalue_rows = generate_branch(args.points, args.tolerance, args.max_iterations)
    point_rows = make_point_table(eigenvalue_rows)
    crossing_frame, crossing_comparison = estimate_hopf_crossings(point_rows, DEFAULT_IMAG_TOL)

    eigenvalue_csv = output_dir / "python_figure2_eigenvalues.csv"
    point_csv = output_dir / "python_figure2_branch_points.csv"
    crossing_csv = output_dir / "python_figure2_hopf_crossings.csv"
    crossing_comparison_csv = output_dir / "python_figure2_hopf_landmark_comparison.csv"
    summary_json = output_dir / "python_figure2_summary.json"
    metadata_json = output_dir / "run_metadata.json"
    plot_png = output_dir / "python_figure2_eigenvalues.png"

    eigenvalue_rows.to_csv(eigenvalue_csv, index=False)
    point_rows.to_csv(point_csv, index=False)
    crossing_frame.to_csv(crossing_csv, index=False)
    crossing_comparison.to_csv(crossing_comparison_csv, index=False)
    write_plot(point_rows, plot_png)

    finite_converged_points = point_rows[
        point_rows["converged"].astype(bool)
        & np.isfinite(point_rows[["n", "q", "s", "lambda1_real", "lambda1_imag", "lambda2_real", "lambda2_imag", "lambda3_real", "lambda3_imag"]]).all(axis=1)
    ]
    summary = {
        "backend": BACKEND,
        "branch_id": BRANCH_ID,
        "point_count": int(len(point_rows)),
        "finite_converged_point_count": int(len(finite_converged_points)),
        "w_min_m_s": float(point_rows["w_m_s"].min()),
        "w_max_m_s": float(point_rows["w_m_s"].max()),
        "max_continuation_residual_norm": float(point_rows["continuation_residual_norm"].max()),
        "max_scaled_physical_residual_norm": float(point_rows["scaled_physical_residual_norm"].max()),
        "all_converged": bool(point_rows["converged"].all()),
        "regime_counts": point_rows["eigenvalue_regime"].value_counts().to_dict(),
        "stability_counts": point_rows["stability_classification"].value_counts().to_dict(),
        "hopf_crossings": crossing_frame.to_dict(orient="records"),
        "hopf_landmark_comparison": crossing_comparison.to_dict(orient="records"),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metadata = {
        "parameters": {
            "p_Pa": PRESSURE_PA,
            "p_hPa": PRESSURE_PA / 100.0,
            "T_K": TEMPERATURE_K,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "N_a_cm3": AEROSOL_N_A / 1.0e6,
            "N_a_assumption": "High-aerosol value inherited from Figure 1 reproduction: 1.0e10 m^-3 = 10000 cm^-3.",
            "w_min_m_s": W_MIN,
            "w_max_m_s": W_MAX,
        },
        "grid": {
            "coordinate": "log_w = natural log(w_m_s)",
            "density_points": args.points,
            "spacing": "uniform in log_w",
        },
        "continuation": {
            "state_coordinates": "log(n), log(q), s",
            "residual": "[dn/dt / n, dq/dt / q, ds/dt] from package equilibrium_residual",
            "tolerance": args.tolerance,
            "max_iterations": args.max_iterations,
            "stop_on_failure": False,
        },
        "jacobian": {
            "matrix": "d(dn/dt,dq/dt,ds/dt)/d(n,q,s) in physical ODE state coordinates",
            "method": "analytic SymPy-derived formula implemented by bergner_spichtinger_2026.stability.physical_jacobian",
            "evaporation": "disabled; discontinuous evaporation term is not included in the physical Jacobian",
        },
        "eigenvalues": {
            "source": "python_analytic",
            "sorting_tolerance_imag": DEFAULT_IMAG_TOL,
            "stability_real_tolerance": DEFAULT_REAL_TOL,
            "sorting_convention": "complex pair as positive-imaginary, negative-imaginary, remaining real eigenvalue; otherwise descending real part",
            "plot_branch_tracking": "plot uses tracked_lambda*_real/imag columns from adjacent minimum-distance matching in the complex plane to avoid connecting canonical-label identity swaps",
            "hopf_estimator": "linear interpolation of Re(complex-pair eigenvalues) in log_w",
            "paper_landmark_w_m_s": list(EXPECTED_HOPF_W_M_S),
            "paper_landmark_documented_tolerance_m_s": HOPF_LANDMARK_TOLERANCE_M_S,
        },
        "commands": {
            "invocation": " ".join([sys.executable, *sys.argv]),
            "recommended": "uv run python episodes/005-figure2-eigenvalues/scripts/generate_python_figure2_eigenvalues.py",
        },
        "software": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "package_version": package_version,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "outputs": [_relative_path(path) for path in [eigenvalue_csv, point_csv, crossing_csv, crossing_comparison_csv, summary_json, metadata_json, plot_png]],
    }
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote Python Figure 2 eigenvalue outputs to {output_dir}")


if __name__ == "__main__":
    main()
