# process.py
# Step 2 — Image processing pipeline.
# Sub-steps: distortion correction → crop → scale detection → silhouette extraction.
# Requires: OpenCV (pip install opencv-python), NumPy (pip install numpy)

import cv2
import numpy as np

import config


# ---------------------------------------------------------------------------
# 2a: Distortion correction
# ---------------------------------------------------------------------------

def undistort(image: np.ndarray) -> np.ndarray:
    """Apply lens distortion correction using calibration values from config.

    Args:
        image: Raw captured image as a NumPy array (BGR or RGB, HxWxC).

    Returns:
        Undistorted image array (same shape).
    """
    h, w = image.shape[:2]
    new_matrix, roi = cv2.getOptimalNewCameraMatrix(
        config.CAMERA_MATRIX,
        config.DISTORTION_COEFFICIENTS,
        (w, h),
        alpha=1,
    )
    undistorted = cv2.undistort(
        image,
        config.CAMERA_MATRIX,
        config.DISTORTION_COEFFICIENTS,
        None,
        new_matrix,
    )
    return undistorted


# ---------------------------------------------------------------------------
# 2b: Crop
# ---------------------------------------------------------------------------

def crop(image: np.ndarray) -> np.ndarray:
    """Remove edge artifacts introduced by the undistort step.

    Uses CROP_BOUNDS from config: (x, y, width, height).

    Args:
        image: Undistorted image array.

    Returns:
        Cropped image array.
    """
    x, y, w, h = config.CROP_BOUNDS
    cropped = image[y : y + h, x : x + w]
    return cropped


# ---------------------------------------------------------------------------
# 2c: Scale detection
# ---------------------------------------------------------------------------

def detect_scale(image: np.ndarray) -> float:
    """Detect the ruler printed on the light board and return pixels-per-mm.

    The function isolates the RULER_REGION, finds the ruler's pixel span using
    edge detection, and divides by RULER_MM_LENGTH to get the scale factor.

    Args:
        image: Cropped (but not yet thresholded) image array.

    Returns:
        pixels_per_mm (float). Raises RuntimeError if ruler not detected.
    """
    x, y, w, h = config.RULER_REGION
    roi = image[y : y + h, x : x + w]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # Project edge map horizontally to find leftmost and rightmost edge column.
    col_sums = np.sum(edges, axis=0)
    nonzero_cols = np.nonzero(col_sums)[0]

    if len(nonzero_cols) < 2:
        raise RuntimeError(
            "Ruler not detected in RULER_REGION. "
            "Check RULER_REGION bounds and lighting."
        )

    ruler_pixel_span = float(nonzero_cols[-1] - nonzero_cols[0])
    pixels_per_mm = ruler_pixel_span / config.RULER_MM_LENGTH

    print(f"[process] Scale detected: {pixels_per_mm:.4f} px/mm "
          f"(span={ruler_pixel_span:.1f}px over {config.RULER_MM_LENGTH}mm)")
    return pixels_per_mm


# ---------------------------------------------------------------------------
# 2d: Silhouette extraction
# ---------------------------------------------------------------------------

def extract_silhouette(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Threshold and extract the dominant tool contour as a clean binary mask.

    Steps:
      1. Convert to grayscale.
      2. Detect scale from the ruler region.
      3. Apply binary threshold (tool=black on lit background=white → invert
         so tool pixels become white in the mask).
      4. Select the largest contour above CONTOUR_MIN_AREA.
      5. Draw a filled contour onto a clean binary bitmap.

    Args:
        image: Cropped, undistorted image array (BGR).

    Returns:
        Tuple of:
          - binary_mask: uint8 array, tool pixels = 255, background = 0
          - largest_contour: the raw OpenCV contour (Nx1x2 array)
          - pixels_per_mm: scale factor for downstream use
    """
    pixels_per_mm = detect_scale(image)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Invert: light board background is bright, tool is dark.
    # After threshold+invert, tool pixels are white (255).
    _, thresh = cv2.threshold(
        gray, config.THRESHOLD_VALUE, 255, cv2.THRESH_BINARY_INV
    )

    # Morphological closing fills small holes inside the tool outline.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        raise RuntimeError("No contours found. Check threshold and lighting.")

    # Filter by minimum area, then pick the largest.
    valid = [c for c in contours if cv2.contourArea(c) >= config.CONTOUR_MIN_AREA]
    if not valid:
        raise RuntimeError(
            f"No contour above CONTOUR_MIN_AREA={config.CONTOUR_MIN_AREA}. "
            "Lower the threshold or adjust CONTOUR_MIN_AREA."
        )

    largest = max(valid, key=cv2.contourArea)

    # Draw the selected contour onto a clean black canvas.
    binary_mask = np.zeros_like(gray, dtype=np.uint8)
    cv2.drawContours(binary_mask, [largest], -1, 255, thickness=cv2.FILLED)

    print(f"[process] Tool contour area: {cv2.contourArea(largest):.0f} px²")
    return binary_mask, largest, pixels_per_mm


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def process_image(image_path: str) -> tuple[np.ndarray, float]:
    """Run the full Step 2 pipeline on an image file.

    Args:
        image_path: Path to the input JPEG.

    Returns:
        Tuple of (binary_mask, pixels_per_mm).
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    image = undistort(image)
    image = crop(image)
    binary_mask, _, pixels_per_mm = extract_silhouette(image)

    return binary_mask, pixels_per_mm


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python process.py <image_path>")
        sys.exit(1)

    mask, scale = process_image(sys.argv[1])
    cv2.imwrite("debug_mask.png", mask)
    print(f"Mask saved to debug_mask.png  |  scale={scale:.4f} px/mm")
