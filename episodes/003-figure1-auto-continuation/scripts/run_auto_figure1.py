#!/usr/bin/env python3
"""Run Episode 3 AUTO-07p Figure 1 log-w equilibrium continuation.

The generated AUTO problem files use the shared top-level Fortran model core and
continue equilibria of the transformed system in (log n, log q, s) with PAR(1)
= log(w).  Raw AUTO outputs, generated run files, command provenance, tool
versions, backend-neutral normalized branch CSVs, and diagnostics are written
under the Episode 3 outputs directory by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, log
from pathlib import Path

import numpy as np

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import coefficients, equilibrium
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "003-figure1-auto-continuation"
AUTO_DIR = EPISODE_DIR / "auto"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure1_auto_branches"
TEMPLATE_F90 = AUTO_DIR / "bs2026_figure1_template.f90"
TEMPLATE_C = AUTO_DIR / "c.bs2026_figure1"
TEMPERATURES_K = (190.0, 210.0, 230.0)
PRESSURE_PA = 30_000.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
DZ_M = 100.0
W_MIN = 0.005
W_MAX = 2.0
LOG_W_MIN = log(W_MIN)
LOG_W_MAX = log(W_MAX)
AUTO_BIN = Path("/usr/local/bin/auto")
SCHEMA_VERSION = "figure1-branch-schema-v1"
BACKEND = "auto"
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
    "auto_branch",
    "auto_point",
    "auto_type_code",
    "auto_label",
    "auto_l2_norm",
]


@dataclass(frozen=True)
class AutoRow:
    branch: int
    point: int
    type_code: int
    label: int
    log_w: float
    l2_norm: float
    log_n: float
    log_q: float
    s: float

    @property
    def w_m_s(self) -> float:
        return exp(self.log_w)

    @property
    def n(self) -> float:
        return exp(self.log_n)

    @property
    def q(self) -> float:
        return exp(self.log_q)


def _run_text(command: list[str], *, cwd: Path | None = None) -> dict[str, object]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _tool_versions() -> dict[str, object]:
    auto_dir = Path("/usr/local/lib64/auto-07p")
    versions = {
        "auto_path": str(AUTO_BIN),
        "auto_exists": AUTO_BIN.exists(),
        "auto_dir": str(auto_dir),
        "auto_version_label": auto_dir.name,
        "auto_launcher_head": AUTO_BIN.read_text(encoding="utf-8", errors="replace").splitlines()[:8] if AUTO_BIN.exists() else [],
        "gfortran": _run_text(["gfortran", "--version"]),
    }
    return versions


def _format_fortran_float(value: float) -> str:
    return f"{value:.17e}".replace("e", "d")


def _render_problem(T: float) -> str:
    env = Environment(p=PRESSURE_PA, T=T, w=W_MIN, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    log_state = log_coordinates_from_physical_state(equilibrium(env))
    replacements = {
        "@LOG_N@": _format_fortran_float(float(log_state[0])),
        "@LOG_Q@": _format_fortran_float(float(log_state[1])),
        "@S@": _format_fortran_float(float(log_state[2])),
        "@LOG_W_MIN@": _format_fortran_float(LOG_W_MIN),
        "@PRESSURE_PA@": _format_fortran_float(PRESSURE_PA),
        "@TEMPERATURE_K@": _format_fortran_float(T),
        "@SEDIMENTATION_F@": _format_fortran_float(SEDIMENTATION_F),
        "@AEROSOL_N_A@": _format_fortran_float(AEROSOL_N_A),
        "@DZ_M@": _format_fortran_float(DZ_M),
    }
    text = TEMPLATE_F90.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _render_constants() -> str:
    return TEMPLATE_C.read_text(encoding="utf-8").replace("__LOG_W_MIN__", f"{LOG_W_MIN:.17e}").replace("__LOG_W_MAX__", f"{LOG_W_MAX:.17e}")


def _auto_script(stem: str) -> str:
    return "\n".join([
        f"ld('{stem}')",
        f"run(c='{stem}')",
        f"sv('{stem}')",
        "cl()",
        "",
    ])


def _parse_b_file(path: Path) -> list[AutoRow]:
    rows: list[AutoRow] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            branch = int(parts[0])
            point = int(parts[1])
            type_code = int(parts[2])
            label = int(parts[3])
            values = [float(part.replace("D", "E")) for part in parts[4:9]]
        except ValueError:
            continue
        if branch == 0:
            continue
        rows.append(AutoRow(branch, point, type_code, label, *values))
    return rows


def _requested_range_rows(rows: list[AutoRow], *, tolerance: float = 5.0e-4) -> list[AutoRow]:
    """Keep raw AUTO points in the requested Figure 1 range, including UZ endpoints."""
    return [row for row in rows if LOG_W_MIN - tolerance <= row.log_w <= LOG_W_MAX + tolerance]


def _diagnose(rows: list[AutoRow], stdout: str, stderr: str) -> dict[str, object]:
    if not rows:
        return {"ok": False, "errors": ["AUTO branch file contained no parseable branch rows."], "warnings": []}

    all_log_ws = np.array([row.log_w for row in rows], dtype=float)
    requested_rows = _requested_range_rows(rows)
    if not requested_rows:
        return {"ok": False, "errors": ["AUTO branch file had no rows in the requested log_w range."], "warnings": []}
    log_ws = np.array([row.log_w for row in requested_rows], dtype=float)
    type_codes = sorted({row.type_code for row in requested_rows if row.type_code != 0})
    errors: list[str] = []
    warnings: list[str] = []
    tolerance = 5.0e-4
    if float(log_ws.min()) > LOG_W_MIN + tolerance:
        errors.append(f"minimum log_w {log_ws.min():.6g} did not reach requested {LOG_W_MIN:.6g}")
    if float(log_ws.max()) < LOG_W_MAX - tolerance:
        errors.append(f"maximum log_w {log_ws.max():.6g} did not reach requested {LOG_W_MAX:.6g}")
    joined = f"{stdout}\n{stderr}".lower()
    for needle in ("error", "failed", "no convergence", "abnormal"):
        if needle in joined:
            warnings.append(f"AUTO output contains diagnostic token: {needle}")
    if not any(row.type_code in (-4, 4) and abs(row.log_w - LOG_W_MAX) <= tolerance for row in rows):
        warnings.append("No UZ label was parsed at the requested upper log_w endpoint.")
    if float(all_log_ws.max()) > LOG_W_MAX + tolerance:
        warnings.append("Raw AUTO branch continued beyond requested log_w upper endpoint before stopping; normalized CSV is clipped to the requested range.")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "row_count": len(requested_rows),
        "raw_row_count": len(rows),
        "log_w_min": float(log_ws.min()),
        "log_w_max": float(log_ws.max()),
        "w_min_m_s": float(np.exp(log_ws.min())),
        "w_max_m_s": float(np.exp(log_ws.max())),
        "type_codes": type_codes,
        "raw_log_w_min": float(all_log_ws.min()),
        "raw_log_w_max": float(all_log_ws.max()),
        "labels": [row.label for row in requested_rows if row.label != 0],
    }


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def _branch_id(T: float) -> str:
    return f"figure1_T{int(T)}K"


def _source_file_for_run(run_name: str) -> str:
    return f"raw/{run_name}/b.{run_name}"


def _residual_norm(row: AutoRow, T: float) -> float:
    env = Environment(p=PRESSURE_PA, T=T, w=row.w_m_s, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    residual = equilibrium_residual([row.log_n, row.log_q, row.s], row.log_w, env, coeff=coefficients(env))
    return float(np.linalg.norm(residual, ord=2))


def _branch_records(T: float, rows: list[AutoRow], *, run_name: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    source_file = _source_file_for_run(run_name)
    for backend_step_index, row in enumerate(rows):
        records.append({
            "backend": BACKEND,
            "schema_version": SCHEMA_VERSION,
            "branch_id": _branch_id(T),
            "T_K": T,
            "temperature_K": T,
            "p_Pa": PRESSURE_PA,
            "pressure_Pa": PRESSURE_PA,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "log_w": row.log_w,
            "w_m_s": row.w_m_s,
            "log_n": row.log_n,
            "log_q": row.log_q,
            "n": row.n,
            "n_kg_dry_air_inv": row.n,
            "q": row.q,
            "q_kg_kg": row.q,
            "s": row.s,
            "residual_norm": _residual_norm(row, T),
            "converged": True,
            "stability": "",
            "backend_step_index": backend_step_index,
            "source_file": source_file,
            "auto_branch": row.branch,
            "auto_point": row.point,
            "auto_type_code": row.type_code,
            "auto_label": row.label,
            "auto_l2_norm": row.l2_norm,
        })
    return records


def _write_branch_csv(path: Path, T: float, rows: list[AutoRow], *, run_name: str) -> None:
    records = _branch_records(T, rows, run_name=run_name)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def _write_combined_branch_csv(path: Path, branch_csvs: list[Path]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_FIELDNAMES)
        writer.writeheader()
        for branch_csv in branch_csvs:
            with branch_csv.open("r", encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                for record in reader:
                    writer.writerow(record)


def _run_temperature(T: float, output_dir: Path) -> dict[str, object]:
    run_name = f"bs2026_T{int(T)}K"
    run_dir = output_dir / "raw" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    stem = run_name
    (run_dir / f"{stem}.f90").write_text(_render_problem(T), encoding="utf-8")
    shutil.copy2(REPO_ROOT / "auto" / "src" / "bs2026_constants.f90", run_dir / "bs2026_constants.f90")
    shutil.copy2(REPO_ROOT / "auto" / "src" / "bs2026_model.f90", run_dir / "bs2026_model.f90")
    (run_dir / f"c.{stem}").write_text(_render_constants(), encoding="utf-8")
    script = _auto_script(stem)
    (run_dir / f"{stem}.auto").write_text(script, encoding="utf-8")

    result = subprocess.run([str(AUTO_BIN)], input=script, cwd=run_dir, text=True, capture_output=True)
    (run_dir / "auto_stdout.txt").write_text(result.stdout, encoding="utf-8")
    (run_dir / "auto_stderr.txt").write_text(result.stderr, encoding="utf-8")
    for module_file in run_dir.glob("*.mod"):
        module_file.unlink()

    b_file = run_dir / f"b.{stem}"
    rows = _parse_b_file(b_file) if b_file.exists() else []
    requested_rows = _requested_range_rows(rows) if rows else []
    branch_csv = output_dir / f"branch_T{int(T)}K.csv"
    if requested_rows:
        _write_branch_csv(branch_csv, T, requested_rows, run_name=run_name)
    diagnostics = _diagnose(rows, result.stdout, result.stderr)
    diagnostics.update({
        "temperature_K": T,
        "run_name": run_name,
        "run_dir": str(_display_path(run_dir)),
        "command": [str(AUTO_BIN)],
        "returncode": result.returncode,
        "run_files": [
            f"raw/{run_name}/{stem}.f90",
            f"raw/{run_name}/bs2026_constants.f90",
            f"raw/{run_name}/bs2026_model.f90",
            f"raw/{run_name}/c.{stem}",
            f"raw/{run_name}/{stem}.auto",
        ],
        "raw_outputs": sorted(path.name for path in run_dir.iterdir()),
        "branch_csv": branch_csv.name if requested_rows else None,
        "branch_id": _branch_id(T),
        "schema_version": SCHEMA_VERSION,
        "normalized_schema_columns": BRANCH_FIELDNAMES,
        "input_files": [
            f"raw/{run_name}/{stem}.f90",
            f"raw/{run_name}/c.{stem}",
            f"raw/{run_name}/{stem}.auto",
        ],
        "raw_auto_output_paths": [f"raw/{run_name}/{name}" for name in sorted(path.name for path in run_dir.iterdir())],
    })
    if result.returncode != 0:
        diagnostics["ok"] = False
        diagnostics.setdefault("errors", []).append(f"AUTO exited with return code {result.returncode}")
    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--temperatures", type=float, nargs="*", default=list(TEMPERATURES_K))
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before running.")
    args = parser.parse_args()

    if not AUTO_BIN.exists():
        raise FileNotFoundError(f"AUTO-07p executable not found at {AUTO_BIN}")
    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    metadata: dict[str, object] = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "auto_problem_template": str(TEMPLATE_F90.relative_to(REPO_ROOT)),
        "auto_constants_template": str(TEMPLATE_C.relative_to(REPO_ROOT)),
        "shared_fortran_sources": ["auto/src/bs2026_constants.f90", "auto/src/bs2026_model.f90"],
        "schema_version": SCHEMA_VERSION,
        "normalized_schema_columns": BRANCH_FIELDNAMES,
        "parser_assumptions": [
            "AUTO b.* files are parsed as whitespace-delimited rows with BR, PT, TY, LAB followed by log_w, L2-NORM, log_n, log_q, and s.",
            "Rows are clipped to the requested Figure 1 log_w interval with a small endpoint tolerance.",
            "Physical w, n, and q are recovered by exponentiating log_w, log_n, and log_q.",
            "AUTO branch/type/label/point fields and L2-NORM are preserved as auto_* diagnostic columns.",
            "Residual norms are recomputed with the Python residual adapter using the shared model semantics for comparison.",
        ],
        "coordinates": {"state": ["log_n", "log_q", "s"], "continuation_parameter": "log_w"},
        "p_Pa": PRESSURE_PA,
        "F": SEDIMENTATION_F,
        "N_a_m3": AEROSOL_N_A,
        "dz_m": DZ_M,
        "w_min_m_s": W_MIN,
        "w_max_m_s": W_MAX,
        "temperatures_K": list(args.temperatures),
        "tool_versions": _tool_versions(),
        "runs": [],
    }

    all_ok = True
    branch_csvs: list[Path] = []
    for T in args.temperatures:
        diagnostics = _run_temperature(T, args.output_dir)
        metadata["runs"].append(diagnostics)
        all_ok = all_ok and bool(diagnostics.get("ok"))
        if diagnostics.get("branch_csv"):
            branch_csvs.append(args.output_dir / str(diagnostics["branch_csv"]))

    combined_csv = args.output_dir / "branches_all.csv"
    _write_combined_branch_csv(combined_csv, branch_csvs)
    metadata["combined_branch_csv"] = combined_csv.name
    metadata["normalized_branch_csvs"] = [path.name for path in branch_csvs]
    metadata["raw_auto_output_paths"] = [path for run in metadata["runs"] for path in run.get("raw_auto_output_paths", [])]

    metadata_path = args.output_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    diagnostics_path = args.output_dir / "run_diagnostics.json"
    diagnostics_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    if not all_ok:
        raise RuntimeError(f"One or more AUTO runs failed diagnostics; see {metadata_path}")
    print(f"Wrote AUTO Figure 1 continuation outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
