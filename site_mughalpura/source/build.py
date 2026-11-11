import sys, ezdxf
from ezdxf.enums import TextEntityAlignment
from PIL import Image, ImageDraw
sys.path.insert(0, sys.argv[1])
import trace as T

S = 0.45          # metres per image pixel (estimated from vehicles - VERIFY)
W, H = 2000, 1125
def P(pt): return (pt[0] * S, (H - pt[1]) * S)

doc = ezdxf.new("R2018", setup=True)
doc.units = ezdxf.units.M
msp = doc.modelspace()
LAYERS = {
    "ROAD-EDGE": 8, "KACHA-PATH": 33, "TRACK-VERIFY": 6, "BOUNDARY-WALL": 1, "BUILDING": 7,
    "APARTMENT": 5, "ROW-HOUSING-BLOCK": 30, "PLOT-LINES-APPROX": 9, "PLOT-BOUNDARY": 2,
    "WATER": 4, "TANK": 140, "TREE": 3, "TEXT": 7, "ANNOTATION": 2, "GE-IMAGE": 254,
}
for n, c in LAYERS.items():
    doc.layers.add(n, color=c)
doc.layers.get("KACHA-PATH").dxf.linetype = "DASHED"
doc.layers.get("TRACK-VERIFY").dxf.linetype = "DASHDOT"
doc.layers.get("PLOT-LINES-APPROX").dxf.linetype = "HIDDEN"
doc.header["$LTSCALE"] = 2.0

def pl(pts, layer, closed=False):
    msp.add_lwpolyline([P(p) for p in pts], close=closed, dxfattribs={"layer": layer})

for e in T.ROAD_EDGES: pl(e, "ROAD-EDGE")
for e in T.PATHS: pl(e, "KACHA-PATH")
for e in T.TRACK: pl(e, "TRACK-VERIFY")
for e in T.WALLS: pl(e, "BOUNDARY-WALL")
for e in T.BUILDINGS: pl(e, "BUILDING", True)
for e in T.APARTMENTS: pl(e, "APARTMENT", True)
for e in T.HOUSE_BLOCKS: pl(e, "ROW-HOUSING-BLOCK", True)
for e in T.CROSS_LANES: pl(e, "ROW-HOUSING-BLOCK")
for e in T.plot_lines(): pl(e, "PLOT-LINES-APPROX")
for e in T.PLOTS: pl(e, "PLOT-BOUNDARY", True)
for e in T.POND: pl(e, "WATER", True)
for c, r in T.WATER_TANK + T.STORAGE_TANKS:
    msp.add_circle(P(c), r * S, dxfattribs={"layer": "TANK"})
for c, r in T.TREES:
    cx, cy = P(c); R = r * S
    msp.add_circle((cx, cy), R, dxfattribs={"layer": "TREE"})
    msp.add_circle((cx, cy), R * 0.15, dxfattribs={"layer": "TREE"})
for (x, y), txt, sz in T.LABELS:
    t = msp.add_text(txt, height=sz * 0.8, dxfattribs={"layer": "TEXT", "style": "Standard"})
    t.set_placement(P((x, y)), align=TextEntityAlignment.MIDDLE_CENTER)

# Hatch for pond
h = msp.add_hatch(color=4, dxfattribs={"layer": "WATER"})
h.set_pattern_fill("ANSI31", scale=0.5)
for e in T.POND: h.paths.add_polyline_path([P(p) for p in e], is_closed=True)

# Site extent frame, north arrow, notes
pl([(0, 0), (W, 0), (W, H), (0, H)], "ANNOTATION", True)
nx, ny = W * S + 25, H * S - 40
msp.add_lwpolyline([(nx, ny), (nx - 6, ny - 18), (nx, ny - 13), (nx + 6, ny - 18)], close=True, dxfattribs={"layer": "ANNOTATION"})
msp.add_text("N", height=6, dxfattribs={"layer": "ANNOTATION"}).set_placement((nx, ny + 6), align=TextEntityAlignment.MIDDLE_CENTER)
# scale bar 100 m
sx, sy = W * S + 10, 40
for i in range(5):
    msp.add_lwpolyline([(sx, sy + i * 20), (sx + 4, sy + i * 20), (sx + 4, sy + (i + 1) * 20), (sx, sy + (i + 1) * 20)], close=True, dxfattribs={"layer": "ANNOTATION"})
msp.add_text("100 m", height=4, dxfattribs={"layer": "ANNOTATION"}).set_placement((sx + 8, sy + 50), align=TextEntityAlignment.MIDDLE_LEFT)
notes = ["SITE PLAN - MUGHALPURA (TRACED FROM GOOGLE EARTH IMAGE)",
         "UNITS: METRES. SCALE ESTIMATED AT 0.45 m/PIXEL FROM VEHICLE SIZES - VERIFY WITH ONE SITE MEASUREMENT AND RESCALE (SCALE cmd, base 0,0).",
         "LAYER GE-IMAGE: 123.jpg UNDERLAY ALIGNED TO LINEWORK (KEEP 123.jpg IN SAME FOLDER AS THIS FILE).",
         "PLOT-LINES-APPROX / TRACK-VERIFY LAYERS ARE INDICATIVE ONLY. ACCURACY OF IMAGE TRACING ~ +/-1 m."]
for i, n in enumerate(notes):
    msp.add_text(n, height=4 if i == 0 else 2.5, dxfattribs={"layer": "ANNOTATION"}).set_placement((0, -10 - i * 6))

# Raster underlay (same image), placed under the drawing
idef = doc.add_image_def(filename="123.jpg", size_in_pixel=(W, H))
img = msp.add_image(idef, insert=(0, 0), size_in_units=(W * S, H * S), rotation=0, dxfattribs={"layer": "GE-IMAGE"})
img.dxf.fade = 30
doc.set_raster_variables(frame=0, quality=1, units="m")
doc.saveas(sys.argv[2])

# Overlay preview for checking
im = Image.open(sys.argv[3]).convert("RGB")
d = ImageDraw.Draw(im)
col = {"road": (255, 255, 255), "path": (255, 170, 0), "wall": (255, 0, 0), "bld": (0, 255, 255),
       "apt": (80, 120, 255), "blk": (255, 128, 0), "plot": (255, 255, 0), "tree": (0, 255, 0)}
def dl(pts, c, closed=False, w=2):
    p = list(pts) + ([pts[0]] if closed else [])
    d.line(p, fill=c, width=w)
for e in T.ROAD_EDGES: dl(e, col["road"])
for e in T.PATHS + T.TRACK: dl(e, col["path"])
for e in T.WALLS: dl(e, col["wall"])
for e in T.BUILDINGS: dl(e, col["bld"], True)
for e in T.APARTMENTS: dl(e, col["apt"], True)
for e in T.HOUSE_BLOCKS: dl(e, col["blk"], True)
for e in T.plot_lines(): dl(e, (200, 200, 0), w=1)
for e in T.PLOTS: dl(e, col["plot"], True)
for (cx, cy), r in T.TREES + T.WATER_TANK + T.STORAGE_TANKS:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col["tree"], width=2)
im.save(sys.argv[4])
