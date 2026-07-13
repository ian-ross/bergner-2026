#!/usr/bin/env python3
"""Run AUTO-07p Figure 2 equilibrium continuation and post-process eigenvalues.

This episode-local workflow uses AUTO to independently continue equilibria of
Bergner & Spichtinger (2026) at p=300 hPa, T=230 K, F=1, N_a=1e10 m^-3 over
w=0.0005--2.0 m s^-1.  AUTO solves the log-coordinate equilibrium residual.
The production eigenvalues are then computed from those AUTO equilibria with the
shared Python analytic physical ODE Jacobian so their semantics match Figure 2.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import exp, log
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from importlib.metadata import PackageNotFoundError, version

try:
    package_version = version("bergner-spichtinger-2026")
except PackageNotFoundError:  # pragma: no cover - editable/local fallback
    package_version = "unknown"

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high
from bergner_spichtinger_2026.core import coefficients, equilibrium, vector_field
from bergner_spichtinger_2026.residuals import equilibrium_residual, log_coordinates_from_physical_state
from bergner_spichtinger_2026.stability import classify_eigenvalues, detect_hopf_crossings, physical_eigenvalues

REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = REPO_ROOT / "episodes" / "005-figure2-eigenvalues"
AUTO_DIR = EPISODE_DIR / "auto"
DEFAULT_OUTPUT_DIR = EPISODE_DIR / "outputs" / "figure2_auto_eigenvalues"
TEMPLATE_F90 = AUTO_DIR / "bs2026_figure2_template.f90"
TEMPLATE_C = AUTO_DIR / "c.bs2026_figure2"

BACKEND = "auto"
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
EXPECTED_HOPF_W_M_S = (0.048, 0.77)
HOPF_LANDMARK_TOLERANCE_M_S = 0.01
DEFAULT_REAL_TOL = 1e-10
DEFAULT_IMAG_TOL = 1e-10
SCHEMA_VERSION = "figure2-auto-eigenvalue-schema-v1"
AUTO_BIN = Path("/usr/local/bin/auto")
EIGENVALUE_SOURCE = "python_analytic_postprocessed_from_auto_equilibria"

LONG_EIGENVALUE_FIELDNAMES = [
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
    "eigenvalue_sorting",
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
        "@LOG_W_MIN@": _format_fortran_float(LOG_W_MIN),
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


def _auto_script(stem: str) -> str:
    return "\n".join([f"ld('{stem}')", f"run(c='{stem}')", f"sv('{stem}')", "cl()", ""])


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
    return [row for row in rows if LOG_W_MIN - tolerance <= row.log_w <= LOG_W_MAX + tolerance]


def _residuals(row: AutoRow) -> tuple[float, float, float]:
    env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=row.w_m_s, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
    coeff = coefficients(env)
    continuation = equilibrium_residual([row.log_n, row.log_q, row.s], row.log_w, env, coeff=coeff)
    physical = vector_field(row.n, row.q, row.s, env, coeff)
    physical_state = np.array([row.n, row.q, row.s], dtype=float)
    return (
        float(np.linalg.norm(continuation, ord=2)),
        float(np.linalg.norm(physical, ord=2)),
        float(np.linalg.norm(physical / np.maximum(np.abs(physical_state), 1.0), ord=2)),
    )


def _eigenvalue_records(rows: list[AutoRow], *, run_name: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    source_file = f"raw/{run_name}/b.{run_name}"
    for point_index, row in enumerate(rows):
        env = Environment(p=PRESSURE_PA, T=TEMPERATURE_K, w=row.w_m_s, F=SEDIMENTATION_F, N_a=AEROSOL_N_A, Δz=DZ_M)
        coeff = coefficients(env)
        continuation_residual_norm, physical_residual_norm, scaled_physical_residual_norm = _residuals(row)
        eigvals = physical_eigenvalues([row.n, row.q, row.s], env=env, coeff=coeff, imag_tol=DEFAULT_IMAG_TOL)
        classification = classify_eigenvalues(eigvals, real_tol=DEFAULT_REAL_TOL, imag_tol=DEFAULT_IMAG_TOL)
        for eigen_index, eigenvalue in enumerate(eigvals, start=1):
            records.append(
                {
                    "backend": BACKEND,
                    "schema_version": SCHEMA_VERSION,
                    "branch_id": BRANCH_ID,
                    "point_index": point_index,
                    "T_K": TEMPERATURE_K,
                    "p_Pa": PRESSURE_PA,
                    "F": SEDIMENTATION_F,
                    "N_a_m3": AEROSOL_N_A,
                    "N_a_cm3": AEROSOL_N_A / 1.0e6,
                    "log_w": row.log_w,
                    "w_m_s": row.w_m_s,
                    "log_n": row.log_n,
                    "log_q": row.log_q,
                    "n": row.n,
                    "q": row.q,
                    "s": row.s,
                    "continuation_residual_norm": continuation_residual_norm,
                    "physical_residual_norm": physical_residual_norm,
                    "scaled_physical_residual_norm": scaled_physical_residual_norm,
                    "converged": True,
                    "iterations": pd.NA,
                    "message": "AUTO equilibrium point parsed from b.*; residual diagnostics recomputed in Python.",
                    "eigen_index": eigen_index,
                    "eigenvalue_real": float(eigenvalue.real),
                    "eigenvalue_imag": float(eigenvalue.imag),
                    "eigenvalue_regime": classification.regime,
                    "stability_classification": classification.stability,
                    "jacobian_coordinate_system": "physical_ode_state",
                    "jacobian_method": "analytic_sympy_transcribed_physical_ode_jacobian",
                    "eigenvalue_source": EIGENVALUE_SOURCE,
                    "eigenvalue_sorting": "canonical_complex_pair_pos_imag_neg_imag_real_else_descending_real",
                    "source_file": source_file,
                    "auto_branch": row.branch,
                    "auto_point": row.point,
                    "auto_type_code": row.type_code,
                    "auto_label": row.label,
                    "auto_l2_norm": row.l2_norm,
                }
            )
    return pd.DataFrame(records, columns=LONG_EIGENVALUE_FIELDNAMES)


def track_eigenvalue_branches(canonical_spectra: np.ndarray) -> np.ndarray:
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
    index_cols = [
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
        "eigenvalue_regime",
        "stability_classification",
        "jacobian_coordinate_system",
        "jacobian_method",
        "eigenvalue_source",
        "source_file",
        "auto_branch",
        "auto_point",
        "auto_type_code",
        "auto_label",
        "auto_l2_norm",
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
    spectra = [
        np.array(
            [
                complex(row.lambda1_real, row.lambda1_imag),
                complex(row.lambda2_real, row.lambda2_imag),
                complex(row.lambda3_real, row.lambda3_imag),
            ],
            dtype=complex,
        )
        for _, row in point_rows.iterrows()
    ]
    crossings = detect_hopf_crossings(point_rows["log_w"].to_numpy(), spectra, real_tol=0.0, imag_tol=imag_tol)
    crossing_frame = pd.DataFrame([asdict(crossing) for crossing in crossings])
    comparison_rows: list[dict[str, Any]] = []
    if not crossing_frame.empty:
        crossing_ws = crossing_frame["w"].to_numpy(dtype=float)
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
    return crossing_frame, pd.DataFrame(comparison_rows)


def _diagnose(rows: list[AutoRow], stdout: str, stderr: str) -> dict[str, object]:
    if not rows:
        return {"ok": False, "errors": ["AUTO branch file contained no parseable branch rows."], "warnings": []}
    all_log_ws = np.array([row.log_w for row in rows], dtype=float)
    requested_rows = _requested_range_rows(rows)
    if not requested_rows:
        return {"ok": False, "errors": ["AUTO branch file had no rows in the requested Figure 2 log_w range."], "warnings": []}
    log_ws = np.array([row.log_w for row in requested_rows], dtype=float)
    tolerance = 5.0e-4
    errors: list[str] = []
    warnings: list[str] = []
    if float(log_ws.min()) > LOG_W_MIN + tolerance:
        errors.append(f"minimum log_w {log_ws.min():.6g} did not reach requested {LOG_W_MIN:.6g}")
    if float(log_ws.max()) < LOG_W_MAX - tolerance:
        errors.append(f"maximum log_w {log_ws.max():.6g} did not reach requested {LOG_W_MAX:.6g}")
    if len(requested_rows) < 200:
        warnings.append(f"AUTO branch has only {len(requested_rows)} requested-range rows; Figure 2 comparison benefits from >=200 points.")
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
        "raw_log_w_min": float(all_log_ws.min()),
        "raw_log_w_max": float(all_log_ws.max()),
        "labels": [row.label for row in requested_rows if row.label != 0],
        "type_codes": sorted({row.type_code for row in requested_rows if row.type_code != 0}),
    }


def _run_auto(output_dir: Path) -> dict[str, object]:
    run_name = "bs2026_figure2_T230K"
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

    b_file = run_dir / f"b.{stem}"
    rows = _parse_b_file(b_file) if b_file.exists() else []
    requested_rows = _requested_range_rows(rows) if rows else []
    diagnostics = _diagnose(rows, result.stdout, result.stderr)
    diagnostics.update(
        {
            "run_name": run_name,
            "run_dir": _relative_path(run_dir),
            "command": [str(AUTO_BIN)],
            "returncode": result.returncode,
            "raw_outputs": sorted(path.name for path in run_dir.iterdir()),
            "input_files": [f"raw/{run_name}/{stem}.f90", f"raw/{run_name}/c.{stem}", f"raw/{run_name}/{stem}.auto"],
            "raw_auto_output_paths": [f"raw/{run_name}/{name}" for name in sorted(path.name for path in run_dir.iterdir())],
            "branch_id": BRANCH_ID,
            "schema_version": SCHEMA_VERSION,
        }
    )
    if result.returncode != 0:
        diagnostics["ok"] = False
        diagnostics.setdefault("errors", []).append(f"AUTO exited with return code {result.returncode}")
    diagnostics["_requested_rows"] = requested_rows
    return diagnostics


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before running.")
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(effective_argv)
    invocation = " ".join([sys.executable, _relative_path(Path(__file__)), *effective_argv])

    if not AUTO_BIN.exists():
        raise FileNotFoundError(f"AUTO-07p executable not found at {AUTO_BIN}")
    if args.clean and args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    run = _run_auto(args.output_dir)
    rows = run.pop("_requested_rows")
    if not run.get("ok"):
        metadata_path = args.output_dir / "run_metadata.json"
        metadata_path.write_text(json.dumps({"runs": [run]}, indent=2), encoding="utf-8")
        raise RuntimeError(f"AUTO Figure 2 run failed diagnostics; see {metadata_path}")

    eigenvalue_rows = _eigenvalue_records(rows, run_name=str(run["run_name"]))
    point_rows = make_point_table(eigenvalue_rows)
    crossing_frame, crossing_comparison = estimate_hopf_crossings(point_rows, DEFAULT_IMAG_TOL)

    eigenvalue_csv = args.output_dir / "auto_figure2_eigenvalues.csv"
    point_csv = args.output_dir / "auto_figure2_branch_points.csv"
    crossing_csv = args.output_dir / "auto_figure2_hopf_crossings.csv"
    crossing_comparison_csv = args.output_dir / "auto_figure2_hopf_landmark_comparison.csv"
    summary_json = args.output_dir / "auto_figure2_summary.json"
    metadata_json = args.output_dir / "run_metadata.json"

    eigenvalue_rows.to_csv(eigenvalue_csv, index=False)
    point_rows.to_csv(point_csv, index=False)
    crossing_frame.to_csv(crossing_csv, index=False)
    crossing_comparison.to_csv(crossing_comparison_csv, index=False)

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
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "p_Pa": PRESSURE_PA,
            "p_hPa": PRESSURE_PA / 100.0,
            "T_K": TEMPERATURE_K,
            "F": SEDIMENTATION_F,
            "N_a_m3": AEROSOL_N_A,
            "N_a_cm3": AEROSOL_N_A / 1.0e6,
            "w_min_m_s": W_MIN,
            "w_max_m_s": W_MAX,
        },
        "auto": {
            "problem_template": _relative_path(TEMPLATE_F90),
            "constants_template": _relative_path(TEMPLATE_C),
            "shared_fortran_sources": ["auto/src/bs2026_constants.f90", "auto/src/bs2026_model.f90"],
            "state_coordinates": "log(n), log(q), s",
            "continuation_parameter": "log_w = natural log(w_m_s)",
            "b_file_parser": "whitespace-delimited AUTO rows with BR, PT, TY, LAB followed by log_w, L2-NORM, log_n, log_q, and s",
            "native_eigenvalue_investigation": [
                "AUTO-07p IPS=1 equilibrium continuation exposes branch labels and bifurcation/stability diagnostics in b./s./d. outputs, but this setup does not directly emit the desired physical ODE Jacobian spectrum d(dn/dt,dq/dt,ds/dt)/d(n,q,s) as normalized numeric columns.",
                "AUTO bifurcation detection would operate on the continuation problem in log-state coordinates and solver scaling; Figure 2 needs physical-coordinate ODE eigenvalues comparable to the Python reproduction.",
                "Adding a Fortran/LAPACK physical eigensolver to the AUTO problem would duplicate the already verified shared Python analytic Jacobian and add toolchain complexity, so production uses labeled Python post-processing of independently generated AUTO equilibria.",
            ],
        },
        "jacobian": {
            "matrix": "d(dn/dt,dq/dt,ds/dt)/d(n,q,s) in physical ODE state coordinates",
            "method": "analytic SymPy-derived formula implemented by bergner_spichtinger_2026.stability.physical_jacobian",
            "evaporation": "disabled; discontinuous evaporation term is not included in the physical Jacobian",
        },
        "eigenvalues": {
            "source": EIGENVALUE_SOURCE,
            "source_clarification": "Eigenvalues are not AUTO-native; they are Python analytic physical-Jacobian eigenvalues post-processed from AUTO equilibrium states parsed from b.*.",
            "sorting_tolerance_imag": DEFAULT_IMAG_TOL,
            "stability_real_tolerance": DEFAULT_REAL_TOL,
            "sorting_convention": "complex pair as positive-imaginary, negative-imaginary, remaining real eigenvalue; otherwise descending real part",
            "plot_branch_tracking": "tracked_lambda*_real/imag columns use adjacent minimum-distance matching in the complex plane",
            "hopf_estimator": "linear interpolation of Re(complex-pair eigenvalues) in log_w",
            "paper_landmark_w_m_s": list(EXPECTED_HOPF_W_M_S),
            "paper_landmark_documented_tolerance_m_s": HOPF_LANDMARK_TOLERANCE_M_S,
        },
        "runs": [run],
        "normalized_schema_columns": LONG_EIGENVALUE_FIELDNAMES,
        "outputs": [_relative_path(path) for path in [eigenvalue_csv, point_csv, crossing_csv, crossing_comparison_csv, summary_json, metadata_json]],
        "commands": {"invocation": invocation, "recommended": "uv run python episodes/005-figure2-eigenvalues/scripts/run_auto_figure2_eigenvalues.py"},
        "software": {"python": platform.python_version(), "platform": platform.platform(), "package_version": package_version, "numpy": np.__version__, "pandas": pd.__version__, "tool_versions": _tool_versions()},
    }
    metadata_json.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output_dir / "run_diagnostics.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote AUTO Figure 2 eigenvalue outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
