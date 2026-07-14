#!/usr/bin/env python3
"""Run native NOX/LOCA Moore--Spence Hopf continuation for Figure 3.

This script is only orchestration/normalization.  The Hopf solves and branch
continuation are performed by the C++ executable command
``bs2026_loca_model nox-loca-hopf-continue``, which constructs LOCA's native
``LOCA::Hopf::MooreSpence::ExtendedGroup`` around the TASK-025 dense
``LOCA::LAPACK`` backend.  No Python Hopf corrector is used here.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from math import exp, log
from pathlib import Path
from typing import Any

import pandas as pd

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover
    package_version = "unknown"

from bergner_spichtinger_2026.approximations import table_ii_lower_hopf_w, table_ii_upper_hopf_w
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import equilibrium
from bergner_spichtinger_2026.residuals import log_coordinates_from_physical_state

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation"
LOCA_ROOT = REPO_ROOT / "loca"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
DEFAULT_BUILD_DIR = REPO_ROOT / ".pytest_cache" / "loca-figure3-hopf-build"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure3_loca_hopf_loci"
DEFAULT_COMPARISON_DIR = EPISODE_DIR / "outputs" / "figure3_backend_comparison"

BACKEND = "loca"
SCHEMA_VERSION = "episode6-hopf-locus-schema-v1"
PRESSURE_PA = 30_000.0
SEED_T_K = 230.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
DZ_M = 100.0
LOWER_SEED_W_M_S = 0.048531
UPPER_SEED_W_M_S = 0.768680
T_MIN = 190.0
T_MAX = 240.0
ANCHOR_TOLERANCE_M_S = 2.0e-5

FIELDNAMES = [
    "backend", "schema_version", "branch_id", "paper_fit_branch", "point_index", "T_K", "p_Pa", "F",
    "N_a_m3", "N_a_cm3", "log_w", "w_m_s", "table_ii_reference_w_m_s", "log_n", "log_q", "n", "q", "s",
    "hopf_frequency", "eigenvalue_real", "eigenvalue_imag", "residual_norm", "converged", "iterations", "message",
    "jacobian_coordinate_system", "state_coordinate_system", "continuation_parameterization", "method", "method_metadata",
    "source_file", "raw_loca_run", "loca_continuation_mode", "loca_native_hopf_stepper",
]


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_text(command: list[str], *, cwd: Path | None = None) -> dict[str, object]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def _build_executable(build_dir: Path) -> tuple[Path, list[dict[str, object]]]:
    if not TRILINOS_CONFIG.is_file():
        raise FileNotFoundError(f"Trilinos CMake config not found at {TRILINOS_CONFIG}")
    commands = [
        ["cmake", "-S", str(LOCA_ROOT), "-B", str(build_dir), f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}"],
        ["cmake", "--build", str(build_dir), "--parallel", "2"],
    ]
    results: list[dict[str, object]] = []
    for command in commands:
        result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
        results.append({"command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError(f"Command failed with return code {result.returncode}: {' '.join(command)}")
    executable = build_dir / "bs2026_loca_model"
    if not executable.is_file():
        raise FileNotFoundError(f"Expected LOCA executable not found at {executable}")
    return executable, results


def _seed_log_state(seed_T: float, w_m_s: float) -> list[float]:
    # Seed equilibrium only; Hopf correction/continuation is in C++ LOCA.
    env = Environment(p=PRESSURE_PA, T=seed_T, w=w_m_s, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    return [float(v) for v in log_coordinates_from_physical_state(equilibrium(env, bracket=(1.000001, 3.0)))]


def _run_branch_piece(executable: Path, branch_id: str, seed_T: float, seed_w: float, target_T: float, steps: int, raw_dir: Path) -> list[dict[str, str]]:
    x0 = _seed_log_state(seed_T, seed_w)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{branch_id}_T{seed_T:g}_to_T{target_T:g}"
    raw_csv = raw_dir / f"{stem}.csv"
    cmd = [
        str(executable), "nox-loca-hopf-continue", *(f"{v:.17g}" for v in x0), f"{log(seed_w):.17g}",
        "--T", f"{seed_T:.17g}", "--T-end", f"{target_T:.17g}", "--steps", str(steps),
        "--p", f"{PRESSURE_PA:.17g}", "--F", f"{SEDIMENTATION_F:.17g}", "--N-a", f"{AEROSOL_N_A:.17g}",
        "--dz", f"{DZ_M:.17g}", "--tol", "1e-6", "--max-newton-iterations", "100",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    raw_csv.write_text(result.stdout, encoding="utf-8")
    (raw_dir / f"{stem}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        if "TEUCHOS_COMPLEX" in result.stderr or "Teuchos_ENABLE_COMPLEX" in result.stderr:
            raise RuntimeError(
                "Native LOCA Moore-Spence Hopf continuation requires a Trilinos build with Teuchos complex support "
                "(Teuchos_ENABLE_COMPLEX). The installed /opt/Trilinos build rejected LOCA::LAPACK::computeComplex()."
            )
        raise RuntimeError(f"Native LOCA Hopf command failed for {stem}; see {raw_dir / (stem + '.stderr.txt')}")
    with raw_csv.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalize(raw_rows: list[dict[str, str]], branch_id: str, raw_source: str) -> list[dict[str, Any]]:
    records = []
    paper_fit_branch = "wb" if branch_id == "lower_hopf" else "wa"
    seen: set[float] = set()
    for row in sorted(raw_rows, key=lambda r: float(r["T"])):
        T = round(float(row["T"]), 10)
        if T in seen:
            continue
        seen.add(T)
        log_w = float(row["log_w"])
        fit = table_ii_lower_hopf_w(T) if branch_id == "lower_hopf" else table_ii_upper_hopf_w(T)
        records.append({
            "backend": BACKEND,
            "schema_version": SCHEMA_VERSION,
            "branch_id": branch_id,
            "paper_fit_branch": paper_fit_branch,
            "point_index": len(records),
            "T_K": T,
            "p_Pa": PRESSURE_PA,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "N_a_cm3": AEROSOL_N_A / 1e6,
            "log_w": log_w,
            "w_m_s": exp(log_w),
            "table_ii_reference_w_m_s": float(fit),
            "log_n": float(row["log_n"]),
            "log_q": float(row["log_q"]),
            "n": exp(float(row["log_n"])),
            "q": exp(float(row["log_q"])),
            "s": float(row["s"]),
            "hopf_frequency": float(row["hopf_frequency"]),
            "eigenvalue_real": float(row["lambda1_real"]),
            "eigenvalue_imag": float(row["lambda1_imag"]),
            "residual_norm": float(row["residual_norm"]),
            "converged": str(row["converged"]).lower() == "true",
            "iterations": int(row["newton_iterations"]),
            "message": "Native LOCA Moore-Spence Hopf continuation row from C++ executable.",
            "jacobian_coordinate_system": "physical_ode_state",
            "state_coordinate_system": "log_n_log_q_s_internal__physical_state_output",
            "continuation_parameterization": "LOCA_MooreSpence_Hopf_bifurcation_parameter_log_w_continued_in_T",
            "method": "native_LOCA_MooreSpence_Hopf_continuation",
            "method_metadata": "C++ LOCA::Hopf::MooreSpence::ExtendedGroup over TASK-025 LOCA::LAPACK backend; no Python Hopf corrector.",
            "source_file": _relative_path(Path(__file__)),
            "raw_loca_run": raw_source,
            "loca_continuation_mode": row["loca_continuation_mode"],
            "loca_native_hopf_stepper": True,
        })
    return records


def _load_plotter_module():
    spec = importlib.util.spec_from_file_location("plot_figure3_hopf_loci", Path(__file__).with_name("plot_figure3_hopf_loci.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_loca(output_dir: Path, build_dir: Path, steps_each_side: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    executable, build_commands = _build_executable(build_dir)
    raw_dir = output_dir / "raw" / "native_loca_hopf"
    all_records: list[dict[str, Any]] = []
    lower_down = _run_branch_piece(executable, "lower_hopf", SEED_T_K, LOWER_SEED_W_M_S, T_MIN, steps_each_side, raw_dir)
    lower_up = _run_branch_piece(executable, "lower_hopf", SEED_T_K, LOWER_SEED_W_M_S, T_MAX, max(1, int(round((T_MAX - SEED_T_K) / ((SEED_T_K - T_MIN) / steps_each_side)))), raw_dir)
    raw_source = _relative_path(raw_dir)
    all_records.extend(_normalize(lower_down + lower_up, "lower_hopf", raw_source))

    upper_down = _run_branch_piece(executable, "upper_hopf", SEED_T_K, UPPER_SEED_W_M_S, T_MIN, steps_each_side, raw_dir)
    upper_endpoint_w = float(table_ii_upper_hopf_w(T_MAX))
    upper_up_reversed = _run_branch_piece(executable, "upper_hopf", T_MAX, upper_endpoint_w, SEED_T_K, max(1, int(round((T_MAX - SEED_T_K) / ((SEED_T_K - T_MIN) / steps_each_side)))), raw_dir)
    all_records.extend(_normalize(upper_down + upper_up_reversed, "upper_hopf", raw_source))
    frame = pd.DataFrame(all_records, columns=FIELDNAMES).sort_values(["branch_id", "T_K"]).reset_index(drop=True)
    diagnostics = {"ok": True, "build_commands": build_commands, "native_loca_hopf": True, "executable": _relative_path(executable)}
    return frame, diagnostics


def write_outputs(frame: pd.DataFrame, diagnostics: dict[str, Any], output_dir: Path, argv: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    loci_csv = output_dir / "loca_figure3_hopf_loci.csv"
    frame.to_csv(loci_csv, index=False)
    frame[frame["T_K"].sub(SEED_T_K).abs() < 1e-9].to_csv(output_dir / "loca_figure3_hopf_seeds.csv", index=False)
    diagnostics_path = output_dir / "run_diagnostics.json"
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8")
    branch_summaries = []
    for branch_id, group in frame.groupby("branch_id"):
        anchor = LOWER_SEED_W_M_S if branch_id == "lower_hopf" else UPPER_SEED_W_M_S
        nearest = group.iloc[(group["T_K"] - SEED_T_K).abs().argsort().iloc[0]]
        branch_summaries.append({"branch_id": branch_id, "T230_abs_error_m_s": abs(float(nearest["w_m_s"]) - anchor), "T230_within_tolerance": abs(float(nearest["w_m_s"]) - anchor) <= ANCHOR_TOLERANCE_M_S})
    summary = {"backend": BACKEND, "schema_version": SCHEMA_VERSION, "branches": sorted(frame["branch_id"].unique()), "row_count": len(frame), "all_converged": bool(frame["converged"].all()), "native_loca_hopf": True, "branch_summaries": branch_summaries}
    (output_dir / "loca_figure3_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    metadata = {"created_utc": datetime.now(timezone.utc).isoformat(), "backend": BACKEND, "package_version": package_version, "python_version": sys.version, "platform": platform.platform(), "command": " ".join([sys.executable, _relative_path(Path(__file__)), *argv]), "method": {"name": "native LOCA Moore-Spence Hopf continuation", "python_corrector_used": False}, "diagnostics": diagnostics}
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    plotter = _load_plotter_module()
    plotter.write_backend_plot(frame, output_dir / "loca_figure3_hopf_loci.png", backend=BACKEND)
    frames = []
    for path in [EPISODE_DIR / "outputs" / "figure3_python_hopf_loci" / "python_figure3_hopf_loci.csv", EPISODE_DIR / "outputs" / "figure3_auto_hopf_loci" / "auto_figure3_hopf_loci.csv", loci_csv]:
        if path.exists():
            frames.append(pd.read_csv(path))
    plotter.write_comparison_plot(frames, DEFAULT_COMPARISON_DIR / "figure3_hopf_backend_comparison.png")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--steps-each-side", type=int, default=40)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.clean:
        if args.output_dir.exists():
            shutil.rmtree(args.output_dir)
        if args.build_dir.exists():
            shutil.rmtree(args.build_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame, diagnostics = run_loca(args.output_dir, args.build_dir, args.steps_each_side)
    write_outputs(frame, diagnostics, args.output_dir, list(sys.argv[1:] if argv is None else argv))
    print(f"Wrote native LOCA Figure 3 Hopf outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
