# tests/test_process.py
# Unit tests for process.py — runs without the Pi camera.
# Drop JPEG test images into sample_images/ to exercise these tests.
#
# Run from the project root:
#   python -m pytest tests/test_process.py -v

import sys
import os
import numpy as np
import pytest

# Allow imports from the project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import config
import process


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_image(
    width: int = 800,
    height: int = 600,
    tool_rect: tuple = (200, 150, 400, 300),
) -> np.ndarray:
    """Create a synthetic light-board image: white background, black rectangle.

    Simulates a backlit board with a single rectangular tool shape.

    Args:
        width, height: Image dimensions.
        tool_rect: (x, y, w, h) of the dark tool rectangle.

    Returns:
        BGR image array.
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)  # white background
    x, y, w, h = tool_rect
    img[y : y + h, x : x + w] = 0  # black tool
    return img


def _patch_config_for_synthetic(monkeypatch, width=800, height=600):
    """Set config values suitable for the synthetic test image."""
    monkeypatch.setattr(config, "CROP_BOUNDS", (0, 0, width, height))
    # Ruler region: a 100-pixel wide stripe, simulated as fully black columns.
    monkeypatch.setattr(config, "RULER_REGION", (0, 0, 200, 20))
    monkeypatch.setattr(config, "RULER_MM_LENGTH", 100.0)
    monkeypatch.setattr(config, "THRESHOLD_VALUE", 127)
    monkeypatch.setattr(config, "CONTOUR_MIN_AREA", 100)


# ---------------------------------------------------------------------------
# crop()
# ---------------------------------------------------------------------------

class TestCrop:
    def test_crop_reduces_size(self, monkeypatch):
        monkeypatch.setattr(config, "CROP_BOUNDS", (10, 10, 200, 150))
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        result = process.crop(img)
        assert result.shape == (150, 200, 3)

    def test_crop_returns_correct_region(self, monkeypatch):
        monkeypatch.setattr(config, "CROP_BOUNDS", (0, 0, 50, 50))
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[0:50, 0:50] = 128
        result = process.crop(img)
        assert result.shape == (50, 50, 3)
        assert result[0, 0, 0] == 128


# ---------------------------------------------------------------------------
# detect_scale()
# ---------------------------------------------------------------------------

class TestDetectScale:
    def test_known_scale(self, monkeypatch):
        """Ruler drawn as two vertical black lines 100 px apart in a white image."""
        monkeypatch.setattr(config, "RULER_REGION", (0, 0, 200, 40))
        monkeypatch.setattr(config, "RULER_MM_LENGTH", 100.0)

        img = np.full((40, 200, 3), 255, dtype=np.uint8)
        # Draw two vertical lines at x=50 and x=150 — span of 100 pixels.
        img[:, 50] = 0
        img[:, 150] = 0

        scale = process.detect_scale(img)
        assert abs(scale - 1.0) < 0.05, f"Expected ~1.0 px/mm, got {scale}"

    def test_no_ruler_raises(self, monkeypatch):
        """All-white ruler region should raise RuntimeError."""
        monkeypatch.setattr(config, "RULER_REGION", (0, 0, 100, 20))
        monkeypatch.setattr(config, "RULER_MM_LENGTH", 100.0)

        img = np.full((20, 100, 3), 255, dtype=np.uint8)
        with pytest.raises(RuntimeError, match="Ruler not detected"):
            process.detect_scale(img)


# ---------------------------------------------------------------------------
# extract_silhouette()
# ---------------------------------------------------------------------------

class TestExtractSilhouette:
    def test_returns_binary_mask(self, monkeypatch):
        _patch_config_for_synthetic(monkeypatch)

        # Add ruler lines so detect_scale succeeds.
        img = _make_synthetic_image()
        img[0:20, 10] = 0
        img[0:20, 110] = 0  # 100 px apart → 1.0 px/mm

        mask, contour, ppm = process.extract_silhouette(img)

        assert mask.dtype == np.uint8
        assert set(np.unique(mask)).issubset({0, 255})

    def test_mask_covers_tool_region(self, monkeypatch):
        _patch_config_for_synthetic(monkeypatch)

        tool = (200, 150, 200, 150)
        img = _make_synthetic_image(tool_rect=tool)
        img[0:20, 10] = 0
        img[0:20, 110] = 0

        mask, _, _ = process.extract_silhouette(img)

        x, y, w, h = tool
        roi = mask[y : y + h, x : x + w]
        white_ratio = np.sum(roi == 255) / roi.size
        assert white_ratio > 0.8, f"Expected tool region mostly white, got {white_ratio:.2f}"

    def test_no_tool_raises(self, monkeypatch):
        _patch_config_for_synthetic(monkeypatch)
        monkeypatch.setattr(config, "CONTOUR_MIN_AREA", 100_000)  # unreachably large

        img = _make_synthetic_image()
        img[0:20, 10] = 0
        img[0:20, 110] = 0

        with pytest.raises(RuntimeError):
            process.extract_silhouette(img)


# ---------------------------------------------------------------------------
# process_image() — integration
# ---------------------------------------------------------------------------

class TestProcessImage:
    def test_with_real_sample(self, tmp_path, monkeypatch):
        """Write a synthetic image to disk and run the full Step 2 pipeline."""
        _patch_config_for_synthetic(monkeypatch)

        img = _make_synthetic_image()
        img[0:20, 10] = 0
        img[0:20, 110] = 0

        # Patch undistort to be a no-op (we have no real calibration data).
        monkeypatch.setattr(process, "undistort", lambda x: x)

        img_path = tmp_path / "test_tool.jpg"
        cv2.imwrite(str(img_path), img)

        mask, ppm = process.process_image(str(img_path))

        assert mask is not None
        assert ppm > 0
