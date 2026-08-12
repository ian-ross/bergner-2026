import copy
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import CubicHermiteSpline


REPO_ROOT = Path(__file__).resolve().parents[1]
EPISODE_ROOT = REPO_ROOT / "episodes/008-figure5-periodic-orbit-continuation"
SCRIPTS = EPISODE_ROOT / "scripts"
OUTPUT = EPISODE_ROOT / "outputs/bootstrap_seed.json"
UPSTREAM_ROOT = REPO_ROOT / "episodes/007-limit-cycle-interactive-widget/outputs"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_bootstrap_seed as bootstrap
from bergner_spichtinger_2026.constants import Environment
from bergner_spichtinger_2026.core import vector_field
from bergner_spichtinger_2026.periodic_seed import (
    PeriodicHermiteSeed,
    SeedValidationError,
    verify_upstream_checksums,
)


def test_frozen_bootstrap_seed_regenerates_deterministically_with_provenance():
    frozen_text = OUTPUT.read_text(encoding="utf-8")
    generated = bootstrap.build_seed()

    assert bootstrap.render_seed(generated) == frozen_text
    assert generated["canonical_parameters"] == bootstrap.EXPECTED_PARAMETERS
    assert generated["period_s"] == pytest.approx(2461.6112682421517, rel=0.0, abs=1.0e-12)
    assert generated["log_period"] == pytest.approx(np.log(generated["period_s"]))
    assert generated["extraction"]["source_cycle_key"] == "paper_0.99"
    assert generated["extraction"]["boundary_kind"] == "saturation_maximum_to_saturation_maximum"
    assert generated["extraction"]["long_ivp_rerun_required"] is False
    assert generated["extraction"]["source_closure_max_abs"] < generated["extraction"]["source_closure_tolerance"]
    assert generated["upstream"]["reference_trajectory"]["sha256"] == (
        "899476206a26a3d0a43a3ecf6887975e7ebb14e613b06df01e207c54e1a086b2"
    )
    assert generated["upstream"]["reference_metadata"]["sha256"] == (
        "7077f0516090526da3876c2b259d5ca4cf624ea04a2644162a8d4b04452b64d9"
    )


def test_periodic_hermite_seed_uses_model_field_slopes_and_evaluates_arbitrary_locations():
    mapping = json.loads(OUTPUT.read_text(encoding="utf-8"))
    seed = PeriodicHermiteSeed.from_json(OUTPUT, verify_upstream_root=REPO_ROOT)
    params = mapping["canonical_parameters"]
    env = Environment(
        T=params["T"],
        p=params["p"],
        w=params["w"],
        F=params["F"],
        N_a=params["N_a"],
        Δz=params["Delta_z"],
        include_evaporation=params["include_evaporation"],
    )

    expected_slopes = []
    for state in seed.transformed_state:
        n, q = np.exp(state[:2])
        physical_rhs = vector_field(float(n), float(q), float(state[2]), env)
        expected_slopes.append(
            seed.period_s * np.array([physical_rhs[0] / n, physical_rhs[1] / q, physical_rhs[2]])
        )
    np.testing.assert_allclose(
        seed.dstate_dtheta,
        expected_slopes,
        rtol=2.0e-14,
        atol=2.0e-13,
    )

    np.testing.assert_array_equal(seed.evaluate(0.0), seed.evaluate(1.0))
    np.testing.assert_array_equal(seed.derivative(0.0), seed.derivative(1.0))
    np.testing.assert_array_equal(seed.evaluate(0.0), seed.transformed_state[0])
    np.testing.assert_array_equal(seed.derivative(0.0), seed.dstate_dtheta[0])
    np.testing.assert_allclose(seed.evaluate(seed.theta), seed.transformed_state, rtol=0.0, atol=2.0e-15)
    np.testing.assert_allclose(seed.derivative(seed.theta), seed.dstate_dtheta, rtol=0.0, atol=2.0e-13)

    endpoint_theta = np.arange(8, dtype=float) / 8.0
    midpoint_stage_theta = endpoint_theta + 0.5 / 8.0
    arbitrary_theta = np.array([-0.125, 0.0, 0.0137, 0.5, 1.0, 1.125])
    assert seed.evaluate(endpoint_theta).shape == (8, 3)
    assert seed.evaluate(midpoint_stage_theta).shape == (8, 3)
    assert seed.derivative(arbitrary_theta).shape == (6, 3)
    assert np.all(np.isfinite(seed.evaluate(arbitrary_theta)))
    np.testing.assert_allclose(seed.evaluate(-0.125), seed.evaluate(0.875), rtol=0.0, atol=0.0)
    np.testing.assert_allclose(seed.evaluate(1.125), seed.evaluate(0.125), rtol=0.0, atol=0.0)

    scipy_reference = CubicHermiteSpline(
        seed.theta,
        seed.transformed_state,
        seed.dstate_dtheta,
        axis=0,
    )
    interior_theta = np.array([0.0137, 0.1234, 0.501, 0.8765])
    np.testing.assert_allclose(seed.evaluate(interior_theta), scipy_reference(interior_theta), rtol=2.0e-14)
    np.testing.assert_allclose(
        seed.derivative(interior_theta),
        scipy_reference(interior_theta, nu=1),
        rtol=1.0e-13,
        atol=1.0e-12,
    )
    with pytest.raises(ValueError, match="read-only"):
        seed.transformed_state[0, 0] += 1.0


def test_from_json_rejects_a_non_object_top_level(tmp_path):
    malformed = tmp_path / "seed.json"
    malformed.write_text("[]", encoding="utf-8")

    with pytest.raises(SeedValidationError, match="top-level object"):
        PeriodicHermiteSeed.from_json(malformed, verify_upstream_root=tmp_path)


def test_upstream_checksum_verification_detects_artifact_drift(tmp_path):
    for source_record in json.loads(OUTPUT.read_text(encoding="utf-8"))["upstream"].values():
        relative = Path(source_record["path"])
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)

    seed_mapping = json.loads(OUTPUT.read_text(encoding="utf-8"))
    verify_upstream_checksums(seed_mapping, tmp_path)

    trajectory = tmp_path / seed_mapping["upstream"]["reference_trajectory"]["path"]
    trajectory.write_text(trajectory.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(SeedValidationError, match="drift detected"):
        verify_upstream_checksums(seed_mapping, tmp_path)


def test_malformed_cycle_boundaries_are_rejected(tmp_path):
    metadata = json.loads((UPSTREAM_ROOT / "reference_metadata.json").read_text(encoding="utf-8"))
    metadata["cycle_boundaries"]["paper_0.99"][-1]["start_s"] += 1.0
    malformed = tmp_path / "reference_metadata.json"
    malformed.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(SeedValidationError, match="not contiguous"):
        bootstrap.build_seed(UPSTREAM_ROOT / "reference_trajectory.csv", malformed)


def test_nonperiodic_seed_values_and_slopes_are_rejected():
    mapping = json.loads(OUTPUT.read_text(encoding="utf-8"))
    nonperiodic_value = copy.deepcopy(mapping)
    nonperiodic_value["knots"]["transformed_state"][-1][0] += 1.0e-8
    with pytest.raises(SeedValidationError, match="endpoint values"):
        PeriodicHermiteSeed.from_mapping(nonperiodic_value)

    nonperiodic_slope = copy.deepcopy(mapping)
    nonperiodic_slope["knots"]["dstate_dtheta"][-1][2] += 1.0e-8
    with pytest.raises(SeedValidationError, match="endpoint slopes"):
        PeriodicHermiteSeed.from_mapping(nonperiodic_slope)
