#!/usr/bin/env python3
"""Generate deterministic native fixed-mesh Gauss LOCA continuation artifacts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from bergner_spichtinger_2026 import (  # noqa: E402
    FixedMesh, FixedTemperatureRhoPath, FrozenPhaseReference, GaussCollocationAssembler,
    HopfLocusCoordinates, SpineTemperaturePath, correct_gauss_orbit, gauss_legendre_rule,
)
from bergner_spichtinger_2026.constants import Environment  # noqa: E402
from bergner_spichtinger_2026.periodic_orbits import transformed_vector_field  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
FIXTURES = OUTPUT / "cpp_higher_order_fixtures"
G2_FIXTURE = FIXTURES / "canonical-g2-n64.txt"
G3_FIXTURE = FIXTURES / "canonical-g3-n32.txt"
QUALIFICATION = OUTPUT / "higher_order_fixed_mesh_qualification.json"
QUALIFICATION_VECTORS = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
MIDPOINT_RESULTS = OUTPUT / "fixed_mesh_midpoint_results.json"
MIDPOINT_BRANCH_VECTORS = OUTPUT / "fixed_mesh_continuation_vectors.npz"
BOOTSTRAP_SEED = OUTPUT / "bootstrap_seed.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
RESULTS = OUTPUT / "native_loca_higher_order_results.json"
VECTORS = OUTPUT / "native_loca_higher_order_vectors.npz"
EXECUTABLE = Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", ROOT / "loca-build/bs2026_midpoint_orbit"))
BRANCH_IDS = (
    "fixed225-to-spine", "spine-positive-T-hat", "spine-negative-T-hat-to-210",
    "slice210-negative-rho", "slice210-positive-rho",
)
PERIOD_RTOL = 2.0e-7
ORBIT_TOL = 2.0e-7
DFDP_RELATIVE_TOLERANCE = 2.0e-6


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


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


def execute(command: str, fixture: Path) -> list[list[str]]:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Build native executable first or set BS2026_MIDPOINT_EXECUTABLE: {EXECUTABLE}")
    completed = subprocess.run(
        [str(EXECUTABLE), command, str(fixture)], cwd=ROOT, text=True,
        capture_output=True, check=True,
    )
    return [line.split() for line in completed.stdout.splitlines() if line.strip()]


def expected_fingerprint() -> list[str]:
    return [sha(ROOT / path) for path in (
        "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
        "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
        "loca/include/bergner_spichtinger_2026_loca/model.hpp",
        "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
        "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
        "loca/src/midpoint_orbit_cli.cpp",
    )]


def validate_event_accounting(
    events: list[dict[str, Any]], *, point_count: int, raw_step_number: int,
    raw_failed_step_count: int, raw_total_step_count: int,
) -> dict[str, Any]:
    if [event["callback_index"] for event in events] != list(range(len(events))):
        raise RuntimeError("native callback indices are not contiguous")
    initial = [event for event in events if event["save_role"] == "initial"]
    final = [event for event in events if event["save_role"] == "final"]
    regular = [event for event in events if event["save_role"] == "regular"]
    accepted = [event for event in events if event["status"] == "accepted"]
    rejected = [event for event in events if event["status"] == "rejected"]
    regular_accepted = [event for event in regular if event["status"] == "accepted"]
    regular_rejected = [event for event in regular if event["status"] == "rejected"]
    if len(initial) != 1 or len(final) != 1 or initial[0]["status"] != "accepted" or final[0]["status"] != "accepted":
        raise RuntimeError("native callbacks require exactly one accepted initial and final save")
    if len(regular) != len(regular_accepted) + len(regular_rejected):
        raise RuntimeError("regular native attempts do not partition into accepted and rejected")
    if point_count != len(accepted):
        raise RuntimeError("native saved-point count does not reconcile with accepted callbacks")
    for rejected_event in rejected:
        index = rejected_event["callback_index"]
        if index + 1 >= len(events) or events[index + 1]["save_role"] != "regular":
            raise RuntimeError("rejected native callback is not adjacent to a regular retry")
        if not np.isclose(rejected_event["retry_coordinate_delta"],
                          events[index + 1]["attempted_coordinate_delta"], rtol=0.0, atol=1e-15):
            raise RuntimeError("rejected callback retry delta is not linked to the adjacent retry")
    if raw_total_step_count != len(regular) or raw_failed_step_count != len(regular_rejected):
        raise RuntimeError("raw LOCA failed/total counts disagree with callback accounting")
    if raw_step_number != len(regular_accepted) + 1:
        raise RuntimeError("raw LOCA step number disagrees with accepted regular callbacks")
    return {
        "callback_indices_contiguous": True,
        "exactly_one_accepted_initial_and_final": True,
        "regular_attempts_equal_accepted_plus_rejected": True,
        "saved_points_equal_accepted_callbacks": True,
        "rejected_retries_are_adjacent_and_linked": True,
        "raw_counts_consistent": True,
    }


def metric_summary(weights: np.ndarray, n: int, r: int) -> dict[str, Any]:
    state_scaling = np.asarray(json.loads(MIDPOINT_RESULTS.read_text())["state_scaling"], dtype=float)
    endpoints = weights[:3*n].reshape(n, 3)
    stages = weights[3*n:3*n*(r+1)].reshape(n, r, 3)
    return {
        "dimension": int(weights.size),
        "endpoint_weight_sums_by_component": endpoints.sum(axis=0).tolist(),
        "stage_weight_sums_by_component": stages.sum(axis=(0, 1)).tolist(),
        "expected_half_scaled_l2_weight_by_component": (0.5 * state_scaling**2).tolist(),
        "log_period_weight": float(weights[-2]), "coordinate_weight": float(weights[-1]),
    }


def smoke_contract(fixture: Path, n: int, r: int) -> dict[str, Any]:
    rows = execute("loca-smoke", fixture)
    find = lambda name: next(row for row in rows if row[0] == name)
    c, method, rule, metric, result, build_identity, cmake_identity = (
        find("loca_contract"), find("loca_method"), find("rule"), find("metric"), find("loca_result"),
        find("build_identity"), find("cmake_identity"),
    )
    fingerprint = find("source_fingerprint")[1:]
    if fingerprint != expected_fingerprint():
        raise RuntimeError("native executable source fingerprint does not match the current checkout")
    weights = np.asarray(metric[2:], dtype=float)
    if int(metric[1]) != weights.size:
        raise RuntimeError("native metric dimension mismatch")
    forced_result = find("forced_rejection_result")
    forced_events = [row for row in rows if row[0] == "forced_rejection_event"]
    events = [{
        "callback_index": int(row[1]), "status": row[2],
        "attempted_coordinate": float(row[3]), "accepted_coordinate": float(row[4]),
        "attempted_coordinate_delta": float(row[5]), "retry_coordinate_delta": float(row[6]),
        "save_role": row[7],
    } for row in forced_events]
    rejected = [event for event in events if event["status"] == "rejected"]
    if len(rejected) != 1 or not 0 < abs(rejected[0]["retry_coordinate_delta"]) < abs(rejected[0]["attempted_coordinate_delta"]):
        raise RuntimeError("forced native rejection did not produce one reduced retry")
    forced_invariants = validate_event_accounting(
        events, point_count=int(forced_result[4]), raw_step_number=int(forced_result[1]),
        raw_failed_step_count=int(forced_result[2]), raw_total_step_count=int(forced_result[3]),
    )
    derivative_rows = execute("loca-dfdp", fixture)
    derivative_checks = []
    for path_name in ("rho", "temperature_hat"):
        summary = next(row for row in derivative_rows if row[0] == "dfdp" and row[1] == path_name)
        column = np.asarray(next(row for row in derivative_rows
                                 if row[0] == "dfdp_column" and row[1] == path_name)[3:], dtype=float)
        centered = np.asarray(next(row for row in derivative_rows
                                   if row[0] == "dfdp_centered_difference" and row[1] == path_name)[3:], dtype=float)
        measured = float(np.linalg.norm(column - centered) / max(1.0, np.linalg.norm(column)))
        if column.size != 3*n*(r+1)+1 or measured > DFDP_RELATIVE_TOLERANCE:
            raise RuntimeError(f"native Thyra DfDp centered-difference check failed for {path_name}, r={r}")
        if float(summary[4]) != float(summary[9]) or not np.isclose(float(summary[5]), float(summary[7]), atol=1e-14) \
                or not np.isclose(float(summary[6]), float(summary[8]), atol=1e-14):
            raise RuntimeError(f"native Thyra DfDp trial environment was not restored for {path_name}, r={r}")
        derivative_checks.append({
            "path": path_name, "requested_out_arg": "OUT_ARG_DfDp DERIV_MV_BY_COL",
            "finite_difference": "centered residual evaluations through the same ContinuationModelEvaluator",
            "epsilon": float(summary[2]), "emitted_relative_error": float(summary[3]),
            "recomputed_relative_error": measured, "relative_tolerance": DFDP_RELATIVE_TOLERANCE,
            "restored_coordinate": float(summary[4]), "restored_temperature_K": float(summary[5]),
            "restored_log_w": float(summary[6]), "expected_temperature_K": float(summary[7]),
            "expected_log_w": float(summary[8]),
        })
    return {
        "continuation_version": c[1], "parameter_vector_count": int(c[2]),
        "parameter_dimension": int(c[3]), "base_dimension": int(c[4]),
        "extended_dimension": int(c[5]), "phase_row": int(c[6]),
        "log_period_index": int(c[7]), "base_has_arclength": method[5] == "true",
        "continuation_method": method[1], "native_stepper": method[3] == "true",
        "metric_version": method[7], "rule": {"family": rule[1], "stage_count": int(rule[2]),
            "formal_order": int(rule[3]), "coefficient_artifact_sha256": rule[4]},
        "mesh": {"interval_count": n, "stage_count": r},
        "dimensions": {"base": 3*n*(r+1)+1, "extended": 3*n*(r+1)+2,
                       "stage_block": 3*n*r, "endpoint_block": 3*n},
        "metric": metric_summary(weights, n, r),
        "build_provenance": {"compiler_and_trilinos": build_identity[1:],
                             "cmake_source_sha256": cmake_identity[1],
                             "cmake_build_type": cmake_identity[2]},
        "model_evaluator_dfdp_checks": derivative_checks,
        "smoke": {"raw_step_number": int(result[1]), "raw_failed_step_count": int(result[2]),
                  "raw_total_step_count": int(result[3]), "saved_point_count": int(result[6]),
                  "predictor": result[7], "step_size": result[8]},
        "forced_native_rejection": {"raw_step_number": int(forced_result[1]),
            "raw_failed_step_count": int(forced_result[2]), "raw_total_step_count": int(forced_result[3]),
            "saved_point_count": int(forced_result[4]), "derived_regular_attempt_count": int(forced_result[5]),
            "derived_regular_accepted_count": int(forced_result[6]),
            "derived_regular_rejected_count": int(forced_result[7]), "events": events,
            "accounting_invariants": forced_invariants},
        "source_fingerprint_sha256": fingerprint,
    }


def python_context() -> tuple[
    FixedMesh, Any, np.ndarray, dict[str, Any], dict[str, np.ndarray]
]:
    qualification = json.loads(QUALIFICATION.read_text())
    result = next(item for item in qualification["results"] if item["case_id"] == "canonical-g3-n32")
    with np.load(QUALIFICATION_VECTORS, allow_pickle=False) as archive:
        arrays = {key: np.asarray(archive[key], dtype=float) for key in archive.files}
    mesh = FixedMesh(arrays["canonical-g3-n32__boundaries"])
    rule = gauss_legendre_rule(3)
    scaling = np.asarray(json.loads(MIDPOINT_RESULTS.read_text())["state_scaling"], dtype=float)
    reference = FrozenPhaseReference(
        mesh, arrays["canonical-g3-n32__phase_values"], arrays["canonical-g3-n32__phase_derivatives"],
        scaling, np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
    )
    return mesh, rule, scaling, {"qualification_record": result, "initial_reference": reference}, arrays


def refreshed_reference(assembler: GaussCollocationAssembler, unknowns: np.ndarray) -> FrozenPhaseReference:
    variables = assembler.layout.unpack(unknowns)
    period = float(np.exp(variables.log_period))
    derivatives = np.empty_like(variables.stages)
    for interval in range(assembler.layout.interval_count):
        for stage in range(assembler.layout.stage_count):
            derivatives[interval, stage] = period * transformed_vector_field(
                variables.stages[interval, stage], assembler.env, assembler.coeff
            )
    return FrozenPhaseReference(
        assembler.mesh, variables.stages, derivatives, assembler.state_scaling,
        np.asarray(assembler.rule.nodes), np.asarray(assembler.rule.quadrature_weights),
    )


def python_segment_setup() -> tuple[dict[str, dict[str, Any]], np.ndarray]:
    mesh, rule, scaling, context, arrays = python_context()
    parameters = json.loads(BOOTSTRAP_SEED.read_text())["canonical_parameters"]
    environment = Environment(
        T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
        N_a=parameters["N_a"], Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    fixed225 = FixedTemperatureRhoPath(locus, environment, 225.0)
    spine = SpineTemperaturePath(locus, environment)
    slice210 = FixedTemperatureRhoPath(locus, environment, 210.0)
    initial_seed = arrays["canonical-g3-n32__unknowns"].copy()
    initial_reference = context["initial_reference"]

    def assembler(path: Any, reference: FrozenPhaseReference, coordinate: float) -> GaussCollocationAssembler:
        return GaussCollocationAssembler(mesh, path.environment(coordinate), reference, rule)

    def seed_bank(path: Any, reference: FrozenPhaseReference, origin: float, target: float,
                  origin_seed: np.ndarray, maximum_coordinate_step: float,
                  bank_id: str) -> list[dict[str, Any]]:
        count = max(1, int(np.ceil(abs(target - origin) / maximum_coordinate_step)))
        coordinates = np.linspace(origin, target, count + 1)
        bank = [{"coordinate": float(origin), "unknowns": np.asarray(origin_seed).copy(),
                 "seed_id": f"{bank_id}-000"}]
        current = np.asarray(origin_seed).copy()
        for index, coordinate in enumerate(coordinates[1:], 1):
            corrected = correct_gauss_orbit(assembler(path, reference, float(coordinate)), current.copy())
            if not corrected.accepted:
                raise RuntimeError(f"independent Python seed bank {bank_id} failed at {coordinate}")
            current = np.asarray(corrected.unknowns).copy()
            bank.append({"coordinate": float(coordinate), "unknowns": current,
                         "seed_id": f"{bank_id}-{index:03d}"})
        return bank

    origin_rho = locus.rho(225.0, float(np.log(environment.w)))
    fixed_bank = seed_bank(fixed225, initial_reference, origin_rho, 0.0, initial_seed, 0.02,
                           "Python-g3-fixed225")
    spine225_seed = np.asarray(fixed_bank[-1]["unknowns"]).copy()
    spine_reference = refreshed_reference(assembler(fixed225, initial_reference, 0.0), spine225_seed)
    spine_positive_bank = seed_bank(spine, spine_reference, 0.4, 0.44, spine225_seed, 0.01,
                                    "Python-g3-spine-positive")
    spine_negative_bank = seed_bank(spine, spine_reference, 0.4, -0.2, spine225_seed, 0.04,
                                    "Python-g3-spine-negative")
    spine210_seed = np.asarray(spine_negative_bank[-1]["unknowns"]).copy()
    slice_reference = refreshed_reference(assembler(spine, spine_reference, -0.2), spine210_seed)
    slice_negative_bank = seed_bank(slice210, slice_reference, 0.0, -0.15, spine210_seed, 0.02,
                                    "Python-g3-slice-negative")
    slice_positive_bank = seed_bank(slice210, slice_reference, 0.0, 0.15, spine210_seed, 0.02,
                                    "Python-g3-slice-positive")

    widths = mesh.widths
    metric = np.zeros(3 * mesh.interval_count * 4 + 2)
    for interval, width in enumerate(widths):
        metric[3*interval:3*interval+3] = 0.25 * (width + widths[interval-1]) * scaling**2
        for stage, weight in enumerate(rule.quadrature_weights):
            start = 3*mesh.interval_count + 3*(interval*3 + stage)
            metric[start:start+3] = 0.5 * width * weight * scaling**2
    metric[-2:] = 1.0
    return {
        "phase-ref-episode007-seed": {"path": fixed225, "reference": initial_reference,
            "seed_bank": fixed_bank},
        "phase-ref-spine-225": {"path": spine, "reference": spine_reference,
            "seed_bank": spine_positive_bank + spine_negative_bank},
        "phase-ref-slice-210": {"path": slice210, "reference": slice_reference,
            "seed_bank": slice_negative_bank + slice_positive_bank},
    }, metric


def build() -> tuple[bytes, bytes]:
    contracts = {"gauss_2": smoke_contract(G2_FIXTURE, 64, 2),
                 "gauss_3": smoke_contract(G3_FIXTURE, 32, 3)}
    rows = execute("loca-branches", G3_FIXTURE)
    if next(row for row in rows if row[0] == "source_fingerprint")[1:] != expected_fingerprint():
        raise RuntimeError("native branch executable source fingerprint does not match current checkout")
    branch_build_identity = next(row for row in rows if row[0] == "build_identity")[1:]
    branch_cmake_identity = next(row for row in rows if row[0] == "cmake_identity")[1:]
    expected_cmake_sha = sha(ROOT / "loca/CMakeLists.txt")
    if branch_cmake_identity != [expected_cmake_sha, "build_type_Release"]:
        raise RuntimeError("native executable CMake source/config identity does not match this Release checkout")
    for contract in contracts.values():
        provenance = contract["build_provenance"]
        if provenance["compiler_and_trilinos"] != branch_build_identity or \
                [provenance["cmake_source_sha256"], provenance["cmake_build_type"]] != branch_cmake_identity:
            raise RuntimeError("native smoke/branch build provenance is inconsistent")
    families, metric = python_segment_setup()
    arrays: dict[str, np.ndarray] = {}
    branches: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []
    events_by_branch: dict[str, list[dict[str, Any]]] = {}
    maximum_period_error = maximum_orbit_error = 0.0

    for begin in [row for row in rows if row[0] == "branch_begin"]:
        _, branch_id, reference_id, coordinate_name, origin, target = begin
        point_rows = [row for row in rows if row[0] == "branch_point" and row[1] == branch_id]
        validation_rows = [row for row in rows if row[0] == "branch_validation" and row[1] == branch_id]
        bootstrap_rows = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == branch_id]
        event_rows = [row for row in rows if row[0] == "branch_event" and row[1] == branch_id]
        restart = next(row for row in rows if row[0] == "branch_restart" and row[1] == branch_id)
        end = next(row for row in rows if row[0] == "branch_end" and row[1] == branch_id)
        if len(validation_rows) != len(point_rows):
            raise RuntimeError(f"missing native accepted-point validation on {branch_id}")
        family = families[reference_id]
        ordered_branch_events: list[dict[str, Any]] = []
        for bootstrap in bootstrap_rows:
            ordered_branch_events.append({"event_type": "native_branch_bootstrap_attempt", "backend": "fixed-parameter NOX/KLU2",
                "branch_id": branch_id, "phase_reference_id": reference_id, "attempt": int(bootstrap[2]),
                "requested_coordinate_step": float(bootstrap[3]), "trial_coordinate": float(bootstrap[4]),
                "accepted": bootstrap[5] == "accepted", "weighted_step_norm": float(bootstrap[6])})
        branch_events = []
        for event in event_rows:
            parsed_event = {"event_type": "native_loca_step", "backend": "LOCA::Stepper",
                "branch_id": branch_id, "phase_reference_id": reference_id, "callback_index": int(event[2]),
                "status": event[3], "accepted": event[3] == "accepted", "attempted_coordinate": float(event[4]),
                "accepted_coordinate": float(event[5]), "attempted_coordinate_delta": float(event[6]),
                "retry_coordinate_delta": float(event[7]), "save_role": event[8]}
            branch_events.append(parsed_event)
            ordered_branch_events.append(parsed_event)
        events_by_branch[branch_id] = ordered_branch_events
        for row, validation in zip(point_rows, validation_rows):
            index, coordinate, period = int(row[2]), float(row[4]), float(row[5])
            native = np.asarray(row[6:], dtype="<f8")
            expected_size = contracts["gauss_3"]["base_dimension"]
            if native.size != expected_size:
                raise RuntimeError(f"unexpected native vector size on {branch_id}: {native.size}")
            assembler = GaussCollocationAssembler(
                family["reference"].mesh, family["path"].environment(coordinate),
                family["reference"], gauss_legendre_rule(3),
            )
            # Every comparison is a separate SciPy correction at the exact
            # native coordinate, initialized from the nearest point in a
            # deterministic Python-only coordinate bank whose grid is fixed
            # independently of LOCA's adaptive points.  The native vector is
            # used only after correction to measure parity.
            seed = min(family["seed_bank"], key=lambda item: abs(float(item["coordinate"]) - coordinate))
            correction = correct_gauss_orbit(assembler, np.asarray(seed["unknowns"]).copy())
            if not correction.accepted:
                raise RuntimeError(f"independent Python correction failed at {branch_id}[{index}]")
            corrected = np.asarray(correction.unknowns)
            corrected_period = float(np.exp(corrected[-1]))
            period_error = abs(period - corrected_period) / corrected_period
            orbit_error = float(np.sqrt(np.dot(metric[:-1], (native - corrected)**2)))
            maximum_period_error = max(maximum_period_error, period_error)
            maximum_orbit_error = max(maximum_orbit_error, orbit_error)
            if period_error > PERIOD_RTOL or orbit_error > ORBIT_TOL:
                raise RuntimeError(f"native/Python parity failed at {branch_id}[{index}]: {period_error}, {orbit_error}")
            vector_key = f"native_g3__{branch_id}__{index:03d}"
            arrays[vector_key] = native
            points.append({"point_id": f"native-g3-{branch_id}-{index:03d}", "branch_id": branch_id,
                "point_index": index, "phase_reference_id": reference_id,
                "active_coordinate_name": coordinate_name, "active_coordinate": coordinate,
                "period_s": period, "vector_key": vector_key,
                "native_validation": {"stage_residual_max": float(validation[3]),
                    "stage_residual_rms": float(validation[4]), "update_residual_max": float(validation[5]),
                    "update_residual_rms": float(validation[6]), "phase_residual_abs": float(validation[7]),
                    "physical_states_positive_finite": validation[8] == "true",
                    "period_positive_finite": validation[9] == "true", "linear_backend": validation[10],
                    "linear_solve_complete": validation[11] == "true",
                    "fixed_parameter_weighted_distance_from_native": float(validation[12])},
                "python_correction_seed_id": str(seed["seed_id"]),
                "python_correction_seed_coordinate": float(seed["coordinate"]),
                "python_correction_seed_origin": "deterministic frozen/Python-only bank independent of native adaptive coordinates",
                "python_correction_function_evaluations": correction.function_evaluations,
                "python_correction_jacobian_evaluations": correction.jacobian_evaluations,
                "python_correction_stage_residual_max": correction.diagnostics.stage_max,
                "python_correction_update_residual_max": correction.diagnostics.update_max,
                "python_correction_phase_residual_abs": correction.diagnostics.phase_abs,
                "python_same_coordinate_period_relative_error": period_error,
                "python_same_coordinate_weighted_orbit_error": orbit_error})
        accounting = validate_event_accounting(
            branch_events, point_count=len(point_rows), raw_step_number=int(end[2]),
            raw_failed_step_count=int(end[3]), raw_total_step_count=int(end[4]),
        )
        direction = np.sign(float(target) - float(origin))
        signed_component, signed_norm = float(restart[2]), float(restart[3])
        injected_component, injected_norm, signed_initial_step = map(float, restart[4:7])
        canonicalized = restart[7] == "true"
        if np.sign(signed_component) != direction or np.sign(signed_initial_step) != direction:
            raise RuntimeError(f"signed bootstrap/step orientation mismatch on {branch_id}")
        if injected_component <= 0.0 or not np.isclose(signed_norm, 1.0, atol=2e-14) \
                or not np.isclose(injected_norm, 1.0, atol=2e-14) or canonicalized != (direction < 0):
            raise RuntimeError(f"injected Restart orientation/norm mismatch on {branch_id}")
        if (int(end[5]), int(end[6]), int(end[7]), int(end[8]), int(end[9])) != (
                1, 1, len(branch_events) - 2, len([event for event in branch_events
                                                   if event["save_role"] == "regular" and event["accepted"]]),
                len([event for event in branch_events
                     if event["save_role"] == "regular" and not event["accepted"]])):
            raise RuntimeError(f"emitted native branch summary disagrees with callbacks on {branch_id}")
        branches.append({"branch_id": branch_id, "phase_reference_id": reference_id,
            "active_coordinate_name": coordinate_name, "origin_coordinate": float(origin),
            "target_coordinate": float(target), "native_point_count": len(point_rows),
            "native_bootstrap_attempt_count": len(bootstrap_rows), "raw_loca_step_number": int(end[2]),
            "raw_loca_failed_step_count": int(end[3]), "raw_loca_total_step_count": int(end[4]),
            "derived_initial_save_count": int(end[5]), "derived_final_save_count": int(end[6]),
            "derived_regular_attempt_count": int(end[7]), "derived_regular_accepted_count": int(end[8]),
            "derived_regular_rejected_count": int(end[9]), "derived_callback_count": len(event_rows),
            "used_bootstrap_restart_tangent": end[10] == "true",
            "restart_orientation": {"signed_bootstrap_parameter_component": signed_component,
                "signed_bootstrap_weighted_norm": signed_norm,
                "injected_parameter_component": injected_component,
                "injected_weighted_norm": injected_norm,
                "signed_initial_step": signed_initial_step,
                "injected_orientation_canonicalized": canonicalized,
                "semantics": "Restart vector canonical parameter component is positive; signed adaptive step selects branch direction"},
            "accounting_invariants": accounting,
            "reached_exact_target": float(point_rows[-1][4]) == float(target)})

    refresh_rows = [row for row in rows if row[0] == "phase_refresh"]
    refresh_events: list[dict[str, Any]] = []
    for index, row in enumerate(refresh_rows):
        if not np.isclose(float(row[6]), float(row[8]), rtol=0.0, atol=1e-12) or \
                not np.isclose(float(row[7]), float(row[9]), rtol=0.0, atol=1e-12):
            raise RuntimeError("phase refresh changed physical coordinates")
        if float(row[15]) > 1e-14 or float(row[16]) > 1e-14 or row[17:19] != ["true", "true"]:
            raise RuntimeError("phase refresh reference identity/full-stack rebuild evidence failed")
        refresh_events.append({"event_type": "native_phase_reference_refresh", "restart_index": index,
            "old_phase_reference_id": row[1], "new_phase_reference_id": row[2], "parent_branch_id": row[3],
            "new_coordinate_name": row[4], "new_coordinate": float(row[5]),
            "old_temperature_K": float(row[6]), "old_log_w": float(row[7]),
            "new_temperature_K": float(row[8]), "new_log_w": float(row[9]),
            "verification": {"backend": "fixed-parameter NOX/KLU2", "accepted": row[14] == "true",
                "stage_residual_max": float(row[10]), "update_residual_max": float(row[11]),
                "phase_residual_abs": float(row[12]), "linear_backend": row[13],
                "physical_temperature_identity_abs": abs(float(row[6]) - float(row[8])),
                "physical_log_w_identity_abs": abs(float(row[7]) - float(row[9])),
                "source_stage_to_reference_max_abs": float(row[15]),
                "source_derivative_to_reference_max_abs": float(row[16])},
            "native_rebuild_reporting": {"assembler_rebuilt": row[17] == "true",
                "model_group_stepper_rebuilt": row[18] == "true"},
            "rebuild_lineage": ["Assembler", "ContinuationModelEvaluator", "WeightedThyraGroup", "LOCA::Stepper"]})
    if [branch["branch_id"] for branch in branches] != list(BRANCH_IDS):
        raise RuntimeError("native output did not contain the exact required branch order")
    if len(refresh_events) != 2:
        raise RuntimeError("native output did not contain both controlled refreshes")
    # Serialize semantic execution order, not the CLI's delayed reporting order:
    # each refreshed reference must be created before any branch consumes it.
    events = [
        *events_by_branch["fixed225-to-spine"], refresh_events[0],
        *events_by_branch["spine-positive-T-hat"],
        *events_by_branch["spine-negative-T-hat-to-210"], refresh_events[1],
        *events_by_branch["slice210-negative-rho"],
        *events_by_branch["slice210-positive-rho"],
    ]

    native_digests = {hashlib.sha256(value.tobytes()).hexdigest() for value in arrays.values()}
    python_digests: set[str] = set()
    for archive_path in (QUALIFICATION_VECTORS, MIDPOINT_BRANCH_VECTORS):
        with np.load(archive_path, allow_pickle=False) as archive:
            python_digests.update(hashlib.sha256(np.asarray(archive[key], dtype="<f8").tobytes()).hexdigest()
                                  for key in archive.files)
    if native_digests & python_digests:
        raise RuntimeError("native vector artifact overlaps a frozen Python array")

    payload: dict[str, Any] = {
        "schema_version": "episode8-native-loca-higher-order-v1",
        "artifact_kind": "independently_executed_native_loca_three_stage_gauss_branches",
        "native_contracts": contracts,
        "branch_execution_contract": {"backend": "LOCA::Stepper", "continuation_method": "Arc Length",
            "predictor": "Secant with signed fixed-parameter bootstrap Restart tangent",
            "step_size": {"method": "Adaptive", "minimum": 1e-8, "maximum": 0.04, "aggressiveness": 0.5},
            "base_system": "square Gauss collocation residual; no duplicate arclength row",
            "parameter_column": "analytic normalized-coordinate chain rule",
            "rejection_retry_owner": "LOCA::Stepper",
            "phase_reference_rebuild_policy": "immutable within segment; two controlled full-stack rebuilds"},
        "required_branch_ids": list(BRANCH_IDS), "branches": branches, "points": points, "events": events,
        "controlled_phase_reference_refresh_count": len(refresh_rows),
        "parity": {"version": "native-python-all-point-parity-v1",
            "reference_backend": "independent Python three-stage fixed-parameter correction at every native coordinate",
            "native_vectors_are_never_Python_seeds": True, "period_relative_tolerance": PERIOD_RTOL,
            "weighted_orbit_tolerance": ORBIT_TOL,
            "maximum_all_point_period_relative_error": maximum_period_error,
            "maximum_all_point_weighted_orbit_error": maximum_orbit_error},
        "scope": "N=32 three-stage fixed-mesh LOCA family plus two-stage native smoke; not adaptive mesh or final Figure 5 accuracy",
        "source_provenance": {key: source_record(path) for key, path in {
            "generator": Path(__file__).resolve(), "cpp_adapter": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
            "cpp_cli": ROOT / "loca/src/midpoint_orbit_cli.cpp", "cpp_assembler": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
            "cpp_model": ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
            "cpp_nox_adapter": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
            "cpp_collocation_coefficients": ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
            "cmake_source_configuration": ROOT / "loca/CMakeLists.txt",
            "python_orbit_solver": ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py",
            "python_continuation_coordinates": ROOT / "src/bergner_spichtinger_2026/periodic_continuation.py",
            "qualification": QUALIFICATION, "qualification_vectors": QUALIFICATION_VECTORS,
            "task065_fixture_manifest": FIXTURES / "manifest.json", "g2_fixture": G2_FIXTURE,
            "g3_fixture": G3_FIXTURE, "bootstrap_seed": BOOTSTRAP_SEED, "hopf_locus": HOPF_LOCI,
            "uv_lock": ROOT / "uv.lock",
        }.items()},
        "runtime_provenance": {"python": sys.version.split()[0], "numpy": np.__version__,
            "emitting_executable_sha256": sha(EXECUTABLE),
            "compiler_and_trilinos": branch_build_identity,
            "cmake_source_sha256": branch_cmake_identity[0],
            "cmake_build_type": branch_cmake_identity[1],
            "emitting_executable_source_fingerprint_sha256": expected_fingerprint(),
            "check_semantics": "--check executes the selected binary and requires byte-identical artifact provenance, including its exact SHA-256; regenerate when build environment changes the executable digest"},
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<exact-current-build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_higher_order_results.py [--check]",
    }
    vector_bytes = npz_bytes(arrays)
    payload["vector_artifact"] = {"path": VECTORS.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(vector_bytes).hexdigest(), "array_count": len(arrays),
        "origin": "vectors emitted by the native C++ LOCA recorder only",
        "digest_disjoint_from_frozen_Python_arrays": True}
    return canonical(payload), vector_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result_bytes, vector_bytes = build()
    if args.check:
        if not RESULTS.is_file() or not VECTORS.is_file() or RESULTS.read_bytes() != result_bytes or VECTORS.read_bytes() != vector_bytes:
            raise SystemExit("native higher-order LOCA artifacts are stale")
        print("verified native higher-order LOCA artifacts")
    else:
        RESULTS.write_bytes(result_bytes)
        VECTORS.write_bytes(vector_bytes)
        print(f"wrote {RESULTS.relative_to(ROOT)} and {VECTORS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
