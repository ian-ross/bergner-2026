from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    FixedMesh,
    FrozenPhaseReference,
    MidpointCollocationAssembler,
    MidpointResidualTolerances,
    PeriodicHermiteSeed,
    correct_midpoint_orbit,
    gauss_legendre_rule,
)
from bergner_spichtinger_2026.constants import Environment


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SEED_PATH = EPISODE_ROOT / "outputs/bootstrap_seed.json"
RESULTS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_results.json"
VECTORS_PATH = EPISODE_ROOT / "outputs/fixed_mesh_midpoint_vectors.npz"
SCRIPT_DIR = EPISODE_ROOT / "scripts"


def _case(interval_count: int) -> tuple[PeriodicHermiteSeed, MidpointCollocationAssembler, np.ndarray]:
    mapping = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    parameters = mapping["canonical_parameters"]
    env = Environment(
        T=parameters["T"],
        p=parameters["p"],
        w=parameters["w"],
        F=parameters["F"],
        N_a=parameters["N_a"],
        Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )
    seed = PeriodicHermiteSeed.from_json(SEED_PATH)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    mesh = FixedMesh.uniform(interval_count)
    rule = gauss_legendre_rule(1)
    reference = FrozenPhaseReference.from_evaluator(
        mesh,
        rule,
        seed.evaluate,
        seed.derivative,
        state_scaling=scaling,
    )
    assembler = MidpointCollocationAssembler(mesh, env, reference)
    initial = assembler.reference_unknowns(seed.evaluate, seed.log_period)
    return seed, assembler, initial


def _fake_solution(x: np.ndarray, *, success: bool) -> SimpleNamespace:
    return SimpleNamespace(
        x=x,
        success=success,
        status=1 if success else 0,
        message="controlled test result",
        cost=0.0,
        optimality=0.0,
        nfev=1,
        njev=1,
    )


def test_n64_sparse_trf_correction_meets_every_independent_block_gate():
    seed, assembler, initial = _case(64)
    result = correct_midpoint_orbit(assembler, initial)

    assert result.accepted
    assert result.scipy_success
    assert result.rejection_reasons == ()
    assert result.function_evaluations > 0
    assert result.jacobian_evaluations is not None and result.jacobian_evaluations > 0
    assert result.diagnostics.stage_max < 1.0e-9
    assert result.diagnostics.stage_rms < 1.0e-9
    assert result.diagnostics.update_max < 1.0e-9
    assert result.diagnostics.update_rms < 1.0e-9
    assert result.diagnostics.phase_abs < 1.0e-10
    assert np.exp(result.unknowns[-1]) == pytest.approx(2768.508882009953)
    assert assembler.weighted_orbit_distance(result.unknowns, initial) == pytest.approx(
        0.172603283762154
    )
    comparison = assembler.compare_with_reference(result.unknowns, seed.evaluate, seed.log_period)
    assert comparison.distance == pytest.approx(0.17260271954440481)


def test_scipy_failure_is_rejected_even_when_all_block_tolerances_pass(monkeypatch: pytest.MonkeyPatch):
    _, assembler, _ = _case(64)
    with np.load(VECTORS_PATH, allow_pickle=False) as vectors:
        accepted_unknowns = vectors["n64_unknowns"].copy()
    module = importlib.import_module("bergner_spichtinger_2026.periodic_orbits")
    monkeypatch.setattr(
        module,
        "least_squares",
        lambda *args, **kwargs: _fake_solution(accepted_unknowns, success=False),
    )

    result = correct_midpoint_orbit(assembler, accepted_unknowns)

    assert not result.accepted
    assert result.rejection_reasons == ("scipy_unsuccessful",)
    assert result.diagnostics.stage_max < 1.0e-9
    assert result.diagnostics.update_max < 1.0e-9
    assert result.diagnostics.phase_abs < 1.0e-10


def test_nominal_scipy_success_is_rejected_when_residual_blocks_miss_tolerances(
    monkeypatch: pytest.MonkeyPatch,
):
    _, assembler, initial = _case(64)
    module = importlib.import_module("bergner_spichtinger_2026.periodic_orbits")
    monkeypatch.setattr(
        module,
        "least_squares",
        lambda *args, **kwargs: _fake_solution(initial, success=True),
    )

    result = correct_midpoint_orbit(assembler, initial)

    assert result.scipy_success
    assert not result.accepted
    assert "stage_max_tolerance" in result.rejection_reasons
    assert "update_max_tolerance" in result.rejection_reasons
    assert "scipy_unsuccessful" not in result.rejection_reasons


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (lambda x: x.__setitem__(0, np.nan), "nonfinite_unknowns"),
        (lambda x: x.__setitem__(-1, 1000.0), "nonpositive_or_nonfinite_period"),
    ],
)
def test_malformed_scipy_vectors_return_structured_rejection_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    mutation,
    expected_reason: str,
):
    _, assembler, initial = _case(64)
    malformed = initial.copy()
    mutation(malformed)
    module = importlib.import_module("bergner_spichtinger_2026.periodic_orbits")
    monkeypatch.setattr(
        module,
        "least_squares",
        lambda *args, **kwargs: _fake_solution(malformed, success=True),
    )

    result = correct_midpoint_orbit(assembler, initial)

    assert not result.accepted
    assert expected_reason in result.rejection_reasons
    assert "residual_unavailable" in result.rejection_reasons
    assert "nonfinite_residual" in result.rejection_reasons
    assert "stage_max_tolerance" in result.rejection_reasons
    assert np.isnan(result.residual).all()
    assert np.isnan(result.diagnostics.phase_abs)


def test_rms_and_phase_gates_independently_reject_nominal_scipy_success(
    monkeypatch: pytest.MonkeyPatch,
):
    _, assembler, _ = _case(64)
    with np.load(VECTORS_PATH, allow_pickle=False) as vectors:
        accepted_unknowns = vectors["n64_unknowns"].copy()
    module = importlib.import_module("bergner_spichtinger_2026.periodic_orbits")
    monkeypatch.setattr(
        module,
        "least_squares",
        lambda *args, **kwargs: _fake_solution(accepted_unknowns, success=True),
    )

    rms_only = correct_midpoint_orbit(
        assembler,
        accepted_unknowns,
        tolerances=MidpointResidualTolerances(
            stage_max=1.0,
            stage_rms=1.0e-20,
            update_max=1.0,
            update_rms=1.0,
            phase_abs=1.0,
        ),
    )
    phase_only = correct_midpoint_orbit(
        assembler,
        accepted_unknowns,
        tolerances=MidpointResidualTolerances(
            stage_max=1.0,
            stage_rms=1.0,
            update_max=1.0,
            update_rms=1.0,
            phase_abs=1.0e-20,
        ),
    )

    assert rms_only.rejection_reasons == ("stage_rms_tolerance",)
    assert phase_only.rejection_reasons == ("phase_tolerance",)


def test_tolerance_contract_rejects_nonpositive_or_nonfinite_values():
    with pytest.raises(ValueError, match="positive and finite"):
        MidpointResidualTolerances(stage_max=0.0)
    with pytest.raises(ValueError, match="positive and finite"):
        MidpointResidualTolerances(phase_abs=np.inf)


def test_curated_results_cover_all_meshes_and_separate_accuracy_from_residuals():
    mapping = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    results = mapping["results"]

    assert mapping["scientific_scope"]["production_accuracy_claimed"] is False
    assert set(mapping["runtime_provenance"]) == {"python", "numpy", "scipy"}
    assert set(mapping["source_provenance"]) == {
        "generator_path",
        "generator_sha256",
        "periodic_orbits_path",
        "periodic_orbits_sha256",
    }
    assert "does not establish" in mapping["scientific_scope"]["accuracy_warning"]
    assert [record["interval_count"] for record in results] == [32, 64, 128, 256]
    assert not results[0]["accepted"]
    assert all(record["accepted"] for record in results[1:])
    required = {
        "period_s",
        "weighted_orbit_correction_from_seed",
        "weighted_orbit_error_vs_episode007",
        "stage_residual_max",
        "stage_residual_rms",
        "update_residual_max",
        "update_residual_rms",
        "phase_residual_abs",
        "phase_energy",
        "function_evaluations",
        "jacobian_evaluations",
        "scipy_status",
        "rejection_reasons",
    }
    assert all(required <= set(record) for record in results)
    accepted_period_errors = [record["period_relative_error_vs_episode007"] for record in results[1:]]
    accepted_orbit_errors = [record["weighted_orbit_error_vs_episode007"] for record in results[1:]]
    assert accepted_period_errors[0] > accepted_period_errors[1] > accepted_period_errors[2]
    assert accepted_orbit_errors[0] > accepted_orbit_errors[1] > accepted_orbit_errors[2]
    assert results[1]["stage_residual_max"] < 1.0e-9
    assert results[1]["period_relative_error_vs_episode007"] > 0.1


def test_frozen_vectors_have_documented_shapes_checksums_and_recomputed_residuals():
    mapping = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    manifest = mapping["vector_artifact"]["arrays"]
    with np.load(VECTORS_PATH, allow_pickle=False) as vectors:
        assert set(vectors.files) == set(manifest)
        for interval_count in (32, 64, 128, 256):
            key = f"n{interval_count}"
            assert vectors[f"{key}_unknowns"].shape == (6 * interval_count + 1,)
            assert vectors[f"{key}_residual"].shape == (6 * interval_count + 1,)
            _, assembler, _ = _case(interval_count)
            np.testing.assert_array_equal(
                assembler.residual(vectors[f"{key}_unknowns"]),
                vectors[f"{key}_residual"],
            )
            assert manifest[f"{key}_unknowns"]["shape"] == [6 * interval_count + 1]

        _, assembler, _ = _case(64)
        nonsolution = vectors["n64_nonsolution_unknowns"]
        nonsolution_residual = vectors["n64_nonsolution_residual"]
        np.testing.assert_array_equal(assembler.residual(nonsolution), nonsolution_residual)
        blocks = assembler.layout.unpack_residual(nonsolution_residual)
        assert np.all(np.linalg.norm(blocks.stages[:, 0], axis=1) > 0.0)
        assert np.all(np.linalg.norm(blocks.updates, axis=1) > 0.0)
        assert abs(blocks.phase) > 0.0
        assert np.max(np.abs(nonsolution_residual)) > 1.0e-5


def test_fixed_mesh_result_generator_rebuilds_committed_outputs_exactly():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        generator = importlib.import_module("generate_fixed_mesh_midpoint_results")
    finally:
        sys.path.remove(str(SCRIPT_DIR))
    generator.generate(check=True)
    mapping, arrays = generator.build_outputs()
    expected_npz = generator._npz_bytes(arrays)
    mapping["vector_artifact"]["file_sha256"] = generator._bytes_sha256(expected_npz)

    assert generator._canonical_json(mapping) == RESULTS_PATH.read_bytes()
    assert expected_npz == VECTORS_PATH.read_bytes()
    with np.load(VECTORS_PATH, allow_pickle=False) as frozen:
        assert set(frozen.files) == set(arrays)
        for key, expected in arrays.items():
            np.testing.assert_array_equal(frozen[key], expected)


def test_generator_check_detects_npz_byte_drift_without_rewriting(
    monkeypatch: pytest.MonkeyPatch,
):
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        generator = importlib.import_module("generate_fixed_mesh_midpoint_results")
    finally:
        sys.path.remove(str(SCRIPT_DIR))
    copied_results = REPO_ROOT / ".tmp-task056-results.json"
    copied_vectors = REPO_ROOT / ".tmp-task056-vectors.npz"
    copied_results.write_bytes(RESULTS_PATH.read_bytes())
    copied_vectors.write_bytes(VECTORS_PATH.read_bytes() + b"drift")
    before = copied_vectors.read_bytes()
    monkeypatch.setattr(generator, "RESULTS_PATH", copied_results)
    monkeypatch.setattr(generator, "VECTORS_PATH", copied_vectors)

    try:
        with pytest.raises(SystemExit, match="byte drift"):
            generator.generate(check=True)
        assert copied_vectors.read_bytes() == before
    finally:
        copied_results.unlink(missing_ok=True)
        copied_vectors.unlink(missing_ok=True)
