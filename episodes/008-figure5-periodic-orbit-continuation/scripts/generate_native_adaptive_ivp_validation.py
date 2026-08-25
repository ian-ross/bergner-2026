#!/usr/bin/env python3
"""Generate TASK-078 stratified independent IVP validation for production points.

The validation set is selected only from schema-valid accepted TASK-075 native
production periodic orbits.  Unresolved, failed, Hopf-limit, interpolated,
qualification-only, and digitized-paper records are recorded as unavailable
strata rather than promoted to production orbits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bergner_spichtinger_2026.core import equilibrium  # noqa: E402
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
from bergner_spichtinger_2026.residuals import log_coordinates_from_physical_state  # noqa: E402
from generate_native_adaptive_floquet_diagnostics import (  # noqa: E402
    MIDPOINT_RESULTS,
    build_assembler,
    load_accepted_orbit_arrays,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_ivp_validation.json"
GENERATOR = Path(__file__).resolve()
POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
FULL_DOMAIN_SUMMARY = OUTPUT / "native_adaptive_full_domain_run.json"
ORBIT_MANIFEST = OUTPUT / "native_adaptive_full_domain_orbit_manifest.json"
ORBIT_NPZ = OUTPUT / "native_adaptive_full_domain_orbits.npz"
FLOQUET = OUTPUT / "native_adaptive_floquet_diagnostics.json"
NEAR_HOPF = OUTPUT / "native_adaptive_near_hopf_review.json"
TASK075_DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
TASK077_DOC = EPISODE / "docs/task077-floquet-postprocessing.md"
DOC = EPISODE / "docs/task078-stratified-ivp-validation.md"
README = EPISODE / "README.md"

SCHEMA_VERSION = "episode008-native-adaptive-ivp-validation-v1"
ARTIFACT_KIND = "task078-stratified-independent-ivp-validation"
STRATIFICATION_VERSION = "task078-production-ivp-stratification-v1"
IVP_METHOD_VERSION = "dop853-radau-phase-aligned-return-v1"
ATTRACTOR_METHOD_VERSION = "perturbed-equilibrium-attractor-screen-v1"
ACCEPTED_TARGET_ID = "spine-210K"
PERIOD_RELATIVE_TOLERANCE = 1.0e-5
SCALED_RETURN_TOLERANCE = 1.0e-5
WEIGHTED_ORBIT_TOLERANCE = 1.0e-5
RADAU_AGREEMENT_TOLERANCE = 2.0e-6
PHASE_SAMPLE_COUNT = 257
DOP853_SPEC = {"method": "DOP853", "rtol": 1.0e-10, "atol": 1.0e-12}
RADAU_SPEC = {"method": "Radau", "rtol": 1.0e-9, "atol": 1.0e-11}

CATEGORY_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"category_id": "qualification_point_lineage", "label": "Qualification points", "required_by_task": True},
    {"category_id": "t210_lower_hopf_side", "label": "T=210 K lower Hopf side where available", "required_by_task": True},
    {"category_id": "t210_upper_hopf_side", "label": "T=210 K upper Hopf side where available", "required_by_task": True},
    {"category_id": "low_temperature_interior", "label": "Low-temperature interior accepted point", "required_by_task": True},
    {"category_id": "high_temperature_interior", "label": "High-temperature interior accepted point", "required_by_task": True},
    {"category_id": "largest_period", "label": "Largest accepted nonlinear period", "required_by_task": True},
    {"category_id": "shortest_period", "label": "Shortest accepted nonlinear period", "required_by_task": True},
    {"category_id": "worst_accepted_defect", "label": "Worst accepted independent defect", "required_by_task": True},
    {"category_id": "worst_floquet_trivial_multiplier", "label": "Worst Floquet trivial multiplier", "required_by_task": True},
    {"category_id": "worst_interpolation_holdout", "label": "Worst interpolation holdout", "required_by_task": True},
    {"category_id": "canonical_spine_anchor", "label": "Canonical rho=0 spine anchor", "required_by_task": True},
    {"category_id": "restart_remesh_boundary", "label": "Native remesh/restart boundary accepted point", "required_by_task": True},
)


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "ivp_validation": SCHEMA_VERSION,
        "stratification": STRATIFICATION_VERSION,
        "ivp_method": IVP_METHOD_VERSION,
        "attractor_screen": ATTRACTOR_METHOD_VERSION,
        "full_domain_run": "episode008-native-adaptive-full-domain-run-v1",
        "floquet": "episode008-native-adaptive-floquet-diagnostics-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def accepted_points(points_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(point)
        for point in points_artifact["continuation_points"]
        if point["validity"] == {"status": "accepted", "source": "computed_native_adaptive", "authoritative": True}
    ]


def target_id_from_point(point: Mapping[str, Any]) -> str:
    return str(point["record_id"]).removeprefix("task075-point-")


def defect_value(point: Mapping[str, Any]) -> float:
    gates = point.get("validation_refs", {})
    value = gates.get("independent_defect_maximum")
    if value is not None:
        return float(value)
    return 0.0


def floquet_trivial_distance_by_target(floquet: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in floquet.get("floquet_diagnostics", []):
        result[str(row["target_id"])] = float(
            row["production_multiplier_classification"]["trivial_distance_from_one"]
        )
    return result


def category_selection(
    points: Sequence[Mapping[str, Any]],
    full_domain: Mapping[str, Any],
    floquet: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_target = {target_id_from_point(point): point for point in points}
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    trivial_distance = floquet_trivial_distance_by_target(floquet)

    def add(category: Mapping[str, Any], target_id: str | None, status: str, reason: str) -> None:
        point_record_id = f"task075-point-{target_id}" if target_id else None
        selected.append(
            {
                "category_id": category["category_id"],
                "label": category["label"],
                "status": status,
                "selected_target_id": target_id,
                "selected_point_record_id": point_record_id,
                "deduplicated_into_validation_set": bool(target_id and target_id not in selected_ids),
                "reason": reason,
            }
        )
        if target_id:
            selected_ids.add(target_id)

    category_map = {item["category_id"]: item for item in CATEGORY_DEFINITIONS}
    if ACCEPTED_TARGET_ID in by_target:
        add(category_map["qualification_point_lineage"], ACCEPTED_TARGET_ID, "available", "accepted spine-210K orbit inherits the adaptive-guard-rho-0 qualification/restart lineage")
        add(category_map["canonical_spine_anchor"], ACCEPTED_TARGET_ID, "available", "only accepted rho=0 canonical spine production orbit")
        add(category_map["restart_remesh_boundary"], ACCEPTED_TARGET_ID, "available", "TASK-081 exact post-remesh restart vector accepted by TASK-075")
    else:
        for category_id in ("qualification_point_lineage", "canonical_spine_anchor", "restart_remesh_boundary"):
            add(category_map[category_id], None, "unavailable", "no accepted native production point exists for this stratum")

    for category_id, reason in (
        ("t210_lower_hopf_side", "T=210 K negative-rho Hopf-side production targets are explicit TASK-075 gaps"),
        ("t210_upper_hopf_side", "T=210 K positive-rho Hopf-side production targets are explicit TASK-075 gaps"),
        ("low_temperature_interior", "low-temperature interior production targets are explicit TASK-075 gaps"),
        ("high_temperature_interior", "high-temperature interior production targets are explicit TASK-075 gaps"),
        ("worst_interpolation_holdout", "TASK-075 holdout errors are not_evaluated because fewer than three accepted points exist"),
    ):
        add(category_map[category_id], None, "unavailable_explicit_gap", reason)

    if points:
        largest = max(points, key=lambda point: float(point["period"]["value"]))
        shortest = min(points, key=lambda point: float(point["period"]["value"]))
        worst_defect = max(points, key=defect_value)
        worst_floquet = max(points, key=lambda point: trivial_distance.get(target_id_from_point(point), -1.0))
        add(category_map["largest_period"], target_id_from_point(largest), "available", "maximum period among accepted production points after explicit gaps are excluded")
        add(category_map["shortest_period"], target_id_from_point(shortest), "available", "minimum period among accepted production points after explicit gaps are excluded")
        add(category_map["worst_accepted_defect"], target_id_from_point(worst_defect), "available", "largest independent defect among accepted production points")
        add(category_map["worst_floquet_trivial_multiplier"], target_id_from_point(worst_floquet), "available", "largest distance of the autonomous trivial Floquet multiplier from +1 among accepted production points")
    else:
        for category_id in ("largest_period", "shortest_period", "worst_accepted_defect", "worst_floquet_trivial_multiplier"):
            add(category_map[category_id], None, "unavailable", "no accepted native production point exists")

    terminal_counts = full_domain["terminal_target_ledger"]["terminal_status_counts"]
    if terminal_counts.get("accepted") != len(points):
        raise RuntimeError("accepted production point count disagrees with TASK-075 ledger")
    return selected, sorted(selected_ids)


def scaled_norms(delta: np.ndarray, scaling: np.ndarray) -> tuple[float, float]:
    scaled = np.asarray(delta, dtype=float) * scaling
    return float(np.linalg.norm(scaled)), float(np.max(np.abs(scaled)))


def run_ivp(point: Mapping[str, Any], *, method: str, rtol: float, atol: float, t_final: float | None = None) -> dict[str, Any]:
    arrays = load_accepted_orbit_arrays(point)
    assembler, unknowns, period = build_assembler(point, arrays)
    variables = assembler.layout.unpack(unknowns)
    initial = np.asarray(variables.endpoints[0], dtype=float)
    scaling = np.asarray(load_json(MIDPOINT_RESULTS)["state_scaling"], dtype=float)
    evaluate = assembler.polynomial_evaluator(unknowns)
    final_time = float(t_final if t_final is not None else period)
    started = time.perf_counter()
    solution = solve_ivp(
        lambda _t, y: transformed_vector_field(y, assembler.env, None),
        (0.0, final_time),
        initial,
        method=method,
        rtol=rtol,
        atol=atol,
        dense_output=True,
    )
    wall = time.perf_counter() - started
    if solution.y.size:
        final_state = solution.sol(period) if solution.sol is not None and final_time >= period else solution.y[:, -1]
        return_norm, return_max = scaled_norms(final_state - initial, scaling)
    else:
        return_norm = return_max = float("inf")

    period_relative_error = float("inf")
    closest_return_norm = float("inf")
    closest_return_time = None
    if solution.success and solution.sol is not None and final_time >= 1.05 * period:
        def distance(t: float) -> float:
            value = (solution.sol(float(t)) - initial) * scaling
            return float(np.linalg.norm(value))

        optimum = minimize_scalar(distance, bounds=(0.95 * period, 1.05 * period), method="bounded", options={"xatol": 1.0e-8})
        closest_return_time = float(optimum.x)
        closest_return_norm = float(optimum.fun)
        period_relative_error = abs(closest_return_time - period) / period
    elif solution.success:
        closest_return_time = period
        closest_return_norm = return_norm
        period_relative_error = 0.0

    phases = np.linspace(0.0, 1.0, PHASE_SAMPLE_COUNT)
    if solution.success and solution.sol is not None:
        ivp_states = solution.sol(phases * period).T
        collocation_states = np.array([evaluate(float(theta)) for theta in phases])
        scaled = (ivp_states - collocation_states) * scaling
        weighted_rms = float(np.sqrt(np.mean(scaled**2)))
        weighted_max = float(np.max(np.abs(scaled)))
    else:
        weighted_rms = weighted_max = float("inf")

    result = {
        "solver": {"method": method, "rtol": float(rtol), "atol": float(atol)},
        "success": bool(solution.success),
        "message": str(solution.message),
        "nfev": int(solution.nfev),
        "njev": None if getattr(solution, "njev", None) is None else int(solution.njev),
        "nlu": None if getattr(solution, "nlu", None) is None else int(solution.nlu),
        "wall_clock_s": wall,
        "native_period_s": period,
        "closest_return_period_s": closest_return_time,
        "closest_return_scaled_norm": closest_return_norm,
        "period_relative_error": period_relative_error,
        "scaled_return_norm_at_native_period": return_norm,
        "scaled_return_max_at_native_period": return_max,
        "phase_aligned_weighted_orbit_rms": weighted_rms,
        "phase_aligned_weighted_orbit_max": weighted_max,
        "phase_sample_count": PHASE_SAMPLE_COUNT,
    }
    if method == "DOP853":
        gates = {
            "solver_success": bool(solution.success),
            "period_relative_error": bool(period_relative_error <= PERIOD_RELATIVE_TOLERANCE),
            "scaled_return_norm": bool(return_norm <= SCALED_RETURN_TOLERANCE),
            "scaled_return_max": bool(return_max <= SCALED_RETURN_TOLERANCE),
            "phase_aligned_weighted_orbit_rms": bool(weighted_rms <= WEIGHTED_ORBIT_TOLERANCE),
            "phase_aligned_weighted_orbit_max": bool(weighted_max <= WEIGHTED_ORBIT_TOLERANCE),
        }
        failures = [key for key, passed in gates.items() if not passed]
        result.update({"gates": gates, "failure_reasons": failures, "validation_status": "passed" if not failures else "failed"})
    return result


def dop853_validation(point: Mapping[str, Any]) -> dict[str, Any]:
    result = run_ivp(point, method="DOP853", rtol=float(DOP853_SPEC["rtol"]), atol=float(DOP853_SPEC["atol"]), t_final=1.05 * float(point["period"]["value"]))
    return {
        "target_id": target_id_from_point(point),
        "continuation_point_record_id": point["record_id"],
        "period": point["period"],
        "coordinates": point["coordinates"],
        "selection_status": "selected_after_category_deduplication",
        "native_period_is_read_only_validation_target": True,
        "dop853_one_period_return_and_trajectory": result,
    }


def radau_agreement(point: Mapping[str, Any], dop853: Mapping[str, Any]) -> dict[str, Any]:
    radau = run_ivp(point, method="Radau", rtol=float(RADAU_SPEC["rtol"]), atol=float(RADAU_SPEC["atol"]), t_final=float(point["period"]["value"]))
    d = dop853["dop853_one_period_return_and_trajectory"]
    deltas = {
        "scaled_return_norm_delta": abs(float(radau["scaled_return_norm_at_native_period"]) - float(d["scaled_return_norm_at_native_period"])),
        "scaled_return_max_delta": abs(float(radau["scaled_return_max_at_native_period"]) - float(d["scaled_return_max_at_native_period"])),
        "weighted_orbit_rms_delta": abs(float(radau["phase_aligned_weighted_orbit_rms"]) - float(d["phase_aligned_weighted_orbit_rms"])),
    }
    gate = bool(radau["success"] and max(deltas.values()) <= RADAU_AGREEMENT_TOLERANCE)
    return {
        "target_id": target_id_from_point(point),
        "selection_status": "run",
        "selection_reasons": ["canonical_headline", "available_accepted_production_point"],
        "radau_result": radau,
        "agreement_vs_dop853": deltas,
        "agreement_tolerance": RADAU_AGREEMENT_TOLERANCE,
        "agreement_gate_pass": gate,
        "failure_reasons": [] if gate else ["radau_dop853_agreement"],
    }


def attractor_checks(point: Mapping[str, Any]) -> list[dict[str, Any]]:
    arrays = load_accepted_orbit_arrays(point)
    assembler, unknowns, period = build_assembler(point, arrays)
    scaling = np.asarray(load_json(MIDPOINT_RESULTS)["state_scaling"], dtype=float)
    evaluate = assembler.polynomial_evaluator(unknowns)
    phases = np.linspace(0.0, 1.0, 513)
    collocation = np.array([evaluate(float(theta)) for theta in phases])
    try:
        eq = log_coordinates_from_physical_state(equilibrium(assembler.env, bracket=(1.000001, 3.0)))
        equilibrium_status = "computed"
    except Exception as exc:  # pragma: no cover - defensive provenance path
        eq = np.asarray(assembler.layout.unpack(unknowns).endpoints[0], dtype=float)
        equilibrium_status = f"equilibrium_failed:{type(exc).__name__}:{exc}"
    perturbations = (
        ("scaled-plus-logn", np.array([1.0, 0.0, 0.0]), 1.0e-8),
        ("scaled-minus-logn", np.array([-1.0, 0.0, 0.0]), 1.0e-8),
        ("scaled-plus-s", np.array([0.0, 0.0, 1.0]), 1.0e-8),
        ("scaled-mixed-logn-s", np.array([1.0, 0.0, 1.0]) / math.sqrt(2.0), 1.0e-8),
    )
    rows = []
    for name, direction, amplitude in perturbations:
        initial = eq + amplitude * direction / scaling
        started = time.perf_counter()
        try:
            solution = solve_ivp(
                lambda _t, y: transformed_vector_field(y, assembler.env, None),
                (0.0, 20.0 * period),
                initial,
                method="DOP853",
                rtol=1.0e-7,
                atol=1.0e-9,
            )
            wall = time.perf_counter() - started
            if solution.y.size:
                final = solution.y[:, -1]
                distances = np.linalg.norm((collocation - final) * scaling, axis=1)
                closest_distance = float(np.min(distances))
                closest_phase = float(phases[int(np.argmin(distances))])
            else:
                closest_distance = float("inf")
                closest_phase = None
            converged = bool(solution.success and closest_distance <= 5.0e-2)
            rows.append(
                {
                    "target_id": target_id_from_point(point),
                    "trial_id": name,
                    "equilibrium_status": equilibrium_status,
                    "perturbation_amplitude_scaled": amplitude,
                    "solver_success": bool(solution.success),
                    "message": str(solution.message),
                    "nfev": int(solution.nfev),
                    "wall_clock_s": wall,
                    "integration_horizon_periods": 20.0,
                    "closest_orbit_scaled_distance": closest_distance,
                    "closest_orbit_phase": closest_phase,
                    "attractor_gate_tolerance": 5.0e-2,
                    "attractor_gate_pass": converged,
                    "failure_reasons": [] if converged else ["closest_orbit_scaled_distance_or_solver_success"],
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "target_id": target_id_from_point(point),
                    "trial_id": name,
                    "equilibrium_status": equilibrium_status,
                    "perturbation_amplitude_scaled": amplitude,
                    "solver_success": False,
                    "message": f"{type(exc).__name__}: {exc}",
                    "nfev": None,
                    "wall_clock_s": time.perf_counter() - started,
                    "integration_horizon_periods": 20.0,
                    "closest_orbit_scaled_distance": None,
                    "closest_orbit_phase": None,
                    "attractor_gate_tolerance": 5.0e-2,
                    "attractor_gate_pass": False,
                    "failure_reasons": ["ivp_exception_from_perturbed_equilibrium"],
                }
            )
    return rows


def build() -> dict[str, Any]:
    points_artifact = load_json(POINTS)
    events_artifact = load_json(EVENTS)
    orbit_manifest = load_json(ORBIT_MANIFEST)
    validate_production_artifact(points_artifact, root=ROOT, artifact_path=POINTS)
    validate_production_artifact(events_artifact, root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(orbit_manifest, root=ROOT, artifact_path=ORBIT_MANIFEST)
    full_domain = load_json(FULL_DOMAIN_SUMMARY)
    floquet = load_json(FLOQUET)
    points = accepted_points(points_artifact)
    category_rows, selected_target_ids = category_selection(points, full_domain, floquet)
    point_by_target = {target_id_from_point(point): point for point in points}
    selected_points = [point_by_target[target_id] for target_id in selected_target_ids]
    validations = [dop853_validation(point) for point in selected_points]
    headline_points = selected_points[:6]
    radau = [radau_agreement(point, validation) for point, validation in zip(headline_points, validations[: len(headline_points)])]
    attractor = []
    for point in headline_points[:4]:
        attractor.extend(attractor_checks(point))
    accepted_count = int(full_domain["terminal_target_ledger"]["terminal_status_counts"]["accepted"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task078-stratified-independent-ivp-validation",
        "scope": "Independent IVP evidence for deduplicated schema-valid accepted native production periodic orbits only.",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "input_validation": {
            "production_schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "continuation_points_schema_valid": True,
            "continuation_events_schema_valid": True,
            "orbit_manifest_schema_valid": True,
            "accepted_only_processing": True,
            "accepted_production_target_count": accepted_count,
            "schema_valid_accepted_target_ids": [target_id_from_point(point) for point in points],
        },
        "stratification_policy": {
            "version": STRATIFICATION_VERSION,
            "documented_category_count": len(CATEGORY_DEFINITIONS),
            "documented_categories": [dict(item) for item in CATEGORY_DEFINITIONS],
            "category_selection": category_rows,
            "available_category_count": sum(row["status"] == "available" for row in category_rows),
            "unavailable_category_count": sum(row["status"] != "available" for row in category_rows),
            "deduplicated_selected_target_ids": selected_target_ids,
            "deduplicated_selected_point_count": len(selected_target_ids),
            "deduplication_rule": "one IVP validation per unique accepted native production target after category selection",
            "unavailable_strata_remain_explicit_gaps": True,
        },
        "validation_tolerances": {
            "period_relative": PERIOD_RELATIVE_TOLERANCE,
            "scaled_return_norm_or_max": SCALED_RETURN_TOLERANCE,
            "phase_aligned_weighted_orbit": WEIGHTED_ORBIT_TOLERANCE,
            "radau_agreement": RADAU_AGREEMENT_TOLERANCE,
        },
        "dop853_validations": validations,
        "dop853_validation_summary": {
            "selected_point_count": len(validations),
            "passed_count": sum(row["dop853_one_period_return_and_trajectory"]["validation_status"] == "passed" for row in validations),
            "failed_count": sum(row["dop853_one_period_return_and_trajectory"]["validation_status"] != "passed" for row in validations),
            "all_selected_points_have_explicit_pass_or_failure_reasons": all(
                row["dop853_one_period_return_and_trajectory"]["validation_status"] == "passed"
                or row["dop853_one_period_return_and_trajectory"]["failure_reasons"]
                for row in validations
            ),
        },
        "headline_selection": {
            "requested_hardest_or_headline_count": 6,
            "available_hardest_or_headline_target_ids": [target_id_from_point(point) for point in headline_points],
            "selection_rule": "accepted deduplicated production points ordered by current category coverage; unavailable headline strata recorded rather than invented",
            "production_evidence_insufficient_for_six_unique_points": len(headline_points) < 6,
        },
        "radau_agreement_checks": radau,
        "radau_agreement_summary": {
            "requested_headline_count": 6,
            "run_count": len(radau),
            "passed_count": sum(row["agreement_gate_pass"] for row in radau),
            "production_evidence_insufficient_for_six_unique_points": len(radau) < 6,
        },
        "perturbed_equilibrium_attractor_checks": attractor,
        "perturbed_equilibrium_attractor_summary": {
            "documented_minimum_unique_points": 4,
            "available_unique_headline_points": len(headline_points),
            "trial_count": len(attractor),
            "unique_target_ids_receiving_trials": sorted({row["target_id"] for row in attractor}),
            "production_evidence_insufficient_for_four_unique_points": len(headline_points) < 4,
            "passed_trial_count": sum(row["attractor_gate_pass"] for row in attractor),
            "failed_trial_count": sum(not row["attractor_gate_pass"] for row in attractor),
            "failures_are_recorded_not_suppressed": all(row["attractor_gate_pass"] or row["failure_reasons"] for row in attractor),
        },
        "independence_policy": {
            "native_continuation_periods_overwritten": False,
            "native_continuation_periods_tuned_by_ivp": False,
            "native_orbit_vectors_recorrected_by_ivp": False,
            "validation_can_only_record_pass_fail_or_unavailable": True,
            "unresolved_failed_hopf_interpolated_digitized_or_qualification_only_records_promoted": False,
            "native_period_is_read_only_validation_target": True,
        },
        "production_record_links": {
            "continuation_points": rel(POINTS),
            "continuation_events": rel(EVENTS),
            "full_domain_summary": rel(FULL_DOMAIN_SUMMARY),
            "curated_orbit_npz_manifest": rel(ORBIT_MANIFEST),
            "curated_orbit_npz": rel(ORBIT_NPZ),
            "floquet_diagnostics": rel(FLOQUET),
            "near_hopf_review": rel(NEAR_HOPF),
        },
        "source_build_identity": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy_integrator": "scipy.integrate.solve_ivp DOP853 and Radau",
            "uv_lock_sha256": sha(ROOT / "uv.lock"),
        },
        "source_provenance": {
            "generator": source_record(GENERATOR, "TASK-078 IVP validation generator"),
            "task075_doc": source_record(TASK075_DOC, "TASK-075 accepted production point and explicit gaps"),
            "task077_doc": source_record(TASK077_DOC, "TASK-077 Floquet worst-trivial-multiplier input"),
            "doc": source_record(DOC, "TASK-078 documentation"),
            "readme": source_record(README, "Episode 008 documentation index"),
            "continuation_points": source_record(POINTS, "TASK-075 accepted production point records"),
            "continuation_events": source_record(EVENTS, "TASK-075 terminal event records"),
            "full_domain_summary": source_record(FULL_DOMAIN_SUMMARY, "TASK-075 target ledger and holdout status"),
            "curated_orbit_manifest": source_record(ORBIT_MANIFEST, "TASK-075 curated orbit manifest"),
            "curated_orbit_npz": source_record(ORBIT_NPZ, "TASK-075 accepted native orbit vectors"),
            "floquet_diagnostics": source_record(FLOQUET, "TASK-077 Floquet diagnostics"),
            "near_hopf_review": source_record(NEAR_HOPF, "TASK-076 near-Hopf availability review"),
            "midpoint_results": source_record(MIDPOINT_RESULTS, "state scaling for weighted IVP distances"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_ivp_validation.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json",
            ],
            "focused_tests": ["uv run pytest tests/test_episode8_native_adaptive_ivp_validation.py -q"],
        },
    }
    SUMMARY.write_bytes(canonical(summary))
    return summary


def check_existing() -> None:
    if not SUMMARY.is_file():
        raise SystemExit(f"missing TASK-078 artifact: {rel(SUMMARY)}")
    summary = load_json(SUMMARY)
    if summary.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("TASK-078 schema version mismatch")
    for artifact_path in (POINTS, EVENTS, ORBIT_MANIFEST):
        validate_production_artifact(load_json(artifact_path), root=ROOT, artifact_path=artifact_path)
    policy = summary["stratification_policy"]
    if policy["documented_category_count"] != 12:
        raise SystemExit("TASK-078 category count changed")
    if policy["deduplicated_selected_target_ids"] != [ACCEPTED_TARGET_ID]:
        raise SystemExit("TASK-078 accepted selected point set changed")
    dop = summary["dop853_validation_summary"]
    if dop["selected_point_count"] != 1 or dop["passed_count"] != 1 or dop["failed_count"] != 0:
        raise SystemExit("TASK-078 DOP853 validation gate failed")
    if summary["radau_agreement_summary"]["passed_count"] != 1:
        raise SystemExit("TASK-078 Radau agreement gate failed")
    if not summary["perturbed_equilibrium_attractor_summary"]["production_evidence_insufficient_for_four_unique_points"]:
        raise SystemExit("TASK-078 attractor availability policy changed")
    if summary["independence_policy"]["native_continuation_periods_overwritten"]:
        raise SystemExit("TASK-078 independence policy violated")
    for key, record in summary["source_provenance"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-078 provenance drift for {key}: {record['path']}")
    print("verified TASK-078 stratified IVP validation")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed TASK-078 artifact")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    build()
    print(f"wrote {rel(SUMMARY)}")


if __name__ == "__main__":
    main()
