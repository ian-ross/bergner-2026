from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/native_adaptive_one_branch_segment.json"
VECTORS = EPISODE / "outputs/native_adaptive_one_branch_segment_vectors.npz"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_one_branch_segment.py"
TRILINOS = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


@lru_cache(maxsize=1)
def executable() -> Path:
    if not TRILINOS.is_file() or shutil.which("cmake") is None:
        pytest.skip("Trilinos/CMake unavailable")
    build = ROOT / ".pytest_cache/task068-native-adaptive-restart-smoke-build"
    subprocess.run([
        "cmake", "-S", "loca", "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", f"-DTrilinos_DIR={TRILINOS.parent}",
    ], cwd=ROOT, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=ROOT, check=True)
    return build / "bs2026_midpoint_orbit"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(RESULTS.read_text())


def test_native_adaptive_one_branch_generator_is_current() -> None:
    env = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable())}
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, env=env, check=True)


def test_one_branch_scope_segment_and_accepted_remesh_boundary() -> None:
    data = load()
    assert data["schema_version"] == "episode008-native-adaptive-one-branch-segment-v1"
    assert data["truthfulness_policy"] == {
        "native_one_branch_fixed_mesh_loca_segment_executed": True,
        "native_one_branch_remesh_restart_executed": True,
        "native_full_spine_and_slices_adaptive_run_executed": False,
        "python_adaptive_evidence_not_rebranded_as_native_full_run": True,
    }
    assert data["selected_branch_id"] == "spine-negative-T-hat-to-210"
    segment = data["native_fixed_mesh_segment"]
    assert segment["continuation_contract"] == {
        "base_dimension": 385,
        "base_has_arclength": False,
        "extended_dimension": 386,
        "fixed_mesh_segment_owner": "LOCA::Stepper",
        "version": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
    }
    assert segment["event_partition"]["accepted_point_count"] == len(segment["points"])
    assert segment["event_partition"]["regular_rejected_count"] == 0
    boundary = segment["remesh_boundary"]
    final_event = segment["events"][-1]
    final_point = segment["points"][-1]
    assert final_event["status"] == "accepted"
    assert final_event["save_role"] == "final"
    assert boundary["event_callback_index"] == final_event["callback_index"]
    assert boundary["point_index"] == final_point["point_index"]
    assert boundary["checkpoint_vector_key"] == final_point["vector_key"]
    assert all(not event["remesh_boundary_candidate"] for event in segment["events"][:-1])


def test_controller_transfer_restart_gates_vectors_and_sources() -> None:
    data = load()
    assert sha(VECTORS) == data["vector_artifact"]["sha256"]
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert len(arrays.files) == data["vector_artifact"]["array_count"]
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        assert data["native_fixed_mesh_segment"]["remesh_boundary"]["checkpoint_vector_key"] in arrays.files
        assert data["restart"]["solution_vector_key"] in arrays.files
        for key in data["transfer"]["vector_keys"].values():
            assert key in arrays.files
        for name in arrays.files:
            value = np.ascontiguousarray(np.asarray(arrays[name], dtype="<f8"))
            spec = data["vector_artifact"]["arrays"][name]
            assert list(value.shape) == spec["shape"]
            assert hashlib.sha256(value.tobytes(order="C")).hexdigest() == spec["sha256"]
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]

    controller = data["adaptive_controller"]
    assert controller["contract"] == [
        "external-gauss3-hr-adaptive-v1",
        "two-grid-relative-defect-v1",
        "composite-r-monitor-v1",
        "defect-bulk-halfmax-marking-v1",
        "global-beta-r-movement-v1",
        "adaptive-cycle-controller-v1",
        "fixed-parameter-remesh-restart-retry-v1",
    ]
    assert controller["cycle_decision_actual"][:2] == ["ordinary_h_r", "continue"]
    assert controller["h_marking"]["marked_count"] > 0
    assert controller["restart_retry_order_h_plus_r"] == [
        "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect",
    ]

    transfer = data["transfer"]
    assert transfer["old_interval_count"] == 75
    assert transfer["new_interval_count"] > transfer["old_interval_count"]
    assert transfer["transferred_solution_recorded"]
    assert transfer["refreshed_phase_reference_recorded"]
    assert transfer["transferred_tangent_recorded"]
    assert transfer["phase_energy"] > 0.0

    restart = data["restart"]
    assert restart["rebuild"]["new_unknown_size"] > restart["rebuild"]["old_unknown_size"]
    assert restart["graph"]["rebuilt"] is True
    assert restart["graph"]["retained_reuse"] is True
    assert restart["correction"]["status"] == "accepted"
    assert restart["correction"]["nox_status"] == "converged"
    assert restart["linear"]["backend"] == "KLU2"
    assert restart["linear"]["solve_complete"] is True
    assert restart["final_diagnostics"]["stage_max"] <= 1e-9
    assert restart["final_diagnostics"]["update_max"] <= 1e-9
    assert restart["final_diagnostics"]["phase_abs"] <= 1e-10
    assert all(restart["gates"].values())
    assert all(data["gates"].values())


def test_one_branch_python_and_restart_smoke_parity() -> None:
    data = load()
    native = data["parity"]["native_fixed_mesh_vs_independent_python"]
    assert native["selected_branch_reached_exact_target"] is True
    assert native["maximum_selected_branch_period_relative_error"] <= native["period_relative_tolerance"]
    assert native["maximum_selected_branch_weighted_orbit_error"] <= native["weighted_orbit_tolerance"]
    smoke = data["parity"]["restart_vs_existing_restart_smoke"]
    assert smoke["case_id"] == data["selected_adaptive_case_id"]
    assert smoke["restart_smoke_all_gates_passed"] is True
    assert smoke["matching_restart_solution_sha256"] == data["restart"]["solution_sha256"]
    assert data["resumable_state"]["full_run_terminal_status"] == "not_claimed"
