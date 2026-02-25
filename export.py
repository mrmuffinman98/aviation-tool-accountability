# export.py
# Step 4 — Write a laser-cutter-ready SVG from scaled Potrace path data.
# Requires: svgwrite (pip install svgwrite)
#
# SVG coordinate conventions:
#   - 1 SVG user unit = 1 mm  (set via viewBox and width/height attributes)
#   - Origin (0,0) is top-left
#   - Potrace uses bottom-left origin so Y axis is flipped here

import os
import time
from pathlib import Path

import potrace
import svgwrite

import config


def paths_to_svg(
    path: potrace.Path,
    image_height_mm: float,
    output_filename: str | None = None,
) -> str:
    """Write an SVG file from a scaled Potrace path.

    Args:
        path: Scaled Potrace Path object (coordinates already in mm).
        image_height_mm: Height of the source image in mm. Required to flip
                         the Y axis from Potrace space (bottom-left origin)
                         to SVG space (top-left origin).
        output_filename: Desired SVG filename (basename only, or full path).
                         Defaults to a timestamped file in SVG_OUTPUT_PATH.

    Returns:
        Absolute path to the written SVG file.
    """
    if output_filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"tool_{timestamp}.svg"

    output_dir = Path(config.SVG_OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / Path(output_filename).name
    output_path = output_path.resolve()

    # Determine bounding box of all path data for the viewBox.
    all_x, all_y = [], []
    for curve in path.curves:
        all_x.append(curve.start_point.x)
        all_y.append(image_height_mm - curve.start_point.y)
        for seg in curve.segments:
            all_x.append(seg.end_point.x)
            all_y.append(image_height_mm - seg.end_point.y)

    if not all_x:
        raise ValueError("Path contains no segments — nothing to export.")

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    width_mm = max_x - min_x
    height_mm = max_y - min_y

    # SVG canvas sized exactly to the tool outline; 1 unit = 1 mm.
    dwg = svgwrite.Drawing(
        filename=str(output_path),
        size=(f"{width_mm}mm", f"{height_mm}mm"),
        viewBox=f"{min_x} {min_y} {width_mm} {height_mm}",
    )

    path_data = _build_svg_path_data(path, image_height_mm)

    dwg.add(
        dwg.path(
            d=path_data,
            fill="none",
            stroke="black",
            stroke_width=0.1,  # 0.1mm hairline — most laser cutters accept this
        )
    )

    dwg.save(pretty=True)
    print(f"[export] SVG saved: {output_path}  ({width_mm:.1f}mm × {height_mm:.1f}mm)")
    return str(output_path)


def _build_svg_path_data(path: potrace.Path, image_height_mm: float) -> str:
    """Convert Potrace path to an SVG path data string (d attribute).

    Potrace uses a bottom-left origin; SVG uses top-left. The Y coordinate
    is flipped by: svg_y = image_height_mm - potrace_y

    Args:
        path: Scaled Potrace Path (coordinates in mm).
        image_height_mm: Height of image in mm for Y-axis flip.

    Returns:
        SVG path data string.
    """
    def flip_y(y: float) -> float:
        return image_height_mm - y

    parts = []

    for curve in path.curves:
        sx = curve.start_point.x
        sy = flip_y(curve.start_point.y)
        parts.append(f"M {sx:.4f} {sy:.4f}")

        for seg in curve.segments:
            ex = seg.end_point.x
            ey = flip_y(seg.end_point.y)

            if seg.is_corner:
                cx = seg.c.x
                cy = flip_y(seg.c.y)
                parts.append(f"L {cx:.4f} {cy:.4f}")
                parts.append(f"L {ex:.4f} {ey:.4f}")
            else:
                c1x, c1y = seg.c1.x, flip_y(seg.c1.y)
                c2x, c2y = seg.c2.x, flip_y(seg.c2.y)
                parts.append(f"C {c1x:.4f} {c1y:.4f} {c2x:.4f} {c2y:.4f} {ex:.4f} {ey:.4f}")

        parts.append("Z")

    return " ".join(parts)


if __name__ == "__main__":
    print("export.py has no standalone demo (requires a Potrace path object).")
    print("Run main.py to exercise the full pipeline.")
