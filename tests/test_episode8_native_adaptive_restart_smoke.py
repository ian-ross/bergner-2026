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
RESULTS = EPISODE / "outputs/native_adaptive_restart_smoke.json"
VECTORS = EPISODE / "outputs/native_adaptive_restart_smoke_vectors.npz"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_restart_smoke.py"
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


def test_native_adaptive_restart_smoke_generator_is_current() -> None:
    env = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable())}
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, env=env, check=True)


def test_native_adaptive_restart_smoke_truthful_scope_and_controller_coverage() -> None:
    data = load()
    assert data["schema_version"] == "episode008-native-adaptive-restart-smoke-v1"
    assert data["truthfulness_policy"] == {
        "native_adaptive_spine_and_slices_executed": False,
        "native_remesh_restart_smoke_executed": True,
        "python_adaptive_evidence_not_rebranded_as_native": True,
    }
    assert data["controller_case_count"] == 4
    assert data["restart_case_count"] == 2
    for case in data["cases"]:
        controller = case["controller"]
        assert controller["contract"] == [
            "external-gauss3-hr-adaptive-v1",
            "two-grid-relative-defect-v1",
            "composite-r-monitor-v1",
            "defect-bulk-halfmax-marking-v1",
            "global-beta-r-movement-v1",
            "adaptive-cycle-controller-v1",
            "fixed-parameter-remesh-restart-retry-v1",
        ]
        assert controller["defect_maximum"] > 0.0
        assert controller["h_growth_limit"] > 0
        assert controller["cycle_decision_actual"][:2] in (["ordinary_h_r", "continue"], ["pure_r", "continue"])
        assert controller["restart_retry_order_h_plus_r"] == [
            "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect",
        ]


def test_native_adaptive_restart_smoke_rebuild_gates_vectors_and_sources() -> None:
    data = load()
    assert sha(VECTORS) == data["vector_artifact"]["sha256"]
    for source in data["source_provenance"].values():
        assert sha(ROOT / source["path"]) == source["sha256"]
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert len(arrays.files) == data["vector_artifact"]["array_count"]
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        for name in arrays.files:
            value = np.ascontiguousarray(np.asarray(arrays[name], dtype="<f8"))
            spec = data["vector_artifact"]["arrays"][name]
            assert list(value.shape) == spec["shape"]
            assert hashlib.sha256(value.tobytes(order="C")).hexdigest() == spec["sha256"]
    restart_cases = [case for case in data["cases"] if case["restart"] is not None]
    assert {case["case_id"] for case in restart_cases} == set(data["restart_case_ids"])
    for case in restart_cases:
        restart = case["restart"]
        assert restart["contract"][:4] == [
            "fixed-parameter-remesh-restart-v1", "h+r",
            "collocation-polynomial-transfer-v1", "fixed-parameter-remesh-restart-retry-v1",
        ]
        assert restart["rebuild"]["new_unknown_size"] > restart["rebuild"]["old_unknown_size"]
        assert restart["graph"] == {
            "entry_count": restart["graph"]["entry_count"],
            "retained_reuse": True,
            "rebuilt": True,
        }
        assert restart["attempts"] == [
            "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect",
        ]
        assert restart["transfer_residual"]["stage_max"] > 1e-8
        assert restart["correction"]["status"] == "accepted"
        assert restart["correction"]["nox_status"] == "converged"
        assert restart["linear"]["backend"] == "KLU2"
        assert restart["linear"]["solve_complete"] is True
        assert all(restart["gates"].values())
        assert restart["final_diagnostics"]["stage_max"] <= 1e-9
        assert restart["final_diagnostics"]["update_max"] <= 1e-9
        assert restart["final_diagnostics"]["phase_abs"] <= 1e-10
        assert restart["tangent"]["accepted"] is True
        assert restart["tangent"]["post_normalization_norm"] == 1.0
