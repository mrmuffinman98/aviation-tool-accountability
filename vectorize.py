# vectorize.py
# Step 3 — Convert binary bitmap silhouette to a smooth vector path.
# Requires: pypotrace (pip install pypotrace)
#           Potrace C library must be installed first:
#             sudo apt install potrace libpotrace-dev

import potrace
import numpy as np


def bitmap_to_paths(
    binary_mask: np.ndarray, pixels_per_mm: float
) -> list[potrace.Path]:
    """Trace the binary mask into Bézier curve paths scaled to millimetres.

    Potrace works on a boolean bitmap where True = ink (tool), False = paper
    (background). The returned paths are already scaled so that coordinate
    units equal millimetres.

    Args:
        binary_mask: uint8 array from process.extract_silhouette(),
                     tool pixels = 255, background = 0.
        pixels_per_mm: scale factor from process.detect_scale().

    Returns:
        List of potrace.Path objects. Typically one path for a single tool.
    """
    # pypotrace expects a boolean numpy array.
    bool_bitmap = binary_mask > 127

    bmp = potrace.Bitmap(bool_bitmap)

    # turdsize: suppress speckles smaller than this many pixels²
    # alphamax: corner detection threshold (0.0 = sharp corners, 1.33 = round)
    # opttolerance: curve optimisation tolerance
    path = bmp.trace(
        turdsize=2,
        turnpolicy=potrace.TURNPOLICY_MINORITY,
        alphamax=1.0,
        opttolerance=0.2,
    )

    # Scale the path coordinates from pixels to millimetres.
    scaled_paths = _scale_paths(path, pixels_per_mm)

    print(f"[vectorize] Traced {len(list(path.curves))} curve(s)")
    return scaled_paths


def _scale_paths(path: potrace.Path, pixels_per_mm: float) -> potrace.Path:
    """Scale all control points in a Potrace path from pixels to mm.

    Potrace paths are mutable; we modify the coordinates in place and return
    the same path object.

    Note: Potrace coordinate origin is bottom-left. svgwrite uses top-left.
    The Y-axis flip is handled in export.py, not here, so coordinates here
    remain in Potrace space (scaled to mm, Y increasing upward).
    """
    scale = 1.0 / pixels_per_mm

    for curve in path.curves:
        for segment in curve.segments:
            if segment.is_corner:
                segment.c.x *= scale
                segment.c.y *= scale
                segment.end_point.x *= scale
                segment.end_point.y *= scale
            else:
                segment.c1.x *= scale
                segment.c1.y *= scale
                segment.c2.x *= scale
                segment.c2.y *= scale
                segment.end_point.x *= scale
                segment.end_point.y *= scale
        # Scale the curve start point.
        curve.start_point.x *= scale
        curve.start_point.y *= scale

    return path


if __name__ == "__main__":
    # Standalone test: load debug_mask.png written by process.py
    import sys
    import cv2

    mask_path = sys.argv[1] if len(sys.argv) > 1 else "debug_mask.png"
    pixels_per_mm = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"Could not load {mask_path}")
        sys.exit(1)

    paths = bitmap_to_paths(mask, pixels_per_mm)
    print("Vectorization OK")
