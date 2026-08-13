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
    JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
    MIDPOINT_FORMULATION_VERSION,
    MidpointCollocationAssembler,
    PeriodicHermiteSeed,
    gauss_legendre_rule,
)
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.periodic_orbits import midpoint_residual_diagnostics

REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
FIXTURES = EPISODE / "outputs/tpetra_midpoint_fixtures"
GENERATOR = EPISODE / "scripts/generate_tpetra_midpoint_fixtures.py"
MANIFEST = FIXTURES / "manifest.json"
FROZEN_VECTORS = EPISODE / "outputs/fixed_mesh_midpoint_vectors.npz"
TRILINOS_CONFIG = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
PARITY_TOLERANCE = 1.0e-11
PARITY_ABSOLUTE_FLOOR = 1.0e-13
DIRECTIONAL_TOLERANCE = JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE


def _missing_reason():
    if not TRILINOS_CONFIG.is_file():
        return f"Trilinos config not found at {TRILINOS_CONFIG}"
    for tool in ("cmake", "g++"):
        if shutil.which(tool) is None:
            return f"{tool} unavailable"
    return None


@lru_cache(maxsize=1)
def _executable() -> Path:
    reason = _missing_reason()
    if reason:
        pytest.skip(reason)
    build = REPO_ROOT / ".pytest_cache/loca-build"
    subprocess.run(["cmake", "-S", "loca", "-B", str(build), f"-DTrilinos_DIR={TRILINOS_CONFIG.parent}"], cwd=REPO_ROOT, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=REPO_ROOT, check=True)
    return build / "bs2026_midpoint_orbit"


def _run(case: str) -> dict:
    completed = subprocess.run([str(_executable()), "evaluate", str(FIXTURES / f"{case}.txt")], cwd=REPO_ROOT, text=True, capture_output=True, check=True)
    lines = completed.stdout.splitlines()
    output: dict[str, object] = {"raw": completed.stdout, "rows": {}}
    for line in lines:
        fields = line.split()
        if fields[0] in {"residual", "jacobian_action", "centered_difference", "rho", "temperature_hat"}:
            output[fields[0]] = np.array(fields[2:], dtype=float)
        elif fields[0] == "layout":
            output["layout"] = tuple(map(int, fields[1:]))
        elif fields[0] == "graph":
            output["graph"] = tuple(map(int, fields[1:]))
        elif fields[0] == "row":
            output["rows"][int(fields[1])] = set(map(int, fields[3:]))
        elif fields[0] == "diagnostics":
            output["diagnostics"] = np.array(fields[1:], dtype=float)
        elif fields[0] == "graph_reused":
            output["graph_reused"] = fields[1] == "true"
        elif fields[0] == "constants":
            output["constants"] = (fields[1], *map(float, fields[2:]))
    return output


def _python_case(case: str):
    count = 8 if case.startswith("n8") else 64
    seed_data = json.loads((EPISODE / "outputs/bootstrap_seed.json").read_text())
    p = seed_data["canonical_parameters"]
    env = Environment(T=p["T"], p=p["p"], w=p["w"], F=p["F"], N_a=p["N_a"], Δz=p["Delta_z"], include_evaporation=False)
    seed = PeriodicHermiteSeed.from_json(EPISODE / "outputs/bootstrap_seed.json")
    mesh = FixedMesh.uniform(count)
    rule = gauss_legendre_rule(1)
    ref = FrozenPhaseReference.from_evaluator(mesh, rule, seed.evaluate, seed.derivative, state_scaling=1 / np.ptp(seed.transformed_state[:-1], axis=0))
    assembler = MidpointCollocationAssembler(mesh, env, ref)
    tokens = (FIXTURES / f"{case}.txt").read_text().split()
    unknowns = np.array(tokens[-assembler.layout.unknown_size :], dtype=float)
    return assembler, unknowns


def test_task059_fixture_generator_is_byte_reproducible_and_manifested():
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=REPO_ROOT, check=True)
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["formulation_version"] == MIDPOINT_FORMULATION_VERSION
    assert manifest["parity_tolerance"] == {
        "relative": PARITY_TOLERANCE,
        "absolute_floor": PARITY_ABSOLUTE_FLOOR,
    }
    assert manifest["directional_relative_tolerance"] == DIRECTIONAL_TOLERANCE
    assert set(manifest["cases"]) == {
        "n8_converged", "n8_nonsolution", "n64_converged", "n64_nonsolution",
        "n64_seed", "n64_perturbed",
    }
    assert set(manifest["source_provenance"]) == {
        "generator", "python_assembler", "cpp_assembler", "cpp_nox_adapter", "cpp_cli",
        "bootstrap_seed", "task056_results", "task056_vectors", "uv_lock",
    }
    for record in manifest["source_provenance"].values():
        path = REPO_ROOT / record["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
    assert set(manifest["runtime_provenance"]) == {"python", "numpy", "scipy"}


@pytest.mark.parametrize("case", ["n8_converged", "n8_nonsolution", "n64_converged", "n64_nonsolution"])
def test_tpetra_residual_component_parity_and_diagnostics(case):
    cpp = _run(case)
    assembler, unknowns = _python_case(case)
    expected = assembler.residual(unknowns)
    np.testing.assert_allclose(cpp["residual"], expected, rtol=PARITY_TOLERANCE, atol=PARITY_ABSOLUTE_FLOOR)
    expected_diagnostics = midpoint_residual_diagnostics(assembler.layout.unpack_residual(expected))
    diagnostics = cpp["diagnostics"]
    np.testing.assert_allclose(diagnostics[:6], [expected_diagnostics.stage_max, expected_diagnostics.stage_rms, expected_diagnostics.update_max, expected_diagnostics.update_rms, expected_diagnostics.phase_abs, assembler.phase_energy], rtol=PARITY_TOLERANCE, atol=PARITY_ABSOLUTE_FLOOR)
    blocks = assembler.layout.unpack_residual(expected)
    stage_flat = np.abs(blocks.stages).reshape(-1)
    update_flat = np.abs(blocks.updates).reshape(-1)
    stage_argmax = int(np.argmax(stage_flat))
    update_argmax = int(np.argmax(update_flat))
    expected_identifiers = [
        stage_argmax // 3, stage_argmax % 3,
        update_argmax // 3, update_argmax % 3,
    ]
    np.testing.assert_array_equal(diagnostics[6:10], expected_identifiers)
    np.testing.assert_allclose(diagnostics[-3:], assembler.state_scaling, rtol=0, atol=0)
    if "converged" in case:
        assert diagnostics[0] <= 1e-9 and diagnostics[1] <= 1e-9
        assert diagnostics[2] <= 1e-9 and diagnostics[3] <= 1e-9
        assert diagnostics[4] <= 1e-10
    else:
        assert np.all(np.linalg.norm(blocks.stages[:, 0], axis=1) > 0)
        assert np.all(np.linalg.norm(blocks.updates, axis=1) > 0)
        assert abs(blocks.phase) > 0


@pytest.mark.parametrize(
    ("case", "count", "size", "entries"),
    [("n8_nonsolution", 8, 49, 288), ("n64_nonsolution", 64, 385, 2304)],
)
def test_tpetra_layout_fixed_graph_wraparound_global_column_and_phase_row(case, count, size, entries):
    output = _run(case)
    endpoint_size = 3 * count
    assert output["layout"] == (count, size, 0, endpoint_size, size - 1, size - 1)
    assert output["graph_reused"] is True
    assert output["graph"] == (entries, size)
    assert output["rows"][0] == {0, endpoint_size, endpoint_size + 1, endpoint_size + 2, size - 1}
    last_update_row = 6 * count - 3
    last_stage = 6 * count - 3
    assert output["rows"][last_update_row] == {0, endpoint_size - 3, last_stage, last_stage + 1, last_stage + 2, size - 1}
    assert output["rows"][size - 1] == set(range(endpoint_size, 2 * endpoint_size))
    assert output["constants"] == (
        MIDPOINT_FORMULATION_VERSION, PARITY_TOLERANCE,
        PARITY_ABSOLUTE_FLOOR, DIRECTIONAL_TOLERANCE,
    )


def test_tpetra_layout_rejects_one_interval():
    completed = subprocess.run(
        [str(_executable()), "guard-one-interval"], cwd=REPO_ROOT,
        text=True, capture_output=True, check=True,
    )
    assert completed.stdout.strip() == "one_interval_rejected true"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("guard-nonfinite-reference", "nonfinite_reference_rejected true"),
        ("guard-invalid-period", "invalid_period_rejected true"),
    ],
)
def test_tpetra_assembler_rejects_invalid_construction_and_period_inputs(command, expected):
    completed = subprocess.run(
        [str(_executable()), command, str(FIXTURES / "n8_nonsolution.txt")],
        cwd=REPO_ROOT, text=True, capture_output=True, check=True,
    )
    assert completed.stdout.strip() == expected


def _environment_columns(assembler, unknowns, *, temperature_step=0.0, log_w_step=0.0):
    env = assembler.env
    moved = Environment(T=env.T + temperature_step, p=env.p, w=env.w * np.exp(log_w_step), F=env.F, N_a=env.N_a, Δz=env.Δz, include_evaporation=False)
    return MidpointCollocationAssembler(assembler.mesh, moved, assembler.phase_reference).residual(unknowns)


def test_tpetra_jacobian_action_and_normalized_parameter_columns_pass_centered_differences():
    case = "n8_nonsolution"
    cpp = _run(case)
    assembler, unknowns = _python_case(case)
    direction = np.sin(np.arange(unknowns.size) + 0.73)
    direction /= np.linalg.norm(direction)
    epsilon = 2e-7
    jv = assembler.jacobian(unknowns) @ direction
    fd = (assembler.residual(unknowns + epsilon * direction) - assembler.residual(unknowns - epsilon * direction)) / (2 * epsilon)
    assert np.linalg.norm(jv - fd) / max(1.0, np.linalg.norm(jv)) < DIRECTIONAL_TOLERANCE
    np.testing.assert_allclose(cpp["jacobian_action"], jv, rtol=PARITY_TOLERANCE, atol=PARITY_ABSOLUTE_FLOOR)
    cpp_directional_error = np.linalg.norm(
        cpp["jacobian_action"] - cpp["centered_difference"]
    ) / max(1.0, np.linalg.norm(cpp["jacobian_action"]))
    assert cpp_directional_error <= DIRECTIONAL_TOLERANCE

    lower, upper, spine = np.log(0.01), np.log(0.25), 0.037
    h = 1e-6
    rho_factor = 0.5 * (upper - lower)
    rho_fd = (_environment_columns(assembler, unknowns, log_w_step=rho_factor * h) - _environment_columns(assembler, unknowns, log_w_step=-rho_factor * h)) / (2 * h)
    t_fd = (_environment_columns(assembler, unknowns, temperature_step=25*h, log_w_step=25*spine*h) - _environment_columns(assembler, unknowns, temperature_step=-25*h, log_w_step=-25*spine*h)) / (2*h)
    assert np.linalg.norm(cpp["rho"] - rho_fd) / max(1.0, np.linalg.norm(cpp["rho"])) < DIRECTIONAL_TOLERANCE
    assert np.linalg.norm(cpp["temperature_hat"] - t_fd) / max(1.0, np.linalg.norm(cpp["temperature_hat"])) < DIRECTIONAL_TOLERANCE


def _run_solve(case: str) -> dict[str, object]:
    completed = subprocess.run(
        [str(_executable()), "solve", str(FIXTURES / f"{case}.txt")],
        cwd=REPO_ROOT, text=True, capture_output=True, check=True,
    )
    result: dict[str, object] = {"raw": completed.stdout}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if fields[0] in {"solution", "final_residual"}:
            result[fields[0]] = np.array(fields[2:], dtype=float)
        elif fields[0] in {"solver", "solver_constants", "accepted", "period", "positivity", "thyra_system", "nox", "linear", "diagnostics", "rejection_reasons"}:
            result[fields[0]] = fields[1:]
    return result


@pytest.mark.parametrize("case", ["n64_seed", "n64_perturbed"])
def test_sparse_thyra_nox_klu2_corrects_n64_starts_with_python_parity(case):
    output = _run_solve(case)
    assembler, _ = _python_case("n64_converged")
    with np.load(FROZEN_VECTORS, allow_pickle=False) as frozen:
        reference = frozen["n64_unknowns"]
    solution = output["solution"]
    residual = assembler.residual(solution)
    blocks = assembler.layout.unpack_residual(residual)
    variables = assembler.layout.unpack(solution)
    manifest_solver = json.loads(MANIFEST.read_text())["fixed_parameter_nox"]
    parity_tolerance = manifest_solver["corrected_solution_parity_tolerance"]

    assert output["solver"] == [manifest_solver["solver_version"]]
    solver_constants = output["solver_constants"]
    assert float(solver_constants[0]) == manifest_solver["nox_norm_f_tolerance"]
    assert int(solver_constants[1]) == manifest_solver["nox_max_iterations"]
    assert float(solver_constants[2]) == manifest_solver["accepted_stage_update_tolerance"]
    assert float(solver_constants[3]) == manifest_solver["accepted_phase_tolerance"]
    assert float(solver_constants[4]) == parity_tolerance
    assert tuple(map(int, output["thyra_system"])) == (
        assembler.layout.unknown_size, assembler.layout.residual_size,
        assembler.layout.log_period_index, assembler.layout.phase_row,
    )
    assert output["nox"][0] == "converged"
    assert int(output["nox"][1]) > 0
    assert output["linear"][0:2] == ["KLU2", "reported"]
    symbolic, numeric, solves = map(int, output["linear"][2:5])
    assert symbolic > 0 and numeric > 0 and solves > 0
    assert output["linear"][5:] == ["true", "true", "true"]
    assert output["accepted"] == ["true"]
    assert output["rejection_reasons"] == ["0"]
    assert output["positivity"] == ["true", "true"]
    physical_log_states = np.concatenate([
        variables.endpoints[:, :2].reshape(-1),
        variables.stages[:, :, :2].reshape(-1),
    ])
    physical_states = np.exp(physical_log_states)
    assert np.all(np.isfinite(physical_states)) and np.all(physical_states > 0.0)
    assert np.all(np.isfinite(variables.endpoints[:, 2]))
    assert np.all(np.isfinite(variables.stages[:, :, 2]))
    physical_period = np.exp(variables.log_period)
    assert np.isfinite(physical_period) and physical_period > 0.0
    assert np.max(np.abs(blocks.stages)) <= manifest_solver["accepted_stage_update_tolerance"]
    assert np.sqrt(np.mean(blocks.stages**2)) <= manifest_solver["accepted_stage_update_tolerance"]
    assert np.max(np.abs(blocks.updates)) <= manifest_solver["accepted_stage_update_tolerance"]
    assert np.sqrt(np.mean(blocks.updates**2)) <= manifest_solver["accepted_stage_update_tolerance"]
    assert abs(blocks.phase) <= manifest_solver["accepted_phase_tolerance"]
    assert np.isfinite(assembler.phase_energy) and assembler.phase_energy > 0
    period = float(output["period"][0])
    reference_period = float(np.exp(reference[-1]))
    assert abs(period - reference_period) / reference_period <= parity_tolerance
    assert assembler.weighted_orbit_distance(solution, reference) <= parity_tolerance


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("block", "block_residual_tolerance"),
        ("phase", "phase_tolerance"),
        ("positivity", "physical_state_positivity_or_finiteness"),
        ("period", "period_positivity_or_finiteness"),
        ("phase-energy", "phase_energy_invalid"),
        ("linear", "linear_solve_diagnostics"),
    ],
)
def test_authoritative_acceptance_rejects_each_nominal_success_failure(failure, reason):
    completed = subprocess.run(
        [str(_executable()), "acceptance-guard", failure, str(FIXTURES / "n64_converged.txt")],
        cwd=REPO_ROOT, text=True, capture_output=True, check=True,
    )
    lines = completed.stdout.splitlines()
    assert lines[0] == "accepted false"
    assert lines[1] == f"rejection_reasons 1 {reason}"


@pytest.mark.parametrize(
    "arguments",
    [
        ("inspect", "n8_converged.txt", "extra"),
        ("evaluate", "n8_converged.txt", "extra"),
        ("solve", "n64_seed.txt", "extra"),
        ("guard-invalid-period", "n8_nonsolution.txt", "extra"),
        ("acceptance-guard", "block"),
    ],
)
def test_midpoint_cli_rejects_command_specific_wrong_arity(arguments):
    completed = subprocess.run(
        [str(_executable()), *arguments], cwd=FIXTURES,
        text=True, capture_output=True,
    )
    assert completed.returncode == 2
    assert completed.stderr.startswith("Usage:")


def test_n64_seed_and_perturbation_fixture_contract():
    assembler, _ = _python_case("n64_converged")
    seed = PeriodicHermiteSeed.from_json(EPISODE / "outputs/bootstrap_seed.json")
    expected_seed = assembler.reference_unknowns(seed.evaluate, seed.log_period)
    tokens = (FIXTURES / "n64_seed.txt").read_text().split()
    seed_fixture = np.array(tokens[-assembler.layout.unknown_size :], dtype=float)
    np.testing.assert_array_equal(seed_fixture, expected_seed)

    tokens = (FIXTURES / "n64_perturbed.txt").read_text().split()
    perturbed = np.array(tokens[-assembler.layout.unknown_size :], dtype=float)
    direction = np.sin(np.arange(perturbed.size, dtype=float) + 0.375)
    expected = expected_seed.copy()
    expected[:-1] += 1.0e-4 * direction[:-1]
    expected[-1] += 1.0e-5 * direction[-1]
    np.testing.assert_array_equal(perturbed, expected)


def test_n64_fixtures_translate_frozen_task056_arrays_and_residuals():
    with np.load(FROZEN_VECTORS, allow_pickle=False) as frozen:
        for case, unknown_key, residual_key in (
            ("n64_converged", "n64_unknowns", "n64_residual"),
            ("n64_nonsolution", "n64_nonsolution_unknowns", "n64_nonsolution_residual"),
        ):
            assembler, unknowns = _python_case(case)
            np.testing.assert_array_equal(unknowns, frozen[unknown_key])
            np.testing.assert_array_equal(assembler.mesh.boundaries, frozen["n64_boundaries"])
            np.testing.assert_array_equal(
                assembler.phase_reference.stage_values,
                frozen["n64_phase_reference_values"],
            )
            np.testing.assert_array_equal(
                assembler.phase_reference.stage_derivatives,
                frozen["n64_phase_reference_derivatives"],
            )
            np.testing.assert_array_equal(assembler.residual(unknowns), frozen[residual_key])
