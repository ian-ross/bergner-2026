#!/usr/bin/env python3
"""Generate TASK-077 Floquet diagnostics for accepted native production orbits.

Floquet multipliers are postprocessed from saved native collocation orbit
vectors.  They are not nonlinear unknowns, continuation acceptance gates, or
retroactive TASK-068 evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import FixedMesh, FrozenPhaseReference, GaussCollocationAssembler, OrbitLayout, gauss_legendre_rule  # noqa: E402
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
from bergner_spichtinger_2026.periodic_orbits import STATE_DIMENSION, transformed_vector_field_jacobian  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SUMMARY = OUTPUT / "native_adaptive_floquet_diagnostics.json"
DOC = EPISODE / "docs/task077-floquet-postprocessing.md"
README = EPISODE / "README.md"
GENERATOR = Path(__file__).resolve()
POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
FULL_DOMAIN_SUMMARY = OUTPUT / "native_adaptive_full_domain_run.json"
ORBIT_MANIFEST = OUTPUT / "native_adaptive_full_domain_orbit_manifest.json"
ORBIT_NPZ = OUTPUT / "native_adaptive_full_domain_orbits.npz"
NEAR_HOPF_POLICY = OUTPUT / "native_adaptive_near_hopf_policy_records.json"
MIDPOINT_RESULTS = OUTPUT / "fixed_mesh_midpoint_results.json"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK075_DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
TASK076_DOC = EPISODE / "docs/task076-near-hopf-approach-policy.md"

SCHEMA_VERSION = "episode008-native-adaptive-floquet-diagnostics-v1"
ARTIFACT_KIND = "task077-native-adaptive-floquet-diagnostics"
FLOQUET_METHOD_VERSION = "collocation-polynomial-variational-postprocess-v1"
VARIATIONAL_RHS_VERSION = "transformed-state-autonomous-variational-v1"
DOP853_LADDER: tuple[dict[str, float | str], ...] = (
    {"name": "dop853_coarse", "method": "DOP853", "rtol": 1.0e-7, "atol": 1.0e-9},
    {"name": "dop853_production", "method": "DOP853", "rtol": 1.0e-9, "atol": 1.0e-11},
    {"name": "dop853_refined", "method": "DOP853", "rtol": 3.0e-11, "atol": 3.0e-13},
)
RADAU_TOLERANCE = {"name": "radau_comparison", "method": "Radau", "rtol": 1.0e-9, "atol": 1.0e-11}
TRIVIAL_TOLERANCE = 1.0e-4
NONTRIVIAL_UNIT_TOLERANCE = 1.0e-4
DOP853_REFINEMENT_TOLERANCE = 1.0e-4
RADAU_COMPARISON_TOLERANCE = 5.0e-4
ACCEPTED_TARGET_ID = "spine-210K"


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
        "floquet": FLOQUET_METHOD_VERSION,
        "diagnostics": SCHEMA_VERSION,
        "variational_rhs": VARIATIONAL_RHS_VERSION,
        "full_domain_run": "episode008-native-adaptive-full-domain-run-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "orbit_source": "task075-curated-orbit-npz-manifest",
    }


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")).hexdigest()


def complex_record(value: complex) -> dict[str, float]:
    z = complex(value)
    return {
        "real": float(z.real),
        "imag": float(z.imag),
        "modulus": float(abs(z)),
        "argument_rad": float(math.atan2(z.imag, z.real)),
    }


def max_complex_delta(first: Sequence[complex], second: Sequence[complex]) -> float:
    if len(first) != len(second):
        return float("inf")
    return float(max((abs(complex(a) - complex(b)) for a, b in zip(first, second)), default=0.0))


def multiplier_classification(eigenvalues: Sequence[complex]) -> dict[str, Any]:
    values = [complex(value) for value in eigenvalues]
    trivial_index = min(range(len(values)), key=lambda idx: abs(values[idx] - 1.0 + 0.0j))
    trivial = values[trivial_index]
    nontrivial = [value for idx, value in enumerate(values) if idx != trivial_index]
    nontrivial_moduli = [abs(value) for value in nontrivial]
    max_nontrivial = max(nontrivial_moduli) if nontrivial_moduli else float("nan")
    suspected_unit = [idx for idx, value in enumerate(nontrivial) if abs(abs(value) - 1.0) <= NONTRIVIAL_UNIT_TOLERANCE]
    if suspected_unit:
        stability = "ambiguous_nontrivial_unit_circle"
        stable = False
        ambiguous = True
    elif max_nontrivial < 1.0 - NONTRIVIAL_UNIT_TOLERANCE:
        stability = "orbitally_stable_autonomous_trivial_multiplier"
        stable = True
        ambiguous = False
    elif max_nontrivial > 1.0 + NONTRIVIAL_UNIT_TOLERANCE:
        stability = "unstable_nontrivial_multiplier_outside_unit_circle"
        stable = False
        ambiguous = False
    else:
        stability = "ambiguous_nontrivial_unit_circle"
        stable = False
        ambiguous = True
    return {
        "trivial_multiplier_index": int(trivial_index),
        "trivial_multiplier": complex_record(trivial),
        "trivial_distance_from_one": float(abs(trivial - 1.0)),
        "trivial_gate_tolerance": TRIVIAL_TOLERANCE,
        "trivial_gate_pass": bool(abs(trivial - 1.0) <= TRIVIAL_TOLERANCE),
        "nontrivial_multipliers": [complex_record(value) for value in nontrivial],
        "max_nontrivial_modulus": float(max_nontrivial),
        "nontrivial_unit_circle_tolerance": NONTRIVIAL_UNIT_TOLERANCE,
        "suspected_nontrivial_unit_circle_indices": [int(idx) for idx in suspected_unit],
        "stability_classification": stability,
        "stable": stable,
        "ambiguous": ambiguous,
        "unstable": stability.startswith("unstable"),
    }


def load_accepted_orbit_arrays(point: Mapping[str, Any]) -> dict[str, np.ndarray]:
    keys = list(point["orbit_vector_ref"]["array_keys"])
    with np.load(ROOT / point["orbit_vector_ref"]["npz_path"], allow_pickle=False) as arrays:
        loaded = {key: np.asarray(arrays[key], dtype=float) for key in keys}
    expected_unknown_sha = point["orbit_vector_ref"]["restart_vector_sha256"]
    if array_sha(loaded["spine_210K_unknowns"]) != expected_unknown_sha:
        raise RuntimeError("accepted orbit restart-vector checksum drift")
    return loaded


def build_environment(point: Mapping[str, Any]) -> Environment:
    coords = point["coordinates"]
    return Environment(
        p=30000.0,
        T=float(coords["temperature"]["value"]),
        w=float(coords["w"]["value"]),
        F=1.0,
        N_a=1e10,
        Δz=100.0,
        include_evaporation=False,
    )


def build_assembler(point: Mapping[str, Any], arrays: Mapping[str, np.ndarray]) -> tuple[GaussCollocationAssembler, np.ndarray, float]:
    boundaries = np.asarray(arrays["spine_210K_boundaries"], dtype=float)
    unknowns = np.asarray(arrays["spine_210K_unknowns"], dtype=float)
    phase_values = np.asarray(arrays["spine_210K_phase_values"], dtype=float).reshape(-1, 3, STATE_DIMENSION)
    phase_derivatives = np.asarray(arrays["spine_210K_phase_derivatives"], dtype=float).reshape(-1, 3, STATE_DIMENSION)
    scaling = np.asarray(load_json(MIDPOINT_RESULTS)["state_scaling"], dtype=float)
    mesh = FixedMesh(boundaries)
    rule = gauss_legendre_rule(3)
    reference = FrozenPhaseReference(mesh, phase_values, phase_derivatives, scaling, rule.nodes, rule.quadrature_weights)
    assembler = GaussCollocationAssembler(mesh, build_environment(point), reference, rule)
    period = float(math.exp(OrbitLayout(mesh.interval_count, 3).unpack(unknowns).log_period))
    return assembler, unknowns, period


def variational_integration(
    assembler: GaussCollocationAssembler,
    unknowns: np.ndarray,
    period: float,
    *,
    method: str,
    rtol: float,
    atol: float,
) -> dict[str, Any]:
    evaluate = assembler.polynomial_evaluator(unknowns)

    def rhs(theta: float, flattened: np.ndarray) -> np.ndarray:
        phi = flattened.reshape(STATE_DIMENSION, STATE_DIMENSION)
        jacobian = transformed_vector_field_jacobian(evaluate(theta), assembler.env, assembler.coeff)
        return (period * jacobian @ phi).reshape(STATE_DIMENSION * STATE_DIMENSION)

    solution = solve_ivp(
        rhs,
        (0.0, 1.0),
        np.eye(STATE_DIMENSION, dtype=float).reshape(STATE_DIMENSION * STATE_DIMENSION),
        method=method,
        rtol=rtol,
        atol=atol,
    )
    if solution.y.size:
        monodromy = solution.y[:, -1].reshape(STATE_DIMENSION, STATE_DIMENSION)
        eigenvalues = list(np.linalg.eigvals(monodromy))
    else:
        monodromy = np.full((STATE_DIMENSION, STATE_DIMENSION), np.nan)
        eigenvalues = [complex(float("nan"), 0.0)] * STATE_DIMENSION
    ordered_indices = sorted(range(len(eigenvalues)), key=lambda idx: (abs(eigenvalues[idx] - 1.0), -abs(eigenvalues[idx])))
    ordered = [eigenvalues[idx] for idx in ordered_indices]
    return {
        "solver": {"method": method, "rtol": float(rtol), "atol": float(atol)},
        "success": bool(solution.success),
        "message": str(solution.message),
        "nfev": int(solution.nfev),
        "njev": None if getattr(solution, "njev", None) is None else int(solution.njev),
        "nlu": None if getattr(solution, "nlu", None) is None else int(solution.nlu),
        "monodromy_matrix": [[float(value) for value in row] for row in monodromy],
        "monodromy_determinant": float(np.linalg.det(monodromy)),
        "monodromy_condition_number": float(np.linalg.cond(monodromy)),
        "multipliers_ordering": "first value is closest to autonomous trivial multiplier +1; remaining values sorted by this deterministic rule",
        "multipliers": [complex_record(value) for value in ordered],
        "_eigenvalues": ordered,
    }


def strip_private(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: strip_private(item) for key, item in value.items() if not str(key).startswith("_")}
    if isinstance(value, list):
        return [strip_private(item) for item in value]
    return value


def point_diagnostics(point: Mapping[str, Any]) -> dict[str, Any]:
    arrays = load_accepted_orbit_arrays(point)
    assembler, unknowns, period = build_assembler(point, arrays)
    integrations = []
    for spec in DOP853_LADDER:
        result = variational_integration(
            assembler,
            unknowns,
            period,
            method=str(spec["method"]),
            rtol=float(spec["rtol"]),
            atol=float(spec["atol"]),
        )
        result["name"] = str(spec["name"])
        integrations.append(result)
    production = next(item for item in integrations if item["name"] == "dop853_production")
    refined = next(item for item in integrations if item["name"] == "dop853_refined")
    classification = multiplier_classification(production["_eigenvalues"])
    dop_comparisons = []
    for previous, current in zip(integrations, integrations[1:]):
        delta = max_complex_delta(previous["_eigenvalues"], current["_eigenvalues"])
        dop_comparisons.append(
            {
                "from": previous["name"],
                "to": current["name"],
                "max_abs_multiplier_delta": delta,
                "tolerance": DOP853_REFINEMENT_TOLERANCE,
                "comparison_gate_pass": bool(delta <= DOP853_REFINEMENT_TOLERANCE),
            }
        )
    radau_reasons = ["canonical_accepted_production_point", "autonomous_trivial_multiplier_unit_circle_consistency"]
    if classification["suspected_nontrivial_unit_circle_indices"]:
        radau_reasons.append("suspected_nontrivial_unit_circle_crossing")
    radau = variational_integration(
        assembler,
        unknowns,
        period,
        method=str(RADAU_TOLERANCE["method"]),
        rtol=float(RADAU_TOLERANCE["rtol"]),
        atol=float(RADAU_TOLERANCE["atol"]),
    )
    radau["name"] = str(RADAU_TOLERANCE["name"])
    radau_classification = multiplier_classification(radau["_eigenvalues"])
    radau_delta = max_complex_delta(production["_eigenvalues"], radau["_eigenvalues"])
    return strip_private(
        {
            "target_id": ACCEPTED_TARGET_ID,
            "continuation_point_record_id": point["record_id"],
            "terminal_event_id": f"task075-terminal-{ACCEPTED_TARGET_ID}",
            "validity": point["validity"],
            "coordinates": point["coordinates"],
            "period": point["period"],
            "orbit_source": {
                "npz_path": point["orbit_vector_ref"]["npz_path"],
                "manifest_artifact_id": point["orbit_vector_ref"]["manifest_artifact_id"],
                "restart_vector_sha256": point["orbit_vector_ref"]["restart_vector_sha256"],
                "array_keys": point["orbit_vector_ref"]["array_keys"],
                "interval_count": int(assembler.mesh.interval_count),
                "stage_count": int(assembler.rule.stage_count),
                "unknown_size": int(unknowns.size),
            },
            "postprocessing_boundary": {
                "not_a_nonlinear_unknown": True,
                "not_a_continuation_acceptance_gate": True,
                "not_task068_acceptance_evidence": True,
                "base_orbit_source": "saved native collocation polynomial from TASK-075 accepted production point",
            },
            "variational_problem": {
                "independent_variable": "normalized phase theta in [0, 1]",
                "equation": "dPhi/dtheta = P * Dg(x_collocation(theta)) * Phi, Phi(0)=I",
                "state_convention": ORBIT_STATE_CONVENTION,
                "polynomial_source": "native piecewise three-stage Gauss collocation polynomial",
                "rhs_version": VARIATIONAL_RHS_VERSION,
            },
            "dop853_variational_integrations": integrations,
            "dop853_tolerance_refinement": {
                "comparisons": dop_comparisons,
                "all_comparisons_pass": bool(all(item["comparison_gate_pass"] for item in dop_comparisons)),
            },
            "production_multiplier_classification": classification,
            "radau_comparison": {
                "selection_status": "run",
                "selection_reasons": radau_reasons,
                "stratified_difficult_point": "canonical_headline_regular_accepted_point; near_hopf_or_mesh_stagnation_strata_unavailable_in_current_accepted_set",
                "suspected_unit_circle_crossing": bool(classification["suspected_nontrivial_unit_circle_indices"]),
                "result": radau,
                "classification": radau_classification,
                "max_abs_multiplier_delta_vs_dop853_production": radau_delta,
                "comparison_tolerance": RADAU_COMPARISON_TOLERANCE,
                "comparison_gate_pass": bool(radau_delta <= RADAU_COMPARISON_TOLERANCE),
                "ambiguous_or_unstable_classification_recorded": bool(radau_classification["ambiguous"] or radau_classification["unstable"]),
            },
            "diagnostic_acceptance": {
                "solver_success": bool(all(item["success"] for item in integrations) and radau["success"]),
                "dop853_refinement_gate": bool(all(item["comparison_gate_pass"] for item in dop_comparisons)),
                "trivial_multiplier_gate": bool(classification["trivial_gate_pass"]),
                "radau_comparison_gate": bool(radau_delta <= RADAU_COMPARISON_TOLERANCE),
                "floquet_diagnostics_recorded": True,
            },
        }
    )


def non_orbit_policy(full_domain: Mapping[str, Any], near_hopf_policy: Mapping[str, Any]) -> dict[str, Any]:
    ledger = full_domain["terminal_target_ledger"]
    return {
        "regular_orbit_source": "TASK-075 continuation_points with validity.status == accepted and computed_native_adaptive source",
        "accepted_regular_orbit_count": int(ledger["terminal_status_counts"]["accepted"]),
        "unresolved_targets_not_relabelled": int(ledger["terminal_status_counts"].get("resolution_unresolved", 0)),
        "failed_targets_not_relabelled": int(ledger["terminal_status_counts"].get("failed", 0)),
        "near_hopf_stops_not_relabelled": int(ledger["terminal_status_counts"].get("near_hopf_stop", 0)),
        "tripwire_stops_not_relabelled": int(ledger["terminal_status_counts"].get("tripwire_stop", 0)),
        "hopf_limit_equilibrium_records_not_regular_orbits": True,
        "near_hopf_policy_record_count": len(near_hopf_policy.get("browser_records", [])),
        "interpolation_or_digitized_paper_used_for_floquet": False,
        "nonaccepted_target_ids_sample": [
            target["target_id"] for target in ledger["targets"] if target["terminal_status"] != "accepted"
        ][:12],
    }


def radau_strata_summary(point_records: Sequence[Mapping[str, Any]], diagnostics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    accepted_ids = [point["record_id"] for point in point_records]
    crossing_ids = [
        row["target_id"]
        for row in diagnostics
        if row["production_multiplier_classification"]["suspected_nontrivial_unit_circle_indices"]
    ]
    return {
        "accepted_point_count": len(point_records),
        "radau_run_target_ids": [row["target_id"] for row in diagnostics if row["radau_comparison"]["selection_status"] == "run"],
        "canonical_headline_regular_ids": accepted_ids,
        "stratified_difficult_points": [
            {
                "stratum": "canonical accepted regular production point",
                "target_ids": [row["target_id"] for row in diagnostics],
                "status": "run",
            },
            {
                "stratum": "near-Hopf or long-period accepted approach point",
                "target_ids": [],
                "status": "not_available_no_schema_valid_accepted_near_hopf_points",
            },
            {
                "stratum": "suspected nontrivial unit-circle crossing",
                "target_ids": crossing_ids,
                "status": "run" if crossing_ids else "not_available_no_nontrivial_crossing_candidate_detected",
            },
        ],
        "ambiguous_or_unstable_classifications_recorded_not_suppressed": True,
    }


def build() -> dict[str, Any]:
    points_artifact = load_json(POINTS)
    events_artifact = load_json(EVENTS)
    orbit_manifest = load_json(ORBIT_MANIFEST)
    validate_production_artifact(points_artifact, root=ROOT, artifact_path=POINTS)
    validate_production_artifact(events_artifact, root=ROOT, artifact_path=EVENTS)
    validate_production_artifact(orbit_manifest, root=ROOT, artifact_path=ORBIT_MANIFEST)
    full_domain = load_json(FULL_DOMAIN_SUMMARY)
    near_hopf = load_json(NEAR_HOPF_POLICY)
    point_records = [
        point
        for point in points_artifact["continuation_points"]
        if point["validity"] == {"status": "accepted", "source": "computed_native_adaptive", "authoritative": True}
    ]
    if [point["record_id"] for point in point_records] != ["task075-point-spine-210K"]:
        raise RuntimeError("TASK-077 expected exactly the TASK-075 accepted spine-210K production orbit")
    if orbit_manifest["orbit_vector_manifest"]["accepted_point_ids"] != [ACCEPTED_TARGET_ID]:
        raise RuntimeError("TASK-077 orbit manifest accepted point set changed")
    diagnostics = [point_diagnostics(point) for point in point_records]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_id": "task077-native-adaptive-floquet-diagnostics",
        "scope": "Floquet multiplier postprocessing for saved native adaptive production collocation orbits; diagnostics only, not nonlinear unknowns or acceptance evidence.",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "input_validation": {
            "production_schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "continuation_points_schema_valid": True,
            "continuation_events_schema_valid": True,
            "orbit_manifest_schema_valid": True,
            "accepted_only_processing": True,
            "schema_valid_accepted_point_ids": [point["record_id"] for point in point_records],
        },
        "floquet_policy": {
            "postprocessing_only": True,
            "not_nonlinear_unknowns": True,
            "not_task068_acceptance_evidence": True,
            "not_task075_continuation_acceptance_gate": True,
            "failed_unresolved_and_hopf_limit_records_never_promoted_to_regular_orbits": True,
        },
        "diagnostic_parameters": {
            "dop853_tolerance_ladder": list(DOP853_LADDER),
            "radau_tolerance": dict(RADAU_TOLERANCE),
            "trivial_multiplier_tolerance": TRIVIAL_TOLERANCE,
            "nontrivial_unit_circle_tolerance": NONTRIVIAL_UNIT_TOLERANCE,
            "dop853_refinement_tolerance": DOP853_REFINEMENT_TOLERANCE,
            "radau_comparison_tolerance": RADAU_COMPARISON_TOLERANCE,
        },
        "floquet_diagnostics": diagnostics,
        "radau_comparison_summary": radau_strata_summary(point_records, diagnostics),
        "non_orbit_policy": non_orbit_policy(full_domain, near_hopf),
        "production_record_links": {
            "continuation_points": rel(POINTS),
            "continuation_events": rel(EVENTS),
            "full_domain_summary": rel(FULL_DOMAIN_SUMMARY),
            "curated_orbit_npz_manifest": rel(ORBIT_MANIFEST),
            "curated_orbit_npz": rel(ORBIT_NPZ),
            "near_hopf_policy_records": rel(NEAR_HOPF_POLICY),
        },
        "source_build_identity": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy_integrator": "scipy.integrate.solve_ivp DOP853 and Radau",
            "uv_lock_sha256": sha(ROOT / "uv.lock"),
        },
        "source_provenance": {
            "generator": source_record(GENERATOR, "TASK-077 Floquet diagnostics generator"),
            "task069_doc": source_record(TASK069_DOC, "TASK-069 approved downstream Floquet postprocessing"),
            "task070_doc": source_record(TASK070_DOC, "TASK-070 production schema boundary"),
            "task075_doc": source_record(TASK075_DOC, "TASK-075 accepted production orbit and explicit gaps"),
            "task076_doc": source_record(TASK076_DOC, "TASK-076 Hopf-limit explicit-gap policy"),
            "doc": source_record(DOC, "TASK-077 documentation"),
            "readme": source_record(README, "Episode 008 documentation index"),
            "continuation_points": source_record(POINTS, "TASK-075 schema-valid accepted continuation point records"),
            "continuation_events": source_record(EVENTS, "TASK-075 terminal continuation events"),
            "full_domain_summary": source_record(FULL_DOMAIN_SUMMARY, "TASK-075 terminal target ledger"),
            "curated_orbit_manifest": source_record(ORBIT_MANIFEST, "TASK-075 curated orbit manifest"),
            "curated_orbit_npz": source_record(ORBIT_NPZ, "TASK-075 accepted native orbit vectors"),
            "near_hopf_policy": source_record(NEAR_HOPF_POLICY, "TASK-076 Hopf-limit explicit-gap records"),
            "uv_lock": source_record(ROOT / "uv.lock", "Python environment lockfile"),
        },
        "verification_commands": {
            "artifact_checks": [
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_floquet_diagnostics.py --check",
                "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/validate_production_artifacts.py episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_points.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_events.json episodes/008-figure5-periodic-orbit-continuation/outputs/native_adaptive_full_domain_orbit_manifest.json",
            ],
            "focused_tests": ["uv run pytest tests/test_episode8_native_adaptive_floquet_diagnostics.py -q"],
        },
    }
    SUMMARY.write_bytes(canonical(summary))
    return summary


def check_existing() -> None:
    if not SUMMARY.is_file():
        raise SystemExit(f"missing TASK-077 artifact: {rel(SUMMARY)}")
    summary = load_json(SUMMARY)
    if summary.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("TASK-077 schema version mismatch")
    for artifact_path in (POINTS, EVENTS, ORBIT_MANIFEST):
        validate_production_artifact(load_json(artifact_path), root=ROOT, artifact_path=artifact_path)
    diagnostics = summary.get("floquet_diagnostics", [])
    if len(diagnostics) != 1 or diagnostics[0].get("target_id") != ACCEPTED_TARGET_ID:
        raise SystemExit("TASK-077 accepted diagnostic target set changed")
    record = diagnostics[0]
    if record["production_multiplier_classification"]["trivial_distance_from_one"] > TRIVIAL_TOLERANCE:
        raise SystemExit("TASK-077 trivial multiplier gate failed")
    if not record["dop853_tolerance_refinement"]["all_comparisons_pass"]:
        raise SystemExit("TASK-077 DOP853 tolerance refinement gate failed")
    if record["radau_comparison"]["selection_status"] != "run" or not record["radau_comparison"]["comparison_gate_pass"]:
        raise SystemExit("TASK-077 Radau comparison gate failed")
    if summary["non_orbit_policy"]["unresolved_targets_not_relabelled"] != 297:
        raise SystemExit("TASK-077 unresolved non-orbit policy count changed")
    for key, record in summary["source_provenance"].items():
        path = ROOT / record["path"]
        if not path.is_file() or sha(path) != record["sha256"]:
            raise SystemExit(f"TASK-077 provenance drift for {key}: {record['path']}")
    print("verified TASK-077 Floquet diagnostics")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed TASK-077 artifacts")
    args = parser.parse_args()
    if args.check:
        check_existing()
        return
    build()
    print(f"wrote {rel(SUMMARY)}")


if __name__ == "__main__":
    main()
