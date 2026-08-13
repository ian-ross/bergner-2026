#!/usr/bin/env python3
"""Generate deterministic Episode 008 fixed-mesh continuation fixtures."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from bergner_spichtinger_2026 import (
    CONTINUATION_FORMULATION_VERSION,
    CONTINUATION_METRIC_VERSION,
    MIDPOINT_FORMULATION_VERSION,
    PARAMETER_COLUMN_VERSION,
    FixedMesh,
    FixedMeshContinuationMetric,
    FixedMeshOrbitFamily,
    FixedTemperatureRhoPath,
    FrozenPhaseReference,
    HopfLocusCoordinates,
    OrbitContinuationPoint,
    PeriodicHermiteSeed,
    SpineTemperaturePath,
    continue_to_coordinate,
    controlled_phase_reference_restart,
    gauss_legendre_rule,
    point_diagnostics,
    sha256_file,
)
from bergner_spichtinger_2026.constants import Environment


REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = EPISODE_ROOT / "outputs/bootstrap_seed.json"
MIDPOINT_VECTORS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_vectors.npz"
HOPF_LOCI_PATH = (
    REPO_ROOT
    / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"
)
RESULTS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_continuation_results.json"
VECTORS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_continuation_vectors.npz"
SCHEMA_VERSION = "1.0.0"
INTERVAL_COUNT = 64


def _canonical_json(mapping: dict[str, Any]) -> bytes:
    return (json.dumps(mapping, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    return _sha256(np.ascontiguousarray(array, dtype="<f8").tobytes(order="C"))


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for key in sorted(arrays):
                member = io.BytesIO()
                np.lib.format.write_array(member, np.asarray(arrays[key]), allow_pickle=False)
                info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, member.getvalue())
        return output.getvalue()


def _environment(parameters: dict[str, Any]) -> Environment:
    return Environment(
        T=parameters["T"],
        p=parameters["p"],
        w=parameters["w"],
        F=parameters["F"],
        N_a=parameters["N_a"],
        Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )


def _event_coordinate(event: dict[str, object]) -> float | None:
    for key in (
        "corrected_coordinate",
        "target_coordinate",
        "trial_coordinate",
        "coordinate",
        "new_coordinate",
        "predictor_coordinate",
    ):
        value = event.get(key)
        if isinstance(value, (float, int)) and np.isfinite(value):
            return float(value)
    return None


def _physical_coordinate_record(path: FixedTemperatureRhoPath | SpineTemperaturePath, coordinate: float) -> dict[str, float]:
    values = path.coordinates(coordinate)
    return {
        "active_coordinate": values.active_coordinate,
        "temperature_hat": values.temperature_hat,
        "rho": values.rho,
        "temperature_K": values.temperature_K,
        "log_w": values.log_w,
        "w_m_s": values.w_m_s,
    }


def build_outputs() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    seed_mapping = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed = PeriodicHermiteSeed.from_json(SEED_PATH, verify_upstream_root=REPO_ROOT)
    base_environment = _environment(seed_mapping["canonical_parameters"])
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI_PATH)
    mesh = FixedMesh.uniform(INTERVAL_COUNT)
    rule = gauss_legendre_rule(1)
    state_scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    initial_reference = FrozenPhaseReference.from_evaluator(
        mesh,
        rule,
        seed.evaluate,
        seed.derivative,
        state_scaling=state_scaling,
    )
    fixed_225_path = FixedTemperatureRhoPath(locus, base_environment, 225.0)
    initial_family = FixedMeshOrbitFamily(
        mesh,
        initial_reference,
        fixed_225_path,
        "phase-ref-episode007-seed",
    )
    initial_metric = FixedMeshContinuationMetric.from_family(initial_family)
    with np.load(MIDPOINT_VECTORS_PATH, allow_pickle=False) as midpoint_vectors:
        initial_unknowns = np.array(midpoint_vectors["n64_unknowns"], copy=True)
    origin_rho = locus.rho(225.0, np.log(0.1))
    origin = OrbitContinuationPoint(
        point_id="episode007-n64-origin",
        branch_id="episode007-bootstrap-origin",
        point_kind="fixed_parameter_origin",
        unknowns=initial_unknowns,
        coordinate=origin_rho,
        phase_reference_id=initial_family.phase_reference_id,
        parent_point_id=None,
        branch_orientation=1,
        accepted_step_size=0.0,
    )

    to_spine = continue_to_coordinate(
        initial_family,
        initial_metric,
        origin,
        branch_id="fixed225-to-spine",
        target_coordinate=0.0,
        bootstrap_coordinate_step=0.02,
        maximum_bootstrap_weighted_step=0.025,
    )
    if not to_spine.reached_target or to_spine.points[-1].coordinate != 0.0:
        raise RuntimeError("fixed-temperature branch did not land on the exact T=225 K spine coordinate.")
    spine_225 = to_spine.points[-1]

    spine_path = SpineTemperaturePath(locus, base_environment)
    spine_family, spine_origin, spine_refresh = controlled_phase_reference_restart(
        initial_family,
        spine_225,
        new_phase_reference_id="phase-ref-spine-225",
        new_path=spine_path,
    )
    spine_metric = FixedMeshContinuationMetric.from_family(spine_family)
    spine_up = continue_to_coordinate(
        spine_family,
        spine_metric,
        spine_origin,
        branch_id="spine-positive-T-hat",
        target_coordinate=locus.temperature_hat(226.0),
        bootstrap_coordinate_step=0.01,
    )
    spine_down = continue_to_coordinate(
        spine_family,
        spine_metric,
        spine_origin,
        branch_id="spine-negative-T-hat-to-210",
        target_coordinate=locus.temperature_hat(210.0),
        bootstrap_coordinate_step=0.01,
        maximum_steps=100,
    )
    if not (
        spine_up.reached_target
        and spine_down.reached_target
        and spine_up.points[-1].coordinate == locus.temperature_hat(226.0)
        and spine_down.points[-1].coordinate == locus.temperature_hat(210.0)
    ):
        raise RuntimeError("bidirectional fixed-mesh spine validation did not land on exact targets.")

    spine_210 = spine_down.points[-1]
    slice_210_path = FixedTemperatureRhoPath(locus, base_environment, 210.0)
    slice_family, slice_origin, slice_refresh = controlled_phase_reference_restart(
        spine_family,
        spine_210,
        new_phase_reference_id="phase-ref-slice-210",
        new_path=slice_210_path,
    )
    slice_metric = FixedMeshContinuationMetric.from_family(slice_family)
    slice_lower = continue_to_coordinate(
        slice_family,
        slice_metric,
        slice_origin,
        branch_id="slice210-negative-rho",
        target_coordinate=-0.15,
        bootstrap_coordinate_step=0.02,
    )
    slice_upper = continue_to_coordinate(
        slice_family,
        slice_metric,
        slice_origin,
        branch_id="slice210-positive-rho",
        target_coordinate=0.15,
        bootstrap_coordinate_step=0.02,
    )
    if not (
        slice_lower.reached_target
        and slice_upper.reached_target
        and slice_lower.points[-1].coordinate == -0.15
        and slice_upper.points[-1].coordinate == 0.15
    ):
        raise RuntimeError("bidirectional fixed-mesh T=210 K slice validation did not land on exact targets.")

    segments = (
        ("fixed225-to-spine", to_spine, initial_family, initial_metric),
        ("spine-positive-T-hat", spine_up, spine_family, spine_metric),
        ("spine-negative-T-hat-to-210", spine_down, spine_family, spine_metric),
        ("slice210-negative-rho", slice_lower, slice_family, slice_metric),
        ("slice210-positive-rho", slice_upper, slice_family, slice_metric),
    )
    points_by_id: dict[str, tuple[OrbitContinuationPoint, FixedMeshOrbitFamily, FixedMeshContinuationMetric]] = {}
    events: list[dict[str, object]] = []
    branch_paths: dict[str, FixedTemperatureRhoPath | SpineTemperaturePath] = {}
    for branch_id, segment, family, metric in segments:
        branch_paths[branch_id] = family.path
        for point in segment.points:
            points_by_id.setdefault(point.point_id, (point, family, metric))
        for event in segment.events:
            record = dict(event)
            coordinate = _event_coordinate(record)
            if coordinate is not None:
                record["physical_coordinates"] = _physical_coordinate_record(family.path, coordinate)
            events.append(record)

    for restarted_point, refresh, family, metric in (
        (spine_origin, spine_refresh, spine_family, spine_metric),
        (slice_origin, slice_refresh, slice_family, slice_metric),
    ):
        points_by_id[restarted_point.point_id] = (restarted_point, family, metric)
        record = dict(refresh)
        record["physical_coordinates"] = _physical_coordinate_record(
            family.path, float(refresh["new_coordinate"])
        )
        events.append(record)

    point_records: list[dict[str, object]] = []
    arrays: dict[str, np.ndarray] = {
        "mesh_boundaries": np.asarray(mesh.boundaries, dtype="<f8"),
        "metric_diagonal_initial": np.asarray(initial_metric.weights, dtype="<f8"),
        "metric_diagonal_spine": np.asarray(spine_metric.weights, dtype="<f8"),
        "metric_diagonal_slice210": np.asarray(slice_metric.weights, dtype="<f8"),
        "phase_ref_episode007_values": np.asarray(initial_reference.stage_values, dtype="<f8"),
        "phase_ref_episode007_derivatives": np.asarray(initial_reference.stage_derivatives, dtype="<f8"),
        "phase_ref_spine225_values": np.asarray(spine_family.phase_reference.stage_values, dtype="<f8"),
        "phase_ref_spine225_derivatives": np.asarray(spine_family.phase_reference.stage_derivatives, dtype="<f8"),
        "phase_ref_slice210_values": np.asarray(slice_family.phase_reference.stage_values, dtype="<f8"),
        "phase_ref_slice210_derivatives": np.asarray(slice_family.phase_reference.stage_derivatives, dtype="<f8"),
    }
    for point_id, (point, family, metric) in points_by_id.items():
        record = point_diagnostics(point, family, metric)
        vector_key = f"point__{point_id}"
        arrays[vector_key] = np.asarray(point.unknowns, dtype="<f8")
        record["vector_key"] = vector_key
        point_records.append(record)
    point_records.sort(key=lambda record: str(record["point_id"]))

    array_manifest = {
        key: {
            "dtype": "float64-little-endian",
            "shape": list(value.shape),
            "sha256": _array_sha256(value),
        }
        for key, value in sorted(arrays.items())
    }
    accepted_events = sum(event.get("accepted") is True for event in events)
    rejected_events = sum(event.get("accepted") is False for event in events)
    informational_events = sum("accepted" not in event for event in events)
    branches = [
        {
            "branch_id": branch_id,
            "active_coordinate_name": family.path.coordinate_name,
            "phase_reference_id": family.phase_reference_id,
            "branch_orientation": segment.points[1].branch_orientation,
            "origin_coordinate": segment.points[0].coordinate,
            "target_coordinate": segment.points[-1].coordinate,
            "accepted_point_count_including_origin": len(segment.points),
            "reached_exact_target": segment.reached_target,
        }
        for branch_id, segment, family, _ in segments
    ]
    mapping: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "episode008_fixed_mesh_midpoint_pseudo_arclength_validation",
        "scientific_scope": {
            "fixed_mesh": True,
            "midpoint_interval_count": INTERVAL_COUNT,
            "production_accuracy_claimed": False,
            "accuracy_warning": "These branches validate continuation machinery on the inaccurate N=64 midpoint baseline; small residuals do not establish period or continuous-orbit accuracy.",
        },
        "method": {
            "continuation_formulation_version": CONTINUATION_FORMULATION_VERSION,
            "continuation_metric_version": CONTINUATION_METRIC_VERSION,
            "midpoint_formulation_version": MIDPOINT_FORMULATION_VERSION,
            "parameter_column_version": PARAMETER_COLUMN_VERSION,
            "nonlinear_solver": "scipy.optimize.least_squares(method='trf') with sparse CSR augmented Jacobian",
            "state_coordinates": ["log(n)", "log(q)", "s"],
            "period_coordinate": "log(period_s)",
            "normalized_coordinates": {
                "temperature_hat": "(T - 215 K) / 25 K",
                "rho": "(log(w) - log(w_spine(T))) / (0.5 * (log(w_upper(T)) - log(w_lower(T))))",
            },
            "metric": {
                "state_scaling": state_scaling.tolist(),
                "state_scaling_definition": "reciprocal exact peak-to-peak ranges of frozen Episode 007 transformed-state knots excluding duplicate terminal knot",
                "endpoint_representation_weight": 0.5,
                "stage_representation_weight": 0.5,
                "log_period_weight": 1.0,
                "active_coordinate_weight": 1.0,
                "uses": ["secants", "tangent normalization", "predictors", "arclength constraint", "reported step sizes"],
            },
            "phase_reference_policy": "immutable within each segment; refresh only at recorded phase_reference_refresh controlled restarts",
            "bootstrap_policy": "signed fixed-parameter corrected neighbor with excessive-step/failure rejection and deterministic halving",
        },
        "runtime_provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "source_provenance": {
            "generator_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
            "generator_sha256": sha256_file(Path(__file__).resolve()),
            "periodic_continuation_path": "src/bergner_spichtinger_2026/periodic_continuation.py",
            "periodic_continuation_sha256": sha256_file(
                REPO_ROOT / "src/bergner_spichtinger_2026/periodic_continuation.py"
            ),
            "periodic_orbits_path": "src/bergner_spichtinger_2026/periodic_orbits.py",
            "periodic_orbits_sha256": sha256_file(
                REPO_ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"
            ),
            "episode007_seed_path": SEED_PATH.relative_to(REPO_ROOT).as_posix(),
            "episode007_seed_sha256": sha256_file(SEED_PATH),
            "episode006_hopf_loci_path": HOPF_LOCI_PATH.relative_to(REPO_ROOT).as_posix(),
            "episode006_hopf_loci_sha256": sha256_file(HOPF_LOCI_PATH),
            "task056_midpoint_vectors_path": MIDPOINT_VECTORS_PATH.relative_to(REPO_ROOT).as_posix(),
            "task056_midpoint_vectors_sha256": sha256_file(MIDPOINT_VECTORS_PATH),
        },
        "canonical_parameters_except_T_w": {
            key: value
            for key, value in seed_mapping["canonical_parameters"].items()
            if key not in {"T", "w"}
        },
        "validated_coordinates": {
            "episode007_origin": _physical_coordinate_record(fixed_225_path, origin_rho),
            "exact_T225_spine": _physical_coordinate_record(fixed_225_path, 0.0),
            "exact_T210_spine": _physical_coordinate_record(spine_path, locus.temperature_hat(210.0)),
            "T210_slice_targets_rho": [-0.15, 0.15],
            "positive_spine_target_T_K": 226.0,
        },
        "summary": {
            "branch_count": len(branches),
            "accepted_point_count": len(point_records),
            "accepted_event_count": accepted_events,
            "rejected_event_count": rejected_events,
            "informational_event_count": informational_events,
            "controlled_phase_reference_refresh_count": 2,
            "every_branch_reached_exact_target": all(branch["reached_exact_target"] for branch in branches),
        },
        "branches": branches,
        "points": point_records,
        "events": events,
        "vector_artifact": {
            "path": VECTORS_PATH.relative_to(REPO_ROOT).as_posix(),
            "format": "deterministic uncompressed NPZ containing NumPy .npy float64 arrays; allow_pickle=False",
            "unknown_order": "all N endpoint blocks, all N one-stage midpoint blocks, then log(period_s)",
            "arrays": array_manifest,
        },
    }
    return mapping, arrays


def generate(*, check: bool = False) -> None:
    mapping, arrays = build_outputs()
    expected_npz = _npz_bytes(arrays)
    mapping["vector_artifact"]["file_sha256"] = _sha256(expected_npz)
    expected_json = _canonical_json(mapping)
    if check:
        if not RESULTS_PATH.is_file() or not VECTORS_PATH.is_file():
            raise SystemExit("Missing fixed-mesh continuation generated artifacts.")
        if VECTORS_PATH.read_bytes() != expected_npz:
            raise SystemExit(f"Generated artifact byte drift: {VECTORS_PATH}")
        if RESULTS_PATH.read_bytes() != expected_json:
            raise SystemExit(f"Generated artifact drift: {RESULTS_PATH}")
        print(f"verified {RESULTS_PATH.relative_to(REPO_ROOT)}")
        print(f"verified {VECTORS_PATH.relative_to(REPO_ROOT)}")
        return
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.write_bytes(expected_npz)
    RESULTS_PATH.write_bytes(expected_json)
    print(f"wrote {RESULTS_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote {VECTORS_PATH.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed outputs differ")
    args = parser.parse_args()
    generate(check=args.check)


if __name__ == "__main__":
    main()
