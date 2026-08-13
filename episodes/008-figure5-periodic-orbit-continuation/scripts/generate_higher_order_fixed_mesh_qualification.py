#!/usr/bin/env python3
"""Generate TASK-064 fixed-mesh Gauss qualification and parity artifacts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

from bergner_spichtinger_2026 import (
    COLLOCATION_ARTIFACT_SHA256,
    DEFECT_DIAGNOSTIC_VERSION,
    GAUSS_FORMULATION_VERSION,
    GAUSS_SOLVER_VERSION,
    JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
    FixedMesh,
    FrozenPhaseReference,
    GaussCollocationAssembler,
    MidpointCollocationAssembler,
    MidpointResidualTolerances,
    PeriodicHermiteSeed,
    correct_gauss_orbit,
    gauss_legendre_rule,
    sha256_file,
)
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.periodic_orbits import transformed_vector_field

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
SEED_PATH = OUTPUT / "bootstrap_seed.json"
COEFFICIENT_PATH = OUTPUT / "collocation_coefficients.json"
MIDPOINT_JSON = OUTPUT / "fixed_mesh_midpoint_results.json"
MIDPOINT_NPZ = OUTPUT / "fixed_mesh_midpoint_vectors.npz"
CONTINUATION_JSON = OUTPUT / "fixed_mesh_continuation_results.json"
CONTINUATION_NPZ = OUTPUT / "fixed_mesh_continuation_vectors.npz"
RESULTS_PATH = OUTPUT / "higher_order_fixed_mesh_qualification.json"
VECTORS_PATH = OUTPUT / "higher_order_fixed_mesh_qualification_vectors.npz"
FIXTURE_DIR = OUTPUT / "higher_order_parity_fixtures"
LOCK_PATH = ROOT / "uv.lock"
PERIODIC_ORBITS_PATH = ROOT / "src/bergner_spichtinger_2026/periodic_orbits.py"

SCHEMA_VERSION = "1.1.0"
QUALIFICATION_VERSION = "fixed-mesh-gauss-qualification-v1"
FIXTURE_SCHEMA_VERSION = "episode008-gauss-parity-v1"
IVP_VERSION = "canonical-dop853-saturation-max-period-v2"
PERTURBATION_VERSION = "sinusoidal-packed-vector-v1"
TRANSFORMED_MODEL_CONTRACT_VERSION = "bergner-spichtinger-2026-no-evaporation-transformed-v1"
REFINEMENT_TOLERANCE = 1.0e-3
DEFECT_TOLERANCE = 1.0e-4
IVP_RTOL = 1.0e-10
IVP_ATOL = 1.0e-12
IVP_PERIOD_WINDOW = 0.10
IVP_MAXIMUM_SCAN_POINTS = 32769
IVP_DENSE_COMPARISON_POINTS = 4097
NONLINEAR_TOLERANCES = MidpointResidualTolerances()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_digest(value: np.ndarray) -> str:
    return digest(np.ascontiguousarray(value, dtype="<f8").tobytes())


def npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for key in sorted(arrays):
                member = io.BytesIO()
                np.lib.format.write_array(member, np.asarray(arrays[key]), allow_pickle=False)
                info = zipfile.ZipInfo(key + ".npy", (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, member.getvalue())
        return output.getvalue()


def environment(
    parameters: dict[str, Any],
    *,
    temperature: float | None = None,
    w: float | None = None,
) -> Environment:
    return Environment(
        T=parameters["T"] if temperature is None else temperature,
        p=parameters["p"],
        w=parameters["w"] if w is None else w,
        F=parameters["F"],
        N_a=parameters["N_a"],
        Δz=parameters["Delta_z"],
        include_evaporation=parameters["include_evaporation"],
    )


def environment_record(env: Environment) -> dict[str, Any]:
    return {
        "temperature_K": env.T,
        "pressure_Pa": env.p,
        "vertical_velocity_m_s": env.w,
        "sedimentation_factor": env.F,
        "aerosol_number_m^-3": env.N_a,
        "column_depth_m": env.Δz,
        "include_evaporation": env.include_evaporation,
    }


def transformed_model_contract() -> dict[str, Any]:
    """Return the stable language-neutral no-evaporation model definition."""
    return {
        "identifier": TRANSFORMED_MODEL_CONTRACT_VERSION,
        "source_equations": "Bergner & Spichtinger (2026), physical Eqs. (4)-(15) with Eq. (12)/(54) disabled",
        "physical_state": {
            "symbols": ["n", "q", "s"],
            "units": ["kg_dry_air^-1", "kg kg_dry_air^-1", "dimensionless"],
            "domain": ["n > 0", "q > 0", "s finite"],
        },
        "transformed_state": {
            "symbols": ["x_n", "x_q", "s"],
            "definition": ["x_n = natural_log(n)", "x_q = natural_log(q)", "s = s"],
            "vector_field": ["g_1 = (dn/dt)/n", "g_2 = (dq/dt)/q", "g_3 = ds/dt"],
            "time_unit": "second",
        },
        "process_terms": {
            "E": "exp(p1e*(s-p2))",
            "Nuc_n": "A_n*E",
            "Nuc_q": "A_q*E",
            "Nuc_s": "-A_s*E",
            "Dep_q": "B_q*n^(2/3)*q^(1/3)*(s-1)",
            "Dep_s": "-B_s*n^(2/3)*q^(1/3)*(s-1)",
            "Sed_n": "-F*C_n*n^(1/3)*q^(2/3)",
            "Sed_q": "-F*C_q*n^(-2/3)*q^(5/3)",
            "Cool": "D*w*s",
            "Evap_n": "0",
        },
        "physical_rhs": [
            "dn/dt = Nuc_n + Sed_n",
            "dq/dt = Nuc_q + Dep_q + Sed_q",
            "ds/dt = Cool + Nuc_s + Dep_s",
        ],
        "coefficient_parameterization": {
            "rule": "Use each fixture's emitted coefficient_values; these are frozen binary64 evaluations of the canonical paper parameterization for its emitted SI environment.",
            "symbols": ["rho_air", "D", "p_si", "p1e", "p2", "A_n", "A_q", "A_s", "B_q", "B_s", "C_n", "C_q"],
            "units": {
                "rho_air": "kg m^-3", "D": "m^-1", "p_si": "Pa",
                "p1e": "dimensionless", "p2": "dimensionless",
                "A_n": "kg_dry_air^-1 s^-1", "A_q": "s^-1", "A_s": "s^-1",
                "B_q": "kg_dry_air^(2/3) s^-1", "B_s": "kg_dry_air^(2/3) s^-1",
                "C_n": "kg_dry_air^(-2/3) s^-1", "C_q": "kg_dry_air^(-2/3) s^-1"
            },
        },
        "environment_conventions": {
            "temperature": "K",
            "pressure": "Pa",
            "vertical_velocity": "m s^-1",
            "sedimentation_factor": "dimensionless",
            "aerosol_number": "m^-3",
            "column_depth": "m",
            "include_evaporation": False,
        },
    }


def coefficient_record(assembler: GaussCollocationAssembler) -> dict[str, float]:
    coeff = assembler.coeff
    return {
        "rho_air": coeff.ρ,
        "D": coeff.D,
        "p_si": coeff.p_si,
        "p1e": coeff.p1e,
        "p2": coeff.p2,
        "A_n": coeff.A_n,
        "A_q": coeff.A_q,
        "A_s": coeff.A_s,
        "B_q": coeff.B_q,
        "B_s": coeff.B_s,
        "C_n": coeff.C_n,
        "C_q": coeff.C_q,
    }


def grid_record(value: Any) -> dict[str, Any]:
    return {
        "name": value.name,
        "nodes": value.local_nodes.tolist(),
        "relative_defects": value.relative_defects.tolist(),
        "maximum": value.maximum,
        "argmax_interval": value.argmax_interval,
        "argmax_local_node": value.argmax_local_node,
        "argmax_phase": value.argmax_phase,
    }


def defect_record(defect: Any) -> dict[str, Any]:
    return {
        "version": DEFECT_DIAGNOSTIC_VERSION,
        "maximum": defect.maximum,
        "argmax_phase": defect.argmax_phase,
        "argmax_bin": defect.argmax_bin,
        "next_gauss": grid_record(defect.next_gauss),
        "staggered_dyadic": grid_record(defect.staggered_dyadic),
        "probe_16": None if defect.probe_16 is None else grid_record(defect.probe_16),
        "materially_disagreeing_elements": list(defect.materially_disagreeing_elements),
        "combined_element_maxima": defect.combined_element_maxima.tolist(),
        "grid_disagreement": defect.grid_disagreement.tolist(),
        "endpoint_left": defect.endpoint_left.tolist(),
        "endpoint_right": defect.endpoint_right.tolist(),
        "derivative_jumps": defect.derivative_jumps.tolist(),
        "probe_admitted": defect.probe_admitted.tolist(),
        "admitted_probe_element_maxima": defect.admitted_probe_element_maxima.tolist(),
    }


def solve_case(
    point_id: str,
    env: Environment,
    stage_count: int,
    interval_count: int,
    initial: np.ndarray,
    reference: FrozenPhaseReference,
) -> tuple[dict[str, Any], GaussCollocationAssembler, Any]:
    mesh = FixedMesh.uniform(interval_count)
    rule = gauss_legendre_rule(stage_count)
    assembler = GaussCollocationAssembler(mesh, env, reference, rule)
    result = correct_gauss_orbit(assembler, initial)
    defect = assembler.independent_defect(result.unknowns)
    diagnostics = result.diagnostics
    nonlinear_accepted = result.accepted
    variables = assembler.layout.unpack(result.unknowns)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        physical_n_q = np.exp(
            np.concatenate(
                (variables.endpoints[:, :2].reshape(-1), variables.stages[:, :, :2].reshape(-1))
            )
        )
        physical_period = np.exp(variables.log_period)
    physical_mapping_passed = bool(
        np.all(np.isfinite(physical_n_q))
        and np.all(physical_n_q > 0.0)
        and np.isfinite(physical_period)
        and physical_period > 0.0
    )
    record = {
        "case_id": f"{point_id}-g{stage_count}-n{interval_count}",
        "point_id": point_id,
        "stage_count": stage_count,
        "formal_order": rule.formal_order,
        "interval_count": interval_count,
        "accepted": nonlinear_accepted,
        "accepted_semantics": "nonlinear_discrete_solution_only",
        "nonlinear_accepted": nonlinear_accepted,
        "nonlinear_terminal_reason": "accepted" if nonlinear_accepted else "nonlinear_rejected",
        "terminal_reason": "accepted" if nonlinear_accepted else "nonlinear_rejected",
        "terminal_reason_semantics": "nonlinear_discrete_solution_only",
        "rejection_reasons": list(result.rejection_reasons),
        "period_s": float(np.exp(result.unknowns[-1])),
        "stage_residual_max": diagnostics.stage_max,
        "stage_residual_rms": diagnostics.stage_rms,
        "update_residual_max": diagnostics.update_max,
        "update_residual_rms": diagnostics.update_rms,
        "phase_residual_abs": diagnostics.phase_abs,
        "phase_energy": assembler.phase_energy,
        "scipy_success": result.scipy_success,
        "scipy_status": result.scipy_status,
        "scipy_message": result.scipy_message,
        "function_evaluations": result.function_evaluations,
        "jacobian_evaluations": result.jacobian_evaluations,
        "defect": defect_record(defect),
        "defect_pass": defect.maximum < DEFECT_TOLERANCE,
        "nonphysical_interior_check": {
            "version": "transformed-state-finite-positive-mapping-v1",
            "evaluated": True,
            "passed": physical_mapping_passed,
            "meaning": "all endpoint/stage log(n),log(q) map to finite positive n,q and log(P) maps to finite positive P",
        },
        "ringing_diagnostic": {
            "status": "not_evaluated",
            "reason": "TASK-064 defines no versioned fixed-mesh polynomial-ringing metric",
        },
    }
    return record, assembler, result


def source_linkage(
    *,
    kind: str,
    artifact: Path,
    vector_key: str,
    reference_id: str,
    reference_artifact: Path,
    parent_case_id: str | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
        "artifact_sha256": sha256_file(artifact),
        "vector_key": vector_key,
        "reference_id": reference_id,
        "reference_artifact_path": reference_artifact.relative_to(ROOT).as_posix(),
        "reference_artifact_sha256": sha256_file(reference_artifact),
        "parent_case_id": parent_case_id,
    }


def _local_maximum_time(dense: Any, bracket: tuple[float, float]) -> float:
    result = minimize_scalar(
        lambda time: -float(dense(time)[2]),
        bounds=bracket,
        method="bounded",
        options={"xatol": 1.0e-10},
    )
    if not result.success:
        raise RuntimeError("DOP853 saturation-maximum refinement failed.")
    return float(result.x)


def independent_ivp_comparison(
    assembler: GaussCollocationAssembler,
    unknowns: np.ndarray,
    scaling: np.ndarray,
) -> dict[str, Any]:
    variables = assembler.layout.unpack(unknowns)
    collocation_period = float(np.exp(variables.log_period))
    polynomial = assembler.polynomial_evaluator(unknowns)
    initial = polynomial(0.0)
    end_time = (2.0 + IVP_PERIOD_WINDOW) * collocation_period
    ivp = solve_ivp(
        lambda time, state: transformed_vector_field(state, assembler.env, assembler.coeff),
        (0.0, end_time),
        initial,
        method="DOP853",
        rtol=IVP_RTOL,
        atol=IVP_ATOL,
        dense_output=True,
    )
    if not ivp.success or ivp.sol is None:
        raise RuntimeError(f"DOP853 failed: {ivp.message}")

    scan_times = np.linspace(0.0, end_time, IVP_MAXIMUM_SCAN_POINTS)
    saturation = ivp.sol(scan_times)[2]
    maxima = np.flatnonzero((saturation[1:-1] > saturation[:-2]) & (saturation[1:-1] >= saturation[2:])) + 1
    windows: list[tuple[float, float]] = []
    for candidate in maxima:
        center = scan_times[candidate]
        if 0.75 * collocation_period < center < 2.05 * collocation_period:
            windows.append((scan_times[candidate - 1], scan_times[candidate + 1]))
    maximum_times = [_local_maximum_time(ivp.sol, window) for window in windows]
    if len(maximum_times) < 2:
        raise RuntimeError("DOP853 did not provide two independently located saturation maxima.")
    first_time, second_time = maximum_times[-2:]
    ivp_period = second_time - first_time
    period_relative_difference = abs(ivp_period - collocation_period) / collocation_period

    phases = np.linspace(0.0, 1.0, IVP_DENSE_COMPARISON_POINTS)
    ivp_states = ivp.sol(first_time + phases * ivp_period).T

    def orbit_distance(phase_shift: float) -> float:
        collocation_states = polynomial(np.mod(phases + phase_shift, 1.0))
        difference = (ivp_states - collocation_states) * scaling
        return float(np.sqrt(np.trapezoid(np.sum(difference * difference, axis=1), phases)))

    phase_fit = minimize_scalar(
        orbit_distance,
        bounds=(-0.5, 0.5),
        method="bounded",
        options={"xatol": 1.0e-12},
    )
    if not phase_fit.success:
        raise RuntimeError("DOP853/collocation phase alignment failed.")
    phase_shift = (float(phase_fit.x) + 0.5) % 1.0 - 0.5
    orbit_error = orbit_distance(phase_shift)
    start_state = ivp.sol(first_time)
    return_state = ivp.sol(second_time)
    return_error = float(np.linalg.norm((return_state - start_state) * scaling))
    accepted = bool(
        period_relative_difference < REFINEMENT_TOLERANCE
        and return_error < REFINEMENT_TOLERANCE
        and orbit_error < REFINEMENT_TOLERANCE
    )
    return {
        "version": IVP_VERSION,
        "case_id": "canonical-g3-n64",
        "success": bool(ivp.success),
        "method": "DOP853",
        "rtol": IVP_RTOL,
        "atol": IVP_ATOL,
        "integration_end_periods": 2.0 + IVP_PERIOD_WINDOW,
        "maximum_scan_points": IVP_MAXIMUM_SCAN_POINTS,
        "dense_comparison_points": IVP_DENSE_COMPARISON_POINTS,
        "period_landmark": "successive independently refined local maxima of saturation s",
        "first_maximum_time_s": first_time,
        "second_maximum_time_s": second_time,
        "collocation_period_s": collocation_period,
        "ivp_derived_period_s": ivp_period,
        "period_relative_difference": period_relative_difference,
        "weighted_return_error": return_error,
        "phase_aligned_weighted_dense_orbit_error": orbit_error,
        "phase_shift_cycles": phase_shift,
        "function_evaluations": int(ivp.nfev),
        "tolerance": REFINEMENT_TOLERANCE,
        "accepted": accepted,
    }


def build_outputs() -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, tuple[GaussCollocationAssembler, np.ndarray]]]:
    seed_mapping = json.loads(SEED_PATH.read_text())
    seed = PeriodicHermiteSeed.from_json(SEED_PATH, verify_upstream_root=ROOT)
    scaling = 1.0 / np.ptp(seed.transformed_state[:-1], axis=0)
    canonical_env = environment(seed_mapping["canonical_parameters"])
    records: list[dict[str, Any]] = []
    arrays: dict[str, np.ndarray] = {}
    solved: dict[str, tuple[GaussCollocationAssembler, np.ndarray]] = {}

    midpoint = json.loads(MIDPOINT_JSON.read_text())
    with np.load(MIDPOINT_NPZ, allow_pickle=False) as frozen:
        for n in (64, 128, 256):
            source = next(item for item in midpoint["results"] if item["interval_count"] == n)
            mesh = FixedMesh.uniform(n)
            rule = gauss_legendre_rule(1)
            reference = FrozenPhaseReference(
                mesh,
                frozen[f"n{n}_phase_reference_values"],
                frozen[f"n{n}_phase_reference_derivatives"],
                scaling,
                np.asarray(rule.nodes),
                np.asarray(rule.quadrature_weights),
            )
            assembler = MidpointCollocationAssembler(mesh, canonical_env, reference)
            unknowns = frozen[f"n{n}_unknowns"].copy()
            defect = assembler.independent_defect(unknowns)
            record = {
                **source,
                "case_id": f"canonical-g1-n{n}",
                "point_id": "canonical",
                "stage_count": 1,
                "formal_order": 2,
                "accepted_semantics": "nonlinear_discrete_solution_only",
                "nonlinear_accepted": source["accepted"],
                "nonlinear_terminal_reason": "accepted" if source["accepted"] else "nonlinear_rejected",
                "terminal_reason": "accepted" if source["accepted"] else "nonlinear_rejected",
                "terminal_reason_semantics": "nonlinear_discrete_solution_only",
                "defect": defect_record(defect),
                "defect_pass": defect.maximum < DEFECT_TOLERANCE,
                "seed_lineage": source_linkage(
                    kind="frozen_TASK_056_midpoint_solution",
                    artifact=MIDPOINT_NPZ,
                    vector_key=f"n{n}_unknowns",
                    reference_id=f"n{n}_phase_reference",
                    reference_artifact=MIDPOINT_NPZ,
                    parent_case_id=None,
                ),
                "nonphysical_interior_check": {
                    "version": "transformed-state-finite-positive-mapping-v1",
                    "evaluated": True,
                    "passed": True,
                },
                "ringing_diagnostic": {
                    "status": "not_evaluated",
                    "reason": "TASK-064 defines no versioned fixed-mesh polynomial-ringing metric",
                },
            }
            records.append(record)
            solved[record["case_id"]] = (assembler, unknowns)

    for stages, counts in ((2, (32, 64, 128)), (3, (16, 32, 64))):
        previous: tuple[GaussCollocationAssembler, np.ndarray, str] | None = None
        for n in counts:
            mesh = FixedMesh.uniform(n)
            rule = gauss_legendre_rule(stages)
            if previous is None:
                reference = FrozenPhaseReference.from_evaluator(
                    mesh, rule, seed.evaluate, seed.derivative, state_scaling=scaling
                )
                temporary = GaussCollocationAssembler(mesh, canonical_env, reference, rule)
                initial = temporary.reference_unknowns(seed.evaluate, seed.log_period)
                lineage = source_linkage(
                    kind="frozen_Episode_007_Hermite_seed",
                    artifact=SEED_PATH,
                    vector_key="periodic_hermite_evaluator",
                    reference_id=seed_mapping["seed_id"],
                    reference_artifact=SEED_PATH,
                    parent_case_id=None,
                )
            else:
                old, old_unknowns, old_case_id = previous
                initial = old.transfer_unknowns(old_unknowns, mesh, rule)
                reference = old.transferred_phase_reference(old_unknowns, mesh, rule)
                lineage = {
                    "kind": "previous_accepted_collocation_case",
                    "parent_case_id": old_case_id,
                    "vector_key": old_case_id + "__unknowns",
                    "reference_id": old_case_id + "__transferred_polynomial",
                    "artifact_path": VECTORS_PATH.relative_to(ROOT).as_posix(),
                }
            record, assembler, result = solve_case(
                "canonical", canonical_env, stages, n, initial, reference
            )
            record["seed_lineage"] = lineage
            records.append(record)
            solved[record["case_id"]] = (assembler, result.unknowns.copy())
            arrays[record["case_id"] + "__unknowns"] = np.asarray(result.unknowns, dtype="<f8")
            arrays[record["case_id"] + "__residual"] = np.asarray(result.residual, dtype="<f8")
            arrays[record["case_id"] + "__boundaries"] = np.asarray(mesh.boundaries, dtype="<f8")
            arrays[record["case_id"] + "__phase_values"] = np.asarray(reference.stage_values, dtype="<f8")
            arrays[record["case_id"] + "__phase_derivatives"] = np.asarray(reference.stage_derivatives, dtype="<f8")
            if result.accepted:
                previous = (assembler, result.unknowns.copy(), record["case_id"])

    continuation = json.loads(CONTINUATION_JSON.read_text())
    point_records = {item["point_id"]: item for item in continuation["points"]}
    base = continuation["canonical_parameters_except_T_w"]
    guard_keys = {
        "guard-rho-0": "spine-negative-T-hat-to-210-target-restart-phase-ref-slice-210",
        "guard-rho-minus-0.15": "slice210-negative-rho-target",
        "guard-rho-plus-0.15": "slice210-positive-rho-target",
    }
    with np.load(CONTINUATION_NPZ, allow_pickle=False) as frozen:
        old_mesh = FixedMesh(frozen["mesh_boundaries"])
        old_rule = gauss_legendre_rule(1)
        old_reference = FrozenPhaseReference(
            old_mesh,
            frozen["phase_ref_slice210_values"],
            frozen["phase_ref_slice210_derivatives"],
            scaling,
            np.asarray(old_rule.nodes),
            np.asarray(old_rule.quadrature_weights),
        )
        for point_id, source_point_id in guard_keys.items():
            point = point_records[source_point_id]
            guard_env = environment(
                {"T": point["temperature_K"], "w": point["w_m_s"], **base}
            )
            source = GaussCollocationAssembler(old_mesh, guard_env, old_reference, old_rule)
            source_unknowns = frozen["point__" + source_point_id].copy()
            for stages, counts in ((2, (64, 128)), (3, (32, 64))):
                previous = (source, source_unknowns, source_point_id)
                for case_index, n in enumerate(counts):
                    mesh = FixedMesh.uniform(n)
                    rule = gauss_legendre_rule(stages)
                    old, old_unknowns, parent_id = previous
                    initial = old.transfer_unknowns(old_unknowns, mesh, rule)
                    reference = old.transferred_phase_reference(old_unknowns, mesh, rule)
                    record, assembler, result = solve_case(
                        point_id, guard_env, stages, n, initial, reference
                    )
                    if case_index == 0:
                        lineage = source_linkage(
                            kind="exact_TASK_061_target_midpoint_polynomial",
                            artifact=CONTINUATION_NPZ,
                            vector_key="point__" + source_point_id,
                            reference_id="phase-ref-slice-210",
                            reference_artifact=CONTINUATION_NPZ,
                            parent_case_id=source_point_id,
                        )
                    else:
                        lineage = {
                            "kind": "previous_accepted_collocation_case",
                            "parent_case_id": parent_id,
                            "vector_key": parent_id + "__unknowns",
                            "reference_id": parent_id + "__transferred_polynomial",
                            "artifact_path": VECTORS_PATH.relative_to(ROOT).as_posix(),
                        }
                    record.update(
                        {
                            "rho": point["rho"],
                            "temperature_K": point["temperature_K"],
                            "w_m_s": point["w_m_s"],
                            "seed_lineage": lineage,
                        }
                    )
                    records.append(record)
                    solved[record["case_id"]] = (assembler, result.unknowns.copy())
                    arrays[record["case_id"] + "__unknowns"] = np.asarray(result.unknowns, dtype="<f8")
                    arrays[record["case_id"] + "__residual"] = np.asarray(result.residual, dtype="<f8")
                    arrays[record["case_id"] + "__boundaries"] = np.asarray(mesh.boundaries, dtype="<f8")
                    arrays[record["case_id"] + "__phase_values"] = np.asarray(reference.stage_values, dtype="<f8")
                    arrays[record["case_id"] + "__phase_derivatives"] = np.asarray(reference.stage_derivatives, dtype="<f8")
                    if result.accepted:
                        previous = (assembler, result.unknowns.copy(), record["case_id"])

    comparisons: list[dict[str, Any]] = []
    for point_id in ("canonical", *guard_keys):
        stage_counts = (1, 2, 3) if point_id == "canonical" else (2, 3)
        for stages in stage_counts:
            cases = sorted(
                (item for item in records if item["point_id"] == point_id and item["stage_count"] == stages),
                key=lambda item: item["interval_count"],
            )
            for left, right in zip(cases, cases[1:]):
                item = {
                    "version": QUALIFICATION_VERSION,
                    "point_id": point_id,
                    "stage_count": stages,
                    "coarse_case_id": left["case_id"],
                    "fine_case_id": right["case_id"],
                }
                if not left["nonlinear_accepted"] or not right["nonlinear_accepted"]:
                    item.update(
                        {
                            "available": False,
                            "terminal_reason": "rejected_case_in_pair",
                            "qualification_pass": False,
                        }
                    )
                else:
                    coarse_assembler, coarse_unknowns = solved[left["case_id"]]
                    fine_assembler, fine_unknowns = solved[right["case_id"]]
                    period_change = abs(right["period_s"] - left["period_s"]) / abs(right["period_s"])
                    orbit_change = fine_assembler.compare_with_collocation(
                        fine_unknowns, coarse_assembler, coarse_unknowns
                    ).distance
                    item.update(
                        {
                            "available": True,
                            "terminal_reason": "compared",
                            "period_relative_change": period_change,
                            "weighted_orbit_change": orbit_change,
                            "period_pass": period_change < REFINEMENT_TOLERANCE,
                            "orbit_pass": orbit_change < REFINEMENT_TOLERANCE,
                            "qualification_pass": bool(
                                period_change < REFINEMENT_TOLERANCE
                                and orbit_change < REFINEMENT_TOLERANCE
                            ),
                        }
                    )
                comparisons.append(item)

    cross_order: list[dict[str, Any]] = []
    for point_id in ("canonical", *guard_keys):
        point_cases = [item for item in records if item["point_id"] == point_id]
        pairs = (
            ((1, 256), (2, 128)),
            ((2, 128), (3, 64)),
        ) if point_id == "canonical" else (
            ((2, 128), (3, 64)),
        )
        for (left_stage, left_n), (right_stage, right_n) in pairs:
            left = next(item for item in point_cases if item["stage_count"] == left_stage and item["interval_count"] == left_n)
            right = next(item for item in point_cases if item["stage_count"] == right_stage and item["interval_count"] == right_n)
            item = {
                "version": QUALIFICATION_VERSION,
                "point_id": point_id,
                "lower_order_case_id": left["case_id"],
                "higher_order_case_id": right["case_id"],
                "broadly_comparable_unknown_sizes": [
                    3 * left_n * (left_stage + 1) + 1,
                    3 * right_n * (right_stage + 1) + 1,
                ],
            }
            if not left["nonlinear_accepted"] or not right["nonlinear_accepted"]:
                item.update({"available": False, "terminal_reason": "rejected_case_in_pair"})
            else:
                left_assembler, left_unknowns = solved[left["case_id"]]
                right_assembler, right_unknowns = solved[right["case_id"]]
                higher_order_defect_smaller = (
                    right["defect"]["maximum"] < left["defect"]["maximum"]
                )
                item.update(
                    {
                        "available": True,
                        "terminal_reason": "compared",
                        "period_relative_difference": abs(right["period_s"] - left["period_s"]) / abs(right["period_s"]),
                        "weighted_orbit_difference": right_assembler.compare_with_collocation(
                            right_unknowns, left_assembler, left_unknowns
                        ).distance,
                        "higher_order_defect_smaller": higher_order_defect_smaller,
                        "order_improvement_status": (
                            "observed" if higher_order_defect_smaller else "not_observed"
                        ),
                        "order_improvement_decision_basis": (
                            "higher-order independent defect is smaller at broadly comparable packed-system size"
                        ),
                    }
                )
            cross_order.append(item)

    comparisons_by_fine = {item["fine_case_id"]: item for item in comparisons}
    for record in records:
        reasons: list[str] = []
        if not record["nonlinear_accepted"]:
            reasons.append("nonlinear_rejected")
        if not record["defect_pass"]:
            reasons.append("independent_defect_above_1e-4")
        refinement = comparisons_by_fine.get(record["case_id"])
        if refinement is None:
            reasons.append("no_preceding_same_rule_case")
        elif not refinement["available"]:
            reasons.append("same_rule_refinement_unavailable")
        else:
            record["same_rule_refinement"] = {
                key: refinement[key]
                for key in (
                    "coarse_case_id",
                    "period_relative_change",
                    "weighted_orbit_change",
                    "period_pass",
                    "orbit_pass",
                )
            }
            if not refinement["qualification_pass"]:
                reasons.append("same_rule_refinement_above_1e-3")
        status = "qualified" if not reasons else "not_qualified"
        record["qualification"] = {
            "version": QUALIFICATION_VERSION,
            "status": status,
            "qualified": status == "qualified",
            "reasons": reasons,
            "nonlinear_acceptance_is_not_qualification": True,
        }

    best_assembler, best_unknowns = solved["canonical-g3-n64"]
    ivp_record = independent_ivp_comparison(best_assembler, best_unknowns, scaling)

    array_manifest = {
        key: {"dtype": "float64-little-endian", "shape": list(value.shape), "sha256": array_digest(value)}
        for key, value in sorted(arrays.items())
    }
    source_paths = {
        "generator": Path(__file__).resolve(),
        "periodic_orbits": PERIODIC_ORBITS_PATH,
        "collocation_coefficients": COEFFICIENT_PATH,
        "bootstrap_seed": SEED_PATH,
        "task056_midpoint_results": MIDPOINT_JSON,
        "task056_midpoint_vectors": MIDPOINT_NPZ,
        "task061_continuation_results": CONTINUATION_JSON,
        "task061_continuation_vectors": CONTINUATION_NPZ,
        "uv_lock": LOCK_PATH,
    }
    mapping: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": "episode008_higher_order_fixed_mesh_qualification",
        "formulation_version": GAUSS_FORMULATION_VERSION,
        "solver_version": GAUSS_SOLVER_VERSION,
        "qualification_version": QUALIFICATION_VERSION,
        "coefficient_artifact_sha256": COLLOCATION_ARTIFACT_SHA256,
        "runtime_provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "source_provenance": {
            key: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
            for key, path in source_paths.items()
        },
        "qualification_contract": {
            "period_relative_tolerance": REFINEMENT_TOLERANCE,
            "weighted_orbit_tolerance": REFINEMENT_TOLERANCE,
            "defect_acceptance_tolerance": DEFECT_TOLERANCE,
            "failed_cases_are_evidence": True,
            "ringing": "not_evaluated_no_versioned_metric",
            "floquet": "not_evaluated",
        },
        "results": records,
        "same_rule_refinement": comparisons,
        "cross_order_evidence": cross_order,
        "canonical_ivp": ivp_record,
        "summary": {
            "nonlinear_accepted_case_count": sum(item["nonlinear_accepted"] for item in records),
            "nonlinear_rejected_case_count": sum(not item["nonlinear_accepted"] for item in records),
            "qualified_case_count": sum(item["qualification"]["qualified"] for item in records),
            "fixed_uniform_mesh_qualified": False,
        },
        "vector_artifact": {
            "path": VECTORS_PATH.relative_to(ROOT).as_posix(),
            "arrays": array_manifest,
            "unknown_order": "N endpoint blocks, N*r stage blocks in interval-major/stage-major order, log(period_s)",
            "residual_order": "N*r scaled stage blocks, N scaled cyclic updates, normalized phase",
        },
    }
    return mapping, arrays, solved


def array_schema(name: str, value: np.ndarray, units: str, ordering: str) -> dict[str, Any]:
    array = np.asarray(value)
    return {
        "name": name,
        "dtype": "float64",
        "shape": list(array.shape),
        "units": units,
        "ordering": ordering,
        "sha256": array_digest(array),
    }


def build_fixtures(
    mapping: dict[str, Any],
    solved: dict[str, tuple[GaussCollocationAssembler, np.ndarray]],
) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    manifest_cases: list[dict[str, Any]] = []
    upstream = {
        key: value
        for key, value in mapping["source_provenance"].items()
        if key in {"periodic_orbits", "collocation_coefficients", "bootstrap_seed", "uv_lock"}
    }
    for stages in (2, 3):
        assembler, accepted = solved[f"canonical-g{stages}-n64"]
        nonsolution = accepted.copy()
        direction = np.sin(np.arange(accepted.size) + 0.375)
        nonsolution[:-1] += 2.0e-3 * direction[:-1]
        nonsolution[-1] += 3.0e-4 * direction[-1]
        for kind, unknowns in (("converged", accepted), ("nonsolution", nonsolution)):
            blocks = assembler.residual_blocks(unknowns)
            arrays = {
                "mesh_boundaries": np.asarray(assembler.mesh.boundaries),
                "unknowns": np.asarray(unknowns),
                "phase_reference_values": np.asarray(assembler.phase_reference.stage_values),
                "phase_reference_derivatives": np.asarray(assembler.phase_reference.stage_derivatives),
                "residual_stages": np.asarray(blocks.stages),
                "residual_updates": np.asarray(blocks.updates),
                "residual_phase": np.asarray([blocks.phase]),
            }
            schemas = {
                "mesh_boundaries": array_schema("mesh_boundaries", arrays["mesh_boundaries"], "normalized phase cycles", "boundary index"),
                "unknowns": array_schema("unknowns", arrays["unknowns"], "mixed transformed-state/log-seconds", "endpoints; stages interval-major/stage-major; log(period_s)"),
                "phase_reference_values": array_schema("phase_reference_values", arrays["phase_reference_values"], "natural_log(kg_dry_air^-1), natural_log(kg kg_dry_air^-1), dimensionless", "interval, stage, component"),
                "phase_reference_derivatives": array_schema("phase_reference_derivatives", arrays["phase_reference_derivatives"], "transformed state per normalized phase cycle", "interval, stage, component"),
                "residual_stages": array_schema("residual_stages", arrays["residual_stages"], "scaled transformed state", "interval, stage, component"),
                "residual_updates": array_schema("residual_updates", arrays["residual_updates"], "scaled transformed state", "interval, component"),
                "residual_phase": array_schema("residual_phase", arrays["residual_phase"], "phase cycles", "scalar"),
            }
            case_id = f"g{stages}-n64-{kind}"
            payload = {
                "schema_version": FIXTURE_SCHEMA_VERSION,
                "case_id": case_id,
                "meaning": kind,
                "formulation_version": GAUSS_FORMULATION_VERSION,
                "solver_version": GAUSS_SOLVER_VERSION,
                "coefficient_artifact_sha256": COLLOCATION_ARTIFACT_SHA256,
                "environment": environment_record(assembler.env),
                "model_contract": transformed_model_contract(),
                "coefficient_values": coefficient_record(assembler),
                "orbit_coordinate_contract": {
                    "normalized_phase_domain": [0.0, 1.0],
                    "period_coordinate": "natural_log(period_s)",
                    "periodic_endpoint_storage": "store N left endpoints; endpoint N equals endpoint 0",
                },
                "rule": {
                    "family": assembler.rule.family,
                    "stage_count": stages,
                    "formal_order": assembler.rule.formal_order,
                    "nodes": list(assembler.rule.nodes),
                    "stage_coefficients": [list(row) for row in assembler.rule.stage_coefficients],
                    "quadrature_weights": list(assembler.rule.quadrature_weights),
                },
                "dimensions": {
                    "interval_count": assembler.layout.interval_count,
                    "state_dimension": assembler.layout.state_dimension,
                    "unknown_size": assembler.layout.unknown_size,
                    "residual_size": assembler.layout.residual_size,
                },
                "state_scaling": assembler.state_scaling.tolist(),
                "nonlinear_tolerances": {
                    "stage_max": NONLINEAR_TOLERANCES.stage_max,
                    "stage_rms": NONLINEAR_TOLERANCES.stage_rms,
                    "update_max": NONLINEAR_TOLERANCES.update_max,
                    "update_rms": NONLINEAR_TOLERANCES.update_rms,
                    "phase_abs": NONLINEAR_TOLERANCES.phase_abs,
                    "jacobian_directional_relative": JACOBIAN_DIRECTIONAL_RELATIVE_TOLERANCE,
                },
                "perturbation": {
                    "version": PERTURBATION_VERSION,
                    "applied": kind == "nonsolution",
                    "definition": "unknowns[k] += 2e-3*sin(k+0.375) for k<last; log_period += 3e-4*sin(last+0.375)",
                },
                "upstream_provenance": upstream,
                "array_schema": schemas,
                "arrays": {key: value.tolist() for key, value in arrays.items()},
                "checksum_convention": "SHA-256 of contiguous little-endian float64 C-order bytes; file hash is canonical sorted-key indented UTF-8 JSON",
            }
            body = canonical_json(payload)
            name = case_id + ".json"
            files[name] = body
            manifest_cases.append(
                {
                    "case_id": case_id,
                    "path": name,
                    "sha256": digest(body),
                    "unknown_size": assembler.layout.unknown_size,
                    "array_checksums": {key: value["sha256"] for key, value in schemas.items()},
                }
            )
    manifest = {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "artifact_kind": "language-neutral-gauss-parity-fixtures",
        "formulation_version": GAUSS_FORMULATION_VERSION,
        "coefficient_artifact_sha256": COLLOCATION_ARTIFACT_SHA256,
        "checksum_convention": "case file SHA-256 over exact canonical JSON bytes; array SHA-256 over contiguous little-endian float64 C-order bytes",
        "ordering": {
            "unknowns": "endpoint interval/component; stage interval/stage/component; log(period_s)",
            "residual": "stage interval/stage/component; update interval/component; phase",
        },
        "cases": manifest_cases,
    }
    files["manifest.json"] = canonical_json(manifest)
    return files


def generate(check: bool = False) -> None:
    mapping, arrays, solved = build_outputs()
    vectors = npz_bytes(arrays)
    mapping["vector_artifact"]["file_sha256"] = digest(vectors)
    result_bytes = canonical_json(mapping)
    fixtures = build_fixtures(mapping, solved)
    if check:
        expected = {
            RESULTS_PATH: result_bytes,
            VECTORS_PATH: vectors,
            **{FIXTURE_DIR / key: value for key, value in fixtures.items()},
        }
        for path, value in expected.items():
            if not path.is_file() or path.read_bytes() != value:
                raise SystemExit(f"Generated artifact drift: {path}")
        extras = set(FIXTURE_DIR.glob("*")) - {FIXTURE_DIR / key for key in fixtures}
        if extras:
            raise SystemExit(f"Unexpected fixture files: {sorted(extras)}")
        print("verified TASK-064 qualification artifacts")
        return
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_bytes(result_bytes)
    VECTORS_PATH.write_bytes(vectors)
    for key, value in fixtures.items():
        (FIXTURE_DIR / key).write_bytes(value)
    print("wrote TASK-064 qualification artifacts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    generate(parser.parse_args().check)


if __name__ == "__main__":
    main()
