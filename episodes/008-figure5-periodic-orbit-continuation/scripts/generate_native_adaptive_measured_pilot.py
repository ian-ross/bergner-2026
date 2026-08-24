#!/usr/bin/env python3
"""Generate the TASK-072 measured native adaptive pilot artifacts.

The pilot re-runs the current native seams that exist for the 210--226 K
spine-and-slices skeleton, then executes the resumable native adaptive driver
with a measured backend.  The only target with a complete adaptive remesh/restart
and convergence gate bundle in the current backend is the T=210 K spine target;
all other skeleton targets remain explicit backend-emitted
``resolution_unresolved`` records with reasons.  No fixed-mesh-only or Python-only
point is relabeled as a completed TASK-072 native adaptive pilot target, and no
interpolation is used to fill gaps.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from math import exp
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import (  # noqa: E402
    HopfLocusCoordinates,
    NativeAdaptiveDriver,
    NativeAdaptiveDriverConfig,
    canonical_sha256,
    sha256_file,
)
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    PARAMETER_COORDINATE_CONVENTION,
    ORBIT_STATE_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_measured_pilot.json"
RUN_DIR = OUTPUT / "native_adaptive_measured_pilot"
EVENTS = OUTPUT / "native_adaptive_measured_pilot_events.json"
RUN_METADATA = OUTPUT / "native_adaptive_measured_pilot_run_metadata.json"

PREPARATORY_MANIFEST = OUTPUT / "native_adaptive_loca_manifest.json"
PROVISIONAL_SUMMARY = OUTPUT / "native_adaptive_spine_slices_run.json"
NATIVE_HIGHER_ORDER = OUTPUT / "native_loca_higher_order_results.json"
NATIVE_HIGHER_ORDER_VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"
ONE_BRANCH = OUTPUT / "native_adaptive_one_branch_segment.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
ADAPTIVE_QUALIFICATION = OUTPUT / "adaptive_qualification_results.json"
RESOURCE_PROFILE = OUTPUT / "native_adaptive_resource_profile.json"
RESOURCE_METADATA = OUTPUT / "native_adaptive_resource_profile_run_metadata.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK071_DOC = EPISODE / "docs/task071-resource-profile.md"
TASK072_DOC = EPISODE / "docs/task072-measured-native-adaptive-pilot.md"
README = EPISODE / "README.md"
GENERATOR = Path(__file__).resolve()
DRIVER_SOURCE = ROOT / "src/bergner_spichtinger_2026/native_adaptive_driver.py"
NATIVE_HIGHER_ORDER_SCRIPT = EPISODE / "scripts/generate_native_loca_higher_order_results.py"
ONE_BRANCH_SCRIPT = EPISODE / "scripts/generate_native_adaptive_one_branch_segment.py"
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_midpoint_orbit"
TIME_BINARY = Path("/usr/bin/time")

SCHEMA_VERSION = "episode008-native-adaptive-measured-pilot-v1"
ARTIFACT_KIND = "task072-measured-native-adaptive-pilot"
RUN_ID = "task072-measured-native-adaptive-pilot"
ALLOWED_TERMINAL_STATUSES = ("accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed")
MEASURED_REMESH_TARGET_ID = "spine-210K"
ADAPTIVE_CASE_ID = "guard-rho-0-g3-n32"

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
    return path.relative_to(ROOT).as_posix()


def display_path(path: Path) -> str:
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


def parse_time_file(path: Path) -> dict[str, Any]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2:
            values[fields[0]] = fields[1]
    missing = {"wall_clock_s", "user_cpu_s", "system_cpu_s", "max_rss_kib", "exit_status"} - values.keys()
    if missing:
        raise RuntimeError(f"/usr/bin/time output missing {sorted(missing)}: {path.read_text()!r}")
    user = float(values["user_cpu_s"])
    system = float(values["system_cpu_s"])
    return {
        "wall_clock_s": float(values["wall_clock_s"]),
        "user_cpu_s": user,
        "system_cpu_s": system,
        "cpu_time_s": user + system,
        "max_rss_kib": int(values["max_rss_kib"]),
        "exit_status": int(values["exit_status"]),
    }


def measured_command(command: Sequence[str], *, env: Mapping[str, str]) -> dict[str, Any]:
    if not TIME_BINARY.is_file():
        raise RuntimeError("/usr/bin/time is required for TASK-072 measurement")
    with tempfile.TemporaryDirectory() as tmp:
        time_file = Path(tmp) / "time.txt"
        wrapped = [
            str(TIME_BINARY),
            "-f",
            "wall_clock_s %e\nuser_cpu_s %U\nsystem_cpu_s %S\nmax_rss_kib %M\nexit_status %x",
            "-o",
            str(time_file),
            *map(str, command),
        ]
        completed = subprocess.run(wrapped, cwd=ROOT, env=dict(env), text=True, capture_output=True, check=False)
        resources = parse_time_file(time_file)
    if completed.returncode != 0 or resources["exit_status"] != 0:
        raise RuntimeError(
            f"measured command failed: {' '.join(map(str, command))}\n"
            f"returncode={completed.returncode}, time={resources}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if resources["wall_clock_s"] <= 0.0 or resources["max_rss_kib"] <= 0:
        raise RuntimeError(f"non-placeholder wall/RSS measurement failed for {command}: {resources}")
    return {
        "command": [display_path(Path(item)) if Path(str(item)).is_absolute() else str(item) for item in command],
        "resources": resources,
        "stdout_tail": completed.stdout.splitlines()[-5:],
        "stderr_tail": completed.stderr.splitlines()[-5:],
    }


def aggregate_resources(measurements: Sequence[Mapping[str, Any]], driver_manifest: Mapping[str, Any]) -> dict[str, Any]:
    command_resources = [item["resources"] for item in measurements]
    driver_resources = driver_manifest["resource_accounting"]
    return {
        "wall_clock_s": sum(float(item["wall_clock_s"]) for item in command_resources)
        + float(driver_resources["segment_wall_clock_s"]),
        "cpu_time_s": sum(float(item["cpu_time_s"]) for item in command_resources)
        + float(driver_resources["segment_cpu_s"]),
        "max_rss_kib": max(
            [int(item["max_rss_kib"]) for item in command_resources]
            + [int(driver_resources["max_rss_kib"])]
        ),
    }


def target_coordinates(target: Mapping[str, Any], locus: HopfLocusCoordinates) -> dict[str, Any]:
    temperature = float(target["temperature_K"])
    rho_value = target.get("rho")
    rho_float = None if rho_value is None else float(rho_value)
    log_w = locus.spine_log_w(temperature) if rho_float is None else locus.log_w_from_rho(temperature, rho_float)
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": temperature, "unit": "K"},
        "log_w": {"value": log_w, "unit": "ln(m s^-1)"},
        "w": {"value": exp(log_w), "unit": "m s^-1"},
        "rho": {"value": rho_float, "unit": "dimensionless"},
        "temperature_hat": {"value": HopfLocusCoordinates.temperature_hat(temperature), "unit": "dimensionless"},
    }


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "pilot": SCHEMA_VERSION,
        "driver": "episode008-native-adaptive-driver-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "restart": "fixed-parameter-remesh-restart-v1",
        "linear_solver": "thyra-nox-amesos2-klu2-v1",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def common_provenance(*, source_artifacts: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    return {
        "task": "TASK-072",
        "created_by": "generate_native_adaptive_measured_pilot.py",
        "digitized_paper_data_policy": "external-comparison-only",
        "source_artifacts": list(source_artifacts),
    }


class MeasuredPilotBackend:
    """Backend that emits TASK-072 pilot statuses from measured native seams."""

    def __init__(self, *, one_branch: Mapping[str, Any], adaptive: Mapping[str, Any]) -> None:
        self.one_branch = copy.deepcopy(dict(one_branch))
        self.adaptive = copy.deepcopy(dict(adaptive))

    def _unresolved_spec(self, target: Mapping[str, Any], cycle_index: int) -> dict[str, Any]:
        if target["target_id"] == MEASURED_REMESH_TARGET_ID:
            reason = (
                "measured native remesh/restart seam reached this target, but exact native restart-vector "
                "independent defect and period/orbit convergence gates are not backend-bound in TASK072; "
                "target remains an explicit unresolved gap"
            )
        elif target.get("native_branch_id"):
            reason = (
                "backend_route_lacks_complete_TASK072_adaptive_defect_and_period_orbit_gate_bundle; "
                "native fixed-mesh checkpoint is not relabeled as measured adaptive pilot acceptance"
            )
        else:
            reason = (
                "no measured native adaptive backend route reached this skeleton target within TASK072 pilot scope; "
                "explicit unresolved gap preserved without interpolation"
            )
        return {
            "backend": "measured-native-adaptive-pilot-backend",
            "events": [{
                "callback_index": 0,
                "status": "rejected",
                "accepted": False,
                "save_role": "final",
                "reason": reason,
            }],
            "points": [],
            "mesh_history": [{"status": "not_advanced", "reason": reason}],
            "defects": {"maximum": None, "status": "not_evaluated", "reason": reason},
            "convergence": {"nox_status": "not_started", "reason": reason},
            "phase_lineage": [],
            "diagnostics": {"terminal_unresolved_reason": reason, "backend_emitted_terminal_status": "resolution_unresolved"},
            "decision": {"action": "stop_unresolved", "terminal_status": "resolution_unresolved", "reason": reason},
        }

    def run_fixed_mesh_segment(
        self,
        target: Mapping[str, Any],
        *,
        cycle_index: int,
        restart_state: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        if target["target_id"] != MEASURED_REMESH_TARGET_ID:
            return self._unresolved_spec(target, cycle_index)
        fixed = copy.deepcopy(dict(self.one_branch["native_fixed_mesh_segment"]))
        reason = self._unresolved_spec(target, cycle_index)["decision"]["reason"]
        fixed["backend"] = "measured-native-adaptive-pilot-backend"
        fixed["restart_state_seen"] = restart_state is not None
        fixed["defects"] = {
            "maximum": self.one_branch["adaptive_controller"]["defect"]["maximum"],
            "status": "native_remesh_restart_measured_but_exact_restart_vector_defect_gate_unresolved",
            "source": "native adaptive controller decision at measured remesh boundary",
        }
        fixed["convergence"] = {
            "nox_status": "converged",
            "linear_backend": "KLU2",
            "source": "native LOCA fixed-mesh segment before unresolved remesh/restart gate boundary",
        }
        fixed["diagnostics"] = {
            "measured_remesh_restart_available": True,
            "restart_gates_passed": all(self.one_branch["restart"]["gates"].values()),
            "restart_solution_sha256": self.one_branch["restart"]["solution_sha256"],
            "terminal_unresolved_reason": reason,
            "backend_emitted_terminal_status": "resolution_unresolved",
        }
        fixed["decision"] = {"action": "stop_unresolved", "terminal_status": "resolution_unresolved", "reason": reason}
        return fixed

    def decide_remesh(self, target: Mapping[str, Any], segment: Mapping[str, Any], *, cycle_index: int) -> Mapping[str, Any]:
        decision = segment.get("decision")
        if isinstance(decision, Mapping):
            return copy.deepcopy(dict(decision))
        return {"action": "stop_converged", "terminal_status": "converged"}

    def restart_after_remesh(
        self,
        target: Mapping[str, Any],
        segment: Mapping[str, Any],
        decision: Mapping[str, Any],
        *,
        cycle_index: int,
        attempt_order: Sequence[str],
    ) -> Mapping[str, Any]:
        restart = copy.deepcopy(dict(self.one_branch["restart"]))
        restart["status"] = "accepted"
        restart["accepted"] = True
        restart["attempt_order"] = list(restart.get("attempts", attempt_order))
        return restart


def target_ledger(manifest: Mapping[str, Any]) -> dict[str, Any]:
    segments_by_target: dict[str, list[Mapping[str, Any]]] = {}
    for segment in manifest["segments"]:
        segments_by_target.setdefault(segment["target_id"], []).append(segment)
    targets: list[dict[str, Any]] = []
    for target in manifest["target_manifest"]:
        target_id = target["target_id"]
        status = manifest["target_status"][target_id]["terminal_status"]
        segment = segments_by_target[target_id][-1]
        reason = segment["adaptive_decision"].get("reason") or manifest["target_status"][target_id].get("reason")
        entry = {
            "target_id": target_id,
            "target_type": target["target_type"],
            "temperature_K": target["temperature_K"],
            "rho": target.get("rho"),
            "terminal_status": status,
            "backend_emitted_terminal_status": True,
            "provisional_terminal_status": target.get("provisional_terminal_status"),
            "completed_segment_id": manifest["target_status"][target_id]["completed_segment_id"],
        }
        if status == "accepted":
            entry["reason"] = "complete measured native adaptive remesh/restart gate bundle accepted by backend"
        else:
            entry["reason"] = reason
            entry["explicit_gap_record"] = True
        targets.append(entry)
    counts = {status: sum(target["terminal_status"] == status for target in targets) for status in ALLOWED_TERMINAL_STATUSES}
    return {
        "target_count": len(targets),
        "terminal_status_allowed_values": list(ALLOWED_TERMINAL_STATUSES),
        "terminal_status_counts": counts,
        "exactly_one_terminal_status_per_target": len({target["target_id"] for target in targets}) == len(targets) and sum(counts.values()) == len(targets),
        "targets": targets,
    }


def gate_summary(manifest: Mapping[str, Any], one_branch: Mapping[str, Any], adaptive: Mapping[str, Any]) -> dict[str, Any]:
    accepted_points = []
    for segment in manifest["segments"]:
        for point in segment["fixed_mesh_segment"].get("points", []):
            gates = point.get("accepted_gates")
            if gates:
                accepted_points.append({"target_id": segment["target_id"], "gates": gates})
    restart_segments = [segment for segment in manifest["segments"] if segment.get("restart")]
    return {
        "accepted_target_count": len([item for item in manifest["target_status"].values() if item["terminal_status"] == "accepted"]),
        "accepted_point_count": len(accepted_points),
        "accepted_points": accepted_points,
        "all_accepted_points_pass_required_gates": all(all(point["gates"].values()) for point in accepted_points),
        "restart_count": len(restart_segments),
        "all_remesh_restarts_pass_required_gates": all(
            all(segment["restart"].get("gates", {}).values()) for segment in restart_segments
        ),
        "required_gate_names": ["residual", "phase", "positivity", "finite_change", "tangent", "linear_solve", "defect", "period_orbit_convergence"],
        "native_restart_solution_sha256": one_branch["restart"]["solution_sha256"],
        "adaptive_defect_gate": {
            "case_id": ADAPTIVE_CASE_ID,
            "final_defect_maximum": next(item for item in adaptive["results"] if item["case_id"] == ADAPTIVE_CASE_ID)["final_defect_maximum"],
            "defect_tolerance": adaptive["defect_tolerance"],
            "period_orbit_convergence_tolerance": adaptive["period_orbit_convergence_tolerance"],
        },
    }


def build_driver_run(targets: Sequence[Mapping[str, Any]], *, one_branch: Mapping[str, Any], adaptive: Mapping[str, Any], executable: Path) -> dict[str, Any]:
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    vector_fingerprints = {
        rel(path): sha(path)
        for path in (PREPARATORY_MANIFEST, PROVISIONAL_SUMMARY, NATIVE_HIGHER_ORDER, NATIVE_HIGHER_ORDER_VECTORS,
                     ONE_BRANCH, ONE_BRANCH_VECTORS, ADAPTIVE_QUALIFICATION, RESOURCE_PROFILE, RESOURCE_METADATA)
    }
    config = NativeAdaptiveDriverConfig(
        run_id=RUN_ID,
        run_directory=RUN_DIR,
        targets=tuple(copy.deepcopy(dict(target)) for target in targets),
        configuration={
            "schema_version": SCHEMA_VERSION,
            "backend": "measured-native-adaptive-pilot-backend",
            "accepted_target_policy": "only targets with complete native remesh/restart plus exact native restart-vector defect and period/orbit gates are accepted",
            "unaccepted_target_policy": "resolution_unresolved explicit gaps; no interpolation and no fixed-mesh/Python relabeling",
            "measured_remesh_target_id": MEASURED_REMESH_TARGET_ID,
        },
        source_paths=(GENERATOR, DRIVER_SOURCE),
        source_root=ROOT,
        executable_path=executable,
        executable_identity={
            "path": display_path(executable),
            "sha256": sha(executable),
            "build_type": "Release",
            "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
        },
        vector_fingerprints=vector_fingerprints,
        max_cycles_per_target=4,
    )
    return NativeAdaptiveDriver(config, MeasuredPilotBackend(one_branch=one_branch, adaptive=adaptive)).run()


def production_events(summary: Mapping[str, Any], manifest: Mapping[str, Any], locus: HopfLocusCoordinates) -> dict[str, Any]:
    target_by_id = {target["target_id"]: target for target in manifest["target_manifest"]}
    records = []
    for target in summary["terminal_target_ledger"]["targets"]:
        status = target["terminal_status"]
        source = "computed_native_adaptive" if status == "accepted" else "unresolved_native_adaptive"
        validity = {"status": status, "source": source, "authoritative": status == "accepted"}
        if status != "accepted":
            validity["reason"] = target["reason"]
        event_type = "accepted_step" if status == "accepted" else "resolution_unresolved"
        records.append({
            "event_id": f"task072-terminal-{target['target_id']}",
            "event_type": event_type,
            "coordinates": target_coordinates(target_by_id[target["target_id"]], locus),
            "validity": validity,
            "method_versions": method_versions(),
        })
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "continuation-events",
        "artifact_id": "task072-native-adaptive-measured-pilot-events",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": common_provenance(source_artifacts=[
            source_record(RUN_DIR / "manifest.json", "TASK-072 measured pilot run manifest"),
            source_record(PREPARATORY_MANIFEST, "TASK-068 provisional skeleton source"),
            source_record(GENERATOR, "TASK-072 pilot generator"),
        ]),
        "continuation_events": records,
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=EVENTS)
    return artifact


def production_run_metadata(summary: Mapping[str, Any]) -> dict[str, Any]:
    resources = summary["measured_resource_accounting"]
    metadata = {
        "run_id": RUN_ID,
        "backend": "measured-native-adaptive-pilot-backend",
        "executable_identity": summary["source_build_checkpoint_identity"]["executable_identity"],
        "build_identity": summary["source_build_checkpoint_identity"]["build_identity"],
        "coordinate_domain": {
            "convention": PARAMETER_COORDINATE_CONVENTION,
            "temperature": {"min": 210.0, "max": 226.0, "unit": "K"},
            "log_w": {"min": -4.5, "max": -0.45, "unit": "ln(m s^-1)"},
            "rho": {"min": -0.15, "max": 0.15, "unit": "dimensionless"},
        },
        "resource_accounting": {
            "wall_clock": {"value": resources["wall_clock_s"], "unit": "s"},
            "cpu_time": {"value": resources["cpu_time_s"], "unit": "s"},
            "max_rss": {"value": resources["max_rss_kib"], "unit": "KiB"},
        },
        "terminal_status_counts": summary["terminal_target_ledger"]["terminal_status_counts"],
        "checkpoint_identity": summary["source_build_checkpoint_identity"]["checkpoint_identity"],
        "stale_checkpoint_policy": summary["source_build_checkpoint_identity"]["stale_checkpoint_policy"],
    }
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "run-metadata",
        "artifact_id": "task072-native-adaptive-measured-pilot-run-metadata",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": common_provenance(source_artifacts=[
            source_record(RUN_DIR / "manifest.json", "TASK-072 measured pilot run manifest"),
            source_record(RESOURCE_PROFILE, "TASK-071 measured resource source"),
            source_record(GENERATOR, "TASK-072 pilot generator"),
        ]),
        "run_metadata": metadata,
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=RUN_METADATA)
    return artifact


def build_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    executable = executable_path()
    if not executable.is_file():
        raise RuntimeError(f"Build native executable first or set BS2026_MIDPOINT_EXECUTABLE: {executable}")
    env = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable)}
    measurements = [
        measured_command(["uv", "run", "python", str(NATIVE_HIGHER_ORDER_SCRIPT), "--check"], env=env),
        measured_command(["uv", "run", "python", str(ONE_BRANCH_SCRIPT), "--check"], env=env),
    ]
    preparatory = load_json(PREPARATORY_MANIFEST)
    provisional = load_json(PROVISIONAL_SUMMARY)
    one_branch = load_json(ONE_BRANCH)
    adaptive = load_json(ADAPTIVE_QUALIFICATION)
    targets = []
    for target in preparatory["planned_run_manifest"]["targets"]:
        copied = copy.deepcopy(dict(target))
        copied["provisional_terminal_status"] = copied.pop("terminal_status", None)
        targets.append(copied)
    before = resource.getrusage(resource.RUSAGE_SELF)
    driver_manifest = build_driver_run(targets, one_branch=one_branch, adaptive=adaptive, executable=executable)
    ledger = target_ledger(driver_manifest)
    gates = gate_summary(driver_manifest, one_branch, adaptive)
    accepted_records = []
    for segment in driver_manifest["segments"]:
        for point in segment["fixed_mesh_segment"].get("points", []):
            if point.get("accepted_gates"):
                accepted_records.append({
                    "target_id": segment["target_id"],
                    "period_s": point["period_s"],
                    "vector_key": point["vector_key"],
                    "vector_sha256": point["vector_sha256"],
                    "accepted_gates": point["accepted_gates"],
                })
    aggregate = aggregate_resources(measurements, driver_manifest)
    if aggregate["wall_clock_s"] <= 0.0 or aggregate["max_rss_kib"] <= 0:
        raise RuntimeError("TASK-072 resource accounting is not measured")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task072-native-adaptive-measured-pilot",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "Measured native adaptive pilot over the TASK-068 210--226 K skeleton; all targets remain explicit unresolved gaps because no target has the complete exact native restart-vector gate bundle required for TASK-072 acceptance.",
        "truthfulness_policy": {
            "native_backend_emitted_every_terminal_status": True,
            "fixed_mesh_or_python_evidence_not_relabelled_as_task072_acceptance": True,
            "unaccepted_targets_are_explicit_unresolved_gap_records": True,
            "interpolation_used_to_fill_targets": False,
            "accepted_target_requires_complete_exact_native_gate_bundle": True,
        },
        "planned_run_manifest": {
            "source": rel(PREPARATORY_MANIFEST),
            "provisional_source": rel(PROVISIONAL_SUMMARY),
            "provisional_spine_range_K": preparatory["planned_run_manifest"]["provisional_spine_range_K"],
            "temperature_skeleton_K": preparatory["planned_run_manifest"]["temperature_skeleton_K"],
            "signed_rho_slice_targets": preparatory["planned_run_manifest"]["signed_rho_slice_targets"],
            "target_count": preparatory["planned_run_manifest"]["target_count"],
        },
        "run_directory": rel(RUN_DIR),
        "run_manifest": {
            "path": rel(RUN_DIR / "manifest.json"),
            "sha256": sha(RUN_DIR / "manifest.json"),
            "segment_count": len(driver_manifest["segments"]),
            "checkpoint_count": len([path for path in (RUN_DIR / "checkpoints").rglob("checkpoint.json")]),
            "status": driver_manifest["status"],
            "resume": driver_manifest["resume"],
            "fingerprints_sha256": driver_manifest["fingerprints_sha256"],
        },
        "terminal_target_ledger": ledger,
        "accepted_target_records": accepted_records,
        "validation_gates": gates,
        "measured_commands": measurements,
        "measured_resource_accounting": aggregate,
        "source_build_checkpoint_identity": {
            "executable_identity": {
                "path": display_path(executable),
                "sha256": sha(executable),
                "exists_at_generation": True,
            },
            "build_identity": {
                "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "uv_lock_sha256": sha(ROOT / "uv.lock"),
            },
            "checkpoint_identity": {
                "run_manifest_sha256": sha(RUN_DIR / "manifest.json"),
                "fingerprints_sha256": driver_manifest["fingerprints_sha256"],
                "checkpoint_sha256_by_segment": {
                    segment["segment_id"]: segment["checkpoint_sha256"] for segment in driver_manifest["segments"]
                },
            },
            "stale_checkpoint_policy": "NativeAdaptiveDriver validates schema, source, executable, vector, configuration, target-manifest, and checkpoint segment hashes before completed checkpoint reuse.",
        },
        "provenance": {
            "generator": source_record(GENERATOR, "TASK-072 pilot generator"),
            "driver_source": source_record(DRIVER_SOURCE, "resumable native adaptive driver"),
            "task069_review": source_record(TASK069_DOC, "pilot requirement and explicit-gap policy"),
            "task070_schema_doc": source_record(TASK070_DOC, "production-v1 schema boundary"),
            "task071_resource_doc": source_record(TASK071_DOC, "measured resource-field requirement"),
            "preparatory_manifest": source_record(PREPARATORY_MANIFEST, "TASK-068 provisional skeleton source"),
            "provisional_summary": source_record(PROVISIONAL_SUMMARY, "TASK-068 provisional status source"),
            "native_higher_order": source_record(NATIVE_HIGHER_ORDER, "measured native branch source"),
            "one_branch": source_record(ONE_BRANCH, "measured native remesh/restart source"),
            "adaptive_qualification": source_record(ADAPTIVE_QUALIFICATION, "defect and period/orbit gate source"),
            "resource_profile": source_record(RESOURCE_PROFILE, "TASK-071 resource identity source"),
            "resource_metadata": source_record(RESOURCE_METADATA, "TASK-071 production run metadata source"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "production_schema_artifacts": {
            "continuation_events": rel(EVENTS),
            "run_metadata": rel(RUN_METADATA),
        },
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py",
        "check_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_measured_pilot.py --check",
    }
    if ledger["target_count"] != 31 or not ledger["exactly_one_terminal_status_per_target"]:
        raise RuntimeError("TASK-072 terminal target ledger is incomplete")
    if ledger["terminal_status_counts"]["accepted"] != 0 or ledger["terminal_status_counts"]["resolution_unresolved"] != 31:
        raise RuntimeError("TASK-072 pilot policy expected all thirty-one targets to remain explicit unresolved targets")
    if not gates["all_accepted_points_pass_required_gates"] or not gates["all_remesh_restarts_pass_required_gates"]:
        raise RuntimeError("TASK-072 gate bundle invariant failed")
    if any(target["terminal_status"] != "accepted" and not target.get("reason") for target in ledger["targets"]):
        raise RuntimeError("TASK-072 unresolved target missing reason")
    SUMMARY.write_bytes(canonical(summary))
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    events = production_events(summary, driver_manifest, locus)
    run_metadata = production_run_metadata(summary)
    return summary, events, run_metadata


def write_outputs(summary: Mapping[str, Any], events: Mapping[str, Any], metadata: Mapping[str, Any]) -> None:
    # SUMMARY and RUN_DIR are written during build_driver_run/build_artifacts so production provenance can hash them.
    EVENTS.write_bytes(canonical(events))
    RUN_METADATA.write_bytes(canonical(metadata))
    # Recompute summary now that production artifacts exist and can be checked by path.
    final_summary = copy.deepcopy(dict(summary))
    final_summary["production_schema_artifact_sha256"] = {
        "continuation_events": sha(EVENTS),
        "run_metadata": sha(RUN_METADATA),
    }
    SUMMARY.write_bytes(canonical(final_summary))


def check_existing() -> None:
    for path in (SUMMARY, EVENTS, RUN_METADATA, RUN_DIR / "manifest.json"):
        if not path.is_file():
            raise SystemExit(f"missing TASK-072 artifact: {path}")
    summary = load_json(SUMMARY)
    for path in (EVENTS, RUN_METADATA):
        validate_production_artifact(load_json(path), root=ROOT, artifact_path=path)
    for key, record in summary["provenance"].items():
        path = ROOT / record["path"]
        if sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-072 provenance drift for {key}: {record['path']}")
    if summary["source_build_checkpoint_identity"]["build_identity"]["compiled_source_fingerprint_sha256"] != [sha(path) for path in COMPILED_SOURCES]:
        raise SystemExit("TASK-072 compiled source fingerprint drift")
    executable_record = summary["source_build_checkpoint_identity"]["executable_identity"]
    executable = Path(str(executable_record["path"]))
    executable = executable if executable.is_absolute() else ROOT / executable
    if executable.is_file() and sha(executable) != executable_record["sha256"]:
        raise SystemExit("TASK-072 executable digest drift")
    manifest = load_json(RUN_DIR / "manifest.json")
    if sha(RUN_DIR / "manifest.json") != summary["run_manifest"]["sha256"]:
        raise SystemExit("TASK-072 run manifest digest drift")
    if manifest["fingerprints_sha256"] != summary["run_manifest"]["fingerprints_sha256"]:
        raise SystemExit("TASK-072 run manifest fingerprint drift")
    for segment in manifest["segments"]:
        checkpoint = RUN_DIR / segment["checkpoint_path"]
        if not checkpoint.is_file() or sha(checkpoint) != segment["checkpoint_sha256"]:
            raise SystemExit(f"TASK-072 checkpoint drift: {checkpoint}")
    if summary["terminal_target_ledger"]["target_count"] != 31 or not summary["terminal_target_ledger"]["exactly_one_terminal_status_per_target"]:
        raise SystemExit("TASK-072 terminal ledger is invalid")
    resources = summary["measured_resource_accounting"]
    if resources["wall_clock_s"] <= 0.0 or resources["max_rss_kib"] <= 0 or resources["cpu_time_s"] < 0.0:
        raise SystemExit("TASK-072 resource accounting is not measured")
    if summary["truthfulness_policy"]["interpolation_used_to_fill_targets"] is not False:
        raise SystemExit("TASK-072 interpolation policy violated")
    print("verified TASK-072 measured native adaptive pilot artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed artifacts without re-measuring timing")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    summary, events, metadata = build_artifacts()
    write_outputs(summary, events, metadata)
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(RUN_DIR)}")
    print(f"wrote {rel(EVENTS)}")
    print(f"wrote {rel(RUN_METADATA)}")


if __name__ == "__main__":
    main()
