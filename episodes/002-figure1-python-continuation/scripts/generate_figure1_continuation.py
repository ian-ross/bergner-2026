#!/usr/bin/env python3
"""Generate Figure 1 continuation branches and comparison tables.

The script follows equilibrium branches for p=300 hPa, F=1, T in
{190, 210, 230} K, and w in [0.005, 2.0] m/s.  It writes branch CSVs,
independent root-solve checks, analytic approximation comparisons, and summary
artifacts under the Episode 2 outputs directory by default.
"""

from __future__ import annotations

import argparse
import json
from math import exp, log
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import root

from bergner_spichtinger_2026.approximations import approximate_equilibrium
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.continuation import continue_branch
from bergner_spichtinger_2026.core import coefficients, equilibrium
from bergner_spichtinger_2026.residuals import (
    equilibrium_residual,
    log_coordinates_from_physical_state,
    make_equilibrium_residual,
    physical_state_from_log_coordinates,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "episodes" / "002-figure1-python-continuation" / "outputs" / "figure1_continuation"
TEMPERATURES_K = (190.0, 210.0, 230.0)
PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0
W_MIN = 0.005
W_MAX = 2.0


def _relative_error(a: float, b: float) -> float:
    denom = max(abs(float(a)), abs(float(b)), np.finfo(float).tiny)
    return abs(float(a) - float(b)) / denom


def _solve_independent_root(env: Environment, initial_guess_physical: np.ndarray) -> dict[str, object]:
    """Solve the fixed-w equilibrium independently from continuation state.

    The initial guess is analytic when available; the root problem is the same
    package residual in log coordinates.  This keeps the check independent of
    the continuation predictor-corrector path while using the same governing
    equations.
    """
    coeff = coefficients(env)
    initial = log_coordinates_from_physical_state(initial_guess_physical)
    log_w = log(env.w)
    sol = root(lambda x: equilibrium_residual(np.asarray(x, dtype=float), log_w, env, coeff=coeff), initial, method="hybr", options={"maxfev": 200})
    state_log = np.asarray(sol.x, dtype=float)
    state = physical_state_from_log_coordinates(state_log)
    residual_norm = float(np.linalg.norm(equilibrium_residual(state_log, log_w, env, coeff=coeff), ord=2))
    return {
        "state": state,
        "log_state": state_log,
        "converged": bool(sol.success and residual_norm <= 1e-8),
        "iterations": getattr(sol, "nfev", None),
        "message": str(sol.message),
        "residual_norm": residual_norm,
    }


def _branch_frame(T: float, controls: np.ndarray, tolerance: float) -> pd.DataFrame:
    env0 = Environment(p=PRESSURE_PA, T=T, w=float(exp(controls[0])), F=SEDIMENTATION_F)
    initial = log_coordinates_from_physical_state(equilibrium(env0))
    result = continue_branch(
        make_equilibrium_residual(env0),
        initial,
        controls,
        tolerance=tolerance,
        max_iterations=200,
        stop_on_failure=False,
    )

    rows: list[dict[str, object]] = []
    for point in result.points:
        n, q, s = physical_state_from_log_coordinates(point.state)
        rows.append(
            {
                "T_K": T,
                "p_Pa": PRESSURE_PA,
                "F": SEDIMENTATION_F,
                "log_w": point.control,
                "w_m_s": exp(point.control),
                "log_n": point.state[0],
                "log_q": point.state[1],
                "n": n,
                "q": q,
                "s": s,
                "converged": point.converged,
                "iterations": point.iterations,
                "message": point.message,
                "residual_norm": point.residual_norm,
            }
        )
    return pd.DataFrame(rows)


def _comparison_frames(branch: pd.DataFrame, sample_indices: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    detailed_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    variables = ("n", "q", "s")

    for _, row in branch.iloc[sample_indices].iterrows():
        env = Environment(p=float(row.p_Pa), T=float(row.T_K), w=float(row.w_m_s), F=float(row.F))
        continuation_state = np.array([row.n, row.q, row.s], dtype=float)
        analytic_state = approximate_equilibrium(env)
        root_result = _solve_independent_root(env, analytic_state)
        root_state = np.asarray(root_result["state"], dtype=float)

        for source, state, residual_norm, converged, iterations, message in (
            ("root_solve", root_state, root_result["residual_norm"], root_result["converged"], root_result["iterations"], root_result["message"]),
            ("analytic_eq92_94", analytic_state, np.nan, True, None, "direct formula"),
        ):
            values = dict(zip(variables, state, strict=True))
            detailed_rows.append(
                {
                    "T_K": row.T_K,
                    "p_Pa": row.p_Pa,
                    "F": row.F,
                    "log_w": row.log_w,
                    "w_m_s": row.w_m_s,
                    "source": source,
                    "n_continuation": row.n,
                    "q_continuation": row.q,
                    "s_continuation": row.s,
                    "n_check": values["n"],
                    "q_check": values["q"],
                    "s_check": values["s"],
                    "abs_diff_n": abs(row.n - values["n"]),
                    "abs_diff_q": abs(row.q - values["q"]),
                    "abs_diff_s": abs(row.s - values["s"]),
                    "rel_diff_n": _relative_error(row.n, values["n"]),
                    "rel_diff_q": _relative_error(row.q, values["q"]),
                    "rel_diff_s": _relative_error(row.s, values["s"]),
                    "check_converged": converged,
                    "check_iterations": iterations,
                    "check_message": message,
                    "check_residual_norm": residual_norm,
                }
            )

    detailed = pd.DataFrame(detailed_rows)
    for (T, source), group in detailed.groupby(["T_K", "source"], sort=True):
        summary: dict[str, object] = {"T_K": T, "source": source, "sample_count": int(len(group))}
        for var in variables:
            summary[f"max_abs_diff_{var}"] = float(group[f"abs_diff_{var}"].max())
            summary[f"median_abs_diff_{var}"] = float(group[f"abs_diff_{var}"].median())
            summary[f"max_rel_diff_{var}"] = float(group[f"rel_diff_{var}"].max())
            summary[f"median_rel_diff_{var}"] = float(group[f"rel_diff_{var}"].median())
        summary["max_check_residual_norm"] = float(group["check_residual_norm"].max(skipna=True)) if group["check_residual_norm"].notna().any() else None
        summary["all_checks_converged"] = bool(group["check_converged"].all())
        summary_rows.append(summary)

    return detailed, pd.DataFrame(summary_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--points", type=int, default=241, help="Number of geometric w samples per branch.")
    parser.add_argument("--check-samples", type=int, default=17, help="Number of sampled continuation points per temperature for root/analytic comparisons.")
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    if args.points < 2:
        raise ValueError("--points must be at least 2.")
    if args.check_samples < 2:
        raise ValueError("--check-samples must be at least 2.")

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    controls = np.linspace(log(W_MIN), log(W_MAX), args.points)
    sample_indices = np.unique(np.rint(np.linspace(0, args.points - 1, min(args.check_samples, args.points))).astype(int))

    branch_frames = []
    detailed_frames = []
    summary_frames = []
    for T in TEMPERATURES_K:
        branch = _branch_frame(T, controls, args.tolerance)
        branch_frames.append(branch)
        branch.to_csv(output_dir / f"branch_T{int(T)}K.csv", index=False)

        detailed, summary = _comparison_frames(branch, sample_indices)
        detailed_frames.append(detailed)
        summary_frames.append(summary)

    branches = pd.concat(branch_frames, ignore_index=True)
    comparisons = pd.concat(detailed_frames, ignore_index=True)
    summary = pd.concat(summary_frames, ignore_index=True)

    branches.to_csv(output_dir / "branches_all.csv", index=False)
    comparisons.to_csv(output_dir / "comparison_details.csv", index=False)
    summary.to_csv(output_dir / "comparison_summary.csv", index=False)
    (output_dir / "comparison_summary.json").write_text(json.dumps(summary.to_dict(orient="records"), indent=2), encoding="utf-8")

    run_metadata = {
        "temperatures_K": list(TEMPERATURES_K),
        "p_Pa": PRESSURE_PA,
        "F": SEDIMENTATION_F,
        "w_min_m_s": W_MIN,
        "w_max_m_s": W_MAX,
        "points_per_branch": args.points,
        "check_sample_indices": sample_indices.tolist(),
        "tolerance": args.tolerance,
        "outputs": [
            "branch_T190K.csv",
            "branch_T210K.csv",
            "branch_T230K.csv",
            "branches_all.csv",
            "comparison_details.csv",
            "comparison_summary.csv",
            "comparison_summary.json",
        ],
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2), encoding="utf-8")
    print(f"Wrote Figure 1 continuation outputs to {output_dir}")


if __name__ == "__main__":
    main()
