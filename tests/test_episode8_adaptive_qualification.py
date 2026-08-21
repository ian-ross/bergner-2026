from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import DEFECT_ACCEPTANCE_TOLERANCE, PERIOD_ORBIT_CONVERGENCE_TOLERANCE, sha256_file

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/adaptive_qualification_results.json"
VECTORS = EPISODE / "outputs/adaptive_qualification_vectors.npz"
SCRIPT = EPISODE / "scripts"


def _array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype="<f8").tobytes()).hexdigest()


def test_adaptive_qualification_runs_all_four_n32_points_and_records_terminal_evidence():
    data = json.loads(RESULTS.read_text())
    assert data["schema_version"] == "episode008-adaptive-qualification-v1"
    assert data["method_version"] == "external-gauss3-hr-adaptive-v1"
    assert data["qualification_points"] == [
        "canonical-g3-n32",
        "guard-rho-0-g3-n32",
        "guard-rho-minus-0.15-g3-n32",
        "guard-rho-plus-0.15-g3-n32",
    ]
    assert data["summary"]["point_count"] == 4
    assert data["summary"]["all_converged"]
    assert data["summary"]["resolution_unresolved_count"] == 0
    assert data["summary"]["broader_ivp_based_evidence"] == "not_evaluated_through_TASK_068"
    assert data["summary"]["floquet_dependent_evidence"] == "not_evaluated_through_TASK_068"

    for result in data["results"]:
        assert result["start_interval_count"] == 32
        assert result["terminal_status"] == "converged"
        assert result["terminal_action"] == "stop_converged"
        assert result["defect_pass"]
        assert result["period_orbit_convergence_pass"]
        assert result["final_defect_maximum"] < DEFECT_ACCEPTANCE_TOLERANCE
        assert result["remesh_correction_count"] <= data["cycle_budget"]
        assert len(result["cycles"]) == result["cycle_count"]
        assert len(result["remesh_events"]) == result["remesh_correction_count"]
        assert result["cycles"][0]["interval_count"] == 32
        final_cycle = result["cycles"][-1]
        assert final_cycle["decision"]["action"] == "stop_converged"
        assert final_cycle["period_relative_change"] < PERIOD_ORBIT_CONVERGENCE_TOLERANCE
        assert final_cycle["weighted_orbit_change"] < PERIOD_ORBIT_CONVERGENCE_TOLERANCE
        assert all("remesh" in cycle["phase_refresh_triggers"] or cycle["cycle_index"] == 0 for cycle in result["cycles"])
        assert all(event["correction_accepted"] for event in result["remesh_events"])
        assert all(event["phase_refresh"] == "full_remesh_refresh" for event in result["remesh_events"])


def test_adaptive_qualification_vectors_checksums_and_cycle_arrays_are_complete():
    data = json.loads(RESULTS.read_text())
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert set(arrays.files) == set(data["vector_artifact"]["arrays"])
        for key, spec in data["vector_artifact"]["arrays"].items():
            assert list(arrays[key].shape) == spec["shape"]
            assert _array_hash(arrays[key]) == spec["sha256"]
        for result in data["results"]:
            for cycle in result["cycles"]:
                prefix = cycle["array_prefix"]
                n = cycle["interval_count"]
                assert arrays[prefix + "__boundaries"].shape == (n + 1,)
                assert arrays[prefix + "__unknowns"].shape == (3 * n * (3 + 1) + 1,)
                for suffix in (
                    "__defect_maxima",
                    "__grid_disagreement",
                    "__endpoint_left",
                    "__endpoint_right",
                    "__derivative_jumps",
                    "__probe_admitted",
                ):
                    assert arrays[prefix + suffix].shape == (n,)
                assert cycle["defect"]["combined_element_maxima_sha256"] == _array_hash(arrays[prefix + "__defect_maxima"])
            for event in result["remesh_events"]:
                prefix = event["array_prefix"]
                assert arrays[prefix + "__split_boundaries"].shape == (event["split_interval_count"] + 1,)
                assert arrays[prefix + "__movement_boundaries"].shape == (event["new_interval_count"] + 1,)
                assert arrays[prefix + "__transferred_unknowns"].shape == arrays[prefix + "__corrected_unknowns"].shape
                assert arrays[prefix + "__monitor_values"].ndim == 1
                assert arrays[prefix + "__monitor_targets"].shape == (event["split_interval_count"] + 1,)


def test_adaptive_qualification_records_aliasing_and_radau_trigger_statuses_without_hiding_failures():
    data = json.loads(RESULTS.read_text())
    assert any(result["defect_aliasing_persistent"] for result in data["results"])
    for result in data["results"]:
        for event in result["aliasing_events"]:
            assert abs(event["current_bin"] - event["previous_bin"]) <= 1 or {event["current_bin"], event["previous_bin"]} == {0, 127}
        for cycle in result["cycles"]:
            triggers = cycle["active_radau_triggers"]
            assert set(triggers) == {
                "defect_below_1e-4_but_convergence_failed",
                "period_or_defect_stagnation_before_mesh_cap",
                "polynomial_ringing",
                "nonphysical_value",
                "broader_ivp_based",
                "floquet_dependent",
            }
            assert triggers["polynomial_ringing"] == "not_evaluated"
            assert triggers["broader_ivp_based"] == "not_evaluated_through_TASK_068"
            assert triggers["floquet_dependent"] == "not_evaluated_through_TASK_068"
            assert cycle["nonphysical_interior_check_passed"] is True


def test_adaptive_qualification_source_hashes_and_generator_check():
    data = json.loads(RESULTS.read_text())
    for item in data["source_provenance"].values():
        assert sha256_file(ROOT / item["path"]) == item["sha256"]
    sys.path.insert(0, str(SCRIPT))
    try:
        generator = importlib.import_module("generate_adaptive_qualification_results")
    finally:
        sys.path.remove(str(SCRIPT))
    generator.generate(check=True)
