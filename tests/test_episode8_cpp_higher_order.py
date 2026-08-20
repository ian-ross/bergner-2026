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

from bergner_spichtinger_2026 import FixedMesh, FrozenPhaseReference, GaussCollocationAssembler, gauss_legendre_rule
from bergner_spichtinger_2026.constants import Environment

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
FIXTURES = EPISODE / "outputs/cpp_higher_order_fixtures"
MANIFEST = FIXTURES / "manifest.json"
VECTORS = EPISODE / "outputs/higher_order_fixed_mesh_qualification_vectors.npz"
RESULTS = EPISODE / "outputs/higher_order_fixed_mesh_qualification.json"
MIDPOINT_RESULTS = EPISODE / "outputs/fixed_mesh_midpoint_results.json"
LANGUAGE_NEUTRAL = EPISODE / "outputs/higher_order_parity_fixtures"
CORRECTION_RESULTS = EPISODE / "outputs/cpp_higher_order_correction_results.json"
GENERATOR = EPISODE / "scripts/generate_cpp_higher_order_fixtures.py"
CORRECTION_GENERATOR = EPISODE / "scripts/generate_cpp_higher_order_correction_results.py"
TRILINOS = Path("/opt/Trilinos/lib64/cmake/Trilinos/TrilinosConfig.cmake")
PARITY_RTOL = 1e-11
PARITY_ATOL = 1e-13


def _missing_reason() -> str | None:
    if not TRILINOS.is_file():
        return f"Trilinos config unavailable: {TRILINOS}"
    if shutil.which("cmake") is None:
        return "cmake unavailable"
    return None


@lru_cache(maxsize=1)
def executable() -> Path:
    reason = _missing_reason()
    if reason:
        pytest.skip(reason)
    build = ROOT / ".pytest_cache/loca-higher-order-build"
    subprocess.run(["cmake", "-S", "loca", "-B", str(build), "-G", "Ninja",
                    "-DCMAKE_BUILD_TYPE=Release", f"-DTrilinos_DIR={TRILINOS.parent}"], cwd=ROOT, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], cwd=ROOT, check=True)
    return build / "bs2026_midpoint_orbit"


def run(command: str, case: str) -> dict[str, object]:
    completed = subprocess.run([str(executable()), command, str(FIXTURES / f"{case}.txt")],
                               cwd=ROOT, text=True, capture_output=True, check=True)
    output: dict[str, object] = {"raw": completed.stdout, "rows": {}}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if fields[0] in {"residual", "jacobian_action", "centered_difference", "log_period", "rho", "temperature_hat", "solution"}:
            output[fields[0]] = np.asarray(fields[2:], dtype=float)
        elif fields[0] == "row":
            output["rows"][int(fields[1])] = list(map(int, fields[3:]))
        else:
            output[fields[0]] = fields[1:]
    return output


def python_case(case: str, *, solution_key: str | None = None) -> tuple[GaussCollocationAssembler, np.ndarray]:
    base = case.removesuffix("-nonsolution")
    result = next(item for item in json.loads(RESULTS.read_text())["results"] if item["case_id"] == base)
    scaling = np.asarray(json.loads(MIDPOINT_RESULTS.read_text())["state_scaling"])
    with np.load(VECTORS, allow_pickle=False) as arrays:
        mesh = FixedMesh(arrays[base + "__boundaries"])
        rule = gauss_legendre_rule(result["stage_count"])
        reference = FrozenPhaseReference(mesh, arrays[base + "__phase_values"],
                                         arrays[base + "__phase_derivatives"], scaling,
                                         np.asarray(rule.nodes), np.asarray(rule.quadrature_weights))
        env = Environment(T=float(result.get("temperature_K", 225.0)), p=30000.0,
                          w=float(result.get("w_m_s", 0.1)), F=1.0, N_a=1e10, Δz=100.0,
                          include_evaporation=False)
        assembler = GaussCollocationAssembler(mesh, env, reference, rule)
        key = solution_key or base + "__unknowns"
        return assembler, arrays[key].copy()


def test_task065_fixture_bundle_is_deterministic_versioned_and_explicit():
    subprocess.run(["uv", "run", "python", str(GENERATOR), "--check"], cwd=ROOT, check=True)
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema_version"] == "episode008-cpp-gauss-fixtures-v1"
    assert manifest["bundle_membership"] == {
        "required_accepted_corrections": ["canonical-g2-n64", "canonical-g3-n32", "canonical-g3-n64",
                                           "guard-rho-0-g3-n32", "guard-rho-minus-0.15-g3-n32",
                                           "guard-rho-plus-0.15-g3-n32"],
        "explicit_upstream_rejections": ["canonical-g3-n16"],
        "representative_nonsolutions": ["canonical-g2-n64-nonsolution", "canonical-g3-n64-nonsolution"],
    }
    assert manifest["coefficient_artifact_sha256"] == "f47a6f789fa463abdfdb8d0b158a78bd228bbe85881199d601d086f49396ba6a"
    for source in manifest["source_provenance"].values():
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    for case in manifest["cases"]:
        assert hashlib.sha256((FIXTURES / case["path"]).read_bytes()).hexdigest() == case["sha256"]
        if case["upstream_status"] == "accepted":
            assert case["accepted_semantics"] == "nonlinear_accepted"
            assert case["scientifically_qualified"] is False
            assert case["seed_lineage"]


PARITY_CASES = [
    "canonical-g2-n64", "canonical-g2-n64-nonsolution",
    "canonical-g3-n32", "canonical-g3-n64", "canonical-g3-n64-nonsolution",
    "guard-rho-0-g3-n32", "guard-rho-minus-0.15-g3-n32", "guard-rho-plus-0.15-g3-n32",
]


@pytest.mark.parametrize("case", PARITY_CASES)
def test_cpp_residual_jacobian_action_and_parameter_columns_match_python(case: str):
    output = run("evaluate", case)
    assembler, _ = python_case(case)
    tokens = (FIXTURES / f"{case}.txt").read_text().split()
    unknowns = np.asarray(tokens[-assembler.layout.unknown_size:], dtype=float)
    expected = assembler.residual(unknowns)
    np.testing.assert_allclose(output["residual"], expected, rtol=PARITY_RTOL, atol=PARITY_ATOL)
    direction = np.sin(np.arange(unknowns.size) + 0.73)
    direction /= np.linalg.norm(direction)
    expected_jv = assembler.jacobian(unknowns) @ direction
    np.testing.assert_allclose(output["jacobian_action"], expected_jv, rtol=PARITY_RTOL, atol=PARITY_ATOL)
    expected_log_period = assembler.jacobian(unknowns)[:, assembler.layout.log_period_index].toarray().ravel()
    np.testing.assert_allclose(output["log_period"], expected_log_period, rtol=PARITY_RTOL, atol=PARITY_ATOL)
    cpp_fd_error = np.linalg.norm(output["jacobian_action"] - output["centered_difference"]) / max(1, np.linalg.norm(output["jacobian_action"]))
    assert cpp_fd_error < 1e-6

    def residual_at(*, dT: float = 0.0, dlogw: float = 0.0) -> np.ndarray:
        env = assembler.env
        moved = Environment(T=env.T + dT, p=env.p, w=env.w * np.exp(dlogw), F=env.F,
                            N_a=env.N_a, Δz=env.Δz, include_evaporation=False)
        return GaussCollocationAssembler(assembler.mesh, moved, assembler.phase_reference, assembler.rule).residual(unknowns)
    h = 1e-6
    lower, upper, spine = np.log(0.01), np.log(0.25), 0.037
    rho_fd = (residual_at(dlogw=0.5 * (upper - lower) * h) - residual_at(dlogw=-0.5 * (upper - lower) * h)) / (2*h)
    temperature_fd = (residual_at(dT=25*h, dlogw=25*spine*h) - residual_at(dT=-25*h, dlogw=-25*spine*h)) / (2*h)
    assert np.linalg.norm(output["rho"] - rho_fd) / max(1, np.linalg.norm(output["rho"])) < 1e-6
    assert np.linalg.norm(output["temperature_hat"] - temperature_fd) / max(1, np.linalg.norm(output["temperature_hat"])) < 1e-6


@pytest.mark.parametrize("name", ["g2-n64-converged", "g3-n64-converged"])
def test_exact_task064_converged_language_neutral_residual_components(name: str, tmp_path: Path):
    source = json.loads((LANGUAGE_NEUTRAL / f"{name}.json").read_text())
    case = source["case_id"].replace("-converged", "")
    tokens = (FIXTURES / f"canonical-{case}.txt").read_text().split()
    unknowns = np.asarray(source["arrays"]["unknowns"], dtype=float)
    tokens[-unknowns.size:] = [format(value, ".17g") for value in unknowns]
    fixture = tmp_path / f"{name}.txt"
    fixture.write_text(" ".join(tokens) + "\n")
    completed = subprocess.run([str(executable()), "evaluate", str(fixture)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    output = {}
    for line in completed.stdout.splitlines():
        fields = line.split()
        if fields[0] in {"residual", "jacobian_action", "log_period", "rho", "temperature_hat"}:
            output[fields[0]] = np.asarray(fields[2:], dtype=float)
    expected = np.concatenate([
        np.asarray(source["arrays"]["residual_stages"], dtype=float).reshape(-1),
        np.asarray(source["arrays"]["residual_updates"], dtype=float).reshape(-1),
        np.asarray(source["arrays"]["residual_phase"], dtype=float).reshape(-1),
    ])
    np.testing.assert_allclose(output["residual"], expected, rtol=PARITY_RTOL, atol=PARITY_ATOL)

    assembler, _ = python_case(f"canonical-{case}")
    direction = np.sin(np.arange(unknowns.size) + 0.73)
    direction /= np.linalg.norm(direction)
    jacobian = assembler.jacobian(unknowns)
    np.testing.assert_allclose(
        output["jacobian_action"], jacobian @ direction,
        rtol=PARITY_RTOL, atol=PARITY_ATOL,
    )
    np.testing.assert_allclose(
        output["log_period"],
        jacobian[:, assembler.layout.log_period_index].toarray().ravel(),
        rtol=PARITY_RTOL, atol=PARITY_ATOL,
    )

    def residual_at(*, dT: float = 0.0, dlogw: float = 0.0) -> np.ndarray:
        env = assembler.env
        moved = Environment(
            T=env.T + dT, p=env.p, w=env.w * np.exp(dlogw), F=env.F,
            N_a=env.N_a, Δz=env.Δz, include_evaporation=False,
        )
        return GaussCollocationAssembler(
            assembler.mesh, moved, assembler.phase_reference, assembler.rule,
        ).residual(unknowns)

    h = 1e-6
    lower, upper, spine = np.log(0.01), np.log(0.25), 0.037
    rho_fd = (
        residual_at(dlogw=0.5 * (upper - lower) * h)
        - residual_at(dlogw=-0.5 * (upper - lower) * h)
    ) / (2 * h)
    temperature_fd = (
        residual_at(dT=25 * h, dlogw=25 * spine * h)
        - residual_at(dT=-25 * h, dlogw=-25 * spine * h)
    ) / (2 * h)
    assert np.linalg.norm(output["rho"] - rho_fd) / max(1, np.linalg.norm(output["rho"])) < 1e-6
    assert np.linalg.norm(output["temperature_hat"] - temperature_fd) / max(
        1, np.linalg.norm(output["temperature_hat"])
    ) < 1e-6


def test_cpp_correction_artifact_is_current_and_complete():
    environment = {**os.environ, "BS2026_MIDPOINT_EXECUTABLE": str(executable())}
    subprocess.run(["uv", "run", "python", str(CORRECTION_GENERATOR), "--check"], cwd=ROOT,
                   env=environment, check=True)
    data = json.loads(CORRECTION_RESULTS.read_text())
    assert data["schema_version"] == "episode008-cpp-gauss-correction-results-v1"
    assert len(data["cases"]) == 9
    accepted = [case for case in data["cases"] if case["upstream_status"] == "accepted"]
    assert len(accepted) == 6
    for case in accepted:
        assert case["accepted"]
        assert case["linear"]["backend"] == "KLU2"
        assert min(case["linear"]["symbolic_factorizations"], case["linear"]["numeric_factorizations"],
                   case["linear"]["solves"]) > 0
        assert case["period_relative_difference"] <= 1e-8
        assert case["phase_aligned_weighted_orbit_distance"] <= 1e-8
    statuses = {case["upstream_status"]: case for case in data["cases"] if case["upstream_status"] != "accepted"}
    assert statuses["rejected"]["rejection_reasons"] == ["upstream_fixture_rejected"]
    assert statuses["nonsolution"]["rejection_reasons"] == ["fixture_not_correction_input"]


@pytest.mark.parametrize(("case", "n", "r"), [("canonical-g2-n64", 64, 2), ("canonical-g3-n32", 32, 3)])
def test_generic_layout_graph_dimensions_counts_wraparound_and_reuse(case: str, n: int, r: int):
    output = run("evaluate", case)
    size = 3*n*(r+1)+1
    assert tuple(map(int, output["layout"])) == (n, size, 0, 3*n, size-1, size-1)
    assert output["graph_reused"] == ["true"]
    assert tuple(map(int, output["graph"])) == (9*n*(r+1)**2, size)
    rows = output["rows"]
    assert all(len(rows[row]) == 3*r+2 for row in range(3*n*r))
    assert all(len(rows[row]) == 3*r+3 for row in range(3*n*r, 3*n*(r+1)))
    assert len(rows[size-1]) == 3*n*r
    last_update = 3*n*r + 3*(n-1)
    assert 0 in rows[last_update] and size-1 in rows[last_update]


@pytest.mark.parametrize("case", ["canonical-g2-n64", "canonical-g3-n32", "canonical-g3-n64",
                                   "guard-rho-0-g3-n32", "guard-rho-minus-0.15-g3-n32",
                                   "guard-rho-plus-0.15-g3-n32"])
def test_required_nox_klu2_corrections_match_python_fixed_mesh(case: str):
    output = run("solve", case)
    assembler, python_solution = python_case(case)
    solution = output["solution"]
    assert output["upstream_status"] == ["accepted"]
    assert output["nox"][0] == "converged"
    assert output["linear"][:2] == ["KLU2", "reported"]
    assert all(int(value) > 0 for value in output["linear"][2:5])
    assert output["linear"][5:] == ["true", "true", "true"]
    assert output["accepted"] == ["true"]
    period_relative = abs(np.exp(solution[-1]) - np.exp(python_solution[-1])) / np.exp(python_solution[-1])
    comparison = assembler.compare_with_collocation(solution, assembler, python_solution)
    assert period_relative <= 1e-8
    assert comparison.distance <= 1e-8


def test_nonsolution_is_not_mislabeled_as_upstream_rejection():
    output = run("solve", "canonical-g3-n64-nonsolution")
    assert output["upstream_status"] == ["nonsolution"]
    assert output["accepted"] == ["false"]
    assert output["rejection_reasons"] == ["1", "fixture_not_correction_input"]
    assert "nox" not in output and "linear" not in output
    assert output["build_identity"] and len(output["source_fingerprint"]) == 6


def test_upstream_rejection_is_propagated_without_running_nox():
    output = run("solve", "canonical-g3-n16")
    assert output["upstream_status"] == ["rejected"]
    assert output["accepted"] == ["false"]
    assert output["rejection_reasons"] == ["1", "upstream_fixture_rejected"]
    assert "nox" not in output and "linear" not in output
    assert output["rule"][3] == "f47a6f789fa463abdfdb8d0b158a78bd228bbe85881199d601d086f49396ba6a"
    assert output["build_identity"] and len(output["source_fingerprint"]) == 6


@pytest.mark.parametrize(("field", "bad", "message"), [
    (4, "5", "formal order"),
    (5, "mystery", "upstream status"),
    (6, "0" * 64, "coefficient checksum"),
])
def test_stale_or_malformed_fixture_metadata_is_rejected(tmp_path: Path, field: int, bad: str, message: str):
    tokens = (FIXTURES / "canonical-g3-n32.txt").read_text().split()
    tokens[field] = bad
    fixture = tmp_path / "malformed.txt"
    fixture.write_text(" ".join(tokens) + "\n")
    completed = subprocess.run([str(executable()), "evaluate", str(fixture)], cwd=ROOT,
                               text=True, capture_output=True)
    assert completed.returncode == 2
    assert message in completed.stderr


def test_overflow_period_solve_returns_stable_rejection(tmp_path: Path):
    case = "canonical-g3-n32"
    assembler, _ = python_case(case)
    tokens = (FIXTURES / f"{case}.txt").read_text().split()
    tokens[-1] = "710"
    fixture = tmp_path / "overflow.txt"
    fixture.write_text(" ".join(tokens) + "\n")
    completed = subprocess.run([str(executable()), "solve", str(fixture)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    assert "nox not_converged" in completed.stdout
    assert "accepted false" in completed.stdout
    assert "nox_not_converged" in completed.stdout
    assert "block_residual_tolerance" in completed.stdout
    assert "linear_solve_diagnostics" in completed.stdout
    assert f"solution {assembler.layout.unknown_size}" in completed.stdout
    assert "final_residual_available false" in completed.stdout
    assert "final_residual " not in completed.stdout


def test_exact_solution_linear_failure_is_stably_rejected_without_throwing(tmp_path: Path):
    case = "canonical-g3-n32"
    assembler, exact = python_case(case)
    tokens = (FIXTURES / f"{case}.txt").read_text().split()
    tokens[-assembler.layout.unknown_size:] = [format(value, ".17g") for value in exact]
    fixture = tmp_path / "exact.txt"
    fixture.write_text(" ".join(tokens) + "\n")
    completed = subprocess.run([str(executable()), "solve", str(fixture)], cwd=ROOT,
                               text=True, capture_output=True, check=True)
    assert "nox converged 0" in completed.stdout
    assert "linear unreported unreported 0 0 0 false false false" in completed.stdout
    assert "accepted false" in completed.stdout
    assert "nox_not_converged" not in completed.stdout
    assert "linear_solve_diagnostics" in completed.stdout


def test_fixture_trailing_data_is_rejected(tmp_path: Path):
    fixture = tmp_path / "trailing.txt"
    fixture.write_text((FIXTURES / "canonical-g3-n32.txt").read_text() + "unexpected\n")
    completed = subprocess.run([str(executable()), "evaluate", str(fixture)], cwd=ROOT,
                               text=True, capture_output=True)
    assert completed.returncode == 2
    assert "trailing data" in completed.stderr


def test_higher_order_layout_is_accepted_by_native_loca_without_extra_base_row():
    output = run("loca-contract", "canonical-g3-n32")
    assert output["loca_contract"][0] == "native-loca-gauss-fixed-mesh-pseudo-arclength-v1"
    assert tuple(map(int, output["loca_contract"][1:])) == (1, 1, 385, 386, 384, 384)
    assert output["loca_method"][:6] == [
        "Arc_Length", "native_stepper", "true", "base_has_arclength", "false", "metric",
    ]
