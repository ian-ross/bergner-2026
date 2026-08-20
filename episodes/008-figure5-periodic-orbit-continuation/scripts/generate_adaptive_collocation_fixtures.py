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
    monitor = build_composite_r_monitor(assembler, unknowns)
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
    arrays = {
        "input_mesh_boundaries": assembler.mesh.boundaries,
        "input_unknowns": unknowns,
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
