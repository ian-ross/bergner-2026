from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
FIXTURES = EPISODE / "outputs/cpp_higher_order_fixtures"
RESULTS = EPISODE / "outputs/native_loca_higher_order_results.json"
VECTORS = EPISODE / "outputs/native_loca_higher_order_vectors.npz"
GENERATOR = EPISODE / "scripts/generate_native_loca_higher_order_results.py"
TRILINOS = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")


@lru_cache(maxsize=1)
def executable() -> Path:
    if not TRILINOS.is_file() or shutil.which("cmake") is None:
        pytest.skip("Trilinos/CMake unavailable")
    build = ROOT / ".pytest_cache/task066-loca-build"
    subprocess.run(["cmake", "-S", "loca", "-B", str(build), "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", f"-DTrilinos_DIR={TRILINOS.parent}"],
                   cwd=ROOT, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=ROOT, check=True)
    return build / "bs2026_midpoint_orbit"


def run(command: str, fixture: str) -> list[list[str]]:
    completed = subprocess.run([str(executable()), command, str(FIXTURES / fixture)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    return [line.split() for line in completed.stdout.splitlines() if line.strip()]


@pytest.mark.parametrize(("fixture", "n", "r", "size"), [
    ("canonical-g2-n64.txt", 64, 2, 577),
    ("canonical-g3-n32.txt", 32, 3, 385),
])
def test_higher_order_loca_base_is_square_and_extended_only_by_loca(fixture: str, n: int, r: int, size: int):
    rows = run("loca-contract", fixture)
    contract = next(row for row in rows if row[0] == "loca_contract")
    assert contract[1] == "native-loca-gauss-fixed-mesh-pseudo-arclength-v1"
    assert tuple(map(int, contract[2:])) == (1, 1, size, size + 1, size - 1, size - 1)
    method = next(row for row in rows if row[0] == "loca_method")
    assert method[1:7] == ["Arc_Length", "native_stepper", "true", "base_has_arclength", "false", "metric"]
    rule = next(row for row in rows if row[0] == "rule")
    assert rule[1:4] == ["gauss-legendre", str(r), str(2*r)]
    assert size == 3*n*(r+1)+1


@pytest.mark.parametrize(("fixture", "n", "r"), [
    ("canonical-g2-n64.txt", 64, 2),
    ("canonical-g3-n32.txt", 32, 3),
])
def test_metric_is_quadrature_normalized_and_native_rejection_retries(fixture: str, n: int, r: int):
    rows = run("loca-smoke", fixture)
    metric = next(row for row in rows if row[0] == "metric")
    weights = np.asarray(metric[2:], dtype=float)
    scaling = np.asarray(json.loads((EPISODE / "outputs/fixed_mesh_midpoint_results.json").read_text())["state_scaling"])
    assert weights.size == 3*n*(r+1)+2
    endpoints = weights[:3*n].reshape(n, 3)
    stages = weights[3*n:3*n*(r+1)].reshape(n, r, 3)
    np.testing.assert_allclose(endpoints.sum(axis=0), 0.5*scaling**2, rtol=2e-15)
    np.testing.assert_allclose(stages.sum(axis=(0, 1)), 0.5*scaling**2, rtol=2e-15)
    assert weights[-2:].tolist() == [1.0, 1.0]
    weighted_dot = next(row for row in rows if row[0] == "group_weighted_dot")
    assert float(weighted_dot[1]) == pytest.approx(float(weighted_dot[2]), rel=2e-15, abs=2e-15)
    forced = next(row for row in rows if row[0] == "forced_rejection_result")
    events = [row for row in rows if row[0] == "forced_rejection_event"]
    assert int(forced[2]) == int(forced[7]) == 1
    rejected = next(row for row in events if row[2] == "rejected")
    retry = events[events.index(rejected) + 1]
    assert 0 < abs(float(rejected[6])) < abs(float(rejected[5]))
    assert float(retry[5]) == pytest.approx(float(rejected[6]))


@pytest.mark.parametrize(("fixture", "r"), [
    ("canonical-g2-n64.txt", 2),
    ("canonical-g3-n32.txt", 3),
])
def test_thyra_model_evaluator_dfdp_matches_centered_residual_trials(fixture: str, r: int):
    rows = run("loca-dfdp", fixture)
    for path_name in ("rho", "temperature_hat"):
        summary = next(row for row in rows if row[0] == "dfdp" and row[1] == path_name)
        column_row = next(row for row in rows if row[0] == "dfdp_column" and row[1] == path_name)
        centered_row = next(row for row in rows if row[0] == "dfdp_centered_difference" and row[1] == path_name)
        column = np.asarray(column_row[3:], dtype=float)
        centered = np.asarray(centered_row[3:], dtype=float)
        assert column.size == centered.size == int(column_row[2]) == int(centered_row[2])
        measured = np.linalg.norm(column - centered) / max(1.0, np.linalg.norm(column))
        assert measured == pytest.approx(float(summary[3]), rel=2e-9, abs=2e-15)
        assert measured < 2e-6
        # The plus/minus trials share the model and assembler.  Its final
        # center call must restore coordinate and physical environment exactly.
        assert float(summary[4]) == float(summary[9])
        assert float(summary[5]) == pytest.approx(float(summary[7]), abs=1e-14)
        assert float(summary[6]) == pytest.approx(float(summary[8]), abs=1e-14)
        assert r in (2, 3)


def test_three_stage_signed_bootstrap_refresh_and_exact_five_branches():
    rows = run("loca-branches", "canonical-g3-n32.txt")
    beginnings = [row for row in rows if row[0] == "branch_begin"]
    assert [row[1] for row in beginnings] == [
        "fixed225-to-spine", "spine-positive-T-hat", "spine-negative-T-hat-to-210",
        "slice210-negative-rho", "slice210-positive-rho",
    ]
    for begin in beginnings:
        branch, origin, target = begin[1], float(begin[4]), float(begin[5])
        direction = np.sign(target-origin)
        bootstrap = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == branch]
        points = [row for row in rows if row[0] == "branch_point" and row[1] == branch]
        validations = [row for row in rows if row[0] == "branch_validation" and row[1] == branch]
        end = next(row for row in rows if row[0] == "branch_end" and row[1] == branch)
        assert bootstrap and np.sign(float(bootstrap[-1][3])) == direction and bootstrap[-1][5] == "accepted"
        assert float(points[-1][4]) == target
        assert len(points) == len(validations)
        assert end[10] == "true"
        restart = next(row for row in rows if row[0] == "branch_restart" and row[1] == branch)
        signed_component, signed_norm = float(restart[2]), float(restart[3])
        injected_component, injected_norm, signed_step = map(float, restart[4:7])
        assert np.sign(signed_component) == np.sign(signed_step) == direction
        assert signed_norm == pytest.approx(1.0, abs=2e-14)
        assert injected_component > 0.0
        assert injected_norm == pytest.approx(1.0, abs=2e-14)
        assert (restart[7] == "true") == (direction < 0)
        for validation in validations:
            assert max(map(float, validation[3:8])) < 1e-9
            assert validation[8:12] == ["true", "true", "KLU2", "true"]
            assert float(validation[12]) < 2e-7
    fixed_bootstrap = [row for row in rows if row[0] == "branch_bootstrap" and row[1] == "fixed225-to-spine"]
    assert [row[5] for row in fixed_bootstrap] == ["rejected", "accepted"]
    assert float(fixed_bootstrap[1][3]) == pytest.approx(0.5 * float(fixed_bootstrap[0][3]))
    refreshes = [row for row in rows if row[0] == "phase_refresh"]
    assert [row[1:3] for row in refreshes] == [
        ["phase-ref-episode007-seed", "phase-ref-spine-225"],
        ["phase-ref-spine-225", "phase-ref-slice-210"],
    ]
    for refresh in refreshes:
        assert float(refresh[6]) == pytest.approx(float(refresh[8]), abs=1e-12)
        assert float(refresh[7]) == pytest.approx(float(refresh[9]), abs=1e-12)
        assert max(float(refresh[15]), float(refresh[16])) <= 1e-14
        assert refresh[17:19] == ["true", "true"]


def _assert_accounting(events: list[dict[str, Any]], branch: dict[str, Any]) -> None:
    assert [event["callback_index"] for event in events] == list(range(len(events)))
    initial = [event for event in events if event["save_role"] == "initial"]
    final = [event for event in events if event["save_role"] == "final"]
    regular = [event for event in events if event["save_role"] == "regular"]
    accepted = [event for event in events if event["status"] == "accepted"]
    rejected = [event for event in regular if event["status"] == "rejected"]
    regular_accepted = [event for event in regular if event["status"] == "accepted"]
    assert len(initial) == len(final) == 1
    assert initial[0]["status"] == final[0]["status"] == "accepted"
    assert len(regular) == len(regular_accepted) + len(rejected)
    assert int(branch["native_point_count"]) == len(accepted)
    assert int(branch["raw_loca_total_step_count"]) == len(regular)
    assert int(branch["raw_loca_failed_step_count"]) == len(rejected)
    assert int(branch["raw_loca_step_number"]) == len(regular_accepted) + 1
    for event in rejected:
        index = int(event["callback_index"])
        retry = events[index + 1]
        assert retry["save_role"] == "regular"
        assert float(event["retry_coordinate_delta"]) == pytest.approx(
            float(retry["attempted_coordinate_delta"]), abs=1e-15,
        )


def test_higher_order_artifacts_are_current_native_only_and_all_point_parity():
    env = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable())}
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, env=env, check=True)
    data = json.loads(RESULTS.read_text())
    assert data["schema_version"] == "episode8-native-loca-higher-order-v1"
    assert [branch["branch_id"] for branch in data["branches"]] == data["required_branch_ids"]
    assert all(branch["reached_exact_target"] and branch["used_bootstrap_restart_tangent"] for branch in data["branches"])
    assert data["controlled_phase_reference_refresh_count"] == 2
    runtime = data["runtime_provenance"]
    assert runtime["emitting_executable_sha256"] == sha256(executable())
    branch_rows = run("loca-contract", "canonical-g3-n32.txt")
    assert runtime["compiler_and_trilinos"] == next(row for row in branch_rows if row[0] == "build_identity")[1:]
    assert runtime["cmake_source_sha256"] == sha256(ROOT / "loca/CMakeLists.txt")
    assert runtime["cmake_build_type"] == "build_type_Release"
    assert "exact SHA-256" in runtime["check_semantics"]
    assert data["parity"]["native_vectors_are_never_Python_seeds"] is True
    assert data["parity"]["maximum_all_point_period_relative_error"] <= data["parity"]["period_relative_tolerance"]
    assert data["parity"]["maximum_all_point_weighted_orbit_error"] <= data["parity"]["weighted_orbit_tolerance"]
    with np.load(VECTORS, allow_pickle=False) as native:
        assert len(native.files) == len(data["points"]) == data["vector_artifact"]["array_count"]
        assert all(name.startswith("native_g3__") and native[name].shape == (385,) for name in native.files)
        assert hashlib.sha256(VECTORS.read_bytes()).hexdigest() == data["vector_artifact"]["sha256"]
    for source in data["source_provenance"].values():
        assert sha256(ROOT / source["path"]) == source["sha256"]
    assert data["source_provenance"]["cmake_source_configuration"]["sha256"] == runtime["cmake_source_sha256"]
    for contract in data["native_contracts"].values():
        assert {check["path"] for check in contract["model_evaluator_dfdp_checks"]} == {"rho", "temperature_hat"}
        assert all(check["requested_out_arg"] == "OUT_ARG_DfDp DERIV_MV_BY_COL"
                   and check["recomputed_relative_error"] <= check["relative_tolerance"]
                   for check in contract["model_evaluator_dfdp_checks"])
        forced = contract["forced_native_rejection"]
        forced_branch = {
            "native_point_count": forced["saved_point_count"],
            "raw_loca_step_number": forced["raw_step_number"],
            "raw_loca_failed_step_count": forced["raw_failed_step_count"],
            "raw_loca_total_step_count": forced["raw_total_step_count"],
        }
        _assert_accounting(forced["events"], forced_branch)
        assert all(forced["accounting_invariants"].values())
    for branch in data["branches"]:
        branch_events = [event for event in data["events"]
                         if event["event_type"] == "native_loca_step" and event["branch_id"] == branch["branch_id"]]
        _assert_accounting(branch_events, branch)
        assert all(branch["accounting_invariants"].values())
        orientation = branch["restart_orientation"]
        direction = np.sign(branch["target_coordinate"] - branch["origin_coordinate"])
        assert np.sign(orientation["signed_bootstrap_parameter_component"]) == direction
        assert np.sign(orientation["signed_initial_step"]) == direction
        assert orientation["injected_parameter_component"] > 0
        assert orientation["signed_bootstrap_weighted_norm"] == pytest.approx(1.0, abs=2e-14)
        assert orientation["injected_weighted_norm"] == pytest.approx(1.0, abs=2e-14)
    refreshes = [event for event in data["events"] if event["event_type"] == "native_phase_reference_refresh"]
    assert len(refreshes) == data["controlled_phase_reference_refresh_count"] == 2
    event_positions = {id(event): index for index, event in enumerate(data["events"])}
    first_spine_consumer = next(event for event in data["events"]
                                if event.get("branch_id") == "spine-positive-T-hat")
    first_slice_consumer = next(event for event in data["events"]
                                if event.get("branch_id") == "slice210-negative-rho")
    assert event_positions[id(refreshes[0])] < event_positions[id(first_spine_consumer)]
    assert event_positions[id(refreshes[1])] < event_positions[id(first_slice_consumer)]
    for refresh in refreshes:
        verification = refresh["verification"]
        assert max(verification["physical_temperature_identity_abs"],
                   verification["physical_log_w_identity_abs"],
                   verification["source_stage_to_reference_max_abs"],
                   verification["source_derivative_to_reference_max_abs"]) <= 1e-12
        assert all(refresh["native_rebuild_reporting"].values())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_higher_order_generator_binds_check_to_exact_executable_digest(tmp_path: Path):
    copied = tmp_path / "bs2026_midpoint_orbit"
    copied.write_bytes(executable().read_bytes() + b"\nTASK066-digest-probe\n")
    copied.chmod(0o755)
    completed = subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT,
        env={**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(copied)}, text=True, capture_output=True)
    assert completed.returncode != 0
    assert "artifacts are stale" in completed.stderr


@pytest.mark.parametrize("relative_source", [
    "loca/include/bergner_spichtinger_2026_loca/midpoint_loca.hpp",
    "loca/src/midpoint_orbit_cli.cpp",
])
def test_higher_order_generator_rejects_stale_executable(tmp_path: Path, relative_source: str):
    copied = tmp_path / "bs2026_midpoint_orbit"
    copied.write_bytes(executable().read_bytes())
    copied.chmod(0o755)
    source = ROOT / relative_source
    original = source.read_text()
    try:
        source.write_text(original + "\n")
        completed = subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT,
            env={**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(copied)}, text=True, capture_output=True)
        assert completed.returncode != 0
        assert "source fingerprint" in completed.stderr
    finally:
        source.write_text(original)
