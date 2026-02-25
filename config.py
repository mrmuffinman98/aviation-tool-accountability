# config.py
# All tunable parameters for the Aviation Tool Accountability System.
# Edit these values once during station setup. Do not scatter magic numbers
# through the pipeline modules — everything configurable lives here.

import numpy as np

# ---------------------------------------------------------------------------
# Camera calibration
# Generated once using cv2.calibrateCamera() with a checkerboard pattern.
# Replace the placeholder arrays below with your actual calibration output.
# ---------------------------------------------------------------------------

CAMERA_MATRIX = np.array([
    [1000.0,    0.0, 640.0],
    [   0.0, 1000.0, 480.0],
    [   0.0,    0.0,   1.0],
], dtype=np.float64)
# ^^^ PLACEHOLDER — run camera_calibration.py and paste real values here.

DISTORTION_COEFFICIENTS = np.array(
    [0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64
)
# ^^^ PLACEHOLDER — run camera_calibration.py and paste real values here.

# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

# Picamera2 capture resolution. Higher = more detail, slower processing.
# (4608, 2592) is the Pi Camera Module 3 native max; start with half for speed.
IMAGE_RESOLUTION = (2304, 1296)

# ---------------------------------------------------------------------------
# Crop
# Applied after undistortion to remove edge artifacts.
# Format: (x, y, width, height) in pixels at IMAGE_RESOLUTION scale.
# Measure these values after running undistortion on a test frame.
# ---------------------------------------------------------------------------

CROP_BOUNDS = (50, 50, 2200, 1196)  # PLACEHOLDER — tune after calibration

# ---------------------------------------------------------------------------
# Ruler / scale detection
# The ruler printed on the light board provides an automatic pixels-per-mm
# ratio on every capture. No manual scale entry required.
# ---------------------------------------------------------------------------

# Pixel region of the image (after crop) where the ruler sits.
# Format: (x, y, width, height). Place ruler toward frame centre to minimise
# residual distortion error.
RULER_REGION = (50, 1100, 500, 80)  # PLACEHOLDER — measure on your setup

# Known real-world length of the ruler segment being detected (millimetres).
RULER_MM_LENGTH = 100.0

# ---------------------------------------------------------------------------
# Silhouette extraction
# ---------------------------------------------------------------------------

# Binary threshold level. 0–255. Background (lit) → white; tool → black.
# Increase if tool pixels bleed into background; decrease if background
# pixels are captured as tool.
THRESHOLD_VALUE = 127

# Minimum contour area (pixels²) to be considered a tool.
# Eliminates dust, reflections, and small noise contours.
CONTOUR_MIN_AREA = 5000

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

SVG_OUTPUT_PATH = "output"
