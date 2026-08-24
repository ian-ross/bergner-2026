#!/usr/bin/env python3
"""Run the TASK-068.01 native adaptive one-branch segment slice.

This is the first integrated native adaptive slice, not the full TASK-068
spine-and-slices run.  It executes the native three-stage fixed-mesh LOCA branch
that lands on the T=210 K spine, chooses only its accepted final point as the
remesh boundary, applies the TASK-067 adaptive-controller seam on the matching
nonuniform guard fixture, transfers solution/phase-reference/tangent data,
rebuilds the sparse Tpetra/Thyra/NOX/KLU2 stack through the native restart seam,
and records deterministic resumable artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import sha256_file  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
CPP_HIGHER_FIXTURES = OUTPUT / "cpp_higher_order_fixtures"
CPP_ADAPTIVE_FIXTURES = OUTPUT / "cpp_adaptive_nonuniform_fixtures"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
RESTART_SMOKE = OUTPUT / "native_adaptive_restart_smoke.json"
RESULTS = OUTPUT / "native_adaptive_one_branch_segment.json"
VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
GENERATOR = Path(__file__).resolve()
EXECUTABLE = Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", ROOT / "loca-build/bs2026_midpoint_orbit"))

SCHEMA_VERSION = "episode008-native-adaptive-one-branch-segment-v1"
VECTOR_ARTIFACT_KIND = "task06801-native-adaptive-one-branch-vectors"
SELECTED_BRANCH_ID = "spine-negative-T-hat-to-210"
SELECTED_PHASE_REFERENCE_ID = "phase-ref-spine-225"
SELECTED_ADAPTIVE_CASE_ID = "adaptive-guard-rho-0-g3-n32"
FIXED_MESH_FIXTURE = CPP_HIGHER_FIXTURES / "canonical-g3-n32.txt"
ADAPTIVE_FIXTURE = CPP_ADAPTIVE_FIXTURES / f"{SELECTED_ADAPTIVE_CASE_ID}.txt"

SOURCE_PATHS = (
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
    ROOT / "loca/src/midpoint_orbit_cli.cpp",
)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def array_sha(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


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


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def execute(command: str, fixture_path: Path) -> list[list[str]]:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Build C++ executable first or set BS2026_MIDPOINT_EXECUTABLE: {EXECUTABLE}")
    completed = subprocess.run(
        [str(EXECUTABLE), command, str(fixture_path)], cwd=ROOT,
        text=True, capture_output=True, check=True,
    )
    return [line.split() for line in completed.stdout.splitlines() if line.strip()]


def as_bool(value: str) -> bool:
    if value not in {"true", "false"}:
        raise RuntimeError(f"invalid boolean field: {value}")
    return value == "true"


def vector_from_row(row: list[str], *, offset: int = 1, width: int = 1) -> np.ndarray:
    count = int(row[offset])
    data = np.asarray(row[offset + 1:], dtype="<f8")
    expected = count * width
    if data.shape != (expected,):
        raise RuntimeError(f"row {row[0]} declared {count}x{width} values but emitted {data.size}")
    return data


def first_row(rows: list[list[str]], name: str) -> list[str]:
    for row in rows:
        if row[0] == name:
            return row
    raise RuntimeError(f"missing row {name}")


def expected_fingerprints() -> list[str]:
    return [sha256_file(path) for path in SOURCE_PATHS]


def parse_native_branch(rows: list[list[str]], arrays: dict[str, np.ndarray]) -> tuple[dict[str, Any], list[str], list[str]]:
    contract = first_row(rows, "loca_contract")
    build_identity = first_row(rows, "build_identity")[1:]
    source_fingerprint = first_row(rows, "source_fingerprint")[1:]
    if source_fingerprint != expected_fingerprints():
        raise RuntimeError("stale native executable source fingerprint for one-branch run")

    begin = next(row for row in rows if row[0] == "branch_begin" and row[1] == SELECTED_BRANCH_ID)
    bootstrap_rows = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == SELECTED_BRANCH_ID]
    restart = next(row for row in rows if row[0] == "branch_restart" and row[1] == SELECTED_BRANCH_ID)
    event_rows = [row for row in rows if row[0] == "branch_event" and row[1] == SELECTED_BRANCH_ID]
    validation_rows = [row for row in rows if row[0] == "branch_validation" and row[1] == SELECTED_BRANCH_ID]
    point_rows = [row for row in rows if row[0] == "branch_point" and row[1] == SELECTED_BRANCH_ID]
    end = next(row for row in rows if row[0] == "branch_end" and row[1] == SELECTED_BRANCH_ID)
    if len(point_rows) != len(validation_rows):
        raise RuntimeError("native one-branch point/validation mismatch")
    if begin[2] != SELECTED_PHASE_REFERENCE_ID or begin[3] != "temperature_hat":
        raise RuntimeError("selected branch does not use the expected spine phase reference/path")

    events: list[dict[str, Any]] = []
    for row in event_rows:
        events.append({
            "callback_index": int(row[2]),
            "status": row[3],
            "accepted": row[3] == "accepted",
            "attempted_coordinate": float(row[4]),
            "accepted_coordinate": float(row[5]),
            "attempted_coordinate_delta": float(row[6]),
            "retry_coordinate_delta": float(row[7]),
            "save_role": row[8],
            "remesh_boundary_candidate": row[8] == "final" and row[3] == "accepted",
        })
    if [event["callback_index"] for event in events] != list(range(len(events))):
        raise RuntimeError("native one-branch callback indices are not contiguous")
    if any(event["save_role"] != "final" and event["remesh_boundary_candidate"] for event in events):
        raise RuntimeError("remesh boundary was not restricted to the final accepted point")
    remesh_events = [event for event in events if event["remesh_boundary_candidate"]]
    if len(remesh_events) != 1:
        raise RuntimeError("native one-branch requires exactly one accepted remesh boundary")
    if any(event["status"] == "rejected" and event["remesh_boundary_candidate"] for event in events):
        raise RuntimeError("rejected event was treated as a remesh boundary")

    points: list[dict[str, Any]] = []
    for point, validation in zip(point_rows, validation_rows, strict=True):
        point_index = int(point[2])
        vector = np.asarray(point[6:], dtype="<f8")
        vector_key = f"native_fixed_mesh__{SELECTED_BRANCH_ID}__point_{point_index:03d}"
        arrays[vector_key] = vector
        native_validation = {
            "stage_residual_max": float(validation[3]),
            "stage_residual_rms": float(validation[4]),
            "update_residual_max": float(validation[5]),
            "update_residual_rms": float(validation[6]),
            "phase_residual_abs": float(validation[7]),
            "physical_states_positive_finite": as_bool(validation[8]),
            "period_positive_finite": as_bool(validation[9]),
            "linear_backend": validation[10],
            "linear_solve_complete": as_bool(validation[11]),
            "fixed_parameter_weighted_distance_from_native": float(validation[12]),
        }
        if not all((
            native_validation["stage_residual_max"] <= 1e-9,
            native_validation["update_residual_max"] <= 1e-9,
            native_validation["phase_residual_abs"] <= 1e-10,
            native_validation["physical_states_positive_finite"],
            native_validation["period_positive_finite"],
            native_validation["linear_solve_complete"],
        )):
            raise RuntimeError(f"native accepted-point gates failed at point {point_index}")
        points.append({
            "point_index": point_index,
            "phase_reference_id": point[3],
            "active_coordinate": float(point[4]),
            "period_s": float(point[5]),
            "vector_key": vector_key,
            "vector_sha256": array_sha(vector),
            "native_validation": native_validation,
        })

    final_point = points[-1]
    if not np.isclose(final_point["active_coordinate"], float(begin[5]), rtol=0.0, atol=1e-14):
        raise RuntimeError("native one-branch final point did not land on target")
    if (int(end[5]), int(end[6]), int(end[8]), int(end[9])) != (1, 1, len(points) - 2, 0):
        raise RuntimeError("native one-branch event partition changed unexpectedly")

    return {
        "branch_id": SELECTED_BRANCH_ID,
        "fixed_mesh_fixture": FIXED_MESH_FIXTURE.relative_to(ROOT).as_posix(),
        "fixture_sha256": sha256_file(FIXED_MESH_FIXTURE),
        "phase_reference_id": begin[2],
        "active_coordinate_name": begin[3],
        "origin_coordinate": float(begin[4]),
        "target_coordinate": float(begin[5]),
        "continuation_contract": {
            "version": contract[1],
            "base_dimension": int(contract[4]),
            "extended_dimension": int(contract[5]),
            "fixed_mesh_segment_owner": "LOCA::Stepper",
            "base_has_arclength": False,
        },
        "bootstrap_attempts": [{
            "attempt": int(row[2]),
            "requested_coordinate_step": float(row[3]),
            "trial_coordinate": float(row[4]),
            "accepted": row[5] == "accepted",
            "weighted_step_norm": float(row[6]),
        } for row in bootstrap_rows],
        "restart_orientation": {
            "signed_bootstrap_parameter_component": float(restart[2]),
            "signed_bootstrap_weighted_norm": float(restart[3]),
            "injected_parameter_component": float(restart[4]),
            "injected_weighted_norm": float(restart[5]),
            "signed_initial_step": float(restart[6]),
            "injected_orientation_canonicalized": as_bool(restart[7]),
        },
        "event_partition": {
            "initial_save_count": int(end[5]),
            "final_save_count": int(end[6]),
            "regular_attempt_count": int(end[7]),
            "regular_accepted_count": int(end[8]),
            "regular_rejected_count": int(end[9]),
            "accepted_point_count": len(points),
        },
        "events": events,
        "points": points,
        "remesh_boundary": {
            "policy": "stop only after an accepted native LOCA callback; rejected/native in-flight attempts are not remesh boundaries",
            "event_callback_index": remesh_events[0]["callback_index"],
            "point_index": final_point["point_index"],
            "active_coordinate": final_point["active_coordinate"],
            "period_s": final_point["period_s"],
            "checkpoint_vector_key": final_point["vector_key"],
            "checkpoint_vector_sha256": final_point["vector_sha256"],
        },
        "build_identity": build_identity,
        "source_fingerprint_sha256": source_fingerprint,
    }, build_identity, source_fingerprint


def parse_controller(rows: list[list[str]], arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    contract = first_row(rows, "adaptive_controller_contract")
    if first_row(rows, "source_fingerprint")[1:] != expected_fingerprints():
        raise RuntimeError("stale native executable source fingerprint for adaptive controller")
    defect_summary = first_row(rows, "defect_summary")
    h_marking = first_row(rows, "h_marking")
    r_movement = first_row(rows, "r_movement")
    for row_name in ("defect_combined", "monitor_target_boundaries", "r_movement_boundaries"):
        row = first_row(rows, row_name)
        arrays[f"controller__{SELECTED_ADAPTIVE_CASE_ID}__{row_name}"] = vector_from_row(row)
    decision = next(row for row in rows if row[:2] == ["cycle_decision", "actual"])
    retry = next(row for row in rows if row[:2] == ["restart_plan", "h+r"])
    return {
        "adaptive_fixture_case_id": SELECTED_ADAPTIVE_CASE_ID,
        "fixture_path": ADAPTIVE_FIXTURE.relative_to(ROOT).as_posix(),
        "fixture_sha256": sha256_file(ADAPTIVE_FIXTURE),
        "contract": contract[1:],
        "defect": {
            "maximum": float(defect_summary[1]),
            "argmax_phase": float(defect_summary[2]),
            "argmax_bin": int(defect_summary[3]),
            "material_probe_count": int(defect_summary[4]),
            "combined_vector_key": f"controller__{SELECTED_ADAPTIVE_CASE_ID}__defect_combined",
        },
        "h_marking": {
            "marked_count": int(h_marking[1]),
            "growth_limit": int(h_marking[2]),
            "new_interval_count": int(h_marking[3]),
            "halfmax_threshold": float(h_marking[4]),
            "marked_elements": [int(value) for value in h_marking[5:]],
        },
        "r_movement": {
            "status": r_movement[1],
            "beta": float(r_movement[2]),
            "attempt_count": int(r_movement[3]),
            "target_boundaries_key": f"controller__{SELECTED_ADAPTIVE_CASE_ID}__monitor_target_boundaries",
            "bounded_boundaries_key": f"controller__{SELECTED_ADAPTIVE_CASE_ID}__r_movement_boundaries",
        },
        "cycle_decision_actual": decision[2:],
        "restart_retry_order_h_plus_r": retry[2:],
    }


def parse_transfer(rows: list[list[str]], arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    contract = first_row(rows, "adaptive_transfer_contract")
    if first_row(rows, "source_fingerprint")[1:] != expected_fingerprints():
        raise RuntimeError("stale native executable source fingerprint for adaptive transfer")
    vector_rows = {
        "destination_boundaries": first_row(rows, "destination_boundaries"),
        "transferred_unknowns": first_row(rows, "transferred_unknowns"),
        "transferred_tangent": first_row(rows, "transferred_tangent"),
        "transferred_phase_values": first_row(rows, "transferred_phase_values"),
        "transferred_phase_derivatives": first_row(rows, "transferred_phase_derivatives"),
    }
    keys: dict[str, str] = {}
    for name, row in vector_rows.items():
        key = f"transfer__{SELECTED_ADAPTIVE_CASE_ID}__{name}"
        arrays[key] = vector_from_row(row, width=3 if name in {"transferred_phase_values", "transferred_phase_derivatives"} else 1)
        keys[name] = key
    return {
        "contract": contract[1:],
        "old_interval_count": int(contract[2]),
        "new_interval_count": int(contract[3]),
        "stage_count": int(contract[4]),
        "finite_difference_tangent_epsilon": float(contract[5]),
        "vector_keys": keys,
        "phase_energy": float(first_row(rows, "transferred_phase_energy")[1]),
        "transferred_solution_recorded": True,
        "refreshed_phase_reference_recorded": True,
        "transferred_tangent_recorded": True,
    }


def parse_restart(rows: list[list[str]], arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    contract = first_row(rows, "adaptive_restart_contract")
    if first_row(rows, "source_fingerprint")[1:] != expected_fingerprints():
        raise RuntimeError("stale native executable source fingerprint for adaptive restart")
    solution = vector_from_row(first_row(rows, "restart_solution"))
    solution_key = f"restart__{SELECTED_ADAPTIVE_CASE_ID}__corrected_solution"
    arrays[solution_key] = solution
    rebuild = first_row(rows, "restart_rebuild")
    graph = first_row(rows, "restart_graph")
    transfer_residual = [float(value) for value in first_row(rows, "restart_transfer_residual")[1:7]]
    tangent = first_row(rows, "restart_tangent")
    correction = first_row(rows, "restart_correction")
    linear = first_row(rows, "restart_linear")
    final = [float(value) for value in first_row(rows, "restart_final_diagnostics")[1:7]]
    gates_row = first_row(rows, "restart_gates")[1:]
    gates = dict(zip(gates_row[::2], [as_bool(value) for value in gates_row[1::2]], strict=True))
    if not all(gates.values()) or correction[1] != "accepted" or correction[2] != "converged":
        raise RuntimeError("native adaptive one-branch restart gates failed")
    return {
        "contract": contract[1:],
        "rebuild": {
            "old_unknown_size": int(rebuild[1]),
            "new_unknown_size": int(rebuild[2]),
            "old_stage_size": int(rebuild[3]),
            "new_stage_size": int(rebuild[4]),
            "old_endpoint_size": int(rebuild[5]),
            "new_endpoint_size": int(rebuild[6]),
            "old_log_period_index": int(rebuild[7]),
            "new_log_period_index": int(rebuild[8]),
            "old_phase_row": int(rebuild[9]),
            "new_phase_row": int(rebuild[10]),
            "old_stage_count": int(rebuild[11]),
            "new_stage_count": int(rebuild[12]),
        },
        "graph": {
            "entry_count": int(graph[1]),
            "retained_reuse": as_bool(graph[3]),
            "rebuilt": as_bool(graph[5]),
        },
        "attempts": first_row(rows, "restart_attempts")[2:],
        "transfer_residual": {
            "stage_max": transfer_residual[0], "stage_rms": transfer_residual[1],
            "update_max": transfer_residual[2], "update_rms": transfer_residual[3],
            "phase_abs": transfer_residual[4], "phase_energy": transfer_residual[5],
        },
        "tangent": {
            "pre_normalization_norm": float(tangent[1]),
            "post_normalization_norm": float(tangent[2]),
            "accepted": as_bool(tangent[3]),
        },
        "correction": {
            "status": correction[1],
            "nox_status": correction[2],
            "iterations": int(correction[3]),
            "nox_residual_norm": float(correction[4]),
            "correction_norm": float(correction[5]),
            "period_s": float(correction[6]),
        },
        "linear": {
            "backend": linear[1], "reported": linear[2] == "reported",
            "symbolic_factorizations": int(linear[3]), "numeric_factorizations": int(linear[4]),
            "solves": int(linear[5]), "symbolic_complete": as_bool(linear[6]),
            "numeric_complete": as_bool(linear[7]), "solve_complete": as_bool(linear[8]),
        },
        "final_diagnostics": {
            "stage_max": final[0], "stage_rms": final[1],
            "update_max": final[2], "update_rms": final[3],
            "phase_abs": final[4], "phase_energy": final[5],
        },
        "gates": gates,
        "solution_vector_key": solution_key,
        "solution_sha256": array_sha(solution),
    }


def restart_smoke_parity(restart_solution_sha256: str) -> dict[str, Any]:
    smoke = json.loads(RESTART_SMOKE.read_text())
    case = next(item for item in smoke["cases"] if item["case_id"] == SELECTED_ADAPTIVE_CASE_ID)
    if case["restart"] is None:
        raise RuntimeError("selected one-branch restart case is absent from restart-smoke artifact")
    if case["restart"]["solution_sha256"] != restart_solution_sha256:
        raise RuntimeError("one-branch restart solution does not match restart-smoke parity artifact")
    return {
        "artifact_path": RESTART_SMOKE.relative_to(ROOT).as_posix(),
        "artifact_sha256": sha256_file(RESTART_SMOKE),
        "case_id": SELECTED_ADAPTIVE_CASE_ID,
        "matching_restart_solution_sha256": restart_solution_sha256,
        "restart_smoke_all_gates_passed": all(case["restart"]["gates"].values()),
        "restart_smoke_source": "existing native adaptive restart-smoke parity artifact",
    }


def native_fixed_mesh_python_parity(branch: dict[str, Any]) -> dict[str, Any]:
    native = json.loads(NATIVE_HIGHER_ORDER.read_text())
    source_branch = next(item for item in native["branches"] if item["branch_id"] == SELECTED_BRANCH_ID)
    source_points = [point for point in native["points"] if point["branch_id"] == SELECTED_BRANCH_ID]
    max_period_error = max(point["python_same_coordinate_period_relative_error"] for point in source_points)
    max_orbit_error = max(point["python_same_coordinate_weighted_orbit_error"] for point in source_points)
    if len(source_points) != branch["event_partition"]["accepted_point_count"]:
        raise RuntimeError("one-branch run point count disagrees with native higher-order parity artifact")
    return {
        "artifact_path": NATIVE_HIGHER_ORDER.relative_to(ROOT).as_posix(),
        "artifact_sha256": sha256_file(NATIVE_HIGHER_ORDER),
        "branch_id": SELECTED_BRANCH_ID,
        "independent_python_correction_backend": native["parity"]["reference_backend"],
        "period_relative_tolerance": native["parity"]["period_relative_tolerance"],
        "weighted_orbit_tolerance": native["parity"]["weighted_orbit_tolerance"],
        "selected_branch_reached_exact_target": source_branch["reached_exact_target"],
        "maximum_selected_branch_period_relative_error": max_period_error,
        "maximum_selected_branch_weighted_orbit_error": max_orbit_error,
    }


def build() -> tuple[bytes, bytes]:
    arrays: dict[str, np.ndarray] = {}
    branch_rows = execute("loca-branches", FIXED_MESH_FIXTURE)
    branch, build_identity, source_fingerprint = parse_native_branch(branch_rows, arrays)
    controller = parse_controller(execute("adaptive-controller", ADAPTIVE_FIXTURE), arrays)
    transfer = parse_transfer(execute("adaptive-transfer", ADAPTIVE_FIXTURE), arrays)
    restart = parse_restart(execute("adaptive-restart", ADAPTIVE_FIXTURE), arrays)
    vector_bytes = npz_bytes(arrays)
    vector_manifest = {
        "artifact_kind": VECTOR_ARTIFACT_KIND,
        "array_count": len(arrays),
        "arrays": {
            key: {"shape": list(np.asarray(value).shape), "sha256": array_sha(value)}
            for key, value in arrays.items()
        },
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "task06801-native-adaptive-one-branch-segment-runner",
        "scope": "one selected native three-stage branch segment plus one accepted remesh/restart boundary; not the full TASK-068 spine-and-slices run",
        "truthfulness_policy": {
            "native_one_branch_fixed_mesh_loca_segment_executed": True,
            "native_one_branch_remesh_restart_executed": True,
            "native_full_spine_and_slices_adaptive_run_executed": False,
            "python_adaptive_evidence_not_rebranded_as_native_full_run": True,
        },
        "selected_branch_id": SELECTED_BRANCH_ID,
        "selected_adaptive_case_id": SELECTED_ADAPTIVE_CASE_ID,
        "native_fixed_mesh_segment": branch,
        "adaptive_controller": controller,
        "transfer": transfer,
        "restart": restart,
        "gates": {
            "native_segment_accepted_point_residual_phase_positivity_linear": all(
                point["native_validation"]["stage_residual_max"] <= 1e-9
                and point["native_validation"]["update_residual_max"] <= 1e-9
                and point["native_validation"]["phase_residual_abs"] <= 1e-10
                and point["native_validation"]["physical_states_positive_finite"]
                and point["native_validation"]["period_positive_finite"]
                and point["native_validation"]["linear_solve_complete"]
                for point in branch["points"]
            ),
            "remesh_transfer_solution_reference_tangent_recorded": (
                transfer["transferred_solution_recorded"]
                and transfer["refreshed_phase_reference_recorded"]
                and transfer["transferred_tangent_recorded"]
            ),
            "restart_residual_phase_positivity_finite_change_linear_tangent": all(restart["gates"].values()),
            "remesh_boundary_is_accepted_native_point": branch["remesh_boundary"]["event_callback_index"] == branch["events"][-1]["callback_index"],
        },
        "parity": {
            "native_fixed_mesh_vs_independent_python": native_fixed_mesh_python_parity(branch),
            "restart_vs_existing_restart_smoke": restart_smoke_parity(restart["solution_sha256"]),
        },
        "resumable_state": {
            "resume_after": "accepted_remesh_restart",
            "checkpoint_vector_key": branch["remesh_boundary"]["checkpoint_vector_key"],
            "restart_solution_vector_key": restart["solution_vector_key"],
            "next_step_scope": "TASK-068.02 generalized adaptive driver/resume behavior",
            "full_run_terminal_status": "not_claimed",
        },
        "vector_artifact": {**vector_manifest, "sha256": hashlib.sha256(vector_bytes).hexdigest()},
        "runtime_provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "compiler_and_trilinos": build_identity,
            "executable_sha256": sha256_file(EXECUTABLE),
            "emitting_executable_source_fingerprints": source_fingerprint,
        },
        "source_provenance": {
            "generator": source_record(GENERATOR),
            "fixed_mesh_fixture": source_record(FIXED_MESH_FIXTURE),
            "adaptive_fixture": source_record(ADAPTIVE_FIXTURE),
            "native_higher_order_results": source_record(NATIVE_HIGHER_ORDER),
            "restart_smoke": source_record(RESTART_SMOKE),
            **{f"compiled_source_{index}": source_record(path) for index, path in enumerate(SOURCE_PATHS)},
        },
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_one_branch_segment.py [--check]",
    }
    return canonical(payload), vector_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    body, vector_bytes = build()
    if args.check:
        if not RESULTS.is_file() or RESULTS.read_bytes() != body or not VECTORS.is_file() or VECTORS.read_bytes() != vector_bytes:
            raise SystemExit("native adaptive one-branch segment artifacts are stale")
        print("verified native adaptive one-branch segment artifacts")
    else:
        RESULTS.write_bytes(body)
        VECTORS.write_bytes(vector_bytes)
        print(f"wrote {RESULTS.relative_to(ROOT)} and {VECTORS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
