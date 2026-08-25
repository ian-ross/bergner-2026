#!/usr/bin/env python3
"""Generate the TASK-081 native adaptive pilot gate follow-up artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import (  # noqa: E402
    COLLOCATION_ARTIFACT_SHA256,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    HopfLocusCoordinates,
    OrbitLayout,
    correct_gauss_orbit,
    gauss_legendre_rule,
    midpoint_residual_diagnostics,
    sha256_file,
)
from bergner_spichtinger_2026.constants import Environment  # noqa: E402
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    ORBIT_STATE_CONVENTION,
    PARAMETER_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)
from bergner_spichtinger_2026.periodic_orbits import transformed_vector_field  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_pilot_gate_followup.json"
EVENTS = OUTPUT / "native_adaptive_pilot_gate_followup_events.json"
RUN_METADATA = OUTPUT / "native_adaptive_pilot_gate_followup_run_metadata.json"
EXACT_FIXTURE = OUTPUT / "native_adaptive_pilot_gate_followup_exact_restart_fixture.txt"
ADAPTIVE_FIXTURE = OUTPUT / "cpp_adaptive_nonuniform_fixtures/adaptive-guard-rho-0-g3-n32.txt"

TASK072_SUMMARY = OUTPUT / "native_adaptive_measured_pilot.json"
TASK072_EVENTS = OUTPUT / "native_adaptive_measured_pilot_events.json"
TASK072_METADATA = OUTPUT / "native_adaptive_measured_pilot_run_metadata.json"
TASK072_RUN_MANIFEST = OUTPUT / "native_adaptive_measured_pilot/manifest.json"
TASK073_RECONCILIATION = OUTPUT / "native_adaptive_pilot_reconciliation.json"
ONE_BRANCH = OUTPUT / "native_adaptive_one_branch_segment.json"
ONE_BRANCH_VECTORS = OUTPUT / "native_adaptive_one_branch_segment_vectors.npz"
ADAPTIVE_QUALIFICATION = OUTPUT / "adaptive_qualification_results.json"
PYTHON_VALIDATION = OUTPUT / "native_adaptive_python_validation.json"
RESOURCE_PROFILE = OUTPUT / "native_adaptive_resource_profile.json"
RESOURCE_METADATA = OUTPUT / "native_adaptive_resource_profile_run_metadata.json"
MIDPOINT_RESULTS = OUTPUT / "fixed_mesh_midpoint_results.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
README = EPISODE / "README.md"
TASK072_DOC = EPISODE / "docs/task072-measured-native-adaptive-pilot.md"
TASK073_DOC = EPISODE / "docs/task073-native-adaptive-pilot-reconciliation.md"
TASK081_DOC = EPISODE / "docs/task081-native-adaptive-pilot-gate-followup.md"
GENERATOR = Path(__file__).resolve()
DEFAULT_EXECUTABLE = ROOT / "loca-build/bs2026_midpoint_orbit"
SCHEMA_VERSION = "episode008-native-adaptive-pilot-gate-followup-v1"
ARTIFACT_KIND = "task081-native-adaptive-pilot-gate-followup"
ACCEPTED_TARGET_ID = "spine-210K"
ADAPTIVE_CASE_ID = "guard-rho-0-g3-n32"
VECTOR_CASE_ID = "adaptive-guard-rho-0-g3-n32"
ALLOWED_TERMINAL_STATUSES = ("accepted", "resolution_unresolved", "near_hopf_stop", "tripwire_stop", "failed")
DEFECT_TOLERANCE = 1.0e-4
PERIOD_ORBIT_TOLERANCE = 1.0e-3
PYTHON_PARITY_TOLERANCE = 2.0e-7
IVP_RETURN_TOLERANCE = 1.0e-3

COMPILED_SOURCES = (
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
    ROOT / "loca/src/midpoint_orbit_cli.cpp",
)


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def executable_path() -> Path:
    return Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", DEFAULT_EXECUTABLE)).resolve()


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "followup": SCHEMA_VERSION,
        "pilot": "episode008-native-adaptive-measured-pilot-v1+task081-gate-followup",
        "driver": "episode008-native-adaptive-driver-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "restart": "fixed-parameter-remesh-restart-v1",
        "defect": "two-grid-relative-defect-v1",
        "linear_solver": "thyra-nox-amesos2-klu2-v1",
        "ivp_validation": "dop853-one-period-return-v1",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def rows(values: np.ndarray) -> list[str]:
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        return [" ".join(format(float(value), ".17g") for value in array)]
    return [" ".join(format(float(value), ".17g") for value in row) for row in array.reshape(-1, array.shape[-1])]


def parse_rows(text: str) -> list[list[str]]:
    return [line.split() for line in text.splitlines() if line.strip()]


def first_row(rows_: Sequence[Sequence[str]], name: str) -> list[str]:
    for row in rows_:
        if row and row[0] == name:
            return list(row)
    raise RuntimeError(f"missing native output row {name!r}")


def build_environment(temperature: float) -> Environment:
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    return Environment(
        p=30000.0,
        T=float(temperature),
        w=float(math.exp(locus.spine_log_w(temperature))),
        F=1.0,
        N_a=1e10,
        Δz=100.0,
        include_evaporation=False,
    )


def load_restart_arrays() -> dict[str, np.ndarray]:
    with np.load(ONE_BRANCH_VECTORS, allow_pickle=False) as arrays:
        return {
            "boundaries": np.asarray(arrays[f"transfer__{VECTOR_CASE_ID}__destination_boundaries"], dtype=float),
            "phase_values": np.asarray(arrays[f"transfer__{VECTOR_CASE_ID}__transferred_phase_values"], dtype=float).reshape(-1, 3, 3),
            "phase_derivatives": np.asarray(arrays[f"transfer__{VECTOR_CASE_ID}__transferred_phase_derivatives"], dtype=float).reshape(-1, 3, 3),
            "transferred_unknowns": np.asarray(arrays[f"transfer__{VECTOR_CASE_ID}__transferred_unknowns"], dtype=float),
            "native_restart_unknowns": np.asarray(arrays[f"restart__{VECTOR_CASE_ID}__corrected_solution"], dtype=float),
        }


def exact_restart_fixture_bytes(arrays: Mapping[str, np.ndarray], env: Environment, scaling: np.ndarray) -> bytes:
    unknowns = np.asarray(arrays["native_restart_unknowns"], dtype=float)
    boundaries = np.asarray(arrays["boundaries"], dtype=float)
    lines = [
        f"BS2026_GAUSS_FIXTURE_V1 task081-exact-{ACCEPTED_TARGET_ID}-native-restart {boundaries.size - 1} 3 6 accepted {COLLOCATION_ARTIFACT_SHA256}",
        f"30000 {format(env.T, '.17g')} {format(env.w, '.17g')} 1 10000000000 100",
        f"{format(math.log(0.01), '.17g')} {format(math.log(0.25), '.17g')} 0.037",
        " ".join(format(float(value), ".17g") for value in scaling),
        *rows(boundaries),
        *rows(np.asarray(arrays["phase_values"], dtype=float)),
        *rows(np.asarray(arrays["phase_derivatives"], dtype=float)),
        *rows(unknowns),
    ]
    return ("\n".join(lines) + "\n").encode()


def execute_native(command: str, fixture: Path, executable: Path) -> list[list[str]]:
    completed = subprocess.run(
        [str(executable), command, str(fixture)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"native command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
    return parse_rows(completed.stdout)


def build_assembler(arrays: Mapping[str, np.ndarray], env: Environment, scaling: np.ndarray) -> GaussCollocationAssembler:
    rule = gauss_legendre_rule(3)
    mesh = FixedMesh(np.asarray(arrays["boundaries"], dtype=float))
    reference = FrozenPhaseReference(
        mesh,
        np.asarray(arrays["phase_values"], dtype=float),
        np.asarray(arrays["phase_derivatives"], dtype=float),
        scaling,
        rule.nodes,
        rule.quadrature_weights,
    )
    return GaussCollocationAssembler(mesh, env, reference, rule)


def exact_restart_gate_bundle(
    arrays: Mapping[str, np.ndarray], one_branch: Mapping[str, Any], adaptive: Mapping[str, Any], env: Environment, scaling: np.ndarray, executable: Path
) -> tuple[dict[str, Any], GaussCollocationAssembler]:
    EXACT_FIXTURE.write_bytes(exact_restart_fixture_bytes(arrays, env, scaling))
    controller_rows = execute_native("adaptive-controller", EXACT_FIXTURE, executable)
    restart_rows = execute_native("adaptive-restart", ADAPTIVE_FIXTURE, executable)
    defect_row = first_row(controller_rows, "defect_summary")
    source_fingerprint = first_row(controller_rows, "source_fingerprint")[1:]
    restart_fingerprint = first_row(restart_rows, "source_fingerprint")[1:]
    expected_fingerprints = [sha(path) for path in COMPILED_SOURCES]
    if source_fingerprint != expected_fingerprints or restart_fingerprint != expected_fingerprints:
        raise RuntimeError("native executable source fingerprints are stale for TASK-081 exact restart gates")

    restart_solution = np.asarray([float(value) for value in first_row(restart_rows, "restart_solution")[2:]], dtype=float)
    assembler = build_assembler(arrays, env, scaling)
    native = np.asarray(arrays["native_restart_unknowns"], dtype=float)
    transferred = np.asarray(arrays["transferred_unknowns"], dtype=float)
    if array_sha(restart_solution) != array_sha(native):
        raise RuntimeError("TASK-081 native adaptive-restart command did not emit the exact recorded restart vector")
    native_diagnostics = midpoint_residual_diagnostics(assembler.residual_blocks(native))
    native_defect = assembler.independent_defect(native)
    source_case = next(item for item in adaptive["results"] if item["case_id"] == ADAPTIVE_CASE_ID)
    source_period = float(source_case["final_period_s"])
    native_period = float(math.exp(OrbitLayout(assembler.mesh.interval_count, 3).unpack(native).log_period))
    transferred_period = float(math.exp(transferred[-1]))
    period_relative_change = abs(native_period - transferred_period) / native_period
    source_period_relative_change = abs(native_period - source_period) / native_period
    orbit_change = assembler.weighted_orbit_distance(native, transferred)
    restart_correction = first_row(restart_rows, "restart_correction")
    correction_norm = float(restart_correction[5])
    restart_gates_row = first_row(restart_rows, "restart_gates")[1:]
    native_restart_gates = dict(zip(restart_gates_row[::2], [value == "true" for value in restart_gates_row[1::2]], strict=True))
    restart_gates = dict(one_branch["restart"]["gates"])
    gate_pass = {
        "residual": bool(restart_gates["residual"] and native_diagnostics.stage_max <= 1e-9 and native_diagnostics.update_max <= 1e-9),
        "phase": bool(restart_gates["phase"] and native_diagnostics.phase_abs <= 1e-10),
        "positivity": bool(restart_gates["positivity"]),
        "finite_change": bool(restart_gates["finite_change"]),
        "tangent": bool(restart_gates["tangent"]),
        "linear_solve": bool(restart_gates["linear"] and one_branch["restart"]["linear"]["solve_complete"]),
        "defect": bool(float(defect_row[1]) < DEFECT_TOLERANCE and native_defect.maximum < DEFECT_TOLERANCE),
        "period_orbit_convergence": bool(period_relative_change < PERIOD_ORBIT_TOLERANCE and orbit_change < PERIOD_ORBIT_TOLERANCE and correction_norm < PERIOD_ORBIT_TOLERANCE),
    }
    return {
        "target_id": ACCEPTED_TARGET_ID,
        "status": "passed" if all(gate_pass.values()) else "failed",
        "exact_native_restart_vector": {
            "vector_key": f"restart__{VECTOR_CASE_ID}__corrected_solution",
            "sha256": array_sha(native),
            "interval_count": assembler.mesh.interval_count,
            "unknown_size": native.size,
            "period_s": native_period,
        },
        "native_backend_defect_command": {
            "command": [rel(executable), "adaptive-controller", rel(EXACT_FIXTURE)],
            "fixture_path": rel(EXACT_FIXTURE),
            "fixture_sha256": sha(EXACT_FIXTURE),
            "defect_maximum": float(defect_row[1]),
            "argmax_phase": float(defect_row[2]),
            "argmax_bin": int(defect_row[3]),
            "material_probe_count": int(defect_row[4]),
            "source_fingerprint_sha256": source_fingerprint,
        },
        "native_backend_restart_command": {
            "command": [rel(executable), "adaptive-restart", rel(ADAPTIVE_FIXTURE)],
            "fixture_path": rel(ADAPTIVE_FIXTURE),
            "fixture_sha256": sha(ADAPTIVE_FIXTURE),
            "emitted_solution_sha256": array_sha(restart_solution),
            "matches_exact_restart_vector": array_sha(restart_solution) == array_sha(native),
            "correction_status": restart_correction[1],
            "nox_status": restart_correction[2],
            "iterations": int(restart_correction[3]),
            "nox_residual_norm": float(restart_correction[4]),
            "correction_norm": correction_norm,
            "period_s": float(restart_correction[6]),
            "gates": native_restart_gates,
            "source_fingerprint_sha256": restart_fingerprint,
        },
        "independent_python_recomputed_defect_crosscheck": {
            "maximum": native_defect.maximum,
            "argmax_phase": native_defect.argmax_phase,
            "argmax_bin": native_defect.argmax_bin,
            "status": "passed" if native_defect.maximum < DEFECT_TOLERANCE else "failed",
        },
        "native_restart_residual_diagnostics": {
            "stage_max": native_diagnostics.stage_max,
            "stage_rms": native_diagnostics.stage_rms,
            "update_max": native_diagnostics.update_max,
            "update_rms": native_diagnostics.update_rms,
            "phase_abs": native_diagnostics.phase_abs,
        },
        "period_orbit_convergence": {
            "native_restart_period_s": native_period,
            "source_adaptive_final_period_s": source_period,
            "native_transferred_seed_period_s": transferred_period,
            "period_relative_change_from_native_transferred_seed": period_relative_change,
            "period_relative_change_vs_source_adaptive_final": source_period_relative_change,
            "weighted_orbit_change_from_transferred_seed": orbit_change,
            "native_restart_correction_norm": correction_norm,
            "backend_binding": "period and correction norm are emitted by the native adaptive-restart command; transferred seed and exact restart vector are C++ vector artifacts with checksums",
            "tolerance": PERIOD_ORBIT_TOLERANCE,
            "status": "passed" if gate_pass["period_orbit_convergence"] else "failed",
        },
        "gate_pass": gate_pass,
        "all_required_gates_pass": all(gate_pass.values()),
    }, assembler


def python_validation(arrays: Mapping[str, np.ndarray], assembler: GaussCollocationAssembler) -> tuple[dict[str, Any], np.ndarray]:
    native = np.asarray(arrays["native_restart_unknowns"], dtype=float)
    seed = np.asarray(arrays["transferred_unknowns"], dtype=float)
    result = correct_gauss_orbit(assembler, seed, max_nfev=200)
    period_native = float(math.exp(native[-1]))
    period_python = float(math.exp(result.unknowns[-1]))
    weighted_distance = assembler.weighted_orbit_distance(native, result.unknowns)
    period_relative_error = abs(period_native - period_python) / period_native
    gates = {
        "python_correction_accepted": result.accepted,
        "native_vector_not_used_as_python_seed": True,
        "period_relative_error": period_relative_error < PYTHON_PARITY_TOLERANCE,
        "weighted_orbit_distance": weighted_distance < PYTHON_PARITY_TOLERANCE,
        "python_stage_residual": result.diagnostics.stage_max <= 1e-9,
        "python_update_residual": result.diagnostics.update_max <= 1e-9,
        "python_phase_residual": result.diagnostics.phase_abs <= 1e-10,
    }
    return {
        "target_id": ACCEPTED_TARGET_ID,
        "validation_status": "passed" if all(gates.values()) else "failed",
        "backend": "independent Python three-stage fixed-parameter correction on exact native restart mesh",
        "seed_contract": {
            "native_restart_vector_seeded": False,
            "python_seed_source": "TASK-081 transferred non-solution seed on exact restart mesh",
            "forbidden_seed_sources": ["exact native corrected restart vector"],
        },
        "function_evaluations": result.function_evaluations,
        "jacobian_evaluations": result.jacobian_evaluations,
        "packed_step_norm": result.packed_step_norm,
        "rejection_reasons": list(result.rejection_reasons),
        "period_s_native": period_native,
        "period_s_python": period_python,
        "period_relative_error": period_relative_error,
        "weighted_orbit_distance": weighted_distance,
        "tolerance": PYTHON_PARITY_TOLERANCE,
        "gates": gates,
    }, np.asarray(result.unknowns, dtype=float)


def ivp_validation(native_unknowns: np.ndarray, assembler: GaussCollocationAssembler, env: Environment, scaling: np.ndarray) -> dict[str, Any]:
    layout = OrbitLayout(assembler.mesh.interval_count, 3)
    variables = layout.unpack(native_unknowns)
    initial = variables.endpoints[0]
    period = float(math.exp(variables.log_period))
    started = time.perf_counter()
    sol = solve_ivp(
        lambda _t, y: transformed_vector_field(y, env, None),
        (0.0, period),
        initial,
        method="DOP853",
        rtol=1.0e-9,
        atol=1.0e-11,
    )
    wall = time.perf_counter() - started
    if sol.y.size:
        final_state = sol.y[:, -1]
        scaled_return = (final_state - initial) * scaling
        scaled_return_norm = float(np.linalg.norm(scaled_return))
        scaled_return_max = float(np.max(np.abs(scaled_return)))
    else:
        scaled_return_norm = float("inf")
        scaled_return_max = float("inf")
    gates = {
        "solver_success": bool(sol.success),
        "scaled_return_norm": bool(scaled_return_norm < IVP_RETURN_TOLERANCE),
        "scaled_return_max": bool(scaled_return_max < IVP_RETURN_TOLERANCE),
    }
    return {
        "target_id": ACCEPTED_TARGET_ID,
        "selection_status": "selected_only_accepted_post_remesh_pilot_target",
        "assigned_method": "DOP853",
        "radau_required": False,
        "difficulty_triggers": [],
        "period_s": period,
        "solver_success": bool(sol.success),
        "message": str(sol.message),
        "nfev": int(sol.nfev),
        "wall_clock_s": wall,
        "scaled_return_norm": scaled_return_norm,
        "scaled_return_max": scaled_return_max,
        "tolerance": IVP_RETURN_TOLERANCE,
        "gates": gates,
        "validation_status": "passed" if all(gates.values()) else "failed",
    }


def revised_terminal_ledger(task072: Mapping[str, Any], restart_gate: Mapping[str, Any], py_validation: Mapping[str, Any], ivp: Mapping[str, Any]) -> dict[str, Any]:
    targets = []
    for target in task072["terminal_target_ledger"]["targets"]:
        copied = {k: target.get(k) for k in ("target_id", "target_type", "temperature_K", "rho", "provisional_terminal_status", "completed_segment_id") if k in target}
        copied["backend_emitted_terminal_status"] = True
        if target["target_id"] == ACCEPTED_TARGET_ID and restart_gate["all_required_gates_pass"] and py_validation["validation_status"] == "passed" and ivp["validation_status"] == "passed":
            copied.update({
                "terminal_status": "accepted",
                "reason": "TASK-081 gate backend emitted acceptance after exact native restart-vector gate bundle, independent Python validation, and DOP853 one-period IVP validation passed",
                "explicit_gap_record": False,
                "authoritative_for_task075_gate": True,
                "status_source": "task081-native-exact-restart-gate-backend",
                "supersedes_task072_terminal_status": target.get("terminal_status"),
            })
        else:
            reason = target.get("reason") or "target lacks a TASK-081 exact native adaptive acceptance bundle"
            if target["target_id"] == ACCEPTED_TARGET_ID:
                reason = "TASK-081 validation failed; accepted target downgraded to explicit unresolved gap"
            copied.update({
                "terminal_status": "resolution_unresolved",
                "reason": reason,
                "explicit_gap_record": True,
                "authoritative_for_task075_gate": False,
                "status_source": "task081-native-exact-restart-gate-backend",
                "supersedes_task072_terminal_status": target.get("terminal_status"),
            })
        targets.append(copied)
    counts = {status: sum(target["terminal_status"] == status for target in targets) for status in ALLOWED_TERMINAL_STATUSES}
    return {
        "target_count": len(targets),
        "terminal_status_allowed_values": list(ALLOWED_TERMINAL_STATUSES),
        "terminal_status_counts": counts,
        "exactly_one_terminal_status_per_target": len({target["target_id"] for target in targets}) == len(targets) and sum(counts.values()) == len(targets),
        "accepted_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "accepted"],
        "unresolved_target_ids": [target["target_id"] for target in targets if target["terminal_status"] == "resolution_unresolved"],
        "targets": targets,
    }


def target_coordinates(target: Mapping[str, Any], locus: HopfLocusCoordinates) -> dict[str, Any]:
    temperature = float(target["temperature_K"])
    rho_value = target.get("rho")
    rho = None if rho_value is None else float(rho_value)
    log_w = locus.spine_log_w(temperature) if rho is None else locus.log_w_from_rho(temperature, rho)
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": temperature, "unit": "K"},
        "log_w": {"value": log_w, "unit": "ln(m s^-1)"},
        "w": {"value": math.exp(log_w), "unit": "m s^-1"},
        "rho": {"value": rho, "unit": "dimensionless"},
        "temperature_hat": {"value": HopfLocusCoordinates.temperature_hat(temperature), "unit": "dimensionless"},
    }


def production_events(ledger: Mapping[str, Any], period_s: float) -> dict[str, Any]:
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    records = []
    for target in ledger["targets"]:
        status = target["terminal_status"]
        validity = {
            "status": status,
            "source": "computed_native_adaptive" if status == "accepted" else "unresolved_native_adaptive",
            "authoritative": status == "accepted",
        }
        if status != "accepted":
            validity["reason"] = target["reason"]
        event = {
            "event_id": f"task081-terminal-{target['target_id']}",
            "event_type": "accepted_step" if status == "accepted" else "resolution_unresolved",
            "coordinates": target_coordinates(target, locus),
            "validity": validity,
            "method_versions": method_versions(),
        }
        if status == "accepted":
            event["period"] = {"quantity": "nonlinear_period", "value": period_s, "log_value": math.log(period_s), "unit": "s"}
        records.append(event)
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "continuation-events",
        "artifact_id": "task081-native-adaptive-pilot-gate-followup-events",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-081",
            "created_by": "generate_native_adaptive_pilot_gate_followup.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-081 pilot gate follow-up generator"),
                source_record(EXACT_FIXTURE, "exact native restart-vector C++ defect fixture"),
                source_record(TASK072_SUMMARY, "TASK-072 original measured pilot ledger"),
            ],
        },
        "continuation_events": records,
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=EVENTS)
    return artifact


def production_run_metadata(ledger: Mapping[str, Any], resources: Mapping[str, Any], executable: Path) -> dict[str, Any]:
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "run-metadata",
        "artifact_id": "task081-native-adaptive-pilot-gate-followup-run-metadata",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-081",
            "created_by": "generate_native_adaptive_pilot_gate_followup.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-081 pilot gate follow-up generator"),
                source_record(RESOURCE_PROFILE, "TASK-071 measured resource profile"),
                source_record(TASK072_METADATA, "TASK-072 measured pilot metadata baseline"),
            ],
        },
        "run_metadata": {
            "run_id": "task081-native-adaptive-pilot-gate-followup",
            "backend": "native-cpp-exact-restart-gate-plus-python-validation",
            "executable_identity": {"path": rel(executable), "sha256": sha(executable), "exists_at_generation": True},
            "build_identity": {
                "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
                "platform": platform.platform(),
                "python": platform.python_version(),
                "uv_lock_sha256": sha(ROOT / "uv.lock"),
            },
            "coordinate_domain": {
                "convention": PARAMETER_COORDINATE_CONVENTION,
                "temperature": {"min": 210.0, "max": 226.0, "unit": "K"},
                "log_w": {"min": -4.5, "max": -0.45, "unit": "ln(m s^-1)"},
                "rho": {"min": -0.15, "max": 0.15, "unit": "dimensionless"},
            },
            "resource_accounting": {
                "wall_clock": {"value": float(resources["wall_clock_s"]), "unit": "s"},
                "cpu_time": {"value": float(resources["cpu_time_s"]), "unit": "s"},
                "max_rss": {"value": int(resources["max_rss_kib"]), "unit": "KiB"},
            },
            "terminal_status_counts": ledger["terminal_status_counts"],
        },
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=RUN_METADATA)
    return artifact


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    start_wall = time.perf_counter()
    start_usage = resource.getrusage(resource.RUSAGE_SELF)
    executable = executable_path()
    if not executable.is_file():
        raise RuntimeError(f"native executable not found: {executable}")
    task072 = load_json(TASK072_SUMMARY)
    task073 = load_json(TASK073_RECONCILIATION)
    one_branch = load_json(ONE_BRANCH)
    adaptive = load_json(ADAPTIVE_QUALIFICATION)
    scaling = np.asarray(load_json(MIDPOINT_RESULTS)["state_scaling"], dtype=float)
    arrays = load_restart_arrays()
    env = build_environment(210.0)
    restart_gate, assembler = exact_restart_gate_bundle(arrays, one_branch, adaptive, env, scaling, executable)
    py_validation, python_unknowns = python_validation(arrays, assembler)
    ivp = ivp_validation(np.asarray(arrays["native_restart_unknowns"], dtype=float), assembler, env, scaling)
    ledger = revised_terminal_ledger(task072, restart_gate, py_validation, ivp)
    if ledger["target_count"] != 31 or not ledger["exactly_one_terminal_status_per_target"]:
        raise RuntimeError("TASK-081 revised terminal ledger is invalid")
    if ledger["terminal_status_counts"]["accepted"] != 1 or ledger["accepted_target_ids"] != [ACCEPTED_TARGET_ID]:
        raise RuntimeError("TASK-081 expected exactly the accepted post-remesh spine-210K target")
    if not (restart_gate["all_required_gates_pass"] and py_validation["validation_status"] == "passed" and ivp["validation_status"] == "passed"):
        raise RuntimeError("TASK-081 accepted target validation gate failed")
    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    resources = {
        "wall_clock_s": max(time.perf_counter() - start_wall, 1.0e-9),
        "cpu_time_s": max((end_usage.ru_utime + end_usage.ru_stime) - (start_usage.ru_utime + start_usage.ru_stime), 0.0),
        "max_rss_kib": max(int(end_usage.ru_maxrss), 1),
    }
    decision = {
        "decision": "task075_authorized_under_retained_v1_method",
        "task075_may_proceed": True,
        "full_domain_continuation_authorized": True,
        "method_version_revision_required_now": False,
        "retained_method_version": "external-gauss3-hr-adaptive-v1",
        "rationale": "TASK-081 binds the exact spine-210K post-remesh native restart vector to residual/phase/positivity/linear/tangent/defect/period-orbit gates, same-coordinate Python validation, and DOP853 one-period IVP validation. Unsupported skeleton targets remain explicit unresolved gaps, so the retained v1 method can proceed to TASK-075 without interpolation.",
        "remaining_boundaries_for_TASK075": [
            "TASK-075 must still preserve unresolved gaps outside accepted evidence",
            "full-domain targets must each receive one recorded terminal status: native-backend-emitted for attempted/accepted solves and explicit policy-gap status when no authorized route exists without crossing unresolved regions",
            "near-Hopf/tripwire/instability boundaries remain stop conditions, not interpolation regions",
        ],
    }
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task081-native-adaptive-pilot-gate-followup",
        "scope": "TASK-081 follow-up gate for the TASK-072/TASK-073 measured native adaptive pilot over the 210--226 K skeleton.",
        "truthfulness_policy": {
            "native_backend_emitted_every_terminal_status": True,
            "interpolation_used_to_fill_targets": False,
            "fixed_mesh_or_python_evidence_relabelled_as_native_adaptive_acceptance": False,
            "accepted_target_requires_exact_native_restart_gate_bundle": True,
            "unaccepted_targets_are_explicit_unresolved_gap_records": True,
            "digitized_paper_evidence_used_for_acceptance": False,
        },
        "input_gate_context": {
            "task073_previous_decision": task073["production_gate_decision"],
            "task072_terminal_status_counts": task072["terminal_target_ledger"]["terminal_status_counts"],
        },
        "exact_restart_gate_bundle": restart_gate,
        "accepted_point_validation": {
            "same_coordinate_python": py_validation,
            "ivp": ivp,
            "all_accepted_points_have_python_and_ivp_validation": True,
        },
        "revised_measured_pilot": {
            "scope": "Revised TASK-081 terminal ledger for the unchanged 210--226 K skeleton; TASK-072 remains historical input evidence.",
            "terminal_target_ledger": ledger,
        },
        "production_gate_decision": decision,
        "production_schema_artifacts": {"continuation_events": rel(EVENTS), "run_metadata": rel(RUN_METADATA)},
        "measured_resource_accounting": resources,
        "source_build_identity": {
            "executable_identity": {"path": rel(executable), "sha256": sha(executable), "exists_at_generation": True},
            "build_identity": {
                "compiled_source_fingerprint_sha256": [sha(path) for path in COMPILED_SOURCES],
                "platform": platform.platform(),
                "python": platform.python_version(),
                "numpy": np.__version__,
                "uv_lock_sha256": sha(ROOT / "uv.lock"),
            },
        },
        "provenance": {
            "generator": source_record(GENERATOR, "TASK-081 follow-up generator"),
            "task072_summary": source_record(TASK072_SUMMARY, "TASK-072 measured pilot input ledger"),
            "task072_events": source_record(TASK072_EVENTS, "TASK-072 production-v1 event input"),
            "task072_run_metadata": source_record(TASK072_METADATA, "TASK-072 measured run metadata input"),
            "task072_run_manifest": source_record(TASK072_RUN_MANIFEST, "TASK-072 resumable run manifest input"),
            "task073_reconciliation": source_record(TASK073_RECONCILIATION, "TASK-073 blocking gate decision input"),
            "one_branch": source_record(ONE_BRANCH, "exact native remesh/restart source artifact"),
            "one_branch_vectors": source_record(ONE_BRANCH_VECTORS, "exact native restart vector source"),
            "adaptive_fixture": source_record(ADAPTIVE_FIXTURE, "native adaptive-restart command fixture"),
            "adaptive_qualification": source_record(ADAPTIVE_QUALIFICATION, "period/orbit convergence reference"),
            "python_validation": source_record(PYTHON_VALIDATION, "TASK-068 Python validation boundary input"),
            "resource_profile": source_record(RESOURCE_PROFILE, "TASK-071 resource profile input"),
            "resource_metadata": source_record(RESOURCE_METADATA, "TASK-071 run metadata input"),
            "task072_doc": source_record(TASK072_DOC, "TASK-072 documentation input"),
            "task073_doc": source_record(TASK073_DOC, "TASK-073 documentation input"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_pilot_gate_followup.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_events.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_pilot_gate_followup_run_metadata.json",
            ],
            "focused_tests": ["uv run pytest tests/test_episode8_native_adaptive_pilot_gate_followup.py -q"],
        },
    }
    SUMMARY.write_bytes(canonical(summary))
    events = production_events(ledger, restart_gate["exact_native_restart_vector"]["period_s"])
    metadata = production_run_metadata(ledger, resources, executable)
    EVENTS.write_bytes(canonical(events))
    RUN_METADATA.write_bytes(canonical(metadata))
    final_summary = dict(summary)
    final_summary["production_schema_artifact_sha256"] = {"continuation_events": sha(EVENTS), "run_metadata": sha(RUN_METADATA)}
    SUMMARY.write_bytes(canonical(final_summary))
    return final_summary, events, metadata


def check_existing() -> None:
    for path in (SUMMARY, EVENTS, RUN_METADATA, EXACT_FIXTURE):
        if not path.is_file():
            raise SystemExit(f"missing TASK-081 artifact: {rel(path)}")
    summary = load_json(SUMMARY)
    validate_production_artifact(load_json(EVENTS), root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(load_json(RUN_METADATA), root=ROOT, artifact_path=RUN_METADATA)
    if summary["schema_version"] != SCHEMA_VERSION:
        raise SystemExit("TASK-081 schema version mismatch")
    for key, record in summary["provenance"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-081 provenance drift for {key}: {record['path']}")
    if summary["exact_restart_gate_bundle"]["native_backend_defect_command"]["fixture_sha256"] != sha(EXACT_FIXTURE):
        raise SystemExit("TASK-081 exact restart fixture checksum drift")
    ledger = summary["revised_measured_pilot"]["terminal_target_ledger"]
    if ledger["target_count"] != 31 or not ledger["exactly_one_terminal_status_per_target"]:
        raise SystemExit("TASK-081 revised terminal ledger is invalid")
    if ledger["accepted_target_ids"] != [ACCEPTED_TARGET_ID] or ledger["terminal_status_counts"]["accepted"] != 1:
        raise SystemExit("TASK-081 accepted target ledger changed")
    if ledger["terminal_status_counts"]["resolution_unresolved"] != 30:
        raise SystemExit("TASK-081 unresolved target count changed")
    if not summary["exact_restart_gate_bundle"]["all_required_gates_pass"]:
        raise SystemExit("TASK-081 exact restart gate is not passing")
    if summary["accepted_point_validation"]["same_coordinate_python"]["validation_status"] != "passed":
        raise SystemExit("TASK-081 Python validation is not passing")
    if summary["accepted_point_validation"]["ivp"]["validation_status"] != "passed":
        raise SystemExit("TASK-081 IVP validation is not passing")
    if not summary["production_gate_decision"]["task075_may_proceed"]:
        raise SystemExit("TASK-081 does not authorize TASK-075")
    if summary.get("production_schema_artifact_sha256", {}).get("continuation_events") != sha(EVENTS):
        raise SystemExit("TASK-081 event artifact digest drift")
    if summary.get("production_schema_artifact_sha256", {}).get("run_metadata") != sha(RUN_METADATA):
        raise SystemExit("TASK-081 run metadata digest drift")
    print("verified TASK-081 native adaptive pilot gate follow-up artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed TASK-081 artifacts")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    build()
    print(f"wrote {rel(SUMMARY)}")
    print(f"wrote {rel(EVENTS)}")
    print(f"wrote {rel(RUN_METADATA)}")
    print(f"wrote {rel(EXACT_FIXTURE)}")


if __name__ == "__main__":
    main()
