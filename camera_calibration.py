# camera_calibration.py
# One-time camera calibration using a printed checkerboard pattern.
#
# Steps:
#   1. Print a checkerboard (e.g. 9x6 inner corners) and tape it flat.
#   2. Photograph it ~15–20 times from different angles using the Pi camera.
#      Save images to calibration_images/ (or supply a directory as argument).
#   3. Run: python camera_calibration.py
#   4. Copy the printed CAMERA_MATRIX and DISTORTION_COEFFICIENTS into config.py.
#
# Requires: OpenCV, NumPy (both already in the project stack)

import sys
import glob
import cv2
import numpy as np


# Checkerboard inner corner dimensions — match your printed pattern.
CHECKERBOARD = (9, 6)  # (columns, rows) of inner corners


def calibrate(images_dir: str = "calibration_images") -> None:
    pattern_size = CHECKERBOARD
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)

    obj_points = []  # 3D points in real world space
    img_points = []  # 2D points in image plane

    image_paths = glob.glob(f"{images_dir}/*.jpg") + glob.glob(f"{images_dir}/*.png")
    if not image_paths:
        print(f"No images found in {images_dir}/")
        print("Place checkerboard JPEG/PNG images there and re-run.")
        sys.exit(1)

    print(f"Found {len(image_paths)} calibration image(s).")
    image_size = None

    for path in sorted(image_paths):
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if image_size is None:
            image_size = (gray.shape[1], gray.shape[0])

        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners_refined)
            print(f"  OK: {path}")
        else:
            print(f"  SKIP (corners not found): {path}")

    if len(obj_points) < 5:
        print(f"\nNeed at least 5 usable images; only {len(obj_points)} found.")
        print("Photograph the checkerboard from more angles.")
        sys.exit(1)

    print(f"\nCalibrating with {len(obj_points)} images...")
    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, image_size, None, None
    )

    print(f"Reprojection error (RMS): {rms:.4f}  (< 0.5 is good)")
    print("\n--- Copy these values into config.py ---\n")
    print("CAMERA_MATRIX = np.array(")
    print(repr(camera_matrix.tolist()) + ", dtype=np.float64)")
    print("\nDISTORTION_COEFFICIENTS = np.array(")
    print(repr(dist_coeffs.flatten().tolist()) + ", dtype=np.float64)")


if __name__ == "__main__":
    images_dir = sys.argv[1] if len(sys.argv) > 1 else "calibration_images"
    calibrate(images_dir)
