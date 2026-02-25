# vectorize.py
# Step 3 — Convert binary bitmap silhouette to a smooth vector path.
#
# Requires:
#   pypotrace  (pip install pypotrace)
#   Potrace C library must be installed first:
#     sudo apt install potrace libpotrace-dev
#
# pypotrace GitHub: https://github.com/flupke/pypotrace
# Import name is 'potrace' (not 'pypotrace').
#
# API reference (confirmed from pypotrace source):
#   potrace.Bitmap(bool_array).trace(**kwargs) -> Path
#   Path.curves        -> iterable of Curve objects
#   Curve.start_point  -> (x, y) tuple  [pixel coordinates]
#   Curve.segments     -> iterable of Segment objects
#   Segment.is_corner  -> bool (True = corner/line, False = cubic bezier)
#   Segment.c          -> tuple of (x,y) control points
#                         corner:  c[0] = corner vertex
#                         bezier:  c[0] = CP1, c[1] = CP2
#   Segment.end_point  -> (x, y) tuple [endpoint of this segment]
#
# Coordinates are returned in PIXEL space. Scale to mm is applied in export.py.

import potrace
import numpy as np


def bitmap_to_paths(binary_mask: np.ndarray) -> potrace.Path:
    """Trace a binary silhouette mask into smooth Bézier curves.

    Returns a Potrace Path object whose coordinates are in pixel space.
    The scale conversion (pixels → mm) is applied in export.py so that
    the SVG viewBox and path data are all in millimetres.

    Args:
        binary_mask: uint8 array from process.extract_silhouette().
                     Tool pixels = 255, background = 0.

    Returns:
        potrace.Path with curve data in pixel coordinates.
    """
    # pypotrace expects a 2D boolean numpy array (True = ink/tool pixel).
    bool_bitmap = binary_mask > 127

    bm = potrace.Bitmap(bool_bitmap)

    # Trace parameters:
    #   turdsize    — suppress speckles smaller than this many pixels²
    #   turnpolicy  — how to resolve ambiguous turns (MINORITY is the potrace default)
    #   alphamax    — corner vs curve threshold: 0.0 = all sharp corners,
    #                 1.0 = round corners, 1.33 = all curves
    #   opttolerance — curve optimisation tolerance (lower = more faithful to bitmap)
    path = bm.trace(
        turdsize=2,
        turnpolicy=potrace.TURNPOLICY_MINORITY,
        alphamax=1.0,
        opttolerance=0.2,
    )

    curve_count = sum(1 for _ in path.curves)
    print(f"[vectorize] Traced {curve_count} curve(s) in pixel space")
    return path


if __name__ == "__main__":
    # Standalone test: load debug_mask.png written by process.py
    import sys
    import cv2

    mask_path = sys.argv[1] if len(sys.argv) > 1 else "debug_mask.png"

    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"Could not load {mask_path}")
        sys.exit(1)

    path = bitmap_to_paths(mask)

    # Print first curve's segments to verify API is working.
    for i, curve in enumerate(path.curves):
        print(f"Curve {i}: start={curve.start_point}")
        for j, seg in enumerate(curve.segments):
            if seg.is_corner:
                print(f"  Seg {j}: CORNER  c[0]={seg.c[0]}  end={seg.end_point}")
            else:
                print(f"  Seg {j}: BEZIER  c[0]={seg.c[0]}  c[1]={seg.c[1]}  end={seg.end_point}")
        if i >= 2:
            print("  (truncated...)")
            break

    print("Vectorization OK")
