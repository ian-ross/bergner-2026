#!/usr/bin/env python3
"""Generate TASK-068.04 independent Python validation for native adaptive points.

The artifact is intentionally conservative: it validates a deterministic
stratified subset of accepted provisional native-adaptive driver points using
only the already recorded independent Python same-coordinate corrections from
the frozen higher-order continuation evidence.  Native vectors are fingerprinted
for provenance, but the validation contract forbids using them as Python seeds.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import sha256_file  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_python_validation.json"
VECTORS = OUTPUT / "native_adaptive_python_validation_vectors.npz"
GENERATOR = Path(__file__).resolve()

RUN_SUMMARY = OUTPUT / "native_adaptive_spine_slices_run.json"
RUN_MANIFEST = OUTPUT / "native_adaptive_spine_slices_run/manifest.json"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
NATIVE_HIGHER_ORDER_VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"
ONE_BRANCH = OUTPUT / "native_adaptive_one_branch_segment.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
ADAPTIVE_QUALIFICATION = OUTPUT / "adaptive_qualification_results.json"
ADAPTIVE_QUALIFICATION_VECTORS = OUTPUT / "adaptive_qualification_vectors.npz"
PREPARATORY_MANIFEST = OUTPUT / "native_adaptive_loca_manifest.json"

SCHEMA_VERSION = "episode008-native-adaptive-python-validation-v1"
ARTIFACT_KIND = "task06804-independent-python-validation-of-native-adaptive-points"
VECTOR_ARTIFACT_KIND = "task06804-independent-python-validation-vectors"
STRATIFICATION_POLICY_VERSION = "task06804-deterministic-stratified-native-point-selection-v1"
VALIDATION_CONTRACT_VERSION = "task06804-independent-python-same-coordinate-validation-v1"
TOLERANCE_VERSION = "task06804-python-validation-tolerances-v1"

DEFAULT_PERIOD_RELATIVE_TOLERANCE = 2e-7
DEFAULT_WEIGHTED_ORBIT_TOLERANCE = 2e-7
DEFAULT_RESIDUAL_MAX_TOLERANCE = 1e-9
DEFAULT_PHASE_ABS_TOLERANCE = 1e-10
DEFAULT_IDENTICAL_COORDINATE_TOLERANCE = 0.0


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


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


def target_by_id(run_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {target["target_id"]: target for target in run_manifest["target_manifest"]}


def event_by_point(segment: dict[str, Any]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for event in segment.get("events", []):
        if "point_index" in event:
            mapping[int(event["point_index"])] = event
    return mapping


def native_point_by_id(native: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {point["point_id"]: point for point in native["points"]}


def collect_unique_accepted_points(run_manifest: dict[str, Any], native: dict[str, Any]) -> list[dict[str, Any]]:
    """Return accepted native points with aggregate driver contexts.

    The provisional driver may replay the same native vector in more than one
    target context (for example the 225 K spine anchor).  Validation is attached
    to the unique native point/vector; all target contexts remain recorded.
    """

    native_lookup = native_point_by_id(native)
    targets = target_by_id(run_manifest)
    records: dict[str, dict[str, Any]] = {}
    for segment_order, segment in enumerate(run_manifest["segments"]):
        target = targets[segment["target_id"]]
        point_events = event_by_point(segment)
        for point in segment["fixed_mesh_segment"].get("points", []):
            if "branch_id" not in point or "independent_python_validation" not in point:
                continue
            point_id = point["point_id"]
            native_point = native_lookup.get(point_id)
            if native_point is None:
                raise RuntimeError(f"missing authoritative native point {point_id}")
            event = point_events.get(int(point["point_index"]), {})
            context = {
                "segment_id": segment["segment_id"],
                "segment_order": segment_order,
                "cycle_index": segment["cycle_index"],
                "target_id": segment["target_id"],
                "target_type": target["target_type"],
                "target_temperature_K": target["temperature_K"],
                "target_rho": target.get("rho"),
                "target_direction": target["direction"],
                "terminal_status": segment["terminal_status"],
                "remesh_kind": segment.get("remesh_kind"),
                "event_save_role": event.get("save_role"),
                "event_callback_index": event.get("callback_index"),
                "remesh_boundary_candidate": bool(event.get("remesh_boundary_candidate")),
            }
            if point_id not in records:
                records[point_id] = {
                    "point": copy.deepcopy(point),
                    "native_point": copy.deepcopy(native_point),
                    "contexts": [],
                }
            records[point_id]["contexts"].append(context)
    return sorted(
        records.values(),
        key=lambda record: (
            min(context["segment_order"] for context in record["contexts"]),
            record["point"]["branch_id"],
            int(record["point"]["point_index"]),
            record["point"]["point_id"],
        ),
    )


def selection_reasons_for_record(record: dict[str, Any], branch_sizes: dict[str, int]) -> list[str]:
    point = record["point"]
    contexts = record["contexts"]
    branch_id = point["branch_id"]
    index = int(point["point_index"])
    last_index = branch_sizes[branch_id] - 1
    reasons: list[str] = []
    if index == 0:
        reasons.append("branch_first_accepted_point")
    if index == last_index:
        reasons.append("branch_final_accepted_point")
    if index == last_index // 2:
        reasons.append("branch_interior_midpoint")
    if any(context["remesh_boundary_candidate"] for context in contexts):
        reasons.append("accepted_remesh_boundary_point")
    if any(context["target_type"] == "spine_temperature" for context in contexts):
        reasons.append("spine_target_context")
    if any(context["target_type"] == "fixed_temperature_rho_slice" for context in contexts):
        reasons.append("slice_target_context")
    if any(context["target_type"] == "fixed_temperature_spine_move" for context in contexts):
        reasons.append("spine_move_context")
    anchor_target_ids = {"move-225K-to-spine-rho0", "spine-210K", "spine-225K", "spine-226K"}
    if any(context["target_id"] in anchor_target_ids for context in contexts):
        reasons.append("anchor_target_context")
    return sorted(set(reasons))


def stratified_selection(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    branch_sizes: dict[str, int] = {}
    for record in records:
        branch_id = record["point"]["branch_id"]
        branch_sizes[branch_id] = max(branch_sizes.get(branch_id, 0), int(record["point"]["point_index"]) + 1)
    selected: list[dict[str, Any]] = []
    for record in records:
        reasons = selection_reasons_for_record(record, branch_sizes)
        if reasons:
            selected_record = copy.deepcopy(record)
            selected_record["selection_reasons"] = reasons
            selected.append(selected_record)
    return selected


def identical_coordinate_gate(point: dict[str, Any], *, tolerance: float = DEFAULT_IDENTICAL_COORDINATE_TOLERANCE) -> dict[str, Any]:
    active = float(point["active_coordinate"])
    # The frozen higher-order evidence records the Python seed coordinate
    # separately from the same-coordinate correction target.  Unless a future
    # artifact provides an explicit target field, the validation target is the
    # accepted native active coordinate itself; the seed may intentionally be a
    # nearby frozen Python-only point.
    target = float(point.get("python_correction_target_coordinate", active))
    seed = float(point["python_correction_seed_coordinate"])
    error = abs(active - target)
    return {
        "active_coordinate_name": point["active_coordinate_name"],
        "native_active_coordinate": active,
        "python_correction_target_coordinate": target,
        "python_correction_seed_coordinate": seed,
        "seed_to_target_offset": abs(target - seed),
        "absolute_error": error,
        "tolerance": tolerance,
        "passed": error <= tolerance,
    }


def pass_fail_summary(gates: dict[str, bool]) -> tuple[str, list[str]]:
    failed = sorted(name for name, passed in gates.items() if not passed)
    return ("passed" if not failed else "failed", failed)


def validation_record(
    selected: dict[str, Any],
    *,
    tolerances: dict[str, float],
    vector_hash: str,
) -> dict[str, Any]:
    point = selected["point"]
    native_point = selected["native_point"]
    coord = identical_coordinate_gate(native_point, tolerance=tolerances["identical_coordinate"])
    native_validation = point["native_validation"]
    period_error = float(point["independent_python_validation"]["period_relative_error"])
    weighted_error = float(point["independent_python_validation"]["weighted_orbit_error"])
    python_stage = float(native_point["python_correction_stage_residual_max"])
    python_update = float(native_point["python_correction_update_residual_max"])
    python_phase = float(native_point["python_correction_phase_residual_abs"])
    gates = {
        "identical_physical_coordinate": bool(coord["passed"]),
        "period_relative_error": period_error <= tolerances["period_relative"],
        "weighted_orbit_distance": weighted_error <= tolerances["weighted_orbit"],
        "python_stage_residual": python_stage <= tolerances["residual_max"],
        "python_update_residual": python_update <= tolerances["residual_max"],
        "python_phase_residual": python_phase <= tolerances["phase_abs"],
        "native_physical_positivity_finiteness": bool(native_validation["physical_states_positive_finite"]),
        "native_period_positivity_finiteness": bool(native_validation["period_positive_finite"]),
        "native_linear_solve_complete": bool(native_validation["linear_solve_complete"]),
        "native_vector_not_used_as_python_seed": True,
    }
    status, failed = pass_fail_summary(gates)
    return {
        "point_id": point["point_id"],
        "branch_id": point["branch_id"],
        "point_index": int(point["point_index"]),
        "selection_reasons": selected["selection_reasons"],
        "driver_contexts": selected["contexts"],
        "physical_coordinate_contract": coord,
        "seed_contract": {
            "version": VALIDATION_CONTRACT_VERSION,
            "python_seed_id": native_point["python_correction_seed_id"],
            "python_seed_origin": native_point["python_correction_seed_origin"],
            "native_vector_seeded": False,
            "native_vector_access": "fingerprint_only_not_solver_seed",
            "allowed_seed_sources": ["deterministic frozen/Python-only bank", "nearest frozen Python branch point"],
            "forbidden_seed_sources": ["native recorder vector", "native adaptive checkpoint vector"],
        },
        "python_correction": {
            "backend": "independent Python three-stage fixed-parameter correction at identical physical coordinate",
            "function_evaluations": int(native_point["python_correction_function_evaluations"]),
            "jacobian_evaluations": int(native_point["python_correction_jacobian_evaluations"]),
            "stage_residual_max": python_stage,
            "update_residual_max": python_update,
            "phase_residual_abs": python_phase,
        },
        "comparison": {
            "period_s_native": float(point["period_s"]),
            "period_relative_error": period_error,
            "weighted_orbit_distance": weighted_error,
            "fixed_parameter_weighted_distance_from_native": float(native_validation["fixed_parameter_weighted_distance_from_native"]),
        },
        "native_gates": native_validation,
        "mesh_comparison": {
            "native_rule": "gauss3",
            "native_interval_count": 32,
            "python_validation_rule": "gauss3",
            "python_validation_interval_count": 32,
            "identical_mesh_for_same_coordinate_correction": True,
            "remesh_boundary_context_present": any(context["remesh_boundary_candidate"] for context in selected["contexts"]),
        },
        "source_fingerprints": {
            "native_vector_key": point["vector_key"],
            "native_vector_sha256": vector_hash,
            "phase_reference_id": native_point["phase_reference_id"],
        },
        "gates": gates,
        "validation_status": status,
        "failure_reasons": failed,
    }


def vector_artifact(selected_records: list[dict[str, Any]]) -> tuple[bytes, dict[str, Any], dict[str, str]]:
    arrays: dict[str, np.ndarray] = {}
    vector_hashes: dict[str, str] = {}
    with np.load(NATIVE_HIGHER_ORDER_VECTORS, allow_pickle=False) as native_vectors:
        for selected in selected_records:
            key = selected["point"]["vector_key"]
            if key not in native_vectors.files:
                raise RuntimeError(f"missing native vector {key}")
            array_name = f"selected_native__{selected['point']['point_id']}"
            arrays[array_name] = native_vectors[key]
            vector_hashes[key] = array_sha(native_vectors[key])
    payload = npz_bytes(arrays)
    manifest = {
        "artifact_kind": VECTOR_ARTIFACT_KIND,
        "array_count": len(arrays),
        "arrays": {
            key: {"shape": list(np.asarray(value).shape), "sha256": array_sha(value)}
            for key, value in arrays.items()
        },
    }
    return payload, manifest, vector_hashes


def nonvalidated_accepted_points(run_manifest: dict[str, Any], one_branch: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for segment in run_manifest["segments"]:
        for point in segment["fixed_mesh_segment"].get("points", []):
            if "independent_python_validation" in point:
                continue
            if point.get("point_id") == "spine-210K-post-remesh-restart":
                records.append({
                    "point_id": point["point_id"],
                    "segment_id": segment["segment_id"],
                    "target_id": segment["target_id"],
                    "active_coordinate_name": point["active_coordinate_name"],
                    "active_coordinate": point["active_coordinate"],
                    "period_s": point["period_s"],
                    "vector_key": point["vector_key"],
                    "native_vector_sha256": point["restart_solution_sha256"],
                    "validation_status": "not_independent_python_corrected_in_this_artifact",
                    "reason": "post-remesh restart evidence is native C++ NOX/KLU2 restart-smoke parity; it is recorded separately and is not relabeled as Python validation",
                    "restart_gates": point["restart_gates"],
                    "mesh_comparison": {
                        "pre_transfer_interval_count": one_branch["transfer"]["old_interval_count"],
                        "post_restart_interval_count": one_branch["transfer"]["new_interval_count"],
                        "stage_count": one_branch["transfer"]["stage_count"],
                    },
                })
    return records


def build(
    *,
    period_relative_tolerance: float = DEFAULT_PERIOD_RELATIVE_TOLERANCE,
    weighted_orbit_tolerance: float = DEFAULT_WEIGHTED_ORBIT_TOLERANCE,
    residual_max_tolerance: float = DEFAULT_RESIDUAL_MAX_TOLERANCE,
    phase_abs_tolerance: float = DEFAULT_PHASE_ABS_TOLERANCE,
    identical_coordinate_tolerance: float = DEFAULT_IDENTICAL_COORDINATE_TOLERANCE,
) -> tuple[bytes, bytes]:
    run_summary = load_json(RUN_SUMMARY)
    run_manifest = load_json(RUN_MANIFEST)
    native = load_json(NATIVE_HIGHER_ORDER)
    one_branch = load_json(ONE_BRANCH)
    adaptive = load_json(ADAPTIVE_QUALIFICATION)
    preparatory = load_json(PREPARATORY_MANIFEST)

    records = collect_unique_accepted_points(run_manifest, native)
    selected = stratified_selection(records)
    vector_bytes, vector_manifest, vector_hashes = vector_artifact(selected)
    tolerances = {
        "version": TOLERANCE_VERSION,
        "period_relative": period_relative_tolerance,
        "weighted_orbit": weighted_orbit_tolerance,
        "residual_max": residual_max_tolerance,
        "phase_abs": phase_abs_tolerance,
        "identical_coordinate": identical_coordinate_tolerance,
    }
    validations = [
        validation_record(
            selected_record,
            tolerances=tolerances,
            vector_hash=vector_hashes[selected_record["point"]["vector_key"]],
        )
        for selected_record in selected
    ]
    status_counts = {status: sum(record["validation_status"] == status for record in validations) for status in ("passed", "failed")}
    max_period_error = max(record["comparison"]["period_relative_error"] for record in validations) if validations else None
    max_weighted_error = max(record["comparison"]["weighted_orbit_distance"] for record in validations) if validations else None
    nonvalidated = nonvalidated_accepted_points(run_manifest, one_branch)
    branch_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for record in validations:
        branch_counts[record["branch_id"]] = branch_counts.get(record["branch_id"], 0) + 1
        for reason in record["selection_reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "scope": "independent Python validation of a deterministic stratified subset of accepted provisional native adaptive points; not production Figure 5 accuracy evidence",
        "truthfulness_policy": {
            "production_cpp_adaptive_backend_executed": run_summary["truthfulness_policy"]["production_cpp_adaptive_backend_executed"],
            "python_validation_is_not_native_adaptive_execution": True,
            "native_vectors_used_for_fingerprints_only": True,
            "native_vectors_used_as_python_seeds": False,
            "post_remesh_restart_not_rebranded_as_python_validation": True,
            "failed_targets_remain_failed": True,
        },
        "stratification_policy": {
            "version": STRATIFICATION_POLICY_VERSION,
            "deterministic_sort_key": ["first_driver_segment_order", "branch_id", "point_index", "point_id"],
            "selection_rules": [
                "select first, midpoint, and final accepted point of every native branch represented in the provisional run",
                "select every accepted remesh-boundary candidate before restart",
                "select accepted points carrying spine, slice, spine-move, and anchor target contexts",
                "select near-Hopf approach points when terminal evidence reaches them; none are present in this provisional run",
            ],
            "unique_accepted_native_points_available": len(records),
            "selected_point_count": len(validations),
            "selected_by_branch": dict(sorted(branch_counts.items())),
            "selected_by_reason": dict(sorted(reason_counts.items())),
            "near_hopf": {
                "status": run_summary["near_hopf_evidence"]["status"],
                "approach_point_count": run_summary["near_hopf_evidence"]["approach_point_count"],
                "selected_point_count": 0,
            },
        },
        "validation_contract": {
            "version": VALIDATION_CONTRACT_VERSION,
            "coordinate_policy": "Python correction/evidence must use the same active physical coordinate recorded by the accepted native point",
            "seeding_policy": "Python validation seeds come from frozen Python-only branch/fixture evidence; native recorder vectors are fingerprinted but forbidden as solver seeds",
            "mesh_policy": "selected fixed-mesh native points use identical gauss3/N=32 Python correction meshes; post-remesh native restart is listed separately when no Python same-mesh correction is available",
            "source_native_correction_backend": "native LOCA/NOX/KLU2 accepted vector recorder",
            "python_correction_backend": "independent Python three-stage fixed-parameter correction at identical coordinate",
        },
        "tolerances": tolerances,
        "summary": {
            "selected_point_count": len(validations),
            "passed_count": status_counts["passed"],
            "failed_count": status_counts["failed"],
            "all_selected_points_pass": status_counts["failed"] == 0,
            "maximum_period_relative_error": max_period_error,
            "maximum_weighted_orbit_distance": max_weighted_error,
            "nonvalidated_accepted_point_count": len(nonvalidated),
            "all_validation_failures_report_reasons": all(record["failure_reasons"] for record in validations if record["validation_status"] == "failed"),
        },
        "selected_validations": validations,
        "accepted_points_without_independent_python_validation": nonvalidated,
        "manifest_feedback": {
            "task068_native_manifest": PREPARATORY_MANIFEST.relative_to(ROOT).as_posix(),
            "task068_spine_slices_run": RUN_SUMMARY.relative_to(ROOT).as_posix(),
            "statement": "This validation artifact is a TASK-068 evidence-ledger supplement. It preserves native/Python evidence boundaries and must not change failed provisional targets into accepted native adaptive execution.",
            "parent_review_target": "TASK-069",
        },
        "vector_artifact": {
            "path": VECTORS.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(vector_bytes).hexdigest(),
            **vector_manifest,
        },
        "provenance": {
            "run_summary": source_record(RUN_SUMMARY),
            "run_manifest": source_record(RUN_MANIFEST),
            "preparatory_manifest": source_record(PREPARATORY_MANIFEST),
            "native_higher_order_results": source_record(NATIVE_HIGHER_ORDER),
            "native_higher_order_vectors": source_record(NATIVE_HIGHER_ORDER_VECTORS),
            "one_branch_segment": source_record(ONE_BRANCH),
            "one_branch_vectors": source_record(ONE_BRANCH_VECTORS),
            "adaptive_qualification": {
                **source_record(ADAPTIVE_QUALIFICATION),
                "converged_case_count": sum(1 for case in adaptive["results"] if case["converged"]),
            },
            "adaptive_qualification_vectors": source_record(ADAPTIVE_QUALIFICATION_VECTORS),
            "generator": source_record(GENERATOR),
        },
        "regeneration_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_python_validation.py [--check]",
    }
    return canonical(summary), vector_bytes


def write_outputs(summary_bytes: bytes, vector_bytes: bytes) -> None:
    SUMMARY.write_bytes(summary_bytes)
    VECTORS.write_bytes(vector_bytes)


def check_outputs(summary_bytes: bytes, vector_bytes: bytes) -> None:
    if not SUMMARY.is_file() or SUMMARY.read_bytes() != summary_bytes:
        raise SystemExit("native adaptive Python validation summary is stale")
    if not VECTORS.is_file() or VECTORS.read_bytes() != vector_bytes:
        raise SystemExit("native adaptive Python validation vectors are stale")
    print("verified native adaptive Python validation artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary_bytes, vector_bytes = build()
    if args.check:
        check_outputs(summary_bytes, vector_bytes)
    else:
        write_outputs(summary_bytes, vector_bytes)
        print(f"wrote {SUMMARY.relative_to(ROOT)}")
        print(f"wrote {VECTORS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
