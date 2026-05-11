# main.py
# Entry point — orchestrates the full pipeline with multi-tool session support.
#
# Capture one tool at a time, then combine into a single shadowboard SVG.
#
# Usage (on Raspberry Pi with camera):
#   python main.py                  # capture a tool and add it to the session
#   python main.py --finish         # combine all session tools into shadowboard SVG
#   python main.py --list           # show tools currently in the session
#   python main.py --clear          # wipe the session and start over
#
# Usage (development, supply a pre-taken image):
#   python main.py --image sample_images/wrench.jpg

import argparse
import json
import shutil
import sys
from pathlib import Path

import process
import vectorize
import export
import config


def run_pipeline(image_path: str | None = None) -> None:
    """Capture and process one tool, saving it to the session."""
    # -----------------------------------------------------------------
    # Step 1: Capture
    # -----------------------------------------------------------------
    if image_path is None:
        try:
            from capture import capture_image
        except ImportError:
            print(
                "[main] ERROR: Picamera2 not available. "
                "Supply --image to use a pre-taken photo.",
                file=sys.stderr,
            )
            sys.exit(1)
        print("[main] Step 1: Capturing image...")
        image_path = capture_image()
    else:
        print(f"[main] Step 1: Using supplied image: {image_path}")

    # -----------------------------------------------------------------
    # Step 2: Image processing
    # -----------------------------------------------------------------
    print("[main] Step 2: Processing image...")
    binary_mask, pixels_per_mm = process.process_image(image_path)

    # -----------------------------------------------------------------
    # Step 3: Vectorize
    # -----------------------------------------------------------------
    print("[main] Step 3: Vectorizing silhouette...")
    svg_content = vectorize.bitmap_to_svg_string(binary_mask)

    # -----------------------------------------------------------------
    # Step 4: Save to session
    # -----------------------------------------------------------------
    print("[main] Step 4: Saving tool to session...")
    export.svg_to_session(svg_content, pixels_per_mm)

    session_dir = Path(config.SESSION_PATH)
    count = len(list(session_dir.glob("tool_*.json")))
    print(f"\n[main] Tool added. Session total: {count} tool(s).")
    print("       Run again to capture another tool.")
    print("       Run with --finish when ready to build the full shadowboard SVG.")


def finish_session() -> None:
    """Combine all session tools into a single shadowboard SVG."""
    import compose
    print("[main] Building shadowboard from session tools...")
    try:
        svg_path = compose.compose_shadowboard()
    except ValueError as exc:
        print(f"[main] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"\n[main] Done. Shadowboard SVG ready for laser cutter: {svg_path}")


def list_session() -> None:
    """Print the tools currently in the session."""
    session_dir = Path(config.SESSION_PATH)
    files = sorted(session_dir.glob("tool_*.json"))
    if not files:
        print("[main] Session is empty. Run without flags to capture a tool.")
        return
    print(f"[main] Session contains {len(files)} tool(s):")
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        print(f"  Tool {data['index']:>2}:  {data['width_mm']:.1f} mm × {data['height_mm']:.1f} mm")


def clear_session() -> None:
    """Delete all tools from the current session."""
    session_dir = Path(config.SESSION_PATH)
    if session_dir.exists():
        shutil.rmtree(session_dir)
        print("[main] Session cleared.")
    else:
        print("[main] Session is already empty.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aviation Tool Accountability System — shadow board SVG generator"
    )
    parser.add_argument(
        "--image",
        metavar="PATH",
        default=None,
        help="Path to a pre-captured image (skips camera capture). "
             "Use this for development without the Pi camera.",
    )
    parser.add_argument(
        "--finish",
        action="store_true",
        help="Combine all session tools into a single shadowboard SVG.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the tools currently in the session.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all tools from the session and start over.",
    )
    args = parser.parse_args()

    if args.finish:
        finish_session()
    elif args.list:
        list_session()
    elif args.clear:
        clear_session()
    else:
        run_pipeline(image_path=args.image)


if __name__ == "__main__":
    main()
