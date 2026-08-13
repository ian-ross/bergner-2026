from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "episodes/008-figure5-periodic-orbit-continuation/outputs/tpetra_midpoint_fixtures"
TRILINOS = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


@lru_cache(maxsize=1)
def executable() -> Path:
    if not TRILINOS.is_file() or not shutil.which("cmake"):
        pytest.skip("Trilinos/CMake unavailable")
    build = REPO / ".pytest_cache/task061-loca-build"
    subprocess.run(["cmake", "-S", "loca", "-B", str(build), f"-DTrilinos_DIR={TRILINOS.parent}"], cwd=REPO, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=REPO, check=True)
    return build / "bs2026_midpoint_orbit"


def run(command: str) -> list[list[str]]:
    completed = subprocess.run(
        [str(executable()), command, str(FIXTURES / "n64_converged.txt")],
        cwd=REPO, text=True, capture_output=True, check=True,
    )
    return [line.split() for line in completed.stdout.splitlines() if line.strip()]


def test_curated_native_source_provenance_hashes_current_paths():
    data = json.loads(
        (REPO / "episodes/008-figure5-periodic-orbit-continuation/outputs/native_loca_midpoint_results.json").read_text()
    )
    for record in data["source_provenance"].values():
        if isinstance(record, dict) and "path" in record and "sha256" in record:
            path = REPO / record["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]


def test_native_loca_base_contract_has_one_parameter_and_no_arclength_row():
    rows = run("loca-contract")
    contract = next(row for row in rows if row[0] == "loca_contract")
    assert contract[1] == "native-loca-midpoint-pseudo-arclength-v2"
    assert tuple(map(int, contract[2:])) == (1, 1, 385, 386, 384, 384)
    method = next(row for row in rows if row[0] == "loca_method")
    assert method[1:7] == ["Arc_Length", "native_stepper", "true", "base_has_arclength", "false", "metric"]


def test_native_loca_uses_binding_metric_and_runs_adaptive_stepper():
    rows = run("loca-smoke")
    metric = next(row for row in rows if row[0] == "metric")
    weights = np.asarray(metric[2:], dtype=float)
    assert int(metric[1]) == 386 == weights.size
    assert weights[-2] == weights[-1] == 1.0
    with np.load(REPO / "episodes/008-figure5-periodic-orbit-continuation/outputs/fixed_mesh_continuation_vectors.npz",
                 allow_pickle=False) as vectors:
        np.testing.assert_allclose(weights, vectors["metric_diagonal_initial"], rtol=0.0, atol=2e-18)
    # Exercise the actual WeightedThyraGroup override on deterministic state directions.
    weighted_dot = next(row for row in rows if row[0] == "group_weighted_dot")
    assert float(weighted_dot[1]) == pytest.approx(float(weighted_dot[2]), rel=2e-15, abs=2e-15)
    assert np.isfinite(float(weighted_dot[1]))
    bootstrap = next(row for row in rows if row[0] == "bootstrap")
    assert int(bootstrap[1]) >= 1
    assert float(bootstrap[3]) > 0.0
    assert float(bootstrap[4]) <= 0.25
    result = next(row for row in rows if row[0] == "loca_result")
    accepted, rejected, attempted, base, extended, saved = map(int, result[1:7])
    assert result[7:] == ["Secant", "Adaptive"]
    # Regression for the former second-step NaN: at least two genuine native
    # attempts must finish before the exact-bound landing point.
    assert accepted >= 3 and attempted >= 2 and rejected >= 0
    assert (base, extended) == (385, 386)
    points = [row for row in rows if row[0] == "loca_point"]
    assert saved == len(points) >= 4
    coordinates = np.asarray([float(row[1]) for row in points])
    assert np.all(np.isfinite(coordinates))
    assert np.all(np.diff(coordinates) > 0.0)
    assert coordinates[-1] == pytest.approx(coordinates[0] + 0.06, abs=1e-14)
    assert all(np.isfinite(float(row[2])) and float(row[2]) > 0.0 for row in points)
    forced_result = next(row for row in rows if row[0] == "forced_rejection_result")
    forced_events = [row for row in rows if row[0] == "forced_rejection_event"]
    assert int(forced_result[2]) == 1
    rejected = [row for row in forced_events if row[2] == "rejected"]
    assert len(rejected) == 1
    rejected_index = forced_events.index(rejected[0])
    retry = forced_events[rejected_index + 1]
    assert all(np.isfinite(float(value)) for value in rejected[0][3:7])
    assert abs(float(rejected[0][6])) < abs(float(rejected[0][5]))
    assert float(retry[5]) == pytest.approx(float(rejected[0][6]))
    assert int(forced_result[5]) == int(forced_result[6]) + int(forced_result[7])
    assert int(forced_result[7]) == 1
    assert sum(row[2] == "accepted" and row[7] == "regular" for row in forced_events) == int(forced_result[6])
    assert forced_events[0][7] == "initial" and forced_events[-1][7] == "final"


def test_native_loca_replays_all_branches_with_restart_lineage():
    rows = run("loca-branches")
    required = [
        "fixed225-to-spine", "spine-positive-T-hat", "spine-negative-T-hat-to-210",
        "slice210-negative-rho", "slice210-positive-rho",
    ]
    beginnings = [row for row in rows if row[0] == "branch_begin"]
    assert [row[1] for row in beginnings] == required
    expected_refs = {
        "fixed225-to-spine": "phase-ref-episode007-seed",
        "spine-positive-T-hat": "phase-ref-spine-225",
        "spine-negative-T-hat-to-210": "phase-ref-spine-225",
        "slice210-negative-rho": "phase-ref-slice-210",
        "slice210-positive-rho": "phase-ref-slice-210",
    }
    for begin in beginnings:
        branch, target = begin[1], float(begin[5])
        points = [row for row in rows if row[0] == "branch_point" and row[1] == branch]
        bootstraps = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == branch]
        end = next(row for row in rows if row[0] == "branch_end" and row[1] == branch)
        assert points and float(points[-1][4]) == target
        assert all(row[3] == expected_refs[branch] for row in points)
        assert bootstraps and bootstraps[-1][5] == "accepted"
        assert end[10] == "true"
        assert int(end[2]) >= 3 and int(end[3]) >= 0
        events = [row for row in rows if row[0] == "branch_event" and row[1] == branch]
        assert len(events) == int(end[5]) + int(end[6]) + int(end[7])
        assert sum(row[3] == "rejected" for row in events) == int(end[9])
        assert events[0][8] == "initial" and events[-1][8] == "final"
        assert sum(row[3] == "accepted" and row[8] == "regular" for row in events) == int(end[8])
        assert all(np.all(np.isfinite(np.asarray(row[4:8], dtype=float))) for row in events)
        assert all(len(row) == 391 for row in points)  # metadata plus 385 native unknowns
    refreshes = [row for row in rows if row[0] == "phase_refresh"]
    assert [row[1:3] for row in refreshes] == [
        ["phase-ref-episode007-seed", "phase-ref-spine-225"],
        ["phase-ref-spine-225", "phase-ref-slice-210"],
    ]
    for row in refreshes:
        assert float(row[6]) == float(row[8])
        assert float(row[7]) == float(row[9])
        assert max(map(float, row[10:13])) < 1e-9
        assert row[13:] == ["KLU2", "true"]
    chronology = [row[0] + ":" + row[1] for row in rows if row[0] in {"branch_begin", "phase_refresh"}]
    assert chronology == [
        "branch_begin:fixed225-to-spine", "phase_refresh:phase-ref-episode007-seed",
        "branch_begin:spine-positive-T-hat", "branch_begin:spine-negative-T-hat-to-210",
        "phase_refresh:phase-ref-spine-225", "branch_begin:slice210-negative-rho",
        "branch_begin:slice210-positive-rho",
    ]


@pytest.mark.parametrize("relative_source", [
    "loca/src/midpoint_orbit_cli.cpp",
    "loca/include/bergner_spichtinger_2026_loca/midpoint_nox.hpp",
    "loca/include/bergner_spichtinger_2026_loca/collocation_coefficients.hpp",
])
def test_native_loca_generator_rejects_stale_source_fingerprint(tmp_path, relative_source):
    import os
    copied = tmp_path / "bs2026_midpoint_orbit"
    copied.write_bytes(executable().read_bytes())
    copied.chmod(0o755)
    source = REPO / relative_source
    original = source.read_text()
    try:
        source.write_text(original + "\n")
        generator = REPO / "episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_midpoint_results.py"
        completed = subprocess.run(["uv", "run", "python", str(generator), "--check"], cwd=REPO,
                                   env={**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(copied)},
                                   text=True, capture_output=True)
        assert completed.returncode != 0
        assert "source fingerprint" in completed.stderr
    finally:
        source.write_text(original)


def test_native_loca_artifacts_cover_all_required_branches_and_regenerate():
    import json
    results = REPO / "episodes/008-figure5-periodic-orbit-continuation/outputs/native_loca_midpoint_results.json"
    generator = REPO / "episodes/008-figure5-periodic-orbit-continuation/scripts/generate_native_loca_midpoint_results.py"
    env = {**__import__("os").environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable())}
    subprocess.run(["uv", "run", "python", str(generator), "--check"], cwd=REPO, env=env, check=True)
    data = json.loads(results.read_text())
    assert data["native_contract"]["native_stepper"] is True
    assert data["native_contract"]["base_has_arclength"] is False
    assert data["artifact_kind"] == "independently_executed_native_loca_midpoint_branches"
    assert {branch["branch_id"] for branch in data["branches"]} == set(data["required_branch_ids"])
    assert all(branch["reached_exact_target"] and branch["used_bootstrap_restart_tangent"] for branch in data["branches"])
    assert data["controlled_phase_reference_refresh_count"] == 2
    event_types = {event["event_type"] for event in data["events"]}
    assert {"native_branch_bootstrap_attempt", "native_loca_step", "native_phase_reference_refresh"} <= event_types
    assert data["parity"]["maximum_all_point_period_relative_error"] <= data["parity"]["period_relative_tolerance"]
    assert data["parity"]["maximum_all_point_weighted_orbit_error"] <= data["parity"]["weighted_orbit_tolerance"]
    assert all(point["python_same_coordinate_period_relative_error"] <= data["parity"]["period_relative_tolerance"]
               and point["python_same_coordinate_weighted_orbit_error"] <= data["parity"]["weighted_orbit_tolerance"]
               for point in data["points"])
    with np.load(REPO / data["vector_artifact"]["path"], allow_pickle=False) as native, \
         np.load(REPO / "episodes/008-figure5-periodic-orbit-continuation/outputs/fixed_mesh_continuation_vectors.npz", allow_pickle=False) as python:
        assert len(native.files) == len(data["points"]) == data["vector_artifact"]["array_count"]
        # Native paths intentionally take different adaptive points; copying the
        # Python fixture wholesale can neither satisfy this key contract nor this value check.
        assert all(name.startswith("native__") for name in native.files)
        native_digests = {__import__("hashlib").sha256(native[name].tobytes()).hexdigest() for name in native.files}
        python_digests = {__import__("hashlib").sha256(python[name].tobytes()).hexdigest()
                          for name in python.files if name.startswith("point__")}
        assert native_digests.isdisjoint(python_digests)
        assert data["vector_artifact"]["digest_disjoint_from_all_frozen_python_points"] is True
    for branch in data["branches"]:
        assert branch["derived_callback_count"] == (branch["derived_initial_save_count"] +
            branch["derived_final_save_count"] + branch["derived_regular_attempt_count"])
        assert branch["derived_regular_attempt_count"] == (branch["derived_regular_accepted_count"] +
            branch["derived_regular_rejected_count"])
        assert branch["derived_initial_save_count"] == branch["derived_final_save_count"] == 1
    refreshes = [event for event in data["events"] if event["event_type"] == "native_phase_reference_refresh"]
    assert all(event["verification"]["accepted"] and event["verification"]["linear_backend"] == "KLU2"
               and event["old_temperature_K"] == event["new_temperature_K"]
               and event["old_log_w"] == event["new_log_w"] for event in refreshes)
    provenance = data["source_provenance"]
    assert {"generator", "cpp_adapter", "cpp_cli", "cpp_assembler", "cpp_model", "cpp_nox_adapter",
            "cpp_collocation_coefficients", "python_continuation", "python_orbit_solver", "seed", "hopf_locus",
            "uv_lock", "fixture", "runtime"} <= provenance.keys()
    assert all(len(record["sha256"]) == 64 for record in provenance.values() if isinstance(record, dict) and "sha256" in record)
    assert all(point["python_correction_seed_point_id"].startswith(("episode007", "fixed225", "spine", "slice"))
               and point["python_correction_function_evaluations"] >= 1 for point in data["points"])
    forced = data["native_contract"]["forced_native_rejection"]
    assert forced["derived_regular_attempt_count"] == (forced["derived_regular_accepted_count"] +
        forced["derived_regular_rejected_count"])
    assert forced["derived_regular_rejected_count"] == forced["raw_failed_step_count"] == 1
    rejected = next(event for event in forced["events"] if event["status"] == "rejected")
    assert 0 < abs(rejected["retry_coordinate_delta"]) < abs(rejected["attempted_coordinate_delta"])
