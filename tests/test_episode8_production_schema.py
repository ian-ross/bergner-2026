from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bergner_spichtinger_2026.episode8_production_schema import (
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    ProductionSchemaValidationError,
    canonical_json_bytes,
    production_schema_contract,
    validate_production_artifact,
)

ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes/008-figure5-periodic-orbit-continuation"
VALIDATOR = EPISODE / "scripts/validate_production_artifacts.py"
CONTRACT = EPISODE / "schemas/episode8-figure5-production-v1.contract.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_source(tmp_path: Path, name: str = "source.json") -> Path:
    path = tmp_path / name
    path.write_text('{"schema_version":"upstream-test-v1"}\n')
    return path


def provenance(tmp_path: Path, source: Path | None = None) -> dict:
    source = source or write_source(tmp_path)
    return {
        "task": "TASK-070",
        "created_by": "pytest",
        "digitized_paper_data_policy": "external-comparison-only",
        "source_artifacts": [
            {
                "path": source.relative_to(tmp_path).as_posix(),
                "sha256": sha(source),
                "role": "minimal upstream fixture",
            }
        ],
    }


def method_versions(source: str = "computed_native_adaptive") -> dict:
    versions = {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "continuation_method": "external-gauss3-hr-adaptive-v1",
        "validator": "pytest-fixture-v1",
    }
    if source == "computed_linearized_equilibrium":
        versions["linearized_period_method"] = "equilibrium-eigenvalue-period-v1"
    return versions


def coordinate_conventions() -> dict:
    return {
        "parameter_coordinates": "temperature-log_w-rho-spine-slices-v1",
        "orbit_state": "transformed-state-log_n-log_q-s-v1",
        "phase": "normalized-phase-theta-in-[0,1]-periodic-v1",
        "period": "physical-period-seconds-logP-internal-v1",
    }


def coordinates(temperature: float = 210.0) -> dict:
    return {
        "convention": "temperature-log_w-rho-spine-slices-v1",
        "temperature": {"value": temperature, "unit": "K"},
        "log_w": {"value": -2.0, "unit": "ln(m s^-1)"},
        "w": {"value": 0.1353352832366127, "unit": "m s^-1"},
        "rho": {"value": 0.0, "unit": "dimensionless"},
        "temperature_hat": {"value": -0.2, "unit": "dimensionless"},
    }


def validity(status: str = "accepted", source: str = "computed_native_adaptive", *, authoritative: bool = True) -> dict:
    record = {"status": status, "source": source, "authoritative": authoritative}
    if status != "accepted":
        record["reason"] = "explicit test reason"
    return record


def period(quantity: str = "nonlinear_period", value: float | None = 2461.6) -> dict:
    return {"quantity": quantity, "value": value, "unit": "s", "log_value": None if value is None else 7.808566}


def base_artifact(tmp_path: Path, kind: str, payload_key: str, payload: object, source: Path | None = None) -> dict:
    return {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": kind,
        "artifact_id": f"test-{kind}",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": provenance(tmp_path, source=source),
        payload_key: payload,
    }


def common_record(source: str = "computed_native_adaptive", status: str = "accepted") -> dict:
    return {
        "record_id": "record-001",
        "coordinates": coordinates(),
        "validity": validity(status, source, authoritative=status == "accepted"),
        "method_versions": method_versions(source),
    }


def valid_artifacts(tmp_path: Path) -> list[dict]:
    source = write_source(tmp_path)
    point = common_record()
    point.update({"period": period(), "orbit_vector_ref": "orbit-npz:orbit_001"})

    event = {
        "event_id": "event-001",
        "event_type": "accepted_step",
        "coordinates": coordinates(),
        "validity": validity(),
        "method_versions": method_versions(),
        "period": period(),
    }

    run_metadata = {
        "run_id": "run-001",
        "backend": "native-adaptive-loca",
        "executable_identity": {"path": "loca-build/bs2026_midpoint_orbit", "sha256": "a" * 64},
        "build_identity": {"compiler": "test", "source_sha256": "b" * 64},
        "coordinate_domain": {
            "convention": "temperature-log_w-rho-spine-slices-v1",
            "temperature": {"min": 210.0, "max": 226.0, "unit": "K"},
            "log_w": {"min": -3.0, "max": -1.0, "unit": "ln(m s^-1)"},
            "rho": {"min": -1.0, "max": 1.0, "unit": "dimensionless"},
        },
        "resource_accounting": {
            "wall_clock": {"value": 12.5, "unit": "s"},
            "cpu_time": {"value": 11.0, "unit": "s"},
            "max_rss": {"value": 1024, "unit": "KiB"},
        },
        "terminal_status_counts": {"accepted": 1, "gap": 0},
    }

    npz_path = tmp_path / "orbit_vectors.npz"
    np.savez(npz_path, theta=np.linspace(0.0, 1.0, 4), states=np.zeros((4, 3)))
    orbit_manifest = {
        "npz_path": npz_path.relative_to(tmp_path).as_posix(),
        "npz_sha256": sha(npz_path),
        "arrays": {
            "theta": {
                "dtype": "float64",
                "byte_order": "little-endian",
                "shape": [4],
                "unit": "dimensionless",
                "role": "normalized phase samples",
            },
            "states": {
                "dtype": "float64",
                "byte_order": "little-endian",
                "shape": [4, 3],
                "unit": "mixed",
                "role": "transformed orbit state log(n), log(q), s",
            },
        },
    }

    linearized = common_record(source="computed_linearized_equilibrium")
    linearized["validity"] = validity("accepted", "computed_linearized_equilibrium")
    linearized["period"] = period("linearized_period", 2400.0)
    linearized["eigenvalue_imaginary_part"] = {"value": 0.002617993877991494, "unit": "rad s^-1"}

    browser_accepted = common_record()
    browser_accepted.update({"record_role": "period_map_cell", "display_period": period("display_period")})
    browser_interpolated = common_record(source="interpolated_holdout_validated", status="interpolated")
    browser_interpolated.update({
        "record_id": "record-interpolated",
        "record_role": "period_map_cell",
        "display_period": period("display_period"),
        "interpolation": {
            "source_point_ids": ["p1", "p2", "p3"],
            "holdout_validation": {"status": "passed", "max_log_period_error": 0.001},
        },
    })
    browser_gap = common_record(source="explicit_gap", status="gap")
    browser_gap.update({"record_id": "record-gap", "record_role": "explicit_gap", "display_period": period("display_period", None)})
    browser_external = common_record(source="external_digitized_paper_comparison", status="external_comparison")
    browser_external.update({
        "record_id": "record-paper",
        "record_role": "external_comparison_overlay",
        "validity": validity("external_comparison", "external_digitized_paper_comparison", authoritative=False),
        "display_period": period("display_period"),
    })

    return [
        base_artifact(tmp_path, "continuation-points", "continuation_points", [point], source),
        base_artifact(tmp_path, "continuation-events", "continuation_events", [event], source),
        base_artifact(tmp_path, "run-metadata", "run_metadata", run_metadata, source),
        base_artifact(tmp_path, "curated-orbit-npz-manifest", "orbit_vector_manifest", orbit_manifest, source),
        base_artifact(tmp_path, "linearized-period-curve", "linearized_period_rows", [linearized], source),
        base_artifact(
            tmp_path,
            "browser-display-dataset",
            "browser_records",
            [browser_accepted, browser_interpolated, browser_gap, browser_external],
            source,
        ),
    ]


def test_production_schema_contract_file_is_current_and_covers_required_artifact_kinds() -> None:
    contract = production_schema_contract()
    assert CONTRACT.read_bytes() == canonical_json_bytes(contract)
    assert set(contract["artifact_kinds"]) == {
        "continuation-points",
        "continuation-events",
        "run-metadata",
        "curated-orbit-npz-manifest",
        "linearized-period-curve",
        "browser-display-dataset",
    }
    assert contract["provenance_policy"]["digitized_paper_data_policy"] == "external-comparison-only"


@pytest.mark.parametrize("index", range(6))
def test_all_episode8_production_artifact_kinds_accept_minimal_valid_records(tmp_path: Path, index: int) -> None:
    artifact = valid_artifacts(tmp_path)[index]
    validate_production_artifact(artifact, root=tmp_path)


def test_validation_cli_accepts_artifact_and_prints_contract(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(json.dumps(valid_artifacts(tmp_path)[0], sort_keys=True))
    subprocess.run(["uv", "run", "python", str(VALIDATOR), str(artifact_path), "--root", str(tmp_path)], cwd=ROOT, check=True)
    completed = subprocess.run(
        ["uv", "run", "python", str(VALIDATOR), "--print-contract"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["schema_version"] == EPISODE8_PRODUCTION_SCHEMA_VERSION


def assert_invalid(artifact: dict, tmp_path: Path, phrase: str) -> None:
    with pytest.raises(ProductionSchemaValidationError) as excinfo:
        validate_production_artifact(artifact, root=tmp_path)
    assert phrase in str(excinfo.value)


def test_validator_rejects_missing_provenance(tmp_path: Path) -> None:
    artifact = valid_artifacts(tmp_path)[0]
    artifact.pop("provenance")
    assert_invalid(artifact, tmp_path, "provenance object is required")


def test_validator_rejects_unresolved_gap_interpolated_source_ambiguity(tmp_path: Path) -> None:
    artifact = valid_artifacts(tmp_path)[5]
    ambiguous = copy.deepcopy(artifact["browser_records"][2])
    ambiguous["record_id"] = "ambiguous-gap"
    ambiguous["validity"] = {
        "status": "gap",
        "source": "interpolated_holdout_validated",
        "sources": ["explicit_gap", "interpolated_holdout_validated"],
        "reason": "ambiguous gap/interpolation source",
        "authoritative": False,
    }
    artifact["browser_records"] = [ambiguous]
    assert_invalid(artifact, tmp_path, "exactly one unambiguous source flag")
    assert_invalid(artifact, tmp_path, "incompatible with status 'gap'")


def test_validator_rejects_checksum_drift(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    artifact = valid_artifacts(tmp_path)[0]
    artifact["provenance"] = provenance(tmp_path, source)
    validate_production_artifact(artifact, root=tmp_path)
    source.write_text("changed\n")
    assert_invalid(artifact, tmp_path, "checksum drift")


def test_validator_rejects_schema_version_mismatch(tmp_path: Path) -> None:
    artifact = valid_artifacts(tmp_path)[0]
    artifact["schema_version"] = "episode8-figure5-production-v0"
    assert_invalid(artifact, tmp_path, "expected 'episode8-figure5-production-v1'")


def test_validator_rejects_incompatible_coordinate_or_unit_fields(tmp_path: Path) -> None:
    artifact = valid_artifacts(tmp_path)[0]
    artifact["continuation_points"][0]["coordinates"]["convention"] = "temperature-w-v0"
    artifact["continuation_points"][0]["coordinates"]["w"]["unit"] = "cm s^-1"
    assert_invalid(artifact, tmp_path, "temperature-log_w-rho-spine-slices-v1")
    assert_invalid(artifact, tmp_path, "must equal 'm s^-1'")


def test_validator_rejects_orbit_npz_checksum_drift(tmp_path: Path) -> None:
    artifact = valid_artifacts(tmp_path)[3]
    validate_production_artifact(artifact, root=tmp_path)
    npz_path = tmp_path / artifact["orbit_vector_manifest"]["npz_path"]
    np.savez(npz_path, theta=np.linspace(0.0, 1.0, 5))
    assert_invalid(artifact, tmp_path, "checksum drift")
