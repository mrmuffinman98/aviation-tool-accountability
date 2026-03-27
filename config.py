# config.py
# All tunable parameters for the Aviation Tool Accountability System.
# Edit these values once during station setup. Do not scatter magic numbers
# through the pipeline modules — everything configurable lives here.

import numpy as np

# ---------------------------------------------------------------------------
# Camera calibration
# Generated once using cv2.calibrateCamera() with a checkerboard pattern.
# Replace the placeholder arrays below with your actual calibration output.
# Run: python camera_calibration.py
# ---------------------------------------------------------------------------

CAMERA_MATRIX = np.array([
    [2757.3684438599776, 0.0,                1156.2323363492503],
    [0.0,                2773.1375227967383,  775.4384227198979],
    [0.0,                0.0,                   1.0            ],
], dtype=np.float64)

DISTORTION_COEFFICIENTS = np.array(
    [0.019202280771496893, 0.6745707789527429, 0.014252213359000484,
     0.0015007128671278341, -3.565156939628043], dtype=np.float64
)

# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

# Picamera2 capture resolution. Higher = more detail, slower processing.
# Pi Camera Module 3 native max is (4608, 2592). Start at half for speed.
IMAGE_RESOLUTION = (2304, 1296)

# Manual focus position for the top-down rig (Pi Camera Module 3 only).
# LensPosition: 0.0 = infinity, higher values = closer subject.
# Typical values for top-down setups:
#   ~5.0  = ~30 cm working distance
#   ~8.0  = ~20 cm working distance
#   ~12.0 = ~15 cm working distance
# Tune by capturing a test image and checking sharpness.
LENS_POSITION = 8.0

# ---------------------------------------------------------------------------
# Crop
# Applied after undistortion to remove edge artifacts.
# Format: (x, y, width, height) in pixels at IMAGE_RESOLUTION scale.
# Measure these values after running undistortion on a test frame.
# ---------------------------------------------------------------------------

CROP_BOUNDS = (0, 0, 2304, 1296)  # Full frame — no cropping

# ---------------------------------------------------------------------------
# ArUco scale detection
# Replace the ruler with a printed ArUco marker of known physical size.
# Tape the marker flat on the light board surface in view of the camera.
#
# To generate and print a marker: python generate_aruco_marker.py
# Use a ruler to verify the printout dimensions match ARUCO_MARKER_SIZE_MM
# before using the system.
# ---------------------------------------------------------------------------

# ArUco dictionary to use. DICT_4X4_50 is fastest to detect and lowest
# false-positive rate — sufficient for a single reference marker.
# Must match what was used in generate_aruco_marker.py.
ARUCO_DICT_NAME = "DICT_4X4_50"

# Which marker ID to expect in the frame (0–49 for DICT_4X4_50).
ARUCO_MARKER_ID = 0

# Physical side length of the printed ArUco marker in millimetres.
# Measure the actual printout with a ruler and set this accurately —
# any error here propagates directly to every SVG dimension.
ARUCO_MARKER_SIZE_MM = 50.0

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

SVG_OUTPUT_PATH = "/home/tomas/Desktop/captures"
