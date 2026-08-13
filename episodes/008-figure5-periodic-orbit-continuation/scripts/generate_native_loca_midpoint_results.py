#!/usr/bin/env python3
"""Generate independent native-LOCA Episode 008 midpoint branch artifacts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from bergner_spichtinger_2026 import (  # noqa: E402
    FixedMesh, FixedMeshOrbitFamily, FixedTemperatureRhoPath, FrozenPhaseReference,
    HopfLocusCoordinates, SpineTemperaturePath, correct_midpoint_orbit, gauss_legendre_rule,
)
from bergner_spichtinger_2026.constants import Environment  # noqa: E402
EPISODE = Path(__file__).resolve().parents[1]
FIXTURE = EPISODE / "outputs/tpetra_midpoint_fixtures/n64_converged.txt"
PYTHON_RESULTS = EPISODE / "outputs/fixed_mesh_continuation_results.json"
PYTHON_VECTORS = EPISODE / "outputs/fixed_mesh_continuation_vectors.npz"
SEED = EPISODE / "outputs/bootstrap_seed.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
RESULTS = EPISODE / "outputs/native_loca_midpoint_results.json"
VECTORS = EPISODE / "outputs/native_loca_midpoint_vectors.npz"
EXECUTABLE = Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", ROOT / "loca-build/bs2026_midpoint_orbit"))
BRANCH_IDS = (
    "fixed225-to-spine", "spine-positive-T-hat", "spine-negative-T-hat-to-210",
    "slice210-negative-rho", "slice210-positive-rho",
)
PERIOD_RTOL = 2.0e-7
ORBIT_TOL = 2.0e-7


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}


def canonical(data: object) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for key in sorted(arrays):
                member = io.BytesIO()
                np.lib.format.write_array(member, np.asarray(arrays[key], dtype="<f8"), allow_pickle=False)
                info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, member.getvalue())
        return output.getvalue()


def execute(command: str) -> list[list[str]]:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Build native executable first or set BS2026_MIDPOINT_EXECUTABLE: {EXECUTABLE}")
    completed = subprocess.run([str(EXECUTABLE), command, str(FIXTURE)], cwd=ROOT, text=True,
                               capture_output=True, check=True)
    return [line.split() for line in completed.stdout.splitlines() if line.strip()]


def contract() -> dict[str, object]:
    rows = execute("loca-smoke")
    find = lambda name: next(row for row in rows if row[0] == name)
    c, method, bootstrap, result, build_identity, fingerprint = (find("loca_contract"), find("loca_method"),
        find("bootstrap"), find("loca_result"), find("build_identity"), find("source_fingerprint"))
    expected_fingerprint = [
        sha(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp"),
        sha(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp"),
        sha(ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp"),
        sha(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp"),
        sha(ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp"),
        sha(ROOT / "loca/src/midpoint_orbit_cli.cpp"),
    ]
    if fingerprint[1:] != expected_fingerprint:
        raise RuntimeError("native executable source fingerprint does not match the current checkout")
    points = [row for row in rows if row[0] == "loca_point"]
    attempts = [row for row in rows if row[0] == "bootstrap_attempt"]
    forced_result = find("forced_rejection_result")
    forced_events = [row for row in rows if row[0] == "forced_rejection_event"]
    forced_records = [{"callback_index": int(row[1]), "status": row[2],
                       "attempted_coordinate": float(row[3]), "accepted_coordinate": float(row[4]),
                       "attempted_coordinate_delta": float(row[5]), "retry_coordinate_delta": float(row[6]),
                       "save_role": row[7]} for row in forced_events]
    rejected = [event for event in forced_records if event["status"] == "rejected"]
    if len(rejected) != 1 or not (0.0 < abs(rejected[0]["retry_coordinate_delta"]) <
                                  abs(rejected[0]["attempted_coordinate_delta"])):
        raise RuntimeError("forced native rejection did not produce one reduced-coordinate-delta retry")
    return {
        "version": c[1], "build_identity": " ".join(build_identity[1:]),
        "source_fingerprint_sha256": expected_fingerprint,
        "parameter_vector_count": int(c[2]), "parameter_dimension": int(c[3]),
        "base_dimension": int(c[4]), "extended_dimension": int(c[5]), "phase_row": int(c[6]),
        "log_period_index": int(c[7]), "continuation_method": method[1], "native_stepper": method[3] == "true",
        "base_has_arclength": method[5] == "true", "metric_version": method[7],
        "bootstrap": {"attempt_count": int(bootstrap[1]), "neighbor_coordinate": float(bootstrap[2]),
                      "tangent_coordinate_component": float(bootstrap[3]), "weighted_step": float(bootstrap[4]),
                      "attempts": [{"attempt": int(row[1]), "requested_coordinate_step": float(row[2]),
                                    "status": row[3], "weighted_step": float(row[4])} for row in attempts]},
        "smoke": {"raw_step_number": int(result[1]), "raw_failed_step_count": int(result[2]),
                  "raw_total_step_count": int(result[3]), "predictor_method": result[7], "step_size_method": result[8],
                  "points": [{"coordinate": float(row[1]), "period_s": float(row[2])} for row in points]},
        "forced_native_rejection": {"raw_step_number": int(forced_result[1]),
            "raw_failed_step_count": int(forced_result[2]), "raw_total_step_count": int(forced_result[3]),
            "saved_point_count": int(forced_result[4]), "derived_regular_attempt_count": int(forced_result[5]),
            "derived_regular_accepted_count": int(forced_result[6]), "derived_regular_rejected_count": int(forced_result[7]),
            "events": forced_records},
    }


def nearest_reference(points: list[dict[str, object]], vectors: dict[str, np.ndarray], coordinate: float) -> tuple[dict[str, object], np.ndarray]:
    point = min(points, key=lambda item: abs(float(item["active_coordinate"]) - coordinate))
    return point, vectors[str(point["vector_key"])]


def python_families(vectors: dict[str, np.ndarray]) -> dict[str, FixedMeshOrbitFamily]:
    parameters = json.loads(SEED.read_text())["canonical_parameters"]
    environment = Environment(T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
                              N_a=parameters["N_a"], Δz=parameters["Delta_z"],
                              include_evaporation=parameters["include_evaporation"])
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    mesh, rule = FixedMesh(np.array(vectors["mesh_boundaries"], copy=True)), gauss_legendre_rule(1)
    scales = np.sqrt(np.asarray(vectors["metric_diagonal_initial"][:3]) * 128.0)
    def reference(prefix: str) -> FrozenPhaseReference:
        return FrozenPhaseReference(mesh, np.array(vectors[f"phase_ref_{prefix}_values"], copy=True),
                                    np.array(vectors[f"phase_ref_{prefix}_derivatives"], copy=True),
                                    scales, rule.nodes, rule.quadrature_weights)
    fixed = FixedTemperatureRhoPath(locus, environment, 225.0)
    spine = SpineTemperaturePath(locus, environment)
    slice210 = FixedTemperatureRhoPath(locus, environment, 210.0)
    return {
        "phase-ref-episode007-seed": FixedMeshOrbitFamily(mesh, reference("episode007"), fixed, "phase-ref-episode007-seed"),
        "phase-ref-spine-225": FixedMeshOrbitFamily(mesh, reference("spine225"), spine, "phase-ref-spine-225"),
        "phase-ref-slice-210": FixedMeshOrbitFamily(mesh, reference("slice210"), slice210, "phase-ref-slice-210"),
    }


def build() -> tuple[bytes, bytes]:
    rows = execute("loca-branches")
    python = json.loads(PYTHON_RESULTS.read_text())
    python_points = {branch: [point for point in python["points"] if point["branch_id"] == branch]
                     for branch in BRANCH_IDS}
    origins = {
        "fixed225-to-spine": "episode007-n64-origin",
        "spine-positive-T-hat": "fixed225-to-spine-target-restart-phase-ref-spine-225",
        "spine-negative-T-hat-to-210": "fixed225-to-spine-target-restart-phase-ref-spine-225",
        "slice210-negative-rho": "spine-negative-T-hat-to-210-target-restart-phase-ref-slice-210",
        "slice210-positive-rho": "spine-negative-T-hat-to-210-target-restart-phase-ref-slice-210",
    }
    by_id = {str(point["point_id"]): point for point in python["points"]}
    for branch, point_id in origins.items():
        python_points[branch].append(by_id[point_id])
    with np.load(PYTHON_VECTORS, allow_pickle=False) as source:
        python_vectors = {name: np.asarray(source[name], dtype=float) for name in source.files}
    families = python_families(python_vectors)
    metrics = {
        "phase-ref-episode007-seed": python_vectors["metric_diagonal_initial"],
        "phase-ref-spine-225": python_vectors["metric_diagonal_spine"],
        "phase-ref-slice-210": python_vectors["metric_diagonal_slice210"],
    }
    arrays: dict[str, np.ndarray] = {}
    branches, points, events = [], [], []
    maximum_period_error = maximum_orbit_error = 0.0
    maximum_shared_period_error = maximum_shared_orbit_error = 0.0
    maximum_all_point_period_error = maximum_all_point_orbit_error = 0.0
    for begin in [row for row in rows if row[0] == "branch_begin"]:
        _, branch_id, reference_id, coordinate_name, origin, target = begin
        point_rows = [row for row in rows if row[0] == "branch_point" and row[1] == branch_id]
        bootstrap_rows = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == branch_id]
        event_rows = [row for row in rows if row[0] == "branch_event" and row[1] == branch_id]
        end = next(row for row in rows if row[0] == "branch_end" and row[1] == branch_id)
        for row in bootstrap_rows:
            events.append({"event_type": "native_branch_bootstrap_attempt", "backend": "LOCA fixed-parameter NOX",
                           "branch_id": branch_id, "phase_reference_id": reference_id, "attempt": int(row[2]),
                           "requested_coordinate_step": float(row[3]), "trial_coordinate": float(row[4]),
                           "accepted": row[5] == "accepted", "weighted_step_norm": float(row[6])})
        for row in event_rows:
            events.append({"event_type": "native_loca_step", "backend": "LOCA::Stepper", "branch_id": branch_id,
                           "phase_reference_id": reference_id, "callback_index": int(row[2]),
                           "accepted": row[3] == "accepted", "attempted_coordinate": float(row[4]),
                           "accepted_coordinate": float(row[5]), "attempted_coordinate_delta": float(row[6]),
                           "retry_coordinate_delta": float(row[7]), "save_role": row[8]})
        for row in point_rows:
            index, coordinate, period = int(row[2]), float(row[4]), float(row[5])
            native = np.asarray(row[6:], dtype="<f8")
            if native.size != 385:
                raise RuntimeError(f"unexpected native vector size on {branch_id}: {native.size}")
            # Independently correct every native coordinate with the Python base
            # formulation. This compares the same physical point without copying
            # or interpolating a Python branch vector into the native artifact.
            python_seed_point, python_seed_vector = nearest_reference(python_points[branch_id], python_vectors, coordinate)
            correction = correct_midpoint_orbit(families[reference_id].assembler(coordinate), python_seed_vector)
            if not correction.accepted:
                raise RuntimeError(f"Python parity correction failed at {branch_id}[{index}]")
            corrected_vector = np.asarray(correction.unknowns)
            corrected_period = float(np.exp(corrected_vector[-1]))
            point_delta = native - corrected_vector
            same_coordinate_period_error = abs(period - corrected_period) / corrected_period
            same_coordinate_orbit_error = float(np.sqrt(np.dot(metrics[reference_id][:-1], point_delta * point_delta)))
            maximum_all_point_period_error = max(maximum_all_point_period_error, same_coordinate_period_error)
            maximum_all_point_orbit_error = max(maximum_all_point_orbit_error, same_coordinate_orbit_error)
            if same_coordinate_period_error > PERIOD_RTOL or same_coordinate_orbit_error > ORBIT_TOL:
                raise RuntimeError(f"native/Python same-coordinate parity failed at {branch_id}[{index}]: "
                                   f"{same_coordinate_period_error}, {same_coordinate_orbit_error}")
            reference_point, reference_vector = nearest_reference(python_points[branch_id], python_vectors, coordinate)
            reference_period = float(reference_point["period_s"])
            period_error = abs(period - reference_period) / reference_period
            delta = native - reference_vector
            orbit_error = float(np.sqrt(np.dot(metrics[reference_id][:-1], delta * delta)))
            maximum_period_error = max(maximum_period_error, period_error)
            maximum_orbit_error = max(maximum_orbit_error, orbit_error)
            coordinate_error = abs(coordinate - float(reference_point["active_coordinate"]))
            if coordinate_error <= 1.0e-12:
                maximum_shared_period_error = max(maximum_shared_period_error, period_error)
                maximum_shared_orbit_error = max(maximum_shared_orbit_error, orbit_error)
            if coordinate_error <= 1.0e-12 and (period_error > PERIOD_RTOL or orbit_error > ORBIT_TOL):
                raise RuntimeError(f"native/Python parity failed at shared point {branch_id}[{index}]: {period_error}, {orbit_error}")
            vector_key = f"native__{branch_id}__{index:03d}"
            arrays[vector_key] = native
            points.append({"point_id": f"native-{branch_id}-{index:03d}", "branch_id": branch_id,
                           "point_index": index, "phase_reference_id": reference_id,
                           "active_coordinate": coordinate, "active_coordinate_name": coordinate_name,
                           "period_s": period, "vector_key": vector_key,
                           "python_correction_seed_point_id": python_seed_point["point_id"],
                           "python_correction_function_evaluations": correction.function_evaluations,
                           "python_correction_jacobian_evaluations": correction.jacobian_evaluations,
                           "python_correction_stage_residual_max": correction.diagnostics.stage_max,
                           "python_correction_update_residual_max": correction.diagnostics.update_max,
                           "python_correction_phase_residual_abs": correction.diagnostics.phase_abs,
                           "python_same_coordinate_period_relative_error": same_coordinate_period_error,
                           "python_same_coordinate_weighted_orbit_error": same_coordinate_orbit_error,
                           "python_nearest_point_id": reference_point["point_id"],
                           "python_nearest_coordinate_distance": coordinate_error,
                           "python_nearest_period_relative_difference": period_error,
                           "python_nearest_weighted_orbit_difference": orbit_error})
        branches.append({"branch_id": branch_id, "phase_reference_id": reference_id,
                         "active_coordinate_name": coordinate_name, "origin_coordinate": float(origin),
                         "target_coordinate": float(target), "native_point_count": len(point_rows),
                         "native_bootstrap_attempt_count": len(bootstrap_rows),
                         "raw_loca_step_number": int(end[2]), "raw_loca_failed_step_count": int(end[3]),
                         "raw_loca_total_step_count": int(end[4]),
                         "derived_initial_save_count": int(end[5]), "derived_final_save_count": int(end[6]),
                         "derived_regular_attempt_count": int(end[7]),
                         "derived_regular_accepted_count": int(end[8]),
                         "derived_regular_rejected_count": int(end[9]),
                         "derived_callback_count": len(event_rows),
                         "used_bootstrap_restart_tangent": end[10] == "true",
                         "reached_exact_target": float(point_rows[-1][4]) == float(target)})
    refreshes = [row for row in rows if row[0] == "phase_refresh"]
    for index, row in enumerate(refreshes):
        events.append({"event_type": "native_phase_reference_refresh", "restart_index": index,
                       "old_phase_reference_id": row[1], "new_phase_reference_id": row[2],
                       "parent_branch_id": row[3], "new_coordinate_name": row[4], "new_coordinate": float(row[5]),
                       "old_temperature_K": float(row[6]), "old_log_w": float(row[7]),
                       "new_temperature_K": float(row[8]), "new_log_w": float(row[9]),
                       "verification": {"backend": "fixed-parameter NOX/KLU2", "accepted": row[14] == "true",
                           "stage_residual_max": float(row[10]), "update_residual_max": float(row[11]),
                           "phase_residual_abs": float(row[12]), "linear_backend": row[13]},
                       "rebuild_lineage": ["Assembler", "ContinuationModelEvaluator", "WeightedThyraGroup", "LOCA::Stepper"]})
    if [branch["branch_id"] for branch in branches] != list(BRANCH_IDS):
        raise RuntimeError("native output did not contain the required branch order")
    native_digests = {hashlib.sha256(value.tobytes()).hexdigest() for value in arrays.values()}
    python_point_digests = {hashlib.sha256(value.tobytes()).hexdigest() for key, value in python_vectors.items()
                            if key.startswith("point__")}
    overlap = native_digests & python_point_digests
    if overlap:
        raise RuntimeError(f"native artifact contains copied frozen Python point vectors: {sorted(overlap)}")
    payload = {
        "schema_version": "episode8-native-loca-midpoint-v2",
        "artifact_kind": "independently_executed_native_loca_midpoint_branches",
        "native_contract": contract(),
        "branch_execution_contract": {"backend": "LOCA::Stepper", "continuation_method": "Arc Length",
            "predictor": "Secant with first-step Restart vector from separately corrected signed two-point bootstrap",
            "step_size": {"method": "Adaptive", "minimum": 1e-8, "maximum": 0.04, "aggressiveness": 0.5},
            "rejection_retry_owner": "LOCA::Stepper",
            "phase_reference_rebuild_policy": "immutable reference within segment; two recorded controlled full-stack rebuilds"},
        "branches": branches, "points": points, "events": events,
        "controlled_phase_reference_refresh_count": len(refreshes), "required_branch_ids": list(BRANCH_IDS),
        "parity": {"version": "native-python-all-point-parity-v1", "reference_backend": "independent Python fixed-parameter correction at every native coordinate",
                   "status": "measured_at_every_native_accepted_point; nearest transparent-branch diagnostics also retained",
                   "period_relative_tolerance": PERIOD_RTOL, "weighted_orbit_tolerance": ORBIT_TOL,
                   "maximum_all_point_period_relative_error": maximum_all_point_period_error,
                   "maximum_all_point_weighted_orbit_error": maximum_all_point_orbit_error,
                   "maximum_shared_point_period_relative_error": maximum_shared_period_error,
                   "maximum_shared_point_weighted_orbit_error": maximum_shared_orbit_error,
                   "maximum_nearest_point_period_relative_difference": maximum_period_error,
                   "maximum_nearest_point_weighted_orbit_difference": maximum_orbit_error,
                   "reference_branch_manifest_sha256": sha(PYTHON_RESULTS)},
        "scope": "N=64 midpoint native-LOCA machinery/parity milestone; not production Figure 5 accuracy",
        "source_provenance": {
            "generator": source_record(Path(__file__).resolve()),
            "cpp_adapter": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp"),
            "cpp_cli": source_record(ROOT / "loca/src/midpoint_orbit_cli.cpp"),
            "cpp_assembler": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp"),
            "cpp_model": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp"),
            "cpp_nox_adapter": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp"),
            "cpp_collocation_coefficients": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp"),
            "python_continuation": source_record(ROOT / "src/bergner_spichtinger_2026/periodic_continuation.py"),
            "python_orbit_solver": source_record(ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"),
            "seed": source_record(SEED), "hopf_locus": source_record(HOPF_LOCI),
            "uv_lock": source_record(ROOT / "uv.lock"), "fixture": source_record(FIXTURE),
            "python_vectors": source_record(PYTHON_VECTORS),
            "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "trilinos_build_identity": contract()["build_identity"],
                        "emitting_executable_source_fingerprint_sha256": contract()["source_fingerprint_sha256"]}},
    }
    vector_bytes = npz_bytes(arrays)
    payload["vector_artifact"] = {"path": str(VECTORS.relative_to(ROOT)), "sha256": hashlib.sha256(vector_bytes).hexdigest(),
                                  "array_count": len(arrays), "origin": "stdout vectors emitted by native C++ LOCA recorder",
                                  "digest_disjoint_from_all_frozen_python_points": True}
    return canonical(payload), vector_bytes


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    result_bytes, vector_bytes = build()
    if args.check:
        if RESULTS.read_bytes() != result_bytes or VECTORS.read_bytes() != vector_bytes:
            raise SystemExit("native LOCA midpoint artifacts are stale")
    else:
        RESULTS.write_bytes(result_bytes); VECTORS.write_bytes(vector_bytes)


if __name__ == "__main__":
    main()
