#!/usr/bin/env python3
"""Execute deterministic TASK-068 native adaptive-controller/restart smoke evidence.

This is not the full spine-and-slices adaptive LOCA run.  It freezes native C++
component evidence for the remesh/restart boundary on final TASK-067 nonuniform
Gauss fixtures: controller intermediates for every projected fixture and full
transfer/rebuild/fixed-parameter correction restart smoke for representative
fixtures.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import scipy

from bergner_spichtinger_2026 import sha256_file

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
FIXTURES = OUTPUT / "cpp_adaptive_nonuniform_fixtures"
FIXTURE_MANIFEST = FIXTURES / "manifest.json"
RESULTS = OUTPUT / "native_adaptive_restart_smoke.json"
VECTORS = OUTPUT / "native_adaptive_restart_smoke_vectors.npz"
GENERATOR = Path(__file__).resolve()
EXECUTABLE = Path(os.environ.get("BS2026_MIDPOINT_EXECUTABLE", ROOT / "loca-build/bs2026_midpoint_orbit"))
SCHEMA_VERSION = "episode008-native-adaptive-restart-smoke-v1"
VECTOR_ARTIFACT_KIND = "task068-native-adaptive-restart-smoke-vectors"
RESTART_CASE_IDS = {"adaptive-canonical-g3-n32", "adaptive-guard-rho-0-g3-n32"}

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


def array_sha(value: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            for key in sorted(arrays):
                member = io.BytesIO()
                np.lib.format.write_array(member, np.asarray(arrays[key], dtype="<f8"), allow_pickle=False)
                info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, member.getvalue())
        return output.getvalue()


def source_record(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def parse_output(stdout: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in stdout.splitlines():
        fields = line.split()
        if fields:
            rows[fields[0]] = fields[1:]
    return rows


def execute(command: str, fixture_path: Path) -> dict[str, list[str]]:
    if not EXECUTABLE.is_file():
        raise RuntimeError(f"Build C++ executable first or set BS2026_MIDPOINT_EXECUTABLE: {EXECUTABLE}")
    completed = subprocess.run([str(EXECUTABLE), command, str(fixture_path)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    return parse_output(completed.stdout)


def as_bool(value: str) -> bool:
    if value not in {"true", "false"}:
        raise RuntimeError(f"invalid boolean field: {value}")
    return value == "true"


def vector_row(rows: dict[str, list[str]], name: str) -> np.ndarray:
    values = rows[name]
    count = int(values[0])
    data = np.asarray(values[1:], dtype=float)
    if data.shape != (count,):
        raise RuntimeError(f"row {name} declared {count} values but emitted {data.size}")
    return data


def build() -> tuple[bytes, bytes]:
    manifest = json.loads(FIXTURE_MANIFEST.read_text())
    expected_fingerprints = [sha256_file(path) for path in SOURCE_PATHS]
    cases: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    emitted_identity: list[str] | None = None
    emitted_fingerprints: list[str] | None = None

    for fixture_record in manifest["cases"]:
        case_id = fixture_record["case_id"]
        fixture_path = FIXTURES / fixture_record["path"]
        controller = execute("adaptive-controller", fixture_path)
        if controller.get("source_fingerprint") != expected_fingerprints:
            raise RuntimeError(f"stale C++ executable source fingerprint for controller case {case_id}")
        if emitted_identity is None:
            emitted_identity = controller["build_identity"]
            emitted_fingerprints = controller["source_fingerprint"]
        elif controller["build_identity"] != emitted_identity or controller["source_fingerprint"] != emitted_fingerprints:
            raise RuntimeError("inconsistent executable provenance across adaptive smoke cases")

        defect_summary = controller["defect_summary"]
        h_marking = controller["h_marking"]
        r_movement = controller["r_movement"]
        arrays[f"{case_id}__defect_combined"] = vector_row(controller, "defect_combined")
        arrays[f"{case_id}__monitor_target_boundaries"] = vector_row(controller, "monitor_target_boundaries")
        arrays[f"{case_id}__r_movement_boundaries"] = vector_row(controller, "r_movement_boundaries")
        case: dict[str, Any] = {
            "case_id": case_id,
            "fixture_path": fixture_record["path"],
            "fixture_sha256": fixture_record["sha256"],
            "controller": {
                "contract": controller["adaptive_controller_contract"],
                "defect_maximum": float(defect_summary[0]),
                "argmax_phase": float(defect_summary[1]),
                "argmax_bin": int(defect_summary[2]),
                "material_probe_count": int(defect_summary[3]),
                "h_marked_count": int(h_marking[0]),
                "h_growth_limit": int(h_marking[1]),
                "h_new_interval_count": int(h_marking[2]),
                "h_halfmax_threshold": float(h_marking[3]),
                "h_marked_elements": [int(value) for value in h_marking[4:]],
                "r_status": r_movement[0],
                "r_beta": float(r_movement[1]),
                "r_attempt_count": int(r_movement[2]),
                "cycle_decision_actual": None,
                "restart_retry_order_h_plus_r": None,
            },
            "restart": None,
        }
        # Preserve explicit controller text snippets without relying on duplicate-label parsing.
        raw_controller = "\n".join(line for line in subprocess.run(
            [str(EXECUTABLE), "adaptive-controller", str(fixture_path)], cwd=ROOT,
            text=True, capture_output=True, check=True,
        ).stdout.splitlines() if line.startswith(("cycle_decision actual", "restart_plan h+r", "restart_plan pure-r", "restart_plan tangent_only")))
        decision_lines = raw_controller.splitlines()
        case["controller"]["decision_and_retry_lines"] = decision_lines
        for line in decision_lines:
            fields = line.split()
            if fields[:2] == ["cycle_decision", "actual"]:
                case["controller"]["cycle_decision_actual"] = fields[2:]
            if fields[:2] == ["restart_plan", "h+r"]:
                case["controller"]["restart_retry_order_h_plus_r"] = fields[2:]
        if case["controller"]["cycle_decision_actual"] is None or case["controller"]["restart_retry_order_h_plus_r"] is None:
            raise RuntimeError(f"missing controller decision/retry lines for {case_id}")

        if case_id in RESTART_CASE_IDS:
            restart = execute("adaptive-restart", fixture_path)
            if restart.get("source_fingerprint") != expected_fingerprints:
                raise RuntimeError(f"stale C++ executable source fingerprint for restart case {case_id}")
            solution = vector_row(restart, "restart_solution")
            arrays[f"{case_id}__restart_solution"] = solution
            transfer_residual = [float(value) for value in restart["restart_transfer_residual"][:6]]
            final_diagnostics = [float(value) for value in restart["restart_final_diagnostics"][:6]]
            correction = restart["restart_correction"]
            linear = restart["restart_linear"]
            gates = restart["restart_gates"]
            if correction[0] != "accepted" or correction[1] != "converged":
                raise RuntimeError(f"adaptive restart did not converge for {case_id}")
            if gates != ["residual", "true", "phase", "true", "positivity", "true",
                         "finite_change", "true", "linear", "true", "tangent", "true"]:
                raise RuntimeError(f"adaptive restart gates failed for {case_id}: {gates}")
            case["restart"] = {
                "contract": restart["adaptive_restart_contract"],
                "rebuild": {
                    "old_unknown_size": int(restart["restart_rebuild"][0]),
                    "new_unknown_size": int(restart["restart_rebuild"][1]),
                    "old_stage_size": int(restart["restart_rebuild"][2]),
                    "new_stage_size": int(restart["restart_rebuild"][3]),
                    "old_endpoint_size": int(restart["restart_rebuild"][4]),
                    "new_endpoint_size": int(restart["restart_rebuild"][5]),
                    "old_log_period_index": int(restart["restart_rebuild"][6]),
                    "new_log_period_index": int(restart["restart_rebuild"][7]),
                    "old_phase_row": int(restart["restart_rebuild"][8]),
                    "new_phase_row": int(restart["restart_rebuild"][9]),
                    "old_stage_count": int(restart["restart_rebuild"][10]),
                    "new_stage_count": int(restart["restart_rebuild"][11]),
                },
                "graph": {
                    "entry_count": int(restart["restart_graph"][0]),
                    "retained_reuse": as_bool(restart["restart_graph"][2]),
                    "rebuilt": as_bool(restart["restart_graph"][4]),
                },
                "attempts": restart["restart_attempts"][1:],
                "transfer_residual": {
                    "stage_max": transfer_residual[0], "stage_rms": transfer_residual[1],
                    "update_max": transfer_residual[2], "update_rms": transfer_residual[3],
                    "phase_abs": transfer_residual[4], "phase_energy": transfer_residual[5],
                },
                "tangent": {
                    "pre_normalization_norm": float(restart["restart_tangent"][0]),
                    "post_normalization_norm": float(restart["restart_tangent"][1]),
                    "accepted": as_bool(restart["restart_tangent"][2]),
                },
                "correction": {
                    "status": correction[0], "nox_status": correction[1],
                    "iterations": int(correction[2]), "nox_residual_norm": float(correction[3]),
                    "correction_norm": float(correction[4]), "period_s": float(correction[5]),
                },
                "linear": {
                    "backend": linear[0], "reported": linear[1] == "reported",
                    "symbolic_factorizations": int(linear[2]), "numeric_factorizations": int(linear[3]),
                    "solves": int(linear[4]), "symbolic_complete": as_bool(linear[5]),
                    "numeric_complete": as_bool(linear[6]), "solve_complete": as_bool(linear[7]),
                },
                "final_diagnostics": {
                    "stage_max": final_diagnostics[0], "stage_rms": final_diagnostics[1],
                    "update_max": final_diagnostics[2], "update_rms": final_diagnostics[3],
                    "phase_abs": final_diagnostics[4], "phase_energy": final_diagnostics[5],
                },
                "gates": dict(zip(gates[::2], [as_bool(value) for value in gates[1::2]], strict=True)),
                "solution_sha256": array_sha(solution),
            }
        cases.append(case)

    vector_bytes = npz_bytes(arrays)
    vector_manifest = {
        "artifact_kind": VECTOR_ARTIFACT_KIND,
        "array_count": len(arrays),
        "arrays": {
            key: {"shape": list(np.asarray(value).shape), "sha256": array_sha(value)}
            for key, value in arrays.items()
        },
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "task068-native-adaptive-restart-smoke",
        "scope": "component smoke for native adaptive controller/restart seams; not the full spine-and-slices adaptive LOCA run",
        "truthfulness_policy": {
            "native_adaptive_spine_and_slices_executed": False,
            "native_remesh_restart_smoke_executed": True,
            "python_adaptive_evidence_not_rebranded_as_native": True,
        },
        "fixture_manifest_sha256": sha256_file(FIXTURE_MANIFEST),
        "controller_case_count": len(cases),
        "restart_case_count": sum(1 for case in cases if case["restart"] is not None),
        "restart_case_ids": sorted(RESTART_CASE_IDS),
        "cases": cases,
        "vector_artifact": {**vector_manifest, "sha256": hashlib.sha256(vector_bytes).hexdigest()},
        "runtime_provenance": {
            "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "compiler_and_trilinos": emitted_identity,
            "executable_sha256": sha256_file(EXECUTABLE),
            "emitting_executable_source_fingerprints": emitted_fingerprints,
        },
        "source_provenance": {
            "generator": source_record(GENERATOR),
            "fixture_manifest": source_record(FIXTURE_MANIFEST),
            **{f"compiled_source_{index}": source_record(path) for index, path in enumerate(SOURCE_PATHS)},
        },
        "regeneration_command": "BS2026_MIDPOINT_EXECUTABLE=<current-build>/bs2026_midpoint_orbit uv run python episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_adaptive_restart_smoke.py [--check]",
    }
    return canonical(payload), vector_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    body, vector_bytes = build()
    if args.check:
        if not RESULTS.is_file() or RESULTS.read_bytes() != body or not VECTORS.is_file() or VECTORS.read_bytes() != vector_bytes:
            raise SystemExit("native adaptive restart smoke artifacts are stale")
        print("verified native adaptive restart smoke artifacts")
    else:
        RESULTS.write_bytes(body)
        VECTORS.write_bytes(vector_bytes)
        print(f"wrote {RESULTS} and {VECTORS}")


if __name__ == "__main__":
    main()
