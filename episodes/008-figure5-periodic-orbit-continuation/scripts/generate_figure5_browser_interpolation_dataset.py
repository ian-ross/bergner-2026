#!/usr/bin/env python3
"""Generate TASK-079 Figure 5 interpolation and browser-display dataset.

The current authoritative nonlinear production ledger contains one accepted
native adaptive orbit (``spine-210K``) and explicit unresolved policy gaps for
the rest of the requested Figure 5 skeleton.  This generator therefore records
that shape-preserving log-period interpolation is *not* attempted for nonlinear
period-map values: the holdout prerequisites are not met, and unresolved/Hopf
regions remain explicit display gaps.  The lower-panel T=210 K linearized curve
is copied from the independent equilibrium-linearized TASK-074 artifact rather
than resampled from any heatmap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026 import HopfLocusCoordinates  # noqa: E402
from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    EPISODE8_PRODUCTION_SCHEMA_VERSION,
    ORBIT_STATE_CONVENTION,
    PARAMETER_COORDINATE_CONVENTION,
    PERIOD_CONVENTION,
    PHASE_COORDINATE_CONVENTION,
    canonical_json_bytes,
    validate_production_artifact,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
ARTIFACT = OUTPUT / "figure5_browser_interpolation_dataset.json"
GENERATOR = Path(__file__).resolve()
DOC = EPISODE / "docs/task079-browser-interpolation-dataset.md"
README = EPISODE / "README.md"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK074_DOC = EPISODE / "docs/task074-t210-linearized-period-curve.md"
TASK075_DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
TASK076_DOC = EPISODE / "docs/task076-near-hopf-approach-policy.md"
TASK077_DOC = EPISODE / "docs/task077-floquet-postprocessing.md"
TASK078_DOC = EPISODE / "docs/task078-stratified-ivp-validation.md"
FULL_DOMAIN_SUMMARY = OUTPUT / "native_adaptive_full_domain_run.json"
FULL_DOMAIN_POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
FULL_DOMAIN_EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
FULL_DOMAIN_RUN_METADATA = OUTPUT / "native_adaptive_full_domain_run_metadata.json"
FULL_DOMAIN_ORBIT_MANIFEST = OUTPUT / "native_adaptive_full_domain_orbit_manifest.json"
NEAR_HOPF_POLICY_RECORDS = OUTPUT / "native_adaptive_near_hopf_policy_records.json"
FLOQUET_DIAGNOSTICS = OUTPUT / "native_adaptive_floquet_diagnostics.json"
IVP_VALIDATION = OUTPUT / "native_adaptive_ivp_validation.json"
T210_LINEARIZED = OUTPUT / "t210_linearized_period_curve.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"

SCHEMA_VERSION = "episode008-figure5-browser-interpolation-dataset-v1"
ARTIFACT_KIND = "task079-figure5-browser-interpolation-dataset"
INTERPOLATION_VERSION = "pchip-shape-preserving-log-period-safe-topology-v1"
HOLDOUT_VERSION = "along-slice-and-withheld-slice-logP-holdout-v1"
MIN_ALONG_SLICE_SOURCE_POINTS = 3
MIN_WITHHELD_SLICE_SOURCE_TEMPERATURES = 3
INVALID_RHO_SAMPLES = (-1.05, 1.05)
COMPARISON_PLACEHOLDER_RHOS = (0.0,)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def canonical(value: object) -> bytes:
    return canonical_json_bytes(value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def coordinate_conventions() -> dict[str, str]:
    return {
        "parameter_coordinates": PARAMETER_COORDINATE_CONVENTION,
        "orbit_state": ORBIT_STATE_CONVENTION,
        "phase": PHASE_COORDINATE_CONVENTION,
        "period": PERIOD_CONVENTION,
    }


def method_versions() -> dict[str, str]:
    return {
        "schema": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "browser_dataset": SCHEMA_VERSION,
        "interpolation": INTERPOLATION_VERSION,
        "holdout": HOLDOUT_VERSION,
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
        "linearized_period": "cpp-nox-loca-equilibrium-physical-jacobian-linearized-period-v1",
        "floquet": "dop853-radau-variational-postprocessing-v1",
        "ivp_validation": "dop853-radau-independent-ivp-validation-v1",
        "hopf_policy": "quadratic-quartic-P-of-amplitude-gated-v1",
    }


def target_id(temperature_K: float, rho: float) -> str:
    temperature = int(temperature_K) if float(temperature_K).is_integer() else temperature_K
    if abs(rho) < 1.0e-15:
        return f"spine-{temperature}K"
    return f"slice-{temperature}K-rho-{rho:+.2f}"


def coordinates(temperature_K: float, rho: float, locus: HopfLocusCoordinates) -> dict[str, Any]:
    log_w = locus.log_w_from_rho(float(temperature_K), float(rho))
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": float(temperature_K), "unit": "K"},
        "log_w": {"value": float(log_w), "unit": "ln(m s^-1)"},
        "w": {"value": float(math.exp(log_w)), "unit": "m s^-1"},
        "rho": {"value": float(rho), "unit": "dimensionless"},
        "temperature_hat": {
            "value": float(HopfLocusCoordinates.temperature_hat(float(temperature_K))),
            "unit": "dimensionless",
        },
    }


def null_display_period() -> dict[str, Any]:
    return {"quantity": "display_period", "value": None, "unit": "s", "log_value": None}


def display_period(value: float | None) -> dict[str, Any]:
    if value is None:
        return null_display_period()
    return {"quantity": "display_period", "value": float(value), "unit": "s", "log_value": math.log(float(value))}


def validity(status: str, source: str, *, authoritative: bool, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "source": source, "authoritative": authoritative}
    if reason is not None:
        result["reason"] = reason
    return result


def accepted_point_records(points_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        point
        for point in points_artifact.get("continuation_points", [])
        if point.get("validity", {}).get("status") == "accepted"
    ]


def full_domain_event_by_target(events_artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for event in events_artifact.get("continuation_events", []):
        event_id = str(event.get("event_id", ""))
        prefix = "task075-terminal-"
        if event_id.startswith(prefix):
            result[event_id[len(prefix) :]] = event
    return result


def interpolation_review(full_domain: Mapping[str, Any], points_artifact: Mapping[str, Any]) -> dict[str, Any]:
    accepted_points = accepted_point_records(points_artifact)
    targets = list(full_domain["terminal_target_ledger"]["targets"])
    accepted_by_temperature: dict[float, list[Mapping[str, Any]]] = defaultdict(list)
    terminal_by_temperature: dict[float, list[Mapping[str, Any]]] = defaultdict(list)
    for target in targets:
        temperature = float(target["temperature_K"])
        terminal_by_temperature[temperature].append(target)
        if target["terminal_status"] == "accepted":
            accepted_by_temperature[temperature].append(target)

    along_slice = []
    for temperature in sorted(terminal_by_temperature):
        accepted = sorted(accepted_by_temperature.get(temperature, []), key=lambda row: float(row["rho"]))
        blockers = [
            row["target_id"]
            for row in sorted(terminal_by_temperature[temperature], key=lambda item: float(item["rho"]))
            if row["terminal_status"] != "accepted"
        ]
        status = "not_evaluated"
        reason = (
            f"requires at least {MIN_ALONG_SLICE_SOURCE_POINTS} accepted native nonlinear points on one safe "
            f"connected T-slice; found {len(accepted)}"
        )
        along_slice.append(
            {
                "temperature_K": temperature,
                "accepted_source_point_ids": [row["target_id"] for row in accepted],
                "accepted_source_point_count": len(accepted),
                "blocked_target_count": len(blockers),
                "blocked_target_ids": blockers,
                "holdout_status": status,
                "max_abs_log_period_error": None,
                "reason": reason,
            }
        )

    accepted_temperatures = sorted(temp for temp, rows in accepted_by_temperature.items() if rows)
    withheld_status = "not_evaluated"
    withheld_reason = (
        f"requires at least {MIN_WITHHELD_SLICE_SOURCE_TEMPERATURES} temperature slices with accepted native "
        f"nonlinear source points and no intervening unresolved/gap barriers; found {len(accepted_temperatures)}"
    )
    unresolved_count = int(full_domain["terminal_target_ledger"]["terminal_status_counts"].get("resolution_unresolved", 0))
    return {
        "method": INTERPOLATION_VERSION,
        "quantity_interpolated_if_enabled": "log(nonlinear_period_s)",
        "shape_preserving_algorithm": "scipy.interpolate.PchipInterpolator on log(P) within one safe connected segment only",
        "interpolation_created": False,
        "interpolated_record_count": 0,
        "accepted_native_nonlinear_source_point_count": len(accepted_points),
        "safe_connected_segment_count_with_enough_sources": 0,
        "along_slice_holdout": {
            "version": HOLDOUT_VERSION,
            "minimum_source_points_per_slice": MIN_ALONG_SLICE_SOURCE_POINTS,
            "slice_reviews": along_slice,
            "overall_status": "not_evaluated",
            "max_abs_log_period_error": None,
        },
        "withheld_slice_holdout": {
            "version": HOLDOUT_VERSION,
            "minimum_source_temperatures": MIN_WITHHELD_SLICE_SOURCE_TEMPERATURES,
            "accepted_source_temperatures_K": accepted_temperatures,
            "overall_status": withheld_status,
            "max_abs_log_period_error": None,
            "reason": withheld_reason,
        },
        "no_crossing_policy": {
            "hopf_boundaries_crossed": False,
            "unresolved_targets_crossed": False,
            "instability_checkpoints_crossed": False,
            "tripwire_or_near_hopf_stops_crossed": False,
            "multivalued_tripwires_crossed": False,
            "reason": (
                "No nonlinear interpolation records are emitted because the current safe topology has one accepted "
                f"native point and {unresolved_count} unresolved targets."
            ),
        },
        "blocked_region_counts": {
            "resolution_unresolved_targets": unresolved_count,
            "near_hopf_stop_targets": int(full_domain["terminal_target_ledger"]["terminal_status_counts"].get("near_hopf_stop", 0)),
            "tripwire_stop_targets": int(full_domain["terminal_target_ledger"]["terminal_status_counts"].get("tripwire_stop", 0)),
            "failed_targets": int(full_domain["terminal_target_ledger"]["terminal_status_counts"].get("failed", 0)),
        },
    }


def stability_review(floquet: Mapping[str, Any], ivp: Mapping[str, Any]) -> dict[str, Any]:
    diagnostics = list(floquet.get("floquet_diagnostics", []))
    ambiguous_or_unstable: list[str] = []
    for item in diagnostics:
        classification = item.get("production_multiplier_classification", {})
        if not isinstance(classification, Mapping):
            ambiguous_or_unstable.append(str(item.get("target_id")))
            continue
        if bool(classification.get("ambiguous")) or bool(classification.get("unstable")):
            ambiguous_or_unstable.append(str(item.get("target_id")))
    ivp_failures: list[str] = []
    for item in ivp.get("dop853_validations", []):
        dop853 = item.get("dop853_one_period_return_and_trajectory", {})
        status = dop853.get("validation_status") if isinstance(dop853, Mapping) else None
        if status not in {"passed", "unavailable"}:
            ivp_failures.append(str(item.get("target_id")))
    return {
        "floquet_diagnostic_count": len(diagnostics),
        "ambiguous_or_unstable_target_ids": ambiguous_or_unstable,
        "ivp_failure_target_ids": ivp_failures,
        "instability_checkpoints_available": bool(diagnostics),
        "interpolation_blocked_by_instability_checkpoint_ids": ambiguous_or_unstable,
    }


def solved_browser_records(points_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for point in accepted_point_records(points_artifact):
        period_value = float(point["period"]["value"])
        base = {
            "coordinates": point["coordinates"],
            "validity": validity("accepted", "computed_native_adaptive", authoritative=True),
            "method_versions": method_versions(),
            "display_period": display_period(period_value),
            "display_category": "solved_native_nonlinear",
            "source_links": {
                "continuation_points_artifact": rel(FULL_DOMAIN_POINTS),
                "continuation_point_record_id": point["record_id"],
                "continuation_events_artifact": rel(FULL_DOMAIN_EVENTS),
                "orbit_manifest_artifact": rel(FULL_DOMAIN_ORBIT_MANIFEST),
                "floquet_diagnostics_artifact": rel(FLOQUET_DIAGNOSTICS),
                "ivp_validation_artifact": rel(IVP_VALIDATION),
            },
            "coordinate_provenance": "TASK-075 native adaptive continuation point coordinates",
            "display_units": {"period": "s", "temperature": "K", "w": "m s^-1", "rho": "dimensionless"},
        }
        records.append(
            {
                **base,
                "record_id": f"task079-upper-map-solved-{point['record_id']}",
                "record_role": "period_map_cell",
                "display_layer": "upper_period_map_nonlinear_solved",
            }
        )
        records.append(
            {
                **base,
                "record_id": f"task079-lower-nonlinear-solved-{point['record_id']}",
                "record_role": "temperature_slice_point",
                "display_layer": "lower_panel_T210K_nonlinear_continuation",
                "lower_panel_source_policy": "authoritative native nonlinear continuation record; not heatmap resampling",
            }
        )
    return records


def unresolved_browser_records(events_by_target: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for target, event in sorted(events_by_target.items()):
        event_validity = event.get("validity", {})
        if event_validity.get("status") == "accepted":
            continue
        reason = str(event_validity.get("reason") or "unresolved native adaptive target remains an explicit display gap")
        records.append(
            {
                "record_id": f"task079-upper-map-unresolved-{target}",
                "record_role": "period_map_cell",
                "coordinates": event["coordinates"],
                "validity": validity("resolution_unresolved", "unresolved_native_adaptive", authoritative=False, reason=reason),
                "method_versions": method_versions(),
                "display_period": null_display_period(),
                "display_category": "gap_unresolved_native_target",
                "display_layer": "upper_period_map_gap",
                "source_links": {
                    "continuation_events_artifact": rel(FULL_DOMAIN_EVENTS),
                    "continuation_event_id": event["event_id"],
                    "full_domain_summary_artifact": rel(FULL_DOMAIN_SUMMARY),
                },
                "interpolation_policy": "not filled by interpolation; unresolved target blocks connected interpolation segments",
                "display_units": {"period": "s", "temperature": "K", "w": "m s^-1", "rho": "dimensionless"},
            }
        )
    return records


def hopf_policy_browser_records(policy_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in policy_artifact.get("browser_records", []):
        copied = dict(record)
        copied["record_id"] = f"task079-hopf-limit-{record['record_id']}"
        copied["method_versions"] = method_versions()
        copied["display_category"] = "hopf_limit_explicit_gap"
        copied["display_layer"] = "upper_period_map_hopf_boundary"
        copied["source_links"] = {
            "near_hopf_policy_artifact": rel(NEAR_HOPF_POLICY_RECORDS),
            "near_hopf_policy_record_id": record["record_id"],
        }
        copied["interpolation_policy"] = "Hopf boundary is a hard no-crossing boundary; no regular-orbit display period is invented."
        records.append(copied)
    return records


def invalid_domain_records(full_domain: Mapping[str, Any], locus: HopfLocusCoordinates) -> list[dict[str, Any]]:
    temperatures = [float(value) for value in full_domain["terminal_target_ledger"]["temperature_slices_K"]]
    records: list[dict[str, Any]] = []
    for temperature in temperatures:
        for rho in INVALID_RHO_SAMPLES:
            side = "below_lower_hopf" if rho < -1.0 else "above_upper_hopf"
            records.append(
                {
                    "record_id": f"task079-invalid-{side}-{int(temperature)}K",
                    "record_role": "period_map_cell",
                    "coordinates": coordinates(temperature, rho, locus),
                    "validity": validity(
                        "invalid",
                        "invalid_outside_hopf_domain",
                        authoritative=False,
                        reason="rho lies outside the Episode 006 lower/upper Hopf-locus bracket for regular periodic orbits",
                    ),
                    "method_versions": method_versions(),
                    "display_period": null_display_period(),
                    "display_category": "invalid_outside_hopf_domain",
                    "display_layer": "upper_period_map_invalid_domain_mask",
                    "source_links": {"hopf_locus_artifact": rel(HOPF_LOCI)},
                    "interpolation_policy": "invalid domain cells are never interpolation targets",
                }
            )
    return records


def linearized_browser_records(linearized_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in linearized_artifact.get("linearized_period_rows", []):
        period_value = row.get("period", {}).get("value")
        accepted = row.get("validity", {}).get("status") == "accepted"
        records.append(
            {
                "record_id": f"task079-lower-linearized-{row['record_id']}",
                "record_role": "temperature_slice_point",
                "coordinates": row["coordinates"],
                "validity": validity(
                    "accepted" if accepted else row["validity"]["status"],
                    "computed_linearized_equilibrium" if accepted else row["validity"]["source"],
                    authoritative=bool(accepted),
                    reason=None if accepted else row["validity"].get("reason", "linearized-period row unavailable"),
                ),
                "method_versions": method_versions(),
                "display_period": display_period(float(period_value) if period_value is not None else None),
                "display_category": "linearized_equilibrium_T210K",
                "display_layer": "lower_panel_T210K_linearized_curve",
                "source_links": {
                    "linearized_period_artifact": rel(T210_LINEARIZED),
                    "linearized_period_record_id": row["record_id"],
                },
                "lower_panel_source_policy": "independent T=210 K equilibrium-linearized period row; not heatmap resampling",
                "eigenvalue_imaginary_part": row.get("eigenvalue_imaginary_part"),
                "sampling": row.get("sampling"),
            }
        )
    return records


def comparison_pending_records(full_domain: Mapping[str, Any], locus: HopfLocusCoordinates) -> list[dict[str, Any]]:
    # TASK-063 is intentionally not a dependency of TASK-079, so this dataset
    # exposes the channel without fabricating image-derived values.  TASK-080 can
    # replace these placeholders with external_comparison records once the
    # digitized paper artifact exists.
    records: list[dict[str, Any]] = []
    for rho in COMPARISON_PLACEHOLDER_RHOS:
        records.append(
            {
                "record_id": f"task079-external-comparison-pending-upper-rho-{rho:+.2f}",
                "record_role": "external_comparison_overlay",
                "coordinates": coordinates(210.0, rho, locus),
                "validity": validity(
                    "not_evaluated",
                    "not_evaluated",
                    authoritative=False,
                    reason="TASK-063 digitized Figure 5 evidence is not complete; no image-derived comparison value is included in TASK-079",
                ),
                "method_versions": method_versions(),
                "display_period": null_display_period(),
                "display_category": "image_derived_comparison_pending",
                "display_layer": "external_digitized_paper_comparison_overlay",
                "source_links": {"pending_task": "TASK-063"},
            }
        )
    lower_coord = coordinates(210.0, 0.0, locus)
    records.append(
        {
            "record_id": "task079-external-comparison-pending-lower-T210K",
            "record_role": "external_comparison_overlay",
            "coordinates": lower_coord,
            "validity": validity(
                "not_evaluated",
                "not_evaluated",
                authoritative=False,
                reason="TASK-063 lower-panel digitized nonlinear/linearized curves are not complete; no image-derived comparison value is included in TASK-079",
            ),
            "method_versions": method_versions(),
            "display_period": null_display_period(),
            "display_category": "image_derived_comparison_pending",
            "display_layer": "external_digitized_paper_comparison_overlay",
            "source_links": {"pending_task": "TASK-063"},
        }
    )
    return records


def build_artifact() -> dict[str, Any]:
    full_domain = load_json(FULL_DOMAIN_SUMMARY)
    points_artifact = load_json(FULL_DOMAIN_POINTS)
    events_artifact = load_json(FULL_DOMAIN_EVENTS)
    near_hopf_policy = load_json(NEAR_HOPF_POLICY_RECORDS)
    floquet = load_json(FLOQUET_DIAGNOSTICS)
    ivp = load_json(IVP_VALIDATION)
    linearized = load_json(T210_LINEARIZED)
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    events_by_target = full_domain_event_by_target(events_artifact)

    records: list[dict[str, Any]] = []
    records.extend(solved_browser_records(points_artifact))
    records.extend(unresolved_browser_records(events_by_target))
    records.extend(hopf_policy_browser_records(near_hopf_policy))
    records.extend(invalid_domain_records(full_domain, locus))
    records.extend(linearized_browser_records(linearized))
    records.extend(comparison_pending_records(full_domain, locus))

    record_ids = [record["record_id"] for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError("duplicate browser record ids")

    category_counts = Counter(str(record["display_category"]) for record in records)
    status_counts = Counter(str(record["validity"]["status"]) for record in records)
    layer_counts = Counter(str(record["display_layer"]) for record in records)
    interpolation = interpolation_review(full_domain, points_artifact)
    stability = stability_review(floquet, ivp)

    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "browser-display-dataset",
        "artifact_id": "task079-figure5-browser-interpolation-dataset",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-079",
            "created_by": "generate_figure5_browser_interpolation_dataset.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": [
                source_record(GENERATOR, "TASK-079 browser/interpolation generator"),
                source_record(FULL_DOMAIN_SUMMARY, "TASK-075 full-domain terminal ledger and sampling-refinement policy"),
                source_record(FULL_DOMAIN_POINTS, "TASK-075 accepted native nonlinear continuation points"),
                source_record(FULL_DOMAIN_EVENTS, "TASK-075 terminal events for unresolved/gap regions"),
                source_record(FULL_DOMAIN_RUN_METADATA, "TASK-075 run metadata"),
                source_record(FULL_DOMAIN_ORBIT_MANIFEST, "TASK-075 accepted orbit manifest"),
                source_record(NEAR_HOPF_POLICY_RECORDS, "TASK-076 Hopf-limit explicit-gap policy records"),
                source_record(FLOQUET_DIAGNOSTICS, "TASK-077 Floquet instability/ambiguity diagnostics"),
                source_record(IVP_VALIDATION, "TASK-078 independent IVP validation diagnostics"),
                source_record(T210_LINEARIZED, "TASK-074 independent T=210 K linearized-period curve"),
                source_record(HOPF_LOCI, "Episode 006 Hopf boundary coordinate reference"),
                source_record(DOC, "TASK-079 browser/interpolation documentation"),
                source_record(TASK069_DOC, "TASK-069 no-undocumented-interpolation decision"),
                source_record(TASK070_DOC, "TASK-070 production schema contract"),
                source_record(TASK074_DOC, "TASK-074 lower-panel linearized-period documentation"),
                source_record(TASK075_DOC, "TASK-075 full-domain continuation documentation"),
                source_record(TASK076_DOC, "TASK-076 near-Hopf explicit-gap documentation"),
                source_record(TASK077_DOC, "TASK-077 Floquet diagnostics documentation"),
                source_record(TASK078_DOC, "TASK-078 IVP validation documentation"),
                source_record(README, "Episode 008 documentation index"),
            ],
        },
        "browser_records": records,
        "dataset_summary": {
            "browser_dataset_version": SCHEMA_VERSION,
            "record_count": len(records),
            "record_category_counts": {key: category_counts.get(key, 0) for key in sorted(set(category_counts) | {
                "solved_native_nonlinear",
                "validated_interpolated_nonlinear",
                "hopf_limit_explicit_gap",
                "image_derived_comparison_pending",
                "image_derived_comparison_value",
                "invalid_outside_hopf_domain",
                "gap_unresolved_native_target",
                "linearized_equilibrium_T210K",
            })},
            "validity_status_counts": dict(sorted(status_counts.items())),
            "display_layer_counts": dict(sorted(layer_counts.items())),
            "authoritative_record_count": sum(1 for record in records if record["validity"]["authoritative"]),
            "non_authoritative_record_count": sum(1 for record in records if not record["validity"]["authoritative"]),
            "digitized_paper_data_policy": "external-comparison-only; TASK-063 pending, so no image-derived values are included",
        },
        "interpolation_review": interpolation,
        "stability_and_validation_barriers": stability,
        "lower_panel_source_policy": {
            "nonlinear_records_source": "TASK-075 accepted native nonlinear continuation points only",
            "linearized_records_source": "TASK-074 independent T=210 K equilibrium-linearized period curve",
            "heatmap_resampling_used": False,
            "nonlinear_record_count": layer_counts.get("lower_panel_T210K_nonlinear_continuation", 0),
            "linearized_record_count": layer_counts.get("lower_panel_T210K_linearized_curve", 0),
        },
        "image_derived_comparison_policy": {
            "task063_status_at_generation": "not_done",
            "image_derived_values_included": False,
            "pending_record_count": category_counts.get("image_derived_comparison_pending", 0),
            "future_overlay_source_flag": "external_digitized_paper_comparison",
            "agreement_with_digitized_pixels_can_override_numerical_validation": False,
        },
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=ARTIFACT)
    return artifact


def write_or_check(*, check: bool) -> None:
    artifact = build_artifact()
    payload = canonical(artifact)
    if check:
        if not ARTIFACT.is_file():
            raise SystemExit(f"missing {rel(ARTIFACT)}")
        current = ARTIFACT.read_bytes()
        if current != payload:
            raise SystemExit(f"{rel(ARTIFACT)} is not current; regenerate without --check")
        # Re-run with artifact_path so checksum verification uses the repository root.
        validate_production_artifact(json.loads(current), root=ROOT, artifact_path=ARTIFACT)
        print(f"{rel(ARTIFACT)} is current")
        return
    ARTIFACT.write_bytes(payload)
    print(f"wrote {rel(ARTIFACT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed artifact is byte-current")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_or_check(check=bool(args.check))


if __name__ == "__main__":
    main()
