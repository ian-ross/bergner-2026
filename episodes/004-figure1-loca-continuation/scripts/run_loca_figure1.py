#!/usr/bin/env python3
"""Run Episode 4 LOCA-style Figure 1 log-w equilibrium continuation.

The C++ executable owns the residual, Sacado state Jacobian, and branch
corrector.  This orchestration layer builds the reusable top-level LOCA model,
computes the first Figure 1 equilibrium state from the Python semantic reference,
runs the C++ continuation mode for each requested temperature, and normalizes the
raw rows to the backend-neutral branch schema established in Episode 3.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from math import exp, log
from pathlib import Path

import numpy as np

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import coefficients, equilibrium
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "004-figure1-loca-continuation"
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
DEFAULT_BUILD_DIR = REPO_ROOT / ".pytest_cache" / "loca-figure1-build"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure1_loca_branches"
TEMPERATURES_K = (190.0, 210.0, 230.0)
PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
DZ_M = 100.0
W_MIN = 0.005
W_MAX = 2.0
LOG_W_MIN = log(W_MIN)
LOG_W_MAX = log(W_MAX)
SCHEMA_VERSION = "figure1-branch-schema-v1"
BACKEND = "loca"
BRANCH_FIELDNAMES = [
    "backend",
    "schema_version",
    "branch_id",
    "T_K",
    "temperature_K",
    "p_Pa",
    "pressure_Pa",
    "F",
    "N_a_m3",
    "log_w",
    "w_m_s",
    "log_n",
    "log_q",
    "n",
    "n_kg_dry_air_inv",
    "q",
    "q_kg_kg",
    "s",
    "residual_norm",
    "converged",
    "stability",
    "backend_step_index",
    "source_file",
    "loca_newton_iterations",
    "loca_continuation_status",
    "loca_step_size",
    "loca_continuation_mode",
]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_text(command: list[str], *, cwd: Path | None = None) -> dict[str, object]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _tool_versions() -> dict[str, object]:
    return {
        "trilinos_config": str(TRILINOS_CONFIG),
        "trilinos_config_exists": TRILINOS_CONFIG.exists(),
        "cmake": _run_text(["cmake", "--version"]),
        "cxx": _run_text(["g++", "--version"]),
    }


def _build_executable(build_dir: Path) -> tuple[Path, list[dict[str, object]]]:
    if not TRILINOS_CONFIG.is_file():
        raise FileNotFoundError(f"Trilinos CMake config not found at {TRILINOS_CONFIG}")
    configure = ["cmake", "-S", str(LOCA_ROOT), "-B", str(build_dir), f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}"]
    build = ["cmake", "--build", str(build_dir), "--parallel", "2"]
    commands: list[dict[str, object]] = []
    for command in (configure, build):
        result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
        commands.append({"command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError(f"Command failed with return code {result.returncode}: {' '.join(command)}")
    executable = build_dir / "bs2026_loca_model"
    if not executable.is_file():
        raise FileNotFoundError(f"Expected LOCA executable not found at {executable}")
    return executable, commands


def _branch_id(T: float) -> str:
    return f"figure1_T{int(T)}K"


def _raw_source_file(T: float) -> str:
    return f"raw/bs2026_loca_T{int(T)}K.csv"


def _initial_log_state(T: float) -> np.ndarray:
    env = Environment(p=PRESSURE_PA, T=T, w=W_MIN, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    return log_coordinates_from_physical_state(equilibrium(env))


def _read_raw_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _residual_norm(log_n: float, log_q: float, s: float, log_w: float, T: float) -> float:
    env = Environment(p=PRESSURE_PA, T=T, w=exp(log_w), F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    residual = equilibrium_residual([log_n, log_q, s], log_w, env, coeff=coefficients(env))
    return float(np.linalg.norm(residual, ord=2))


def _normalize_rows(T: float, rows: list[dict[str, str]], *, backend_label: str = BACKEND) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    source_file = _raw_source_file(T)
    for row in rows:
        log_w = float(row["log_w"])
        log_n = float(row["log_n"])
        log_q = float(row["log_q"])
        s = float(row["s"])
        n = exp(log_n)
        q = exp(log_q)
        records.append({
            "backend": backend_label,
            "schema_version": SCHEMA_VERSION,
            "branch_id": _branch_id(T),
            "T_K": T,
            "temperature_K": T,
            "p_Pa": PRESSURE_PA,
            "pressure_Pa": PRESSURE_PA,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "log_w": log_w,
            "w_m_s": exp(log_w),
            "log_n": log_n,
            "log_q": log_q,
            "n": n,
            "n_kg_dry_air_inv": n,
            "q": q,
            "q_kg_kg": q,
            "s": s,
            "residual_norm": _residual_norm(log_n, log_q, s, log_w, T),
            "converged": row["converged"],
            "stability": "",
            "backend_step_index": int(row["backend_step_index"]),
            "source_file": source_file,
            "loca_newton_iterations": int(row["newton_iterations"]),
            "loca_continuation_status": row["continuation_status"],
            "loca_step_size": float(row["step_size"]),
            "loca_continuation_mode": row["loca_continuation_mode"],
        })
    return records


def _write_csv(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def _diagnose_records(T: float, records: list[dict[str, object]], returncode: int, stderr: str) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    if returncode != 0:
        errors.append(f"LOCA executable exited with return code {returncode}")
    if not records:
        errors.append("LOCA continuation produced no normalized rows.")
        return {"ok": False, "errors": errors, "warnings": warnings, "temperature_K": T}

    log_ws = np.array([float(row["log_w"]) for row in records], dtype=float)
    residual_norms = np.array([float(row["residual_norm"]) for row in records], dtype=float)
    n_values = np.array([float(row["n"]) for row in records], dtype=float)
    q_values = np.array([float(row["q"]) for row in records], dtype=float)
    tolerance = 5.0e-10
    if float(log_ws.min()) > LOG_W_MIN + tolerance:
        errors.append(f"minimum log_w {log_ws.min():.6g} did not reach requested {LOG_W_MIN:.6g}")
    if float(log_ws.max()) < LOG_W_MAX - tolerance:
        errors.append(f"maximum log_w {log_ws.max():.6g} did not reach requested {LOG_W_MAX:.6g}")
    if not bool(np.all(n_values > 0.0)):
        errors.append("normalized branch contains non-positive n values")
    if not bool(np.all(q_values > 0.0)):
        errors.append("normalized branch contains non-positive q values")
    if not bool(np.all(np.isfinite(residual_norms))):
        errors.append("normalized branch contains non-finite residual norms")
    if not all(str(row["converged"]).lower() == "true" for row in records):
        errors.append("one or more LOCA continuation points did not converge")
    if float(residual_norms.max()) > 1.0e-7:
        errors.append(f"maximum residual norm {residual_norms.max():.6g} exceeds tolerance")
    joined = stderr.lower()
    for needle in ("error", "failed", "no convergence", "abnormal"):
        if needle in joined:
            warnings.append(f"LOCA stderr contains diagnostic token: {needle}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "temperature_K": T,
        "branch_id": _branch_id(T),
        "branch_csv": f"branch_T{int(T)}K.csv",
        "raw_output": _raw_source_file(T),
        "row_count": len(records),
        "log_w_min": float(log_ws.min()),
        "log_w_max": float(log_ws.max()),
        "w_min_m_s": float(np.exp(log_ws.min())),
        "w_max_m_s": float(np.exp(log_ws.max())),
        "max_residual_norm": float(residual_norms.max()),
        "min_n": float(n_values.min()),
        "min_q": float(q_values.min()),
    }


def _run_temperature(T: float, executable: Path, output_dir: Path, *, steps: int, tolerance: float, backend_command: str = "continue", backend_label: str = BACKEND) -> tuple[list[dict[str, object]], dict[str, object]]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / _raw_source_file(T)
    x0 = _initial_log_state(T)
    command = [
        str(executable),
        backend_command,
        *(f"{value:.17g}" for value in x0),
        f"{LOG_W_MIN:.17g}",
        "--log-w-end",
        f"{LOG_W_MAX:.17g}",
        "--steps",
        str(steps),
        "--tol",
        f"{tolerance:.17g}",
        "--p",
        f"{PRESSURE_PA:.17g}",
        "--T",
        f"{T:.17g}",
        "--F",
        f"{SEDIMENTATION_F:.17g}",
        "--N-a",
        f"{AEROSOL_N_A:.17g}",
        "--dz",
        f"{DZ_M:.17g}",
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    raw_path.write_text(result.stdout, encoding="utf-8")
    (raw_dir / f"bs2026_loca_T{int(T)}K.stderr.txt").write_text(result.stderr, encoding="utf-8")
    raw_rows = _read_raw_rows(raw_path) if result.stdout.strip() else []
    records = _normalize_rows(T, raw_rows, backend_label=backend_label) if raw_rows else []
    branch_csv = output_dir / f"branch_T{int(T)}K.csv"
    _write_csv(branch_csv, records)
    diagnostics = _diagnose_records(T, records, result.returncode, result.stderr)
    diagnostics.update({
        "command": command,
        "returncode": result.returncode,
        "initial_log_state_from_python": [float(value) for value in x0],
        "normalized_schema_columns": BRANCH_FIELDNAMES,
        "schema_version": SCHEMA_VERSION,
    })
    return records, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--temperatures", type=float, nargs="*", default=list(TEMPERATURES_K))
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--tol", type=float, default=1.0e-10)
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before running.")
    parser.add_argument("--backend-command", choices=["continue", "nox-loca-continue"], default="continue")
    parser.add_argument("--backend-label", default=BACKEND)
    args = parser.parse_args()

    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    executable, build_commands = _build_executable(args.build_dir)
    metadata: dict[str, object] = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "loca_root": _display_path(LOCA_ROOT),
        "loca_executable": _display_path(executable),
        "schema_version": SCHEMA_VERSION,
        "normalized_schema_columns": BRANCH_FIELDNAMES,
        "coordinates": {"state": ["log_n", "log_q", "s"], "continuation_parameter": "log_w"},
        "backend_command": args.backend_command,
        "backend_label": args.backend_label,
        "continuation_mode": "C++ natural-parameter predictor/corrector using residual and Sacado state Jacobian",
        "p_Pa": PRESSURE_PA,
        "F": SEDIMENTATION_F,
        "N_a_m3": AEROSOL_N_A,
        "dz_m": DZ_M,
        "w_min_m_s": W_MIN,
        "w_max_m_s": W_MAX,
        "temperatures_K": list(args.temperatures),
        "steps": args.steps,
        "newton_tolerance": args.tol,
        "tool_versions": _tool_versions(),
        "build_commands": build_commands,
        "runs": [],
    }

    all_records: list[dict[str, object]] = []
    branch_csvs: list[str] = []
    all_ok = True
    for T in args.temperatures:
        records, diagnostics = _run_temperature(T, executable, args.output_dir, steps=args.steps, tolerance=args.tol, backend_command=args.backend_command, backend_label=args.backend_label)
        all_records.extend(records)
        metadata["runs"].append(diagnostics)
        all_ok = all_ok and bool(diagnostics.get("ok"))
        branch_csvs.append(f"branch_T{int(T)}K.csv")

    _write_csv(args.output_dir / "branches_all.csv", all_records)
    metadata["combined_branch_csv"] = "branches_all.csv"
    metadata["normalized_branch_csvs"] = branch_csvs
    metadata["raw_loca_output_paths"] = [run.get("raw_output") for run in metadata["runs"]]

    (args.output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output_dir / "run_diagnostics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if not all_ok:
        raise RuntimeError(f"One or more LOCA runs failed diagnostics; see {args.output_dir / 'run_diagnostics.json'}")
    print(f"Wrote LOCA Figure 1 continuation outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
