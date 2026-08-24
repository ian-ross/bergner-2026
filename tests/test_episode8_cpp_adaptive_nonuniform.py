from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    MidpointResidualTolerances,
    apply_global_beta_r_movement,
    build_composite_r_monitor,
    correct_gauss_orbit,
    decide_adaptation_cycle,
    gauss_legendre_rule,
    mark_h_refinement,
    restart_plan,
    transfer_tangent_by_collocation_polynomial,
)
from bergner_spichtinger_2026.constants import Environment

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
FIXTURES = EPISODE / "outputs/cpp_adaptive_nonuniform_fixtures"
MANIFEST = FIXTURES / "manifest.json"
GENERATOR = EPISODE / "scripts/generate_cpp_adaptive_nonuniform_fixtures.py"
TRILINOS = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
PARITY_RTOL = 1e-11
PARITY_ATOL = 1e-13


@lru_cache(maxsize=1)
def executable() -> Path:
    if not TRILINOS.is_file() or shutil.which("cmake") is None:
        pytest.skip("Trilinos/CMake unavailable")
    build = ROOT / ".pytest_cache/task068-nonuniform-build"
    subprocess.run([
        "cmake", "-S", "loca", "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", f"-DTrilinos_DIR={TRILINOS.parent}",
    ], cwd=ROOT, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=ROOT, check=True)
    return build / "bs2026_midpoint_orbit"


def parse_fixture(path: Path) -> tuple[GaussCollocationAssembler, np.ndarray, dict[str, float]]:
    tokens = path.read_text().split()
    if tokens[0] != "BS2026_GAUSS_FIXTURE_V1":
        raise AssertionError("unexpected fixture magic")
    interval_count = int(tokens[2])
    stage_count = int(tokens[3])
    offset = 7
    p, temperature, w, F, n_a, dz = map(float, tokens[offset:offset + 6])
    offset += 6
    lower, upper, spine = map(float, tokens[offset:offset + 3])
    offset += 3
    scaling = np.asarray(tokens[offset:offset + 3], dtype=float)
    offset += 3
    boundaries = np.asarray(tokens[offset:offset + interval_count + 1], dtype=float)
    offset += interval_count + 1
    stage_rows = interval_count * stage_count
    phase_values = np.asarray(tokens[offset:offset + 3 * stage_rows], dtype=float).reshape(interval_count, stage_count, 3)
    offset += 3 * stage_rows
    phase_derivatives = np.asarray(tokens[offset:offset + 3 * stage_rows], dtype=float).reshape(interval_count, stage_count, 3)
    offset += 3 * stage_rows
    unknown_size = 3 * interval_count * (stage_count + 1) + 1
    unknowns = np.asarray(tokens[offset:offset + unknown_size], dtype=float)
    assert unknowns.size == unknown_size
    assert offset + unknown_size == len(tokens)
    rule = gauss_legendre_rule(stage_count)
    reference = FrozenPhaseReference(
        FixedMesh(boundaries), phase_values, phase_derivatives, scaling,
        np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
    )
    env = Environment(p=p, T=temperature, w=w, F=F, N_a=n_a, Δz=dz, include_evaporation=False)
    assembler = GaussCollocationAssembler(reference.mesh, env, reference, rule)
    return assembler, unknowns, {"lower": lower, "upper": upper, "spine": spine}


def run(command: str, fixture: str) -> dict[str, object]:
    completed = subprocess.run([str(executable()), command, str(FIXTURES / fixture)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    output: dict[str, object] = {"raw": completed.stdout, "rows": {}}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if fields[0] in {
            "residual", "jacobian_action", "centered_difference", "log_period", "rho", "temperature_hat", "solution",
            "destination_boundaries", "transferred_unknowns", "transferred_tangent",
            "transferred_phase_values", "transferred_phase_derivatives",
            "defect_combined", "defect_next_element", "defect_dyadic_element", "defect_probe_admitted",
            "defect_grid_disagreement", "defect_endpoint_left", "defect_endpoint_right",
            "defect_derivative_jumps", "monitor_values", "monitor_target_boundaries",
            "r_movement_boundaries", "restart_solution",
        }:
            output[fields[0]] = np.asarray(fields[2:], dtype=float)
        elif fields[0] == "row":
            output["rows"][int(fields[1])] = list(map(int, fields[3:]))
        elif fields[0] == "defect_material_elements":
            output[fields[0]] = [int(value) for value in fields[2:]]
        elif fields[0] == "h_marking":
            output[fields[0]] = fields[1:4] + [float(fields[4])] + [int(value) for value in fields[5:]]
        else:
            output[fields[0]] = fields[1:]
    return output


def deterministic_split_boundaries(boundaries: np.ndarray) -> np.ndarray:
    result = [float(boundaries[0])]
    for interval in range(boundaries.size - 1):
        if interval % 9 == 0:
            result.append(0.5 * float(boundaries[interval] + boundaries[interval + 1]))
        result.append(float(boundaries[interval + 1]))
    return np.asarray(result, dtype=float)


def continuation_metric_weights(assembler: GaussCollocationAssembler) -> np.ndarray:
    mesh = assembler.mesh
    layout = assembler.layout
    weights = np.zeros(layout.unknown_size + 1)
    for interval, width in enumerate(mesh.widths):
        previous_width = mesh.widths[(interval - 1) % mesh.interval_count]
        for component, scale in enumerate(assembler.state_scaling):
            weights[layout.endpoint_slice(interval).start + component] = 0.25 * (width + previous_width) * scale**2
            for stage, quadrature_weight in enumerate(assembler.rule.quadrature_weights):
                weights[layout.stage_slice(interval, stage).start + component] = 0.5 * width * quadrature_weight * scale**2
    weights[layout.log_period_index] = 1.0
    weights[-1] = 1.0
    return weights


def test_task068_nonuniform_fixture_bundle_is_current_and_versioned() -> None:
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema_version"] == "episode008-cpp-adaptive-nonuniform-fixtures-v1"
    assert manifest["adaptive_method_version"] == "external-gauss3-hr-adaptive-v1"
    assert manifest["projection_contract"]["mesh"] == "nonuniform final cycle boundaries"
    assert [case["source_case_id"] for case in manifest["cases"]] == [
        "canonical-g3-n32",
        "guard-rho-0-g3-n32",
        "guard-rho-minus-0.15-g3-n32",
        "guard-rho-plus-0.15-g3-n32",
    ]
    for source in manifest["source_provenance"].values():
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    for case in manifest["cases"]:
        path = FIXTURES / case["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case["sha256"]
        assert case["interval_count"] > 32
        assert case["status"] == "accepted"
        assert case["final_defect_maximum"] < 1e-4


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-0-g3-n32.txt",
    "adaptive-guard-rho-minus-0.15-g3-n32.txt",
    "adaptive-guard-rho-plus-0.15-g3-n32.txt",
])
def test_cpp_nonuniform_residual_jacobian_and_parameter_columns_match_python(fixture: str) -> None:
    assembler, unknowns, path = parse_fixture(FIXTURES / fixture)
    output = run("evaluate", fixture)
    np.testing.assert_allclose(output["residual"], assembler.residual(unknowns), rtol=PARITY_RTOL, atol=PARITY_ATOL)
    direction = np.sin(np.arange(unknowns.size) + 0.73)
    direction /= np.linalg.norm(direction)
    jacobian = assembler.jacobian(unknowns)
    np.testing.assert_allclose(output["jacobian_action"], jacobian @ direction, rtol=PARITY_RTOL, atol=PARITY_ATOL)
    np.testing.assert_allclose(
        output["log_period"], jacobian[:, assembler.layout.log_period_index].toarray().ravel(),
        rtol=PARITY_RTOL, atol=PARITY_ATOL,
    )
    cpp_fd_error = np.linalg.norm(output["jacobian_action"] - output["centered_difference"]) / max(
        1.0, np.linalg.norm(output["jacobian_action"]),
    )
    assert cpp_fd_error < 1e-6

    def residual_at(*, dT: float = 0.0, dlogw: float = 0.0) -> np.ndarray:
        env = assembler.env
        moved = Environment(
            T=env.T + dT, p=env.p, w=env.w * np.exp(dlogw), F=env.F,
            N_a=env.N_a, Δz=env.Δz, include_evaporation=False,
        )
        return GaussCollocationAssembler(assembler.mesh, moved, assembler.phase_reference, assembler.rule).residual(unknowns)

    h = 1e-6
    rho_fd = (
        residual_at(dlogw=0.5 * (path["upper"] - path["lower"]) * h)
        - residual_at(dlogw=-0.5 * (path["upper"] - path["lower"]) * h)
    ) / (2 * h)
    temperature_fd = (
        residual_at(dT=25 * h, dlogw=25 * path["spine"] * h)
        - residual_at(dT=-25 * h, dlogw=-25 * path["spine"] * h)
    ) / (2 * h)
    assert np.linalg.norm(output["rho"] - rho_fd) / max(1.0, np.linalg.norm(output["rho"])) < 1e-6
    assert np.linalg.norm(output["temperature_hat"] - temperature_fd) / max(
        1.0, np.linalg.norm(output["temperature_hat"]),
    ) < 1e-6


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-minus-0.15-g3-n32.txt",
])
def test_cpp_nonuniform_continuation_metric_matches_independent_python_formula(fixture: str) -> None:
    assembler, _, _ = parse_fixture(FIXTURES / fixture)
    output = run("loca-contract", fixture)
    assert output["loca_contract"][0] == "native-loca-gauss-fixed-mesh-pseudo-arclength-v1"
    assert output["loca_method"][6] == "endpoint-stage-half-weighted-l2-v1"
    metric = np.asarray(output["metric"], dtype=float)
    np.testing.assert_allclose(metric[1:], continuation_metric_weights(assembler), rtol=1e-14, atol=1e-15)
    dot = np.asarray(output["group_weighted_dot"], dtype=float)
    np.testing.assert_allclose(dot[0], dot[1], rtol=1e-14, atol=1e-14)


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-plus-0.15-g3-n32.txt",
])
def test_cpp_nonuniform_collocation_polynomial_transfer_matches_python(fixture: str) -> None:
    assembler, unknowns, _ = parse_fixture(FIXTURES / fixture)
    output = run("adaptive-transfer", fixture)
    contract = output["adaptive_transfer_contract"]
    assert contract[0] == "collocation-polynomial-transfer-v1"
    destination_boundaries = deterministic_split_boundaries(assembler.mesh.boundaries)
    np.testing.assert_allclose(output["destination_boundaries"], destination_boundaries, rtol=0, atol=0)
    destination_mesh = FixedMesh(destination_boundaries)
    expected_unknowns = assembler.transfer_unknowns(unknowns, destination_mesh, assembler.rule)
    reference = assembler.transferred_phase_reference(unknowns, destination_mesh, assembler.rule)
    tangent = np.cos(np.arange(unknowns.size) + 0.21)
    tangent /= np.linalg.norm(tangent)
    expected_tangent = transfer_tangent_by_collocation_polynomial(
        assembler, unknowns, tangent, destination_mesh, assembler.rule,
    )
    np.testing.assert_allclose(output["transferred_unknowns"], expected_unknowns, rtol=1e-11, atol=1e-13)
    np.testing.assert_allclose(output["transferred_tangent"], expected_tangent, rtol=2e-7, atol=3e-9)
    phase_values = output["transferred_phase_values"].reshape(
        destination_mesh.interval_count, assembler.rule.stage_count, 3,
    )
    phase_derivatives = output["transferred_phase_derivatives"].reshape(
        destination_mesh.interval_count, assembler.rule.stage_count, 3,
    )
    np.testing.assert_allclose(phase_values, reference.stage_values, rtol=1e-11, atol=1e-13)
    np.testing.assert_allclose(phase_derivatives, reference.stage_derivatives, rtol=1e-11, atol=1e-13)
    np.testing.assert_allclose(float(output["transferred_phase_energy"][0]), reference.phase_energy, rtol=1e-11)


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-minus-0.15-g3-n32.txt",
])
def test_cpp_nonuniform_adaptive_controller_intermediates_match_python(fixture: str) -> None:
    assembler, unknowns, _ = parse_fixture(FIXTURES / fixture)
    output = run("adaptive-controller", fixture)
    assert output["adaptive_controller_contract"] == [
        "external-gauss3-hr-adaptive-v1",
        "two-grid-relative-defect-v1",
        "composite-r-monitor-v1",
        "defect-bulk-halfmax-marking-v1",
        "global-beta-r-movement-v1",
        "adaptive-cycle-controller-v1",
        "fixed-parameter-remesh-restart-retry-v1",
    ]
    defect = assembler.independent_defect(unknowns)
    np.testing.assert_allclose(output["defect_combined"], defect.combined_element_maxima, rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_next_element"], np.max(defect.next_gauss.relative_defects, axis=1), rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_dyadic_element"], np.max(defect.staggered_dyadic.relative_defects, axis=1), rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_probe_admitted"], defect.admitted_probe_element_maxima, rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_grid_disagreement"], defect.grid_disagreement, rtol=3e-8, atol=1e-12)
    np.testing.assert_allclose(output["defect_endpoint_left"], defect.endpoint_left, rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_endpoint_right"], defect.endpoint_right, rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(output["defect_derivative_jumps"], defect.derivative_jumps, rtol=1e-10, atol=1e-13)
    summary = np.asarray(output["defect_summary"][:3], dtype=float)
    np.testing.assert_allclose(summary[0], defect.maximum, rtol=1e-10, atol=1e-13)
    assert int(summary[2]) == defect.argmax_bin
    assert output["defect_material_elements"] == list(defect.materially_disagreeing_elements)

    monitor = build_composite_r_monitor(assembler, unknowns)
    np.testing.assert_allclose(output["monitor_values"], monitor.values, rtol=1e-9, atol=2e-12)
    np.testing.assert_allclose(output["monitor_target_boundaries"], monitor.target_boundaries, rtol=1e-9, atol=2e-12)
    h = mark_h_refinement(defect)
    cpp_h = output["h_marking"]
    assert int(cpp_h[0]) == len(h.marked_elements)
    assert int(cpp_h[1]) == h.growth_limit
    assert int(cpp_h[2]) == h.new_interval_count
    np.testing.assert_allclose(float(cpp_h[3]), h.halfmax_threshold, rtol=1e-12, atol=1e-15)
    assert cpp_h[4:] == list(h.marked_elements)
    r = apply_global_beta_r_movement(assembler.mesh, monitor.target_boundaries)
    assert output["r_movement"][0] == ("accepted" if r.accepted else "stalled")
    np.testing.assert_allclose(float(output["r_movement"][1]), r.beta, rtol=0, atol=0)
    np.testing.assert_allclose(np.asarray(output["r_movement"][3:], dtype=float), r.attempted_betas, rtol=0, atol=0)
    np.testing.assert_allclose(output["r_movement_boundaries"], r.new_boundaries, rtol=3e-12, atol=2e-13)
    decision = decide_adaptation_cycle(
        interval_count=assembler.mesh.interval_count,
        cycle_index=0,
        defect_maximum=defect.maximum,
        period_relative_change=None,
        weighted_orbit_change=None,
        consecutive_pure_r_cycles=0,
        pure_r_defect_reduction=None,
        maximum_defect_element=int(np.argmax(defect.combined_element_maxima)),
    )
    assert output["cycle_decision"] == ["cycle_budget", "resolution_unresolved", "resolution_unresolved", "cycle_budget_exhausted"]
    assert f"cycle_decision actual {decision.action} {decision.terminal_status} {' '.join(decision.reasons)}" in output["raw"]
    assert output["restart_plan"] == [
        "tangent_only", "deterministic_two_point_rebootstrap",
        "restart_with_rebootstrapped_tangent", "reject_after_rebootstrap_failure",
    ]
    assert f"restart_plan h+r {' '.join(attempt.name for attempt in restart_plan(remesh_kind='h+r').attempts)}" in output["raw"]
    assert f"restart_plan pure-r {' '.join(attempt.name for attempt in restart_plan(remesh_kind='pure-r').attempts)}" in output["raw"]


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-0-g3-n32.txt",
])
def test_cpp_nonuniform_adaptive_restart_rebuild_and_correction_match_python(fixture: str) -> None:
    assembler, unknowns, _ = parse_fixture(FIXTURES / fixture)
    output = run("adaptive-restart", fixture)
    assert output["adaptive_restart_contract"][:4] == [
        "fixed-parameter-remesh-restart-v1", "h+r",
        "collocation-polynomial-transfer-v1", "fixed-parameter-remesh-restart-retry-v1",
    ]
    old_intervals = assembler.mesh.interval_count
    destination_boundaries = deterministic_split_boundaries(assembler.mesh.boundaries)
    destination_mesh = FixedMesh(destination_boundaries)
    destination_reference = assembler.transferred_phase_reference(unknowns, destination_mesh, assembler.rule)
    destination_assembler = GaussCollocationAssembler(destination_mesh, assembler.env, destination_reference, assembler.rule)
    transferred = assembler.transfer_unknowns(unknowns, destination_mesh, assembler.rule)
    python_correction = correct_gauss_orbit(
        destination_assembler, transferred,
        tolerances=MidpointResidualTolerances(), max_nfev=300,
    )
    assert python_correction.accepted
    rebuild = [int(value) for value in output["restart_rebuild"]]
    assert rebuild[:2] == [unknowns.size, transferred.size]
    assert rebuild[10:] == [assembler.rule.stage_count, assembler.rule.stage_count]
    assert int(output["adaptive_restart_contract"][4]) == old_intervals
    assert int(output["adaptive_restart_contract"][5]) == destination_mesh.interval_count
    assert output["restart_graph"][1:] == ["retained_reuse", "true", "rebuilt", "true"]
    assert output["restart_attempts"] == [
        "3", "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect",
    ]
    transfer_residual = np.asarray(output["restart_transfer_residual"][:5], dtype=float)
    assert transfer_residual[:4].max() > 1e-8
    assert transfer_residual[4] <= 1e-12
    tangent = np.asarray(output["restart_tangent"][:2], dtype=float)
    assert tangent[0] > 0.0
    np.testing.assert_allclose(tangent[1], 1.0, rtol=0, atol=0)
    assert output["restart_tangent"][2] == "true"
    assert output["restart_correction"][:2] == ["accepted", "converged"]
    assert output["restart_linear"][:2] == ["KLU2", "reported"]
    assert output["restart_linear"][5:] == ["true", "true", "true"]
    assert output["restart_gates"] == [
        "residual", "true", "phase", "true", "positivity", "true",
        "finite_change", "true", "linear", "true", "tangent", "true",
    ]
    diagnostics = np.asarray(output["restart_final_diagnostics"][:5], dtype=float)
    assert diagnostics[:4].max() <= 1e-9
    assert diagnostics[4] <= 1e-10
    np.testing.assert_allclose(float(output["restart_correction"][5]), np.exp(python_correction.unknowns[-1]), rtol=2e-12)
    np.testing.assert_allclose(output["restart_solution"], python_correction.unknowns, rtol=2e-9, atol=2e-10)


@pytest.mark.parametrize("fixture", [
    "adaptive-canonical-g3-n32.txt",
    "adaptive-guard-rho-0-g3-n32.txt",
    "adaptive-guard-rho-minus-0.15-g3-n32.txt",
    "adaptive-guard-rho-plus-0.15-g3-n32.txt",
])
def test_cpp_nonuniform_fixed_parameter_corrections_pass_independent_gates(fixture: str) -> None:
    output = run("solve", fixture)
    assert output["upstream_status"] == ["accepted"]
    assert output["nox"][0] == "converged"
    assert output["linear"][:2] == ["KLU2", "reported"]
    assert all(int(value) > 0 for value in output["linear"][2:5])
    assert output["linear"][5:] == ["true", "true", "true"]
    assert output["accepted"] == ["true"]
    diagnostics = np.asarray(output["diagnostics"][:5], dtype=float)
    assert diagnostics[:4].max() <= 1e-9
    assert diagnostics[4] <= 1e-10
