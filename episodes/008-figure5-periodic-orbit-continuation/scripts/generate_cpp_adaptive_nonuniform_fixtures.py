#!/usr/bin/env python3
"""Project TASK-067 adaptive final nonuniform meshes into C++ parity fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import COLLOCATION_ARTIFACT_SHA256, gauss_legendre_rule, sha256_file  # noqa: E402
from bergner_spichtinger_2026.constants import Environment  # noqa: E402
from bergner_spichtinger_2026.periodic_orbits import OrbitLayout, transformed_vector_field  # noqa: E402

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
ADAPTIVE = OUTPUT / "adaptive_qualification_results.json"
ADAPTIVE_VECTORS = OUTPUT / "adaptive_qualification_vectors.npz"
FIXED = OUTPUT / "higher_order_fixed_mesh_qualification.json"
MIDPOINT = OUTPUT / "fixed_mesh_midpoint_results.json"
TARGET = OUTPUT / "cpp_adaptive_nonuniform_fixtures"
GENERATOR = Path(__file__).resolve()
SCHEMA_VERSION = "episode008-cpp-adaptive-nonuniform-fixtures-v1"
FIXTURE_MAGIC = "BS2026_GAUSS_FIXTURE_V1"
PERTURBATION_VERSION = "small-sinusoidal-nonuniform-correction-seed-v1"
CASE_IDS = (
    "canonical-g3-n32",
    "guard-rho-0-g3-n32",
    "guard-rho-minus-0.15-g3-n32",
    "guard-rho-plus-0.15-g3-n32",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_digest(value: np.ndarray) -> str:
    return digest(np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes())


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def rows(values: np.ndarray) -> list[str]:
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        return [" ".join(format(float(value), ".17g") for value in array)]
    return [" ".join(format(float(value), ".17g") for value in row) for row in array.reshape(-1, array.shape[-1])]


def environment_for(record: dict[str, Any]) -> Environment:
    return Environment(
        p=30000.0,
        T=float(record.get("temperature_K") or 225.0),
        w=float(record.get("w_m_s") or 0.1),
        F=1.0,
        N_a=1e10,
        Δz=100.0,
        include_evaporation=False,
    )


def refreshed_phase_reference(unknowns: np.ndarray, interval_count: int, env: Environment) -> tuple[np.ndarray, np.ndarray]:
    rule = gauss_legendre_rule(3)
    layout = OrbitLayout(interval_count, rule.stage_count)
    variables = layout.unpack(unknowns)
    period = float(np.exp(variables.log_period))
    phase_values = np.asarray(variables.stages, dtype=float).reshape(interval_count * rule.stage_count, 3)
    phase_derivatives = np.empty_like(phase_values)
    for row, state in enumerate(phase_values):
        phase_derivatives[row] = period * transformed_vector_field(state, env, None)
    return phase_values, phase_derivatives


def fixture_bytes(case_id: str, interval_count: int, env: Environment, scaling: np.ndarray,
                  boundaries: np.ndarray, phase_values: np.ndarray, phase_derivatives: np.ndarray,
                  unknowns: np.ndarray) -> bytes:
    lines = [
        f"{FIXTURE_MAGIC} adaptive-{case_id} {interval_count} 3 6 accepted {COLLOCATION_ARTIFACT_SHA256}",
        f"30000 {format(env.T, '.17g')} {format(env.w, '.17g')} 1 10000000000 100",
        f"{format(np.log(0.01), '.17g')} {format(np.log(0.25), '.17g')} 0.037",
        " ".join(format(float(value), ".17g") for value in scaling),
        *rows(boundaries),
        *rows(phase_values),
        *rows(phase_derivatives),
        *rows(unknowns),
    ]
    return ("\n".join(lines) + "\n").encode()


def build() -> dict[str, bytes]:
    adaptive = json.loads(ADAPTIVE.read_text())
    fixed = {item["case_id"]: item for item in json.loads(FIXED.read_text())["results"]}
    adaptive_by_case = {item["case_id"]: item for item in adaptive["results"]}
    scaling = np.asarray(json.loads(MIDPOINT.read_text())["state_scaling"], dtype=float)
    files: dict[str, bytes] = {}
    cases: list[dict[str, Any]] = []
    with np.load(ADAPTIVE_VECTORS, allow_pickle=False) as arrays:
        for case_id in CASE_IDS:
            result = adaptive_by_case[case_id]
            final = result["cycles"][-1]
            prefix = final["array_prefix"]
            boundaries = np.asarray(arrays[f"{prefix}__boundaries"], dtype=float)
            exact_unknowns = np.asarray(arrays[f"{prefix}__unknowns"], dtype=float)
            interval_count = boundaries.size - 1
            env = environment_for(fixed[case_id])
            phase_values, phase_derivatives = refreshed_phase_reference(exact_unknowns, interval_count, env)
            fixture_unknowns = exact_unknowns.copy()
            direction = np.sin(np.arange(fixture_unknowns.size, dtype=float) + 0.625)
            fixture_unknowns[:-1] += 1.0e-6 * direction[:-1]
            fixture_unknowns[-1] += 1.0e-7 * direction[-1]
            body = fixture_bytes(case_id, interval_count, env, scaling, boundaries,
                                 phase_values, phase_derivatives, fixture_unknowns)
            path = f"adaptive-{case_id}.txt"
            files[path] = body
            cases.append({
                "case_id": f"adaptive-{case_id}",
                "source_case_id": case_id,
                "path": path,
                "sha256": digest(body),
                "stage_count": 3,
                "formal_order": 6,
                "interval_count": interval_count,
                "status": "accepted",
                "terminal_status": result["terminal_status"],
                "final_defect_maximum": result["final_defect_maximum"],
                "final_period_s": result["final_period_s"],
                "phase_reference_policy": "refreshed from final adaptive accepted orbit stage values and period*g(stage)",
                "exact_unknowns_sha256": array_digest(exact_unknowns),
                "fixture_unknowns_sha256": array_digest(fixture_unknowns),
                "boundaries_sha256": array_digest(boundaries),
                "phase_values_sha256": array_digest(phase_values),
                "phase_derivatives_sha256": array_digest(phase_derivatives),
                "solve_seed_perturbation": {
                    "version": PERTURBATION_VERSION,
                    "definition": "unknowns[k] += 1e-6*sin(k+0.625) for k<last; log_period += 1e-7*sin(last+0.625)",
                },
                "environment": {"T": env.T, "w": env.w, "p": env.p, "F": env.F, "N_a": env.N_a, "dz": env.Δz},
            })
    source_paths = {
        "generator": GENERATOR,
        "adaptive_qualification": ADAPTIVE,
        "adaptive_qualification_vectors": ADAPTIVE_VECTORS,
        "fixed_mesh_qualification": FIXED,
        "fixed_mesh_midpoint_results": MIDPOINT,
        "python_periodic_orbits": ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py",
        "python_adaptive_orbits": ROOT / "src/bergner_spichtinger_2026/adaptive_orbits.py",
        "cpp_assembler": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
        "cpp_nox": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
        "cpp_loca": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
        "cpp_cli": ROOT / "loca/src/midpoint_orbit_cli.cpp",
        "cpp_collocation_coefficients": ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
        "uv_lock": ROOT / "uv.lock",
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "cpp-gauss-adaptive-nonuniform-fixtures",
        "fixture_magic": FIXTURE_MAGIC,
        "formulation_version": "explicit-stage-gauss-fixed-mesh-v1",
        "adaptive_method_version": adaptive["method_version"],
        "controller_version": adaptive["controller_version"],
        "coefficient_artifact_sha256": COLLOCATION_ARTIFACT_SHA256,
        "parity_tolerances": {"residual_relative": 1e-11, "absolute_floor": 1e-13, "directional_relative": 1e-6},
        "runtime_provenance": {"python": platform.python_version(), "numpy": np.__version__},
        "projection_contract": {
            "source": "TASK-067 final adaptive qualification cycles",
            "mesh": "nonuniform final cycle boundaries",
            "phase_reference": "full remesh-refresh reference from exact final orbit stage values and derivatives",
            "unknowns": "versioned small perturbation of exact final accepted adaptive unknowns so C++ corrections exercise NOX/KLU2",
        },
        "source_provenance": {key: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
                              for key, path in source_paths.items()},
        "cases": cases,
        "regeneration_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_adaptive_nonuniform_fixtures.py --check",
    }
    files["manifest.json"] = canonical_json(manifest)
    return files


def generate(check: bool = False) -> None:
    files = build()
    if check:
        for name, body in files.items():
            path = TARGET / name
            if not path.is_file() or path.read_bytes() != body:
                raise SystemExit(f"TASK-068 nonuniform fixture drift: {path.relative_to(ROOT)}")
        extras = set(TARGET.glob("*")) - {TARGET / name for name in files}
        if extras:
            raise SystemExit(f"unexpected TASK-068 nonuniform fixture files: {sorted(extras)}")
        print("verified TASK-068 C++ adaptive nonuniform fixtures")
        return
    TARGET.mkdir(parents=True, exist_ok=True)
    for path in TARGET.glob("*"):
        path.unlink()
    for name, body in files.items():
        (TARGET / name).write_bytes(body)
    print("wrote TASK-068 C++ adaptive nonuniform fixtures")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)


if __name__ == "__main__":
    main()
