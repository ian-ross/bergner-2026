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
    gauss_legendre_rule,
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
        }:
            output[fields[0]] = np.asarray(fields[2:], dtype=float)
        elif fields[0] == "row":
            output["rows"][int(fields[1])] = list(map(int, fields[3:]))
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
