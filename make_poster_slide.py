"""
Generate poster_code_section.pptx — a single editable slide for the
Aviation Tool Accountability poster's Code Overview section.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

NAVY  = RGBColor(0x1a, 0x3a, 0x4a)
TEAL  = RGBColor(0x2e, 0x7d, 0x9e)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK  = RGBColor(0x22, 0x22, 0x22)
LGRAY = RGBColor(0xee, 0xee, 0xee)


def add_rect(slide, l, t, w, h, fill=None, line=None):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    shape.line.fill.background()
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(0.5)
    else:
        shape.line.fill.background()
    return shape


def add_label(slide, text, l, t, w, h, bg, fg=WHITE, size=9, bold=False):
    shape = add_rect(slide, l, t, w, h, fill=bg)
    tf = shape.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = fg
    return shape


def add_textbox(slide, text, l, t, w, h, size=9, bold=False, color=DARK, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


prs = Presentation()
prs.slide_width  = Inches(5)
prs.slide_height = Inches(4)

blank_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(blank_layout)

# White background
bg = slide.background
fill = bg.fill
fill.solid()
fill.fore_color.rgb = WHITE

# Header bar
add_label(slide, "CODE OVERVIEW", 0, 0, 5, 0.28, bg=NAVY, size=10, bold=True)

# Pipeline boxes
boxes = [("capture.py", "Photo"), ("process.py", "Silhouette"),
         ("vectorize.py", "SVG"), ("export.py", "Laser File")]
box_w = 0.88
gap   = 0.18
start = 0.18
top   = 0.38

for i, (name, sub) in enumerate(boxes):
    x = start + i * (box_w + gap)
    shape = add_rect(slide, x, top, box_w, 0.42, fill=TEAL)
    tf = shape.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r1 = p.add_run()
    r1.text = name + "\n"
    r1.font.size = Pt(8)
    r1.font.bold = True
    r1.font.color.rgb = WHITE
    r2 = p.add_run()
    r2.text = sub
    r2.font.size = Pt(7)
    r2.font.bold = False
    r2.font.color.rgb = RGBColor(0xCC, 0xE8, 0xF4)

    # Arrow (skip after last box)
    if i < len(boxes) - 1:
        ax = x + box_w + 0.02
        add_textbox(slide, "›", ax, top + 0.08, 0.14, 0.28, size=14, color=TEAL, align=PP_ALIGN.CENTER)

# Divider line
add_rect(slide, 0.18, 0.90, 4.64, 0.01, fill=LGRAY)

# Description paragraph
desc = (
    "Pi camera captures a JPEG → OpenCV undistorts and detects an ArUco marker "
    "for real-world scale → tool silhouette is extracted and expanded for foam "
    "clearance → vtracer converts the mask to SVG → dimensions are patched to mm "
    "for the laser cutter. All parameters live in config.py."
)
add_textbox(slide, desc, 0.18, 0.96, 4.64, 0.90, size=9, color=DARK)

# Divider line
add_rect(slide, 0.18, 1.94, 4.64, 0.01, fill=LGRAY)

# Tech stack pills
pills = ["Python 3", "OpenCV", "Picamera2", "vtracer", "Raspberry Pi", "ArUco Markers"]
px = 0.18
py = 2.02
for pill in pills:
    pw = len(pill) * 0.072 + 0.18
    if px + pw > 4.82:
        px = 0.18
        py += 0.28
    shape = add_rect(slide, px, py, pw, 0.22, fill=NAVY)
    tf = shape.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = pill
    r.font.size = Pt(8)
    r.font.color.rgb = WHITE
    px += pw + 0.08

prs.save("poster_code_section.pptx")
print("Saved: poster_code_section.pptx")
