#!/usr/bin/env python3
"""Generate language-neutral TASK-059 midpoint parity fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bergner_spichtinger_2026 import (  # noqa: E402
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    PeriodicHermiteSeed,
    correct_midpoint_orbit,
    gauss_legendre_rule,
    MIDPOINT_FORMULATION_VERSION,
    JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
)
from bergner_spichtinger_2026.constants import Environment  # noqa: E402

EPISODE_ROOT = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
OUTPUT_ROOT = EPISODE_ROOT / "outputs" / "tpetra_midpoint_fixtures"
SEED_PATH = EPISODE_ROOT / "outputs/bootstrap_seed.json"
MIDPOINT_RESULTS = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_results.json"
MIDPOINT_VECTORS = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_vectors.npz"
MANIFEST_PATH = OUTPUT_ROOT / "manifest.json"
CASE_NAMES = (
    "n8_converged", "n8_nonsolution", "n64_converged", "n64_nonsolution",
    "n64_seed", "n64_perturbed",
)
SCHEMA_VERSION = "1.1.0"
PARITY_RELATIVE_TOLERANCE = 1.0e-11
PARITY_ABSOLUTE_FLOOR = 1.0e-13
CORRECTED_SOLUTION_PARITY_TOLERANCE = 1.0e-8
PERTURBATION_STATE_AMPLITUDE = 1.0e-4
PERTURBATION_LOG_PERIOD_AMPLITUDE = 1.0e-5
PERTURBATION_PHASE_OFFSET = 0.375


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(mapping: dict) -> bytes:
    return (json.dumps(mapping, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _environment() -> Environment:
    parameters = json.loads(SEED_PATH.read_text(encoding="utf-8"))["canonical_parameters"]
    return Environment(
        T=parameters["T"], p=parameters["p"], w=parameters["w"], F=parameters["F"],
        N_a=parameters["N_a"], Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )


def _assembler(count: int):
    seed = PeriodicHermiteSeed.from_json(SEED_PATH)
    mesh = FixedMesh.uniform(count)
    rule = gauss_legendre_rule(1)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    reference = FrozenPhaseReference.from_evaluator(
        mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling
    )
    return seed, MidpointCollocationAssembler(mesh, _environment(), reference)


def _write_fixture(name: str, assembler: MidpointCollocationAssembler, unknowns: np.ndarray) -> bytes:
    env = assembler.env
    reference = assembler.phase_reference
    lines = [
        f"BS2026_MIDPOINT_FIXTURE_V1 {name} {assembler.layout.interval_count}",
        " ".join(f"{value:.17g}" for value in (env.p, env.T, env.w, env.F, env.N_a, env.Δz)),
        " ".join(f"{value:.17g}" for value in (np.log(0.01), np.log(0.25), 0.037)),
        " ".join(f"{value:.17g}" for value in reference.state_scaling),
        " ".join(f"{value:.17g}" for value in assembler.mesh.boundaries),
        " ".join(f"{value:.17g}" for value in reference.stage_values.reshape(-1)),
        " ".join(f"{value:.17g}" for value in reference.stage_derivatives.reshape(-1)),
        " ".join(f"{value:.17g}" for value in unknowns),
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _assert_residual_semantics(name: str, assembler: MidpointCollocationAssembler,
                               unknowns: np.ndarray, expected_residual: np.ndarray | None = None) -> None:
    residual = assembler.residual(unknowns)
    if expected_residual is not None:
        np.testing.assert_array_equal(residual, expected_residual)
    blocks = assembler.layout.unpack_residual(residual)
    diagnostics = np.array([
        np.max(np.abs(blocks.stages)),
        np.sqrt(np.mean(blocks.stages**2)),
        np.max(np.abs(blocks.updates)),
        np.sqrt(np.mean(blocks.updates**2)),
        abs(blocks.phase),
    ])
    if name.endswith("converged"):
        gates = np.array([1e-9, 1e-9, 1e-9, 1e-9, 1e-10])
        if np.any(diagnostics > gates):
            raise RuntimeError(f"{name} misses converged residual gates: {diagnostics}")
    elif name == "n64_seed":
        if not (np.all(np.linalg.norm(blocks.stages[:, 0], axis=1) > 0.0)
                and np.all(np.linalg.norm(blocks.updates, axis=1) > 0.0)):
            raise RuntimeError(f"{name} does not exercise stage and update blocks")
    elif not (np.all(np.linalg.norm(blocks.stages[:, 0], axis=1) > 0.0)
              and np.all(np.linalg.norm(blocks.updates, axis=1) > 0.0)
              and abs(blocks.phase) > 0.0):
        raise RuntimeError(f"{name} does not exercise every residual block")


def build() -> dict[str, bytes]:
    seed8, assembler8 = _assembler(8)
    initial8 = assembler8.reference_unknowns(seed8.evaluate, seed8.log_period)
    solved8 = correct_midpoint_orbit(assembler8, initial8)
    if not solved8.accepted:
        raise RuntimeError(f"N=8 correction failed: {solved8.rejection_reasons}")
    nonsolution8 = solved8.unknowns.copy()
    direction8 = np.sin(np.arange(nonsolution8.size, dtype=float) + 0.375)
    nonsolution8[:-1] += 2.0e-3 * direction8[:-1]
    nonsolution8[-1] += 3.0e-4 * direction8[-1]

    seed64, regenerated64 = _assembler(64)
    with np.load(MIDPOINT_VECTORS, allow_pickle=False) as vectors:
        frozen_reference = FrozenPhaseReference(
            mesh=FixedMesh(np.array(vectors["n64_boundaries"], copy=True)),
            stage_values=np.array(vectors["n64_phase_reference_values"], copy=True),
            stage_derivatives=np.array(vectors["n64_phase_reference_derivatives"], copy=True),
            state_scaling=regenerated64.state_scaling,
            collocation_nodes=np.asarray(gauss_legendre_rule(1).nodes),
            quadrature_weights=np.asarray(gauss_legendre_rule(1).quadrature_weights),
        )
        assembler64 = MidpointCollocationAssembler(frozen_reference.mesh, _environment(), frozen_reference)
        np.testing.assert_array_equal(assembler64.mesh.boundaries, regenerated64.mesh.boundaries)
        np.testing.assert_array_equal(assembler64.phase_reference.stage_values,
                                      regenerated64.phase_reference.stage_values)
        np.testing.assert_array_equal(assembler64.phase_reference.stage_derivatives,
                                      regenerated64.phase_reference.stage_derivatives)
        seed_unknowns64 = assembler64.reference_unknowns(seed64.evaluate, seed64.log_period)
        perturbed64 = seed_unknowns64.copy()
        perturbation = np.sin(np.arange(perturbed64.size, dtype=float) + PERTURBATION_PHASE_OFFSET)
        perturbed64[:-1] += PERTURBATION_STATE_AMPLITUDE * perturbation[:-1]
        perturbed64[-1] += PERTURBATION_LOG_PERIOD_AMPLITUDE * perturbation[-1]
        cases = {
            "n8_converged": (assembler8, np.asarray(solved8.unknowns)),
            "n8_nonsolution": (assembler8, nonsolution8),
            "n64_converged": (assembler64, np.array(vectors["n64_unknowns"], copy=True)),
            "n64_nonsolution": (assembler64, np.array(vectors["n64_nonsolution_unknowns"], copy=True)),
            "n64_seed": (assembler64, seed_unknowns64),
            "n64_perturbed": (assembler64, perturbed64),
        }
        _assert_residual_semantics("n64_converged", assembler64, cases["n64_converged"][1],
                                   vectors["n64_residual"])
        _assert_residual_semantics("n64_nonsolution", assembler64, cases["n64_nonsolution"][1],
                                   vectors["n64_nonsolution_residual"])
    _assert_residual_semantics("n8_converged", assembler8, solved8.unknowns)
    _assert_residual_semantics("n8_nonsolution", assembler8, nonsolution8)
    _assert_residual_semantics("n64_seed", assembler64, cases["n64_seed"][1])
    _assert_residual_semantics("n64_perturbed", assembler64, cases["n64_perturbed"][1])
    fixture_outputs = {name: _write_fixture(name, *cases[name]) for name in CASE_NAMES}
    generator_path = Path(__file__).resolve()
    source_paths = {
        "generator": generator_path,
        "python_assembler": REPO_ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py",
        "cpp_assembler": REPO_ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
        "cpp_nox_adapter": REPO_ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
        "cpp_cli": REPO_ROOT / "loca/src/midpoint_orbit_cli.cpp",
        "bootstrap_seed": SEED_PATH,
        "task056_results": MIDPOINT_RESULTS,
        "task056_vectors": MIDPOINT_VECTORS,
        "uv_lock": REPO_ROOT / "uv.lock",
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "episode008_tpetra_midpoint_parity_fixtures",
        "formulation_version": MIDPOINT_FORMULATION_VERSION,
        "parity_tolerance": {
            "relative": PARITY_RELATIVE_TOLERANCE,
            "absolute_floor": PARITY_ABSOLUTE_FLOOR,
        },
        "directional_relative_tolerance": JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
        "fixed_parameter_nox": {
            "solver_version": "thyra-nox-amesos2-klu2-v1",
            "linear_solver": "Amesos2 KLU2",
            "nox_norm_f_tolerance": 1.0e-11,
            "nox_max_iterations": 40,
            "direction_method": "Newton",
            "line_search_method": "Backtrack",
            "backtrack_default_step": 1.0,
            "backtrack_minimum_step": 1.0e-10,
            "backtrack_recovery_step": 1.0e-6,
            "refactorization_policy": "REPIVOT_ON_REFACTORIZATION",
            "accepted_stage_update_tolerance": 1.0e-9,
            "accepted_phase_tolerance": 1.0e-10,
            "corrected_solution_parity_tolerance": CORRECTED_SOLUTION_PARITY_TOLERANCE,
            "perturbation": {
                "formula": "x[k] += state_amplitude*sin(k+phase_offset), k < 6N; log(P) += log_period_amplitude*sin(6N+phase_offset)",
                "state_amplitude": PERTURBATION_STATE_AMPLITUDE,
                "log_period_amplitude": PERTURBATION_LOG_PERIOD_AMPLITUDE,
                "phase_offset": PERTURBATION_PHASE_OFFSET,
            },
        },
        "runtime_provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "source_provenance": {
            key: {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": _sha256_file(path),
            }
            for key, path in source_paths.items()
        },
        "cases": {
            name: {
                "interval_count": cases[name][0].layout.interval_count,
                "unknown_shape": [cases[name][0].layout.unknown_size],
                "residual_shape": [cases[name][0].layout.residual_size],
                "meaning": (
                    "accepted discrete solution" if name.endswith("converged")
                    else "canonical N=64 Hermite/bootstrap initial seed" if name == "n64_seed"
                    else "deterministically perturbed canonical N=64 Hermite/bootstrap initial seed" if name == "n64_perturbed"
                    else "deterministic nonsolution exercising stage, update, and phase blocks"
                ),
                "fixture_path": (OUTPUT_ROOT / f"{name}.txt").relative_to(REPO_ROOT).as_posix(),
                "fixture_sha256": _sha256_bytes(fixture_outputs[name]),
                "upstream": (
                    "Episode 007 Hermite seed sampled by the TASK-056 formulation" if name in {"n64_seed", "n64_perturbed"}
                    else "TASK-056 frozen arrays" if name.startswith("n64")
                    else "TASK-059 deterministic N=8 correction"
                ),
            }
            for name in CASE_NAMES
        },
    }
    fixture_outputs["manifest"] = _canonical_json(manifest)
    return fixture_outputs


def generate(*, check: bool) -> None:
    outputs = build()
    drift = []
    for name, content in outputs.items():
        path = MANIFEST_PATH if name == "manifest" else OUTPUT_ROOT / f"{name}.txt"
        if check:
            if not path.is_file() or path.read_bytes() != content:
                drift.append(path.relative_to(REPO_ROOT).as_posix())
        else:
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if drift:
        raise SystemExit("TASK-059 fixture byte drift: " + ", ".join(drift))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(check=args.check)


if __name__ == "__main__":
    main()
