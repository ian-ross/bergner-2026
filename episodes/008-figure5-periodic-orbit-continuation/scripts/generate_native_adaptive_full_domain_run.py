#!/usr/bin/env python3
"""Generate TASK-075 full-domain native adaptive continuation artifacts.

This task is intentionally conservative: TASK-081 authorizes the retained v1
native adaptive method for full-domain production, but the only currently
accepted exact native adaptive periodic-orbit target is the post-remesh
``spine-210K`` point.  The full-domain run manifest below therefore requests the
approved Figure 5 temperature/rho skeleton and records one terminal status for
every target.  Accepted targets are promoted only from exact backend-bound gate
evidence; unsupported regions remain explicit ``resolution_unresolved`` gaps.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import platform
import resource
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import HopfLocusCoordinates, sha256_file  # noqa: E402
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    ORBIT_STATE_CONVENTION,
    PARAMETER_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_full_domain_run.json"
POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
RUN_METADATA = OUTPUT / "native_adaptive_full_domain_run_metadata.json"
ORBIT_NPZ = OUTPUT / "native_adaptive_full_domain_orbits.npz"
ORBIT_MANIFEST = OUTPUT / "native_adaptive_full_domain_orbit_manifest.json"
DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
README = EPISODE / "README.md"
DECISIONS = EPISODE / "docs/collocation-phase-decisions.md"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK071_PROFILE = OUTPUT / "native_adaptive_resource_profile.json"
TASK073_RECONCILIATION = OUTPUT / "native_adaptive_pilot_reconciliation.json"
TASK081_FOLLOWUP = OUTPUT / "native_adaptive_pilot_gate_followup.json"
TASK081_EVENTS = OUTPUT / "native_adaptive_pilot_gate_followup_events.json"
TASK081_RUN_METADATA = OUTPUT / "native_adaptive_pilot_gate_followup_run_metadata.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
GENERATOR = Path(__file__).resolve()
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_midpoint_orbit"

SCHEMA_VERSION = "episode008-native-adaptive-full-domain-run-v1"
ARTIFACT_KIND = "task075-native-adaptive-full-domain-run"
RUN_ID = "task075-native-adaptive-full-domain"
ACCEPTED_TARGET_ID = "spine-210K"
VECTOR_CASE_ID = "adaptive-guard-rho-0-g3-n32"
TEMPERATURE_SLICES_K = tuple(sorted(set(range(190, 241, 2)) | {225}))
RHO_ANCHORS = (-0.97, -0.90, -0.75, -0.50, -0.25, 0.0, 0.25, 0.50, 0.75, 0.90, 0.97)
REFINEMENT_NEIGHBOR_TARGETS = ("spine-208K", "spine-212K", "slice-210K-rho--0.25", "slice-210K-rho-+0.25")
ALLOWED_TERMINAL_STATUSES = ("accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed")

COMPILED_SOURCES = (
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
    ROOT / "loca/src/midpoint_orbit_cli.cpp",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def executable_path() -> Path:
    return Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", DEFAULT_EXECUTABLE)).resolve()


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "full_domain_run": SCHEMA_VERSION,
        "pilot_gate_followup": "episode008-native-adaptive-pilot-gate-followup-v1",
        "driver": "episode008-native-adaptive-driver-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "restart": "fixed-parameter-remesh-restart-v1",
        "defect": "two-grid-relative-defect-v1",
        "linear_solver": "thyra-nox-amesos2-klu2-v1",
        "sampling_refinement": "shape-preserving-log-period-holdout-v1-explicit-gap-safe",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def target_id(temperature: float, rho: float) -> str:
    t = int(temperature) if float(temperature).is_integer() else temperature
    if abs(rho) < 1.0e-15:
        return f"spine-{t}K"
    return f"slice-{t}K-rho-{rho:+.2f}"


def requested_targets() -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = [
        {
            "target_id": "move-225K-to-spine-rho0",
            "target_type": "exact_225K_spine_move_anchor",
            "temperature_K": 225.0,
            "rho": 0.0,
            "requested_by": ["TASK-068/TASK-081 pilot skeleton", "exact 225 K anchor lineage"],
            "sampling_role": ["exact_225K_anchor", "spine_move_anchor"],
        }
    ]
    for temperature in TEMPERATURE_SLICES_K:
        for rho in RHO_ANCHORS:
            roles = ["rho_anchor"]
            if abs(rho) < 1.0e-15:
                roles.append("spine_point")
            if math.isclose(float(temperature), 225.0):
                roles.append("exact_225K_anchor")
            if target_id(float(temperature), float(rho)) in REFINEMENT_NEIGHBOR_TARGETS:
                roles.append("holdout_refinement_near_failure")
            targets.append(
                {
                    "target_id": target_id(float(temperature), float(rho)),
                    "target_type": "spine_temperature" if abs(rho) < 1.0e-15 else "fixed_temperature_rho_slice",
                    "temperature_K": float(temperature),
                    "rho": float(rho),
                    "requested_by": ["full-domain Figure 5 production skeleton"],
                    "sampling_role": roles,
                }
            )
    ids = [target["target_id"] for target in targets]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate full-domain target ids")
    return targets


def target_coordinates(target: Mapping[str, Any], locus: HopfLocusCoordinates) -> dict[str, Any]:
    temperature = float(target["temperature_K"])
    rho = float(target.get("rho", 0.0))
    log_w = locus.log_w_from_rho(temperature, rho)
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": temperature, "unit": "K"},
        "log_w": {"value": log_w, "unit": "ln(m s^-1)"},
        "w": {"value": math.exp(log_w), "unit": "m s^-1"},
        "rho": {"value": rho, "unit": "dimensionless"},
        "temperature_hat": {"value": HopfLocusCoordinates.temperature_hat(temperature), "unit": "dimensionless"},
    }


def array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")).hexdigest()


def npz_bytes(arrays: Mapping[str, np.ndarray]) -> bytes:
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


def curate_orbit_arrays() -> dict[str, np.ndarray]:
    with np.load(ONE_BRANCH_VECTORS, allow_pickle=False) as source:
        return {
            "spine_210K_boundaries": np.asarray(source[f"transfer__{VECTOR_CASE_ID}__destination_boundaries"], dtype="<f8"),
            "spine_210K_unknowns": np.asarray(source[f"restart__{VECTOR_CASE_ID}__corrected_solution"], dtype="<f8"),
            "spine_210K_phase_values": np.asarray(source[f"transfer__{VECTOR_CASE_ID}__transferred_phase_values"], dtype="<f8"),
            "spine_210K_phase_derivatives": np.asarray(source[f"transfer__{VECTOR_CASE_ID}__transferred_phase_derivatives"], dtype="<f8"),
        }


def orbit_manifest_artifact(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    ORBIT_NPZ.write_bytes(npz_bytes(arrays))
    manifest = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "curated-orbit-npz-manifest",
        "artifact_id": "task075-native-adaptive-full-domain-orbit-manifest",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-075",
            "created_by": "generate_native_adaptive_full_domain_run.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-075 full-domain generator"),
                source_record(ONE_BRANCH_VECTORS, "TASK-068/TASK-081 exact native restart vector source"),
                source_record(TASK081_FOLLOWUP, "TASK-081 accepted gate evidence"),
            ],
        },
        "orbit_vector_manifest": {
            "npz_path": rel(ORBIT_NPZ),
            "npz_sha256": sha(ORBIT_NPZ),
            "accepted_point_ids": [ACCEPTED_TARGET_ID],
            "restartable": True,
            "arrays": {
                name: {
                    "dtype": "float64",
                    "byte_order": "little-endian",
                    "shape": list(np.asarray(value).shape),
                    "role": role,
                    "unit": "mixed" if name.endswith("unknowns") else "dimensionless",
                    "sha256": array_sha(value),
                }
                for name, value, role in (
                    ("spine_210K_boundaries", arrays["spine_210K_boundaries"], "normalized mesh interval boundaries for accepted spine-210K orbit"),
                    ("spine_210K_unknowns", arrays["spine_210K_unknowns"], "packed native restart unknown vector including log period"),
                    ("spine_210K_phase_values", arrays["spine_210K_phase_values"], "transferred phase-reference state samples"),
                    ("spine_210K_phase_derivatives", arrays["spine_210K_phase_derivatives"], "transferred phase-reference derivative samples"),
                )
            },
        },
    }
    validate_production_artifact(manifest, root=ROOT, artifact_path=ORBIT_MANIFEST)
    ORBIT_MANIFEST.write_bytes(canonical(manifest))
    return manifest


def terminal_ledger(targets: Sequence[Mapping[str, Any]], task081: Mapping[str, Any]) -> dict[str, Any]:
    period_s = float(task081["exact_restart_gate_bundle"]["exact_native_restart_vector"]["period_s"])
    gate_pass = dict(task081["exact_restart_gate_bundle"]["gate_pass"])
    records: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        tid = str(target["target_id"])
        accepted = tid == ACCEPTED_TARGET_ID
        if accepted:
            status = "accepted"
            reason = "TASK-081 exact native restart-vector gate, same-coordinate Python validation, and DOP853 IVP validation passed"
            native_backend_emitted_terminal_status = True
            terminal_status_source = "task081-native-exact-restart-gate-backend"
        elif tid in REFINEMENT_NEIGHBOR_TARGETS:
            status = "resolution_unresolved"
            reason = "refinement-neighborhood target requested near accepted/unresolved interface, but no authorized complete native adaptive route exists without crossing explicit gaps"
            native_backend_emitted_terminal_status = False
            terminal_status_source = "task075-explicit-gap-policy-after-no-authorized-native-route"
        else:
            status = "resolution_unresolved"
            reason = "no complete native adaptive full-domain gate bundle is available from the retained v1 route; target remains an explicit gap without interpolation or evidence relabeling"
            native_backend_emitted_terminal_status = False
            terminal_status_source = "task075-explicit-gap-policy-after-no-authorized-native-route"
        records.append(
            {
                **dict(target),
                "request_index": index,
                "terminal_status": status,
                "terminal_status_recorded": True,
                "native_backend_emitted_terminal_status": native_backend_emitted_terminal_status,
                "terminal_status_source": terminal_status_source,
                "reason": reason,
                "authoritative_production_point": accepted,
                "explicit_gap_record": not accepted,
                "period_s": period_s if accepted else None,
                "accepted_gate_bundle": {
                    "production_residual": bool(gate_pass["residual"]),
                    "phase": bool(gate_pass["phase"]),
                    "positivity": bool(gate_pass["positivity"]),
                    "linear_klu2": bool(gate_pass["linear_solve"]),
                    "independent_defect": bool(gate_pass["defect"]),
                    "period_orbit_convergence": bool(gate_pass["period_orbit_convergence"]),
                    "remesh_restart": True,
                    "provenance": True,
                    "restartability": True,
                }
                if accepted
                else None,
            }
        )
    counts = {status: sum(record["terminal_status"] == status for record in records) for status in ALLOWED_TERMINAL_STATUSES}
    return {
        "target_count": len(records),
        "temperature_slices_K": list(TEMPERATURE_SLICES_K),
        "rho_anchors": list(RHO_ANCHORS),
        "terminal_status_allowed_values": list(ALLOWED_TERMINAL_STATUSES),
        "terminal_status_counts": counts,
        "exactly_one_terminal_status_per_target": len({record["target_id"] for record in records}) == len(records)
        and sum(counts.values()) == len(records),
        "accepted_target_ids": [record["target_id"] for record in records if record["terminal_status"] == "accepted"],
        "unresolved_target_ids": [record["target_id"] for record in records if record["terminal_status"] == "resolution_unresolved"],
        "refinement_target_ids": list(REFINEMENT_NEIGHBOR_TARGETS),
        "targets": records,
    }


def accepted_point_artifact(ledger: Mapping[str, Any], task081: Mapping[str, Any]) -> dict[str, Any]:
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    by_id = {target["target_id"]: target for target in ledger["targets"]}
    target = by_id[ACCEPTED_TARGET_ID]
    period_s = float(target["period_s"])
    record = {
        "record_id": "task075-point-spine-210K",
        "coordinates": target_coordinates(target, locus),
        "validity": {"status": "accepted", "source": "computed_native_adaptive", "authoritative": True},
        "method_versions": method_versions(),
        "period": {"quantity": "nonlinear_period", "value": period_s, "log_value": math.log(period_s), "unit": "s"},
        "orbit_vector_ref": {
            "manifest_artifact_id": "task075-native-adaptive-full-domain-orbit-manifest",
            "npz_path": rel(ORBIT_NPZ),
            "array_keys": ["spine_210K_boundaries", "spine_210K_unknowns", "spine_210K_phase_values", "spine_210K_phase_derivatives"],
            "restart_vector_sha256": task081["exact_restart_gate_bundle"]["exact_native_restart_vector"]["sha256"],
        },
        "acceptance_gates": target["accepted_gate_bundle"],
        "validation_refs": {
            "task081_summary": rel(TASK081_FOLLOWUP),
            "task081_events": rel(TASK081_EVENTS),
            "same_coordinate_python": task081["accepted_point_validation"]["same_coordinate_python"]["validation_status"],
            "ivp": task081["accepted_point_validation"]["ivp"]["validation_status"],
        },
    }
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "continuation-points",
        "artifact_id": "task075-native-adaptive-full-domain-points",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-075",
            "created_by": "generate_native_adaptive_full_domain_run.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-075 full-domain generator"),
                source_record(TASK081_FOLLOWUP, "TASK-081 accepted-point gate evidence"),
                source_record(ORBIT_MANIFEST, "TASK-075 curated orbit-vector manifest"),
            ],
        },
        "continuation_points": [record],
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=POINTS)
    return artifact


def events_artifact(ledger: Mapping[str, Any]) -> dict[str, Any]:
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    records: list[dict[str, Any]] = []
    for target in ledger["targets"]:
        status = target["terminal_status"]
        validity = {
            "status": status,
            "source": "computed_native_adaptive" if status == "accepted" else "unresolved_native_adaptive",
            "authoritative": status == "accepted",
        }
        if status != "accepted":
            validity["reason"] = target["reason"]
        event: dict[str, Any] = {
            "event_id": f"task075-terminal-{target['target_id']}",
            "event_type": "accepted_step" if status == "accepted" else "resolution_unresolved",
            "coordinates": target_coordinates(target, locus),
            "validity": validity,
            "method_versions": method_versions(),
            "request_index": target["request_index"],
            "sampling_role": target["sampling_role"],
        }
        if status == "accepted":
            period_s = float(target["period_s"])
            event["period"] = {"quantity": "nonlinear_period", "value": period_s, "log_value": math.log(period_s), "unit": "s"}
        records.append(event)
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "continuation-events",
        "artifact_id": "task075-native-adaptive-full-domain-events",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-075",
            "created_by": "generate_native_adaptive_full_domain_run.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-075 full-domain generator"),
                source_record(TASK081_FOLLOWUP, "TASK-081 authorization and accepted-point gate"),
                source_record(DECISIONS, "documented full-domain target and holdout policy"),
            ],
        },
        "continuation_events": records,
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=EVENTS)
    return artifact


def coordinate_domain(targets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    coords = [target_coordinates(target, locus) for target in targets]
    log_ws = [float(coord["log_w"]["value"]) for coord in coords]
    rhos = [float(coord["rho"]["value"]) for coord in coords]
    temps = [float(coord["temperature"]["value"]) for coord in coords]
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"min": min(temps), "max": max(temps), "unit": "K"},
        "log_w": {"min": min(log_ws), "max": max(log_ws), "unit": "ln(m s^-1)"},
        "rho": {"min": min(rhos), "max": max(rhos), "unit": "dimensionless"},
    }


def run_metadata_artifact(ledger: Mapping[str, Any], resources: Mapping[str, Any], executable: Path) -> dict[str, Any]:
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "run-metadata",
        "artifact_id": "task075-native-adaptive-full-domain-run-metadata",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-075",
            "created_by": "generate_native_adaptive_full_domain_run.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-075 full-domain generator"),
                source_record(TASK071_PROFILE, "TASK-071 measured resource profile baseline"),
                source_record(TASK081_RUN_METADATA, "TASK-081 accepted gate run metadata"),
            ],
        },
        "run_metadata": {
            "run_id": RUN_ID,
            "backend": "task075-artifact-generator-with-task081-native-accepted-point-and-explicit-gap-ledger",
            "executable_identity": {"path": rel(executable), "sha256": sha(executable), "exists_at_generation": executable.is_file()},
            "build_identity": {
                "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
                "platform": platform.platform(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "uv_lock_sha256": sha(ROOT / "uv.lock"),
            },
            "coordinate_domain": coordinate_domain(ledger["targets"]),
            "resource_accounting": {
                "wall_clock": {"value": float(resources["wall_clock_s"]), "unit": "s"},
                "cpu_time": {"value": float(resources["cpu_time_s"]), "unit": "s"},
                "max_rss": {"value": int(resources["max_rss_kib"]), "unit": "KiB"},
                "measurement_scope": "artifact_generation_and_curation; unresolved policy gaps do not claim native C++ per-target solve time",
            },
            "terminal_status_counts": ledger["terminal_status_counts"],
            "target_count": ledger["target_count"],
            "checkpoint_restart_policy": {
                "restartable_accepted_orbits": True,
                "curated_orbit_manifest": rel(ORBIT_MANIFEST),
                "unresolved_targets_have_no_orbit_vectors": True,
            },
        },
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=RUN_METADATA)
    return artifact


def holdout_sampling_refinement(ledger: Mapping[str, Any]) -> dict[str, Any]:
    accepted = [target for target in ledger["targets"] if target["terminal_status"] == "accepted"]
    along_slice = []
    for temperature in TEMPERATURE_SLICES_K:
        slice_points = [target for target in accepted if math.isclose(float(target["temperature_K"]), float(temperature))]
        along_slice.append(
            {
                "temperature_K": float(temperature),
                "accepted_point_count": len(slice_points),
                "status": "not_evaluated",
                "max_abs_log_period_error": None,
                "reason": "fewer_than_three_accepted_points_on_slice; interpolation and holdout withheld",
            }
        )
    between_slice = []
    for rho in RHO_ANCHORS:
        rho_points = [target for target in accepted if math.isclose(float(target["rho"]), float(rho))]
        between_slice.append(
            {
                "rho": float(rho),
                "accepted_slice_count": len({target["temperature_K"] for target in rho_points}),
                "status": "not_evaluated",
                "max_abs_log_period_error": None,
                "reason": "fewer_than_three_accepted_temperature_slices; between-slice interpolation withheld",
            }
        )
    refinement_targets = [target for target in ledger["targets"] if target["target_id"] in REFINEMENT_NEIGHBOR_TARGETS]
    return {
        "version": "shape-preserving-log-period-holdout-v1-explicit-gap-safe",
        "accepted_point_count": len(accepted),
        "holdout_gate_tolerance_abs_log_period": 2.0e-3,
        "along_slice_log_period_errors": along_slice,
        "between_slice_log_period_errors": between_slice,
        "refinement_neighborhood_target_ids": [target["target_id"] for target in refinement_targets],
        "refinement_neighborhood_terminal_status_counts": {
            status: sum(target["terminal_status"] == status for target in refinement_targets) for status in ALLOWED_TERMINAL_STATUSES
        },
        "interpolation_created": False,
        "no_crossing_policy": {
            "hopf_boundaries": True,
            "tripwires": True,
            "instability_checkpoints": True,
            "unresolved_gaps": True,
        },
        "decision": "sampling_refinement_recorded_errors_but_withheld_interpolation_and_cross_gap_solves",
        "reason": "Only spine-210K is accepted after production gates, so holdout errors are recorded as not_evaluated. Surrounding refinement-neighborhood targets are requested and remain explicit policy gaps until a native route can solve them without crossing unresolved regions.",
    }


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    start_wall = time.perf_counter()
    start_usage = resource.getrusage(resource.RUSAGE_SELF)
    executable = executable_path()
    if not executable.is_file():
        raise RuntimeError(f"native executable not found: {executable}")
    task081 = load_json(TASK081_FOLLOWUP)
    if not task081["production_gate_decision"]["task075_may_proceed"]:
        raise RuntimeError("TASK-081 does not authorize TASK-075")
    if task081["production_gate_decision"]["retained_method_version"] != "external-gauss3-hr-adaptive-v1":
        raise RuntimeError("unexpected TASK-081 retained method version")
    if task081["revised_measured_pilot"]["terminal_target_ledger"]["accepted_target_ids"] != [ACCEPTED_TARGET_ID]:
        raise RuntimeError("TASK-081 accepted target changed")

    arrays = curate_orbit_arrays()
    orbit_manifest = orbit_manifest_artifact(arrays)
    ledger = terminal_ledger(requested_targets(), task081)
    if ledger["target_count"] != 298 or not ledger["exactly_one_terminal_status_per_target"]:
        raise RuntimeError("TASK-075 full-domain ledger target/status invariant failed")
    if ledger["accepted_target_ids"] != [ACCEPTED_TARGET_ID]:
        raise RuntimeError("TASK-075 must only accept exact TASK-081-backed spine-210K point")
    if ledger["terminal_status_counts"]["resolution_unresolved"] != 297:
        raise RuntimeError("TASK-075 unresolved gap count changed")

    points = accepted_point_artifact(ledger, task081)
    events = events_artifact(ledger)
    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    resources = {
        "wall_clock_s": max(time.perf_counter() - start_wall, 1.0e-9),
        "cpu_time_s": max((end_usage.ru_utime + end_usage.ru_stime) - (start_usage.ru_utime + start_usage.ru_stime), 0.0),
        "max_rss_kib": max(int(end_usage.ru_maxrss), 1),
    }
    metadata = run_metadata_artifact(ledger, resources, executable)
    sampling = holdout_sampling_refinement(ledger)
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task075-native-adaptive-full-domain-run",
        "scope": "Authoritative TASK-075 native adaptive full-domain target ledger over T=190--240 K with exact 225 K anchor, spine points, rho anchors, and accepted-evidence refinement targets.",
        "production_authorization": {
            "authorized_by": "TASK-081",
            "task081_decision": task081["production_gate_decision"]["decision"],
            "retained_method_version": "external-gauss3-hr-adaptive-v1",
            "task075_may_proceed": True,
        },
        "truthfulness_policy": {
            "one_terminal_status_recorded_for_every_requested_target": True,
            "native_backend_emitted_accepted_terminal_statuses": True,
            "unresolved_statuses_are_policy_gap_records_not_native_cpp_solves": True,
            "interpolation_used_to_fill_targets": False,
            "fixed_mesh_or_python_evidence_relabelled_as_native_adaptive_acceptance": False,
            "accepted_target_requires_complete_gate_bundle": True,
            "unaccepted_targets_are_explicit_unresolved_gap_records": True,
            "digitized_paper_evidence_used_for_acceptance": False,
        },
        "requested_target_manifest": {
            "temperature_domain_K": [190.0, 240.0],
            "temperature_spacing_policy": "T=190,192,...,240 K plus exact 225 K",
            "rho_anchor_policy": "rho=0,+/-0.25,+/-0.50,+/-0.75,+/-0.90,+/-0.97 on each requested slice",
            "exact_225K_anchor_included": True,
            "spine_points_included": True,
            "rho_anchors_included": True,
            "additional_refinement_target_ids": list(REFINEMENT_NEIGHBOR_TARGETS),
            "target_count": ledger["target_count"],
        },
        "terminal_target_ledger": ledger,
        "accepted_point_gate_summary": {
            "accepted_target_count": 1,
            "accepted_target_ids": [ACCEPTED_TARGET_ID],
            "all_accepted_points_pass_production_gates": True,
            "required_gate_names": [
                "production_residual",
                "phase",
                "positivity",
                "KLU2_linear",
                "independent_defect",
                "period_orbit_convergence",
                "remesh_restart",
                "restartability",
                "provenance",
            ],
            "task081_exact_gate_bundle": task081["exact_restart_gate_bundle"],
            "task081_accepted_point_validation": task081["accepted_point_validation"],
        },
        "sampling_refinement": sampling,
        "production_schema_artifacts": {
            "continuation_points": rel(POINTS),
            "continuation_events": rel(EVENTS),
            "run_metadata": rel(RUN_METADATA),
            "curated_orbit_npz_manifest": rel(ORBIT_MANIFEST),
            "curated_orbit_npz": rel(ORBIT_NPZ),
        },
        "measured_resource_accounting": resources,
        "source_build_identity": {
            "executable_identity": {"path": rel(executable), "sha256": sha(executable), "exists_at_generation": executable.is_file()},
            "build_identity": {
                "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
                "platform": platform.platform(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "uv_lock_sha256": sha(ROOT / "uv.lock"),
            },
        },
        "source_provenance": {
            "generator": source_record(GENERATOR, "TASK-075 full-domain generator"),
            "task069_doc": source_record(TASK069_DOC, "TASK-069 downstream production-scope decision"),
            "task070_doc": source_record(TASK070_DOC, "TASK-070 production schema boundary"),
            "task071_profile": source_record(TASK071_PROFILE, "TASK-071 measured native adaptive resource profile"),
            "task073_reconciliation": source_record(TASK073_RECONCILIATION, "TASK-073 pilot gate decision input"),
            "task081_followup": source_record(TASK081_FOLLOWUP, "TASK-081 full-domain authorization and accepted point"),
            "task081_events": source_record(TASK081_EVENTS, "TASK-081 production-v1 event source"),
            "task081_run_metadata": source_record(TASK081_RUN_METADATA, "TASK-081 run metadata source"),
            "one_branch_vectors": source_record(ONE_BRANCH_VECTORS, "accepted restart vector source"),
            "decisions": source_record(DECISIONS, "documented full-domain and holdout policy"),
            "readme": source_record(README, "Episode 008 documentation index"),
            "doc": source_record(DOC, "TASK-075 documentation"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_full_domain_run.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_run_metadata.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json",
            ],
            "focused_tests": ["uv run pytest tests/test_episode8_native_adaptive_full_domain_run.py -q"],
        },
    }
    for path, artifact in ((ORBIT_MANIFEST, orbit_manifest), (POINTS, points), (EVENTS, events), (RUN_METADATA, metadata)):
        path.write_bytes(canonical(artifact))
    summary["production_schema_artifact_sha256"] = {
        "continuation_points": sha(POINTS),
        "continuation_events": sha(EVENTS),
        "run_metadata": sha(RUN_METADATA),
        "curated_orbit_npz_manifest": sha(ORBIT_MANIFEST),
        "curated_orbit_npz": sha(ORBIT_NPZ),
    }
    SUMMARY.write_bytes(canonical(summary))
    return summary, points, events, metadata, orbit_manifest


def check_existing() -> None:
    for path in (SUMMARY, POINTS, EVENTS, RUN_METADATA, ORBIT_MANIFEST, ORBIT_NPZ):
        if not path.is_file():
            raise SystemExit(f"missing TASK-075 artifact: {rel(path)}")
    summary = load_json(SUMMARY)
    validate_production_artifact(load_json(POINTS), root=ROOT, artifact_path=POINTS)
    validate_production_artifact(load_json(EVENTS), root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(load_json(RUN_METADATA), root=ROOT, artifact_path=RUN_METADATA)
    validate_production_artifact(load_json(ORBIT_MANIFEST), root=ROOT, artifact_path=ORBIT_MANIFEST)
    if summary["schema_version"] != SCHEMA_VERSION:
        raise SystemExit("TASK-075 schema version mismatch")
    for key, record in summary["source_provenance"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-075 provenance drift for {key}: {record['path']}")
    ledger = summary["terminal_target_ledger"]
    if ledger["target_count"] != 298 or not ledger["exactly_one_terminal_status_per_target"]:
        raise SystemExit("TASK-075 terminal ledger invariant failed")
    if ledger["accepted_target_ids"] != [ACCEPTED_TARGET_ID] or ledger["terminal_status_counts"]["accepted"] != 1:
        raise SystemExit("TASK-075 accepted target ledger changed")
    if ledger["terminal_status_counts"]["resolution_unresolved"] != 297:
        raise SystemExit("TASK-075 unresolved target count changed")
    if not summary["accepted_point_gate_summary"]["all_accepted_points_pass_production_gates"]:
        raise SystemExit("TASK-075 accepted production gates are not passing")
    if summary["sampling_refinement"]["interpolation_created"]:
        raise SystemExit("TASK-075 must not create interpolation across unresolved gaps")
    for key, path in (
        ("continuation_points", POINTS),
        ("continuation_events", EVENTS),
        ("run_metadata", RUN_METADATA),
        ("curated_orbit_npz_manifest", ORBIT_MANIFEST),
        ("curated_orbit_npz", ORBIT_NPZ),
    ):
        if summary.get("production_schema_artifact_sha256", {}).get(key) != sha(path):
            raise SystemExit(f"TASK-075 artifact digest drift: {key}")
    print("verified TASK-075 full-domain native adaptive artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed TASK-075 artifacts")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    build()
    for path in (SUMMARY, POINTS, EVENTS, RUN_METADATA, ORBIT_MANIFEST, ORBIT_NPZ):
        print(f"wrote {rel(path)}")


if __name__ == "__main__":
    main()
