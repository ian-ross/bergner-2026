from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SUMMARY = EPISODE / "outputs/native_adaptive_python_validation.json"
VECTORS = EPISODE / "outputs/native_adaptive_python_validation_vectors.npz"
GENERATOR = EPISODE / "scripts/generate_native_adaptive_python_validation.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> dict:
    return json.loads(SUMMARY.read_text())


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_native_adaptive_python_validation", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_adaptive_python_validation_generator_is_current() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)


def test_stratification_policy_covers_branches_slices_remesh_anchors_and_near_hopf_scope() -> None:
    data = load()
    policy = data["stratification_policy"]
    assert data["schema_version"] == "episode008-native-adaptive-python-validation-v1"
    assert policy["version"] == "task06804-deterministic-stratified-native-point-selection-v1"
    assert policy["unique_accepted_native_points_available"] == 32
    assert policy["selected_point_count"] == data["summary"]["selected_point_count"] == 32
    assert set(policy["selected_by_branch"]) == {
        "fixed225-to-spine",
        "spine-negative-T-hat-to-210",
        "spine-positive-T-hat",
        "slice210-negative-rho",
        "slice210-positive-rho",
    }
    reasons = policy["selected_by_reason"]
    assert reasons["accepted_remesh_boundary_point"] == 1
    assert reasons["branch_first_accepted_point"] == 5
    assert reasons["branch_final_accepted_point"] == 5
    assert reasons["branch_interior_midpoint"] == 5
    assert reasons["spine_target_context"] > 0
    assert reasons["slice_target_context"] > 0
    assert reasons["anchor_target_context"] > 0
    assert policy["near_hopf"] == {
        "approach_point_count": 0,
        "selected_point_count": 0,
        "status": "not_reached_in_provisional_run",
    }


def test_validation_contract_tolerances_and_truthfulness_boundaries() -> None:
    data = load()
    assert data["summary"]["all_selected_points_pass"] is True
    assert data["summary"]["failed_count"] == 0
    assert data["summary"]["maximum_period_relative_error"] <= data["tolerances"]["period_relative"]
    assert data["summary"]["maximum_weighted_orbit_distance"] <= data["tolerances"]["weighted_orbit"]
    assert data["truthfulness_policy"] == {
        "failed_targets_remain_failed": True,
        "native_vectors_used_as_python_seeds": False,
        "native_vectors_used_for_fingerprints_only": True,
        "post_remesh_restart_not_rebranded_as_python_validation": True,
        "production_cpp_adaptive_backend_executed": False,
        "python_validation_is_not_native_adaptive_execution": True,
    }
    for record in data["selected_validations"]:
        assert record["validation_status"] == "passed"
        assert record["failure_reasons"] == []
        assert all(record["gates"].values())
        assert record["physical_coordinate_contract"]["passed"] is True
        assert record["physical_coordinate_contract"]["absolute_error"] == 0.0
        assert record["seed_contract"]["native_vector_seeded"] is False
        assert record["seed_contract"]["native_vector_access"] == "fingerprint_only_not_solver_seed"
        assert record["mesh_comparison"]["identical_mesh_for_same_coordinate_correction"] is True
        assert record["comparison"]["period_relative_error"] <= data["tolerances"]["period_relative"]
        assert record["comparison"]["weighted_orbit_distance"] <= data["tolerances"]["weighted_orbit"]
    nonvalidated = data["accepted_points_without_independent_python_validation"]
    assert len(nonvalidated) == 1
    restart = nonvalidated[0]
    assert restart["point_id"] == "spine-210K-post-remesh-restart"
    assert restart["validation_status"] == "not_independent_python_corrected_in_this_artifact"
    assert "not relabeled as Python validation" in restart["reason"]
    assert all(restart["restart_gates"].values())


def test_vector_artifact_hashes_and_source_fingerprints_match() -> None:
    data = load()
    assert sha(VECTORS) == data["vector_artifact"]["sha256"]
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert len(arrays.files) == data["vector_artifact"]["array_count"]
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        for name in arrays.files:
            value = np.ascontiguousarray(np.asarray(arrays[name], dtype="<f8"))
            spec = data["vector_artifact"]["arrays"][name]
            assert list(value.shape) == spec["shape"]
            assert hashlib.sha256(value.tobytes(order="C")).hexdigest() == spec["sha256"]
    array_hashes = {spec["sha256"] for spec in data["vector_artifact"]["arrays"].values()}
    for record in data["selected_validations"]:
        assert record["source_fingerprints"]["native_vector_sha256"] in array_hashes
    for source in data["provenance"].values():
        if isinstance(source, dict) and "path" in source:
            assert sha(ROOT / source["path"]) == source["sha256"]


def test_tolerance_failure_reporting_and_identical_coordinate_guard() -> None:
    module = load_generator_module()
    strict_summary_bytes, _ = module.build(period_relative_tolerance=1e-16, weighted_orbit_tolerance=1e-16)
    strict = json.loads(strict_summary_bytes)
    assert strict["summary"]["all_selected_points_pass"] is False
    assert strict["summary"]["failed_count"] > 0
    assert strict["summary"]["all_validation_failures_report_reasons"] is True
    assert any(
        {"period_relative_error", "weighted_orbit_distance"}.intersection(record["failure_reasons"])
        for record in strict["selected_validations"]
    )
    gate = module.identical_coordinate_gate({
        "active_coordinate_name": "rho",
        "active_coordinate": 0.0,
        "python_correction_target_coordinate": 1e-6,
        "python_correction_seed_coordinate": 0.0,
    })
    assert gate["passed"] is False
    assert gate["absolute_error"] == 1e-6


def test_no_python_only_evidence_is_rebranded_as_native_adaptive_execution() -> None:
    data = load()
    feedback = data["manifest_feedback"]
    assert feedback["parent_review_target"] == "TASK-069"
    assert "must not change failed provisional targets" in feedback["statement"]
    assert data["validation_contract"]["source_native_correction_backend"] == "native LOCA/NOX/KLU2 accepted vector recorder"
    assert data["validation_contract"]["python_correction_backend"].startswith("independent Python")
    assert all(
        "Python" in record["python_correction"]["backend"]
        and record["seed_contract"]["native_vector_seeded"] is False
        for record in data["selected_validations"]
    )
