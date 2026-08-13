#!/usr/bin/env python3
"""Project TASK-064 Gauss vectors into deterministic C++ TASK-065 text fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from bergner_spichtinger_2026 import COLLOCATION_ARTIFACT_SHA256, sha256_file

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
RESULTS = OUTPUT / "higher_order_fixed_mesh_qualification.json"
VECTORS = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
MIDPOINT = OUTPUT / "fixed_mesh_midpoint_results.json"
PARITY = OUTPUT / "higher_order_parity_fixtures"
PARITY_MANIFEST = PARITY / "manifest.json"
TARGET = OUTPUT / "cpp_higher_order_fixtures"
GENERATOR = Path(__file__).resolve()
CPP_ASSEMBLER = ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_orbit.hpp"
CPP_NOX = ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp"
CPP_CLI = ROOT / "loca/src/midpoint_orbit_cli.cpp"
LOCK = ROOT / "uv.lock"
SCHEMA_VERSION = "episode008-cpp-gauss-fixtures-v1"
FIXTURE_MAGIC = "BS2026_GAUSS_FIXTURE_V1"
PERTURBATION_VERSION = "sinusoidal-packed-vector-v1"

ACCEPTED_CASES = (
    "canonical-g2-n64",
    "canonical-g3-n32",
    "canonical-g3-n64",
    "guard-rho-0-g3-n32",
    "guard-rho-minus-0.15-g3-n32",
    "guard-rho-plus-0.15-g3-n32",
)
REJECTED_CASES = ("canonical-g3-n16",)
NONSOLUTION_SOURCES = {
    "canonical-g2-n64-nonsolution": "g2-n64-nonsolution.json",
    "canonical-g3-n64-nonsolution": "g3-n64-nonsolution.json",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def rows(values: np.ndarray) -> list[str]:
    array = np.asarray(values, dtype=float)
    if array.ndim == 1:
        return [" ".join(format(float(value), ".17g") for value in array)]
    return [" ".join(format(float(value), ".17g") for value in row) for row in array.reshape(-1, array.shape[-1])]


def fixture_bytes(record: dict[str, Any], arrays: dict[str, np.ndarray], scaling: np.ndarray,
                  unknowns: np.ndarray, status: str, *, array_case_id: str | None = None) -> bytes:
    stage_count = int(record["stage_count"])
    interval_count = int(record["interval_count"])
    temperature = float(record.get("temperature_K", 225.0))
    w = float(record.get("w_m_s", 0.1))
    array_case_id = array_case_id or record["case_id"]
    lines = [
        f"{FIXTURE_MAGIC} {record['case_id']} {interval_count} {stage_count} {record['formal_order']} {status} {COLLOCATION_ARTIFACT_SHA256}",
        f"30000 {format(temperature, '.17g')} {format(w, '.17g')} 1 10000000000 100",
        f"{format(np.log(0.01), '.17g')} {format(np.log(0.25), '.17g')} 0.037",
        " ".join(format(float(value), ".17g") for value in scaling),
        *rows(arrays[array_case_id + "__boundaries"]),
        *rows(arrays[array_case_id + "__phase_values"]),
        *rows(arrays[array_case_id + "__phase_derivatives"]),
        *rows(unknowns),
    ]
    return ("\n".join(lines) + "\n").encode()


def build() -> dict[str, bytes]:
    qualification = json.loads(RESULTS.read_text())
    records = {item["case_id"]: item for item in qualification["results"]}
    scaling = np.asarray(json.loads(MIDPOINT.read_text())["state_scaling"], dtype=float)
    files: dict[str, bytes] = {}
    cases: list[dict[str, Any]] = []
    with np.load(VECTORS, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
        for case_id in ACCEPTED_CASES + REJECTED_CASES:
            record = records[case_id]
            status = "accepted" if record["nonlinear_accepted"] else "rejected"
            unknowns = arrays[case_id + "__unknowns"].copy()
            # Force at least one real Newton/KLU2 solve; an exact upstream
            # solution can converge at iteration zero with no linear diagnostics.
            if status == "accepted":
                direction = np.sin(np.arange(unknowns.size, dtype=float) + 0.375)
                unknowns[:-1] += 1.0e-4 * direction[:-1]
                unknowns[-1] += 1.0e-5 * direction[-1]
            body = fixture_bytes(record, arrays, scaling, unknowns, status)
            name = case_id + ".txt"
            files[name] = body
            cases.append({
                "case_id": case_id, "path": name, "sha256": digest(body),
                "stage_count": record["stage_count"], "formal_order": record["formal_order"],
                "interval_count": record["interval_count"], "upstream_status": status,
                "upstream_rejection_reasons": record["rejection_reasons"],
                "period_s": record["period_s"], "unknown_size": unknowns.size,
                "unknown_sha256": digest(np.ascontiguousarray(unknowns, dtype="<f8").tobytes()),
                "python_solution_key": case_id + "__unknowns",
                "accepted_semantics": "nonlinear_accepted",
                "scientifically_qualified": bool(record["qualification"]["qualified"]),
                "phase_reference_id": record["seed_lineage"]["reference_id"],
                "seed_lineage": record["seed_lineage"],
                "solve_seed_perturbation": None if status != "accepted" else {
                    "version": "small-sinusoidal-correction-seed-v1",
                    "definition": "unknowns[k] += 1e-4*sin(k+0.375) for k<last; log_period += 1e-5*sin(last+0.375)",
                },
            })
        for projected_id, source_name in NONSOLUTION_SOURCES.items():
            source_path = PARITY / source_name
            source = json.loads(source_path.read_text())
            source_base = "canonical-g2-n64" if source["rule"]["stage_count"] == 2 else "canonical-g3-n64"
            record = records[source_base]
            unknowns = np.asarray(source["arrays"]["unknowns"], dtype=float)
            projected_arrays = {
                projected_id + "__boundaries": np.asarray(source["arrays"]["mesh_boundaries"], dtype=float),
                projected_id + "__phase_values": np.asarray(source["arrays"]["phase_reference_values"], dtype=float),
                projected_id + "__phase_derivatives": np.asarray(source["arrays"]["phase_reference_derivatives"], dtype=float),
            }
            body = fixture_bytes({**record, "case_id": projected_id}, projected_arrays,
                                 np.asarray(source["state_scaling"], dtype=float), unknowns, "nonsolution")
            name = projected_id + ".txt"
            files[name] = body
            cases.append({
                "case_id": projected_id, "path": name, "sha256": digest(body),
                "stage_count": record["stage_count"], "formal_order": record["formal_order"],
                "interval_count": record["interval_count"], "upstream_status": "nonsolution",
                "upstream_rejection_reasons": [], "period_s": float(np.exp(unknowns[-1])),
                "unknown_size": unknowns.size,
                "unknown_sha256": digest(np.ascontiguousarray(unknowns, dtype="<f8").tobytes()),
                "phase_reference_id": record["seed_lineage"]["reference_id"],
                "perturbation_version": source["perturbation"]["version"],
                "projection_source": {
                    "path": source_path.relative_to(ROOT).as_posix(),
                    "sha256": sha256_file(source_path),
                    "source_case_id": source["case_id"],
                    "unknown_sha256": source["array_schema"]["unknowns"]["sha256"],
                    "projection": "exact_unknowns_mesh_and_phase_reference",
                },
            })
    source_paths = {
        "generator": GENERATOR, "qualification": RESULTS, "qualification_vectors": VECTORS,
        "fixed_mesh_midpoint_results": MIDPOINT,
        "language_neutral_parity_manifest": PARITY_MANIFEST,
        "cpp_assembler": CPP_ASSEMBLER, "cpp_nox": CPP_NOX, "cpp_cli": CPP_CLI,
        "cpp_model": ROOT / "loca/include/bergner_spichtinger_2026_loca/model.hpp",
        "cpp_loca": ROOT / "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
        "cpp_collocation_coefficients": ROOT / "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
        "python_periodic_orbits": ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py",
        "python_collocation_coefficients": ROOT / "src/bergner_spichtinger_2026/collocation_coefficients.py",
        "uv_lock": LOCK,
    }
    for source_name in ("g2-n64-converged.json", "g2-n64-nonsolution.json",
                        "g3-n64-converged.json", "g3-n64-nonsolution.json"):
        source_paths["language_neutral_" + source_name.removesuffix(".json").replace("-", "_")] = PARITY / source_name
    sources = {key: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
               for key, path in source_paths.items()}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "cpp-gauss-fixed-parameter-fixtures",
        "fixture_magic": FIXTURE_MAGIC,
        "formulation_version": "explicit-stage-gauss-fixed-mesh-v1",
        "solver_version": "thyra-nox-amesos2-klu2-v1",
        "coefficient_artifact_sha256": COLLOCATION_ARTIFACT_SHA256,
        "parity_tolerances": {"residual_relative": 1e-11, "absolute_floor": 1e-13,
                              "directional_relative": 1e-6, "corrected_fixed_mesh": 1e-8},
        "runtime_provenance": {"python": platform.python_version(), "numpy": np.__version__,
                               "scipy": scipy.__version__},
        "projection_contract": {
            "upstream_schema_version": json.loads(PARITY_MANIFEST.read_text())["schema_version"],
            "upstream_manifest_sha256": sha256_file(PARITY_MANIFEST),
            "accepted_correction_seeds": "qualification solution plus versioned small sinusoidal perturbation",
            "nonsolutions": "exact unknowns, mesh, and phase reference from TASK-064 language-neutral cases",
        },
        "source_provenance": sources,
        "bundle_membership": {
            "required_accepted_corrections": list(ACCEPTED_CASES),
            "explicit_upstream_rejections": list(REJECTED_CASES),
            "representative_nonsolutions": list(NONSOLUTION_SOURCES),
        },
        "cases": cases,
        "regeneration_command": "uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_cpp_higher_order_fixtures.py --check",
    }
    files["manifest.json"] = canonical_json(manifest)
    return files


def generate(check: bool = False) -> None:
    files = build()
    if check:
        for name, body in files.items():
            path = TARGET / name
            if not path.is_file() or path.read_bytes() != body:
                raise SystemExit(f"TASK-065 fixture drift: {path.relative_to(ROOT)}")
        extras = set(TARGET.glob("*")) - {TARGET / name for name in files}
        if extras:
            raise SystemExit(f"unexpected TASK-065 fixture files: {sorted(extras)}")
        print("verified TASK-065 C++ Gauss fixtures")
        return
    TARGET.mkdir(parents=True, exist_ok=True)
    for path in TARGET.glob("*"):
        path.unlink()
    for name, body in files.items():
        (TARGET / name).write_bytes(body)
    print("wrote TASK-065 C++ Gauss fixtures")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)


if __name__ == "__main__":
    main()
