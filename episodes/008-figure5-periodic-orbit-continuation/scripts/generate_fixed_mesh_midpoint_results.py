#!/usr/bin/env python3
"""Correct and freeze Episode 008 uniform fixed-mesh midpoint baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from bergner_spichtinger_2026 import (
    MIDPOINT_FORMULATION_VERSION,
    MIDPOINT_SOLVER_VERSION,
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    MidpointResidualTolerances,
    PeriodicHermiteSeed,
    correct_midpoint_orbit,
    gauss_legendre_rule,
    sha256_file,
)
from bergner_spichtinger_2026.constants import Environment


REPO_ROOT = Path(__file__).resolve().parents[3]
EPISODE_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = EPISODE_ROOT / "outputs/bootstrap_seed.json"
RESULTS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_results.json"
VECTORS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_vectors.npz"
MESH_COUNTS = (32, 64, 128, 256)
SCHEMA_VERSION = "1.1.0"


def _canonical_json(mapping: dict[str, Any]) -> bytes:
    return (json.dumps(mapping, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def _seed_scaling(seed: PeriodicHermiteSeed) -> np.ndarray:
    ranges = np.ptp(seed.transformed_state[:-1], axis=0)
    if np.any(ranges <= 0.0) or not np.all(np.isfinite(ranges)):
        raise ValueError("frozen seed has invalid transformed-state ranges.")
    return 1.0 / ranges


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array, dtype="<f8")
    return _bytes_sha256(value.tobytes(order="C"))


def _deterministic_nonsolution(unknowns: np.ndarray) -> np.ndarray:
    result = np.array(unknowns, dtype=float, copy=True)
    direction = np.sin(np.arange(result.size, dtype=float) + 0.375)
    result[:-1] += 2.0e-3 * direction[:-1]
    result[-1] += 3.0e-4 * direction[-1]
    return result


def _build_case(
    interval_count: int,
    seed: PeriodicHermiteSeed,
    env: Environment,
    scaling: np.ndarray,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    mesh = FixedMesh.uniform(interval_count)
    rule = gauss_legendre_rule(1)
    reference = FrozenPhaseReference.from_evaluator(
        mesh,
        rule,
        seed.evaluate,
        seed.derivative,
        state_scaling=scaling,
    )
    assembler = MidpointCollocationAssembler(mesh, env, reference)
    initial = assembler.reference_unknowns(seed.evaluate, seed.log_period)
    result = correct_midpoint_orbit(assembler, initial)
    comparison = assembler.compare_with_reference(
        result.unknowns,
        seed.evaluate,
        seed.log_period,
        align_phase=True,
    )
    variables = assembler.layout.unpack(result.unknowns)
    period_s = float(np.exp(variables.log_period))
    correction = assembler.weighted_orbit_distance(result.unknowns, initial)
    period_relative_error = abs(period_s - seed.period_s) / seed.period_s
    key = f"n{interval_count}"
    arrays = {
        f"{key}_boundaries": np.asarray(mesh.boundaries, dtype="<f8"),
        f"{key}_unknowns": np.asarray(result.unknowns, dtype="<f8"),
        f"{key}_residual": np.asarray(assembler.residual(result.unknowns), dtype="<f8"),
        f"{key}_phase_reference_values": np.asarray(reference.stage_values, dtype="<f8"),
        f"{key}_phase_reference_derivatives": np.asarray(reference.stage_derivatives, dtype="<f8"),
    }
    if interval_count == 64:
        nonsolution = _deterministic_nonsolution(result.unknowns)
        arrays["n64_nonsolution_unknowns"] = np.asarray(nonsolution, dtype="<f8")
        arrays["n64_nonsolution_residual"] = np.asarray(
            assembler.residual(nonsolution), dtype="<f8"
        )
    diagnostics = result.diagnostics
    record = {
        "interval_count": interval_count,
        "accepted": result.accepted,
        "rejection_reasons": list(result.rejection_reasons),
        "period_s": period_s,
        "period_relative_error_vs_episode007": period_relative_error,
        "weighted_orbit_correction_from_seed": correction,
        "weighted_orbit_error_vs_episode007": comparison.distance,
        "episode007_comparison_phase_shift_cycles": comparison.phase_shift,
        "stage_residual_max": diagnostics.stage_max,
        "stage_residual_rms": diagnostics.stage_rms,
        "update_residual_max": diagnostics.update_max,
        "update_residual_rms": diagnostics.update_rms,
        "phase_residual_abs": diagnostics.phase_abs,
        "phase_energy": assembler.phase_energy,
        "scipy_success": result.scipy_success,
        "scipy_status": result.scipy_status,
        "scipy_message": result.scipy_message,
        "scipy_cost": result.scipy_cost,
        "scipy_optimality": result.scipy_optimality,
        "function_evaluations": result.function_evaluations,
        "jacobian_evaluations": result.jacobian_evaluations,
        "packed_step_norm": result.packed_step_norm,
        "vector_keys": sorted(arrays),
    }
    return record, arrays


def _npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    """Return deterministic uncompressed NPZ bytes for the supplied arrays."""
    import io
    import zipfile

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


def build_outputs() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    seed_mapping = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed = PeriodicHermiteSeed.from_json(SEED_PATH, verify_upstream_root=REPO_ROOT)
    env = _environment(seed_mapping["canonical_parameters"])
    scaling = _seed_scaling(seed)
    records: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    for interval_count in MESH_COUNTS:
        record, case_arrays = _build_case(interval_count, seed, env, scaling)
        records.append(record)
        arrays.update(case_arrays)

    array_manifest = {
        key: {
            "dtype": "float64-little-endian",
            "shape": list(value.shape),
            "sha256": _array_sha256(value),
        }
        for key, value in sorted(arrays.items())
    }
    tolerances = MidpointResidualTolerances()
    mapping: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "episode008_fixed_mesh_midpoint_validation",
        "formulation_version": MIDPOINT_FORMULATION_VERSION,
        "solver_version": MIDPOINT_SOLVER_VERSION,
        "runtime_provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "source_provenance": {
            "generator_path": Path(__file__).resolve().relative_to(REPO_ROOT).as_posix(),
            "generator_sha256": sha256_file(Path(__file__).resolve()),
            "periodic_orbits_path": "src/bergner_spichtinger_2026/periodic_orbits.py",
            "periodic_orbits_sha256": sha256_file(
                REPO_ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"
            ),
        },
        "scientific_scope": {
            "discrete_nonlinear_convergence": "accepted only by independent stage/update/phase block thresholds",
            "accuracy_warning": "A small discrete residual does not establish continuous-orbit or period accuracy; compare the separate Episode 007 error fields.",
            "production_accuracy_claimed": False,
        },
        "mesh_interval_counts": list(MESH_COUNTS),
        "state_coordinates": ["log(n)", "log(q)", "s"],
        "state_scaling": scaling.tolist(),
        "state_scaling_definition": "reciprocal exact peak-to-peak ranges of frozen Episode 007 transformed-state knots excluding duplicate terminal knot",
        "residual_tolerances": {
            "stage_max": tolerances.stage_max,
            "stage_rms": tolerances.stage_rms,
            "update_max": tolerances.update_max,
            "update_rms": tolerances.update_rms,
            "phase_abs": tolerances.phase_abs,
        },
        "solver_options": {
            "library": "scipy.optimize.least_squares",
            "method": "trf",
            "jacobian": "analytic scipy.sparse.csr_matrix",
            "x_scale": "jac",
            "xtol": 1.0e-13,
            "ftol": 1.0e-13,
            "gtol": 1.0e-13,
            "max_nfev": 1000,
        },
        "episode007_reference": {
            "seed_path": SEED_PATH.relative_to(REPO_ROOT).as_posix(),
            "seed_sha256": sha256_file(SEED_PATH),
            "seed_id": seed_mapping["seed_id"],
            "period_s": seed.period_s,
        },
        "canonical_parameters": seed_mapping["canonical_parameters"],
        "vector_artifact": {
            "path": VECTORS_PATH.relative_to(REPO_ROOT).as_posix(),
            "format": "deterministic uncompressed NPZ containing NumPy .npy float64 arrays; allow_pickle=False",
            "unknown_order": "all N endpoint blocks, all N one-stage midpoint blocks, then log(period_s)",
            "residual_order": "all N scaled stage blocks, all N scaled cyclic-update blocks, then normalized phase residual",
            "array_checksum": "SHA-256 of contiguous little-endian float64 C-order bytes",
            "parity_cases": {
                "n64_solution": "accepted corrected orbit and cancellation-scale residual",
                "n64_nonsolution": "deterministic 2e-3 state/stage and 3e-4 log-period perturbation of the accepted orbit; all residual blocks are nontrivial",
            },
            "arrays": array_manifest,
        },
        "results": records,
    }
    return mapping, arrays


def generate(*, check: bool = False) -> None:
    mapping, arrays = build_outputs()
    expected_npz = _npz_bytes(arrays)
    mapping["vector_artifact"]["file_sha256"] = _bytes_sha256(expected_npz)
    expected_json = _canonical_json(mapping)

    if check:
        if not RESULTS_PATH.is_file():
            raise SystemExit(f"Missing generated artifact: {RESULTS_PATH}")
        if not VECTORS_PATH.is_file():
            raise SystemExit(f"Missing generated artifact: {VECTORS_PATH}")
        if VECTORS_PATH.read_bytes() != expected_npz:
            raise SystemExit(f"Generated artifact byte drift: {VECTORS_PATH}")
        if RESULTS_PATH.read_bytes() != expected_json:
            raise SystemExit(f"Generated artifact drift: {RESULTS_PATH}")
        with np.load(VECTORS_PATH, allow_pickle=False) as frozen:
            if set(frozen.files) != set(arrays):
                raise SystemExit(f"Generated artifact drift: {VECTORS_PATH} array keys")
            for key, expected in arrays.items():
                if not np.array_equal(frozen[key], expected):
                    raise SystemExit(f"Generated artifact drift: {VECTORS_PATH}:{key}")
                manifest = mapping["vector_artifact"]["arrays"][key]
                if _array_sha256(frozen[key]) != manifest["sha256"]:
                    raise SystemExit(f"Generated artifact checksum drift: {VECTORS_PATH}:{key}")
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
