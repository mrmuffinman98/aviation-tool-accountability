# compose.py
# Combines per-tool session SVGs into a single shadowboard SVG for laser cutting.
#
# The outer SVG uses mm as its coordinate unit (1 viewBox unit = 1mm) sized to
# BOARD_WIDTH_MM × BOARD_HEIGHT_MM. Each tool is a nested <svg> element with its
# own pixel-space viewBox, positioned using a shelf-packing layout.

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import config

_SVG_NS = "http://www.w3.org/2000/svg"


def _load_session_tools(session_dir: Path) -> list[dict]:
    files = sorted(session_dir.glob("tool_*.json"))
    tools = []
    for f in files:
        with open(f) as fh:
            tools.append(json.load(fh))
    return tools


def _shelf_layout(
    tools: list[dict],
    board_w: float,
    board_h: float,
    padding: float,
) -> list[tuple[float, float]]:
    """Assign (x, y) mm positions using a left-to-right shelf packing algorithm."""
    positions = []
    cursor_x = padding
    cursor_y = padding
    row_height = 0.0

    for i, tool in enumerate(tools):
        if cursor_x + tool["width_mm"] > board_w - padding:
            cursor_x = padding
            cursor_y += row_height
            row_height = 0.0

        if cursor_y + tool["height_mm"] > board_h - padding:
            raise ValueError(
                f"Tool {i + 1} ({tool['width_mm']:.1f}×{tool['height_mm']:.1f}mm) "
                f"does not fit on the board ({board_w}×{board_h}mm). "
                "Increase BOARD_WIDTH_MM / BOARD_HEIGHT_MM in config.py or capture fewer tools."
            )

        positions.append((cursor_x, cursor_y))
        cursor_x += tool["width_mm"] + padding
        row_height = max(row_height, tool["height_mm"] + padding)

    return positions


def compose_shadowboard() -> str:
    """Load all session tools and write a single combined shadowboard SVG.

    Returns:
        Absolute path to the saved SVG file.
    """
    session_dir = Path(config.SESSION_PATH)
    tools = _load_session_tools(session_dir)
    if not tools:
        raise ValueError("No tools in session. Capture at least one tool first.")

    board_w = config.BOARD_WIDTH_MM
    board_h = config.BOARD_HEIGHT_MM
    padding = config.TOOL_PADDING_MM

    positions = _shelf_layout(tools, board_w, board_h, padding)

    ET.register_namespace("", _SVG_NS)

    root = ET.Element(f"{{{_SVG_NS}}}svg")
    root.set("xmlns", _SVG_NS)
    root.set("width",   f"{board_w}mm")
    root.set("height",  f"{board_h}mm")
    root.set("viewBox", f"0 0 {board_w} {board_h}")

    for tool, (x, y) in zip(tools, positions):
        tool_root = ET.fromstring(tool["svg_content"])
        viewbox = tool_root.get(
            "viewBox", f"0 0 {tool['width_mm']} {tool['height_mm']}"
        )

        nested = ET.SubElement(root, f"{{{_SVG_NS}}}svg")
        nested.set("x",       f"{x:.4f}")
        nested.set("y",       f"{y:.4f}")
        nested.set("width",   f"{tool['width_mm']:.4f}")
        nested.set("height",  f"{tool['height_mm']:.4f}")
        nested.set("viewBox", viewbox)

        for child in list(tool_root):
            nested.append(child)

    output_dir = Path(config.SVG_OUTPUT_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = (output_dir / f"shadowboard_{timestamp}.svg").resolve()

    ET.ElementTree(root).write(str(output_path), xml_declaration=True, encoding="unicode")

    print(
        f"[compose] Shadowboard SVG saved: {output_path}  "
        f"({len(tools)} tool(s), {board_w}×{board_h}mm)"
    )
    return str(output_path)
