from __future__ import annotations

import json
from pathlib import Path

import pytest

from bergner_spichtinger_2026 import (
    NativeAdaptiveDriver,
    NativeAdaptiveDriverConfig,
    ScriptedNativeAdaptiveBackend,
    SegmentLifecycleState,
    StaleCheckpointError,
    evaluate_single_valued_tripwire,
    partition_loca_events,
)


def source_file(tmp_path: Path) -> Path:
    path = tmp_path / "driver_source.py"
    path.write_text("source-v1\n")
    return path


def config(tmp_path: Path, source: Path, *, configuration: dict | None = None) -> NativeAdaptiveDriverConfig:
    return NativeAdaptiveDriverConfig(
        run_id="pytest-native-adaptive",
        run_directory=tmp_path / "run",
        targets=(
            {"target_id": "target-a", "target_type": "spine_temperature", "coordinate": 210.0},
            {"target_id": "target-b", "target_type": "fixed_temperature_rho_slice", "coordinate": 0.15},
        ),
        configuration=configuration or {"rule": "gauss3", "mesh": "n32"},
        source_paths=(source,),
        source_root=tmp_path,
        vector_fingerprints={"seed": "abc123"},
        max_cycles_per_target=4,
    )


def test_event_partitioning_distinguishes_initial_regular_final_retries_and_boundaries() -> None:
    events = [
        {"callback_index": 0, "status": "accepted", "save_role": "initial", "point_index": 0},
        {"callback_index": 1, "status": "rejected", "save_role": "regular"},
        {"callback_index": 2, "status": "accepted", "save_role": "regular", "point_index": 1},
        {"callback_index": 3, "status": "accepted", "save_role": "final", "point_index": 2, "remesh_boundary_candidate": True},
    ]
    partition = partition_loca_events(events)
    assert partition["callback_count"] == 4
    assert partition["accepted_callback_count"] == 3
    assert partition["rejected_callback_count"] == 1
    assert partition["initial_save_count"] == 1
    assert partition["regular_save_count"] == 2
    assert partition["final_save_count"] == 1
    assert partition["rejected_remesh_boundary_count"] == 0
    assert partition["callback_indices_contiguous"] is True


def test_resume_after_interruption_does_not_rerun_completed_segment(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [
            {"decision": {"action": "ordinary_h_r", "terminal_status": "continue"}},
            {"decision": {"action": "stop_converged", "terminal_status": "converged"}},
        ],
        "target-b": [
            {"decision": {"action": "pure_r", "terminal_status": "continue", "remesh_kind": "pure-r"}},
            {"decision": {"action": "stop_converged", "terminal_status": "converged"}},
        ],
    }
    first_backend = ScriptedNativeAdaptiveBackend(script)
    driver = NativeAdaptiveDriver(config(tmp_path, source), first_backend)
    interrupted = driver.run(max_new_segments=1)
    assert interrupted["status"] == "interrupted"
    assert len(interrupted["segments"]) == 1
    assert interrupted["segments"][0]["state_sequence"] == [
        SegmentLifecycleState.PENDING.value,
        SegmentLifecycleState.RUNNING_FIXED_MESH.value,
        SegmentLifecycleState.REMESH_PENDING.value,
        SegmentLifecycleState.RESTART_PENDING.value,
        SegmentLifecycleState.ACCEPTED.value,
    ]
    assert first_backend.executions["target-a"] == 1

    resumed_backend = ScriptedNativeAdaptiveBackend(script)
    resumed = NativeAdaptiveDriver.resume(config(tmp_path, source), resumed_backend)
    complete = resumed.run()
    assert complete["status"] == "complete"
    assert complete["target_status"]["target-a"]["terminal_status"] == "accepted"
    assert complete["target_status"]["target-b"]["terminal_status"] == "accepted"
    assert len(complete["segments"]) == 4
    # Only the second cycle of target-a runs after resume; the checkpointed first
    # cycle is loaded from disk instead of being recomputed.
    assert resumed_backend.executions["target-a"] == 1
    assert resumed_backend.executions["target-b"] == 2
    assert complete["segments"][0]["checkpoint_complete"] is True
    assert (tmp_path / "run" / complete["segments"][0]["checkpoint_path"]).is_file()


def test_stale_checkpoint_rejection_covers_source_and_configuration_fingerprints(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {"target-a": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}], "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}]}
    NativeAdaptiveDriver(config(tmp_path, source), ScriptedNativeAdaptiveBackend(script)).run(max_new_segments=1)

    source.write_text("source-v2\n")
    with pytest.raises(StaleCheckpointError, match="fingerprints"):
        NativeAdaptiveDriver.resume(config(tmp_path, source), ScriptedNativeAdaptiveBackend(script))

    source.write_text("source-v1\n")
    with pytest.raises(StaleCheckpointError, match="fingerprints"):
        NativeAdaptiveDriver.resume(
            config(tmp_path, source, configuration={"rule": "gauss3", "mesh": "n64"}),
            ScriptedNativeAdaptiveBackend(script),
        )


def test_deterministic_retry_order_and_remesh_identity_are_recorded(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [
            {
                "decision": {"action": "ordinary_h_r", "terminal_status": "continue"},
                "restart": {"accepted": True, "attempt_order": ["h_r_transfer_correct", "h_r_refresh_reference_recorrect"]},
            },
            {"decision": {"action": "stop_converged", "terminal_status": "converged"}},
        ],
        "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
    }
    backend = ScriptedNativeAdaptiveBackend(script)
    manifest = NativeAdaptiveDriver(config(tmp_path, source), backend).run(max_new_segments=1)
    segment = manifest["segments"][0]
    assert segment["remesh_kind"] == "h+r"
    assert backend.restart_attempts == [["h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect"]]
    assert segment["restart"]["rebuild"] == {
        "identity_changed": True,
        "graph_rebuilt": True,
        "retained_graph_reuse": True,
    }
    assert segment["restart"]["tangent"]["post_normalization_norm"] == 1.0


def test_failed_hr_restart_preserves_attempts_reasons_and_failed_terminal_status(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [
            {
                "events": [
                    {"callback_index": 0, "status": "accepted", "accepted": True, "save_role": "initial", "point_index": 0, "vector_key": "a0"},
                    {"callback_index": 1, "status": "accepted", "accepted": True, "save_role": "final", "point_index": 1, "vector_key": "a1", "remesh_boundary_candidate": True},
                ],
                "decision": {"action": "ordinary_h_r", "terminal_status": "continue", "reasons": ["defect_gate_failed"]},
                "restart": {
                    "accepted": False,
                    "status": "failed",
                    "attempt_order": ["h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect"],
                    "rejection_reasons": ["transfer_correction_failed", "phase_gate_failed"],
                },
            }
        ],
        "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
    }
    manifest = NativeAdaptiveDriver(config(tmp_path, source), ScriptedNativeAdaptiveBackend(script)).run()
    failed = manifest["segments"][0]
    assert manifest["target_status"]["target-a"]["terminal_status"] == "failed"
    assert failed["terminal_status"] == "failed"
    assert failed["state_sequence"][-1] == SegmentLifecycleState.FAILED.value
    assert failed["restart"]["attempt_order"] == [
        "h_r_transfer_correct", "h_r_refresh_reference_recorrect", "h_r_rebootstrap_tangent_recorrect",
    ]
    assert {reason for item in failed["diagnostics"]["rejection_reasons"] for reason in item["reasons"]} >= {
        "transfer_correction_failed", "phase_gate_failed", "defect_gate_failed",
    }
    assert failed["diagnostics"]["failed_or_unresolved_points_preserved"] == [{
        "source": "restart",
        "terminal_status": "failed",
        "reason": ["transfer_correction_failed", "phase_gate_failed"],
    }]
    assert failed["event_partition"]["rejected_remesh_boundary_count"] == 0


def test_pure_r_restart_order_and_phase_refresh_triggers_are_recorded(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [
            {
                "decision": {"action": "pure_r", "terminal_status": "continue", "remesh_kind": "pure-r", "reasons": ["convergence_gate_failed"]},
                "diagnostics": {"phase_refresh_triggers": ["remesh", "phase_energy_ratio"]},
            },
            {"decision": {"action": "stop_converged", "terminal_status": "converged"}},
        ],
        "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
    }
    backend = ScriptedNativeAdaptiveBackend(script)
    manifest = NativeAdaptiveDriver(config(tmp_path, source), backend).run(max_new_segments=1)
    segment = manifest["segments"][0]
    assert segment["remesh_kind"] == "pure-r"
    assert backend.restart_attempts == [[
        "pure_r_transfer_correct", "pure_r_refresh_reference_recorrect", "pure_r_rebootstrap_tangent_recorrect",
    ]]
    assert segment["diagnostics"]["phase_refresh_triggers"] == ["remesh", "phase_energy_ratio"]
    assert segment["restart"]["accepted"] is True


def test_cap_alias_radau_tripwire_and_deferred_evidence_channels_are_normalized(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [
            {
                "points": [
                    {"active_coordinate": 0.0, "active_tangent_sign": 1, "period_s": 100.0, "weighted_orbit_marker": 0.0},
                    {"active_coordinate": 0.20, "active_tangent_sign": -1, "period_s": 100.1, "weighted_orbit_marker": 0.01},
                    {"active_coordinate": 0.10, "active_tangent_sign": -1, "period_s": 100.2, "weighted_orbit_marker": 0.02},
                ],
                "diagnostics": {
                    "aliasing_events": [{"current_bin": 3, "previous_bin": 2, "status": "recorded"}],
                    "radau_triggers": {
                        "defect_below_1e-4_but_convergence_failed": True,
                        "period_or_defect_stagnation_before_mesh_cap": True,
                        "polynomial_ringing": "not_evaluated",
                        "nonphysical_value": False,
                    },
                },
                "decision": {
                    "version": "adaptive-cycle-controller-v1",
                    "action": "mesh_cap_escalation",
                    "terminal_status": "continue",
                    "permit_hard_cap": True,
                    "reasons": ["soft_cap_failed_after_corrected_cycle"],
                },
            }
        ],
        "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
    }
    manifest = NativeAdaptiveDriver(config(tmp_path, source), ScriptedNativeAdaptiveBackend(script)).run(max_new_segments=1)
    diagnostics = manifest["segments"][0]["diagnostics"]
    assert diagnostics["cap_escalations"] == [{
        "kind": "mesh_cap_escalation",
        "cycle_decision_version": "adaptive-cycle-controller-v1",
        "reasons": ["soft_cap_failed_after_corrected_cycle"],
        "permit_hard_cap": True,
    }]
    assert diagnostics["aliasing_events"][0]["status"] == "recorded"
    assert diagnostics["radau_triggers"]["defect_below_1e-4_but_convergence_failed"] is True
    assert diagnostics["radau_triggers"]["period_or_defect_stagnation_before_mesh_cap"] is True
    assert diagnostics["radau_triggers"]["polynomial_ringing"] == "not_evaluated"
    assert diagnostics["radau_triggers"]["nonphysical_value"] is False
    assert diagnostics["radau_triggers"]["broader_ivp_based"] == "not_evaluated_through_TASK_068"
    assert diagnostics["radau_triggers"]["floquet_dependent"] == "not_evaluated_through_TASK_068"
    tripwire = diagnostics["single_valued_tripwire"]
    assert tripwire["status"] == "tripwire_stop"
    assert {trigger["kind"] for trigger in tripwire["triggers"]} >= {
        "active_coordinate_tangent_sign_change", "normalized_coordinate_reversal",
    }
    assert diagnostics["not_evaluated_evidence"] == {
        "broader_ivp_based": "not_evaluated_through_TASK_068",
        "floquet_dependent": "not_evaluated_through_TASK_068",
    }


def test_single_valued_tripwire_observed_duplicate_and_not_evaluated_paths() -> None:
    assert evaluate_single_valued_tripwire([])["status"] == "not_evaluated"
    observed = evaluate_single_valued_tripwire([
        {"active_coordinate": -0.1, "active_tangent_sign": 1, "period_s": 10.0, "weighted_orbit_marker": 0.0},
        {"active_coordinate": 0.1, "active_tangent_sign": 1, "period_s": 10.1, "weighted_orbit_marker": 0.001},
    ])
    assert observed["status"] == "single_valued_observed"
    duplicate = evaluate_single_valued_tripwire([
        {"active_coordinate": 0.0, "period_s": 100.0, "weighted_orbit_marker": 0.0},
        {"active_coordinate": 5.0e-5, "period_s": 101.0, "weighted_orbit_marker": 0.02},
    ])
    assert duplicate["status"] == "tripwire_stop"
    assert duplicate["triggers"][0]["kind"] == "duplicate_coordinate_incompatible_orbit"


def test_fixed_mesh_regression_without_requested_remesh_writes_terminal_checkpoint(tmp_path: Path) -> None:
    source = source_file(tmp_path)
    script = {
        "target-a": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
        "target-b": [{"decision": {"action": "stop_converged", "terminal_status": "converged"}}],
    }
    manifest = NativeAdaptiveDriver(config(tmp_path, source), ScriptedNativeAdaptiveBackend(script)).run()
    assert manifest["status"] == "complete"
    assert [segment["remesh_kind"] for segment in manifest["segments"]] == [None, None]
    assert all(segment["restart"] is None for segment in manifest["segments"])
    assert all(segment["terminal_status"] == "accepted" for segment in manifest["segments"])
    persisted = json.loads((tmp_path / "run" / "manifest.json").read_text())
    assert persisted["resume"]["complete_checkpoint_count"] == 2
    assert persisted["resource_accounting"]["segment_wall_clock_s"] >= 0.0
