#!/usr/bin/env python3
"""Run deterministic TASK-067 Python adaptive qualification from N=32 seeds."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from bergner_spichtinger_2026 import (
    ADAPTIVE_CONTROLLER_VERSION,
    ADAPTIVE_METHOD_VERSION,
    DEFECT_ACCEPTANCE_TOLERANCE,
    PERIOD_ORBIT_CONVERGENCE_TOLERANCE,
    CYCLE_BUDGET,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    MidpointResidualTolerances,
    apply_global_beta_r_movement,
    bisect_marked_elements,
    build_composite_r_monitor,
    correct_gauss_orbit,
    decide_adaptation_cycle,
    gauss_legendre_rule,
    mark_h_refinement,
    restart_plan,
    sha256_file,
    transfer_orbit_phase_and_tangent,
)
from bergner_spichtinger_2026.constants import Environment

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
INPUT_JSON = OUTPUT / "higher_order_fixed_mesh_qualification.json"
INPUT_NPZ = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
MIDPOINT_JSON = OUTPUT / "fixed_mesh_midpoint_results.json"
SEED_JSON = OUTPUT / "bootstrap_seed.json"
RESULTS_PATH = OUTPUT / "adaptive_qualification_results.json"
VECTORS_PATH = OUTPUT / "adaptive_qualification_vectors.npz"
SCRIPT_PATH = EPISODE / "scripts/generate_adaptive_qualification_results.py"
ADAPTIVE_ORBITS_PATH = ROOT / "src/bergner_spichtinger_2026/adaptive_orbits.py"
PERIODIC_ORBITS_PATH = ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"

SCHEMA_VERSION = "episode008-adaptive-qualification-v1"
QUALIFICATION_POINTS = (
    "canonical-g3-n32",
    "guard-rho-0-g3-n32",
    "guard-rho-minus-0.15-g3-n32",
    "guard-rho-plus-0.15-g3-n32",
)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_digest(value: np.ndarray) -> str:
    return digest(np.ascontiguousarray(value, dtype="<f8").tobytes())


def npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for key in sorted(arrays):
                member = io.BytesIO()
                np.lib.format.write_array(member, np.asarray(arrays[key]), allow_pickle=False)
                info = zipfile.ZipInfo(key + ".npy", (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, member.getvalue())
        return output.getvalue()


def defect_record(defect: Any) -> dict[str, Any]:
    return {
        "maximum": defect.maximum,
        "argmax_phase": defect.argmax_phase,
        "argmax_bin": defect.argmax_bin,
        "materially_disagreeing_elements": list(defect.materially_disagreeing_elements),
        "combined_element_maxima_sha256": array_digest(defect.combined_element_maxima),
        "grid_disagreement_sha256": array_digest(defect.grid_disagreement),
        "endpoint_left_sha256": array_digest(defect.endpoint_left),
        "endpoint_right_sha256": array_digest(defect.endpoint_right),
        "derivative_jumps_sha256": array_digest(defect.derivative_jumps),
        "probe_admitted_sha256": array_digest(defect.probe_admitted.astype(float)),
    }


def env_for(record: dict[str, Any], parameters: dict[str, Any]) -> Environment:
    return Environment(
        T=float(record.get("temperature_K", parameters["T"])),
        p=float(parameters["p"]),
        w=float(record.get("w_m_s", parameters["w"])),
        F=float(parameters["F"]),
        N_a=float(parameters["N_a"]),
        Δz=float(parameters["Delta_z"]),
        include_evaporation=False,
    )


def physical_mapping_passes(assembler: GaussCollocationAssembler, unknowns: np.ndarray) -> bool:
    variables = assembler.layout.unpack(unknowns)
    with np.errstate(over="ignore", invalid="ignore"):
        positives = np.exp(np.concatenate((variables.endpoints[:, :2].reshape(-1), variables.stages[:, :, :2].reshape(-1))))
        period = np.exp(variables.log_period)
    return bool(np.all(np.isfinite(positives)) and np.all(positives > 0.0) and np.isfinite(period) and period > 0.0)


def run_point(case_id: str, records: dict[str, Any], parameters: dict[str, Any], scaling: np.ndarray, source: Any, arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    rule = gauss_legendre_rule(3)
    record = records[case_id]
    env = env_for(record, parameters)
    mesh = FixedMesh(source[case_id + "__boundaries"])
    reference = FrozenPhaseReference(
        mesh,
        source[case_id + "__phase_values"],
        source[case_id + "__phase_derivatives"],
        scaling,
        np.asarray(rule.nodes),
        np.asarray(rule.quadrature_weights),
    )
    assembler = GaussCollocationAssembler(mesh, env, reference, rule)
    unknowns = np.asarray(source[case_id + "__unknowns"])
    previous: tuple[GaussCollocationAssembler, float, np.ndarray] | None = None
    soft_cap_escalated = False
    consecutive_pure_r = 0
    previous_pure_r_defect: float | None = None
    previous_argmax_bin: int | None = None
    cycles: list[dict[str, Any]] = []
    remesh_events: list[dict[str, Any]] = []
    aliasing_events: list[dict[str, Any]] = []

    for cycle_index in range(CYCLE_BUDGET + 1):
        prefix = f"{case_id}__cycle_{cycle_index}"
        defect = assembler.independent_defect(unknowns)
        period = float(np.exp(unknowns[-1]))
        period_change = None
        orbit_change = None
        if previous is not None:
            period_change = abs(period - previous[1]) / abs(period)
            orbit_change = assembler.compare_with_collocation(unknowns, previous[0], previous[2]).distance
        if previous_argmax_bin is not None:
            distance = abs(defect.argmax_bin - previous_argmax_bin)
            circular = min(distance, 128 - distance)
            if circular <= 1:
                aliasing_events.append({"cycle_index": cycle_index, "previous_bin": previous_argmax_bin, "current_bin": defect.argmax_bin})
        previous_argmax_bin = defect.argmax_bin
        arrays[prefix + "__boundaries"] = mesh.boundaries
        arrays[prefix + "__unknowns"] = unknowns
        arrays[prefix + "__defect_maxima"] = defect.combined_element_maxima
        arrays[prefix + "__grid_disagreement"] = defect.grid_disagreement
        arrays[prefix + "__endpoint_left"] = defect.endpoint_left
        arrays[prefix + "__endpoint_right"] = defect.endpoint_right
        arrays[prefix + "__derivative_jumps"] = defect.derivative_jumps
        arrays[prefix + "__probe_admitted"] = defect.probe_admitted.astype(float)
        decision = decide_adaptation_cycle(
            interval_count=mesh.interval_count,
            cycle_index=cycle_index,
            defect_maximum=defect.maximum,
            period_relative_change=period_change,
            weighted_orbit_change=orbit_change,
            consecutive_pure_r_cycles=consecutive_pure_r,
            pure_r_defect_reduction=None if previous_pure_r_defect is None else (previous_pure_r_defect - defect.maximum) / previous_pure_r_defect,
            maximum_defect_element=int(np.argmax(defect.combined_element_maxima)),
            soft_cap_escalated=soft_cap_escalated,
        )
        soft_cap_escalated = decision.permit_hard_cap
        nonphysical_trigger = not physical_mapping_passes(assembler, unknowns)
        radau_triggers = {
            "defect_below_1e-4_but_convergence_failed": bool(defect.maximum < DEFECT_ACCEPTANCE_TOLERANCE and not (period_change is not None and orbit_change is not None and period_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE and orbit_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE)),
            "period_or_defect_stagnation_before_mesh_cap": False,
            "polynomial_ringing": "not_evaluated",
            "nonphysical_value": bool(nonphysical_trigger),
            "broader_ivp_based": "not_evaluated_through_TASK_068",
            "floquet_dependent": "not_evaluated_through_TASK_068",
        }
        cycles.append({
            "cycle_index": cycle_index,
            "interval_count": mesh.interval_count,
            "period_s": period,
            "period_relative_change": period_change,
            "weighted_orbit_change": orbit_change,
            "defect": defect_record(defect),
            "phase_reference_id": f"{case_id}:cycle-{cycle_index}:remesh-refresh",
            "phase_refresh_triggers": ["initial_reference"] if cycle_index == 0 else ["remesh"],
            "decision": decision.__dict__,
            "nonphysical_interior_check_passed": not nonphysical_trigger,
            "active_radau_triggers": radau_triggers,
            "array_prefix": prefix,
        })
        if decision.terminal_status != "continue":
            return {
                "case_id": case_id,
                "start_interval_count": 32,
                "terminal_status": decision.terminal_status,
                "terminal_action": decision.action,
                "converged": decision.terminal_status == "converged",
                "cycle_count": len(cycles),
                "remesh_correction_count": len(remesh_events),
                "final_interval_count": mesh.interval_count,
                "final_period_s": period,
                "final_defect_maximum": defect.maximum,
                "defect_pass": defect.maximum < DEFECT_ACCEPTANCE_TOLERANCE,
                "period_orbit_convergence_pass": bool(period_change is not None and orbit_change is not None and period_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE and orbit_change < PERIOD_ORBIT_CONVERGENCE_TOLERANCE),
                "defect_aliasing_persistent": bool(aliasing_events),
                "aliasing_events": aliasing_events,
                "cycles": cycles,
                "remesh_events": remesh_events,
            }

        previous = (assembler, period, unknowns)
        if decision.action == "pure_r":
            split_mesh = mesh
            marked_elements: tuple[int, ...] = ()
            previous_pure_r_defect = defect.maximum if previous_pure_r_defect is None else previous_pure_r_defect
            consecutive_pure_r += 1
        else:
            marked_elements = (decision.force_split_element,) if decision.force_split_element is not None else mark_h_refinement(
                defect,
                max_interval_count=512 if decision.permit_hard_cap else 256,
            ).marked_elements
            split_mesh = bisect_marked_elements(mesh, marked_elements)
            previous_pure_r_defect = None
            consecutive_pure_r = 0

        transferred_to_split = assembler.transfer_unknowns(unknowns, split_mesh, rule)
        split_reference = assembler.transferred_phase_reference(unknowns, split_mesh, rule)
        split_assembler = GaussCollocationAssembler(split_mesh, env, split_reference, rule)
        monitor = build_composite_r_monitor(split_assembler, transferred_to_split)
        movement = apply_global_beta_r_movement(split_mesh, monitor.target_boundaries)
        destination_mesh = FixedMesh(movement.new_boundaries)
        transferred, new_reference, _ = transfer_orbit_phase_and_tangent(split_assembler, transferred_to_split, None, destination_mesh, rule)
        destination_assembler = GaussCollocationAssembler(destination_mesh, env, new_reference, rule)
        correction = correct_gauss_orbit(destination_assembler, transferred, tolerances=MidpointResidualTolerances(), max_nfev=300)
        event_prefix = f"{case_id}__remesh_{cycle_index}"
        arrays[event_prefix + "__split_boundaries"] = split_mesh.boundaries
        arrays[event_prefix + "__monitor_values"] = monitor.values
        arrays[event_prefix + "__monitor_targets"] = monitor.target_boundaries
        arrays[event_prefix + "__movement_boundaries"] = movement.new_boundaries
        arrays[event_prefix + "__transferred_unknowns"] = transferred
        arrays[event_prefix + "__corrected_unknowns"] = correction.unknowns
        remesh_events.append({
            "cycle_index": cycle_index,
            "kind": "pure-r" if not marked_elements else "h+r",
            "marked_elements": list(marked_elements),
            "old_interval_count": mesh.interval_count,
            "split_interval_count": split_mesh.interval_count,
            "new_interval_count": destination_mesh.interval_count,
            "monitor_total_mass": monitor.total_mass,
            "movement": {
                "accepted": movement.accepted,
                "stalled": movement.stalled,
                "beta": movement.beta,
                "attempted_betas": list(movement.attempted_betas),
                "rejection_reasons": list(movement.rejection_reasons),
            },
            "restart_plan": [attempt.__dict__ for attempt in restart_plan(remesh_kind="pure-r" if not marked_elements else "h+r").attempts],
            "correction_accepted": correction.accepted,
            "correction_rejection_reasons": list(correction.rejection_reasons),
            "function_evaluations": correction.function_evaluations,
            "phase_refresh": "full_remesh_refresh",
            "array_prefix": event_prefix,
        })
        if not correction.accepted:
            cycles[-1]["decision"] = {**cycles[-1]["decision"], "terminal_status": "resolution_unresolved", "reasons": ["fixed_parameter_correction_failed"]}
            break
        mesh = destination_mesh
        assembler = destination_assembler
        unknowns = correction.unknowns

    return {
        "case_id": case_id,
        "start_interval_count": 32,
        "terminal_status": "resolution_unresolved",
        "terminal_action": "cycle_loop_fell_through",
        "converged": False,
        "cycle_count": len(cycles),
        "remesh_correction_count": len(remesh_events),
        "final_interval_count": mesh.interval_count,
        "final_period_s": float(np.exp(unknowns[-1])),
        "final_defect_maximum": float("nan"),
        "defect_pass": False,
        "period_orbit_convergence_pass": False,
        "defect_aliasing_persistent": bool(aliasing_events),
        "aliasing_events": aliasing_events,
        "cycles": cycles,
        "remesh_events": remesh_events,
    }


def generate(*, check: bool = False) -> None:
    fixed = json.loads(INPUT_JSON.read_text())
    records = {item["case_id"]: item for item in fixed["results"]}
    parameters = json.loads(SEED_JSON.read_text())["canonical_parameters"]
    scaling = np.asarray(json.loads(MIDPOINT_JSON.read_text())["state_scaling"])
    arrays: dict[str, np.ndarray] = {}
    with np.load(INPUT_NPZ, allow_pickle=False) as source:
        results = [run_point(case_id, records, parameters, scaling, source, arrays) for case_id in QUALIFICATION_POINTS]
    vector_bytes = npz_bytes(arrays)
    vector_manifest = {key: {"shape": list(np.asarray(value).shape), "sha256": array_digest(np.asarray(value))} for key, value in arrays.items()}
    data = {
        "schema_version": SCHEMA_VERSION,
        "method_version": ADAPTIVE_METHOD_VERSION,
        "controller_version": ADAPTIVE_CONTROLLER_VERSION,
        "defect_tolerance": DEFECT_ACCEPTANCE_TOLERANCE,
        "period_orbit_convergence_tolerance": PERIOD_ORBIT_CONVERGENCE_TOLERANCE,
        "cycle_budget": CYCLE_BUDGET,
        "qualification_points": list(QUALIFICATION_POINTS),
        "results": results,
        "summary": {
            "point_count": len(results),
            "converged_count": sum(1 for item in results if item["converged"]),
            "all_converged": all(item["converged"] for item in results),
            "resolution_unresolved_count": sum(1 for item in results if item["terminal_status"] == "resolution_unresolved"),
            "max_final_interval_count": max(item["final_interval_count"] for item in results),
            "broader_ivp_based_evidence": "not_evaluated_through_TASK_068",
            "floquet_dependent_evidence": "not_evaluated_through_TASK_068",
        },
        "source_provenance": {
            "generator": {"path": str(SCRIPT_PATH.relative_to(ROOT)), "sha256": sha256_file(SCRIPT_PATH)},
            "adaptive_orbits": {"path": str(ADAPTIVE_ORBITS_PATH.relative_to(ROOT)), "sha256": sha256_file(ADAPTIVE_ORBITS_PATH)},
            "periodic_orbits": {"path": str(PERIODIC_ORBITS_PATH.relative_to(ROOT)), "sha256": sha256_file(PERIODIC_ORBITS_PATH)},
            "fixed_mesh_qualification": {"path": str(INPUT_JSON.relative_to(ROOT)), "sha256": sha256_file(INPUT_JSON)},
            "fixed_mesh_qualification_vectors": {"path": str(INPUT_NPZ.relative_to(ROOT)), "sha256": sha256_file(INPUT_NPZ)},
            "bootstrap_seed": {"path": str(SEED_JSON.relative_to(ROOT)), "sha256": sha256_file(SEED_JSON)},
        },
        "vector_artifact": {"path": str(VECTORS_PATH.relative_to(ROOT)), "sha256": digest(vector_bytes), "arrays": vector_manifest},
    }
    result_bytes = canonical_json(data)
    if check:
        if RESULTS_PATH.read_bytes() != result_bytes:
            raise AssertionError(f"{RESULTS_PATH} is not up to date")
        if VECTORS_PATH.read_bytes() != vector_bytes:
            raise AssertionError(f"{VECTORS_PATH} is not up to date")
        return
    RESULTS_PATH.write_bytes(result_bytes)
    VECTORS_PATH.write_bytes(vector_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(check=args.check)


if __name__ == "__main__":
    main()
