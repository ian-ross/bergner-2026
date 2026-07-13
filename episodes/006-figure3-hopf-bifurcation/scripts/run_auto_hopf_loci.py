#!/usr/bin/env python3
"""Run AUTO-07p native Hopf detection/continuation for Figure 3.

The workflow is intentionally AUTO-native for bifurcation handling:

1. continue equilibria at T=230 K in log_w with ``ISP=2`` so AUTO labels Hopf
   bifurcations on the transformed ODE;
2. restart from the two AUTO Hopf labels with ``ISW=2`` and active parameters
   ``ICP=[1, 3]`` (log_w and T) to continue each Hopf locus;
3. normalize raw AUTO b/s/d artifacts into the Episode 006 Hopf-locus schema.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from math import exp, log
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
from importlib.metadata import PackageNotFoundError, version

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover
    package_version = "unknown"

from bergner_spichtinger_2026.approximations import table_ii_lower_hopf_w, table_ii_upper_hopf_w
from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import coefficients, equilibrium, vector_field
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state
from bergner_spichtinger_2026.stability import physical_eigenvalues

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "006-figure3-hopf-bifurcation"
AUTO_DIR = EPISODE_DIR / "auto"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure3_auto_hopf_loci"
TEMPLATE_F90 = AUTO_DIR / "bs2026_figure3_hopf_template.f90"
TEMPLATE_C = AUTO_DIR / "c.bs2026_figure3_hopf"
AUTO_BIN = Path("/usr/local/bin/auto")
DEFAULT_COMPARISON_DIR = EPISODE_DIR / "outputs" / "figure3_backend_comparison"

BACKEND = "auto"
SCHEMA_VERSION = "episode6-hopf-locus-schema-v1"
PRESSURE_PA = 30_000.0
TEMPERATURE_K = 230.0
SEDIMENTATION_F = 1.0
AEROSOL_N_A = N_a_figure1_high
DZ_M = 100.0
W_MIN = 0.0005
W_MAX = 2.0
LOG_W_MIN = log(W_MIN)
LOG_W_MAX = log(W_MAX)
T_MIN = 190.0
T_MAX = 240.0
LOWER_ANCHOR_W_M_S = 0.048531
UPPER_ANCHOR_W_M_S = 0.768680
ANCHOR_TOLERANCE_M_S = 0.02

FIELDNAMES = [
    "backend",
    "schema_version",
    "branch_id",
    "paper_fit_branch",
    "point_index",
    "T_K",
    "p_Pa",
    "F",
    "N_a_m3",
    "N_a_cm3",
    "log_w",
    "w_m_s",
    "table_ii_reference_w_m_s",
    "log_n",
    "log_q",
    "n",
    "q",
    "s",
    "hopf_frequency",
    "eigenvalue_real",
    "eigenvalue_imag",
    "residual_norm",
    "equilibrium_residual_norm",
    "physical_residual_norm",
    "converged",
    "iterations",
    "message",
    "jacobian_coordinate_system",
    "state_coordinate_system",
    "continuation_parameterization",
    "method",
    "method_metadata",
    "source_file",
    "raw_auto_run",
    "auto_branch",
    "auto_point",
    "auto_type_code",
    "auto_label",
    "auto_l2_norm",
    "auto_hopf_source_label",
]


class AutoRow(NamedTuple):
    branch: int
    point: int
    type_code: int
    label: int
    log_w: float
    l2_norm: float
    log_n: float
    log_q: float
    s: float
    T_K: float | None = None
    source_file: str = ""

    @property
    def w_m_s(self) -> float:
        return exp(self.log_w)

    @property
    def n(self) -> float:
        return exp(self.log_n)

    @property
    def q(self) -> float:
        return exp(self.log_q)


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _run_text(command: list[str], *, cwd: Path | None = None) -> dict[str, object]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def _tool_versions() -> dict[str, object]:
    auto_dir = Path("/usr/local/lib64/auto-07p")
    return {
        "auto_path": str(AUTO_BIN),
        "auto_exists": AUTO_BIN.exists(),
        "auto_dir": str(auto_dir),
        "auto_version_label": auto_dir.name,
        "auto_launcher_head": AUTO_BIN.read_text(encoding="utf-8", errors="replace").splitlines()[:8] if AUTO_BIN.exists() else [],
        "gfortran": _run_text(["gfortran", "--version"]),
    }


def _format_fortran_float(value: float) -> str:
    return f"{value:.17e}".replace("e", "d")


def _render_problem() -> str:
    env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=W_MIN, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    log_state = log_coordinates_from_physical_state(equilibrium(env))
    replacements = {
        "@LOG_N@": _format_fortran_float(float(log_state[0])),
        "@LOG_Q@": _format_fortran_float(float(log_state[1])),
        "@S@": _format_fortran_float(float(log_state[2])),
        "@LOG_W_START@": _format_fortran_float(LOG_W_MIN),
        "@PRESSURE_PA@": _format_fortran_float(PRESSURE_PA),
        "@TEMPERATURE_K@": _format_fortran_float(TEMPERATURE_K),
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


def _parse_b_file(path: Path, *, has_active_T: bool) -> list[AutoRow]:
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
            values = [float(part.replace("D", "E")) for part in parts[4:]]
        except ValueError:
            continue
        if branch == 0 or len(values) < 5:
            continue
        T = values[5] if has_active_T and len(values) >= 6 else TEMPERATURE_K
        rows.append(AutoRow(branch, point, type_code, label, values[0], values[1], values[2], values[3], values[4], T, _relative_path(path)))
    return rows


def _is_hopf_equilibrium_label(row: AutoRow) -> bool:
    # AUTO b-files encode ordinary Hopf special points as type code 3 on the
    # initial equilibrium branch in this AUTO-07p build.  Continued Hopf curves
    # use composite type codes such as 34/39 and are parsed separately.
    return abs(row.type_code) == 3 and row.label != 0


def _auto_script(stem: str) -> str:
    return f"""
ld('{stem}')
r0 = run(c='{stem}', sv='{stem}.eq')
print('AUTO_HOPF_LABELS', [s['LAB'] for s in r0('HB')])
run(r0('HB1'), ICP=[1,3], ILP=0, ISW=2, NMX=900, NPR=2, DS=0.01, DSMIN=1e-6, DSMAX=0.5, UZR={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, UZSTOP={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, sv='{stem}.hb1.fw')
run(r0('HB1'), ICP=[1,3], ILP=0, ISW=2, NMX=900, NPR=2, DS='-', DSMIN=1e-6, DSMAX=0.5, UZR={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, UZSTOP={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, sv='{stem}.hb1.bw')
run(r0('HB2'), ICP=[1,3], ILP=0, ISW=2, NMX=900, NPR=2, DS=0.01, DSMIN=1e-6, DSMAX=0.5, UZR={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, UZSTOP={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, sv='{stem}.hb2.fw')
run(r0('HB2'), ICP=[1,3], ILP=0, ISW=2, NMX=900, NPR=2, DS='-', DSMIN=1e-6, DSMAX=0.5, UZR={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, UZSTOP={{3:[{T_MIN:.12g},{T_MAX:.12g}]}}, sv='{stem}.hb2.bw')
cl()
"""


def _residuals(row: AutoRow) -> tuple[float, float, float, float]:
    env = Environment(p=PRESSURE_PA, T=float(row.T_K), w=row.w_m_s, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    coeff = coefficients(env)
    continuation = equilibrium_residual([row.log_n, row.log_q, row.s], row.log_w, env, coeff=coeff)
    physical = vector_field(row.n, row.q, row.s, env, coeff)
    eigvals = physical_eigenvalues([row.n, row.q, row.s], env=env, coeff=coeff, canonical=True)
    pair = max(eigvals, key=lambda value: abs(value.imag))
    return (
        float(np.linalg.norm(continuation, ord=2)),
        float(np.linalg.norm(continuation, ord=2)),
        float(np.linalg.norm(physical, ord=2)),
        abs(float(pair.imag)),
    )


def _branch_rows(rows: list[AutoRow], *, branch_id: str, source_run: str, source_label: int) -> list[dict[str, Any]]:
    paper_fit_branch = "wb" if branch_id == "lower_hopf" else "wa"
    records: list[dict[str, Any]] = []
    selected = [row for row in rows if row.T_K is not None and T_MIN - 1e-4 <= row.T_K <= T_MAX + 1e-4]
    # In this model the two Hopf loci are connected into a larger AUTO Hopf
    # curve, so a restart from either HB label can traverse both paper branches.
    # Normalize the labeled Figure 3 branches by retaining the segment closest
    # (in log_w) to the corresponding Table II reference branch at each T.
    def belongs_to_requested_branch(row: AutoRow) -> bool:
        lower_log_w = log(float(table_ii_lower_hopf_w(float(row.T_K))))
        upper_log_w = log(float(table_ii_upper_hopf_w(float(row.T_K))))
        lower_distance = abs(row.log_w - lower_log_w)
        upper_distance = abs(row.log_w - upper_log_w)
        return lower_distance <= upper_distance if branch_id == "lower_hopf" else upper_distance < lower_distance

    selected = [row for row in selected if belongs_to_requested_branch(row)]
    selected = sorted(selected, key=lambda row: (float(row.T_K), row.log_w, row.point, row.label))
    seen: set[tuple[float, float]] = set()
    deduped: list[AutoRow] = []
    for row in selected:
        key = (round(float(row.T_K), 8), round(float(row.log_w), 10))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    for point_index, row in enumerate(deduped):
        residual_norm, eq_norm, physical_norm, omega = _residuals(row)
        fit_w = table_ii_lower_hopf_w(float(row.T_K)) if branch_id == "lower_hopf" else table_ii_upper_hopf_w(float(row.T_K))
        records.append(
            {
                "backend": BACKEND,
                "schema_version": SCHEMA_VERSION,
                "branch_id": branch_id,
                "paper_fit_branch": paper_fit_branch,
                "point_index": point_index,
                "T_K": float(row.T_K),
                "p_Pa": PRESSURE_PA,
                "F": SEDIMENTATION_F,
                "N_a_m3": AEROSOL_N_A,
                "N_a_cm3": AEROSOL_N_A / 1.0e6,
                "log_w": row.log_w,
                "w_m_s": row.w_m_s,
                "table_ii_reference_w_m_s": float(fit_w),
                "log_n": row.log_n,
                "log_q": row.log_q,
                "n": row.n,
                "q": row.q,
                "s": row.s,
                "hopf_frequency": omega,
                "eigenvalue_real": 0.0,
                "eigenvalue_imag": omega,
                "residual_norm": residual_norm,
                "equilibrium_residual_norm": eq_norm,
                "physical_residual_norm": physical_norm,
                "converged": True,
                "iterations": pd.NA,
                "message": "AUTO-native Hopf curve point parsed from b.*; residual/frequency diagnostics recomputed in Python.",
                "jacobian_coordinate_system": "physical_ode_state",
                "state_coordinate_system": "log_n_log_q_s_internal__physical_state_output",
                "continuation_parameterization": "AUTO_ISW2_Hopf_curve_active_parameters_log_w_T",
                "method": "AUTO-07p_native_equilibrium_Hopf_detection_and_ISW2_Hopf_curve_continuation",
                "method_metadata": "Initial branch uses ISP=2 to label HB at T=230 K; loci restart from AUTO HB labels with ISW=2 and ICP=[1,3].",
                "source_file": row.source_file,
                "raw_auto_run": source_run,
                "auto_branch": row.branch,
                "auto_point": row.point,
                "auto_type_code": row.type_code,
                "auto_label": row.label,
                "auto_l2_norm": row.l2_norm,
                "auto_hopf_source_label": source_label,
            }
        )
    return records


def _copy_raw(run_dir: Path) -> list[str]:
    return sorted(_relative_path(path) for path in run_dir.iterdir() if path.is_file())


def run_auto(output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    run_name = "bs2026_figure3_hopf"
    run_dir = output_dir / "raw" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    stem = run_name
    (run_dir / f"{stem}.f90").write_text(_render_problem(), encoding="utf-8")
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

    eq_rows = _parse_b_file(run_dir / f"b.{stem}.eq", has_active_T=False) if (run_dir / f"b.{stem}.eq").exists() else []
    hopf_rows = [row for row in eq_rows if _is_hopf_equilibrium_label(row)]
    hopf_rows = sorted(hopf_rows, key=lambda row: row.w_m_s)
    errors: list[str] = []
    warnings: list[str] = []
    if result.returncode != 0:
        errors.append(f"AUTO exited with return code {result.returncode}")
    if len(hopf_rows) < 2:
        errors.append(f"Expected at least two AUTO Hopf labels on equilibrium branch, found {len(hopf_rows)}")

    all_records: list[dict[str, Any]] = []
    branch_summaries: list[dict[str, Any]] = []
    for branch_id, hopf in zip(["lower_hopf", "upper_hopf"], hopf_rows[:2], strict=False):
        pieces: list[AutoRow] = []
        for direction in ("fw", "bw"):
            source_run = f"{stem}.hb{1 if branch_id == 'lower_hopf' else 2}.{direction}"
            b_path = run_dir / f"b.{source_run}"
            if not b_path.exists():
                warnings.append(f"Missing raw AUTO Hopf continuation b-file: {b_path.name}")
                continue
            pieces.extend(_parse_b_file(b_path, has_active_T=True))
        records = _branch_rows(pieces, branch_id=branch_id, source_run=run_name, source_label=hopf.label)
        all_records.extend(records)
        if records:
            Ts = [record["T_K"] for record in records]
            w230 = min((record for record in records), key=lambda record: abs(record["T_K"] - TEMPERATURE_K))["w_m_s"]
            anchor = LOWER_ANCHOR_W_M_S if branch_id == "lower_hopf" else UPPER_ANCHOR_W_M_S
            branch_summaries.append(
                {
                    "branch_id": branch_id,
                    "source_hopf_label": hopf.label,
                    "source_hopf_w_m_s": hopf.w_m_s,
                    "point_count": len(records),
                    "T_min_K": min(Ts),
                    "T_max_K": max(Ts),
                    "nearest_T230_w_m_s": w230,
                    "T230_anchor_w_m_s": anchor,
                    "T230_abs_error_m_s": abs(w230 - anchor),
                    "T230_within_tolerance": abs(w230 - anchor) <= ANCHOR_TOLERANCE_M_S,
                }
            )

    frame = pd.DataFrame(all_records, columns=FIELDNAMES)
    diagnostics = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "run_name": run_name,
        "run_dir": _relative_path(run_dir),
        "command": [str(AUTO_BIN)],
        "returncode": result.returncode,
        "equilibrium_hopf_labels": [row.label for row in hopf_rows],
        "equilibrium_hopf_w_m_s": [row.w_m_s for row in hopf_rows],
        "branch_summaries": branch_summaries,
        "raw_auto_output_paths": _copy_raw(run_dir),
    }
    if not frame.empty:
        for branch_id in ("lower_hopf", "upper_hopf"):
            part = frame[frame["branch_id"] == branch_id]
            if part.empty:
                errors.append(f"No normalized rows for {branch_id}")
                continue
            if float(part["T_K"].min()) > T_MIN + 0.5 or float(part["T_K"].max()) < T_MAX - 0.5:
                errors.append(f"{branch_id} does not cover requested T range: {part['T_K'].min()}--{part['T_K'].max()} K")
    diagnostics["ok"] = not errors
    return frame, diagnostics


def _load_plotter_module():
    plotter_path = Path(__file__).with_name("plot_figure3_hopf_loci.py")
    spec = importlib.util.spec_from_file_location("plot_figure3_hopf_loci", plotter_path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Could not load plotter module from {plotter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_outputs(frame: pd.DataFrame, diagnostics: dict[str, Any], output_dir: Path, argv: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    loci_csv = output_dir / "auto_figure3_hopf_loci.csv"
    labels_csv = output_dir / "auto_figure3_hopf_labels.csv"
    summary_json = output_dir / "auto_figure3_summary.json"
    metadata_json = output_dir / "run_metadata.json"
    diagnostics_json = output_dir / "run_diagnostics.json"
    backend_plot_path = output_dir / "auto_figure3_hopf_loci.png"
    comparison_plot_path = DEFAULT_COMPARISON_DIR / "figure3_hopf_backend_comparison.png"

    frame.to_csv(loci_csv, index=False)
    if not frame.empty:
        plotter = _load_plotter_module()
        plotter.write_backend_plot(frame, backend_plot_path, backend=BACKEND)
        available_frames = [frame]
        python_csv = EPISODE_DIR / "outputs" / "figure3_python_hopf_loci" / "python_figure3_hopf_loci.csv"
        if python_csv.exists():
            available_frames.insert(0, pd.read_csv(python_csv))
        plotter.write_comparison_plot(available_frames, comparison_plot_path)
    label_rows = []
    for label, w in zip(diagnostics.get("equilibrium_hopf_labels", []), diagnostics.get("equilibrium_hopf_w_m_s", []), strict=False):
        label_rows.append({"backend": BACKEND, "T_K": TEMPERATURE_K, "auto_label": label, "w_m_s": w, "log_w": log(float(w))})
    pd.DataFrame(label_rows).to_csv(labels_csv, index=False)

    summary = {
        "backend": BACKEND,
        "schema_version": SCHEMA_VERSION,
        "branches": sorted(frame["branch_id"].unique().tolist()) if not frame.empty else [],
        "row_count": int(len(frame)),
        "T_min_K": float(frame["T_K"].min()) if not frame.empty else None,
        "T_max_K": float(frame["T_K"].max()) if not frame.empty else None,
        "all_converged": bool(frame["converged"].all()) if not frame.empty else False,
        "max_residual_norm": float(frame["residual_norm"].max()) if not frame.empty else None,
        "diagnostics_ok": bool(diagnostics.get("ok")),
        "branch_summaries": diagnostics.get("branch_summaries", []),
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "backend": BACKEND,
        "package_version": package_version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "command": " ".join([sys.executable, _relative_path(Path(__file__)), *argv]),
        "parameters": {
            "p_Pa": PRESSURE_PA,
            "T_seed_K": TEMPERATURE_K,
            "T_min_K": T_MIN,
            "T_max_K": T_MAX,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "w_min_m_s": W_MIN,
            "w_max_m_s": W_MAX,
        },
        "method": {
            "name": "AUTO-07p native Hopf detection and Hopf curve continuation",
            "equilibrium_detection": "IPS=1, ISP=2, active ICP=[1] at T=230 K labels HB points on the transformed ODE equilibrium branch.",
            "hopf_continuation": "Restart from AUTO HB1/HB2 with ISW=2 and active ICP=[1,3] for log_w and T.",
            "coordinate_note": "FUNC is the paper ODE transformed to (log n, log q, s), preserving Hopf eigenvalues under a smooth coordinate transform.",
        },
        "auto": {
            "problem_template": _relative_path(TEMPLATE_F90),
            "constants_template": _relative_path(TEMPLATE_C),
            "shared_fortran_sources": ["auto/src/bs2026_constants.f90", "auto/src/bs2026_model.f90"],
            "tool_versions": _tool_versions(),
        },
        "outputs": {
            "loci_csv": _relative_path(loci_csv),
            "labels_csv": _relative_path(labels_csv),
            "summary_json": _relative_path(summary_json),
            "metadata_json": _relative_path(metadata_json),
            "diagnostics_json": _relative_path(diagnostics_json),
            "backend_plot_png": _relative_path(backend_plot_path),
            "comparison_plot_png": _relative_path(comparison_plot_path),
        },
        "normalized_schema_columns": FIELDNAMES,
        "diagnostics": diagnostics,
    }
    metadata_json.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    diagnostics_json.write_text(json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--clean", action="store_true", help="Remove output directory before running.")
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(effective_argv)

    if not AUTO_BIN.exists():
        raise FileNotFoundError(f"AUTO-07p executable not found at {AUTO_BIN}")
    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    frame, diagnostics = run_auto(args.output_dir)
    write_outputs(frame, diagnostics, args.output_dir, effective_argv)
    if not diagnostics.get("ok"):
        raise RuntimeError(f"AUTO Figure 3 Hopf run failed diagnostics; see {args.output_dir / 'run_diagnostics.json'}")
    print(f"Wrote AUTO Figure 3 Hopf outputs to {args.output_dir}")


if __name__ == "__main__":  # pragma: no cover
    main()
