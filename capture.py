# capture.py
# Step 1 — Capture a high-resolution image of the tool on the light board.
# Requires: Picamera2 (sudo apt install python3-picamera2)
# Only runs on a Raspberry Pi with the camera module connected via CSI.

import time
from pathlib import Path
from picamera2 import Picamera2

import config


def capture_image(output_path: str | None = None) -> str:
    """Capture one frame from the Pi camera and save it to disk.

    Args:
        output_path: Where to save the JPEG. Defaults to a timestamped file
                     in the current directory.

    Returns:
        Absolute path to the saved image file.
    """
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"capture_{timestamp}.jpg"

    output_path = str(Path(output_path).resolve())

    cam = Picamera2()
    still_config = cam.create_still_configuration(
        main={"size": config.IMAGE_RESOLUTION, "format": "RGB888"}
    )
    cam.configure(still_config)
    cam.start()

    # Brief warm-up so auto-exposure settles before capture.
    time.sleep(2)

    cam.capture_file(output_path)
    cam.stop()
    cam.close()

    print(f"[capture] Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick standalone test — run on the Pi to verify camera is working.
    path = capture_image()
    print(f"Capture complete: {path}")
