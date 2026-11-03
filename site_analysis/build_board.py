"""Compose the site-analysis presentation board as a 4K (3840 x 2160) PDF.

The original survey drawing (original_site_analysis.jpg) keeps its geometry:
no crop, rotation, redraw or overlay, only a uniform scale. The circular site
photographs are converted to black and white; the blue drainage channel and
red survey markers keep their colour. All new graphics sit outside the map.

Edit the TEXT section below, then run:
    python3 build_board.py
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
SRC = HERE / "original_site_analysis.jpg"
OUT_PDF = HERE / "site_analysis_board_4k.pdf"

# ---------------------------------------------------------------- palette
BG = (241, 240, 236)
INK = (30, 30, 30)
MUTED = (110, 108, 104)
HAIR = (180, 178, 172)
WATER = (46, 126, 160)
MARKER = (192, 57, 43)

FD = "/usr/share/fonts/opentype/inter/"
def f(w, s):
    return ImageFont.truetype(FD + f"Inter-{w}.otf", s)

# ---------------------------------------------------------------- text
TITLE = "SITE ANALYSIS"
SUBTITLE = "Street activity and the drainage channel: photographic survey"

LEFT_NOTES = [
    ("Urban morphology",
     "Dense, fine-grain fabric of small plots and narrow lanes. Little open "
     "space inside the blocks, so the streets carry most daily activity."),
    ("Drainage channel",
     "The open channel (blue) runs through the site as a continuous line. "
     "Its edges switch between green verges and strips used for dumping."),
    ("Commercial frontage",
     "Shops, kiosks and vegetable carts gather on the main roads and at "
     "junctions, forming small informal activity nodes."),
]
RIGHT_NOTES = [
    ("Workshops and storage",
     "Sheds with large metal doors and open yards show light industry and "
     "storage mixed into the housing."),
    ("Waste",
     "Refuse collects on vacant plots, at wall bases and along the channel, "
     "on edges with no clear owner or use."),
    ("Open ground",
     "The large unbuilt land to the east is used for loading and parking. "
     "It is the main open space left in the area."),
]
FOOTNOTE = ("Photographs taken on site. Each is linked by a line to the red "
            "point where it was taken.")

# ---------------------------------------------------------------- photos to B&W
def photos_to_bw(img):
    a = np.asarray(img).astype(int)
    # Photographs are filled discs; map linework is thin. An opening on the
    # non-white mask keeps the discs and drops the lines.
    nw = Image.fromarray(((a.min(2) < 238) * 255).astype(np.uint8))
    m = nw.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MaxFilter(9))
    m = m.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.MinFilter(11))
    in_photo = np.asarray(m) > 0
    saturated = np.asarray(img.convert("HSV"))[..., 1] > 70
    keep_colour = saturated & ~in_photo      # blue channel, red markers
    grey = np.asarray(img.convert("L").convert("RGB"))
    out = np.where(keep_colour[..., None], np.asarray(img), grey)
    return Image.fromarray(out.astype(np.uint8))

# ---------------------------------------------------------------- layout
W, H = 3840, 2160
M = 110
src = photos_to_bw(Image.open(SRC).convert("RGB"))
SCALE = 1.86
mw, mh = round(src.width * SCALE), round(src.height * SCALE)
map_img = src.resize((mw, mh), Image.LANCZOS)

board = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(board)

def wrap(t, font, width):
    lines, cur = [], ""
    for w_ in t.split():
        trial = (cur + " " + w_).strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur); cur = w_
    return lines + [cur] if cur else lines

def para(x, y, t, font, width, fill=INK, lh=1.5):
    for line in wrap(t, font, width):
        d.text((x, y), line, font=font, fill=fill)
        y += int(font.size * lh)
    return y

# header
tf = f("Bold", 76)
d.text((M, M - 10), TITLE, font=tf, fill=INK)
d.text((M + d.textlength(TITLE, font=tf) + 36, M + 30), SUBTITLE,
       font=f("Light", 32), fill=MUTED)
d.line([(M, M + 105), (W - M, M + 105)], fill=INK, width=2)

# map panel
COL = 560
mx = (W - mw) // 2
my = M + 170
d.rectangle([mx - 1, my - 1, mx + mw, my + mh], outline=HAIR, width=1)
board.paste(map_img, (mx, my))
d.text((mx, my + mh + 16), "Fig. 1  Observation map", font=f("Regular", 24), fill=MUTED)

# notes
def notes(x, y, items, width):
    hf, bf = f("SemiBold", 28), f("Light", 25)
    for head, body in items:
        d.line([(x, y), (x + width, y)], fill=HAIR, width=1)
        d.text((x, y + 18), head.upper(), font=hf, fill=INK)
        y = para(x, y + 66, body, bf, width, lh=1.55) + 60
    return y

lx = M
rx = mx + mw + (mx - M - COL)
rw = W - M - rx
notes(lx, my, LEFT_NOTES, COL)
notes(rx, my, RIGHT_NOTES, rw)

# legend
ly = my + mh - 330
d.line([(rx, ly), (rx + rw, ly)], fill=INK, width=2)
d.text((rx, ly + 18), "LEGEND", font=f("SemiBold", 28), fill=INK)
ly += 90
lf = f("Light", 25)
d.ellipse([rx + 2, ly, rx + 42, ly + 40], outline=INK, width=2, fill=(150, 150, 150))
d.text((rx + 70, ly + 6), "Site photograph", font=lf, fill=INK); ly += 65
d.ellipse([rx + 15, ly + 12, rx + 29, ly + 26], fill=MARKER)
d.text((rx + 70, ly + 4), "Survey point", font=lf, fill=INK); ly += 60
d.line([(rx, ly + 18), (rx + 44, ly + 18)], fill=INK, width=2)
d.text((rx + 70, ly + 4), "Photo reference line", font=lf, fill=INK); ly += 60
d.line([(rx, ly + 18), (rx + 44, ly + 18)], fill=WATER, width=6)
d.text((rx + 70, ly + 4), "Water / drainage channel", font=lf, fill=INK)

# footer
d.text((M, H - M + 10), FOOTNOTE, font=f("Light", 22), fill=MUTED)

board.save(OUT_PDF, resolution=300)
print("map", (mx, my, mw, mh), "board", board.size)
