from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np

from bergner_spichtinger_2026 import (
    MONITOR_SUBCELLS_PER_ELEMENT,
    FixedMesh,
    apply_global_beta_r_movement,
    mark_h_refinement,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/adaptive_collocation_fixtures.json"
VECTORS = EPISODE / "outputs/adaptive_collocation_fixtures_vectors.npz"
SCRIPT = EPISODE / "scripts"


def _array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype="<f8").tobytes()).hexdigest()


def test_adaptive_fixture_schema_provenance_and_downstream_not_evaluated_status():
    data = json.loads(RESULTS.read_text())
    assert data["schema_version"] == "episode008-adaptive-collocation-fixtures-v1"
    assert data["method_version"] == "external-gauss3-hr-adaptive-v1"
    assert data["monitor"]["version"] == "composite-r-monitor-v1"
    assert data["marking"]["version"] == "defect-bulk-halfmax-marking-v1"
    assert data["movement"]["version"] == "global-beta-r-movement-v1"
    assert data["restart_retry"]["version"] == "fixed-parameter-remesh-restart-retry-v1"
    assert data["downstream_evidence_status"] == {
        "broader_ivp_radau_evidence": "not_evaluated_through_TASK_068",
        "floquet_dependent_evidence": "not_evaluated_through_TASK_068",
    }
    for item in data["source_provenance"].values():
        assert sha256_file(ROOT / item["path"]) == item["sha256"]


def test_adaptive_fixture_vectors_recompute_monitor_marking_movement_and_checksums():
    data = json.loads(RESULTS.read_text())
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        for key, spec in data["vector_artifact"]["arrays"].items():
            assert list(arrays[key].shape) == spec["shape"]
            assert _array_hash(arrays[key]) == spec["sha256"]
        mesh = FixedMesh(arrays["input_mesh_boundaries"])
        assert arrays["defect_next_gauss_relative"].shape[0] == mesh.interval_count
        assert arrays["defect_staggered_dyadic_relative"].shape == (mesh.interval_count, 4)
        assert arrays["defect_combined_element_maxima"].shape == (mesh.interval_count,)
        assert data["defect"]["combined_element_maxima_sha256"] == _array_hash(arrays["defect_combined_element_maxima"])
        assert data["defect"]["grid_disagreement_sha256"] == _array_hash(arrays["defect_grid_disagreement"])
        next_grid = arrays["synthetic_probe_next"]
        dyadic_grid = arrays["synthetic_probe_dyadic"]
        probe_grid = arrays["synthetic_probe_probe16"]
        larger = np.maximum(next_grid, dyadic_grid)
        disagreement = np.divide(np.abs(next_grid - dyadic_grid), larger, out=np.zeros_like(larger), where=larger > 0)
        material = (larger > 1.0e-5) & (disagreement > 0.5)
        combined = larger.copy()
        combined[material] = np.maximum(combined[material], probe_grid[material])
        np.testing.assert_allclose(disagreement, arrays["synthetic_probe_disagreement"])
        np.testing.assert_allclose(combined, arrays["synthetic_probe_combined"])
        assert data["synthetic_probe_escalation"]["materially_disagreeing_elements"] == np.flatnonzero(material).tolist()
        assert data["synthetic_probe_escalation"]["unflagged_probe_element_ignored"]

        assert arrays["monitor_values"].shape == (mesh.interval_count * MONITOR_SUBCELLS_PER_ELEMENT,)
        assert np.all(arrays["monitor_values"] >= 0.20)
        assert np.all(np.diff(arrays["monitor_cumulative_upper"]) > 0.0)
        assert data["monitor"]["value_sha256"] == _array_hash(arrays["monitor_values"])
        assert data["monitor"]["target_boundary_sha256"] == _array_hash(arrays["monitor_target_boundaries"])
        for name in data["monitor"]["density_order"]:
            raw = arrays[f"density_{name}_raw"]
            normalized = arrays[f"density_{name}_normalized"]
            assert raw.shape == normalized.shape == arrays["monitor_values"].shape
            assert np.all(raw >= 0.0)
            assert np.all(normalized >= 0.0)

        marking = mark_h_refinement(arrays["synthetic_defects"], max_interval_count=7)
        assert list(marking.marked_elements) == data["marking"]["marked_elements"]
        assert _array_hash(arrays["split_mesh_boundaries"]) == data["marking"]["split_mesh_sha256"]
        movement = apply_global_beta_r_movement(mesh, arrays["monitor_target_boundaries"])
        assert movement.beta == data["movement"]["beta"]
        np.testing.assert_array_equal(movement.new_boundaries, arrays["movement_boundaries"])
        assert arrays["transferred_unknowns"].shape == arrays["transferred_tangent"].shape
        assert arrays["transferred_phase_values"].shape == arrays["transferred_phase_derivatives"].shape
        assert data["restart_retry"]["executed_tangent_only_rebootstrap"]["unknowns_sha256"] == _array_hash(arrays["restart_corrected_unknowns"])
        assert data["restart_retry"]["executed_tangent_only_rebootstrap"]["tangent_sha256"] == _array_hash(arrays["restart_rebootstrapped_tangent"])


def test_restart_retry_attempt_order_and_generator_check():
    data = json.loads(RESULTS.read_text())
    assert [item["name"] for item in data["restart_retry"]["h_plus_r"]] == [
        "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect"
    ]
    assert [item["name"] for item in data["restart_retry"]["pure_r"]] == [
        "pure_r_transfer_correct", "pure_r_refresh_reference_recorrect", "pure_r_rebootstrap_tangent_recorrect"
    ]
    assert data["restart_retry"]["tangent_only_failure"][0]["name"] == "deterministic_two_point_rebootstrap"
    executed = data["restart_retry"]["executed_tangent_only_rebootstrap"]
    assert executed["accepted"]
    assert executed["attempt_names"] == [
        "h_r_transfer_correct", "deterministic_two_point_rebootstrap", "restart_with_rebootstrapped_tangent"
    ]
    assert executed["final_rejection_reasons"] == []

    sys.path.insert(0, str(SCRIPT))
    try:
        generator = importlib.import_module("generate_adaptive_collocation_fixtures")
    finally:
        sys.path.remove(str(SCRIPT))
    generator.generate(check=True)
