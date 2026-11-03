"""Compose the site-analysis presentation board.

The original survey drawing (original_site_analysis.jpg) is placed on the board
unaltered: no crop, rotation, redraw or overlay. It is only scaled uniformly
(same factor on both axes), so every photograph, leader line and red marker
keeps its exact relative position. All new graphics sit OUTSIDE the map panel.

Edit the TEXT section below to change titles and notes, then run:
    python3 build_board.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
SRC = HERE / "original_site_analysis.jpg"
OUT_PNG = HERE / "site_analysis_board.png"
OUT_PDF = HERE / "site_analysis_board.pdf"

# ---------------------------------------------------------------- palette
BG = (244, 242, 237)        # light warm grey
PAPER = (255, 255, 255)
INK = (38, 38, 38)
MUTED = (125, 120, 112)
HAIR = (190, 185, 176)
ACCENT = (196, 104, 60)     # muted terracotta (from reference)
WATER = (46, 126, 160)      # matches the drawing's channel blue
MARKER = (192, 57, 43)      # matches the drawing's red markers

# ---------------------------------------------------------------- fonts
FD = "/usr/share/fonts/opentype/inter/"
def f(w, s):
    return ImageFont.truetype(FD + f"Inter-{w}.otf", s)

# ---------------------------------------------------------------- text
TITLE = "SITE ANALYSIS"
SUBTITLE = "Street life, activity nodes and the drainage channel — photographic survey"
BOARD_NO = "01"

CATEGORIES = [
    ("Retail", "Shopfronts & kiosks"),
    ("Street vending", "Fruit & vegetable carts"),
    ("Workshops", "Storage sheds & yards"),
    ("Transport", "Loaders, rickshaws, bikes"),
    ("Solid waste", "Dumping on open edges"),
    ("Water channel", "Open drain & green edge"),
    ("Open ground", "Unbuilt plots, parking"),
]

LEFT_NOTES = [
    ("01", "Urban morphology",
     "A dense, fine-grain fabric of small plots and narrow lanes. Building "
     "footprints are tightly packed, leaving little public open space inside "
     "the blocks; streets carry most everyday activity."),
    ("02", "Drainage channel",
     "The open channel (blue) runs as a continuous linear spine through the "
     "site. Its edges alternate between green verges and neglected strips "
     "used for dumping, splitting the neighbourhood into two halves."),
    ("03", "Commercial frontage",
     "Small shops, kiosks and vending carts gather along the main roads and "
     "at street junctions, forming informal activity nodes."),
]

RIGHT_NOTES = [
    ("04", "Workshops & storage",
     "Sheds with large metal doors and open yards indicate light industry "
     "and storage mixed into the residential fabric."),
    ("05", "Waste & open edges",
     "Refuse accumulates on vacant plots, wall bases and along the channel — "
     "edges without clear ownership or use."),
    ("06", "Open ground",
     "Large unbuilt land on the eastern side is used for loading and "
     "parking; it is the main reserve of open space for the area."),
]

FOOTNOTE = ("Observation points were recorded on site; each photograph is "
            "linked by a leader line to the red marker where it was taken. "
            "Base drawing reproduced without alteration.")

# ---------------------------------------------------------------- layout
W, H = 4961, 3508                    # A3 landscape @ 300 dpi
M = 150                              # outer margin
src = Image.open(SRC).convert("RGB")
SCALE = 2.55                         # uniform scale only
mw, mh = round(src.width * SCALE), round(src.height * SCALE)
map_img = src.resize((mw, mh), Image.LANCZOS)

board = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(board)

def text_w(t, font):
    return d.textlength(t, font=font)

def wrap(t, font, width):
    words, lines, cur = t.split(), [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if text_w(trial, font) <= width:
            cur = trial
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines

def para(x, y, t, font, width, fill=INK, lh=1.5):
    for line in wrap(t, font, width):
        d.text((x, y), line, font=font, fill=fill)
        y += int(font.size * lh)
    return y

# ---- header
d.text((M, M - 20), TITLE, font=f("Bold", 120), fill=INK)
tw = text_w(TITLE, f("Bold", 120))
d.text((M + tw + 50, M + 52), SUBTITLE, font=f("Light", 46), fill=MUTED)
nf = f("Thin", 150)
d.text((W - M - text_w(BOARD_NO, nf), M - 45), BOARD_NO, font=nf, fill=ACCENT)
d.line([(M, M + 160), (W - M, M + 160)], fill=INK, width=3)

# ---- map panel (centre)
COL_L = 620                          # side column width
mx = M + COL_L + 70
my = M + 520
d.rectangle([mx - 2, my - 2, mx + mw + 1, my + mh + 1], outline=HAIR, width=2)
board.paste(map_img, (mx, my))       # the original, unaltered
cap_y = my + mh + 22
d.text((mx, cap_y), "FIG. 01", font=f("SemiBold", 30), fill=ACCENT)
d.text((mx + 140, cap_y), "Observation map — survey points, photographs and drainage channel",
       font=f("Regular", 30), fill=MUTED)

# ---- activity strip (above map)
sy = M + 260
cw = mw / len(CATEGORIES)
for i, (name, sub) in enumerate(CATEGORIES):
    cx = mx + i * cw
    col = WATER if name == "Water channel" else ACCENT
    d.ellipse([cx, sy + 8, cx + 36, sy + 44], outline=col, width=3)
    d.text((cx + 18, sy + 26), f"{i+1}", font=f("SemiBold", 22), fill=col, anchor="mm")
    d.text((cx + 54, sy), name.upper(), font=f("SemiBold", 34), fill=INK)
    d.text((cx + 54, sy + 50), sub, font=f("Light", 28), fill=MUTED)
    if i:
        d.line([(cx - 25, sy + 5), (cx - 25, sy + 95)], fill=HAIR, width=2)
d.line([(mx, sy + 170), (mx + mw, sy + 170)], fill=HAIR, width=2)

# ---- side note columns
def note_column(x, y, notes, width):
    for num, head, body in notes:
        d.text((x, y), num, font=f("Thin", 96), fill=ACCENT)
        d.text((x + 150, y + 22), head.upper(), font=f("SemiBold", 38), fill=INK)
        d.line([(x + 150, y + 82), (x + width, y + 82)], fill=HAIR, width=2)
        y = para(x + 150, y + 108, body, f("Light", 30), width - 150, fill=INK, lh=1.55)
        y += 90
    return y

lx = M
note_column(lx, my, LEFT_NOTES, COL_L)
rx = mx + mw + 70
rw = W - M - rx
note_column(rx, my, RIGHT_NOTES, rw)

# ---- legend (bottom of right column)
ly = my + mh - 520
d.text((rx, ly), "LEGEND", font=f("SemiBold", 38), fill=INK)
d.line([(rx, ly + 60), (rx + rw, ly + 60)], fill=INK, width=2)
ly += 110
lf = f("Light", 32)
# site photograph
d.ellipse([rx, ly - 6, rx + 60, ly + 54], outline=INK, width=2)
d.ellipse([rx + 12, ly + 6, rx + 48, ly + 42], fill=HAIR)
d.text((rx + 100, ly + 6), "Site photograph", font=lf, fill=INK); ly += 105
# survey point
d.ellipse([rx + 20, ly + 10, rx + 40, ly + 30], fill=MARKER)
d.text((rx + 100, ly + 2), "Survey / observation point", font=lf, fill=INK); ly += 90
# leader
d.line([(rx, ly + 20), (rx + 60, ly + 20)], fill=INK, width=2)
d.text((rx + 100, ly + 2), "Photo leader line", font=lf, fill=INK); ly += 90
# channel
d.line([(rx, ly + 20), (rx + 60, ly + 20)], fill=WATER, width=8)
d.text((rx + 100, ly + 2), "Water / drainage channel", font=lf, fill=INK); ly += 90

# ---- footer
fy = H - M - 40
d.line([(M, fy - 40), (W - M, fy - 40)], fill=HAIR, width=2)
d.text((M, fy), "NOTE", font=f("SemiBold", 28), fill=ACCENT)
d.text((M + 110, fy), FOOTNOTE, font=f("Light", 28), fill=MUTED)

board.save(OUT_PNG, dpi=(300, 300))
board.save(OUT_PDF, resolution=300)
print("map placed at", (mx, my), "size", (mw, mh), "board", board.size)
