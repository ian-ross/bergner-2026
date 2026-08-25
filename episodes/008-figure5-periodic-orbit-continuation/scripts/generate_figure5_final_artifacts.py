#!/usr/bin/env python3
"""Generate final TASK-080 Figure 5 reproduction, paper-comparison, and browser artifacts.

The final artifacts assemble authoritative Episode 008 production/display records
with TASK-063 digitized paper evidence.  Digitized paper samples are preserved as
non-authoritative external comparison overlays; they never replace native
continuation, IVP, or Floquet validation outcomes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
EPISODE = Path(__file__).resolve().parents[1]
SCRIPTS = EPISODE / "scripts"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

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

OUTPUT = EPISODE / "outputs"
GENERATOR = Path(__file__).resolve()
DOC = EPISODE / "docs/task080-final-figure5-artifacts.md"
README = EPISODE / "README.md"

TASK063_DOC = EPISODE / "docs/task063-paper-figure5-digitization.md"
TASK069_DOC = EPISODE / "docs/task069-evidence-review-and-next-stage-design.md"
TASK070_DOC = EPISODE / "docs/production-schemas.md"
TASK074_DOC = EPISODE / "docs/task074-t210-linearized-period-curve.md"
TASK075_DOC = EPISODE / "docs/task075-full-domain-native-adaptive-continuation.md"
TASK076_DOC = EPISODE / "docs/task076-near-hopf-approach-policy.md"
TASK077_DOC = EPISODE / "docs/task077-floquet-postprocessing.md"
TASK078_DOC = EPISODE / "docs/task078-stratified-ivp-validation.md"
TASK079_DOC = EPISODE / "docs/task079-browser-interpolation-dataset.md"

TASK079_BROWSER = OUTPUT / "figure5_browser_interpolation_dataset.json"
PAPER_DIGITIZATION = OUTPUT / "paper_figure5_digitization.json"
PAPER_UPPER_SAMPLES = OUTPUT / "paper_figure5_digitization_upper_period_samples.csv"
PAPER_UPPER_BOUNDARIES = OUTPUT / "paper_figure5_digitization_upper_hopf_boundaries.csv"
PAPER_LOWER_CURVES = OUTPUT / "paper_figure5_digitization_lower_curves.csv"
FULL_DOMAIN_POINTS = OUTPUT / "native_adaptive_full_domain_points.json"
FULL_DOMAIN_EVENTS = OUTPUT / "native_adaptive_full_domain_events.json"
T210_LINEARIZED = OUTPUT / "t210_linearized_period_curve.json"
FLOQUET_DIAGNOSTICS = OUTPUT / "native_adaptive_floquet_diagnostics.json"
IVP_VALIDATION = OUTPUT / "native_adaptive_ivp_validation.json"
HOPF_LOCI = ROOT / "episodes/006-figure3-hopf-bifurcation/outputs/figure3_loca_hopf_loci/loca_figure3_hopf_loci.csv"

FINAL_BROWSER = OUTPUT / "figure5_final_browser_dataset.json"
FINAL_COMPARISON = OUTPUT / "figure5_final_paper_comparison.json"
FINAL_PLOT = OUTPUT / "figure5_final_reproduction.png"

SCHEMA_VERSION = "episode008-figure5-final-browser-dataset-v1"
COMPARISON_SCHEMA_VERSION = "episode008-figure5-paper-comparison-report-v1"
ARTIFACT_KIND = "task080-figure5-final-artifacts"
METHOD_VERSION = "final-paper-comparison-browser-assembly-v1"
DISCREPANCY_RULE = "abs(delta_log_period_natural) <= max(3*sigma_digitized_log_period_natural, 0.02)"
UPPER_COLOR_SIGMA_LOG10_PERIOD = 0.004398826979472141
MIN_LOG_PERIOD_TOLERANCE = 0.02


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def source_record(path: Path, role: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha(path), "role": role}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


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
        "final_browser_dataset": SCHEMA_VERSION,
        "paper_comparison_report": COMPARISON_SCHEMA_VERSION,
        "final_artifact_assembly": METHOD_VERSION,
        "upstream_browser_dataset": "episode008-figure5-browser-interpolation-dataset-v1",
        "paper_digitization": "manual-calibration-threshold-component-colorbar-v1",
        "comparison_discrepancy_rule": "task062-task069-image-derived-evidence-subordinate-v1",
        "linearized_period": "cpp-nox-loca-equilibrium-physical-jacobian-linearized-period-v1",
        "continuation": "native-loca-gauss-fixed-mesh-pseudo-arclength-v1",
        "adaptive": "external-gauss3-hr-adaptive-v1",
    }


def coordinates(temperature_K: float, log_w: float, locus: HopfLocusCoordinates) -> dict[str, Any]:
    return {
        "convention": PARAMETER_COORDINATE_CONVENTION,
        "temperature": {"value": float(temperature_K), "unit": "K"},
        "log_w": {"value": float(log_w), "unit": "ln(m s^-1)"},
        "w": {"value": float(math.exp(log_w)), "unit": "m s^-1"},
        "rho": {"value": float(locus.rho(float(temperature_K), float(log_w))), "unit": "dimensionless"},
        "temperature_hat": {
            "value": float(HopfLocusCoordinates.temperature_hat(float(temperature_K))),
            "unit": "dimensionless",
        },
    }


def display_period(value: float | None) -> dict[str, Any]:
    if value is None:
        return {"quantity": "display_period", "value": None, "unit": "s", "log_value": None}
    return {"quantity": "display_period", "value": float(value), "unit": "s", "log_value": math.log(float(value))}


def validity(status: str, source: str, *, authoritative: bool, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "source": source, "authoritative": authoritative}
    if reason is not None:
        result["reason"] = reason
    return result


def paper_upper_comparison_records(rows: Sequence[Mapping[str, str]], locus: HopfLocusCoordinates) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        period = float(row["period_s"])
        log_w = float(row["log_w_ln_m_s"])
        temperature = float(row["temperature_K"])
        sample_id = row["sample_id"]
        records.append(
            {
                "record_id": f"task080-paper-upper-period-{sample_id}",
                "record_role": "external_comparison_overlay",
                "coordinates": coordinates(temperature, log_w, locus),
                "validity": validity("external_comparison", "external_digitized_paper_comparison", authoritative=False),
                "method_versions": method_versions(),
                "display_period": display_period(period),
                "display_category": "image_derived_comparison_value_upper_period_map",
                "display_layer": "external_digitized_paper_upper_period_map",
                "source_links": {
                    "paper_digitization_artifact": rel(PAPER_DIGITIZATION),
                    "paper_digitization_csv": rel(PAPER_UPPER_SAMPLES),
                    "paper_sample_id": sample_id,
                },
                "uncertainty": {
                    "sigma_log10_period": UPPER_COLOR_SIGMA_LOG10_PERIOD,
                    "sigma_log_period_natural": UPPER_COLOR_SIGMA_LOG10_PERIOD * math.log(10.0),
                    "source": "TASK-063 colorbar half-pixel period uncertainty",
                },
                "comparison_policy": "image-derived external evidence only; cannot override numerical convergence, Floquet, or IVP validation",
            }
        )
    return records


def paper_lower_comparison_records(rows: Sequence[Mapping[str, str]], locus: HopfLocusCoordinates) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        period = float(row["period_s"])
        log_w = float(row["log_w_ln_m_s"])
        curve_id = row["curve_id"]
        records.append(
            {
                "record_id": f"task080-paper-lower-{curve_id}-{index:04d}",
                "record_role": "external_comparison_overlay",
                "coordinates": coordinates(210.0, log_w, locus),
                "validity": validity("external_comparison", "external_digitized_paper_comparison", authoritative=False),
                "method_versions": method_versions(),
                "display_period": display_period(period),
                "display_category": f"image_derived_comparison_value_lower_{curve_id}",
                "display_layer": "external_digitized_paper_lower_T210K_slice",
                "source_links": {
                    "paper_digitization_artifact": rel(PAPER_DIGITIZATION),
                    "paper_digitization_csv": rel(PAPER_LOWER_CURVES),
                    "paper_curve_id": curve_id,
                    "paper_curve_row_index": index,
                },
                "uncertainty": {
                    "sigma_period_s": 28.571428571428573,
                    "sigma_log_period_natural": 28.571428571428573 / period,
                    "source": "TASK-063 lower-panel half-pixel vertical period uncertainty",
                },
                "comparison_policy": "image-derived external evidence only; cannot override numerical convergence, Floquet, or IVP validation",
            }
        )
    return records


def final_browser_records(task079_browser: Mapping[str, Any], locus: HopfLocusCoordinates) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in task079_browser["browser_records"]:
        if record.get("display_category") == "image_derived_comparison_pending":
            continue
        copied = json.loads(json.dumps(record))
        copied["record_id"] = f"task080-production-{record['record_id']}"
        copied["method_versions"] = method_versions()
        copied.setdefault("source_links", {})["task079_source_record_id"] = record["record_id"]
        records.append(copied)
    records.extend(paper_upper_comparison_records(read_csv(PAPER_UPPER_SAMPLES), locus))
    records.extend(paper_lower_comparison_records(read_csv(PAPER_LOWER_CURVES), locus))
    ids = [record["record_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate final browser record ids")
    return records


def nearest(items: Sequence[Mapping[str, Any]], value: float, getter) -> Mapping[str, Any]:
    return min(items, key=lambda item: abs(float(getter(item)) - value))


def log_period_tolerance(sigma_log_period: float) -> float:
    return max(3.0 * float(sigma_log_period), MIN_LOG_PERIOD_TOLERANCE)


def comparison_status(delta_log_period: float, sigma_log_period: float) -> str:
    return "within_digitization_uncertainty" if abs(delta_log_period) <= log_period_tolerance(sigma_log_period) else "discrepancy_requires_investigation"


def build_comparison_report(task079_browser: Mapping[str, Any]) -> dict[str, Any]:
    upper_rows = read_csv(PAPER_UPPER_SAMPLES)
    lower_rows = read_csv(PAPER_LOWER_CURVES)
    lower_black = [row for row in lower_rows if row["curve_id"] == "nonlinear_limitcycle_period_black_curve"]
    lower_red = [row for row in lower_rows if row["curve_id"] == "equilibrium_linearized_period_red_curve"]
    linearized_rows = load_json(T210_LINEARIZED)["linearized_period_rows"]
    accepted_linearized = [row for row in linearized_rows if row["validity"]["status"] == "accepted"]
    solved_upper = [
        record
        for record in task079_browser["browser_records"]
        if record["display_category"] == "solved_native_nonlinear"
        and record["display_layer"] == "upper_period_map_nonlinear_solved"
    ]
    solved_lower = [
        record
        for record in task079_browser["browser_records"]
        if record["display_layer"] == "lower_panel_T210K_nonlinear_continuation"
    ]

    pairwise: list[dict[str, Any]] = []
    for solved in solved_upper:
        coord = solved["coordinates"]
        paper = min(
            upper_rows,
            key=lambda row: ((float(row["temperature_K"]) - coord["temperature"]["value"]) / 1.0) ** 2
            + ((float(row["log_w_ln_m_s"]) - coord["log_w"]["value"]) / 0.1) ** 2,
        )
        delta = math.log(float(paper["period_s"])) - math.log(float(solved["display_period"]["value"]))
        sigma = UPPER_COLOR_SIGMA_LOG10_PERIOD * math.log(10.0)
        pairwise.append(
            {
                "comparison_id": f"upper-period-map-nearest-{solved['record_id']}",
                "computed_record_id": solved["record_id"],
                "paper_record_id": paper["sample_id"],
                "comparison_layer": "upper_period_map",
                "computed_period_s": solved["display_period"]["value"],
                "paper_period_s": float(paper["period_s"]),
                "delta_log_period_natural": delta,
                "sigma_digitized_log_period_natural": sigma,
                "tolerance_log_period_natural": log_period_tolerance(sigma),
                "status": comparison_status(delta, sigma),
                "paper_evidence_role": "image-derived external comparison only",
                "override_numerical_validation": False,
            }
        )

    for solved in solved_lower:
        coord = solved["coordinates"]
        paper = nearest(lower_black, coord["log_w"]["value"], lambda row: row["log_w_ln_m_s"])
        sigma = 28.571428571428573 / float(paper["period_s"])
        delta = math.log(float(paper["period_s"])) - math.log(float(solved["display_period"]["value"]))
        pairwise.append(
            {
                "comparison_id": f"lower-nonlinear-nearest-{solved['record_id']}",
                "computed_record_id": solved["record_id"],
                "paper_record_id": f"nonlinear_limitcycle_period_black_curve@pixel_x={paper['pixel_x']}",
                "comparison_layer": "lower_T210K_nonlinear_slice",
                "computed_period_s": solved["display_period"]["value"],
                "paper_period_s": float(paper["period_s"]),
                "delta_log_period_natural": delta,
                "sigma_digitized_log_period_natural": sigma,
                "tolerance_log_period_natural": log_period_tolerance(sigma),
                "status": comparison_status(delta, sigma),
                "paper_evidence_role": "image-derived external comparison only",
                "override_numerical_validation": False,
            }
        )

    linearized_deltas: list[float] = []
    linearized_statuses: Counter[str] = Counter()
    for paper in lower_red:
        row = nearest(accepted_linearized, float(paper["log_w_ln_m_s"]), lambda item: item["coordinates"]["log_w"]["value"])
        sigma = 28.571428571428573 / float(paper["period_s"])
        delta = math.log(float(paper["period_s"])) - math.log(float(row["period"]["value"]))
        linearized_deltas.append(delta)
        linearized_statuses[comparison_status(delta, sigma)] += 1
    abs_deltas = sorted(abs(value) for value in linearized_deltas)

    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "artifact_kind": "task080-paper-comparison-report",
        "artifact_id": "task080-figure5-paper-comparison-report",
        "method_versions": method_versions(),
        "discrepancy_rule": {
            "rule": DISCREPANCY_RULE,
            "paper_evidence_role": "image-derived external comparison only",
            "agreement_can_override_numerical_convergence_or_ivp_validation": False,
            "discrepancy_action": "investigate and document; do not replace authoritative production status or period values",
        },
        "source_counts": {
            "authoritative_browser_records_from_task079": len(task079_browser["browser_records"]),
            "paper_upper_period_samples": len(upper_rows),
            "paper_upper_hopf_boundary_rows": len(read_csv(PAPER_UPPER_BOUNDARIES)),
            "paper_lower_curve_rows": len(lower_rows),
        },
        "pairwise_comparisons": pairwise,
        "linearized_curve_summary": {
            "paper_curve_id": "equilibrium_linearized_period_red_curve",
            "authoritative_source": rel(T210_LINEARIZED),
            "paper_row_count_compared_to_nearest_authoritative_row": len(linearized_deltas),
            "status_counts": dict(sorted(linearized_statuses.items())),
            "median_abs_delta_log_period_natural": abs_deltas[len(abs_deltas) // 2],
            "max_abs_delta_log_period_natural": max(abs_deltas),
        },
        "scientific_outcome": {
            "accepted_native_nonlinear_points": task079_browser["interpolation_review"]["accepted_native_nonlinear_source_point_count"],
            "interpolated_nonlinear_points": task079_browser["interpolation_review"]["interpolated_record_count"],
            "unresolved_native_targets": task079_browser["interpolation_review"]["blocked_region_counts"]["resolution_unresolved_targets"],
            "ivp_failures": task079_browser["stability_and_validation_barriers"]["ivp_failure_target_ids"],
            "floquet_ambiguous_or_unstable_targets": task079_browser["stability_and_validation_barriers"]["ambiguous_or_unstable_target_ids"],
        },
        "provenance": {
            "task": "TASK-080",
            "created_by": "generate_figure5_final_artifacts.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": final_source_artifacts(include_outputs=False),
        },
    }


def final_source_artifacts(*, include_outputs: bool) -> list[dict[str, str]]:
    paths = [
        (GENERATOR, "TASK-080 final artifact generator"),
        (TASK079_BROWSER, "TASK-079 authoritative browser/interpolation dataset input"),
        (PAPER_DIGITIZATION, "TASK-063 paper digitization summary"),
        (PAPER_UPPER_SAMPLES, "TASK-063 upper period-map paper samples"),
        (PAPER_UPPER_BOUNDARIES, "TASK-063 upper Hopf-boundary paper samples"),
        (PAPER_LOWER_CURVES, "TASK-063 lower T=210 K paper curves"),
        (FULL_DOMAIN_POINTS, "TASK-075 accepted nonlinear production records"),
        (FULL_DOMAIN_EVENTS, "TASK-075 unresolved/gap production events"),
        (T210_LINEARIZED, "TASK-074 independent T=210 K linearized-period curve"),
        (FLOQUET_DIAGNOSTICS, "TASK-077 Floquet diagnostics"),
        (IVP_VALIDATION, "TASK-078 independent IVP validation"),
        (HOPF_LOCI, "Episode 006 Hopf-locus coordinate reference"),
        (TASK063_DOC, "TASK-063 digitized-paper comparison policy"),
        (TASK069_DOC, "TASK-069 subordinate image-evidence and explicit-gap policy"),
        (TASK070_DOC, "TASK-070 production schema documentation"),
        (TASK074_DOC, "TASK-074 lower-panel linearized-period documentation"),
        (TASK075_DOC, "TASK-075 full-domain continuation documentation"),
        (TASK076_DOC, "TASK-076 Hopf-gap policy documentation"),
        (TASK077_DOC, "TASK-077 Floquet documentation"),
        (TASK078_DOC, "TASK-078 IVP validation documentation"),
        (TASK079_DOC, "TASK-079 browser/interpolation documentation"),
        (DOC, "TASK-080 final-artifact documentation"),
        (README, "Episode 008 documentation index"),
    ]
    if include_outputs:
        paths.extend(
            [
                (FINAL_PLOT, "TASK-080 final reproduction plot output"),
                (FINAL_COMPARISON, "TASK-080 paper-comparison report output"),
            ]
        )
    return [source_record(path, role) for path, role in paths]


def build_final_browser_artifact() -> dict[str, Any]:
    task079_browser = load_json(TASK079_BROWSER)
    locus = HopfLocusCoordinates.from_episode6_csv(HOPF_LOCI)
    records = final_browser_records(task079_browser, locus)
    category_counts = Counter(str(record["display_category"]) for record in records)
    status_counts = Counter(str(record["validity"]["status"]) for record in records)
    layer_counts = Counter(str(record["display_layer"]) for record in records)
    artifact = {
        "schema_version": EPISODE8_PRODUCTION_SCHEMA_VERSION,
        "artifact_kind": "browser-display-dataset",
        "artifact_id": "task080-figure5-final-browser-dataset",
        "method_versions": method_versions(),
        "coordinate_conventions": coordinate_conventions(),
        "provenance": {
            "task": "TASK-080",
            "created_by": "generate_figure5_final_artifacts.py",
            "digitized_paper_data_policy": "external-comparison-only",
            "source_artifacts": final_source_artifacts(include_outputs=True),
        },
        "browser_records": records,
        "dataset_summary": {
            "final_browser_dataset_version": SCHEMA_VERSION,
            "record_count": len(records),
            "record_category_counts": dict(sorted(category_counts.items())),
            "validity_status_counts": dict(sorted(status_counts.items())),
            "display_layer_counts": dict(sorted(layer_counts.items())),
            "authoritative_record_count": sum(1 for record in records if record["validity"]["authoritative"]),
            "external_comparison_record_count": status_counts.get("external_comparison", 0),
            "interpolated_nonlinear_record_count": category_counts.get("validated_interpolated_nonlinear", 0),
            "compact_browser_payload_policy": "records carry only calibrated coordinates, periods, uncertainty, and source links; raw raster pixels and Episode 007 widget code are excluded",
        },
        "final_plot_outputs": [{"path": rel(FINAL_PLOT), "sha256": sha(FINAL_PLOT), "role": "paper-facing Figure 5 reproduction plot"}],
        "paper_comparison_report": {"path": rel(FINAL_COMPARISON), "sha256": sha(FINAL_COMPARISON)},
        "source_separation_policy": {
            "episode007_widget_integration_code_used": False,
            "browser_artifact_role": "data-only JSON payload for future browser use",
            "digitized_paper_records_authoritative": False,
            "heatmap_resampling_used_for_lower_panel": False,
        },
        "upstream_interpolation_review": task079_browser["interpolation_review"],
        "lower_panel_source_policy": task079_browser["lower_panel_source_policy"],
        "image_derived_comparison_policy": {
            "image_derived_values_included": True,
            "paper_digitization_artifact": rel(PAPER_DIGITIZATION),
            "source_flag": "external_digitized_paper_comparison",
            "agreement_with_digitized_pixels_can_override_numerical_validation": False,
            "discrepancy_rule": DISCREPANCY_RULE,
        },
    }
    validate_production_artifact(artifact, root=ROOT, artifact_path=FINAL_BROWSER)
    return artifact


def plot_records_from_files(path: Path) -> None:
    task079_browser = load_json(TASK079_BROWSER)
    upper_rows = read_csv(PAPER_UPPER_SAMPLES)
    lower_rows = read_csv(PAPER_LOWER_CURVES)
    records = task079_browser["browser_records"]
    solved_upper = [r for r in records if r["display_layer"] == "upper_period_map_nonlinear_solved"]
    unresolved = [r for r in records if r["display_category"] == "gap_unresolved_native_target"]
    hopf = [r for r in records if r["display_category"] == "hopf_limit_explicit_gap"]
    invalid = [r for r in records if r["display_category"] == "invalid_outside_hopf_domain"]
    lower_nonlinear = [r for r in records if r["display_layer"] == "lower_panel_T210K_nonlinear_continuation"]
    linearized = [r for r in records if r["display_layer"] == "lower_panel_T210K_linearized_curve" and r["display_period"]["value"] is not None]
    red = [row for row in lower_rows if row["curve_id"] == "equilibrium_linearized_period_red_curve"]
    black = [row for row in lower_rows if row["curve_id"] == "nonlinear_limitcycle_period_black_curve"]

    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(9.0, 8.0), constrained_layout=True)
    if upper_rows:
        sc = ax_top.scatter(
            [float(row["temperature_K"]) for row in upper_rows],
            [float(row["w_m_s"]) for row in upper_rows],
            c=[math.log10(float(row["period_s"])) for row in upper_rows],
            s=15,
            cmap="viridis",
            alpha=0.75,
            label="paper image period samples (TASK-063)",
        )
        cbar = fig.colorbar(sc, ax=ax_top, pad=0.01)
        cbar.set_label("paper log10(period / s)")
    ax_top.scatter(
        [r["coordinates"]["temperature"]["value"] for r in unresolved],
        [r["coordinates"]["w"]["value"] for r in unresolved],
        marker="x",
        c="0.65",
        s=18,
        linewidths=0.8,
        label="unresolved production gaps",
    )
    ax_top.scatter(
        [r["coordinates"]["temperature"]["value"] for r in invalid],
        [r["coordinates"]["w"]["value"] for r in invalid],
        marker="|",
        c="tab:red",
        s=25,
        label="invalid outside Hopf bracket",
    )
    ax_top.scatter(
        [r["coordinates"]["temperature"]["value"] for r in hopf],
        [r["coordinates"]["w"]["value"] for r in hopf],
        marker="^",
        facecolors="none",
        edgecolors="tab:orange",
        s=80,
        label="Hopf-limit explicit gaps",
    )
    ax_top.scatter(
        [r["coordinates"]["temperature"]["value"] for r in solved_upper],
        [r["coordinates"]["w"]["value"] for r in solved_upper],
        marker="*",
        c="black",
        s=180,
        label="accepted native nonlinear solve",
        zorder=5,
    )
    ax_top.set_yscale("log")
    ax_top.set_xlim(189, 241)
    ax_top.set_ylim(4.0e-4, 2.4)
    ax_top.set_xlabel("Temperature T (K)")
    ax_top.set_ylabel("vertical velocity w (m s$^{-1}$)")
    ax_top.set_title("Figure 5 upper period map: final Episode 008 evidence")
    ax_top.legend(loc="lower right", fontsize=8)

    ax_bottom.plot(
        [float(row["w_m_s"]) for row in red],
        [float(row["period_s"]) for row in red],
        color="tab:red",
        alpha=0.35,
        linewidth=2.0,
        label="paper red linearized curve (image-derived)",
    )
    ax_bottom.plot(
        [float(row["w_m_s"]) for row in black],
        [float(row["period_s"]) for row in black],
        color="black",
        alpha=0.35,
        linewidth=2.0,
        label="paper black nonlinear curve (image-derived)",
    )
    ax_bottom.plot(
        [r["coordinates"]["w"]["value"] for r in linearized],
        [r["display_period"]["value"] for r in linearized],
        color="tab:red",
        linewidth=1.2,
        label="TASK-074 independent linearized period",
    )
    ax_bottom.scatter(
        [r["coordinates"]["w"]["value"] for r in lower_nonlinear],
        [r["display_period"]["value"] for r in lower_nonlinear],
        marker="*",
        c="black",
        s=160,
        label="TASK-075 accepted nonlinear solve",
        zorder=5,
    )
    ax_bottom.set_xscale("log")
    ax_bottom.set_xlim(4.5e-4, 2.2)
    ax_bottom.set_ylim(0, 18000)
    ax_bottom.set_xlabel("vertical velocity w (m s$^{-1}$) at T=210 K")
    ax_bottom.set_ylabel("period (s)")
    ax_bottom.set_title("Figure 5 lower slice: nonlinear production + independent linearized curve")
    ax_bottom.legend(loc="upper right", fontsize=8)
    fig.savefig(path, dpi=180, metadata={"Software": "generate_figure5_final_artifacts.py"})
    plt.close(fig)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value))


def write_or_check(*, check: bool) -> None:
    if check:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_plot = Path(tmpdir) / FINAL_PLOT.name
            plot_records_from_files(temp_plot)
            if not FINAL_PLOT.is_file():
                raise SystemExit(f"missing {rel(FINAL_PLOT)}")
            if temp_plot.read_bytes() != FINAL_PLOT.read_bytes():
                raise SystemExit(f"{rel(FINAL_PLOT)} is not current; regenerate without --check")
        task079_browser = load_json(TASK079_BROWSER)
        comparison = build_comparison_report(task079_browser)
        browser = build_final_browser_artifact()
        for path, value in ((FINAL_COMPARISON, comparison), (FINAL_BROWSER, browser)):
            expected = canonical_json_bytes(value)
            if not path.is_file():
                raise SystemExit(f"missing {rel(path)}")
            if path.read_bytes() != expected:
                raise SystemExit(f"{rel(path)} is not current; regenerate without --check")
        validate_production_artifact(json.loads(FINAL_BROWSER.read_text()), root=ROOT, artifact_path=FINAL_BROWSER)
        print(f"{rel(FINAL_BROWSER)}, {rel(FINAL_COMPARISON)}, and {rel(FINAL_PLOT)} are current")
        return

    plot_records_from_files(FINAL_PLOT)
    task079_browser = load_json(TASK079_BROWSER)
    comparison = build_comparison_report(task079_browser)
    write_json(FINAL_COMPARISON, comparison)
    browser = build_final_browser_artifact()
    write_json(FINAL_BROWSER, browser)
    print(f"wrote {rel(FINAL_BROWSER)}")
    print(f"wrote {rel(FINAL_COMPARISON)}")
    print(f"wrote {rel(FINAL_PLOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed final artifacts are byte-current")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_or_check(check=bool(args.check))


if __name__ == "__main__":
    main()
