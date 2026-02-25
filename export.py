# export.py
# Step 4 — Write a laser-cutter-ready SVG from Potrace path data.
#
# Requires: svgwrite (pip install svgwrite)
#           svgwrite GitHub: https://github.com/mozman/svgwrite
#
# SVG output conventions:
#   - 1 SVG user unit = 1 mm  (enforced via width/height in mm + viewBox)
#   - Origin (0,0) is top-left
#   - Potrace uses bottom-left origin → Y axis is flipped here
#   - Scale applied here: pixel coordinates → mm using pixels_per_mm

import time
from pathlib import Path

import potrace
import svgwrite

import config


def paths_to_svg(
    path: potrace.Path,
    pixels_per_mm: float,
    mask_height_px: int,
    output_filename: str | None = None,
) -> str:
    """Write an SVG file from a Potrace path, applying scale and Y-axis flip.

    The path coordinates from vectorize.py are in pixel space. This function
    converts them to mm (divide by pixels_per_mm) and flips the Y axis
    (Potrace origin is bottom-left; SVG origin is top-left).

    Args:
        path: Potrace Path object from vectorize.bitmap_to_paths().
              Coordinates are in pixel space.
        pixels_per_mm: Scale factor from process.detect_scale().
        mask_height_px: Height of the binary mask in pixels. Required for
                        the Y-axis flip: svg_y = mask_height_px - potrace_y
        output_filename: Desired SVG filename. Defaults to a timestamped
                         file in SVG_OUTPUT_PATH from config.

    Returns:
        Absolute path to the written SVG file.
    """
    if output_filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_filename = f"tool_{timestamp}.svg"

    output_dir = Path(config.SVG_OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (output_dir / Path(output_filename).name).resolve()

    def px_to_mm(px_val: float) -> float:
        return px_val / pixels_per_mm

    def flip_y(y_px: float) -> float:
        """Convert Potrace Y (bottom-left origin) to SVG Y (top-left origin)."""
        return px_to_mm(mask_height_px - y_px)

    # Build all path data and collect bounding box in mm.
    all_path_data = _build_all_svg_path_data(path, px_to_mm, flip_y)

    if not all_path_data:
        raise ValueError("Path contains no segments — nothing to export.")

    # Determine canvas size from bounding box of all coordinates.
    min_x, max_x, min_y, max_y = _bounding_box(path, px_to_mm, flip_y)
    width_mm  = max_x - min_x
    height_mm = max_y - min_y

    # SVG canvas sized to the tool outline. 1 unit = 1 mm.
    dwg = svgwrite.Drawing(
        filename=str(output_path),
        size=(f"{width_mm:.4f}mm", f"{height_mm:.4f}mm"),
        viewBox=f"{min_x:.4f} {min_y:.4f} {width_mm:.4f} {height_mm:.4f}",
    )

    for path_data in all_path_data:
        dwg.add(
            dwg.path(
                d=path_data,
                fill="none",
                stroke="black",
                stroke_width=0.1,   # 0.1mm hairline — standard laser cutter cut line
            )
        )

    dwg.save(pretty=True)
    print(
        f"[export] SVG saved: {output_path}  "
        f"({width_mm:.1f}mm × {height_mm:.1f}mm)"
    )
    return str(output_path)


def _build_all_svg_path_data(path, px_to_mm, flip_y) -> list[str]:
    """Build SVG path data strings for every curve in the Potrace path.

    Uses the verified pypotrace API:
      curve.start_point          -> (x, y) tuple
      segment.is_corner          -> bool
      segment.c[0]               -> corner vertex OR bezier CP1  (x, y) tuple
      segment.c[1]               -> bezier CP2  (x, y) tuple  (bezier only)
      segment.end_point          -> (x, y) tuple

    Args:
        path: potrace.Path object (pixel coordinates).
        px_to_mm: callable, converts a pixel value to mm.
        flip_y: callable, converts Potrace Y (bottom-left) to SVG Y (top-left).

    Returns:
        List of SVG path data strings, one per closed curve.
    """
    result = []

    for curve in path.curves:
        sx, sy = curve.start_point
        parts = [f"M {px_to_mm(sx):.4f},{flip_y(sy):.4f}"]

        for seg in curve.segments:
            ex, ey = seg.end_point

            if seg.is_corner:
                # Corner segment: line to corner vertex, then line to endpoint.
                cx, cy = seg.c[0]
                parts.append(f"L {px_to_mm(cx):.4f},{flip_y(cy):.4f}")
                parts.append(f"L {px_to_mm(ex):.4f},{flip_y(ey):.4f}")
            else:
                # Cubic bezier: two control points then endpoint.
                c1x, c1y = seg.c[0]
                c2x, c2y = seg.c[1]
                parts.append(
                    f"C {px_to_mm(c1x):.4f},{flip_y(c1y):.4f} "
                    f"{px_to_mm(c2x):.4f},{flip_y(c2y):.4f} "
                    f"{px_to_mm(ex):.4f},{flip_y(ey):.4f}"
                )

        parts.append("Z")
        result.append(" ".join(parts))

    return result


def _bounding_box(path, px_to_mm, flip_y) -> tuple[float, float, float, float]:
    """Return (min_x, max_x, min_y, max_y) in mm across all path coordinates."""
    xs, ys = [], []

    def add(pt):
        xs.append(px_to_mm(pt[0]))
        ys.append(flip_y(pt[1]))

    for curve in path.curves:
        add(curve.start_point)
        for seg in curve.segments:
            add(seg.end_point)
            add(seg.c[0])
            if not seg.is_corner:
                add(seg.c[1])

    if not xs:
        return 0.0, 1.0, 0.0, 1.0

    return min(xs), max(xs), min(ys), max(ys)


if __name__ == "__main__":
    print("export.py has no standalone demo (requires a Potrace path object).")
    print("Run: python main.py --image sample_images/your_tool.jpg")
