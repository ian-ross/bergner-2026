#!/usr/bin/env python3
"""Run LOCA-side Figure 2 continuation with backend physical eigenvalues.

The top-level C++ executable owns the continuation residual, Sacado physical
Jacobian, and Teuchos::LAPACK GEEV eigenvalue calculation. This episode-local
orchestration layer builds the executable, runs the dense Figure 2 branch, and
splits primary branch/eigenvalue outputs from physical-Jacobian diagnostics.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from math import exp, log
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from importlib.metadata import PackageNotFoundError, version

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover
    package_version = "unknown"

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import equilibrium, vector_field
from bergner_spichtinger_2026.residuals import log_coordinates_from_physical_state

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "005-figure2-eigenvalues"
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
DEFAULT_BUILD_DIR = REPO_ROOT / ".pytest_cache" / "loca-figure2-build"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure2_loca_eigenvalues"

BACKEND = "loca"
BRANCH_ID = "figure2_T230K"
PRESSURE_PA = 30_000.0
TEMPERATURE_K = 230.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
DZ_M = 100.0
W_MIN = 0.0005
W_MAX = 2.0
LOG_W_MIN = log(W_MIN)
LOG_W_MAX = log(W_MAX)
DEFAULT_POINTS = 801
DEFAULT_TOLERANCE = 1.0e-10
DEFAULT_MAX_NEWTON_ITERATIONS = 40
SCHEMA_VERSION = "figure2-loca-eigenvalue-schema-v1"

POINT_FIELDNAMES = [
    "backend",
    "schema_version",
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
    "lambda1_real",
    "lambda1_imag",
    "lambda2_real",
    "lambda2_imag",
    "lambda3_real",
    "lambda3_imag",
    "eigenvalue_regime",
    "stability_classification",
    "jacobian_coordinate_system",
    "jacobian_method",
    "eigenvalue_source",
    "source_file",
]

EIGENVALUE_FIELDNAMES = [
    "backend",
    "schema_version",
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
    "eigen_index",
    "eigenvalue_real",
    "eigenvalue_imag",
    "eigenvalue_regime",
    "stability_classification",
    "jacobian_coordinate_system",
    "jacobian_method",
    "eigenvalue_source",
    "source_file",
]

JACOBIAN_FIELDNAMES = [
    "backend",
    "schema_version",
    "branch_id",
    "point_index",
    "log_w",
    "w_m_s",
    "n",
    "q",
    "s",
    "jacobian_coordinate_system",
    "jacobian_method",
    "physical_jacobian_11",
    "physical_jacobian_12",
    "physical_jacobian_13",
    "physical_jacobian_21",
    "physical_jacobian_22",
    "physical_jacobian_23",
    "physical_jacobian_31",
    "physical_jacobian_32",
    "physical_jacobian_33",
]


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_text(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def _build_executable(build_dir: Path) -> tuple[Path, list[dict[str, object]]]:
    if not TRILINOS_CONFIG.is_file():
        raise FileNotFoundError(f"Trilinos CMake config not found at {TRILINOS_CONFIG}")
    commands = [
        ["cmake", "-S", str(LOCA_ROOT), "-B", str(build_dir), f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}"],
        ["cmake", "--build", str(build_dir), "--parallel", "2"],
    ]
    records: list[dict[str, object]] = []
    for command in commands:
        result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
        records.append({"command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError(f"Command failed with return code {result.returncode}: {' '.join(command)}")
    executable = build_dir / "bs2026_loca_model"
    if not executable.is_file():
        raise FileNotFoundError(f"Expected LOCA executable not found at {executable}")
    return executable, records


def _initial_log_state() -> np.ndarray:
    env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=W_MIN, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    return log_coordinates_from_physical_state(equilibrium(env, bracket=(1.000001, 3.0)))


def _run_loca_continue(executable: Path, output_dir: Path, *, points: int, tolerance: float, max_newton_iterations: int) -> tuple[list[dict[str, str]], dict[str, object]]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "bs2026_loca_figure2_raw.csv"
    stderr_path = raw_dir / "bs2026_loca_figure2.stderr.txt"
    x0 = _initial_log_state()
    command = [
        str(executable),
        "continue",
        *(f"{value:.17g}" for value in x0),
        f"{LOG_W_MIN:.17g}",
        "--log-w-end",
        f"{LOG_W_MAX:.17g}",
        "--steps",
        str(points - 1),
        "--tol",
        f"{tolerance:.17g}",
        "--max-newton-iterations",
        str(max_newton_iterations),
        "--p",
        f"{PRESSURE_PA:.17g}",
        "--T",
        f"{TEMPERATURE_K:.17g}",
        "--F",
        f"{SEDIMENTATION_F:.17g}",
        "--N-a",
        f"{AEROSOL_N_A:.17g}",
        "--dz",
        f"{DZ_M:.17g}",
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    raw_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    rows: list[dict[str, str]] = []
    if result.stdout.strip():
        rows = list(csv.DictReader(result.stdout.splitlines()))
    return rows, {
        "command": command,
        "returncode": result.returncode,
        "stderr": result.stderr,
        "raw_csv": _relative_path(raw_path),
        "raw_stderr": _relative_path(stderr_path),
        "initial_log_state_from_python": [float(value) for value in x0],
    }


def _normalize(raw_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    point_rows: list[dict[str, Any]] = []
    eigenvalue_rows: list[dict[str, Any]] = []
    jacobian_rows: list[dict[str, Any]] = []
    source_file = _relative_path(Path(__file__))
    for point_index, row in enumerate(raw_rows):
        log_w = float(row["log_w"])
        log_n = float(row["log_n"])
        log_q = float(row["log_q"])
        n = exp(log_n)
        q = exp(log_q)
        s = float(row["s"])
        w = exp(log_w)
        env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=w, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
        physical_state = np.array([n, q, s], dtype=float)
        rhs = vector_field(n, q, s, env)
        physical_residual_norm = float(np.linalg.norm(rhs, ord=2))
        scaled_physical_residual_norm = float(np.linalg.norm(rhs / np.maximum(np.abs(physical_state), 1.0), ord=2))
        base = {
            "backend": BACKEND,
            "schema_version": SCHEMA_VERSION,
            "branch_id": BRANCH_ID,
            "point_index": point_index,
            "T_K": TEMPERATURE_K,
            "p_Pa": PRESSURE_PA,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "N_a_cm3": AEROSOL_N_A / 1.0e6,
            "log_w": log_w,
            "w_m_s": w,
            "log_n": log_n,
            "log_q": log_q,
            "n": n,
            "q": q,
            "s": s,
            "continuation_residual_norm": float(row["residual_norm"]),
            "physical_residual_norm": physical_residual_norm,
            "scaled_physical_residual_norm": scaled_physical_residual_norm,
            "converged": row["converged"],
            "iterations": int(row["newton_iterations"]),
            "message": row["continuation_status"],
            "eigenvalue_regime": row["eigenvalue_regime"],
            "stability_classification": row["stability_classification"],
            "jacobian_coordinate_system": row["jacobian_coordinate_system"],
            "jacobian_method": "sacado_forward_ad_physical_ode_state",
            "eigenvalue_source": row["eigenvalue_source"],
            "source_file": source_file,
        }
        wide = dict(base)
        for eigen_index in (1, 2, 3):
            wide[f"lambda{eigen_index}_real"] = float(row[f"lambda{eigen_index}_real"])
            wide[f"lambda{eigen_index}_imag"] = float(row[f"lambda{eigen_index}_imag"])
            eigenvalue_rows.append({
                **base,
                "eigen_index": eigen_index,
                "eigenvalue_real": float(row[f"lambda{eigen_index}_real"]),
                "eigenvalue_imag": float(row[f"lambda{eigen_index}_imag"]),
            })
        point_rows.append(wide)
        jacobian_rows.append({
            "backend": BACKEND,
            "schema_version": SCHEMA_VERSION,
            "branch_id": BRANCH_ID,
            "point_index": point_index,
            "log_w": log_w,
            "w_m_s": w,
            "n": n,
            "q": q,
            "s": s,
            "jacobian_coordinate_system": row["jacobian_coordinate_system"],
            "jacobian_method": "sacado_forward_ad_physical_ode_state",
            **{f"physical_jacobian_{i}{j}": float(row[f"physical_jacobian_{i}{j}"]) for i in (1, 2, 3) for j in (1, 2, 3)},
        })
    return point_rows, eigenvalue_rows, jacobian_rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _summary(point_rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(point_rows)
    finite_cols = ["n", "q", "s", "lambda1_real", "lambda1_imag", "lambda2_real", "lambda2_imag", "lambda3_real", "lambda3_imag"]
    finite_converged = frame[frame["converged"].astype(str).str.lower().eq("true") & np.isfinite(frame[finite_cols].to_numpy()).all(axis=1)]
    return {
        "backend": BACKEND,
        "branch_id": BRANCH_ID,
        "point_count": int(len(frame)),
        "finite_converged_point_count": int(len(finite_converged)),
        "w_min_m_s": float(frame["w_m_s"].min()) if len(frame) else None,
        "w_max_m_s": float(frame["w_m_s"].max()) if len(frame) else None,
        "max_continuation_residual_norm": float(frame["continuation_residual_norm"].max()) if len(frame) else None,
        "max_scaled_physical_residual_norm": float(frame["scaled_physical_residual_norm"].max()) if len(frame) else None,
        "all_converged": bool(frame["converged"].astype(str).str.lower().eq("true").all()) if len(frame) else False,
        "regime_counts": frame["eigenvalue_regime"].value_counts().to_dict() if len(frame) else {},
        "stability_counts": frame["stability_classification"].value_counts().to_dict() if len(frame) else {},
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--points", type=int, default=DEFAULT_POINTS, help="Number of log-spaced w samples; must be at least 400.")
    parser.add_argument("--tol", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--max-newton-iterations", type=int, default=DEFAULT_MAX_NEWTON_ITERATIONS)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(argv)

    if args.points < 400:
        raise ValueError("--points must be at least 400 for the Figure 2 LOCA eigenvalue contract.")
    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    executable, build_commands = _build_executable(args.build_dir)
    raw_rows, run_record = _run_loca_continue(executable, args.output_dir, points=args.points, tolerance=args.tol, max_newton_iterations=args.max_newton_iterations)
    if run_record["returncode"] != 0:
        raise RuntimeError(f"LOCA executable failed; see {args.output_dir / 'raw'}")
    point_rows, eigenvalue_rows, jacobian_rows = _normalize(raw_rows)

    point_csv = args.output_dir / "loca_figure2_branch_points.csv"
    eigenvalue_csv = args.output_dir / "loca_figure2_eigenvalues.csv"
    jacobian_csv = args.output_dir / "loca_figure2_physical_jacobian_diagnostics.csv"
    summary_json = args.output_dir / "loca_figure2_summary.json"
    metadata_json = args.output_dir / "run_metadata.json"

    _write_csv(point_csv, point_rows, POINT_FIELDNAMES)
    _write_csv(eigenvalue_csv, eigenvalue_rows, EIGENVALUE_FIELDNAMES)
    _write_csv(jacobian_csv, jacobian_rows, JACOBIAN_FIELDNAMES)
    summary = _summary(point_rows)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "loca_root": _relative_path(LOCA_ROOT),
        "loca_executable": _relative_path(executable),
        "schema_version": SCHEMA_VERSION,
        "parameters": {"p_Pa": PRESSURE_PA, "T_K": TEMPERATURE_K, "F": SEDIMENTATION_F, "N_a_m3": AEROSOL_N_A, "N_a_cm3": AEROSOL_N_A / 1.0e6, "dz_m": DZ_M, "w_min_m_s": W_MIN, "w_max_m_s": W_MAX},
        "grid": {"coordinate": "log_w = natural log(w_m_s)", "density_points": args.points, "spacing": "uniform in log_w"},
        "continuation": {"state_coordinates": "log(n), log(q), s", "residual": "C++ [dn/dt / n, dq/dt / q, ds/dt]", "tolerance": args.tol, "max_newton_iterations": args.max_newton_iterations},
        "jacobian": {"matrix": "d(dn/dt,dq/dt,ds/dt)/d(n,q,s)", "coordinate_system": "physical_ode_state", "method": "Sacado forward automatic differentiation in the LOCA C++ executable", "diagnostic_csv": _relative_path(jacobian_csv), "primary_csv_policy": "physical Jacobian entries are kept out of the primary branch/eigenvalue CSVs"},
        "eigenvalues": {"source": "teuchos_lapack_geev", "sorting_convention": "canonical_complex_pair_pos_imag_neg_imag_real_else_descending_real", "implementation_note": "Teuchos::LAPACK GEEV is used; no direct dgeev fallback was needed for this Trilinos build."},
        "outputs": [_relative_path(path) for path in [point_csv, eigenvalue_csv, jacobian_csv, summary_json, metadata_json]],
        "build_commands": build_commands,
        "run": run_record,
        "tool_versions": {"trilinos_config": str(TRILINOS_CONFIG), "trilinos_config_exists": TRILINOS_CONFIG.exists(), "cmake": _run_text(["cmake", "--version"]), "cxx": _run_text(["g++", "--version"])},
        "software": {"python": platform.python_version(), "platform": platform.platform(), "package_version": package_version, "numpy": np.__version__, "pandas": pd.__version__},
        "commands": {"invocation": " ".join([sys.executable, *sys.argv]), "recommended": "uv run python episodes/005-figure2-eigenvalues/scripts/run_loca_figure2_eigenvalues.py"},
        "summary": summary,
    }
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if summary["finite_converged_point_count"] < 400:
        raise RuntimeError("LOCA Figure 2 run produced fewer than 400 finite converged points.")
    print(f"Wrote LOCA Figure 2 eigenvalue outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
