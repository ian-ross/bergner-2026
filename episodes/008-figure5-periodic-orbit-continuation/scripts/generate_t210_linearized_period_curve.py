#!/usr/bin/env python3
"""Generate the TASK-074 T=210 K equilibrium-linearized period curve.

This artifact is independent from Episode 008 periodic-orbit continuation.  It
uses the native C++ equilibrium corrector/eigenvalue CLI to continue the
positive equilibrium over the saved Figure 5 vertical-velocity domain and then
computes the physical-Jacobian linearized period
``P_lin = 2*pi/abs(Im(lambda_pair))`` where a genuine complex pair is present.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.interpolate import PchipInterpolator

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026.constants import Environment, N_a_figure1_high  # noqa: E402
from bergner_spichtinger_2026.core import equilibrium  # noqa: E402
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    PARAMETER_COORDINATE_CONVENTION,
    ORBIT_STATE_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)
from bergner_spichtinger_2026.stability import physical_jacobian  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
ARTIFACT = OUTPUT / "t210_linearized_period_curve.json"
GENERATOR = Path(__file__).resolve()
DECISIONS_DOC = EPISODE / "docs/collocation-phase-decisions.md"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
README = EPISODE / "README.md"
EPISODE006_LOCA_HOPF = (
    ROOT
    / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
)
MODEL_SOURCE = ROOT / "loca/src/model_cli.cpp"
MODEL_HEADER = ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp"
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_loca_model"

METHOD_VERSION = "cpp-nox-loca-equilibrium-physical-jacobian-linearized-period-v1"
EIGENPAIR_TRACKING_VERSION = "continuation-distance-plus-eigenvector-overlap-v1"
HOLDOUT_REFINEMENT_VERSION = "pchip-log-period-holdout-2e-3-v1"
PYTHON_PARITY_VERSION = "physical-jacobian-stratified-parity-rtol-1e-8-v1"

T_K = 210.0
P_PA = 30_000.0
F_VALUE = 1.0
N_A = float(N_a_figure1_high)
W_MIN = 5.0e-4
W_MAX = 2.0
INITIAL_GRID_POINTS = 401
FREQUENCY_FLOOR = 1.0e-8
HOLDOUT_TOLERANCE = 2.0e-3
PYTHON_PARITY_RTOL = 1.0e-8
PYTHON_PARITY_ATOL = 1.0e-12
MAX_REFINEMENT_ITERATIONS = 8


@dataclass(frozen=True)
class NativeRow:
    log_w: float
    w: float
    log_n: float
    log_q: float
    s: float
    residual_norm: float
    converged: bool
    newton_iterations: int
    continuation_status: str
    eigenvalues: tuple[complex, complex, complex]
    eigenvalue_regime: str
    stability_classification: str
    physical_jacobian: np.ndarray
    sample_source: str
    anchor_branch_id: str | None = None


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def executable_path() -> Path:
    return Path(os.environ.get("BS2026_MODEL_EXECUTABLE", DEFAULT_EXECUTABLE)).resolve()


def parse_bool(text: str) -> bool:
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"not a C++ bool token: {text!r}")


def parse_native_csv(stdout: str, *, sample_source: str, anchor_branch_id: str | None = None) -> list[NativeRow]:
    rows = list(csv.DictReader(stdout.splitlines()))
    parsed: list[NativeRow] = []
    for row in rows:
        jac_values = [float(row[f"physical_jacobian_{i}{j}"]) for i in range(1, 4) for j in range(1, 4)]
        parsed.append(
            NativeRow(
                log_w=float(row["log_w"]),
                w=math.exp(float(row["log_w"])),
                log_n=float(row["log_n"]),
                log_q=float(row["log_q"]),
                s=float(row["s"]),
                residual_norm=float(row["residual_norm"]),
                converged=parse_bool(row["converged"]),
                newton_iterations=int(row["newton_iterations"]),
                continuation_status=row["continuation_status"],
                eigenvalues=(
                    complex(float(row["lambda1_real"]), float(row["lambda1_imag"])),
                    complex(float(row["lambda2_real"]), float(row["lambda2_imag"])),
                    complex(float(row["lambda3_real"]), float(row["lambda3_imag"])),
                ),
                eigenvalue_regime=row["eigenvalue_regime"],
                stability_classification=row["stability_classification"],
                physical_jacobian=np.asarray(jac_values, dtype=float).reshape((3, 3)),
                sample_source=sample_source,
                anchor_branch_id=anchor_branch_id,
            )
        )
    return parsed


def run_native_continuation(
    executable: Path,
    x0: Sequence[float],
    log_w_start: float,
    log_w_end: float,
    steps: int,
    *,
    sample_source: str,
    anchor_branch_id: str | None = None,
) -> list[NativeRow]:
    command = [
        str(executable),
        "nox-loca-continue",
        *(f"{float(value):.17g}" for value in x0),
        f"{log_w_start:.17g}",
        "--log-w-end",
        f"{log_w_end:.17g}",
        "--steps",
        str(steps),
        "--T",
        f"{T_K:.17g}",
        "--p",
        f"{P_PA:.17g}",
        "--F",
        f"{F_VALUE:.17g}",
        "--N-a",
        f"{N_A:.17g}",
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"native C++ equilibrium continuation failed with exit code {completed.returncode}: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    rows = parse_native_csv(completed.stdout, sample_source=sample_source, anchor_branch_id=anchor_branch_id)
    if not rows:
        raise RuntimeError("native C++ continuation emitted no rows")
    return rows


def load_hopf_anchors() -> list[dict[str, Any]]:
    with EPISODE006_LOCA_HOPF.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if math.isclose(float(row["T_K"]), T_K, abs_tol=1.0e-12)]
    anchors: list[dict[str, Any]] = []
    for row in rows:
        anchors.append(
            {
                "branch_id": row["branch_id"],
                "log_w": float(row["log_w"]),
                "w": float(row["w_m_s"]),
                # This is the physical-Jacobian Hopf frequency recorded by Episode 006.
                "physical_jacobian_frequency": abs(float(row["eigenvalue_imag"])),
                # Retained for transparency: the Moore-Spence extended-group omega is a transformed-coordinate value.
                "moore_spence_frequency": abs(float(row["hopf_frequency"])),
                "source_row": int(row["point_index"]),
            }
        )
    if {anchor["branch_id"] for anchor in anchors} != {"lower_hopf", "upper_hopf"}:
        raise RuntimeError(f"expected exact lower/upper Episode 006 T=210 K anchors, got {anchors}")
    return sorted(anchors, key=lambda item: item["log_w"])


def initial_native_rows(executable: Path) -> dict[float, NativeRow]:
    env = Environment(p=P_PA, T=T_K, w=W_MIN, F=F_VALUE, N_a=N_A)
    y0 = equilibrium(env, bracket=(1.000001, 3.0))
    x0 = (math.log(float(y0[0])), math.log(float(y0[1])), float(y0[2]))
    rows = run_native_continuation(
        executable,
        x0,
        math.log(W_MIN),
        math.log(W_MAX),
        INITIAL_GRID_POINTS - 1,
        sample_source="initial_401_log_spaced_grid",
    )
    mapping = {round(row.log_w, 15): row for row in rows}
    if len(mapping) != INITIAL_GRID_POINTS:
        raise RuntimeError(f"expected {INITIAL_GRID_POINTS} unique native initial-grid rows, got {len(mapping)}")
    return mapping


def insert_native_sample(
    samples: dict[float, NativeRow],
    executable: Path,
    target_log_w: float,
    *,
    sample_source: str,
    anchor_branch_id: str | None = None,
) -> None:
    key = round(target_log_w, 15)
    if key in samples:
        existing = samples[key]
        if sample_source == "episode006_exact_hopf_anchor":
            samples[key] = NativeRow(**{**existing.__dict__, "sample_source": sample_source, "anchor_branch_id": anchor_branch_id})
        return
    nearest = min(samples.values(), key=lambda row: abs(row.log_w - target_log_w))
    rows = run_native_continuation(
        executable,
        (nearest.log_n, nearest.log_q, nearest.s),
        nearest.log_w,
        target_log_w,
        1,
        sample_source=sample_source,
        anchor_branch_id=anchor_branch_id,
    )
    candidate = rows[-1]
    if abs(candidate.log_w - target_log_w) > 5.0e-13:
        raise RuntimeError(f"native C++ endpoint drift: requested {target_log_w}, got {candidate.log_w}")
    samples[key] = candidate


def complex_pair_from_native(row: NativeRow) -> tuple[complex | None, str | None]:
    if not row.converged:
        return None, "native_equilibrium_not_converged"
    candidates = [value for value in row.eigenvalues if value.imag > 0.0]
    if not candidates:
        return None, "real_pair"
    pair = max(candidates, key=lambda value: value.imag)
    if abs(pair.imag) <= FREQUENCY_FLOOR:
        return None, "frequency_below_floor"
    return pair, None


def eigensystem_from_native_jacobian(row: NativeRow) -> tuple[np.ndarray, np.ndarray]:
    vals, vecs = np.linalg.eig(row.physical_jacobian)
    return vals, vecs


def track_rows(rows: Sequence[NativeRow], anchors: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lower, upper = anchors[0]["log_w"], anchors[1]["log_w"]
    previous_pair: complex | None = None
    previous_vector: np.ndarray | None = None
    records: list[dict[str, Any]] = []
    anchor_checks: list[dict[str, Any]] = []
    anchor_by_branch = {str(anchor["branch_id"]): anchor for anchor in anchors}

    for index, row in enumerate(rows):
        pair, invalid_reason = complex_pair_from_native(row)
        vals, vecs = eigensystem_from_native_jacobian(row)
        positive = [i for i, value in enumerate(vals) if value.imag > FREQUENCY_FLOOR]
        tracked_vector: np.ndarray | None = None
        tracked_pair_from_jacobian: complex | None = None
        eigenvector_overlap = None
        continuation_distance = None
        if positive:
            if previous_pair is None:
                chosen = max(positive, key=lambda i: vals[i].imag)
            else:
                chosen = min(positive, key=lambda i: abs(vals[i] - previous_pair))
                continuation_distance = float(abs(vals[chosen] - previous_pair))
            tracked_pair_from_jacobian = complex(vals[chosen])
            vector = vecs[:, chosen] / np.linalg.norm(vecs[:, chosen])
            if previous_vector is not None:
                eigenvector_overlap = float(abs(np.vdot(previous_vector, vector)))
            tracked_vector = vector
        if pair is not None:
            # Preserve the C++/Teuchos eigenvalue as the authoritative frequency, while
            # using the native physical-Jacobian matrix to document continuity.
            previous_pair = pair
            previous_vector = tracked_vector

        period_value = None if pair is None else float(2.0 * math.pi / abs(pair.imag))
        log_period = None if period_value is None else float(math.log(period_value))
        rho = float((2.0 * row.log_w - lower - upper) / (upper - lower))
        status = "accepted" if pair is not None else "gap"
        source = "computed_linearized_equilibrium" if pair is not None else "explicit_gap"
        authoritative = pair is not None
        validity: dict[str, Any] = {"status": status, "source": source, "authoritative": authoritative}
        if invalid_reason is not None:
            validity["reason"] = invalid_reason
        method_versions = {
            "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "linearized_period_method": METHOD_VERSION,
            "eigenpair_tracking": EIGENPAIR_TRACKING_VERSION,
            "holdout_refinement": HOLDOUT_REFINEMENT_VERSION,
        }
        record: dict[str, Any] = {
            "record_id": f"t210-linearized-{index:06d}",
            "coordinates": {
                "convention": PARAMETER_COORDINATE_CONVENTION,
                "temperature": {"value": T_K, "unit": "K"},
                "log_w": {"value": row.log_w, "unit": "ln(m s^-1)"},
                "w": {"value": row.w, "unit": "m s^-1"},
                "rho": {"value": rho, "unit": "dimensionless"},
                "temperature_hat": {"value": (T_K - 215.0) / 25.0, "unit": "dimensionless"},
            },
            "validity": validity,
            "method_versions": method_versions,
            "period": {"quantity": "linearized_period", "value": period_value, "unit": "s", "log_value": log_period},
            "eigenvalue_imaginary_part": {
                "value": None if pair is None else float(abs(pair.imag)),
                "unit": "rad s^-1",
            },
            "eigenvalues": [
                {"real": float(value.real), "imag": float(value.imag), "unit": "s^-1"} for value in row.eigenvalues
            ],
            "equilibrium_state": {
                "coordinate_system": "log_n_log_q_s_internal_and_physical_state_output",
                "log_n": row.log_n,
                "log_q": row.log_q,
                "s": row.s,
                "n": float(math.exp(row.log_n)),
                "q": float(math.exp(row.log_q)),
            },
            "native_cpp_diagnostics": {
                "residual_norm": row.residual_norm,
                "converged": row.converged,
                "newton_iterations": row.newton_iterations,
                "continuation_status": row.continuation_status,
                "eigenvalue_regime": row.eigenvalue_regime,
                "stability_classification": row.stability_classification,
                "jacobian_coordinate_system": "physical_ode_state",
                "physical_jacobian": row.physical_jacobian.tolist(),
            },
            "eigenpair_continuity": {
                "tracking_version": EIGENPAIR_TRACKING_VERSION,
                "tracked_positive_imaginary_eigenvalue": None
                if tracked_pair_from_jacobian is None
                else {"real": float(tracked_pair_from_jacobian.real), "imag": float(tracked_pair_from_jacobian.imag)},
                "continuation_distance_from_previous": continuation_distance,
                "eigenvector_overlap_from_previous": eigenvector_overlap,
                "ambiguity_resolved_by_overlap": bool(eigenvector_overlap is not None and eigenvector_overlap < 0.95),
            },
            "sampling": {
                "sample_source": row.sample_source,
                "anchor_branch_id": row.anchor_branch_id,
                "invalid_or_gap_reason": invalid_reason,
                "period_clipped_to_plot_range": False,
            },
        }
        records.append(record)
        if row.anchor_branch_id is not None:
            anchor = anchor_by_branch[row.anchor_branch_id]
            relative_error = abs(float(record["eigenvalue_imaginary_part"]["value"]) - anchor["physical_jacobian_frequency"]) / anchor[
                "physical_jacobian_frequency"
            ]
            anchor_checks.append(
                {
                    "branch_id": row.anchor_branch_id,
                    "record_id": record["record_id"],
                    "log_w": row.log_w,
                    "w": row.w,
                    "episode006_physical_jacobian_frequency": anchor["physical_jacobian_frequency"],
                    "episode006_moore_spence_frequency_retained_not_gated": anchor["moore_spence_frequency"],
                    "native_frequency": record["eigenvalue_imaginary_part"]["value"],
                    "relative_error": relative_error,
                    "passed": relative_error <= PYTHON_PARITY_RTOL,
                }
            )
    return records, anchor_checks


def contiguous_valid_runs(records: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    runs: list[list[int]] = []
    current: list[int] = []
    for index, record in enumerate(records):
        value = record["period"]["log_value"]
        valid = record["validity"]["status"] == "accepted" and value is not None and math.isfinite(float(value))
        if valid:
            current.append(index)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


def holdout_report(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    run_reports: list[dict[str, Any]] = []
    worst: dict[str, Any] | None = None
    for run_index, run in enumerate(contiguous_valid_runs(records)):
        if len(run) < 5:
            run_reports.append({"run_index": run_index, "status": "not_enough_points", "point_count": len(run)})
            continue
        x = np.asarray([records[i]["coordinates"]["log_w"]["value"] for i in run], dtype=float)
        y = np.asarray([records[i]["period"]["log_value"] for i in run], dtype=float)
        holdout_local = [i for i in range(1, len(run) - 1) if i % 2 == 1]
        keep = np.ones(len(run), dtype=bool)
        keep[holdout_local] = False
        if int(np.count_nonzero(keep)) < 3:
            run_reports.append({"run_index": run_index, "status": "not_enough_kept_points", "point_count": len(run)})
            continue
        interpolator = PchipInterpolator(x[keep], y[keep], extrapolate=False)
        predicted = interpolator(x[holdout_local])
        errors = np.abs(predicted - y[holdout_local])
        max_position = int(np.argmax(errors))
        local_index = holdout_local[max_position]
        report = {
            "run_index": run_index,
            "status": "passed" if float(errors[max_position]) <= HOLDOUT_TOLERANCE else "failed",
            "point_count": len(run),
            "withheld_count": len(holdout_local),
            "max_abs_log_period_error": float(errors[max_position]),
            "worst_record_index": run[local_index],
            "worst_log_w": float(x[local_index]),
            "left_log_w": float(x[local_index - 1]),
            "right_log_w": float(x[local_index + 1]),
        }
        run_reports.append(report)
        if worst is None or report["max_abs_log_period_error"] > worst["max_abs_log_period_error"]:
            worst = report
    max_error = 0.0 if worst is None else float(worst["max_abs_log_period_error"])
    return {
        "version": HOLDOUT_REFINEMENT_VERSION,
        "tolerance": HOLDOUT_TOLERANCE,
        "status": "passed" if max_error <= HOLDOUT_TOLERANCE else "failed",
        "max_abs_log_period_error": max_error,
        "worst": worst,
        "runs": run_reports,
    }


def refine_samples(samples: dict[float, NativeRow], executable: Path, anchors: Sequence[Mapping[str, Any]]) -> tuple[list[NativeRow], list[dict[str, Any]], dict[str, Any]]:
    refinement_events: list[dict[str, Any]] = []
    for iteration in range(MAX_REFINEMENT_ITERATIONS + 1):
        native_rows = sorted(samples.values(), key=lambda row: row.log_w)
        records, _ = track_rows(native_rows, anchors)
        report = holdout_report(records)
        if report["status"] == "passed":
            report["iterations"] = iteration
            return native_rows, refinement_events, report
        if iteration == MAX_REFINEMENT_ITERATIONS:
            raise RuntimeError(f"holdout refinement did not converge: {report}")
        worst = report["worst"]
        if not isinstance(worst, Mapping):
            raise RuntimeError(f"holdout failed without a worst point: {report}")
        candidates = [
            0.5 * (float(worst["left_log_w"]) + float(worst["worst_log_w"])),
            0.5 * (float(worst["worst_log_w"]) + float(worst["right_log_w"])),
        ]
        added: list[float] = []
        for candidate in candidates:
            key = round(candidate, 15)
            if key not in samples:
                insert_native_sample(samples, executable, candidate, sample_source="holdout_refinement")
                added.append(candidate)
        refinement_events.append(
            {
                "iteration": iteration + 1,
                "trigger_error": worst["max_abs_log_period_error"],
                "trigger_log_w": worst["worst_log_w"],
                "inserted_log_w": added,
            }
        )
        if not added:
            raise RuntimeError(f"holdout requested only existing samples: {report}")
    raise AssertionError("unreachable")


def stratified_indices(count: int, anchor_indices: Iterable[int]) -> list[int]:
    base = {0, count - 1, count // 4, count // 2, (3 * count) // 4, *anchor_indices}
    # Add log-spaced-ish coverage over record indices without depending on period shape.
    for fraction in np.linspace(0.05, 0.95, 9):
        base.add(int(round(fraction * (count - 1))))
    return sorted(i for i in base if 0 <= i < count)


def python_parity(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    anchor_indices = [i for i, record in enumerate(records) if record["sampling"]["anchor_branch_id"] is not None]
    indices = stratified_indices(len(records), anchor_indices)
    sample_reports: list[dict[str, Any]] = []
    max_jacobian_error = 0.0
    max_eigen_imag_relative_error = 0.0
    max_period_relative_error = 0.0
    for index in indices:
        record = records[index]
        state = record["equilibrium_state"]
        env = Environment(
            p=P_PA,
            T=T_K,
            w=float(record["coordinates"]["w"]["value"]),
            F=F_VALUE,
            N_a=N_A,
        )
        py_jac = physical_jacobian([state["n"], state["q"], state["s"]], env=env)
        native_jac = np.asarray(record["native_cpp_diagnostics"]["physical_jacobian"], dtype=float)
        jac_abs = float(np.max(np.abs(py_jac - native_jac)))
        jac_rel = float(np.max(np.abs(py_jac - native_jac) / np.maximum(np.abs(py_jac), PYTHON_PARITY_ATOL)))
        py_vals = np.linalg.eigvals(py_jac)
        py_pair_imag = max((abs(float(value.imag)) for value in py_vals), default=0.0)
        native_imag = record["eigenvalue_imaginary_part"]["value"]
        eig_rel = 0.0
        period_rel = 0.0
        if native_imag is not None and py_pair_imag > 0.0:
            eig_rel = abs(float(native_imag) - py_pair_imag) / py_pair_imag
            py_period = 2.0 * math.pi / py_pair_imag
            period_rel = abs(float(record["period"]["value"]) - py_period) / py_period
        max_jacobian_error = max(max_jacobian_error, jac_rel)
        max_eigen_imag_relative_error = max(max_eigen_imag_relative_error, eig_rel)
        max_period_relative_error = max(max_period_relative_error, period_rel)
        sample_reports.append(
            {
                "record_id": record["record_id"],
                "index": index,
                "log_w": record["coordinates"]["log_w"]["value"],
                "jacobian_max_abs_error": jac_abs,
                "jacobian_max_relative_error": jac_rel,
                "eigen_imag_relative_error": eig_rel,
                "period_relative_error": period_rel,
                "passed": jac_rel <= PYTHON_PARITY_RTOL and eig_rel <= PYTHON_PARITY_RTOL and period_rel <= PYTHON_PARITY_RTOL,
            }
        )
    return {
        "version": PYTHON_PARITY_VERSION,
        "rtol": PYTHON_PARITY_RTOL,
        "atol": PYTHON_PARITY_ATOL,
        "sample_count": len(indices),
        "max_jacobian_relative_error": max_jacobian_error,
        "max_eigen_imag_relative_error": max_eigen_imag_relative_error,
        "max_period_relative_error": max_period_relative_error,
        "passed": all(report["passed"] for report in sample_reports),
        "samples": sample_reports,
    }


def build_artifact(executable: Path) -> dict[str, Any]:
    if not executable.is_file():
        raise FileNotFoundError(
            f"C++ model executable not found: {executable}. Build with `cmake -S loca -B loca-build -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build loca-build --parallel 2`, or set BS2026_MODEL_EXECUTABLE."
        )
    anchors = load_hopf_anchors()
    samples = initial_native_rows(executable)
    for anchor in anchors:
        insert_native_sample(
            samples,
            executable,
            float(anchor["log_w"]),
            sample_source="episode006_exact_hopf_anchor",
            anchor_branch_id=str(anchor["branch_id"]),
        )
    native_rows, refinement_events, holdout = refine_samples(samples, executable, anchors)
    records, anchor_checks = track_rows(native_rows, anchors)
    parity = python_parity(records)
    if not all(check["passed"] for check in anchor_checks):
        raise RuntimeError(f"Episode 006 Hopf-frequency anchor checks failed: {anchor_checks}")
    if not parity["passed"]:
        raise RuntimeError(f"Python physical-Jacobian parity failed: {parity}")
    accepted = [record for record in records if record["validity"]["status"] == "accepted"]
    gaps = [record for record in records if record["validity"]["status"] != "accepted"]
    periods = [float(record["period"]["value"]) for record in accepted]
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "linearized-period-curve",
        "artifact_id": "task074-t210-linearized-period-curve",
        "method_versions": {
            "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "linearized_period_method": METHOD_VERSION,
            "eigenpair_tracking": EIGENPAIR_TRACKING_VERSION,
            "holdout_refinement": HOLDOUT_REFINEMENT_VERSION,
            "python_parity": PYTHON_PARITY_VERSION,
        },
        "coordinate_conventions": {
            "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
            "orbit_state": ORBIT_STATE_CONVENTION,
            "phase": PHASE_COORDINATE_CONVENTION,
            "period": PERIOD_CONVENTION,
        },
        "provenance": {
            "task": "TASK-074",
            "created_by": "generate_t210_linearized_period_curve.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(EPISODE006_LOCA_HOPF, "exact Episode 006 native LOCA T=210 K Hopf anchors"),
                source_record(DECISIONS_DOC, "documented exact T=210 K linearized-period contract"),
                source_record(TASK069_DOC, "TASK-069 downstream authorization for T=210 K linearized periods"),
                source_record(TASK070_DOC, "TASK-070 production schema boundary"),
                source_record(MODEL_SOURCE, "native C++ equilibrium/eigenvalue CLI source"),
                source_record(MODEL_HEADER, "native C++ model derivative implementation"),
                source_record(GENERATOR, "TASK-074 deterministic generator"),
            ],
        },
        "linearized_period_rows": records,
        "summary": {
            "temperature_K": T_K,
            "w_domain_m_s": [W_MIN, W_MAX],
            "log_w_domain": [math.log(W_MIN), math.log(W_MAX)],
            "initial_grid_points": INITIAL_GRID_POINTS,
            "total_rows": len(records),
            "accepted_rows": len(accepted),
            "gap_or_invalid_rows": len(gaps),
            "frequency_floor_rad_s": FREQUENCY_FLOOR,
            "period_min_s": min(periods) if periods else None,
            "period_max_s": max(periods) if periods else None,
            "period_clipping_policy": "never_clip_or_invent_finite_periods",
            "native_backend": "C++ bs2026_loca_model nox-loca-continue with physical-Jacobian Teuchos/LAPACK eigenvalues",
            "executable_identity": {"path": str(executable.relative_to(ROOT)) if executable.is_relative_to(ROOT) else str(executable), "sha256": sha(executable)},
            "exact_hopf_anchors": anchors,
        },
        "sampling_refinement": {
            "holdout": holdout,
            "refinement_events": refinement_events,
        },
        "validation": {
            "episode006_hopf_frequency_checks": {
                "frequency_column": "eigenvalue_imag from Episode 006 native LOCA physical-Jacobian rows",
                "rtol": PYTHON_PARITY_RTOL,
                "passed": all(check["passed"] for check in anchor_checks),
                "checks": anchor_checks,
            },
            "python_physical_jacobian_parity": parity,
            "no_period_clipping_or_finite_gap_fabrication": all(
                (record["period"]["value"] is None) == (record["validity"]["status"] != "accepted")
                and record["sampling"]["period_clipped_to_plot_range"] is False
                for record in records
            ),
        },
    }
    validate_production_artifact(artifact, root=ROOT)
    return artifact


def write_or_check(artifact: Mapping[str, Any], path: Path, *, check: bool) -> None:
    payload = canonical_json_bytes(artifact)
    if check:
        if not path.is_file():
            raise FileNotFoundError(f"artifact missing: {path}")
        current = path.read_bytes()
        if current != payload:
            with tempfile.NamedTemporaryFile(prefix="task074-t210-linearized-period-", suffix=".json", delete=False) as handle:
                handle.write(payload)
                temp_name = handle.name
            raise RuntimeError(f"{path} is stale; regenerated bytes written to {temp_name}")
        print(f"{rel(path)} is current")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        print(f"wrote {rel(path)}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify that the committed artifact is byte-for-byte current")
    parser.add_argument("--output", type=Path, default=ARTIFACT, help="output artifact path")
    parser.add_argument("--executable", type=Path, default=None, help="path to bs2026_loca_model")
    args = parser.parse_args(argv)
    executable = (args.executable or executable_path()).resolve()
    artifact = build_artifact(executable)
    write_or_check(artifact, args.output.resolve(), check=args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
