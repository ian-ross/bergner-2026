#!/usr/bin/env python3
"""Measure TASK-071 native adaptive continuation resource usage.

The artifact generated here replaces TASK-068's deterministic zero resource
placeholders with measured wall-clock, CPU, max-RSS, NOX iteration, and KLU2
counter evidence for representative seams that exist today:

* a fixed-mesh three-stage NOX/KLU2 correction through the native executable;
* the accepted one-branch remesh/restart slice through its current generator;
* the provisional pilot-style native adaptive driver summary through its current
  driver/checkpoint seam.

These measurements are profiling evidence only.  They are not scientific
acceptance of any continuation point and do not convert TASK-068 failed/pending
provisional targets into accepted production Figure 5 data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

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
PROFILE = OUTPUT / "native_adaptive_resource_profile.json"
RUN_METADATA = OUTPUT / "native_adaptive_resource_profile_run_metadata.json"

FIXED_FIXTURE = OUTPUT / "cpp_higher_order_fixtures/canonical-g3-n32.txt"
ONE_BRANCH_SCRIPT = EPISODE / "scripts/generate_native_adaptive_one_branch_segment.py"
SPINE_SLICES_SCRIPT = EPISODE / "scripts/generate_native_adaptive_spine_slices_run.py"
ONE_BRANCH_ARTIFACT = OUTPUT / "native_adaptive_one_branch_segment.json"
SPINE_SLICES_SUMMARY = OUTPUT / "native_adaptive_spine_slices_run.json"
SPINE_SLICES_MANIFEST = OUTPUT / "native_adaptive_spine_slices_run/manifest.json"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
DECISIONS_DOC = EPISODE / "docs/collocation-phase-decisions.md"
README = EPISODE / "README.md"
GENERATOR = Path(__file__).resolve()
DRIVER_SOURCE = ROOT / "src/bergner_spichtinger_2026/native_adaptive_driver.py"

SCHEMA_VERSION = "episode008-native-adaptive-resource-profile-v1"
ARTIFACT_KIND = "task071-native-adaptive-resource-profile"
RUN_ID = "task071-native-adaptive-resource-profile"
TIME_BINARY = Path("/usr/bin/time")
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_midpoint_orbit"
ITERATIVE_TRIGGER_VERSION = "task062-klu2-iterative-trigger-policy-v1"

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
        return str(resolved)


def display_command(command: Sequence[str]) -> list[str]:
    displayed: list[str] = []
    for item in command:
        path = Path(str(item))
        if path.is_absolute():
            displayed.append(display_path(path))
        else:
            displayed.append(str(item))
    return displayed


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
    required = {"wall_clock_s", "user_cpu_s", "system_cpu_s", "max_rss_kib", "exit_status"}
    missing = required - values.keys()
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


def measure_command(command: Sequence[str], *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    if not TIME_BINARY.is_file():
        raise RuntimeError("/usr/bin/time is required for TASK-071 resource measurement")
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
        completed = subprocess.run(
            wrapped,
            cwd=ROOT,
            env=dict(env) if env is not None else None,
            text=True,
            capture_output=True,
            check=False,
        )
        resources = parse_time_file(time_file)
    if completed.returncode != 0:
        raise RuntimeError(
            f"measured command failed with exit code {completed.returncode}: {' '.join(map(str, command))}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if resources["exit_status"] != 0:
        raise RuntimeError(f"/usr/bin/time reported nonzero exit status for {' '.join(map(str, command))}")
    if resources["wall_clock_s"] <= 0.0 or resources["max_rss_kib"] <= 0:
        raise RuntimeError(f"non-placeholder wall/RSS measurement failed for {' '.join(map(str, command))}: {resources}")
    return {
        "command": display_command(command),
        "command_string": " ".join(display_command(command)),
        "resources": resources,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def rows(stdout: str) -> list[list[str]]:
    return [line.split() for line in stdout.splitlines() if line.strip()]


def row_by_name(parsed: Sequence[Sequence[str]], name: str) -> list[str]:
    return list(next(row for row in parsed if row[0] == name))


def fixed_mesh_measurement(executable: Path, env: Mapping[str, str]) -> dict[str, Any]:
    measured = measure_command([str(executable), "solve", str(FIXED_FIXTURE)], env=env)
    parsed = rows(measured["stdout"])
    nox = row_by_name(parsed, "nox")
    linear = row_by_name(parsed, "linear")
    build_identity = row_by_name(parsed, "build_identity")[1:]
    cmake_identity = row_by_name(parsed, "cmake_identity")[1:]
    source_fingerprint = row_by_name(parsed, "source_fingerprint")[1:]
    diagnostics = row_by_name(parsed, "diagnostics")[1:]
    accepted = row_by_name(parsed, "accepted")[1] == "true"
    return {
        "segment_id": "fixed-mesh-gauss3-n32-correction",
        "segment_type": "fixed_mesh",
        "description": "Native three-stage N=32 fixed-mesh NOX/KLU2 correction of the canonical higher-order fixture.",
        "measurement_command": measured["command"],
        "resources": measured["resources"],
        "counter_source": "line-oriented bs2026_midpoint_orbit solve output",
        "counter_aggregation_role": "independent_measured_correction",
        "nonlinear_iterations": int(nox[2]),
        "nox_status": nox[1],
        "nox_residual_norm": float(nox[3]),
        "klu2": {
            "backend": linear[1],
            "reported": linear[2] == "reported",
            "symbolic_factorizations": int(linear[3]),
            "numeric_factorizations": int(linear[4]),
            "linear_solves": int(linear[5]),
            "symbolic_complete": linear[6] == "true",
            "numeric_complete": linear[7] == "true",
            "solve_complete": linear[8] == "true",
        },
        "native_acceptance_gates_passed": accepted,
        "diagnostics": {
            "stage_residual_max": float(diagnostics[0]),
            "stage_residual_rms": float(diagnostics[1]),
            "update_residual_max": float(diagnostics[2]),
            "update_residual_rms": float(diagnostics[3]),
            "phase_residual_abs": float(diagnostics[4]),
            "phase_energy": float(diagnostics[5]),
        },
        "build_identity": {"compiler_and_trilinos": build_identity, "cmake_identity": cmake_identity},
        "source_fingerprint_sha256": source_fingerprint,
    }


def remesh_restart_measurement(executable: Path, env: Mapping[str, str]) -> dict[str, Any]:
    measured = measure_command(["uv", "run", "python", str(ONE_BRANCH_SCRIPT), "--check"], env=env)
    data = load_json(ONE_BRANCH_ARTIFACT)
    restart = data["restart"]
    segment = data["native_fixed_mesh_segment"]
    linear = restart["linear"]
    correction = restart["correction"]
    return {
        "segment_id": "one-branch-remesh-restart",
        "segment_type": "remesh_restart",
        "description": "Current one-branch native adaptive seam: fixed-mesh LOCA segment, h+r transfer, rebuild, and fixed-parameter NOX/KLU2 restart correction.",
        "measurement_command": measured["command"],
        "resources": measured["resources"],
        "counter_source": rel(ONE_BRANCH_ARTIFACT),
        "counter_aggregation_role": "independent_measured_correction",
        "selected_branch_id": data["selected_branch_id"],
        "native_fixed_mesh_event_count": len(segment["events"]),
        "native_fixed_mesh_accepted_point_count": len(segment["points"]),
        "nonlinear_iterations": int(correction["iterations"]),
        "nox_status": correction["nox_status"],
        "nox_residual_norm": float(correction["nox_residual_norm"]),
        "klu2": {
            "backend": linear["backend"],
            "reported": bool(linear["reported"]),
            "symbolic_factorizations": int(linear["symbolic_factorizations"]),
            "numeric_factorizations": int(linear["numeric_factorizations"]),
            "linear_solves": int(linear["solves"]),
            "symbolic_complete": bool(linear["symbolic_complete"]),
            "numeric_complete": bool(linear["numeric_complete"]),
            "solve_complete": bool(linear["solve_complete"]),
        },
        "restart_gates_passed": all(bool(value) for value in restart["gates"].values()),
        "build_identity": data["runtime_provenance"],
    }


def pilot_measurement(executable: Path, env: Mapping[str, str], fixed: Mapping[str, Any], remesh: Mapping[str, Any]) -> dict[str, Any]:
    measured = measure_command(["uv", "run", "python", str(SPINE_SLICES_SCRIPT), "--check"], env=env)
    summary = load_json(SPINE_SLICES_SUMMARY)
    manifest = load_json(SPINE_SLICES_MANIFEST)
    terminal = summary["terminal_target_ledger"]
    validation = summary["validation_gates"]
    # The provisional pilot-style driver replays current native fixed-mesh and
    # restart evidence.  Counter aggregation is therefore deliberately a lower
    # bound from concrete NOX/KLU2 seams measured above, not a claim that failed
    # TASK-068 targets were executed by production adaptive C++.
    return {
        "segment_id": "pilot-style-spine-slices-driver-check",
        "segment_type": "pilot_style_native_adaptive_driver",
        "description": "Check-mode execution of the current resumable spine-and-slices driver seam using curated native fixed-mesh/restart evidence.",
        "measurement_command": measured["command"],
        "resources": measured["resources"],
        "counter_source": "aggregate lower bound from measured fixed-mesh correction plus measured one-branch restart; driver-internal TASK-068 resources remain placeholders and are not used",
        "counter_aggregation_role": "contextual_lower_bound_duplicate_not_added_to_unique_counter_totals",
        "run_manifest_path": rel(SPINE_SLICES_MANIFEST),
        "summary_path": rel(SPINE_SLICES_SUMMARY),
        "driver_manifest_placeholder_resources_ignored": manifest["resource_accounting"] == {
            "max_rss_kib": 0,
            "segment_cpu_s": 0.0,
            "segment_wall_clock_s": 0.0,
        },
        "terminal_status_counts": terminal["terminal_status_counts"],
        "accepted_segment_count": int(validation["accepted_segment_count"]),
        "accepted_point_count": int(validation["accepted_point_count"]),
        "restart_count": int(validation["restart_count"]),
        "failed_or_unresolved_outcome_count": len(validation["unresolved_rejected_capped_tripwire_outcomes_recorded"]),
        "nonlinear_iterations": int(fixed["nonlinear_iterations"]) + int(remesh["nonlinear_iterations"]),
        "nox_status": "aggregate_measured_representative_seams",
        "klu2": {
            "backend": "KLU2",
            "reported": bool(fixed["klu2"]["reported"] and remesh["klu2"]["reported"]),
            "symbolic_factorizations": int(fixed["klu2"]["symbolic_factorizations"]) + int(remesh["klu2"]["symbolic_factorizations"]),
            "numeric_factorizations": int(fixed["klu2"]["numeric_factorizations"]) + int(remesh["klu2"]["numeric_factorizations"]),
            "linear_solves": int(fixed["klu2"]["linear_solves"]) + int(remesh["klu2"]["linear_solves"]),
            "symbolic_complete": bool(fixed["klu2"]["symbolic_complete"] and remesh["klu2"]["symbolic_complete"]),
            "numeric_complete": bool(fixed["klu2"]["numeric_complete"] and remesh["klu2"]["numeric_complete"]),
            "solve_complete": bool(fixed["klu2"]["solve_complete"] and remesh["klu2"]["solve_complete"]),
        },
        "truthfulness_policy": summary["truthfulness_policy"],
        "build_identity": {"executable_path": display_path(executable), "executable_sha256": sha(executable), "driver_fingerprints_sha256": manifest["fingerprints_sha256"]},
    }


def aggregate_measurements(measurements: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    independent_counter_rows = [
        item for item in measurements
        if item.get("counter_aggregation_role") == "independent_measured_correction"
    ]
    return {
        "wall_clock_s": sum(float(item["resources"]["wall_clock_s"]) for item in measurements),
        "cpu_time_s": sum(float(item["resources"]["cpu_time_s"]) for item in measurements),
        "max_rss_kib": max(int(item["resources"]["max_rss_kib"]) for item in measurements),
        "unique_counter_row_count": len(independent_counter_rows),
        "counter_aggregation_policy": "NOX/KLU2 totals include only independent measured correction rows; pilot-style lower-bound duplicate counters are reported per-row but not added again.",
        "nonlinear_iterations": sum(int(item["nonlinear_iterations"]) for item in independent_counter_rows),
        "klu2_symbolic_factorizations": sum(int(item["klu2"]["symbolic_factorizations"]) for item in independent_counter_rows),
        "klu2_numeric_factorizations": sum(int(item["klu2"]["numeric_factorizations"]) for item in independent_counter_rows),
        "linear_solves": sum(int(item["klu2"]["linear_solves"]) for item in independent_counter_rows),
    }


def klu2_review(measurements: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any]) -> dict[str, Any]:
    max_rss = int(aggregate["max_rss_kib"])
    total_wall = float(aggregate["wall_clock_s"])
    max_wall = max(float(item["resources"]["wall_clock_s"]) for item in measurements)
    max_cpu = max(float(item["resources"]["cpu_time_s"]) for item in measurements)
    all_klu2 = all(item["klu2"].get("backend") == "KLU2" and item["klu2"].get("solve_complete") for item in measurements)
    memory_threshold_met = max_rss > 4 * 1024 * 1024
    run_budget_threshold_met = False
    exposed_boolean_triggers = [memory_threshold_met, run_budget_threshold_met]
    thresholds_met = any(exposed_boolean_triggers)
    decision = (
        "iterative_solver_trigger_threshold_met_review_Belos_Ifpack2"
        if thresholds_met else "serial_KLU2_remains_acceptable_for_current_native_adaptive_pilot_seams"
    )
    return {
        "policy_version": ITERATIVE_TRIGGER_VERSION,
        "documented_trigger_source": rel(DECISIONS_DOC),
        "documented_triggers": {
            "realistic_N_256_to_512_factorization_memory_above_4_GiB": memory_threshold_met,
            "median_factorization_or_solve_time_above_30_s_per_nonlinear_iteration": "not_evaluated_backend_does_not_expose_factorization_timing",
            "more_than_70_percent_runtime_in_linear_algebra": "not_evaluated_backend_does_not_expose_linear_algebra_timing_split",
            "inability_to_meet_recorded_run_budget": run_budget_threshold_met,
        },
        "measured_bounds": {
            "total_wall_clock_s": total_wall,
            "max_segment_wall_clock_s": max_wall,
            "max_segment_cpu_time_s": max_cpu,
            "max_rss_kib": max_rss,
            "max_rss_gib": max_rss / (1024.0 * 1024.0),
            "total_nonlinear_iterations": int(aggregate["nonlinear_iterations"]),
            "total_klu2_symbolic_factorizations": int(aggregate["klu2_symbolic_factorizations"]),
            "total_klu2_numeric_factorizations": int(aggregate["klu2_numeric_factorizations"]),
            "total_linear_solves": int(aggregate["linear_solves"]),
        },
        "decision": decision,
        "iterative_solver_thresholds_met": thresholds_met,
        "rationale": (
            "All measured representative seams completed with reported KLU2 activity. "
            "The max-RSS trigger is evaluated directly from measurements and the run-budget trigger is false for this checkable pilot profile. "
            "The backend does not expose factorization/solve timing splits, so those trigger channels remain explicit not-evaluated rather than inferred. "
            "Belos/Ifpack2 work is not justified unless an evaluated trigger is true; retain KLU2 as the serial oracle/reference pending larger production profiling."
        ),
        "cost_is_scientific_acceptance": False,
        "all_measured_klu2_solves_complete": all_klu2,
    }


def production_run_metadata(profile: Mapping[str, Any], executable: Path) -> dict[str, Any]:
    aggregate = profile["aggregate_resource_accounting"]
    return {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "run-metadata",
        "artifact_id": "task071-native-adaptive-resource-profile-run-metadata",
        "method_versions": {
            "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "continuation_method": "external-gauss3-hr-adaptive-v1",
            "validator": "episode8-production-validator-v1",
            "profiling_method": SCHEMA_VERSION,
        },
        "coordinate_conventions": {
            "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
            "orbit_state": ORBIT_STATE_CONVENTION,
            "phase": PHASE_COORDINATE_CONVENTION,
            "period": PERIOD_CONVENTION,
        },
        "provenance": {
            "task": "TASK-071",
            "created_by": "generate_native_adaptive_resource_profile.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                {"path": rel(PROFILE), "sha256": sha(PROFILE), "role": "TASK-071 measured profile artifact"},
                {"path": rel(TASK069_DOC), "sha256": sha(TASK069_DOC), "role": "TASK-069 profiling requirement"},
                {"path": rel(TASK070_DOC), "sha256": sha(TASK070_DOC), "role": "production schema boundary"},
            ],
        },
        "run_metadata": {
            "run_id": RUN_ID,
            "backend": "native-adaptive-loca-current-seams-profiled",
            "executable_identity": {"path": display_path(executable), "sha256": sha(executable)},
            "build_identity": profile["runtime_identity"],
            "coordinate_domain": {
                "convention": PARAMETER_COORDINATE_CONVENTION,
                "temperature": {"min": 210.0, "max": 226.0, "unit": "K"},
                "log_w": {"min": float("-4.605170185988091"), "max": float("-1.3862943611198906"), "unit": "ln(m s^-1)"},
                "rho": {"min": -0.15, "max": 0.15, "unit": "dimensionless"},
            },
            "resource_accounting": {
                "wall_clock": {"value": float(aggregate["wall_clock_s"]), "unit": "s"},
                "cpu_time": {"value": float(aggregate["cpu_time_s"]), "unit": "s"},
                "max_rss": {"value": int(aggregate["max_rss_kib"]), "unit": "KiB"},
            },
            "terminal_status_counts": profile["pilot_terminal_status_counts"],
        },
    }


def validate_profile(profile: Mapping[str, Any]) -> None:
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("profile schema_version mismatch")
    measurements = profile.get("measurements")
    if not isinstance(measurements, list) or {item.get("segment_type") for item in measurements} != {
        "fixed_mesh", "remesh_restart", "pilot_style_native_adaptive_driver",
    }:
        raise RuntimeError("profile must contain fixed_mesh, remesh_restart, and pilot_style measurements")
    for item in measurements:
        resources = item["resources"]
        if resources["wall_clock_s"] <= 0.0 or resources["cpu_time_s"] < 0.0 or resources["max_rss_kib"] <= 0:
            raise RuntimeError(f"placeholder or invalid resources in {item['segment_id']}")
        if int(item["nonlinear_iterations"]) <= 0:
            raise RuntimeError(f"missing nonlinear iteration counter in {item['segment_id']}")
        klu2 = item["klu2"]
        if klu2["backend"] != "KLU2" or not klu2["reported"] or not klu2["solve_complete"]:
            raise RuntimeError(f"missing KLU2 completion counters in {item['segment_id']}")
        if min(int(klu2["symbolic_factorizations"]), int(klu2["numeric_factorizations"]), int(klu2["linear_solves"])) <= 0:
            raise RuntimeError(f"zero KLU2 activity in {item['segment_id']}")
    review = profile["klu2_iterative_solver_review"]
    if review["cost_is_scientific_acceptance"] is not False:
        raise RuntimeError("cost profile must not be marked as scientific acceptance")
    memory_trigger = review["documented_triggers"]["realistic_N_256_to_512_factorization_memory_above_4_GiB"]
    budget_trigger = review["documented_triggers"]["inability_to_meet_recorded_run_budget"]
    if review["iterative_solver_thresholds_met"] != bool(memory_trigger or budget_trigger):
        raise RuntimeError("KLU2 trigger review is internally inconsistent with evaluated trigger channels")


def validate_metadata_matches_profile(metadata: Mapping[str, Any], profile: Mapping[str, Any]) -> None:
    run_metadata = metadata.get("run_metadata", {})
    aggregate = profile["aggregate_resource_accounting"]
    resources = run_metadata.get("resource_accounting", {})
    checks = {
        "wall_clock": (resources.get("wall_clock", {}).get("value"), aggregate["wall_clock_s"]),
        "cpu_time": (resources.get("cpu_time", {}).get("value"), aggregate["cpu_time_s"]),
        "max_rss": (resources.get("max_rss", {}).get("value"), aggregate["max_rss_kib"]),
    }
    for name, (observed, expected) in checks.items():
        if observed != expected:
            raise RuntimeError(f"production run metadata {name} does not match TASK-071 profile")
    if run_metadata.get("terminal_status_counts") != profile.get("pilot_terminal_status_counts"):
        raise RuntimeError("production run metadata terminal counts do not match TASK-071 profile")
    if metadata.get("method_versions", {}).get("profiling_method") != profile.get("schema_version"):
        raise RuntimeError("production run metadata profiling method does not match TASK-071 profile")
    profile_source = next(
        (source for source in metadata.get("provenance", {}).get("source_artifacts", []) if source.get("path") == rel(PROFILE)),
        None,
    )
    if profile_source is None or profile_source.get("sha256") != sha(PROFILE):
        raise RuntimeError("production run metadata does not reference the current TASK-071 profile checksum")
    executable_identity = run_metadata.get("executable_identity", {})
    if executable_identity.get("sha256") != profile.get("runtime_identity", {}).get("executable_sha256"):
        raise RuntimeError("production run metadata executable digest does not match TASK-071 profile")


def check_existing() -> None:
    if not PROFILE.is_file() or not RUN_METADATA.is_file():
        raise SystemExit("TASK-071 resource profile artifacts are missing; run without --check to generate them")
    profile = load_json(PROFILE)
    validate_profile(profile)
    for source in profile["source_provenance"].values():
        path = ROOT / source["path"]
        if sha(path) != source["sha256"]:
            raise SystemExit(f"source provenance drift in TASK-071 profile: {source['path']}")
    if profile["runtime_identity"].get("compiled_source_fingerprint_sha256") != [sha(path) for path in COMPILED_SOURCES]:
        raise SystemExit("compiled native source fingerprint drift in TASK-071 profile")
    executable_record_path = profile["runtime_identity"].get("executable_path")
    executable_record = Path(str(executable_record_path))
    executable_candidate = executable_record if executable_record.is_absolute() else ROOT / executable_record
    if executable_candidate.is_file() and sha(executable_candidate) != profile["runtime_identity"].get("executable_sha256"):
        raise SystemExit("native executable digest drift in TASK-071 profile")
    metadata = load_json(RUN_METADATA)
    validate_production_artifact(metadata, root=ROOT, artifact_path=RUN_METADATA)
    validate_metadata_matches_profile(metadata, profile)
    print("verified TASK-071 native adaptive resource profile artifacts")


def build_profile() -> dict[str, Any]:
    executable = executable_path()
    if not executable.is_file():
        raise RuntimeError(f"Build native executable first or set BS2026_MIDPOINT_EXECUTABLE: {executable}")
    env = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable)}
    fixed = fixed_mesh_measurement(executable, env)
    remesh = remesh_restart_measurement(executable, env)
    pilot = pilot_measurement(executable, env, fixed, remesh)
    measurements = [fixed, remesh, pilot]
    aggregate = aggregate_measurements(measurements)
    profile: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task071-native-adaptive-resource-profile",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "Measured resource evidence for current native adaptive seams; not production Figure 5 scientific acceptance.",
        "truthfulness_policy": {
            "replaces_task068_zero_resource_placeholders": True,
            "cost_measurements_are_not_scientific_acceptance": True,
            "failed_or_pending_targets_not_rebranded_as_accepted": True,
            "production_cpp_full_adaptive_backend_executed": False,
            "current_backend_seams_profiled": ["fixed_mesh", "remesh_restart", "pilot_style_native_adaptive_driver"],
        },
        "measurement_method": {
            "version": SCHEMA_VERSION,
            "timer": "/usr/bin/time -f wall/user/system/max-rss",
            "wall_clock_unit": "s",
            "cpu_time_unit": "s",
            "max_rss_unit": "KiB",
            "counter_policy": "extract NOX/KLU2 counters from native line output and current native adaptive artifact seams; do not infer unexposed factorization timing",
        },
        "runtime_identity": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "executable_path": display_path(executable),
            "executable_sha256": sha(executable),
            "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
            "uv_lock_sha256": sha(ROOT / "uv.lock"),
        },
        "source_provenance": {
            "generator": source_record(GENERATOR, "TASK-071 profiling generator"),
            "task069_review": source_record(TASK069_DOC, "profiling requirement and KLU2 pending-profile decision"),
            "task070_schema_doc": source_record(TASK070_DOC, "production-v1 metadata boundary"),
            "collocation_decisions": source_record(DECISIONS_DOC, "documented iterative-solver trigger thresholds"),
            "episode_readme": source_record(README, "Episode 008 documentation"),
            "one_branch_artifact": source_record(ONE_BRANCH_ARTIFACT, "remesh/restart counter source"),
            "spine_slices_summary": source_record(SPINE_SLICES_SUMMARY, "pilot-style driver summary source"),
            "spine_slices_manifest": source_record(SPINE_SLICES_MANIFEST, "pilot-style driver manifest source"),
            "fixed_mesh_fixture": source_record(FIXED_FIXTURE, "fixed-mesh correction fixture"),
            "one_branch_generator": source_record(ONE_BRANCH_SCRIPT, "remesh/restart generator command"),
            "spine_slices_generator": source_record(SPINE_SLICES_SCRIPT, "pilot-style driver generator command"),
            "native_adaptive_driver": source_record(DRIVER_SOURCE, "pilot-style driver implementation"),
            "cpp_midpoint_loca": source_record(COMPILED_SOURCES[0], "compiled native LOCA adapter"),
            "cpp_midpoint_orbit": source_record(COMPILED_SOURCES[1], "compiled native sparse orbit assembler"),
            "cpp_model": source_record(COMPILED_SOURCES[2], "compiled native local model"),
            "cpp_midpoint_nox": source_record(COMPILED_SOURCES[3], "compiled native NOX/KLU2 adapter"),
            "cpp_collocation_coefficients": source_record(COMPILED_SOURCES[4], "compiled collocation coefficients"),
            "cpp_midpoint_cli": source_record(COMPILED_SOURCES[5], "compiled native CLI"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "measurements": measurements,
        "aggregate_resource_accounting": aggregate,
        "pilot_terminal_status_counts": pilot["terminal_status_counts"],
        "klu2_iterative_solver_review": klu2_review(measurements, aggregate),
        "production_schema_metadata_artifact": rel(RUN_METADATA),
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py",
        "check_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_resource_profile.py --check",
    }
    validate_profile(profile)
    return profile


def write_outputs(profile: dict[str, Any]) -> None:
    PROFILE.write_bytes(canonical(profile))
    # Build metadata after PROFILE exists so provenance can contain PROFILE's checksum.
    metadata = production_run_metadata(profile, executable_path())
    validate_production_artifact(metadata, root=ROOT, artifact_path=RUN_METADATA)
    RUN_METADATA.write_bytes(canonical(metadata))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed artifacts without re-measuring timing")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    profile = build_profile()
    write_outputs(profile)
    print(f"wrote {rel(PROFILE)}")
    print(f"wrote {rel(RUN_METADATA)}")


if __name__ == "__main__":
    main()
