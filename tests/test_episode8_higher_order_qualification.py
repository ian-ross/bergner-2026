from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026 import (
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    gauss_legendre_rule,
    sha256_file,
)
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import coefficients

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
RESULTS = EPISODE / "outputs/higher_order_fixed_mesh_qualification.json"
VECTORS = EPISODE / "outputs/higher_order_fixed_mesh_qualification_vectors.npz"
FIXTURES = EPISODE / "outputs/higher_order_parity_fixtures"
SCRIPT = EPISODE / "scripts"


def _array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype="<f8").tobytes()).hexdigest()


def _environment(record: dict[str, object]) -> Environment:
    return Environment(
        T=float(record["temperature_K"]),
        p=float(record["pressure_Pa"]),
        w=float(record["vertical_velocity_m_s"]),
        F=float(record["sedimentation_factor"]),
        N_a=float(record["aerosol_number_m^-3"]),
        Δz=float(record["column_depth_m"]),
        include_evaporation=bool(record["include_evaporation"]),
    )


def test_qualification_contains_exact_ladders_lineage_decisions_and_independent_ivp():
    data = json.loads(RESULTS.read_text())
    ids = {item["case_id"] for item in data["results"]}
    canonical = (
        {f"canonical-g1-n{n}" for n in (64, 128, 256)}
        | {f"canonical-g2-n{n}" for n in (32, 64, 128)}
        | {f"canonical-g3-n{n}" for n in (16, 32, 64)}
    )
    guards = {
        f"guard-rho-{rho}-g{stage}-n{n}"
        for rho in ("0", "minus-0.15", "plus-0.15")
        for stage, counts in ((2, (64, 128)), (3, (32, 64)))
        for n in counts
    }
    assert ids == canonical | guards
    rejected = [item for item in data["results"] if not item["nonlinear_accepted"]]
    assert [item["case_id"] for item in rejected] == ["canonical-g3-n16"]
    assert rejected[0]["nonlinear_terminal_reason"] == "nonlinear_rejected"
    assert all(item["accepted_semantics"] == "nonlinear_discrete_solution_only" for item in data["results"])
    assert data["summary"]["qualified_case_count"] == 0
    assert not data["summary"]["fixed_uniform_mesh_qualified"]
    assert all(not item["qualification"]["qualified"] for item in data["results"])
    assert all(item["qualification"]["version"] == data["qualification_version"] for item in data["results"])

    records = {item["case_id"]: item for item in data["results"]}
    first_guards = [
        records[f"guard-rho-{rho}-g{stage}-n{n}"]
        for rho in ("0", "minus-0.15", "plus-0.15")
        for stage, n in ((2, 64), (3, 32))
    ]
    assert all(item["seed_lineage"]["kind"] == "exact_TASK_061_target_midpoint_polynomial" for item in first_guards)
    for rho in ("0", "minus-0.15", "plus-0.15"):
        assert records[f"guard-rho-{rho}-g2-n128"]["seed_lineage"]["parent_case_id"] == f"guard-rho-{rho}-g2-n64"
        assert records[f"guard-rho-{rho}-g3-n64"]["seed_lineage"]["parent_case_id"] == f"guard-rho-{rho}-g3-n32"

    assert len(data["same_rule_refinement"]) == 12
    assert all(item["terminal_reason"] in {"compared", "rejected_case_in_pair"} for item in data["same_rule_refinement"])
    assert len(data["cross_order_evidence"]) == 5
    assert all(item["terminal_reason"] == "compared" for item in data["cross_order_evidence"])

    ivp = data["canonical_ivp"]
    assert ivp["version"] == "canonical-dop853-saturation-max-period-v2"
    assert ivp["accepted"]
    assert ivp["first_maximum_time_s"] < ivp["second_maximum_time_s"]
    assert ivp["ivp_derived_period_s"] == pytest.approx(
        ivp["second_maximum_time_s"] - ivp["first_maximum_time_s"], rel=0, abs=1e-12
    )
    assert ivp["period_relative_difference"] < 1e-3
    assert ivp["weighted_return_error"] < 1e-3
    assert ivp["phase_aligned_weighted_dense_orbit_error"] < 1e-3


def test_all_comparisons_recompute_from_curated_vectors():
    data = json.loads(RESULTS.read_text())
    records = {item["case_id"]: item for item in data["results"]}
    seed = json.loads((EPISODE / "outputs/bootstrap_seed.json").read_text())
    parameters = seed["canonical_parameters"]
    midpoint = json.loads((EPISODE / "outputs/fixed_mesh_midpoint_results.json").read_text())
    scaling = np.asarray(midpoint["state_scaling"])

    with np.load(VECTORS, allow_pickle=False) as arrays, np.load(
        EPISODE / "outputs/fixed_mesh_midpoint_vectors.npz", allow_pickle=False
    ) as midpoint_arrays:
        def build(case_id: str) -> tuple[GaussCollocationAssembler, np.ndarray]:
            record = records[case_id]
            stage = record["stage_count"]
            n = record["interval_count"]
            if stage == 1:
                boundaries = midpoint_arrays[f"n{n}_boundaries"]
                unknowns = midpoint_arrays[f"n{n}_unknowns"]
                values = midpoint_arrays[f"n{n}_phase_reference_values"]
                derivatives = midpoint_arrays[f"n{n}_phase_reference_derivatives"]
            else:
                boundaries = arrays[case_id + "__boundaries"]
                unknowns = arrays[case_id + "__unknowns"]
                values = arrays[case_id + "__phase_values"]
                derivatives = arrays[case_id + "__phase_derivatives"]
            env = Environment(
                T=float(record.get("temperature_K", parameters["T"])),
                p=parameters["p"],
                w=float(record.get("w_m_s", parameters["w"])),
                F=parameters["F"],
                N_a=parameters["N_a"],
                Δz=parameters["Delta_z"],
                include_evaporation=False,
            )
            mesh = FixedMesh(boundaries)
            rule = gauss_legendre_rule(stage)
            reference = FrozenPhaseReference(
                mesh, values, derivatives, scaling,
                np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
            )
            return GaussCollocationAssembler(mesh, env, reference, rule), unknowns

        for comparison in data["same_rule_refinement"]:
            if not comparison["available"]:
                assert comparison["terminal_reason"] == "rejected_case_in_pair"
                continue
            coarse_a, coarse_x = build(comparison["coarse_case_id"])
            fine_a, fine_x = build(comparison["fine_case_id"])
            coarse_period = records[comparison["coarse_case_id"]]["period_s"]
            fine_period = records[comparison["fine_case_id"]]["period_s"]
            expected_period = abs(fine_period - coarse_period) / abs(fine_period)
            expected_orbit = fine_a.compare_with_collocation(fine_x, coarse_a, coarse_x).distance
            assert comparison["period_relative_change"] == pytest.approx(expected_period, rel=2e-13)
            assert comparison["weighted_orbit_change"] == pytest.approx(expected_orbit, rel=2e-12)

        for comparison in data["cross_order_evidence"]:
            lower_a, lower_x = build(comparison["lower_order_case_id"])
            higher_a, higher_x = build(comparison["higher_order_case_id"])
            expected = higher_a.compare_with_collocation(higher_x, lower_a, lower_x).distance
            assert comparison["weighted_orbit_difference"] == pytest.approx(expected, rel=2e-12)


def test_defect_serialization_is_full_and_material_decisions_recompute():
    data = json.loads(RESULTS.read_text())
    for record in data["results"]:
        defect = record["defect"]
        n = record["interval_count"]
        for key in (
            "combined_element_maxima",
            "grid_disagreement",
            "endpoint_left",
            "endpoint_right",
            "derivative_jumps",
            "probe_admitted",
            "admitted_probe_element_maxima",
        ):
            assert len(defect[key]) == n
        next_max = np.max(np.asarray(defect["next_gauss"]["relative_defects"]), axis=1)
        dyadic_max = np.max(np.asarray(defect["staggered_dyadic"]["relative_defects"]), axis=1)
        larger = np.maximum(next_max, dyadic_max)
        disagreement = np.divide(
            np.abs(next_max - dyadic_max), larger,
            out=np.zeros_like(larger), where=larger > 0,
        )
        material = np.flatnonzero((larger > 1e-5) & (disagreement > 0.5))
        assert defect["materially_disagreeing_elements"] == material.tolist()
        np.testing.assert_allclose(defect["grid_disagreement"], disagreement, rtol=0, atol=1e-15)
        admitted = np.asarray(defect["probe_admitted"], dtype=bool)
        np.testing.assert_array_equal(np.flatnonzero(admitted), material)
        assert defect["maximum"] == pytest.approx(max(defect["combined_element_maxima"]))


def test_source_provenance_hashes_every_direct_input():
    data = json.loads(RESULTS.read_text())
    expected = {
        "generator",
        "periodic_orbits",
        "collocation_coefficients",
        "bootstrap_seed",
        "task056_midpoint_results",
        "task056_midpoint_vectors",
        "task061_continuation_results",
        "task061_continuation_vectors",
        "uv_lock",
    }
    assert set(data["source_provenance"]) == expected
    for value in data["source_provenance"].values():
        path = ROOT / value["path"]
        assert sha256_file(path) == value["sha256"]


def test_vector_checksums_and_representative_residual_recompute():
    data = json.loads(RESULTS.read_text())
    manifest = data["vector_artifact"]["arrays"]
    with np.load(VECTORS, allow_pickle=False) as arrays:
        assert set(arrays.files) == set(manifest)
        for key, spec in manifest.items():
            assert _array_hash(arrays[key]) == spec["sha256"]
            assert list(arrays[key].shape) == spec["shape"]
        case = "canonical-g3-n64"
        seed = json.loads((EPISODE / "outputs/bootstrap_seed.json").read_text())
        parameters = seed["canonical_parameters"]
        env = Environment(
            T=parameters["T"], p=parameters["p"], w=parameters["w"],
            F=parameters["F"], N_a=parameters["N_a"], Δz=parameters["Delta_z"],
            include_evaporation=False,
        )
        mesh = FixedMesh(arrays[case + "__boundaries"])
        rule = gauss_legendre_rule(3)
        scaling = np.asarray(json.loads((EPISODE / "outputs/fixed_mesh_midpoint_results.json").read_text())["state_scaling"])
        reference = FrozenPhaseReference(
            mesh, arrays[case + "__phase_values"], arrays[case + "__phase_derivatives"],
            scaling, np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
        )
        assembler = GaussCollocationAssembler(mesh, env, reference, rule)
        np.testing.assert_array_equal(
            assembler.residual(arrays[case + "__unknowns"]), arrays[case + "__residual"]
        )


def test_language_neutral_fixtures_recompute_all_blocks_and_checksums():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    assert manifest["schema_version"] == "episode008-gauss-parity-v1"
    assert {item["case_id"] for item in manifest["cases"]} == {
        "g2-n64-converged", "g2-n64-nonsolution", "g3-n64-converged", "g3-n64-nonsolution"
    }
    for record in manifest["cases"]:
        body = (FIXTURES / record["path"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == record["sha256"]
        case = json.loads(body)
        arrays = {key: np.asarray(value, dtype=float) for key, value in case["arrays"].items()}
        for key, value in arrays.items():
            assert _array_hash(value) == case["array_schema"][key]["sha256"]
            assert list(value.shape) == case["array_schema"][key]["shape"]
            assert record["array_checksums"][key] == case["array_schema"][key]["sha256"]
        env = _environment(case["environment"])
        contract = case["model_contract"]
        assert contract["identifier"] == "bergner-spichtinger-2026-no-evaporation-transformed-v1"
        assert contract["process_terms"]["Evap_n"] == "0"
        assert contract["transformed_state"]["vector_field"] == [
            "g_1 = (dn/dt)/n", "g_2 = (dq/dt)/q", "g_3 = ds/dt"
        ]
        assert contract["environment_conventions"]["include_evaporation"] is False
        expected_coefficients = coefficients(env)
        expected_values = {
            "rho_air": expected_coefficients.ρ, "D": expected_coefficients.D,
            "p_si": expected_coefficients.p_si, "p1e": expected_coefficients.p1e,
            "p2": expected_coefficients.p2, "A_n": expected_coefficients.A_n,
            "A_q": expected_coefficients.A_q, "A_s": expected_coefficients.A_s,
            "B_q": expected_coefficients.B_q, "B_s": expected_coefficients.B_s,
            "C_n": expected_coefficients.C_n, "C_q": expected_coefficients.C_q,
        }
        assert case["coefficient_values"] == expected_values
        assert case["orbit_coordinate_contract"]["period_coordinate"] == "natural_log(period_s)"
        rule = gauss_legendre_rule(case["rule"]["stage_count"])
        mesh = FixedMesh(arrays["mesh_boundaries"])
        reference = FrozenPhaseReference(
            mesh, arrays["phase_reference_values"], arrays["phase_reference_derivatives"],
            np.asarray(case["state_scaling"]), np.asarray(rule.nodes), np.asarray(rule.quadrature_weights),
        )
        assembler = GaussCollocationAssembler(mesh, env, reference, rule)
        blocks = assembler.residual_blocks(arrays["unknowns"])
        np.testing.assert_array_equal(blocks.stages, arrays["residual_stages"])
        np.testing.assert_array_equal(blocks.updates, arrays["residual_updates"])
        np.testing.assert_array_equal(np.asarray([blocks.phase]), arrays["residual_phase"])
        if case["meaning"] == "nonsolution":
            assert np.max(np.abs(assembler.residual(arrays["unknowns"]))) > 1e-5


def test_generator_check_regenerates_every_artifact_deterministically():
    sys.path.insert(0, str(SCRIPT))
    try:
        generator = importlib.import_module("generate_higher_order_fixed_mesh_qualification")
    finally:
        sys.path.remove(str(SCRIPT))
    generator.generate(check=True)
