#!/usr/bin/env python3
"""Execute and freeze TASK-065 C++ Gauss fixed-parameter correction evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from bergner_spichtinger_2026 import FixedMesh, FrozenPhaseReference, GaussCollocationAssembler, gauss_legendre_rule, sha256_file
from bergner_spichtinger_2026.constants import Environment

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
FIXTURES = OUTPUT / "cpp_higher_order_fixtures"
FIXTURE_MANIFEST = FIXTURES / "manifest.json"
QUALIFICATION = OUTPUT / "higher_order_fixed_mesh_qualification.json"
VECTORS = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
MIDPOINT_RESULTS = OUTPUT / "fixed_mesh_midpoint_results.json"
RESULTS = OUTPUT / "cpp_higher_order_correction_results.json"
GENERATOR = Path(__file__).resolve()
EXECUTABLE = Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", ROOT / "loca-build/bs2026_midpoint_orbit"))
SCHEMA_VERSION = "episode008-cpp-gauss-correction-results-v1"

SOURCE_PATHS = (
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
    ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
    ROOT / "loca/src/midpoint_orbit_cli.cpp",
)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def parse_output(stdout: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in stdout.splitlines():
        fields = line.split()
        if fields:
            rows[fields[0]] = fields[1:]
    return rows


def execute(case_path: Path) -> dict[str, list[str]]:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Build C++ executable first or set BS2026_MIDPOINT_EXECUTABLE: {EXECUTABLE}")
    completed = subprocess.run([str(EXECUTABLE), "solve", str(case_path)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    return parse_output(completed.stdout)


def boolean(value: str) -> bool:
    if value not in {"true", "false"}:
        raise RuntimeError(f"invalid boolean output: {value}")
    return value == "true"


def assembler_for(case_id: str, records: dict[str, dict[str, Any]], arrays: Any,
                  scaling: np.ndarray) -> tuple[GaussCollocationAssembler, np.ndarray]:
    record = records[case_id]
    rule = gauss_legendre_rule(int(record["stage_count"]))
    mesh = FixedMesh(arrays[case_id + "__boundaries"])
    reference = FrozenPhaseReference(
        mesh, arrays[case_id + "__phase_values"], arrays[case_id + "__phase_derivatives"],
        scaling, np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
    )
    environment = Environment(
        T=float(record.get("temperature_K", 225.0)), p=30000.0,
        w=float(record.get("w_m_s", 0.1)), F=1.0, N_a=1e10, Δz=100.0,
        include_evaporation=False,
    )
    return GaussCollocationAssembler(mesh, environment, reference, rule), arrays[case_id + "__unknowns"].copy()


def build() -> bytes:
    manifest = json.loads(FIXTURE_MANIFEST.read_text())
    qualification = json.loads(QUALIFICATION.read_text())
    records = {item["case_id"]: item for item in qualification["results"]}
    scaling = np.asarray(json.loads(MIDPOINT_RESULTS.read_text())["state_scaling"], dtype=float)
    cases: list[dict[str, Any]] = []
    emitted_identity: list[str] | None = None
    emitted_fingerprints: list[str] | None = None
    expected_fingerprints = [sha256_file(path) for path in SOURCE_PATHS]

    with np.load(VECTORS, allow_pickle=False) as arrays:
        for fixture_record in manifest["cases"]:
            case_id = fixture_record["case_id"]
            rows = execute(FIXTURES / fixture_record["path"])
            if rows.get("upstream_status") != [fixture_record["upstream_status"]]:
                raise RuntimeError(f"upstream status mismatch for {case_id}")
            if rows.get("source_fingerprint") != expected_fingerprints:
                raise RuntimeError(f"stale C++ executable source fingerprint for {case_id}")
            if emitted_identity is None:
                emitted_identity = rows["build_identity"]
                emitted_fingerprints = rows["source_fingerprint"]
            elif rows["build_identity"] != emitted_identity or rows["source_fingerprint"] != emitted_fingerprints:
                raise RuntimeError("inconsistent executable provenance across correction cases")

            mesh = [int(value) for value in rows["mesh"]]
            layout = [int(value) for value in rows["solve_layout"]]
            graph = rows["solve_graph"]
            accepted = rows["accepted"] == ["true"]
            rejection_reasons = rows["rejection_reasons"][1:]
            item: dict[str, Any] = {
                "case_id": case_id,
                "upstream_status": fixture_record["upstream_status"],
                "rule": {
                    "family": rows["rule"][0], "stage_count": int(rows["rule"][1]),
                    "formal_order": int(rows["rule"][2]), "coefficient_artifact_sha256": rows["rule"][3],
                },
                "mesh": {"interval_count": mesh[0], "stage_count": mesh[1], "boundary_count": mesh[2]},
                "layout": {
                    "domain_dimension": layout[0], "range_dimension": layout[1],
                    "stage_block_dimension": layout[2], "update_block_dimension": layout[3],
                    "phase_block_dimension": layout[4],
                },
                "graph": {"entry_count": int(graph[0]), "retained_reuse": graph[2] == "true"},
                "accepted": accepted,
                "rejection_reasons": rejection_reasons,
                "nox": None,
                "linear": None,
                "residual_diagnostics": None,
                "final_residual_available": rows.get("final_residual_available", ["false"])[0] == "true",
                "corrected_period_s": None,
                "period_relative_difference": None,
                "phase_aligned_weighted_orbit_distance": None,
                "fixture_sha256": fixture_record["sha256"],
            }
            if fixture_record["upstream_status"] == "accepted":
                nox = rows["nox"]
                linear = rows["linear"]
                diagnostics = rows["diagnostics"]
                solution = np.asarray(rows["solution"][1:], dtype=float)
                assembler, python_solution = assembler_for(case_id, records, arrays, scaling)
                period = float(rows["period"][0])
                period_difference = abs(period - float(np.exp(python_solution[-1]))) / float(np.exp(python_solution[-1]))
                orbit_difference = assembler.compare_with_collocation(
                    solution, assembler, python_solution,
                ).distance
                item.update({
                    "nox": {"status": nox[0], "iterations": int(nox[1]), "residual_norm": float(nox[2])},
                    "linear": {
                        "backend": linear[0], "reported": linear[1] == "reported",
                        "symbolic_factorizations": int(linear[2]), "numeric_factorizations": int(linear[3]),
                        "solves": int(linear[4]), "symbolic_complete": boolean(linear[5]),
                        "numeric_complete": boolean(linear[6]), "solve_complete": boolean(linear[7]),
                    },
                    "residual_diagnostics": {
                        "stage_max": float(diagnostics[0]), "stage_rms": float(diagnostics[1]),
                        "update_max": float(diagnostics[2]), "update_rms": float(diagnostics[3]),
                        "phase_abs": float(diagnostics[4]), "phase_energy": float(diagnostics[5]),
                    },
                    "corrected_period_s": period,
                    "period_relative_difference": float(period_difference),
                    "phase_aligned_weighted_orbit_distance": float(orbit_difference),
                })
                if not accepted or not item["final_residual_available"]:
                    raise RuntimeError(f"required correction was not accepted for {case_id}")
                if period_difference > 1e-8 or orbit_difference > 1e-8:
                    raise RuntimeError(f"fixed-mesh correction parity failed for {case_id}")
            cases.append(item)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "cpp-gauss-fixed-parameter-correction-results",
        "fixture_manifest_sha256": sha256_file(FIXTURE_MANIFEST),
        "coefficient_artifact_sha256": manifest["coefficient_artifact_sha256"],
        "parity_tolerance": 1e-8,
        "cases": cases,
        "runtime_provenance": {
            "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "compiler_and_trilinos": emitted_identity,
            "executable_sha256": sha256_file(EXECUTABLE),
            "emitting_executable_source_fingerprints": emitted_fingerprints,
        },
        "source_provenance": {
            "generator": {"path": GENERATOR.relative_to(ROOT).as_posix(), "sha256": sha256_file(GENERATOR)},
            "fixture_manifest": {"path": FIXTURE_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256_file(FIXTURE_MANIFEST)},
            "qualification": {"path": QUALIFICATION.relative_to(ROOT).as_posix(), "sha256": sha256_file(QUALIFICATION)},
            "qualification_vectors": {"path": VECTORS.relative_to(ROOT).as_posix(), "sha256": sha256_file(VECTORS)},
            "fixed_mesh_midpoint_results": {"path": MIDPOINT_RESULTS.relative_to(ROOT).as_posix(), "sha256": sha256_file(MIDPOINT_RESULTS)},
            **{f"compiled_source_{index}": {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
               for index, path in enumerate(SOURCE_PATHS)},
        },
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_correction_results.py --check",
    }
    return canonical(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    body = build()
    if args.check:
        if not RESULTS.is_file() or RESULTS.read_bytes() != body:
            raise SystemExit("TASK-065 C++ correction results are stale")
        print("verified TASK-065 C++ correction results")
    else:
        RESULTS.write_bytes(body)
        print("wrote TASK-065 C++ correction results")


if __name__ == "__main__":
    main()
