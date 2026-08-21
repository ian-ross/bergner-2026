#!/usr/bin/env python3
"""Generate deterministic TASK-067 adaptive collocation fixtures."""
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
    ADAPTIVE_METHOD_VERSION,
    H_MARKING_VERSION,
    MONITOR_VERSION,
    RESTART_RETRY_VERSION,
    R_MOVEMENT_VERSION,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    PeriodicHermiteSeed,
    apply_global_beta_r_movement,
    bisect_marked_elements,
    build_composite_r_monitor,
    execute_fixed_parameter_restart,
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
SEED_PATH = OUTPUT / "bootstrap_seed.json"
FIXED_QUALIFICATION_JSON = OUTPUT / "higher_order_fixed_mesh_qualification.json"
FIXED_QUALIFICATION_NPZ = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
MIDPOINT_JSON = OUTPUT / "fixed_mesh_midpoint_results.json"
RESULTS_PATH = OUTPUT / "adaptive_collocation_fixtures.json"
VECTORS_PATH = OUTPUT / "adaptive_collocation_fixtures_vectors.npz"
SCRIPT_PATH = EPISODE / "scripts/generate_adaptive_collocation_fixtures.py"
PERIODIC_ORBITS_PATH = ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"
ADAPTIVE_ORBITS_PATH = ROOT / "src/bergner_spichtinger_2026/adaptive_orbits.py"

SCHEMA_VERSION = "episode008-adaptive-collocation-fixtures-v1"


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


def build_case() -> tuple[GaussCollocationAssembler, np.ndarray]:
    seed_json = json.loads(SEED_PATH.read_text())
    parameters = seed_json["canonical_parameters"]
    env = Environment(
        T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
        N_a=parameters["N_a"], Δz=parameters["Delta_z"], include_evaporation=False,
    )
    seed = PeriodicHermiteSeed.from_json(SEED_PATH)
    mesh = FixedMesh(np.array([0.0, 0.08, 0.22, 0.48, 0.74, 1.0]))
    rule = gauss_legendre_rule(3)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    reference = FrozenPhaseReference.from_evaluator(mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling)
    assembler = GaussCollocationAssembler(mesh, env, reference, rule)
    unknowns = assembler.reference_unknowns(seed.evaluate, seed.log_period)
    return assembler, unknowns


def grid_record(grid: Any) -> dict[str, Any]:
    return {
        "name": grid.name,
        "nodes": grid.local_nodes.tolist(),
        "relative_defects_sha256": array_digest(grid.relative_defects),
        "maximum": grid.maximum,
        "argmax_interval": grid.argmax_interval,
        "argmax_local_node": grid.argmax_local_node,
        "argmax_phase": grid.argmax_phase,
    }


def build_accepted_restart_case() -> tuple[GaussCollocationAssembler, np.ndarray]:
    records = {item["case_id"]: item for item in json.loads(FIXED_QUALIFICATION_JSON.read_text())["results"]}
    parameters = json.loads(SEED_PATH.read_text())["canonical_parameters"]
    scaling = np.asarray(json.loads(MIDPOINT_JSON.read_text())["state_scaling"])
    case_id = "canonical-g3-n32"
    record = records[case_id]
    env = Environment(
        T=float(record.get("temperature_K", parameters["T"])),
        p=float(parameters["p"]),
        w=float(record.get("w_m_s", parameters["w"])),
        F=float(parameters["F"]),
        N_a=float(parameters["N_a"]),
        Δz=float(parameters["Delta_z"]),
        include_evaporation=False,
    )
    rule = gauss_legendre_rule(3)
    with np.load(FIXED_QUALIFICATION_NPZ, allow_pickle=False) as source:
        mesh = FixedMesh(source[case_id + "__boundaries"])
        reference = FrozenPhaseReference(
            mesh,
            source[case_id + "__phase_values"],
            source[case_id + "__phase_derivatives"],
            scaling,
            np.asarray(rule.nodes),
            np.asarray(rule.quadrature_weights),
        )
        unknowns = np.asarray(source[case_id + "__unknowns"])
    return GaussCollocationAssembler(mesh, env, reference, rule), unknowns


def density_record(density: Any) -> dict[str, Any]:
    return {
        "name": density.name,
        "maximum": density.maximum,
        "weighted_average_after_max_rescale": density.weighted_average_after_max_rescale,
        "weighted_average_after_winsorization": density.weighted_average_after_winsorization,
        "raw_sha256": array_digest(density.raw),
        "normalized_sha256": array_digest(density.normalized),
    }


def generate(*, check: bool = False) -> None:
    assembler, unknowns = build_case()
    defect = assembler.independent_defect(unknowns)
    monitor = build_composite_r_monitor(assembler, unknowns)
    synthetic_next = np.array([2.0e-4, 2.0e-5, 8.0e-5, 6.0e-5, 1.0e-5])
    synthetic_dyadic = np.array([2.0e-5, 2.2e-5, 7.0e-5, 2.0e-5, 1.0e-5])
    synthetic_probe = np.array([3.0e-4, 9.0e-1, 1.0e-4, 8.0e-5, 1.0e-5])
    synthetic_larger = np.maximum(synthetic_next, synthetic_dyadic)
    synthetic_disagreement = np.divide(
        np.abs(synthetic_next - synthetic_dyadic),
        synthetic_larger,
        out=np.zeros_like(synthetic_larger),
        where=synthetic_larger > 0.0,
    )
    synthetic_material = (synthetic_larger > 1.0e-5) & (synthetic_disagreement > 0.5)
    synthetic_probe_admitted = synthetic_material.astype(float)
    synthetic_combined = synthetic_larger.copy()
    synthetic_combined[synthetic_material] = np.maximum(
        synthetic_combined[synthetic_material], synthetic_probe[synthetic_material]
    )
    synthetic_defects = np.array([2.5e-4, 1.0e-5, 6.0e-4, 3.0e-4, 4.0e-5])
    marking = mark_h_refinement(synthetic_defects, max_interval_count=7)
    split_mesh = bisect_marked_elements(assembler.mesh, marking.marked_elements)
    movement = apply_global_beta_r_movement(assembler.mesh, monitor.target_boundaries)
    destination_mesh = FixedMesh.uniform(7)
    rule = gauss_legendre_rule(3)
    tangent = np.sin(np.arange(unknowns.size) + 0.25)
    transferred, transferred_reference, transferred_tangent = transfer_orbit_phase_and_tangent(
        assembler, unknowns, tangent, destination_mesh, rule
    )
    restart_assembler, restart_unknowns = build_accepted_restart_case()
    previous_for_rebootstrap = restart_unknowns.copy()
    previous_for_rebootstrap[0] += 1.0e-3
    restart_execution = execute_fixed_parameter_restart(
        restart_assembler,
        restart_unknowns,
        remesh_kind="h+r",
        tangent=np.zeros_like(transferred),
        previous_unknowns=previous_for_rebootstrap,
        require_tangent=True,
        max_nfev=50,
    )
    arrays = {
        "input_mesh_boundaries": assembler.mesh.boundaries,
        "input_unknowns": unknowns,
        "defect_next_gauss_relative": defect.next_gauss.relative_defects,
        "defect_staggered_dyadic_relative": defect.staggered_dyadic.relative_defects,
        "defect_probe_16_relative": np.empty((0, 0)) if defect.probe_16 is None else defect.probe_16.relative_defects,
        "defect_combined_element_maxima": defect.combined_element_maxima,
        "defect_grid_disagreement": defect.grid_disagreement,
        "synthetic_probe_next": synthetic_next,
        "synthetic_probe_dyadic": synthetic_dyadic,
        "synthetic_probe_probe16": synthetic_probe,
        "synthetic_probe_disagreement": synthetic_disagreement,
        "synthetic_probe_admitted": synthetic_probe_admitted,
        "synthetic_probe_combined": synthetic_combined,
        "monitor_subcell_midpoints": monitor.subcell_midpoint_phases,
        "monitor_subcell_widths": monitor.subcell_widths,
        "monitor_values": monitor.values,
        "monitor_cumulative_upper": monitor.cumulative_upper,
        "monitor_target_boundaries": monitor.target_boundaries,
        "synthetic_defects": synthetic_defects,
        "split_mesh_boundaries": split_mesh.boundaries,
        "movement_boundaries": movement.new_boundaries,
        "destination_mesh_boundaries": destination_mesh.boundaries,
        "transferred_unknowns": transferred,
        "transferred_phase_values": transferred_reference.stage_values,
        "transferred_phase_derivatives": transferred_reference.stage_derivatives,
        "transferred_tangent": transferred_tangent,
        "restart_corrected_unknowns": restart_execution.unknowns,
        "restart_rebootstrapped_tangent": np.empty(0) if restart_execution.tangent is None else restart_execution.tangent,
    }
    for density in monitor.densities:
        arrays[f"density_{density.name}_raw"] = density.raw
        arrays[f"density_{density.name}_normalized"] = density.normalized
    vector_bytes = npz_bytes(arrays)
    vector_manifest = {key: {"shape": list(np.asarray(value).shape), "sha256": array_digest(np.asarray(value))} for key, value in arrays.items()}
    data = {
        "schema_version": SCHEMA_VERSION,
        "method_version": ADAPTIVE_METHOD_VERSION,
        "source_provenance": {
            "generator": {"path": str(SCRIPT_PATH.relative_to(ROOT)), "sha256": sha256_file(SCRIPT_PATH)},
            "adaptive_orbits": {"path": str(ADAPTIVE_ORBITS_PATH.relative_to(ROOT)), "sha256": sha256_file(ADAPTIVE_ORBITS_PATH)},
            "periodic_orbits": {"path": str(PERIODIC_ORBITS_PATH.relative_to(ROOT)), "sha256": sha256_file(PERIODIC_ORBITS_PATH)},
            "bootstrap_seed": {"path": str(SEED_PATH.relative_to(ROOT)), "sha256": sha256_file(SEED_PATH)},
        "fixed_qualification": {"path": str(FIXED_QUALIFICATION_JSON.relative_to(ROOT)), "sha256": sha256_file(FIXED_QUALIFICATION_JSON)},
        "fixed_qualification_vectors": {"path": str(FIXED_QUALIFICATION_NPZ.relative_to(ROOT)), "sha256": sha256_file(FIXED_QUALIFICATION_NPZ)},
        },
        "defect": {
            "next_gauss": grid_record(defect.next_gauss),
            "staggered_dyadic": grid_record(defect.staggered_dyadic),
            "probe_16": None if defect.probe_16 is None else grid_record(defect.probe_16),
            "combined_element_maxima_sha256": array_digest(defect.combined_element_maxima),
            "grid_disagreement_sha256": array_digest(defect.grid_disagreement),
            "maximum": defect.maximum,
            "argmax_bin": defect.argmax_bin,
        },
        "synthetic_probe_escalation": {
            "materially_disagreeing_elements": np.flatnonzero(synthetic_material).tolist(),
            "probe_admitted_sha256": array_digest(synthetic_probe_admitted),
            "combined_sha256": array_digest(synthetic_combined),
            "unflagged_probe_element_ignored": int(np.argmax(synthetic_probe)) not in np.flatnonzero(synthetic_material).tolist(),
        },
        "monitor": {
            "version": MONITOR_VERSION,
            "subcells_per_element": 16,
            "density_order": [density.name for density in monitor.densities],
            "densities": [density_record(density) for density in monitor.densities],
            "value_sha256": array_digest(monitor.values),
            "total_mass": monitor.total_mass,
            "target_boundary_sha256": array_digest(monitor.target_boundaries),
        },
        "marking": {
            "version": H_MARKING_VERSION,
            "marked_elements": list(marking.marked_elements),
            "uncapped_marked_elements": list(marking.uncapped_marked_elements),
            "growth_limit": marking.growth_limit,
            "new_interval_count": marking.new_interval_count,
            "split_mesh_sha256": array_digest(split_mesh.boundaries),
        },
        "movement": {
            "version": R_MOVEMENT_VERSION,
            "accepted": movement.accepted,
            "stalled": movement.stalled,
            "beta": movement.beta,
            "attempted_betas": list(movement.attempted_betas),
            "rejection_reasons": list(movement.rejection_reasons),
            "new_boundaries_sha256": array_digest(movement.new_boundaries),
        },
        "transfer": {
            "destination_interval_count": destination_mesh.interval_count,
            "transferred_unknowns_sha256": array_digest(transferred),
            "transferred_phase_energy": transferred_reference.phase_energy,
            "transferred_tangent_sha256": array_digest(transferred_tangent),
        },
        "restart_retry": {
            "version": RESTART_RETRY_VERSION,
            "h_plus_r": [attempt.__dict__ for attempt in restart_plan(remesh_kind="h+r").attempts],
            "pure_r": [attempt.__dict__ for attempt in restart_plan(remesh_kind="pure-r").attempts],
            "tangent_only_failure": [attempt.__dict__ for attempt in restart_plan(remesh_kind="h+r", tangent_only_failure=True).attempts],
            "executed_tangent_only_rebootstrap": {
                "accepted": restart_execution.accepted,
                "attempt_names": [attempt.attempt.name for attempt in restart_execution.attempts],
                "final_rejection_reasons": list(restart_execution.rejection_reasons),
                "unknowns_sha256": array_digest(restart_execution.unknowns),
                "tangent_sha256": "" if restart_execution.tangent is None else array_digest(restart_execution.tangent),
            },
        },
        "vector_artifact": {
            "path": str(VECTORS_PATH.relative_to(ROOT)),
            "sha256": digest(vector_bytes),
            "arrays": vector_manifest,
        },
        "downstream_evidence_status": {
            "broader_ivp_radau_evidence": "not_evaluated_through_TASK_068",
            "floquet_dependent_evidence": "not_evaluated_through_TASK_068",
        },
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
