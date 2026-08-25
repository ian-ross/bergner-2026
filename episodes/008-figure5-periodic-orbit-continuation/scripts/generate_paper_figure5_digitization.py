#!/usr/bin/env python3
"""Digitize Bergner & Spichtinger (2026) Figure 5 from the saved publisher image.

The generated artifacts are explicitly image-derived comparison evidence for
Episode 008.  They are not backend continuation results and must not be used as
convergence evidence for the native/Python collocation workflow.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bergner_spichtinger_2026.episode8_production_schema import (  # noqa: E402
    CHECKSUM_CONVENTION,
    canonical_json_bytes,
)

EPISODE = Path(__file__).resolve().parents[1]
OUTPUT = EPISODE / "outputs"
GENERATOR = Path(__file__).resolve()
SOURCE_IMAGE = ROOT / "sources/original/bergner-spichtinger-2026_files/m_043115_1_5.0297531.figures.online.f5.jpeg"
SOURCE_PDF = ROOT / "sources/original/bergner-spichtinger-2026.pdf"

JSON_ARTIFACT = OUTPUT / "paper_figure5_digitization.json"
UPPER_BOUNDARY_CSV = OUTPUT / "paper_figure5_digitization_upper_hopf_boundaries.csv"
UPPER_COLOR_CSV = OUTPUT / "paper_figure5_digitization_upper_period_samples.csv"
LOWER_CURVES_CSV = OUTPUT / "paper_figure5_digitization_lower_curves.csv"
OVERLAY_PNG = OUTPUT / "paper_figure5_digitization_overlay.png"
RESIDUAL_PNG = OUTPUT / "paper_figure5_digitization_residuals.png"

SCHEMA_VERSION = "episode008-paper-figure5-digitization-v1"
METHOD_VERSION = "manual-calibration-threshold-component-colorbar-v1"
ARTIFACT_KIND = "task063-paper-figure5-digitization"


@dataclass(frozen=True)
class PanelCalibration:
    """Affine calibration for a log-x/log-y or linear-x/linear-y panel."""

    name: str
    pixel_x_min: int
    pixel_x_max: int
    pixel_y_top: int
    pixel_y_bottom: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    x_scale: str
    y_scale: str
    x_quantity: str
    y_quantity: str
    x_unit: str
    y_unit: str

    def x_to_physical(self, pixel_x: float) -> float:
        fraction = (pixel_x - self.pixel_x_min) / (self.pixel_x_max - self.pixel_x_min)
        value = self.x_min + fraction * (self.x_max - self.x_min)
        return 10.0**value if self.x_scale == "log10" else value

    def y_to_physical(self, pixel_y: float) -> float:
        fraction_from_bottom = (self.pixel_y_bottom - pixel_y) / (self.pixel_y_bottom - self.pixel_y_top)
        value = self.y_min + fraction_from_bottom * (self.y_max - self.y_min)
        return 10.0**value if self.y_scale == "log10" else value

    def physical_x_to_pixel(self, x_value: float) -> float:
        coordinate = math.log10(x_value) if self.x_scale == "log10" else x_value
        fraction = (coordinate - self.x_min) / (self.x_max - self.x_min)
        return self.pixel_x_min + fraction * (self.pixel_x_max - self.pixel_x_min)

    def physical_y_to_pixel(self, y_value: float) -> float:
        coordinate = math.log10(y_value) if self.y_scale == "log10" else y_value
        fraction = (coordinate - self.y_min) / (self.y_max - self.y_min)
        return self.pixel_y_bottom - fraction * (self.pixel_y_bottom - self.pixel_y_top)

    def pixel_resolution(self) -> dict[str, Any]:
        x_per_pixel = (self.x_max - self.x_min) / (self.pixel_x_max - self.pixel_x_min)
        y_per_pixel = (self.y_max - self.y_min) / (self.pixel_y_bottom - self.pixel_y_top)
        return {
            "x_half_pixel_uncertainty": 0.5 * x_per_pixel,
            "x_uncertainty_coordinate": "log10(" + self.x_unit + ")" if self.x_scale == "log10" else self.x_unit,
            "y_half_pixel_uncertainty": 0.5 * y_per_pixel,
            "y_uncertainty_coordinate": "log10(" + self.y_unit + ")" if self.y_scale == "log10" else self.y_unit,
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pixel_bounds": {
                "x_min": self.pixel_x_min,
                "x_max": self.pixel_x_max,
                "y_top": self.pixel_y_top,
                "y_bottom": self.pixel_y_bottom,
            },
            "physical_bounds": {
                self.x_quantity: {"min": self.x_to_physical(self.pixel_x_min), "max": self.x_to_physical(self.pixel_x_max), "unit": self.x_unit},
                self.y_quantity: {"min": self.y_to_physical(self.pixel_y_bottom), "max": self.y_to_physical(self.pixel_y_top), "unit": self.y_unit},
            },
            "axis_scales": {"x": self.x_scale, "y": self.y_scale},
            "pixel_resolution_limits": self.pixel_resolution(),
        }


TOP = PanelCalibration(
    name="upper_period_map",
    pixel_x_min=60,
    pixel_x_max=428,
    pixel_y_top=7,
    pixel_y_bottom=348,
    x_min=190.0,
    x_max=240.0,
    y_min=math.log10(5.0e-4),
    y_max=math.log10(2.0),
    x_scale="linear",
    y_scale="log10",
    x_quantity="temperature",
    y_quantity="vertical_velocity",
    x_unit="K",
    y_unit="m s^-1",
)

BOTTOM = PanelCalibration(
    name="lower_T210K_slice",
    pixel_x_min=64,
    pixel_x_max=429,
    pixel_y_top=407,
    pixel_y_bottom=722,
    x_min=math.log10(5.0e-4),
    x_max=math.log10(2.0),
    y_min=0.0,
    y_max=18000.0,
    x_scale="log10",
    y_scale="linear",
    x_quantity="vertical_velocity",
    y_quantity="period",
    x_unit="m s^-1",
    y_unit="s",
)

COLORBAR = {
    "pixel_x_min": 450,
    "pixel_x_max": 467,
    "pixel_y_top": 7,
    "pixel_y_bottom": 348,
    "log10_period_top": 5.0,
    "log10_period_bottom": 2.0,
    "period_unit": "s",
}


class GenerationError(RuntimeError):
    """Raised when the source figure cannot be digitized reproducibly."""


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path: Path, role: str) -> dict[str, Any]:
    return {"path": rel(path), "sha256": sha(path), "role": role, "bytes": path.stat().st_size}


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(value))


def read_rgb() -> np.ndarray:
    if not SOURCE_IMAGE.is_file():
        raise GenerationError(f"missing source image: {SOURCE_IMAGE}")
    image = Image.open(SOURCE_IMAGE).convert("RGB")
    if image.size != (520, 760):
        raise GenerationError(f"unexpected Figure 5 image size {image.size}; calibration is for 520x760")
    return np.asarray(image, dtype=np.uint8)


def saturation_and_value(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scaled = rgb.astype(float) / 255.0
    mx = scaled.max(axis=2)
    mn = scaled.min(axis=2)
    sat = np.divide(mx - mn, mx, out=np.zeros_like(mx), where=mx > 0.0)
    return sat, mx


def contiguous_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = int(idx[0])
    previous = int(idx[0])
    for raw in idx[1:]:
        current = int(raw)
        if current == previous + 1:
            previous = current
        else:
            runs.append((start, previous))
            start = previous = current
    runs.append((start, previous))
    return runs


def extract_upper_boundaries(rgb: np.ndarray) -> list[dict[str, Any]]:
    sat, val = saturation_and_value(rgb)
    y_slice = slice(TOP.pixel_y_top, TOP.pixel_y_bottom + 1)
    x_slice = slice(TOP.pixel_x_min, TOP.pixel_x_max + 1)
    # The upper panel colored region is the only contiguous high-saturation band
    # in each column.  Grid lines and labels are low-saturation; black borders
    # are low-value.  This deliberately extracts the color-domain edge rather
    # than trying to trace antialiased black strokes.
    colored = (sat[y_slice, x_slice] > 0.20) & (val[y_slice, x_slice] > 0.25)
    rows: list[dict[str, Any]] = []
    for offset, pixel_x in enumerate(range(TOP.pixel_x_min, TOP.pixel_x_max + 1)):
        runs = contiguous_runs(colored[:, offset])
        if not runs:
            continue
        top_run, bottom_run = max(runs, key=lambda item: item[1] - item[0])
        if bottom_run - top_run + 1 < 20:
            continue
        upper_y = TOP.pixel_y_top + top_run
        lower_y = TOP.pixel_y_top + bottom_run
        upper_w = TOP.y_to_physical(upper_y)
        lower_w = TOP.y_to_physical(lower_y)
        temperature = TOP.x_to_physical(pixel_x)
        rows.append(
            {
                "panel": "upper_period_map",
                "pixel_x": pixel_x,
                "temperature_K": temperature,
                "upper_boundary_pixel_y": upper_y,
                "upper_boundary_w_m_s": upper_w,
                "upper_boundary_log_w_ln_m_s": math.log(upper_w),
                "lower_boundary_pixel_y": lower_y,
                "lower_boundary_w_m_s": lower_w,
                "lower_boundary_log_w_ln_m_s": math.log(lower_w),
                "direct_digitization": True,
                "validity": "direct_edge_detected",
                "edge_detector": "largest high-saturation contiguous vertical run",
                "vertical_color_run_pixels": bottom_run - top_run + 1,
            }
        )
    if len(rows) < 300:
        raise GenerationError(f"upper-boundary extraction found only {len(rows)} columns")
    return rows


def colorbar_profile(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x0 = COLORBAR["pixel_x_min"] + 2
    x1 = COLORBAR["pixel_x_max"] - 2
    y0 = COLORBAR["pixel_y_top"]
    y1 = COLORBAR["pixel_y_bottom"]
    strip = rgb[y0 : y1 + 1, x0 : x1 + 1].astype(float)
    colors = strip.mean(axis=1)
    ys = np.arange(y0, y1 + 1)
    frac = (ys - y0) / (y1 - y0)
    log_period = COLORBAR["log10_period_top"] + frac * (
        COLORBAR["log10_period_bottom"] - COLORBAR["log10_period_top"]
    )
    return colors, log_period


def sample_patch_color(rgb: np.ndarray, pixel_x: int, pixel_y: int) -> tuple[np.ndarray, int, bool]:
    x0 = max(0, pixel_x - 2)
    x1 = min(rgb.shape[1] - 1, pixel_x + 2)
    y0 = max(0, pixel_y - 2)
    y1 = min(rgb.shape[0] - 1, pixel_y + 2)
    patch = rgb[y0 : y1 + 1, x0 : x1 + 1]
    sat, val = saturation_and_value(patch)
    colorful = (sat > 0.20) & (val > 0.25)
    if np.any(colorful):
        selected = patch[colorful]
        return selected.astype(float).mean(axis=0), int(selected.shape[0]), True
    return patch.reshape(-1, 3).astype(float).mean(axis=0), int(patch.shape[0] * patch.shape[1]), False


def estimate_log_period_from_color(color: np.ndarray, colorbar_colors: np.ndarray, colorbar_log_period: np.ndarray) -> tuple[float, int, float]:
    distances = np.linalg.norm(colorbar_colors - color[None, :], axis=1)
    idx = int(np.argmin(distances))
    return float(colorbar_log_period[idx]), int(COLORBAR["pixel_y_top"] + idx), float(distances[idx])


def extract_upper_period_samples(rgb: np.ndarray, boundaries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_x = {int(row["pixel_x"]): row for row in boundaries}
    colorbar_colors, colorbar_log_period = colorbar_profile(rgb)
    rows: list[dict[str, Any]] = []
    vertical_fractions = [round(float(v), 2) for v in np.linspace(0.08, 0.92, 15)]
    for pixel_x in range(64, 425, 8):
        if pixel_x not in by_x:
            continue
        boundary = by_x[pixel_x]
        upper_y = float(boundary["upper_boundary_pixel_y"])
        lower_y = float(boundary["lower_boundary_pixel_y"])
        for fraction_from_lower in vertical_fractions:
            pixel_y_float = lower_y + fraction_from_lower * (upper_y - lower_y)
            pixel_y = int(round(pixel_y_float))
            mean_color, colorful_pixels, color_valid = sample_patch_color(rgb, pixel_x, pixel_y)
            log_period, colorbar_y, color_distance = estimate_log_period_from_color(
                mean_color, colorbar_colors, colorbar_log_period
            )
            w_value = TOP.y_to_physical(pixel_y_float)
            rows.append(
                {
                    "sample_id": f"upper-color-x{pixel_x:03d}-f{int(round(100*fraction_from_lower)):02d}",
                    "panel": "upper_period_map",
                    "pixel_x": pixel_x,
                    "pixel_y": pixel_y,
                    "sample_position_fraction_from_lower_boundary": fraction_from_lower,
                    "temperature_K": TOP.x_to_physical(pixel_x),
                    "log_w_ln_m_s": math.log(w_value),
                    "w_m_s": w_value,
                    "log10_period_from_colorbar": log_period,
                    "period_s": 10.0**log_period,
                    "source_type": "direct_digitized_color_sample",
                    "value_role": "image_colorbar_lookup_not_backend_result",
                    "validity": "valid" if color_valid else "low_saturation_patch",
                    "patch_colorful_pixel_count": colorful_pixels,
                    "mean_rgb": [round(float(v), 6) for v in mean_color],
                    "matched_colorbar_pixel_y": colorbar_y,
                    "rgb_distance_to_colorbar": color_distance,
                }
            )
    if len(rows) < 500:
        raise GenerationError(f"upper color extraction produced only {len(rows)} samples")
    return rows


def connected_component_rows(
    mask: np.ndarray,
    *,
    bbox: tuple[int, int, int, int],
    component_rank: int = 0,
) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    roi = mask[y0 : y1 + 1, x0 : x1 + 1]
    labels, count = ndimage.label(roi, structure=np.ones((3, 3), dtype=int))
    if count == 0:
        raise GenerationError(f"no connected components found in {bbox}")
    component_sizes = ndimage.sum(np.ones_like(labels), labels, index=np.arange(1, count + 1))
    order = np.argsort(component_sizes)[::-1]
    if component_rank >= len(order):
        raise GenerationError(f"component rank {component_rank} unavailable in {bbox}")
    label_value = int(order[component_rank] + 1)
    ys, xs = np.nonzero(labels == label_value)
    return np.column_stack((xs + x0, ys + y0)).astype(int)


def aggregate_curve_pixels(
    pixels: np.ndarray,
    *,
    curve_id: str,
    color_name: str,
    calibration: PanelCalibration,
    source_type: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pixel_x in sorted(np.unique(pixels[:, 0])):
        y_values = pixels[pixels[:, 0] == pixel_x, 1]
        pixel_y = float(np.median(y_values))
        w_value = calibration.x_to_physical(float(pixel_x))
        period = calibration.y_to_physical(pixel_y)
        rows.append(
            {
                "curve_id": curve_id,
                "panel": "lower_T210K_slice",
                "color_name": color_name,
                "pixel_x": int(pixel_x),
                "pixel_y_median": pixel_y,
                "pixel_y_min": int(y_values.min()),
                "pixel_y_max": int(y_values.max()),
                "pixels_in_column": int(y_values.size),
                "temperature_K": 210.0,
                "w_m_s": w_value,
                "log_w_ln_m_s": math.log(w_value),
                "period_s": period,
                "source_type": source_type,
                "direct_digitization": True,
                "validity": "valid_curve_pixel",
            }
        )
    return rows


def extract_lower_curves(rgb: np.ndarray) -> list[dict[str, Any]]:
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    red_mask = (r > 120) & (r > g + 25) & (r > b + 25) & (g < 180) & (b < 180)
    red_pixels = connected_component_rows(
        red_mask,
        bbox=(BOTTOM.pixel_x_min, BOTTOM.pixel_y_top, BOTTOM.pixel_x_max - 1, BOTTOM.pixel_y_bottom),
        component_rank=0,
    )
    dark_mask = (r < 120) & (g < 120) & (b < 120)
    # Restrict to the plotted nonlinear black curve.  This avoids axes, labels,
    # tick text, and the legend while preserving the visible curve and endpoints.
    black_pixels = connected_component_rows(dark_mask, bbox=(150, 500, 370, 704), component_rank=0)
    rows = aggregate_curve_pixels(
        red_pixels,
        curve_id="equilibrium_linearized_period_red_curve",
        color_name="red",
        calibration=BOTTOM,
        source_type="direct_digitized_curve_pixel",
    )
    rows.extend(
        aggregate_curve_pixels(
            black_pixels,
            curve_id="nonlinear_limitcycle_period_black_curve",
            color_name="black",
            calibration=BOTTOM,
            source_type="direct_digitized_curve_pixel",
        )
    )
    if Counter(row["curve_id"] for row in rows)["equilibrium_linearized_period_red_curve"] < 300:
        raise GenerationError("red lower-panel curve extraction did not span the expected x range")
    if Counter(row["curve_id"] for row in rows)["nonlinear_limitcycle_period_black_curve"] < 100:
        raise GenerationError("black lower-panel curve extraction did not span the expected x range")
    return rows


def calibration_cross_checks() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for temp in range(190, 241, 5):
        predicted = TOP.physical_x_to_pixel(float(temp))
        observed = round(predicted)
        checks.append(
            {
                "panel": "upper_period_map",
                "axis": "temperature_K",
                "tick_value": float(temp),
                "predicted_pixel": predicted,
                "observed_pixel_integer": observed,
                "residual_px": observed - predicted,
            }
        )
    for w in (1.0, 1.0e-1, 1.0e-2, 1.0e-3):
        predicted = TOP.physical_y_to_pixel(w)
        observed = round(predicted)
        checks.append(
            {
                "panel": "upper_period_map",
                "axis": "vertical_velocity_m_s",
                "tick_value": w,
                "predicted_pixel": predicted,
                "observed_pixel_integer": observed,
                "residual_px": observed - predicted,
            }
        )
    for w in (1.0e-3, 1.0e-2, 1.0e-1, 1.0):
        predicted = BOTTOM.physical_x_to_pixel(w)
        observed = round(predicted)
        checks.append(
            {
                "panel": "lower_T210K_slice",
                "axis": "vertical_velocity_m_s",
                "tick_value": w,
                "predicted_pixel": predicted,
                "observed_pixel_integer": observed,
                "residual_px": observed - predicted,
            }
        )
    for period in range(0, 18001, 2000):
        predicted = BOTTOM.physical_y_to_pixel(float(period))
        observed = round(predicted)
        checks.append(
            {
                "panel": "lower_T210K_slice",
                "axis": "period_s",
                "tick_value": float(period),
                "predicted_pixel": predicted,
                "observed_pixel_integer": observed,
                "residual_px": observed - predicted,
            }
        )
    return checks


def validation_summary(
    boundaries: Sequence[Mapping[str, Any]],
    upper_samples: Sequence[Mapping[str, Any]],
    lower_curves: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checks = calibration_cross_checks()
    residuals = [abs(float(row["residual_px"])) for row in checks]
    upper_distances = [float(row["rgb_distance_to_colorbar"]) for row in upper_samples]
    curve_counts = Counter(row["curve_id"] for row in lower_curves)
    boundary_run_lengths = [int(row["vertical_color_run_pixels"]) for row in boundaries]
    black_rows = [row for row in lower_curves if row["curve_id"] == "nonlinear_limitcycle_period_black_curve"]
    red_rows = [row for row in lower_curves if row["curve_id"] == "equilibrium_linearized_period_red_curve"]
    return {
        "calibration_cross_checks": checks,
        "calibration_residual_px_max_abs": max(residuals),
        "calibration_residual_px_rms": math.sqrt(sum(v * v for v in residuals) / len(residuals)),
        "upper_boundary_column_count": len(boundaries),
        "upper_boundary_color_run_pixels_min": min(boundary_run_lengths),
        "upper_boundary_color_run_pixels_max": max(boundary_run_lengths),
        "upper_color_sample_count": len(upper_samples),
        "upper_color_validity_counts": dict(Counter(row["validity"] for row in upper_samples)),
        "upper_colorbar_rgb_distance_median": float(np.median(upper_distances)),
        "upper_colorbar_rgb_distance_p95": float(np.percentile(upper_distances, 95)),
        "lower_curve_column_counts": dict(curve_counts),
        "lower_curve_endpoints": {
            "equilibrium_linearized_period_red_curve": {
                "first_w_m_s": red_rows[0]["w_m_s"],
                "last_w_m_s": red_rows[-1]["w_m_s"],
                "endpoint_policy": "visible red pixels reach both horizontal plot limits; no extrapolated endpoints added",
            },
            "nonlinear_limitcycle_period_black_curve": {
                "first_w_m_s": black_rows[0]["w_m_s"],
                "last_w_m_s": black_rows[-1]["w_m_s"],
                "endpoint_policy": "curve exists only over visible paper limit-cycle segment; no Hopf endpoint extrapolation added",
            },
        },
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_overlay(rgb: np.ndarray, boundaries: Sequence[Mapping[str, Any]], lower_curves: Sequence[Mapping[str, Any]]) -> None:
    image = Image.fromarray(rgb).convert("RGBA")
    draw = ImageDraw.Draw(image)
    upper_line = [(int(row["pixel_x"]), int(row["upper_boundary_pixel_y"])) for row in boundaries]
    lower_line = [(int(row["pixel_x"]), int(row["lower_boundary_pixel_y"])) for row in boundaries]
    if len(upper_line) > 1:
        draw.line(upper_line, fill=(0, 255, 255, 255), width=1)
    if len(lower_line) > 1:
        draw.line(lower_line, fill=(0, 0, 255, 255), width=1)
    for curve_id, color in (
        ("equilibrium_linearized_period_red_curve", (255, 255, 0, 255)),
        ("nonlinear_limitcycle_period_black_curve", (0, 255, 0, 255)),
    ):
        points = [
            (int(row["pixel_x"]), int(round(float(row["pixel_y_median"]))))
            for row in lower_curves
            if row["curve_id"] == curve_id
        ]
        if len(points) > 1:
            draw.line(points, fill=color, width=1)
    image.convert("RGB").save(OVERLAY_PNG)


def make_residual_plot(validation: Mapping[str, Any], upper_samples: Sequence[Mapping[str, Any]]) -> None:
    width, height = 640, 360
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    margin_left, margin_right, margin_top, margin_bottom = 60, 20, 25, 45
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    draw.rectangle((margin_left, margin_top, width - margin_right, height - margin_bottom), outline="black")
    distances = np.asarray([float(row["rgb_distance_to_colorbar"]) for row in upper_samples])
    bins = np.linspace(0.0, max(1.0, float(distances.max())), 31)
    counts, edges = np.histogram(distances, bins=bins)
    max_count = max(1, int(counts.max()))
    for idx, count in enumerate(counts):
        x0 = margin_left + idx * plot_w / len(counts)
        x1 = margin_left + (idx + 1) * plot_w / len(counts)
        y1 = height - margin_bottom
        y0 = y1 - (int(count) / max_count) * plot_h
        draw.rectangle((x0, y0, x1, y1), fill=(220, 120, 60), outline=(120, 70, 40))
    draw.text((margin_left, 5), "Upper-panel colorbar RGB-distance residuals", fill="black")
    draw.text((margin_left, height - 30), f"0 to {edges[-1]:.1f} RGB units; p95={validation['upper_colorbar_rgb_distance_p95']:.1f}", fill="black")
    draw.text((margin_left + 285, height - 30), f"calibration max |residual|={validation['calibration_residual_px_max_abs']:.3f} px", fill="black")
    image.save(RESIDUAL_PNG)


def build_artifact(
    boundaries: Sequence[Mapping[str, Any]],
    upper_samples: Sequence[Mapping[str, Any]],
    lower_curves: Sequence[Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_kind": ARTIFACT_KIND,
        "method_version": METHOD_VERSION,
        "checksum_convention": CHECKSUM_CONVENTION,
        "data_role": "external_digitized_paper_comparison_only",
        "not_authoritative_for_continuation_convergence": True,
        "source_figure": {
            "paper": "Bergner & Spichtinger (2026), Figure 5",
            "primary_extraction_source": rel(SOURCE_IMAGE),
            "secondary_source_checksum_recorded": rel(SOURCE_PDF),
            "source_originals_modified": False,
        },
        "provenance": {
            "generator": source_record(GENERATOR, "digitization_generator"),
            "source_artifacts": [
                source_record(SOURCE_IMAGE, "primary_saved_publisher_figure5_image"),
                source_record(SOURCE_PDF, "saved_source_pdf_checksum_reference"),
            ],
            "extraction_steps": [
                "manual pixel-axis calibration from saved Figure 5 raster",
                "upper-panel high-saturation domain-edge extraction for Hopf boundaries",
                "empirical colorbar lookup from saved raster for upper-panel period colors",
                "lower-panel red and black connected-component curve extraction",
                "deterministic overlay and residual diagnostic rendering",
            ],
        },
        "schemas": {
            "upper_hopf_boundaries_csv": {
                "path": rel(UPPER_BOUNDARY_CSV),
                "primary_key": ["panel", "pixel_x"],
                "units": {
                    "temperature_K": "K",
                    "upper_boundary_w_m_s": "m s^-1",
                    "upper_boundary_log_w_ln_m_s": "ln(m s^-1)",
                    "lower_boundary_w_m_s": "m s^-1",
                    "lower_boundary_log_w_ln_m_s": "ln(m s^-1)",
                },
                "coordinate_convention": "temperature-linear/log10-w-axis-from-paper-raster",
                "source_type": "direct edge samples; no boundary interpolation rows added",
            },
            "upper_period_samples_csv": {
                "path": rel(UPPER_COLOR_CSV),
                "primary_key": ["sample_id"],
                "units": {"temperature_K": "K", "log_w_ln_m_s": "ln(m s^-1)", "period_s": "s"},
                "coordinate_convention": "calibrated pixel centers inside directly digitized Hopf-band",
                "source_type": "direct color samples matched to the paper colorbar; no backend computation",
            },
            "lower_curves_csv": {
                "path": rel(LOWER_CURVES_CSV),
                "primary_key": ["curve_id", "pixel_x"],
                "units": {"temperature_K": "K", "w_m_s": "m s^-1", "period_s": "s"},
                "coordinate_convention": "T=210 K lower panel, log10-w x-axis, linear-period y-axis",
                "curve_identity": {
                    "equilibrium_linearized_period_red_curve": "paper red curve labelled tau=2*pi/Im(lambda)",
                    "nonlinear_limitcycle_period_black_curve": "paper black curve labelled tau_limitcycle",
                },
                "gap_policy": "visible pixels only; no extrapolation through gaps or to Hopf endpoints",
            },
        },
        "calibration": {
            "upper_panel": TOP.to_json(),
            "lower_panel": BOTTOM.to_json(),
            "colorbar": {
                "pixel_bounds": {
                    "x_min": COLORBAR["pixel_x_min"],
                    "x_max": COLORBAR["pixel_x_max"],
                    "y_top": COLORBAR["pixel_y_top"],
                    "y_bottom": COLORBAR["pixel_y_bottom"],
                },
                "log10_period_range": {
                    "top": COLORBAR["log10_period_top"],
                    "bottom": COLORBAR["log10_period_bottom"],
                    "unit": "log10(s)",
                },
                "half_pixel_uncertainty_log10_period": 0.5
                * abs(COLORBAR["log10_period_top"] - COLORBAR["log10_period_bottom"])
                / (COLORBAR["pixel_y_bottom"] - COLORBAR["pixel_y_top"]),
            },
        },
        "dataset_summary": {
            "upper_boundary_rows": len(boundaries),
            "upper_period_color_samples": len(upper_samples),
            "lower_curve_rows": len(lower_curves),
            "lower_curve_counts": dict(Counter(row["curve_id"] for row in lower_curves)),
            "machine_readable_outputs": [rel(UPPER_BOUNDARY_CSV), rel(UPPER_COLOR_CSV), rel(LOWER_CURVES_CSV)],
            "validation_outputs": [rel(OVERLAY_PNG), rel(RESIDUAL_PNG)],
        },
        "uncertainty_and_resolution_limits": {
            "pixel_centering": "all physical coordinates inherit at least +/-0.5 pixel uncertainty on each calibrated axis",
            "jpeg_antialiasing": "source is a lossy raster; curve/color values are paper-image evidence, not original numerical arrays",
            "upper_color_period": "period estimates additionally inherit empirical colorbar matching residual and colorbar half-pixel log10-period resolution",
            "lower_curve_period": "lower y-axis period resolution is approximately +/-28.6 s from half a pixel before antialiasing/line-thickness effects",
            "direct_vs_derived_policy": "CSV rows labeled direct_digitization or direct_digitized_color_sample are direct image samples; no derived interpolation rows are emitted in TASK-063 artifacts",
        },
        "validation": dict(validation),
    }


def generate() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rgb = read_rgb()
    boundaries = extract_upper_boundaries(rgb)
    upper_samples = extract_upper_period_samples(rgb, boundaries)
    lower_curves = extract_lower_curves(rgb)
    validation = validation_summary(boundaries, upper_samples, lower_curves)
    artifact = build_artifact(boundaries, upper_samples, lower_curves, validation)

    write_json(JSON_ARTIFACT, artifact)
    write_csv(
        UPPER_BOUNDARY_CSV,
        boundaries,
        [
            "panel",
            "pixel_x",
            "temperature_K",
            "upper_boundary_pixel_y",
            "upper_boundary_w_m_s",
            "upper_boundary_log_w_ln_m_s",
            "lower_boundary_pixel_y",
            "lower_boundary_w_m_s",
            "lower_boundary_log_w_ln_m_s",
            "direct_digitization",
            "validity",
            "edge_detector",
            "vertical_color_run_pixels",
        ],
    )
    write_csv(
        UPPER_COLOR_CSV,
        upper_samples,
        [
            "sample_id",
            "panel",
            "pixel_x",
            "pixel_y",
            "sample_position_fraction_from_lower_boundary",
            "temperature_K",
            "log_w_ln_m_s",
            "w_m_s",
            "log10_period_from_colorbar",
            "period_s",
            "source_type",
            "value_role",
            "validity",
            "patch_colorful_pixel_count",
            "mean_rgb",
            "matched_colorbar_pixel_y",
            "rgb_distance_to_colorbar",
        ],
    )
    write_csv(
        LOWER_CURVES_CSV,
        lower_curves,
        [
            "curve_id",
            "panel",
            "color_name",
            "pixel_x",
            "pixel_y_median",
            "pixel_y_min",
            "pixel_y_max",
            "pixels_in_column",
            "temperature_K",
            "w_m_s",
            "log_w_ln_m_s",
            "period_s",
            "source_type",
            "direct_digitization",
            "validity",
        ],
    )
    make_overlay(rgb, boundaries, lower_curves)
    make_residual_plot(validation, upper_samples)


def check_current() -> None:
    expected_paths = [JSON_ARTIFACT, UPPER_BOUNDARY_CSV, UPPER_COLOR_CSV, LOWER_CURVES_CSV, OVERLAY_PNG, RESIDUAL_PNG]
    before = {path: path.read_bytes() if path.exists() else None for path in expected_paths}
    generate()
    changed = []
    for path in expected_paths:
        after = path.read_bytes()
        if before[path] != after:
            changed.append(rel(path))
    if changed:
        raise SystemExit("digitization artifacts were not current; regenerated: " + ", ".join(changed))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="regenerate and fail if committed outputs were stale")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.check:
        check_current()
    else:
        generate()


if __name__ == "__main__":
    main()
