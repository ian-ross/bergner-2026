"""Durable native adaptive LOCA driver orchestration helpers.

The classes in this module deliberately separate *orchestration* from the heavy
Trilinos/LOCA numerical work.  A backend object executes fixed-mesh LOCA
segments and remesh/restart corrections; :class:`NativeAdaptiveDriver` owns the
versioned segment lifecycle, event accounting, deterministic retry order,
checkpoints, resume validation, and run manifest bookkeeping.  This lets tests
exercise interruption/resume and stale-checkpoint behavior with a scripted
backend while production scripts can provide a backend that shells out to the
native executable.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import resource
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Mapping, Protocol, Sequence

from .adaptive_orbits import RESTART_RETRY_VERSION, restart_plan
from .periodic_seed import sha256_file

NATIVE_ADAPTIVE_DRIVER_SCHEMA_VERSION = "episode008-native-adaptive-driver-v1"
NATIVE_ADAPTIVE_CHECKPOINT_SCHEMA_VERSION = "episode008-native-adaptive-checkpoint-v1"

TERMINAL_STATUS_ALLOWED_VALUES = (
    "accepted",
    "resolution_unresolved",
    "near_hopf_stop",
    "tripwire_stop",
    "failed",
)

CONTINUE_ACTIONS = {"ordinary_h_r", "forced_single_split_h_r", "mesh_cap_escalation", "pure_r"}
SINGLE_VALUED_TRIPWIRE_VERSION = "single-valued-tripwire-v1"
SINGLE_VALUED_COORDINATE_TOLERANCE = 1.0e-4
SINGLE_VALUED_PERIOD_RELATIVE_TOLERANCE = 1.0e-3
SINGLE_VALUED_WEIGHTED_ORBIT_TOLERANCE = 1.0e-2
RADAU_TRIGGER_KEYS = (
    "defect_below_1e-4_but_convergence_failed",
    "period_or_defect_stagnation_before_mesh_cap",
    "polynomial_ringing",
    "nonphysical_value",
    "broader_ivp_based",
    "floquet_dependent",
)
NOT_EVALUATED_THROUGH_TASK_068 = {
    "broader_ivp_based": "not_evaluated_through_TASK_068",
    "floquet_dependent": "not_evaluated_through_TASK_068",
}


class SegmentLifecycleState(StrEnum):
    """Versioned lifecycle states for one native adaptive segment."""

    PENDING = "pending"
    RUNNING_FIXED_MESH = "running_fixed_mesh"
    REMESH_PENDING = "remesh_pending"
    RESTART_PENDING = "restart_pending"
    ACCEPTED = "accepted"
    UNRESOLVED = "unresolved"
    TRIPWIRE_STOP = "tripwire_stop"
    NEAR_HOPF_STOP = "near_hopf_stop"
    FAILED = "failed"


class StaleCheckpointError(RuntimeError):
    """Raised when a run manifest/checkpoint cannot be resumed safely."""


class NativeAdaptiveBackend(Protocol):
    """Numerical backend required by :class:`NativeAdaptiveDriver`."""

    def run_fixed_mesh_segment(
        self,
        target: Mapping[str, Any],
        *,
        cycle_index: int,
        restart_state: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        """Execute one native fixed-mesh LOCA segment and return segment evidence."""
        ...

    def decide_remesh(
        self,
        target: Mapping[str, Any],
        segment: Mapping[str, Any],
        *,
        cycle_index: int,
    ) -> Mapping[str, Any]:
        """Return the adaptive cycle decision for an accepted segment boundary."""
        ...

    def restart_after_remesh(
        self,
        target: Mapping[str, Any],
        segment: Mapping[str, Any],
        decision: Mapping[str, Any],
        *,
        cycle_index: int,
        attempt_order: Sequence[str],
    ) -> Mapping[str, Any]:
        """Execute deterministic remesh/restart attempts and return restart evidence."""
        ...


@dataclass(frozen=True)
class NativeAdaptiveDriverConfig:
    """Run-level identity used to validate manifests and checkpoints."""

    run_id: str
    run_directory: Path
    targets: tuple[Mapping[str, Any], ...]
    configuration: Mapping[str, Any] = field(default_factory=dict)
    source_paths: tuple[Path, ...] = ()
    source_root: Path | None = None
    executable_path: Path | None = None
    executable_identity: Mapping[str, Any] = field(default_factory=dict)
    vector_fingerprints: Mapping[str, str] = field(default_factory=dict)
    max_cycles_per_target: int = 8
    schema_version: str = NATIVE_ADAPTIVE_DRIVER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.max_cycles_per_target < 1:
            raise ValueError("max_cycles_per_target must be positive")
        if not self.targets:
            raise ValueError("at least one target is required")
        target_ids = [str(target.get("target_id", "")) for target in self.targets]
        if any(not target_id for target_id in target_ids):
            raise ValueError("every target requires a non-empty target_id")
        if len(set(target_ids)) != len(target_ids):
            raise ValueError("target_id values must be unique")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: object) -> bytes:
    """Return the canonical JSON byte representation used for fingerprints."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically write a deterministic pretty JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    body = (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    tmp.write_bytes(body)
    os.replace(tmp, path)


def _relative_or_absolute(path: Path, root: Path | None) -> str:
    resolved = path.resolve()
    if root is None:
        return resolved.as_posix()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def source_fingerprints(paths: Sequence[Path], *, source_root: Path | None = None) -> dict[str, str]:
    """Hash source files for stale-checkpoint rejection."""

    records: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        records[_relative_or_absolute(path, source_root)] = sha256_file(path)
    return dict(sorted(records.items()))


def executable_fingerprint(path: Path | None) -> dict[str, Any]:
    """Return a stable executable identity record."""

    if path is None:
        return {"path": None, "sha256": None, "exists": False}
    return {
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "exists": path.is_file(),
    }


def build_run_fingerprints(config: NativeAdaptiveDriverConfig) -> dict[str, Any]:
    """Build the complete resume-compatibility fingerprint bundle."""

    target_manifest = [dict(target) for target in config.targets]
    return {
        "schema_version": config.schema_version,
        "checkpoint_schema_version": NATIVE_ADAPTIVE_CHECKPOINT_SCHEMA_VERSION,
        "source_fingerprints": source_fingerprints(config.source_paths, source_root=config.source_root),
        "executable": executable_fingerprint(config.executable_path),
        "executable_identity": dict(config.executable_identity),
        "vector_fingerprints": dict(sorted(config.vector_fingerprints.items())),
        "configuration_sha256": canonical_sha256(config.configuration),
        "target_manifest_sha256": canonical_sha256(target_manifest),
    }


def fingerprint_bundle_sha256(fingerprints: Mapping[str, Any]) -> str:
    return canonical_sha256(fingerprints)


def _as_float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and result not in (float("inf"), float("-inf")) else None


def evaluate_single_valued_tripwire(points: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate the documented TASK-068 cheap single-valuedness tripwire.

    The native adaptive run is expected to stop a slice, not choose a branch, if
    a tangent sign change, normalized-coordinate reversal, or duplicate
    coordinate with incompatible period/orbit evidence is observed.  Empty or
    single-point slices are recorded truthfully as not evaluated.
    """

    records = [dict(point) for point in points]
    if len(records) < 2:
        return {
            "version": SINGLE_VALUED_TRIPWIRE_VERSION,
            "status": "not_evaluated",
            "reason": "fewer_than_two_accepted_points",
            "trigger_count": 0,
            "triggers": [],
        }

    def coordinate(point: Mapping[str, Any]) -> float | None:
        for key in ("normalized_coordinate", "active_coordinate", "coordinate", "rho", "temperature_hat"):
            if key in point:
                return _as_float_or_none(point[key])
        return None

    def tangent_sign(point: Mapping[str, Any]) -> int | None:
        for key in ("active_tangent_sign", "tangent_sign"):
            if key in point:
                value = _as_float_or_none(point[key])
                if value is None or value == 0.0:
                    return None
                return 1 if value > 0.0 else -1
        value = _as_float_or_none(point.get("active_tangent_component"))
        if value is None or value == 0.0:
            return None
        return 1 if value > 0.0 else -1

    def period(point: Mapping[str, Any]) -> float | None:
        return _as_float_or_none(point.get("period_s", point.get("period")))

    def orbit_marker(point: Mapping[str, Any]) -> float | None:
        for key in ("weighted_orbit_marker", "weighted_orbit_coordinate", "phase_aligned_weighted_orbit_distance"):
            if key in point:
                return _as_float_or_none(point[key])
        return None

    triggers: list[dict[str, Any]] = []
    coordinates = [coordinate(point) for point in records]
    tangent_signs = [tangent_sign(point) for point in records]
    for index, (previous, current) in enumerate(zip(tangent_signs[:-1], tangent_signs[1:]), start=1):
        if previous is not None and current is not None and previous * current < 0:
            triggers.append({
                "kind": "active_coordinate_tangent_sign_change",
                "point_index": index,
                "previous_sign": previous,
                "current_sign": current,
            })

    reference_direction: int | None = None
    for index, (previous, current) in enumerate(zip(coordinates[:-1], coordinates[1:]), start=1):
        if previous is None or current is None:
            continue
        delta = current - previous
        if abs(delta) <= SINGLE_VALUED_COORDINATE_TOLERANCE:
            continue
        sign = 1 if delta > 0.0 else -1
        if reference_direction is None:
            reference_direction = sign
        elif sign != reference_direction:
            triggers.append({
                "kind": "normalized_coordinate_reversal",
                "point_index": index,
                "delta": delta,
                "threshold": SINGLE_VALUED_COORDINATE_TOLERANCE,
            })

    for i, first in enumerate(records):
        ci = coordinates[i]
        if ci is None:
            continue
        pi = period(first)
        oi = orbit_marker(first)
        for j in range(i + 1, len(records)):
            cj = coordinates[j]
            if cj is None or abs(cj - ci) > SINGLE_VALUED_COORDINATE_TOLERANCE:
                continue
            pj = period(records[j])
            oj = orbit_marker(records[j])
            period_rel = None if pi is None or pj is None else abs(pj - pi) / max(1.0, abs(pi), abs(pj))
            orbit_diff = None if oi is None or oj is None else abs(oj - oi)
            if ((period_rel is not None and period_rel > SINGLE_VALUED_PERIOD_RELATIVE_TOLERANCE)
                    or (orbit_diff is not None and orbit_diff > SINGLE_VALUED_WEIGHTED_ORBIT_TOLERANCE)):
                triggers.append({
                    "kind": "duplicate_coordinate_incompatible_orbit",
                    "first_point_index": i,
                    "second_point_index": j,
                    "coordinate_difference": abs(cj - ci),
                    "period_relative_difference": period_rel,
                    "weighted_orbit_difference": orbit_diff,
                    "coordinate_threshold": SINGLE_VALUED_COORDINATE_TOLERANCE,
                    "period_relative_threshold": SINGLE_VALUED_PERIOD_RELATIVE_TOLERANCE,
                    "weighted_orbit_threshold": SINGLE_VALUED_WEIGHTED_ORBIT_TOLERANCE,
                })

    return {
        "version": SINGLE_VALUED_TRIPWIRE_VERSION,
        "status": "tripwire_stop" if triggers else "single_valued_observed",
        "trigger_count": len(triggers),
        "triggers": triggers,
    }


def partition_loca_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Partition LOCA save/callback records into accepted/rejected accounting fields."""

    callbacks = list(events)
    accepted = [event for event in callbacks if event.get("status") == "accepted" or event.get("accepted") is True]
    rejected = [event for event in callbacks if event.get("status") == "rejected" or event.get("accepted") is False]
    initial = [event for event in callbacks if event.get("save_role") == "initial"]
    regular = [event for event in callbacks if event.get("save_role") == "regular"]
    final = [event for event in callbacks if event.get("save_role") == "final"]
    remesh_candidates = [event for event in callbacks if event.get("remesh_boundary_candidate")]
    invalid_boundary = [event for event in remesh_candidates if event not in accepted]
    callback_indices = [event.get("callback_index") for event in callbacks if "callback_index" in event]
    contiguous = callback_indices == list(range(len(callback_indices))) if callback_indices else True
    return {
        "callback_count": len(callbacks),
        "accepted_callback_count": len(accepted),
        "rejected_callback_count": len(rejected),
        "initial_save_count": len(initial),
        "regular_save_count": len(regular),
        "final_save_count": len(final),
        "remesh_boundary_candidate_count": len(remesh_candidates),
        "rejected_remesh_boundary_count": len(invalid_boundary),
        "callback_indices_contiguous": contiguous,
        "saved_points_equal_accepted_callbacks": len(accepted) == sum(1 for event in callbacks if event.get("vector_key") or event.get("point_index") is not None),
    }


def _resource_snapshot(start_wall: float, start_cpu: float, start_rss: int) -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "segment_wall_clock_s": max(0.0, time.perf_counter() - start_wall),
        "segment_cpu_s": max(0.0, (usage.ru_utime + usage.ru_stime) - start_cpu),
        "segment_max_rss_kib": max(start_rss, int(usage.ru_maxrss)),
    }


def _default_diagnostics(segment: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = dict(segment.get("diagnostics", {}))
    diagnostics.setdefault("defects", segment.get("defects", {}))
    diagnostics.setdefault("convergence", segment.get("convergence", {}))
    diagnostics.setdefault("phase_lineage", segment.get("phase_lineage", []))
    diagnostics.setdefault("mesh_history", segment.get("mesh_history", []))
    diagnostics.setdefault("transfer_correction_details", segment.get("transfer_correction_details", []))
    return diagnostics


def _collect_rejection_reasons(
    fixed: Mapping[str, Any],
    decision: Mapping[str, Any],
    restart: Mapping[str, Any] | None,
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    for event in events:
        if event.get("status") == "rejected" or event.get("accepted") is False:
            event_reasons = event.get("rejection_reasons", event.get("reason"))
            if event_reasons is None:
                event_reasons = "rejected_callback"
            if isinstance(event_reasons, str):
                event_reasons = [event_reasons]
            reasons.append({
                "source": "loca_event",
                "callback_index": event.get("callback_index"),
                "reasons": list(event_reasons),
            })
    for source_name, payload in (("fixed_mesh_segment", fixed), ("adaptive_decision", decision)):
        payload_reasons = payload.get("rejection_reasons", payload.get("reasons", payload.get("reason")))
        if payload_reasons:
            if isinstance(payload_reasons, str):
                payload_reasons = [payload_reasons]
            reasons.append({"source": source_name, "reasons": list(payload_reasons)})
    if restart is not None and not restart.get("accepted", restart.get("status") == "accepted"):
        payload_reasons = restart.get("rejection_reasons", restart.get("reason", "remesh_restart_failed"))
        if isinstance(payload_reasons, str):
            payload_reasons = [payload_reasons]
        reasons.append({"source": "restart", "reasons": list(payload_reasons)})
    return reasons


def native_adaptive_diagnostics(
    fixed: Mapping[str, Any],
    decision: Mapping[str, Any],
    restart: Mapping[str, Any] | None,
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Normalize native adaptive diagnostic channels for manifests/checkpoints.

    Missing channels are filled with explicit empty or not-evaluated values so a
    later successful retry cannot erase failed callbacks, cap escalations,
    unresolved evidence, or TASK-068 deferred IVP/Floquet boundaries.
    """

    diagnostics = _default_diagnostics(fixed)
    diagnostics.setdefault("cap_escalations", fixed.get("cap_escalations", []))
    if decision.get("action") == "mesh_cap_escalation":
        diagnostics["cap_escalations"] = [
            *diagnostics["cap_escalations"],
            {
                "kind": "mesh_cap_escalation",
                "cycle_decision_version": decision.get("version"),
                "reasons": list(decision.get("reasons", ("soft_cap_failed_after_corrected_cycle",))),
                "permit_hard_cap": bool(decision.get("permit_hard_cap", True)),
            },
        ]
    diagnostics.setdefault("aliasing_events", fixed.get("aliasing_events", []))
    radau = dict(diagnostics.get("radau_triggers", fixed.get("active_radau_triggers", {})))
    for key in RADAU_TRIGGER_KEYS:
        radau.setdefault(key, NOT_EVALUATED_THROUGH_TASK_068.get(key, "not_evaluated"))
    radau["broader_ivp_based"] = NOT_EVALUATED_THROUGH_TASK_068["broader_ivp_based"]
    radau["floquet_dependent"] = NOT_EVALUATED_THROUGH_TASK_068["floquet_dependent"]
    diagnostics["radau_triggers"] = radau
    diagnostics.setdefault("single_valued_tripwire", evaluate_single_valued_tripwire(fixed.get("points", [])))
    diagnostics["rejection_reasons"] = _collect_rejection_reasons(fixed, decision, restart, events)
    preserved: list[dict[str, Any]] = []
    if decision.get("terminal_status") in {"failed", "resolution_unresolved", "tripwire_stop", "near_hopf_stop"}:
        preserved.append({
            "source": "adaptive_decision",
            "terminal_status": decision.get("terminal_status"),
            "reason": decision.get("reason", decision.get("reasons")),
        })
    if restart is not None and not restart.get("accepted", restart.get("status") == "accepted"):
        preserved.append({
            "source": "restart",
            "terminal_status": "failed",
            "reason": restart.get("rejection_reasons", restart.get("reason", "remesh_restart_failed")),
        })
    diagnostics["failed_or_unresolved_points_preserved"] = preserved
    diagnostics["not_evaluated_evidence"] = dict(NOT_EVALUATED_THROUGH_TASK_068)
    return diagnostics


def _terminal_state(status: str) -> SegmentLifecycleState:
    if status == "accepted":
        return SegmentLifecycleState.ACCEPTED
    if status == "resolution_unresolved":
        return SegmentLifecycleState.UNRESOLVED
    if status == "near_hopf_stop":
        return SegmentLifecycleState.NEAR_HOPF_STOP
    if status == "tripwire_stop":
        return SegmentLifecycleState.TRIPWIRE_STOP
    return SegmentLifecycleState.FAILED


class NativeAdaptiveDriver:
    """Orchestrate native fixed-mesh LOCA segments with durable resume state."""

    def __init__(
        self,
        config: NativeAdaptiveDriverConfig,
        backend: NativeAdaptiveBackend,
        *,
        manifest: dict[str, Any] | None = None,
    ) -> None:
        self.config = config
        self.backend = backend
        self.run_directory = config.run_directory
        self.manifest_path = self.run_directory / "manifest.json"
        self.checkpoint_directory = self.run_directory / "checkpoints"
        self.fingerprints = build_run_fingerprints(config)
        self.fingerprints_sha256 = fingerprint_bundle_sha256(self.fingerprints)
        self.manifest = manifest if manifest is not None else self._new_manifest()

    @classmethod
    def resume(cls, config: NativeAdaptiveDriverConfig, backend: NativeAdaptiveBackend) -> "NativeAdaptiveDriver":
        """Load an existing run and reject stale/incompatible state."""

        manifest_path = config.run_directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        driver = cls(config, backend, manifest=manifest)
        driver.validate_resume_state()
        return driver

    def _new_manifest(self) -> dict[str, Any]:
        now = _utc_now()
        return {
            "schema_version": self.config.schema_version,
            "artifact_kind": "native-adaptive-driver-run-manifest",
            "run_id": self.config.run_id,
            "status": "initialized",
            "created_at": now,
            "updated_at": now,
            "fingerprints": self.fingerprints,
            "fingerprints_sha256": self.fingerprints_sha256,
            "lifecycle_states": [state.value for state in SegmentLifecycleState],
            "terminal_status_allowed_values": list(TERMINAL_STATUS_ALLOWED_VALUES),
            "retry_policies": {
                "version": RESTART_RETRY_VERSION,
                "h+r": [attempt.name for attempt in restart_plan(remesh_kind="h+r").attempts],
                "pure-r": [attempt.name for attempt in restart_plan(remesh_kind="pure-r").attempts],
                "tangent_only_failure": [
                    attempt.name for attempt in restart_plan(remesh_kind="h+r", tangent_only_failure=True).attempts
                ],
                "tangent_policy": "renormalize transferred tangent; deterministic two-point rebootstrap only for tangent-only failure",
            },
            "configuration": copy.deepcopy(dict(self.config.configuration)),
            "target_manifest": [copy.deepcopy(dict(target)) for target in self.config.targets],
            "target_status": {
                str(target["target_id"]): {"terminal_status": "pending", "completed_segment_id": None}
                for target in self.config.targets
            },
            "segments": [],
            "resource_accounting": {
                "segment_wall_clock_s": 0.0,
                "segment_cpu_s": 0.0,
                "max_rss_kib": 0,
            },
            "resume": {"latest_complete_segment_id": None, "complete_checkpoint_count": 0},
        }

    def validate_resume_state(self) -> None:
        """Validate manifest and every completed checkpoint against current fingerprints."""

        if self.manifest.get("schema_version") != self.config.schema_version:
            raise StaleCheckpointError("manifest schema_version is incompatible")
        if self.manifest.get("fingerprints") != self.fingerprints:
            raise StaleCheckpointError("manifest fingerprints do not match current schema/source/executable/vector/configuration/targets")
        if self.manifest.get("fingerprints_sha256") != self.fingerprints_sha256:
            raise StaleCheckpointError("manifest fingerprint digest is stale")
        for segment in self.manifest.get("segments", []):
            if not segment.get("checkpoint_complete"):
                continue
            checkpoint_path = self.run_directory / segment["checkpoint_path"]
            checkpoint = json.loads(checkpoint_path.read_text())
            if checkpoint.get("schema_version") != NATIVE_ADAPTIVE_CHECKPOINT_SCHEMA_VERSION:
                raise StaleCheckpointError(f"checkpoint {checkpoint_path} schema is incompatible")
            if checkpoint.get("fingerprints_sha256") != self.fingerprints_sha256:
                raise StaleCheckpointError(f"checkpoint {checkpoint_path} fingerprints are stale")
            if checkpoint.get("segment_sha256") != canonical_sha256(checkpoint.get("segment")):
                raise StaleCheckpointError(f"checkpoint {checkpoint_path} segment digest is invalid")

    def save_manifest(self) -> None:
        self.manifest["updated_at"] = _utc_now()
        atomic_write_json(self.manifest_path, self.manifest)

    def _checkpoint_path(self, segment_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in segment_id)
        return self.checkpoint_directory / safe / "checkpoint.json"

    def _write_checkpoint(self, segment: Mapping[str, Any]) -> str:
        path = self._checkpoint_path(str(segment["segment_id"]))
        payload = {
            "schema_version": NATIVE_ADAPTIVE_CHECKPOINT_SCHEMA_VERSION,
            "run_id": self.config.run_id,
            "segment_id": segment["segment_id"],
            "created_at": _utc_now(),
            "fingerprints": self.fingerprints,
            "fingerprints_sha256": self.fingerprints_sha256,
            "segment": copy.deepcopy(dict(segment)),
            "segment_sha256": canonical_sha256(segment),
        }
        atomic_write_json(path, payload)
        return path.relative_to(self.run_directory).as_posix()

    def _completed_segment_count(self, target_id: str) -> int:
        return sum(1 for segment in self.manifest["segments"] if segment["target_id"] == target_id and segment.get("checkpoint_complete"))

    def _last_restart_state(self, target_id: str) -> Mapping[str, Any] | None:
        candidates = [segment for segment in self.manifest["segments"] if segment["target_id"] == target_id and segment.get("restart")]
        return candidates[-1]["restart"] if candidates else None

    def _append_segment(self, segment: dict[str, Any]) -> None:
        checkpoint_path = self._write_checkpoint(segment)
        segment["checkpoint_path"] = checkpoint_path
        segment["checkpoint_complete"] = True
        segment["checkpoint_sha256"] = sha256_file(self.run_directory / checkpoint_path)
        self.manifest["segments"].append(segment)
        self.manifest["resume"] = {
            "latest_complete_segment_id": segment["segment_id"],
            "complete_checkpoint_count": sum(1 for item in self.manifest["segments"] if item.get("checkpoint_complete")),
        }
        resources = self.manifest["resource_accounting"]
        seg_resources = segment["resources"]
        resources["segment_wall_clock_s"] += seg_resources["segment_wall_clock_s"]
        resources["segment_cpu_s"] += seg_resources["segment_cpu_s"]
        resources["max_rss_kib"] = max(resources["max_rss_kib"], seg_resources["segment_max_rss_kib"])
        self.save_manifest()

    def run(self, *, max_new_segments: int | None = None) -> dict[str, Any]:
        """Run until all targets are terminal or ``max_new_segments`` checkpoints are written."""

        if max_new_segments is not None and max_new_segments < 1:
            raise ValueError("max_new_segments must be positive when provided")
        self.validate_resume_state() if self.manifest_path.exists() and self.manifest.get("segments") else None
        self.manifest["status"] = "running"
        self.save_manifest()
        written = 0
        target_by_id = {str(target["target_id"]): target for target in self.config.targets}

        for target_id, target in target_by_id.items():
            status = self.manifest["target_status"][target_id]
            if status["terminal_status"] in TERMINAL_STATUS_ALLOWED_VALUES:
                continue
            while self._completed_segment_count(target_id) < self.config.max_cycles_per_target:
                if max_new_segments is not None and written >= max_new_segments:
                    self.manifest["status"] = "interrupted"
                    self.save_manifest()
                    return self.manifest
                cycle_index = self._completed_segment_count(target_id)
                restart_state = self._last_restart_state(target_id)
                segment = self._run_one_segment(target, cycle_index=cycle_index, restart_state=restart_state)
                self._append_segment(segment)
                written += 1
                final = segment["terminal_status"]
                if final != "continue":
                    status["terminal_status"] = final
                    status["completed_segment_id"] = segment["segment_id"]
                    self.save_manifest()
                    break
            else:
                status["terminal_status"] = "resolution_unresolved"
                status["reason"] = "max_cycles_per_target_exhausted"
                self.save_manifest()

        unfinished = [item for item in self.manifest["target_status"].values() if item["terminal_status"] not in TERMINAL_STATUS_ALLOWED_VALUES]
        self.manifest["status"] = "complete" if not unfinished else "interrupted"
        self.save_manifest()
        return self.manifest

    def _run_one_segment(
        self,
        target: Mapping[str, Any],
        *,
        cycle_index: int,
        restart_state: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        target_id = str(target["target_id"])
        segment_id = f"segment-{len(self.manifest['segments']):04d}__{target_id}__cycle-{cycle_index:02d}"
        usage = resource.getrusage(resource.RUSAGE_SELF)
        start_wall = time.perf_counter()
        start_cpu = usage.ru_utime + usage.ru_stime
        start_rss = int(usage.ru_maxrss)

        fixed = dict(self.backend.run_fixed_mesh_segment(target, cycle_index=cycle_index, restart_state=restart_state))
        events = [dict(event) for event in fixed.get("events", [])]
        partition = partition_loca_events(events)
        if partition["rejected_remesh_boundary_count"]:
            raise RuntimeError("rejected LOCA callback cannot be a remesh boundary")
        if not events:
            raise RuntimeError("fixed-mesh segment must record at least one LOCA callback")

        decision = dict(self.backend.decide_remesh(target, fixed, cycle_index=cycle_index))
        action = str(decision.get("action", "stop_converged"))
        terminal_status = str(decision.get("terminal_status", "converged"))
        restart: Mapping[str, Any] | None = None
        lifecycle = SegmentLifecycleState.ACCEPTED
        state_sequence = [SegmentLifecycleState.PENDING.value, SegmentLifecycleState.RUNNING_FIXED_MESH.value]
        remesh_kind: Literal["h+r", "pure-r"] | None = None

        if action in CONTINUE_ACTIONS and terminal_status == "continue":
            state_sequence.append(SegmentLifecycleState.REMESH_PENDING.value)
            remesh_kind = "pure-r" if action == "pure_r" or decision.get("remesh_kind") == "pure-r" else "h+r"
            attempt_order = [attempt.name for attempt in restart_plan(remesh_kind=remesh_kind).attempts]
            state_sequence.append(SegmentLifecycleState.RESTART_PENDING.value)
            restart = dict(self.backend.restart_after_remesh(
                target,
                fixed,
                decision,
                cycle_index=cycle_index,
                attempt_order=attempt_order,
            ))
            observed = list(restart.get("attempt_order", restart.get("attempts", attempt_order)))
            if observed[: len(attempt_order)] != attempt_order[: len(observed)]:
                raise RuntimeError("restart attempts did not follow deterministic retry ordering")
            if restart.get("accepted", restart.get("status") == "accepted"):
                lifecycle = SegmentLifecycleState.ACCEPTED
                state_sequence.append(lifecycle.value)
                terminal_status = "continue"
            else:
                lifecycle = SegmentLifecycleState.FAILED
                state_sequence.append(lifecycle.value)
                terminal_status = "failed"
        elif terminal_status == "converged":
            terminal_status = "accepted"
            lifecycle = SegmentLifecycleState.ACCEPTED
            state_sequence.append(lifecycle.value)
        elif terminal_status in TERMINAL_STATUS_ALLOWED_VALUES:
            lifecycle = _terminal_state(terminal_status)
            state_sequence.append(lifecycle.value)
        else:
            terminal_status = "failed"
            lifecycle = SegmentLifecycleState.FAILED
            state_sequence.append(lifecycle.value)

        resources = _resource_snapshot(start_wall, start_cpu, start_rss)
        return {
            "segment_id": segment_id,
            "target_id": target_id,
            "cycle_index": cycle_index,
            "state_sequence": state_sequence,
            "lifecycle_state": lifecycle.value,
            "terminal_status": terminal_status,
            "remesh_kind": remesh_kind,
            "fixed_mesh_segment": fixed,
            "events": events,
            "event_partition": partition,
            "mesh_history": fixed.get("mesh_history", decision.get("mesh_history", [])),
            "transfer_correction_details": fixed.get("transfer_correction_details", []),
            "diagnostics": native_adaptive_diagnostics(fixed, decision, restart, events),
            "adaptive_decision": decision,
            "restart": restart,
            "resources": resources,
        }


class ScriptedNativeAdaptiveBackend:
    """Small deterministic backend for tests and smoke artifacts.

    ``script`` maps each target id to an ordered list of segment specifications.
    A specification may provide ``events``, ``points``, ``decision`` and
    ``restart`` dictionaries.  Missing numerical fields are filled with finite
    placeholder diagnostics so that the driver contract can be exercised without
    Trilinos.
    """

    def __init__(self, script: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        self.script = {str(key): [copy.deepcopy(dict(item)) for item in value] for key, value in script.items()}
        self.executions: dict[str, int] = {str(key): 0 for key in script}
        self.restart_attempts: list[list[str]] = []

    def _spec(self, target: Mapping[str, Any], cycle_index: int) -> Mapping[str, Any]:
        target_id = str(target["target_id"])
        try:
            return self.script[target_id][cycle_index]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"no scripted segment for {target_id} cycle {cycle_index}") from exc

    def run_fixed_mesh_segment(
        self,
        target: Mapping[str, Any],
        *,
        cycle_index: int,
        restart_state: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        target_id = str(target["target_id"])
        self.executions[target_id] = self.executions.get(target_id, 0) + 1
        spec = copy.deepcopy(dict(self._spec(target, cycle_index)))
        decision = dict(spec.get("decision", {"action": "stop_converged", "terminal_status": "converged"}))
        wants_remesh_boundary = decision.get("action") in CONTINUE_ACTIONS and decision.get("terminal_status") == "continue"
        events = spec.get("events") or [
            {"callback_index": 0, "status": "accepted", "save_role": "initial", "point_index": 0, "vector_key": f"{target_id}__{cycle_index}__initial"},
            {"callback_index": 1, "status": "accepted", "save_role": "final", "point_index": 1, "vector_key": f"{target_id}__{cycle_index}__final", "remesh_boundary_candidate": wants_remesh_boundary},
        ]
        return {
            "backend": "scripted-native-adaptive-backend",
            "restart_state_seen": restart_state is not None,
            "events": events,
            "points": spec.get("points", []),
            "mesh_history": spec.get("mesh_history", [{"interval_count": spec.get("interval_count", 32)}]),
            "transfer_correction_details": spec.get("transfer_correction_details", []),
            "defects": spec.get("defects", {"maximum": 0.0}),
            "convergence": spec.get("convergence", {"nox_status": "converged"}),
            "phase_lineage": spec.get("phase_lineage", []),
            "diagnostics": spec.get("diagnostics", {}),
        }

    def decide_remesh(
        self,
        target: Mapping[str, Any],
        segment: Mapping[str, Any],
        *,
        cycle_index: int,
    ) -> Mapping[str, Any]:
        spec = self._spec(target, cycle_index)
        return copy.deepcopy(dict(spec.get("decision", {"action": "stop_converged", "terminal_status": "converged"})))

    def restart_after_remesh(
        self,
        target: Mapping[str, Any],
        segment: Mapping[str, Any],
        decision: Mapping[str, Any],
        *,
        cycle_index: int,
        attempt_order: Sequence[str],
    ) -> Mapping[str, Any]:
        self.restart_attempts.append(list(attempt_order))
        spec = self._spec(target, cycle_index)
        restart = copy.deepcopy(dict(spec.get("restart", {})))
        restart.setdefault("status", "accepted")
        restart.setdefault("accepted", True)
        restart.setdefault("attempt_order", list(attempt_order))
        restart.setdefault("tangent", {"policy": "renormalized", "post_normalization_norm": 1.0})
        restart.setdefault("rebuild", {"identity_changed": True, "graph_rebuilt": True, "retained_graph_reuse": True})
        restart.setdefault("resources", {"linear_solve_count": 1, "nonlinear_iteration_count": 1})
        return restart
