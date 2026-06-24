#!/usr/bin/env python3
"""Extract and digitize Figure 1 from the Bergner & Spichtinger (2026) PDF.

The saved publisher PDF does not expose Figure 1 as an embedded raster in
``pdfimages``; the figure appears as rendered page content.  This script
therefore reproducibly renders PDF page 12 at high resolution, crops the Figure
1 region, calibrates the three panels, digitizes the visible colored curves, and
writes QA overlays plus provenance metadata.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "sources/original/bergner-spichtinger-2026.pdf"
OUT = ROOT / "episodes/002-figure1-python-continuation/outputs/figure1_digitized"
DPI = 600
BASE_DPI = 300
PAGE_NUMBER = 12

# Coordinates measured on a 300-dpi rendering of PDF page 12.  The script scales
# them to DPI to keep the calibration reproducible and inspectable.
BASE_FIGURE_CROP = (170, 2110, 2320, 2860)  # left, top, right, bottom; includes labels and caption
BASE_PANEL_BOUNDS = {
    "number_concentration": (298, 2150, 862, 2644),
    "mass_concentration": (1009, 2150, 1573, 2644),
    "saturation_ratio": (1696, 2150, 2284, 2644),
}

TEMPERATURES = {
    "blue": {"T_K": 190, "rgb": (0, 0, 255)},
    "gray": {"T_K": 210, "rgb": (128, 128, 128)},
    "red": {"T_K": 230, "rgb": (255, 0, 0)},
}


@dataclass(frozen=True)
class PanelCalibration:
    panel: str
    value_name: str
    value_unit: str
    bounds_px: tuple[int, int, int, int]
    x_min: float = 0.005
    x_max: float = 2.0
    x_scale: str = "log10"
    y_min: float = 0.0
    y_max: float = 1.0
    y_scale: str = "linear"

    def x_to_w(self, x_px: float) -> float:
        left, _top, right, _bottom = self.bounds_px
        f = (x_px - left) / (right - left)
        return 10 ** (math.log10(self.x_min) + f * (math.log10(self.x_max) - math.log10(self.x_min)))

    def y_to_value(self, y_px: float) -> float:
        _left, top, _right, bottom = self.bounds_px
        f = (bottom - y_px) / (bottom - top)
        if self.y_scale == "log10":
            return 10 ** (math.log10(self.y_min) + f * (math.log10(self.y_max) - math.log10(self.y_min)))
        return self.y_min + f * (self.y_max - self.y_min)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scale_box(box: tuple[int, int, int, int], scale: float) -> tuple[int, int, int, int]:
    return tuple(int(round(v * scale)) for v in box)  # type: ignore[return-value]


def render_page(pdf: Path, out_png: Path) -> None:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm is required for reproducible PDF rendering")
    with tempfile.TemporaryDirectory() as td:
        stem = Path(td) / "page"
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(PAGE_NUMBER),
                "-l",
                str(PAGE_NUMBER),
                "-r",
                str(DPI),
                "-png",
                str(pdf),
                str(stem),
            ],
            check=True,
        )
        rendered = Path(td) / f"page-{PAGE_NUMBER}.png"
        shutil.copy2(rendered, out_png)


def list_pdf_images(pdf: Path) -> str:
    if shutil.which("pdfimages") is None:
        return "pdfimages not available"
    proc = subprocess.run(["pdfimages", "-list", str(pdf)], check=True, text=True, capture_output=True)
    return proc.stdout


def calibrations(scale: float) -> dict[str, PanelCalibration]:
    b = {name: scale_box(box, scale) for name, box in BASE_PANEL_BOUNDS.items()}
    return {
        "number_concentration": PanelCalibration(
            "number_concentration", "ice_crystal_number_concentration", "1 kg-1", b["number_concentration"], y_min=1e3, y_max=1e7, y_scale="log10"
        ),
        "mass_concentration": PanelCalibration(
            "mass_concentration", "ice_crystal_mass_concentration", "kg kg-1", b["mass_concentration"], y_min=1e-8, y_max=1e-3, y_scale="log10"
        ),
        "saturation_ratio": PanelCalibration(
            "saturation_ratio", "saturation_ratio", "1", b["saturation_ratio"], y_min=1.4, y_max=1.6, y_scale="linear"
        ),
    }


def color_mask(arr: np.ndarray, color: str) -> np.ndarray:
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    if color == "red":
        return (r > 135) & (r > g + 45) & (r > b + 45)
    if color == "blue":
        return (b > 120) & (b > r + 45) & (b > g + 35)
    if color == "gray":
        # The T=210 K line is neutral gray.  Exclude very dark axes/text and
        # light dotted grid; the per-column robust extraction below removes the
        # remaining grid intersections.
        spread = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
        lum = (r + g + b) / 3
        return (spread < 18) & (lum > 75) & (lum < 190)
    raise ValueError(color)


def digitize_curve(arr: np.ndarray, cal: PanelCalibration, color: str, n_samples: int = 180) -> list[dict[str, object]]:
    left, top, right, bottom = cal.bounds_px
    pad = int(round((DPI / BASE_DPI) * 3))
    roi = arr[top + pad : bottom - pad + 1, left + pad : right - pad + 1]
    mask = color_mask(roi, color)

    # Drop axis/grid pixels near known major grid columns/rows.  This is most
    # important for the neutral gray curve.
    h, w = mask.shape
    major_x = [int(round((math.log10(x) - math.log10(cal.x_min)) / (math.log10(cal.x_max) - math.log10(cal.x_min)) * (right - left))) for x in (0.01, 0.1, 1.0)]
    for x0 in major_x:
        lo, hi = max(0, x0 - pad - 2), min(w, x0 + pad + 3)
        if hi > lo:
            mask[:, lo:hi] = False
    if color == "gray":
        # Avoid horizontal grid lines for all panels.
        if cal.y_scale == "log10":
            y_ticks = [10 ** e for e in range(math.floor(math.log10(cal.y_min)), math.ceil(math.log10(cal.y_max)) + 1)]
            y_ticks = [y for y in y_ticks if cal.y_min <= y <= cal.y_max]
            rows = [int(round((bottom - top) * (1 - (math.log10(y) - math.log10(cal.y_min)) / (math.log10(cal.y_max) - math.log10(cal.y_min))))) for y in y_ticks]
        else:
            y_ticks = np.linspace(cal.y_min, cal.y_max, 5)
            rows = [int(round((bottom - top) * (1 - (y - cal.y_min) / (cal.y_max - cal.y_min)))) for y in y_ticks]
        for y0 in rows:
            lo, hi = max(0, y0 - pad - 2), min(h, y0 + pad + 3)
            if hi > lo:
                mask[lo:hi, :] = False

    xs = np.linspace(0, w - 1, n_samples).round().astype(int)
    # The neutral gray curve shares the panel with a gray legend at the left;
    # track it from right to left, where the curve is isolated, then reverse.
    if color == "gray":
        xs = xs[::-1]
    raw_points: list[tuple[int, float, int]] = []
    last_y: float | None = None
    for xi in xs:
        lo, hi = max(0, xi - 2), min(w, xi + 3)
        ys = np.where(mask[:, lo:hi])[0]
        if ys.size == 0:
            continue
        if color == "gray" and last_y is not None:
            y = float(ys[np.argmin(np.abs(ys - last_y))])
        else:
            y = float(np.median(ys))
        # Reject obvious text/legend outliers by requiring a smooth curve.
        if last_y is not None and abs(y - last_y) > max(16, h * 0.08):
            close = ys[np.abs(ys - last_y) <= max(16, h * 0.08)]
            if close.size:
                y = float(np.median(close))
            elif color == "gray":
                continue
        last_y = y
        raw_points.append((xi, y, int(ys.size)))

    if color == "gray":
        raw_points = list(reversed(raw_points))

    rows: list[dict[str, object]] = []
    for i, (xi, y, candidates) in enumerate(raw_points):
        x_px = left + pad + xi
        y_px = top + pad + y
        rows.append(
            {
                "panel": cal.panel,
                "value_name": cal.value_name,
                "value_unit": cal.value_unit,
                "T_K": TEMPERATURES[color]["T_K"],
                "curve_color": color,
                "w_m_s": cal.x_to_w(x_px),
                "value": cal.y_to_value(y_px),
                "x_px_page": round(x_px, 3),
                "y_px_page": round(y_px, 3),
                "x_px_panel": round(x_px - left, 3),
                "y_px_panel": round(y_px - top, 3),
                "candidate_pixels_in_column_window": candidates,
                "source_pdf": str(PDF.relative_to(ROOT)),
                "source_page": PAGE_NUMBER,
                "source_render_dpi": DPI,
                "source_image": str((OUT / "figure1_source.png").relative_to(ROOT)),
                "digitization_method": "color-threshold median-by-column with grid-pixel suppression",
                "point_index": i,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "panel",
        "value_name",
        "value_unit",
        "T_K",
        "curve_color",
        "w_m_s",
        "value",
        "x_px_page",
        "y_px_page",
        "x_px_panel",
        "y_px_panel",
        "candidate_pixels_in_column_window",
        "source_pdf",
        "source_page",
        "source_render_dpi",
        "source_image",
        "digitization_method",
        "point_index",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def draw_overlay(page_image: Image.Image, rows: list[dict[str, object]], cals: dict[str, PanelCalibration]) -> Image.Image:
    overlay = page_image.copy()
    draw = ImageDraw.Draw(overlay)
    for cal in cals.values():
        draw.rectangle(cal.bounds_px, outline=(0, 160, 0), width=max(2, int(DPI / 150)))
    radius = max(2, int(DPI / 200))
    for row in rows:
        x = float(row["x_px_page"])
        y = float(row["y_px_page"])
        rgb = TEMPERATURES[str(row["curve_color"])] ["rgb"]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=rgb, fill=rgb)
    return overlay


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rendered_page = OUT / f"figure1_page{PAGE_NUMBER}_{DPI}dpi.png"
    figure_source = OUT / "figure1_source.png"
    image_list = OUT / "pdfimages_list.txt"

    render_page(PDF, rendered_page)
    image_list.write_text(list_pdf_images(PDF))

    page = Image.open(rendered_page).convert("RGB")
    scale = DPI / BASE_DPI
    crop = scale_box(BASE_FIGURE_CROP, scale)
    page.crop(crop).save(figure_source)

    cals = calibrations(scale)
    arr = np.array(page)
    rows: list[dict[str, object]] = []
    for cal in cals.values():
        for color in ("blue", "gray", "red"):
            rows.extend(digitize_curve(arr, cal, color))

    csv_path = OUT / "figure1_digitized_curves.csv"
    write_csv(csv_path, rows)

    overlay_page = draw_overlay(page, rows, cals)
    overlay_page.save(OUT / "figure1_digitized_overlay_page.png")
    overlay_page.crop(crop).save(OUT / "figure1_digitized_overlay.png")

    counts: dict[str, int] = {}
    for row in rows:
        key = f"{row['panel']}|T={row['T_K']}"
        counts[key] = counts.get(key, 0) + 1

    metadata = {
        "figure": "Figure 1",
        "paper": "Bergner & Spichtinger (2026), Ice clouds as nonlinear oscillators",
        "source_pdf": str(PDF.relative_to(ROOT)),
        "source_pdf_sha256": sha256(PDF),
        "source_page": PAGE_NUMBER,
        "rendering": {
            "tool": "pdftoppm",
            "dpi": DPI,
            "rendered_page": str(rendered_page.relative_to(ROOT)),
            "figure_source_image": str(figure_source.relative_to(ROOT)),
            "note": "pdfimages list shows no embedded Figure 1 raster; high-resolution source image is a reproducible 600-dpi render/crop from the saved PDF page.",
        },
        "calibration": {
            "coordinate_system": "page-render pixels, origin at upper-left",
            "figure_crop_px": crop,
            "panels": {
                name: {
                    "bounds_px": cal.bounds_px,
                    "x_axis": {"name": "vertical_velocity", "unit": "m s-1", "scale": cal.x_scale, "min": cal.x_min, "max": cal.x_max},
                    "y_axis": {"name": cal.value_name, "unit": cal.value_unit, "scale": cal.y_scale, "min": cal.y_min, "max": cal.y_max},
                }
                for name, cal in cals.items()
            },
        },
        "digitization": {
            "curve_temperatures": {color: info["T_K"] for color, info in TEMPERATURES.items()},
            "method": "color thresholding followed by per-column robust median extraction; grid lines suppressed before neutral gray extraction",
            "csv": str(csv_path.relative_to(ROOT)),
            "overlay": str((OUT / "figure1_digitized_overlay.png").relative_to(ROOT)),
            "point_counts": counts,
            "quality_note": "Overlay artifact is the primary QA check. Gray T=210 curves are lower confidence because they are neutral and close to dotted grid/fit strokes.",
        },
    }
    (OUT / "figure1_digitization_metadata.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False))
    (OUT / "figure1_digitization_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Wrote {len(rows)} digitized points to {csv_path}")
    print(f"Wrote metadata and overlays under {OUT}")


if __name__ == "__main__":
    main()
