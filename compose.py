# compose.py
# Combines per-tool session SVGs into a single stacked SVG for laser cutting.
#
# Tools are placed vertically one after the next with a 2mm gap between them.
# The canvas is sized exactly to fit — no fixed board dimensions.
# Arrange and nest the output in your CAD/vector tool before cutting.

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import config

_SVG_NS = "http://www.w3.org/2000/svg"
_GAP_MM = 2.0


def _load_session_tools(session_dir: Path) -> list[dict]:
    files = sorted(session_dir.glob("tool_*.json"))
    tools = []
    for f in files:
        with open(f) as fh:
            tools.append(json.load(fh))
    return tools


def compose_shadowboard() -> str:
    """Stack all session tools vertically and write a single SVG.

    Returns:
        Absolute path to the saved SVG file.
    """
    session_dir = Path(config.SESSION_PATH)
    tools = _load_session_tools(session_dir)
    if not tools:
        raise ValueError("No tools in session. Capture at least one tool first.")

    canvas_w = max(t["width_mm"]  for t in tools)
    canvas_h = (
        sum(t["height_mm"] for t in tools)
        + _GAP_MM * (len(tools) - 1)
    )

    ET.register_namespace("", _SVG_NS)

    root = ET.Element(f"{{{_SVG_NS}}}svg")
    root.set("xmlns",   _SVG_NS)
    root.set("width",   f"{canvas_w}mm")
    root.set("height",  f"{canvas_h}mm")
    root.set("viewBox", f"0 0 {canvas_w} {canvas_h}")

    y = 0.0
    for tool in tools:
        tool_root = ET.fromstring(tool["svg_content"])
        viewbox = tool_root.get(
            "viewBox", f"0 0 {tool['width_mm']} {tool['height_mm']}"
        )

        nested = ET.SubElement(root, f"{{{_SVG_NS}}}svg")
        nested.set("x",       "0")
        nested.set("y",       f"{y:.4f}")
        nested.set("width",   f"{tool['width_mm']:.4f}")
        nested.set("height",  f"{tool['height_mm']:.4f}")
        nested.set("viewBox", viewbox)

        for child in list(tool_root):
            nested.append(child)

        y += tool["height_mm"] + _GAP_MM

    output_dir = Path(config.SVG_OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = (output_dir / f"shadowboard_{timestamp}.svg").resolve()

    ET.ElementTree(root).write(str(output_path), xml_declaration=True, encoding="unicode")

    print(
        f"[compose] Shadowboard SVG saved: {output_path}  "
        f"({len(tools)} tool(s), {canvas_w:.1f}×{canvas_h:.1f}mm)"
    )
    return str(output_path)
