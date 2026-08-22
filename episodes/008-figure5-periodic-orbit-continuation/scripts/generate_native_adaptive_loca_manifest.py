#!/usr/bin/env python3
"""Generate the TASK-068 native adaptive-LOCA remesh/restart manifest.

This artifact is deliberately conservative.  It reconciles the frozen TASK-067
Python adaptive/remesh contracts with the already executed native fixed-mesh
three-stage LOCA stack, enumerates the planned spine-and-slices adaptive targets,
and records which targets have native fixed-mesh evidence versus which remain
pending for the full adaptive native run.  It must not relabel fixed-mesh or
Python-only evidence as completed native adaptive remeshing.
"""
from __future__ import annotations

import argparse
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

from bergner_spichtinger_2026 import (  # noqa: E402
    ADAPTIVE_CONTROLLER_VERSION,
    ADAPTIVE_METHOD_VERSION,
    H_MARKING_VERSION,
    MONITOR_VERSION,
    R_MOVEMENT_VERSION,
    RESTART_RETRY_VERSION,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
RESULTS = OUTPUT / "native_adaptive_loca_manifest.json"
VECTORS = OUTPUT / "native_adaptive_loca_manifest_vectors.npz"

ADAPTIVE_FIXTURES = OUTPUT / "adaptive_collocation_fixtures.json"
ADAPTIVE_FIXTURE_VECTORS = OUTPUT / "adaptive_collocation_fixtures_vectors.npz"
ADAPTIVE_QUALIFICATION = OUTPUT / "adaptive_qualification_results.json"
ADAPTIVE_QUALIFICATION_VECTORS = OUTPUT / "adaptive_qualification_vectors.npz"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
NATIVE_HIGHER_ORDER_VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"
CPP_CORRECTION = OUTPUT / "cpp_higher_order_correction_results.json"
CPP_NONUNIFORM_FIXTURES = OUTPUT / "cpp_adaptive_nonuniform_fixtures/manifest.json"

SCHEMA_VERSION = "episode008-native-adaptive-loca-manifest-v1"
ARTIFACT_KIND = "task068-native-adaptive-loca-remesh-restart-manifest"
VECTOR_ARTIFACT_KIND = "task068-native-adaptive-loca-manifest-vectors"
ALLOWED_TERMINAL_STATUSES = (
    "accepted",
    "resolution_unresolved",
    "near_hopf_stop",
    "tripwire_stop",
    "failed",
)
PROVISIONAL_SPINE_RANGE_K = (210, 226)
TEMPERATURE_SKELETON_K = tuple(sorted(set(range(210, 227, 2)) | {225}))
SIGNED_RHO_TARGETS = (-0.15, 0.15)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def final_cycle(case: dict[str, Any]) -> dict[str, Any]:
    cycles = case["cycles"]
    if not cycles:
        raise RuntimeError(f"adaptive case {case['case_id']} has no cycles")
    return cycles[-1]


def build_vector_artifact(adaptive: dict[str, Any], native: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    arrays: dict[str, np.ndarray] = {}
    with np.load(ADAPTIVE_QUALIFICATION_VECTORS, allow_pickle=False) as adaptive_npz:
        for case in adaptive["results"]:
            prefix = final_cycle(case)["array_prefix"]
            for suffix in ("boundaries", "unknowns", "defect_maxima", "probe_admitted"):
                key = f"{prefix}__{suffix}"
                if key not in adaptive_npz.files:
                    raise RuntimeError(f"missing adaptive qualification array {key}")
                arrays[f"adaptive_final__{case['case_id']}__{suffix}"] = adaptive_npz[key]
    with np.load(NATIVE_HIGHER_ORDER_VECTORS, allow_pickle=False) as native_npz:
        # Store native checkpoints for the start/end of each already executed fixed-mesh branch.
        for branch in native["branches"]:
            names = sorted(name for name in native_npz.files if name.startswith(f"native_g3__{branch['branch_id']}__"))
            if not names:
                raise RuntimeError(f"missing native vectors for {branch['branch_id']}")
            arrays[f"native_fixed_mesh_checkpoint__{branch['branch_id']}__first"] = native_npz[names[0]]
            arrays[f"native_fixed_mesh_checkpoint__{branch['branch_id']}__last"] = native_npz[names[-1]]
    vector_bytes = npz_bytes(arrays)
    manifest = {
        "artifact_kind": VECTOR_ARTIFACT_KIND,
        "array_count": len(arrays),
        "arrays": {
            key: {"shape": list(np.asarray(value).shape), "sha256": array_sha(value)}
            for key, value in arrays.items()
        },
    }
    return vector_bytes, manifest


def accepted_native_branch_ids(native: dict[str, Any]) -> set[str]:
    return {
        branch["branch_id"]
        for branch in native["branches"]
        if branch.get("reached_exact_target") and branch.get("used_bootstrap_restart_tangent")
    }


def target_record(
    *,
    target_id: str,
    target_type: str,
    temperature_K: float,
    rho: float | None,
    direction: str,
    terminal_status: str,
    evidence: str,
    reason: str | None = None,
    native_branch_id: str | None = None,
) -> dict[str, Any]:
    if terminal_status not in ALLOWED_TERMINAL_STATUSES:
        raise RuntimeError(f"invalid terminal status for {target_id}: {terminal_status}")
    record: dict[str, Any] = {
        "target_id": target_id,
        "target_type": target_type,
        "temperature_K": temperature_K,
        "rho": rho,
        "direction": direction,
        "terminal_status": terminal_status,
        "evidence_level": evidence,
    }
    if native_branch_id is not None:
        record["native_branch_id"] = native_branch_id
    if reason is not None:
        record["reason"] = reason
    elif terminal_status == "failed":
        raise RuntimeError(f"failed target {target_id} requires a reason")
    return record


def build_planned_manifest(native: dict[str, Any]) -> dict[str, Any]:
    accepted = accepted_native_branch_ids(native)
    targets: list[dict[str, Any]] = []
    pending_reason = "native_adaptive_remesh_run_pending; fixed-mesh/native or Python-adaptive evidence is not relabeled"

    targets.append(target_record(
        target_id="move-225K-to-spine-rho0",
        target_type="fixed_temperature_spine_move",
        temperature_K=225.0,
        rho=0.0,
        direction="rho_positive",
        terminal_status="accepted" if "fixed225-to-spine" in accepted else "failed",
        evidence="native_fixed_mesh_three_stage_LOCA_checkpoint_plus_TASK067_adaptive_contract",
        reason=None if "fixed225-to-spine" in accepted else "missing native fixed-mesh branch",
        native_branch_id="fixed225-to-spine",
    ))

    for temperature in TEMPERATURE_SKELETON_K:
        if temperature < 225:
            branch_id = "spine-negative-T-hat-to-210" if temperature == 210 else None
            direction = "temperature_negative"
        elif temperature > 225:
            branch_id = "spine-positive-T-hat" if temperature == 226 else None
            direction = "temperature_positive"
        else:
            branch_id = "fixed225-to-spine"
            direction = "anchor"
        status = "accepted" if branch_id in accepted else "failed"
        targets.append(target_record(
            target_id=f"spine-{temperature}K",
            target_type="spine_temperature",
            temperature_K=float(temperature),
            rho=0.0,
            direction=direction,
            terminal_status=status,
            evidence="native_fixed_mesh_three_stage_LOCA_checkpoint" if status == "accepted" else "planned_target_only",
            reason=None if status == "accepted" else pending_reason,
            native_branch_id=branch_id,
        ))
        for rho in SIGNED_RHO_TARGETS:
            if temperature == 210 and rho < 0:
                branch_id = "slice210-negative-rho"
            elif temperature == 210 and rho > 0:
                branch_id = "slice210-positive-rho"
            else:
                branch_id = None
            status = "accepted" if branch_id in accepted else "failed"
            targets.append(target_record(
                target_id=f"slice-{temperature}K-rho-{rho:+.2f}",
                target_type="fixed_temperature_rho_slice",
                temperature_K=float(temperature),
                rho=float(rho),
                direction="rho_negative" if rho < 0 else "rho_positive",
                terminal_status=status,
                evidence="native_fixed_mesh_three_stage_LOCA_checkpoint" if status == "accepted" else "planned_target_only",
                reason=None if status == "accepted" else pending_reason,
                native_branch_id=branch_id,
            ))

    if len({target["target_id"] for target in targets}) != len(targets):
        raise RuntimeError("planned target ids are not unique")
    if any(target["terminal_status"] not in ALLOWED_TERMINAL_STATUSES for target in targets):
        raise RuntimeError("planned target has an invalid terminal status")
    return {
        "provisional_spine_range_K": list(PROVISIONAL_SPINE_RANGE_K),
        "temperature_skeleton_K": list(TEMPERATURE_SKELETON_K),
        "signed_rho_slice_targets": list(SIGNED_RHO_TARGETS),
        "target_count": len(targets),
        "terminal_status_allowed_values": list(ALLOWED_TERMINAL_STATUSES),
        "terminal_status_counts": {status: sum(target["terminal_status"] == status for target in targets)
                                   for status in ALLOWED_TERMINAL_STATUSES},
        "targets": targets,
        "coverage_statement": (
            "The manifest enumerates T=225 K to spine, both temperature directions over the "
            "provisional 210--226 K range, and signed rho slices for every 2 K skeleton target. "
            "Targets not yet executed by native adaptive remeshing are explicit failed terminal "
            "statuses with reasons rather than interpolated or suppressed points."
        ),
    }


def parity_summary(native: dict[str, Any], cpp: dict[str, Any], adaptive: dict[str, Any], nonuniform: dict[str, Any]) -> dict[str, Any]:
    final_defects = [final_cycle(case)["defect"]["maximum"] for case in adaptive["results"]]
    accepted_cpp = [case for case in cpp["cases"] if case["accepted"]]
    return {
        "stratified_native_fixed_mesh_python_corrections": native["parity"],
        "native_fixed_parameter_correction_cases": {
            "accepted_count": len(accepted_cpp),
            "case_count": len(cpp["cases"]),
            "rejected_or_nonsolution_count": len(cpp["cases"]) - len(accepted_cpp),
            "maximum_period_relative_difference": max(abs(case["period_relative_difference"]) for case in accepted_cpp),
            "maximum_phase_aligned_weighted_orbit_distance": max(case["phase_aligned_weighted_orbit_distance"] for case in accepted_cpp),
        },
        "python_adaptive_final_defect_maximum": max(final_defects),
        "python_adaptive_all_qualification_cases_converged": all(case["converged"] for case in adaptive["results"]),
        "cpp_nonuniform_fixture_parity": {
            "case_count": len(nonuniform["cases"]),
            "all_projected_from_final_adaptive_cycles": all(case["status"] == "accepted" and case["final_defect_maximum"] < 1e-4 for case in nonuniform["cases"]),
            "schema_version": nonuniform["schema_version"],
            "manifest_sha256": sha(CPP_NONUNIFORM_FIXTURES),
            "source": "checked by tests/test_episode8_cpp_adaptive_nonuniform.py against native C++ evaluate/loca-contract/adaptive-transfer/solve seams",
        },
        "evidence_boundary": (
            "Native parity here is fixed-mesh three-stage LOCA and fixed-parameter C++ correction. "
            "Adaptive remesh transfer/restart intermediates are from TASK-067 Python fixtures until "
            "the native adaptive run is executed."
        ),
    }


def build_manifest() -> tuple[bytes, bytes]:
    fixtures = load_json(ADAPTIVE_FIXTURES)
    adaptive = load_json(ADAPTIVE_QUALIFICATION)
    native = load_json(NATIVE_HIGHER_ORDER)
    cpp = load_json(CPP_CORRECTION)
    nonuniform = load_json(CPP_NONUNIFORM_FIXTURES)

    if fixtures["method_version"] != ADAPTIVE_METHOD_VERSION:
        raise RuntimeError("adaptive fixture method version mismatch")
    if adaptive["method_version"] != ADAPTIVE_METHOD_VERSION:
        raise RuntimeError("adaptive qualification method version mismatch")
    if native["schema_version"] != "episode8-native-loca-higher-order-v1":
        raise RuntimeError("unexpected native higher-order schema")
    if cpp["schema_version"] != "episode008-cpp-gauss-correction-results-v1":
        raise RuntimeError("unexpected C++ correction schema")
    if nonuniform["schema_version"] != "episode008-cpp-adaptive-nonuniform-fixtures-v1":
        raise RuntimeError("unexpected C++ nonuniform fixture schema")

    vector_bytes, vector_manifest = build_vector_artifact(adaptive, native)
    vector_manifest["sha256"] = hashlib.sha256(vector_bytes).hexdigest()
    vector_manifest["source_npz"] = {
        "adaptive_qualification_vectors": source_record(ADAPTIVE_QUALIFICATION_VECTORS),
        "native_loca_higher_order_vectors": source_record(NATIVE_HIGHER_ORDER_VECTORS),
    }

    planned = build_planned_manifest(native)
    branch_count = len(native["branches"])
    refresh_count = native["controlled_phase_reference_refresh_count"]
    accepted_point_count = len([event for event in native["events"] if event.get("status") == "accepted"])
    rejected_event_count = len([event for event in native["events"] if event.get("status") == "rejected"])

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "scope": (
            "TASK-068 start artifact: native fixed-mesh LOCA plus Python adaptive fixtures reconciled "
            "into a resumable adaptive-run manifest; not final Figure 5 production data."
        ),
        "truthfulness_policy": {
            "native_adaptive_remesh_executed": False,
            "fixed_mesh_native_evidence_may_seed_adaptive_run": True,
            "python_adaptive_evidence_not_rebranded_as_native": True,
            "broader_ivp_based_evidence": "not_evaluated",
            "floquet_dependent_evidence": "not_evaluated",
        },
        "versions": {
            "adaptive_method": ADAPTIVE_METHOD_VERSION,
            "monitor": MONITOR_VERSION,
            "h_marking": H_MARKING_VERSION,
            "r_movement": R_MOVEMENT_VERSION,
            "adaptive_controller": ADAPTIVE_CONTROLLER_VERSION,
            "restart_retry": RESTART_RETRY_VERSION,
            "native_loca_fixed_mesh": native["native_contracts"]["gauss_3"]["continuation_version"],
            "manifest_schema": SCHEMA_VERSION,
        },
        "native_segment_contract": {
            "fixed_mesh_segment_owner": "LOCA::Stepper",
            "remesh_boundary_policy": "stop only at accepted native points before any h/r rebuild",
            "base_system": "square three-stage Gauss residual; LOCA owns Arc Length extension",
            "full_rebuild_lineage": ["Tpetra::Map", "Tpetra::CrsGraph", "Tpetra::CrsMatrix", "Thyra model", "NOX group", "KLU2 LOWS", "WeightedThyraGroup", "LOCA::Stepper"],
            "post_transfer_restart_gates": ["residual", "phase", "positivity", "finite_change", "linear_KLU2", "restart_tangent"],
            "tangent_policy": "renormalize transferred tangent; deterministic two-point rebootstrap only for tangent-only failure",
            "retry_order_from_TASK067_fixture": fixtures["restart_retry"],
        },
        "native_fixed_mesh_evidence": {
            "branch_count": branch_count,
            "required_branch_ids": native["required_branch_ids"],
            "controlled_phase_reference_refresh_count": refresh_count,
            "accepted_event_count": accepted_point_count,
            "rejected_event_count": rejected_event_count,
            "all_branches_reached_exact_target": all(branch["reached_exact_target"] for branch in native["branches"]),
            "all_restart_tangents_used": all(branch["used_bootstrap_restart_tangent"] for branch in native["branches"]),
            "source_manifest_sha256": sha(NATIVE_HIGHER_ORDER),
        },
        "adaptive_reference_evidence": {
            "qualification_case_count": len(adaptive["results"]),
            "all_cases_converged": all(case["converged"] for case in adaptive["results"]),
            "final_interval_counts": {case["case_id"]: final_cycle(case)["interval_count"] for case in adaptive["results"]},
            "final_defect_maxima": {case["case_id"]: final_cycle(case)["defect"]["maximum"] for case in adaptive["results"]},
            "restart_fixture_source_sha256": sha(ADAPTIVE_FIXTURES),
            "qualification_source_sha256": sha(ADAPTIVE_QUALIFICATION),
        },
        "planned_run_manifest": planned,
        "near_hopf_evidence": {
            "status": "not_reached_in_this_preparatory_manifest",
            "required_future_recording": ["amplitude", "period", "terminal_status", "approach_coordinate", "near_hopf_stop_reason"],
            "minimum_reliable_point_target_when_reached": 5,
            "fit_review_deferred_to": "TASK-069",
        },
        "parity": parity_summary(native, cpp, adaptive, nonuniform),
        "resumability": {
            "completion_state": "pre_run_manifest_ready",
            "checkpoint_arrays": "first/last native fixed-mesh checkpoints and final Python adaptive meshes are in vector_artifact",
            "stale_checkpoint_rejection_basis": ["source_provenance", "vector_artifact.sha256", "source_npz hashes", "schema_version"],
        },
        "source_provenance": {
            "manifest_generator": source_record(Path(__file__)),
            "adaptive_fixtures": source_record(ADAPTIVE_FIXTURES),
            "adaptive_fixture_vectors": source_record(ADAPTIVE_FIXTURE_VECTORS),
            "adaptive_qualification": source_record(ADAPTIVE_QUALIFICATION),
            "adaptive_qualification_vectors": source_record(ADAPTIVE_QUALIFICATION_VECTORS),
            "native_loca_higher_order_results": source_record(NATIVE_HIGHER_ORDER),
            "native_loca_higher_order_vectors": source_record(NATIVE_HIGHER_ORDER_VECTORS),
            "cpp_higher_order_correction_results": source_record(CPP_CORRECTION),
            "cpp_adaptive_nonuniform_fixture_manifest": source_record(CPP_NONUNIFORM_FIXTURES),
            "cpp_adaptive_nonuniform_fixture_generator": source_record(EPISODE / "scripts/generate_cpp_adaptive_nonuniform_fixtures.py"),
            "adaptive_orbits_source": source_record(ROOT / "src/bergner_spichtinger_2026/adaptive_orbits.py"),
            "native_loca_header": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp"),
            "native_orbit_header": source_record(ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp"),
            "native_cli_source": source_record(ROOT / "loca/src/midpoint_orbit_cli.cpp"),
        },
        "vector_artifact": vector_manifest,
        "regeneration_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_loca_manifest.py [--check]",
    }
    return canonical(manifest), vector_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify existing outputs without rewriting")
    args = parser.parse_args()
    result_bytes, vector_bytes = build_manifest()
    if args.check:
        if not RESULTS.is_file() or not VECTORS.is_file() or RESULTS.read_bytes() != result_bytes or VECTORS.read_bytes() != vector_bytes:
            raise SystemExit("native adaptive LOCA manifest artifacts are stale")
        print("verified native adaptive LOCA manifest artifacts")
    else:
        RESULTS.write_bytes(result_bytes)
        VECTORS.write_bytes(vector_bytes)
        print(f"wrote {RESULTS.relative_to(ROOT)}")
        print(f"wrote {VECTORS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
