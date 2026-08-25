"""Episode 008 Figure 5 production schema contracts and validators.

The validators in this module intentionally implement a conservative subset of
JSON Schema in plain Python.  They are the boundary that downstream production
continuation, validation, interpolation, and browser-display tasks must pass
before an artifact is treated as authoritative Figure 5 data.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

EPISODE8_PRODUCTION_SCHEMA_VERSION = "episode8-figure5-production-v1"
PARAMETER_COORDINATE_CONVENTION = "temperature-log_w-rho-spine-slices-v1"
ORBIT_STATE_CONVENTION = "transformed-state-log_n-log_q-s-v1"
PHASE_COORDINATE_CONVENTION = "normalized-phase-theta-in-[0,1]-periodic-v1"
PERIOD_CONVENTION = "physical-period-seconds-logP-internal-v1"
CHECKSUM_CONVENTION = "sha256-canonical-json-or-file-bytes-v1"

ARTIFACT_KINDS = {
    "continuation-points",
    "continuation-events",
    "run-metadata",
    "curated-orbit-npz-manifest",
    "linearized-period-curve",
    "browser-display-dataset",
}

ARTIFACT_PAYLOAD_KEYS = {
    "continuation-points": "continuation_points",
    "continuation-events": "continuation_events",
    "run-metadata": "run_metadata",
    "curated-orbit-npz-manifest": "orbit_vector_manifest",
    "linearized-period-curve": "linearized_period_rows",
    "browser-display-dataset": "browser_records",
}

UNIT_CONVENTIONS = {
    "temperature": "K",
    "vertical_velocity": "m s^-1",
    "log_vertical_velocity": "ln(m s^-1)",
    "rho": "dimensionless",
    "temperature_hat": "dimensionless",
    "period": "s",
    "eigenvalue_imaginary_part": "rad s^-1",
    "memory": "KiB",
    "wall_clock": "s",
    "cpu_time": "s",
}

VALIDITY_STATUSES = {
    "accepted",
    "resolution_unresolved",
    "near_hopf_stop",
    "tripwire_stop",
    "failed",
    "interpolated",
    "gap",
    "invalid",
    "not_evaluated",
    "external_comparison",
}

SOURCE_FLAGS = {
    "computed_native_adaptive",
    "computed_linearized_equilibrium",
    "unresolved_native_adaptive",
    "interpolated_holdout_validated",
    "explicit_gap",
    "invalid_outside_hopf_domain",
    "not_evaluated",
    "external_digitized_paper_comparison",
}

STATUS_SOURCE_COMPATIBILITY = {
    "accepted": {"computed_native_adaptive", "computed_linearized_equilibrium"},
    "resolution_unresolved": {"unresolved_native_adaptive"},
    "near_hopf_stop": {"computed_native_adaptive"},
    "tripwire_stop": {"computed_native_adaptive"},
    "failed": {"computed_native_adaptive"},
    "interpolated": {"interpolated_holdout_validated"},
    "gap": {"explicit_gap"},
    "invalid": {"invalid_outside_hopf_domain"},
    "not_evaluated": {"not_evaluated"},
    "external_comparison": {"external_digitized_paper_comparison"},
}

EVENT_TYPES = {
    "branch_bootstrap",
    "accepted_step",
    "rejected_step",
    "phase_reference_refresh",
    "remesh_restart",
    "near_hopf_stop",
    "tripwire_stop",
    "resolution_unresolved",
    "gap_record",
    "interpolation_created",
}

BROWSER_RECORD_ROLES = {
    "period_map_cell",
    "temperature_slice_point",
    "hopf_boundary_limit",
    "explicit_gap",
    "external_comparison_overlay",
}

REQUIRED_COORDINATE_CONVENTIONS = {
    "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
    "orbit_state": ORBIT_STATE_CONVENTION,
    "phase": PHASE_COORDINATE_CONVENTION,
    "period": PERIOD_CONVENTION,
}


class ProductionSchemaValidationError(ValueError):
    """Raised when an Episode 008 production artifact violates the schema."""


@dataclass(frozen=True)
class ValidationIssue:
    """A single schema-validation issue."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def canonical_json_bytes(value: object) -> bytes:
    """Return canonical sorted-key UTF-8 JSON bytes with a trailing newline."""

    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file's exact bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_schema_contract() -> dict[str, Any]:
    """Return the language-neutral Episode 008 production schema contract."""

    return {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "contract_kind": "episode8-production-schema-contract",
        "artifact_kinds": sorted(ARTIFACT_KINDS),
        "artifact_payload_keys": dict(sorted(ARTIFACT_PAYLOAD_KEYS.items())),
        "coordinate_conventions": dict(REQUIRED_COORDINATE_CONVENTIONS),
        "unit_conventions": dict(sorted(UNIT_CONVENTIONS.items())),
        "validity_statuses": sorted(VALIDITY_STATUSES),
        "source_flags": sorted(SOURCE_FLAGS),
        "status_source_compatibility": {
            key: sorted(value) for key, value in sorted(STATUS_SOURCE_COMPATIBILITY.items())
        },
        "event_types": sorted(EVENT_TYPES),
        "browser_record_roles": sorted(BROWSER_RECORD_ROLES),
        "provenance_policy": {
            "source_artifacts_required": True,
            "recorded_sha256_required": True,
            "digitized_paper_data_policy": "external-comparison-only",
            "schema_version_must_match": EPISODE8_PRODUCTION_SCHEMA_VERSION,
            "checksum_convention": CHECKSUM_CONVENTION,
        },
    }


def validation_errors(
    artifact: Mapping[str, Any],
    *,
    root: Path | None = None,
    artifact_path: Path | None = None,
    verify_checksums: bool = True,
) -> list[ValidationIssue]:
    """Return all validation issues for an Episode 008 production artifact."""

    validator = _Validator(root=root, artifact_path=artifact_path, verify_checksums=verify_checksums)
    validator.validate_artifact(artifact)
    return validator.issues


def validate_production_artifact(
    artifact: Mapping[str, Any],
    *,
    root: Path | None = None,
    artifact_path: Path | None = None,
    verify_checksums: bool = True,
) -> None:
    """Validate an Episode 008 production artifact or raise one combined error."""

    issues = validation_errors(
        artifact,
        root=root,
        artifact_path=artifact_path,
        verify_checksums=verify_checksums,
    )
    if issues:
        joined = "\n".join(str(issue) for issue in issues)
        raise ProductionSchemaValidationError(joined)


class _Validator:
    def __init__(self, *, root: Path | None, artifact_path: Path | None, verify_checksums: bool) -> None:
        self.root = root
        self.artifact_path = artifact_path
        self.verify_checksums = verify_checksums
        self.issues: list[ValidationIssue] = []

    def error(self, path: str, message: str) -> None:
        self.issues.append(ValidationIssue(path, message))

    def validate_artifact(self, artifact: Mapping[str, Any]) -> None:
        if not isinstance(artifact, Mapping):
            self.error("$", "artifact must be a JSON object")
            return
        schema_version = artifact.get("schema_version")
        if schema_version != EPISODE8_PRODUCTION_SCHEMA_VERSION:
            self.error("$.schema_version", f"expected {EPISODE8_PRODUCTION_SCHEMA_VERSION!r}, got {schema_version!r}")
        artifact_kind = artifact.get("artifact_kind")
        if artifact_kind not in ARTIFACT_KINDS:
            self.error("$.artifact_kind", f"expected one of {sorted(ARTIFACT_KINDS)}, got {artifact_kind!r}")
            return
        if not _nonempty_str(artifact.get("artifact_id")):
            self.error("$.artifact_id", "non-empty artifact_id is required")
        self.validate_method_versions(artifact.get("method_versions"), "$.method_versions")
        self.validate_coordinate_conventions(artifact.get("coordinate_conventions"), "$.coordinate_conventions")
        self.validate_provenance(artifact.get("provenance"), "$.provenance")
        payload_key = ARTIFACT_PAYLOAD_KEYS[artifact_kind]
        if payload_key not in artifact:
            self.error(f"$.{payload_key}", f"payload key required for artifact_kind {artifact_kind!r}")
            return
        if artifact_kind == "continuation-points":
            self.validate_continuation_points(artifact[payload_key], f"$.{payload_key}")
        elif artifact_kind == "continuation-events":
            self.validate_continuation_events(artifact[payload_key], f"$.{payload_key}")
        elif artifact_kind == "run-metadata":
            self.validate_run_metadata(artifact[payload_key], f"$.{payload_key}")
        elif artifact_kind == "curated-orbit-npz-manifest":
            self.validate_orbit_manifest(artifact[payload_key], f"$.{payload_key}")
        elif artifact_kind == "linearized-period-curve":
            self.validate_linearized_period_rows(artifact[payload_key], f"$.{payload_key}")
        elif artifact_kind == "browser-display-dataset":
            self.validate_browser_records(artifact[payload_key], f"$.{payload_key}")

    def validate_method_versions(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping) or not value:
            self.error(path, "non-empty method_versions object is required")
            return
        schema = value.get("schema")
        if schema != EPISODE8_PRODUCTION_SCHEMA_VERSION:
            self.error(f"{path}.schema", f"must equal {EPISODE8_PRODUCTION_SCHEMA_VERSION!r}")
        for key, item in value.items():
            if not _nonempty_str(key) or not _nonempty_str(item):
                self.error(f"{path}.{key}", "method-version keys and values must be non-empty strings")

    def validate_coordinate_conventions(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "coordinate_conventions object is required")
            return
        for key, expected in REQUIRED_COORDINATE_CONVENTIONS.items():
            if value.get(key) != expected:
                self.error(f"{path}.{key}", f"must equal {expected!r}")

    def validate_provenance(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "provenance object is required")
            return
        if value.get("digitized_paper_data_policy") != "external-comparison-only":
            self.error(f"{path}.digitized_paper_data_policy", "must be 'external-comparison-only'")
        if not _nonempty_str(value.get("task")):
            self.error(f"{path}.task", "task identifier is required")
        if not _nonempty_str(value.get("created_by")):
            self.error(f"{path}.created_by", "created_by is required")
        source_artifacts = value.get("source_artifacts")
        if not isinstance(source_artifacts, Sequence) or isinstance(source_artifacts, (str, bytes)) or not source_artifacts:
            self.error(f"{path}.source_artifacts", "at least one source artifact with path and sha256 is required")
            return
        for index, record in enumerate(source_artifacts):
            self.validate_artifact_record(record, f"{path}.source_artifacts[{index}]")

    def validate_artifact_record(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "source artifact record must be an object")
            return
        if not _nonempty_str(value.get("path")):
            self.error(f"{path}.path", "source artifact path is required")
        if not _is_sha256(value.get("sha256")):
            self.error(f"{path}.sha256", "source artifact sha256 must be a 64-character hexadecimal digest")
        if not _nonempty_str(value.get("role")):
            self.error(f"{path}.role", "source artifact role is required")
        if self.verify_checksums and _nonempty_str(value.get("path")) and _is_sha256(value.get("sha256")):
            self.verify_file_checksum(value["path"], value["sha256"], f"{path}.sha256")

    def verify_file_checksum(self, relative_or_absolute: str, expected: str, path: str) -> None:
        file_path = Path(relative_or_absolute)
        if not file_path.is_absolute():
            base = self.root
            if base is None and self.artifact_path is not None:
                base = self.artifact_path.parent
            if base is None:
                return
            file_path = base / file_path
        if not file_path.is_file():
            self.error(path, f"referenced file does not exist: {file_path}")
            return
        actual = sha256_file(file_path)
        if actual != expected:
            self.error(path, f"checksum drift for {file_path}: expected {expected}, got {actual}")

    def validate_continuation_points(self, value: Any, path: str) -> None:
        records = self.require_nonempty_list(value, path)
        for index, record in enumerate(records):
            record_path = f"{path}[{index}]"
            self.validate_common_record(record, record_path)
            if isinstance(record, Mapping):
                self.validate_period(record.get("period"), f"{record_path}.period", quantity="nonlinear_period", allow_null=False)
                if "orbit_vector_ref" not in record:
                    self.error(f"{record_path}.orbit_vector_ref", "continuation points must reference a curated orbit vector or explicit gap record")

    def validate_continuation_events(self, value: Any, path: str) -> None:
        records = self.require_nonempty_list(value, path)
        for index, record in enumerate(records):
            record_path = f"{path}[{index}]"
            if not isinstance(record, Mapping):
                self.error(record_path, "event record must be an object")
                continue
            if not _nonempty_str(record.get("event_id")):
                self.error(f"{record_path}.event_id", "event_id is required")
            if record.get("event_type") not in EVENT_TYPES:
                self.error(f"{record_path}.event_type", f"expected one of {sorted(EVENT_TYPES)}")
            self.validate_coordinates(record.get("coordinates"), f"{record_path}.coordinates")
            self.validate_validity(record.get("validity"), f"{record_path}.validity")
            self.validate_method_versions(record.get("method_versions"), f"{record_path}.method_versions")
            if "period" in record:
                self.validate_period(record.get("period"), f"{record_path}.period", quantity="nonlinear_period", allow_null=True)

    def validate_run_metadata(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "run_metadata must be an object")
            return
        for key in ("run_id", "backend", "executable_identity", "build_identity"):
            if key not in value:
                self.error(f"{path}.{key}", "run metadata field is required")
        self.validate_coordinate_domain(value.get("coordinate_domain"), f"{path}.coordinate_domain")
        resources = value.get("resource_accounting")
        if not isinstance(resources, Mapping):
            self.error(f"{path}.resource_accounting", "resource accounting with units is required")
        else:
            self.validate_quantity(resources.get("wall_clock"), f"{path}.resource_accounting.wall_clock", "s", positive=True)
            self.validate_quantity(resources.get("cpu_time"), f"{path}.resource_accounting.cpu_time", "s", nonnegative=True)
            self.validate_quantity(resources.get("max_rss"), f"{path}.resource_accounting.max_rss", "KiB", positive=True)
        terminal = value.get("terminal_status_counts")
        if not isinstance(terminal, Mapping):
            self.error(f"{path}.terminal_status_counts", "terminal_status_counts object is required")
        else:
            for status in terminal:
                if status not in VALIDITY_STATUSES:
                    self.error(f"{path}.terminal_status_counts.{status}", "unknown terminal status")

    def validate_orbit_manifest(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "orbit_vector_manifest must be an object")
            return
        if not _nonempty_str(value.get("npz_path")):
            self.error(f"{path}.npz_path", "npz_path is required")
        if not _is_sha256(value.get("npz_sha256")):
            self.error(f"{path}.npz_sha256", "npz_sha256 must be a 64-character hexadecimal digest")
        elif self.verify_checksums and _nonempty_str(value.get("npz_path")):
            self.verify_file_checksum(value["npz_path"], value["npz_sha256"], f"{path}.npz_sha256")
        arrays = value.get("arrays")
        if not isinstance(arrays, Mapping) or not arrays:
            self.error(f"{path}.arrays", "non-empty arrays schema is required")
            return
        for name, schema in arrays.items():
            array_path = f"{path}.arrays.{name}"
            if not _nonempty_str(name) or not isinstance(schema, Mapping):
                self.error(array_path, "array schemas must be keyed objects")
                continue
            if schema.get("dtype") != "float64":
                self.error(f"{array_path}.dtype", "curated orbit arrays must be float64")
            if schema.get("byte_order") != "little-endian":
                self.error(f"{array_path}.byte_order", "curated orbit arrays must be little-endian")
            shape = schema.get("shape")
            if not isinstance(shape, Sequence) or isinstance(shape, (str, bytes)) or not all(isinstance(item, int) and item >= 0 for item in shape):
                self.error(f"{array_path}.shape", "shape must be a list of non-negative integers")
            if not _nonempty_str(schema.get("role")):
                self.error(f"{array_path}.role", "array role is required")
            if "unit" in schema and schema["unit"] not in set(UNIT_CONVENTIONS.values()) | {"mixed", "dimensionless"}:
                self.error(f"{array_path}.unit", "array unit is not in the production unit convention")
            if "sha256" in schema and not _is_sha256(schema.get("sha256")):
                self.error(f"{array_path}.sha256", "array checksum must be a SHA-256 digest")

    def validate_linearized_period_rows(self, value: Any, path: str) -> None:
        records = self.require_nonempty_list(value, path)
        for index, record in enumerate(records):
            record_path = f"{path}[{index}]"
            self.validate_common_record(record, record_path)
            if isinstance(record, Mapping):
                coordinates = record.get("coordinates")
                if isinstance(coordinates, Mapping):
                    temperature = _quantity_value(coordinates.get("temperature"))
                    if temperature is not None and not math.isclose(temperature, 210.0, rel_tol=0.0, abs_tol=1e-12):
                        self.error(f"{record_path}.coordinates.temperature.value", "linearized-period rows are restricted to T=210 K")
                validity = record.get("validity")
                status = validity.get("status") if isinstance(validity, Mapping) else None
                allow_null = status in {"gap", "invalid", "failed", "not_evaluated", "resolution_unresolved"}
                self.validate_period(record.get("period"), f"{record_path}.period", quantity="linearized_period", allow_null=allow_null)
                self.validate_quantity(
                    record.get("eigenvalue_imaginary_part"),
                    f"{record_path}.eigenvalue_imaginary_part",
                    "rad s^-1",
                    positive=not allow_null,
                    allow_null=allow_null,
                )

    def validate_browser_records(self, value: Any, path: str) -> None:
        records = self.require_nonempty_list(value, path)
        for index, record in enumerate(records):
            record_path = f"{path}[{index}]"
            self.validate_common_record(record, record_path)
            if not isinstance(record, Mapping):
                continue
            role = record.get("record_role")
            if role not in BROWSER_RECORD_ROLES:
                self.error(f"{record_path}.record_role", f"expected one of {sorted(BROWSER_RECORD_ROLES)}")
            validity_value = record.get("validity")
            validity: Mapping[str, Any] = validity_value if isinstance(validity_value, Mapping) else {}
            status = validity.get("status")
            source = validity.get("source")
            allow_null = status in {"gap", "invalid", "not_evaluated", "resolution_unresolved", "failed"}
            self.validate_period(record.get("display_period"), f"{record_path}.display_period", quantity="display_period", allow_null=allow_null)
            if status == "interpolated":
                interpolation = record.get("interpolation")
                if not isinstance(interpolation, Mapping):
                    self.error(f"{record_path}.interpolation", "interpolated records require interpolation provenance")
                else:
                    source_ids = interpolation.get("source_point_ids")
                    if not isinstance(source_ids, Sequence) or isinstance(source_ids, (str, bytes)) or len(source_ids) < 3:
                        self.error(f"{record_path}.interpolation.source_point_ids", "at least three source point ids are required")
                    holdout = interpolation.get("holdout_validation")
                    if not isinstance(holdout, Mapping) or holdout.get("status") != "passed":
                        self.error(f"{record_path}.interpolation.holdout_validation", "holdout validation must be present and passed")
            elif "interpolation" in record:
                self.error(f"{record_path}.interpolation", "only records with validity.status='interpolated' may carry interpolation data")
            if source == "external_digitized_paper_comparison":
                if validity.get("authoritative") is not False or role != "external_comparison_overlay":
                    self.error(
                        f"{record_path}.validity",
                        "digitized paper records must be non-authoritative external comparison overlays",
                    )

    def validate_common_record(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "record must be an object")
            return
        if not _nonempty_str(value.get("record_id")):
            self.error(f"{path}.record_id", "record_id is required")
        self.validate_coordinates(value.get("coordinates"), f"{path}.coordinates")
        self.validate_validity(value.get("validity"), f"{path}.validity")
        self.validate_method_versions(value.get("method_versions"), f"{path}.method_versions")

    def validate_coordinates(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "coordinates object is required")
            return
        if value.get("convention") != PARAMETER_COORDINATE_CONVENTION:
            self.error(f"{path}.convention", f"must equal {PARAMETER_COORDINATE_CONVENTION!r}")
        self.validate_quantity(value.get("temperature"), f"{path}.temperature", "K")
        self.validate_quantity(value.get("log_w"), f"{path}.log_w", "ln(m s^-1)")
        self.validate_quantity(value.get("w"), f"{path}.w", "m s^-1", positive=True)
        if "rho" in value:
            self.validate_quantity(value.get("rho"), f"{path}.rho", "dimensionless", allow_null=True)
        if "temperature_hat" in value:
            self.validate_quantity(value.get("temperature_hat"), f"{path}.temperature_hat", "dimensionless", allow_null=True)

    def validate_coordinate_domain(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "coordinate_domain object is required")
            return
        if value.get("convention") != PARAMETER_COORDINATE_CONVENTION:
            self.error(f"{path}.convention", f"must equal {PARAMETER_COORDINATE_CONVENTION!r}")
        for key, unit in (("temperature", "K"), ("log_w", "ln(m s^-1)"), ("rho", "dimensionless")):
            bounds = value.get(key)
            if not isinstance(bounds, Mapping):
                self.error(f"{path}.{key}", "coordinate-domain bounds are required")
                continue
            if bounds.get("unit") != unit:
                self.error(f"{path}.{key}.unit", f"must equal {unit!r}")
            minimum = _finite_float(bounds.get("min"))
            maximum = _finite_float(bounds.get("max"))
            if minimum is None or maximum is None:
                self.error(f"{path}.{key}", "min/max must be finite and ordered")
            elif minimum > maximum:
                self.error(f"{path}.{key}", "min/max must be finite and ordered")

    def validate_validity(self, value: Any, path: str) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "validity object is required")
            return
        if "sources" in value or isinstance(value.get("source"), Sequence) and not isinstance(value.get("source"), (str, bytes)):
            self.error(path, "exactly one unambiguous source flag is required; do not use sources lists")
        status = value.get("status")
        source = value.get("source")
        if status not in VALIDITY_STATUSES:
            self.error(f"{path}.status", f"expected one of {sorted(VALIDITY_STATUSES)}")
        if source not in SOURCE_FLAGS:
            self.error(f"{path}.source", f"expected one of {sorted(SOURCE_FLAGS)}")
        if status in STATUS_SOURCE_COMPATIBILITY and source in SOURCE_FLAGS:
            allowed = STATUS_SOURCE_COMPATIBILITY[status]
            if source not in allowed:
                self.error(f"{path}.source", f"source {source!r} is incompatible with status {status!r}; expected {sorted(allowed)}")
        if status in {"resolution_unresolved", "gap", "failed", "near_hopf_stop", "tripwire_stop", "invalid", "not_evaluated"}:
            if not _nonempty_str(value.get("reason")):
                self.error(f"{path}.reason", f"status {status!r} requires an explicit reason")
        authoritative = value.get("authoritative")
        if not isinstance(authoritative, bool):
            self.error(f"{path}.authoritative", "authoritative boolean is required")
        if source in {"explicit_gap", "unresolved_native_adaptive", "not_evaluated", "external_digitized_paper_comparison"} and authoritative is True:
            self.error(f"{path}.authoritative", f"source {source!r} cannot be authoritative production data")

    def validate_period(self, value: Any, path: str, *, quantity: str, allow_null: bool) -> None:
        if value is None and allow_null:
            return
        if not isinstance(value, Mapping):
            self.error(path, "period object is required")
            return
        if value.get("quantity") != quantity:
            self.error(f"{path}.quantity", f"must equal {quantity!r}")
        self.validate_quantity(value, path, "s", positive=not allow_null, allow_null=allow_null)
        if "log_value" in value and value["log_value"] is not None and not _finite_number(value["log_value"]):
            self.error(f"{path}.log_value", "log_value must be finite or null")

    def validate_quantity(
        self,
        value: Any,
        path: str,
        unit: str,
        *,
        positive: bool = False,
        nonnegative: bool = False,
        allow_null: bool = False,
    ) -> None:
        if not isinstance(value, Mapping):
            self.error(path, "quantity object is required")
            return
        if value.get("unit") != unit:
            self.error(f"{path}.unit", f"must equal {unit!r}")
        raw = value.get("value")
        if raw is None and allow_null:
            return
        raw_float = _finite_float(raw)
        if raw_float is None:
            self.error(f"{path}.value", "value must be finite")
            return
        if positive and raw_float <= 0:
            self.error(f"{path}.value", "value must be positive")
        if nonnegative and raw_float < 0:
            self.error(f"{path}.value", "value must be non-negative")

    def require_nonempty_list(self, value: Any, path: str) -> list[Any]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
            self.error(path, "non-empty list is required")
            return []
        return list(value)


def _finite_number(value: Any) -> bool:
    return _finite_float(value) is not None


def _finite_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _quantity_value(value: Any) -> float | None:
    if isinstance(value, Mapping) and _finite_number(value.get("value")):
        return float(value["value"])
    return None
