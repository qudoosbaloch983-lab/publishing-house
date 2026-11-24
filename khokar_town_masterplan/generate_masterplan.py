"""
Khokar Town Low-Income Housing — 2D Masterplan generator (AutoCAD-compatible DXF)

Usage:
    pip install ezdxf shapely matplotlib
    python generate_masterplan.py site_khoker.dxf Khokar_Town_Masterplan.dxf [preview.png]

How it works
------------
* The user's site DXF is opened and used as the base drawing. The original
  site-boundary LWPOLYLINE and the 7 original DIMENSION entities are kept
  vertex-for-vertex; only their layer assignment is changed so they sit on
  the masterplan layer structure.
* Drawing units are INCHES (as in the source file, $INSUNITS = 1). The design is
  set out in FEET in a local frame whose origin is the SW extreme of the site
  boundary (min-x, min-y of the source vertices) and is converted to the source
  coordinate system with T(x, y) = (OX + 12x, OY + 12y). No rotation / scaling is
  applied, so everything registers exactly on the original boundary.
* North is taken as +Y (the source file's $NORTHDIRECTION = 0).
* Every building / zone polygon is checked to lie inside the original boundary;
  the script aborts if anything falls outside.
* An area schedule and unit count are computed from the actual geometry and
  written into the drawing and to masterplan_schedule.json.
"""
import json
import math
import sys
from collections import OrderedDict, defaultdict

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union

SRC = sys.argv[1] if len(sys.argv) > 1 else "site_khoker.dxf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Khokar_Town_Masterplan.dxf"
PNG = sys.argv[3] if len(sys.argv) > 3 else None

MARLA = 225.0  # sq ft (LDA / Punjab govt standard marla)

doc = ezdxf.readfile(SRC)
msp = doc.modelspace()

# ---------------------------------------------------------------- site boundary
_bnds = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
assert len(_bnds) == 1, "expected exactly one boundary polyline in source"
BND = _bnds[0]
RAW = [tuple(p) for p in BND.get_points("xy")]
OX = min(p[0] for p in RAW)
OY = min(p[1] for p in RAW)


def T(x, y):
    """local feet -> drawing inches"""
    return (OX + 12.0 * x, OY + 12.0 * y)


SITE = Polygon([((x - OX) / 12.0, (y - OY) / 12.0) for x, y in RAW])
assert SITE.is_valid

# ---------------------------------------------------------------- layers
LAYERS = OrderedDict([
    # name                              (rgb, lineweight)
    ("MP-00-CONTEXT-INDICATIVE",        ((160, 160, 160), 18)),
    ("MP-01-SITE-BOUNDARY",             ((220, 20, 20), 70)),
    ("MP-02-APARTMENTS",                ((176, 64, 48), 50)),
    ("MP-03-CLUSTER-HOUSES",            ((176, 120, 20), 35)),
    ("MP-03A-CLUSTER-COURTYARDS",       ((196, 160, 60), 18)),
    ("MP-04-SINGLE-HOUSES",             ((130, 70, 140), 35)),
    ("MP-05-COMMERCIAL",                ((40, 90, 170), 50)),
    ("MP-06-COMMUNITY-FACILITIES",      ((110, 60, 160), 50)),
    ("MP-07-PARKS-LANDSCAPE",           ((60, 130, 50), 18)),
    ("MP-08-PEDESTRIAN-PATHWAYS",       ((170, 120, 70), 18)),
    ("MP-09-ROADS-CIRCULATION",         ((90, 90, 90), 35)),
    ("MP-10-SERVICES-UTILITIES",        ((0, 130, 140), 35)),
    ("MP-11-DIMENSIONS",                ((0, 0, 0), 13)),
    ("MP-12-ANNOTATION",                ((0, 0, 0), 13)),
    ("MP-13-LEGEND-SCHEDULE",           ((0, 0, 0), 13)),
])
FILL_RGB = {
    "MP-02-APARTMENTS": (226, 120, 98),
    "MP-03-CLUSTER-HOUSES": (240, 190, 90),
    "MP-03A-CLUSTER-COURTYARDS": (250, 234, 190),
    "MP-04-SINGLE-HOUSES": (200, 160, 210),
    "MP-05-COMMERCIAL": (120, 165, 225),
    "MP-06-COMMUNITY-FACILITIES": (175, 150, 215),
    "MP-07-PARKS-LANDSCAPE": (165, 210, 140),
    "MP-08-PEDESTRIAN-PATHWAYS": (235, 220, 195),
    "MP-09-ROADS-CIRCULATION": (200, 200, 200),
    "MP-10-SERVICES-UTILITIES": (140, 205, 210),
}
for name, (rgb, lw) in LAYERS.items():
    if name not in doc.layers:
        lay = doc.layers.add(name)
    else:
        lay = doc.layers.get(name)
    lay.rgb = rgb
    lay.dxf.lineweight = lw
for name, rgb in FILL_RGB.items():
    fl = name + "-FILL"
    lay = doc.layers.add(fl) if fl not in doc.layers else doc.layers.get(fl)
    lay.rgb = rgb
    lay.dxf.lineweight = 0
if "DASHED2" in doc.linetypes:
    doc.layers.get("MP-00-CONTEXT-INDICATIVE").dxf.linetype = "DASHED2"

if "MP-TEXT" not in doc.styles:
    doc.styles.add("MP-TEXT", font="arial.ttf")
if "MP-ARCH" not in doc.dimstyles:
    ds = doc.dimstyles.new("MP-ARCH")
    ds.dxf.dimtxt = 18
    ds.dxf.dimasz = 12
    ds.dxf.dimexo = 6
    ds.dxf.dimexe = 6
    ds.dxf.dimgap = 4
    ds.dxf.dimblk = "ARCHTICK"
    ds.dxf.dimlunit = 4      # architectural
    ds.dxf.dimtad = 1
    ds.dxf.dimdec = 0
    ds.dxf.dimtxsty = "MP-TEXT"
    ds.dxf.dimclrd = 256
    ds.dxf.dimclre = 256
    ds.dxf.dimclrt = 256

# move original entities onto masterplan layers (geometry untouched)
BND.dxf.layer = "MP-01-SITE-BOUNDARY"
for e in msp:
    if e.dxftype() == "DIMENSION":
        e.dxf.layer = "MP-11-DIMENSIONS"

# ---------------------------------------------------------------- registries
AREA = defaultdict(list)      # schedule category -> [shapely polygons]
INSIDE_CHECK = []             # (name, polygon) must lie inside SITE
UNITS = defaultdict(int)
HOUSES = []                   # dicts


def _coords(poly):
    return list(poly.exterior.coords)[:-1]


def outline(poly, layer, closed=True):
    if isinstance(poly, Polygon):
        pts = _coords(poly)
    else:
        pts = poly
    msp.add_lwpolyline([T(*p) for p in pts], close=closed, dxfattribs={"layer": layer})


def fill(poly, layer):
    h = msp.add_hatch(color=256, dxfattribs={"layer": layer + "-FILL"})
    h.paths.add_polyline_path([T(*p) for p in _coords(poly)], is_closed=True)
    for hole in poly.interiors:
        h.paths.add_polyline_path([T(*p) for p in list(hole.coords)[:-1]], is_closed=True)
    return h


def zone(poly, layer, cat=None, do_fill=True, check=True, name=""):
    """draw polygon outline (+fill), register in area schedule"""
    if check:
        INSIDE_CHECK.append((name or layer, poly))
    if do_fill:
        fill(poly, layer)
    outline(poly, layer)
    if cat:
        AREA[cat].append(poly)
    return poly


def R(x0, y0, x1, y1):
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def text(s, x, y, h=12, layer="MP-12-ANNOTATION", rot=0.0, align=TextEntityAlignment.MIDDLE_CENTER):
    t = msp.add_text(s, height=12.0 * h, rotation=rot, dxfattribs={"layer": layer, "style": "MP-TEXT"})
    t.set_placement(T(x, y), align=align)
    return t


def mtext(s, x, y, h=12, width=None, layer="MP-12-ANNOTATION", attach=5):
    m = msp.add_mtext(s, dxfattribs={"layer": layer, "style": "MP-TEXT", "char_height": h,
                                     "attachment_point": attach})
    m.dxf.insert = T(x, y)
    if width:
        m.dxf.width = width
    return m


def circle(x, y, r, layer):
    msp.add_circle(T(x, y), 12 * r, dxfattribs={"layer": layer})


def line(p, q, layer, lt=None):
    a = {"layer": layer}
    if lt:
        a["linetype"] = lt
    msp.add_line(T(*p), T(*q), dxfattribs=a)


def tree(x, y, r=5):
    circle(x, y, r, "MP-07-PARKS-LANDSCAPE")
    circle(x, y, r * 0.25, "MP-07-PARKS-LANDSCAPE")


def dim(p1, p2, base, angle=0):
    d = msp.add_linear_dim(base=T(*base), p1=T(*p1), p2=T(*p2), angle=angle,
                           dimstyle="MP-ARCH", dxfattribs={"layer": "MP-11-DIMENSIONS"})
    d.render()


# ================================================================ HOUSING
HTYPES = {
    "2.5M": dict(marla=2.5, layer="MP-03-CLUSTER-HOUSES"),
    "3M": dict(marla=3.0, layer="MP-03-CLUSTER-HOUSES"),
    "4M": dict(marla=4.0, layer="MP-03-CLUSTER-HOUSES"),
    "5M-S": dict(marla=5.0, layer="MP-04-SINGLE-HOUSES"),
}


def house(x0, y0, x1, y1, typ, front, hid, stagger=0.0, front_set=5.0, rear_set=0.0):
    """plot rectangle + built footprint. front in N,S,E,W = side facing courtyard/street"""
    lay = HTYPES[typ]["layer"]
    plot = R(x0, y0, x1, y1)
    INSIDE_CHECK.append((hid, plot))
    outline(plot, lay)
    fs = front_set + stagger
    fx0, fy0, fx1, fy1 = x0, y0, x1, y1
    if front == "N":
        fy1 -= fs; fy0 += rear_set
    elif front == "S":
        fy0 += fs; fy1 -= rear_set
    elif front == "E":
        fx1 -= fs; fx0 += rear_set
    elif front == "W":
        fx0 += fs; fx1 -= rear_set
    fp = R(fx0, fy0, fx1, fy1)
    fill(fp, lay)
    outline(fp, lay)
    # entrance marker: short tick on the front edge, centred
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tick = {"N": ((cx - 1.5, fy1), (cx + 1.5, fy1), (cx, fy1 + 2)),
            "S": ((cx - 1.5, fy0), (cx + 1.5, fy0), (cx, fy0 - 2)),
            "E": ((fx1, cy - 1.5), (fx1, cy + 1.5), (fx1 + 2, cy)),
            "W": ((fx0, cy - 1.5), (fx0, cy + 1.5), (fx0 - 2, cy))}[front]
    msp.add_lwpolyline([T(*p) for p in tick], close=True, dxfattribs={"layer": lay})
    rot = 90 if front in ("E", "W") else 0
    fcx, fcy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    label = typ.replace("-S", "")
    if rot:
        text(hid, fcx - 2.2, fcy, 1.6, lay, rot=rot)
        text(label, fcx + 2.2, fcy, 1.6, lay, rot=rot)
    else:
        text(hid, fcx, fcy + 2.2, 1.6, lay)
        text(label, fcx, fcy - 2.2, 1.6, lay)
    a = plot.area
    cat = "Single housing plots" if typ == "5M-S" else "Cluster housing plots"
    AREA[cat].append(plot)
    UNITS[typ] += 1
    HOUSES.append(dict(id=hid, type=typ, plot_sqft=round(a, 1), marla=round(a / MARLA, 2),
                       footprint_sqft=round(fp.area, 1)))
    return plot


def row_x(x0, y0, n, w, d, typ, front, prefix, start=1, stagger=True):
    """n plots side by side along +x, depth d along +y"""
    for i in range(n):
        st = (1.5 if i % 2 else 0.0) if stagger else 0.0
        house(x0 + i * w, y0, x0 + (i + 1) * w, y0 + d, typ, front, f"{prefix}-{start + i:02d}", stagger=st)
    return start + n


def row_y(x0, y0, n, w, d, typ, front, prefix, start=1, stagger=True):
    """n plots stacked along +y (frontage w along y), depth d along +x"""
    for i in range(n):
        st = (1.5 if i % 2 else 0.0) if stagger else 0.0
        house(x0, y0 + i * w, x0 + d, y0 + (i + 1) * w, typ, front, f"{prefix}-{start + i:02d}", stagger=st)
    return start + n


def courtyard(poly, label, trees=(), cluster_label=None, lab_xy=None):
    zone(poly, "MP-03A-CLUSTER-COURTYARDS", "Cluster shared courtyards", name=label)
    c = poly.centroid
    lx, ly = lab_xy if lab_xy else (c.x, c.y)
    for (tx, ty) in trees:
        tree(tx, ty, 4)


CLUSTERS = []


def cluster_tag(name, typ, n, x, y, rot=0):
    """cluster title placed inside its shared courtyard"""
    CLUSTERS.append(dict(cluster=name, type=typ, houses=n))
    mt = typ.replace("M", " MARLA")
    if rot:
        text(name, x - 2.4, y, 2.6, "MP-12-ANNOTATION", rot=rot)
        text(f"{n} x {mt}", x + 1.4, y, 1.7, "MP-12-ANNOTATION", rot=rot)
        text("shared court", x + 4.4, y, 1.4, "MP-12-ANNOTATION", rot=rot)
    else:
        text(f"{name} - SHARED COURTYARD", x, y + 3.0, 2.6, "MP-12-ANNOTATION")
        text(f"{n} x {mt} cluster houses (G+1)", x, y - 1.0, 1.8, "MP-12-ANNOTATION")
        text("doors open onto the court; service lanes at rear", x, y - 4.2, 1.3, "MP-12-ANNOTATION")


# ---- C1 : west block, 3 Marla (22.5' x 30' = 675 sft) -- E-W courtyard
row_x(12, 202, 4, 22.5, 30, "3M", "N", "C1")
row_x(12, 256, 4, 22.5, 30, "3M", "S", "C1", start=5)
courtyard(R(8, 232, 106, 256), "C1 - 3 MARLA", trees=[(16, 244), (98, 244)])
cluster_tag("CLUSTER C1", "3M", 8, 57, 244)

# ---- C2 : west block, 2.5 Marla (22.5' x 25' = 562.5 sft)
row_x(12, 294, 4, 22.5, 25, "2.5M", "N", "C2")
row_x(12, 341, 4, 22.5, 25, "2.5M", "S", "C2", start=5)
courtyard(R(8, 319, 106, 341), "C2 - 2.5 MARLA", trees=[(16, 330), (98, 330)])
cluster_tag("CLUSTER C2", "2.5M", 8, 57, 330)

# ---- C3 : north band, 3 Marla (25' x 27' = 675 sft)
row_x(116, 305, 5, 25, 27, "3M", "N", "C3")
row_x(116, 354, 5, 25, 27, "3M", "S", "C3", start=6)
courtyard(R(112, 332, 246, 354), "C3 - 3 MARLA", trees=[(122, 343), (236, 343)],
          lab_xy=(160, 343))
cluster_tag("CLUSTER C3", "3M", 10, 178.5, 343)

# ---- C4 : park-edge U-cluster, 2.5 Marla (20' x 28.125' = 562.5 sft) opening to the park
row_x(204, 202, 2, 20, 28.125, "2.5M", "N", "C4", stagger=False)
row_x(204, 271.875, 2, 20, 28.125, "2.5M", "S", "C4", start=3, stagger=False)
C4_D = 562.5 / 20.875   # 26.95' deep -> exactly 562.5 sft
row_y(246 - C4_D, 230.125, 2, 20.875, C4_D, "2.5M", "W", "C4", start=5, stagger=False)
courtyard(R(202, 230.125, 246 - C4_D, 271.875), "C4", trees=[(210.5, 234.5), (210.5, 267.5)])
cluster_tag("CLUSTER C4", "2.5M", 6, 209.5, 251, rot=90)

# ---- C5 : east block, 4 Marla (22.5' x 40' = 900 sft)
row_x(280, 204, 4, 22.5, 40, "4M", "N", "C5")
row_x(280, 268, 4, 22.5, 40, "4M", "S", "C5", start=5)
courtyard(R(280, 244, 370, 268), "C5 - 4 MARLA", trees=[(287, 256), (363, 256)])
cluster_tag("CLUSTER C5", "4M", 8, 325, 256)

# ---- Single housing units (5 Marla, 24' x 47' = 1128 sft), fronting the main road
for i in range(5):
    house(35, 50 + 24 * i, 82, 74 + 24 * i, "5M-S", "E", f"S-{i + 1:02d}", front_set=7, rear_set=6)
text("SINGLE HOUSING UNITS", 58.5, 174.5, 2.6, "MP-04-SINGLE-HOUSES")
text("5 x 5 MARLA INDIVIDUAL HOUSES", 58.5, 171.5, 1.8, "MP-04-SINGLE-HOUSES")

# ================================================================ APARTMENTS (exactly two)
APTS = [
    ("APARTMENT BLOCK A", R(128, 128, 194, 168)),
    ("APARTMENT BLOCK B", R(288, 334, 354, 376)),
]
APT_FLOORS, APT_FLATS_PER_FLOOR = 4, 3   # G+3, 3 x 2-bed flats per floor
for nm, p in APTS:
    zone(p, "MP-02-APARTMENTS", "Apartment building footprints", name=nm)
    x0, y0, x1, y1 = p.bounds
    # stair/lift core + corridor indication
    cx = (x0 + x1) / 2
    core = R(cx - 6, y0 + 12, cx + 6, y1 - 12)
    outline(core, "MP-02-APARTMENTS")
    line((cx - 6, y0 + 12), (cx + 6, y1 - 12), "MP-02-APARTMENTS")
    line((cx + 6, y0 + 12), (cx - 6, y1 - 12), "MP-02-APARTMENTS")
    line((x0 + 22, y0), (x0 + 22, y1), "MP-02-APARTMENTS")
    line((x1 - 22, y0), (x1 - 22, y1), "MP-02-APARTMENTS")
    text(nm, cx, (y0 + y1) / 2 + 10, 3.0, "MP-02-APARTMENTS")
    text(f"G+{APT_FLOORS - 1}  |  {APT_FLOORS * APT_FLATS_PER_FLOOR} FLATS", cx, (y0 + y1) / 2 - 10, 2.2, "MP-02-APARTMENTS")
    UNITS["APT"] += APT_FLOORS * APT_FLATS_PER_FLOOR

# ================================================================ COMMERCIAL
mw = zone(R(8, 6, 80, 40), "MP-05-COMMERCIAL", "Commercial market", name="Market W")
me = zone(R(134, 6, 188, 40), "MP-05-COMMERCIAL", "Commercial market", name="Market E")
SHOPS = 0
for (x0, x1, n) in ((8, 80, 6), (134, 188, 4)):
    w = (x1 - x0) / n
    for i in range(1, n):
        line((x0 + i * w, 12), (x0 + i * w, 40), "MP-05-COMMERCIAL")
    line((x0, 12), (x1, 12), "MP-05-COMMERCIAL")           # arcade line
    for i in range(n):
        text(f"SHOP", x0 + (i + 0.5) * w, 27, 1.6, "MP-05-COMMERCIAL")
    SHOPS += n
text("NEIGHBOURHOOD MARKET (6 SHOPS)", 44, 9, 2.0, "MP-05-COMMERCIAL")
text("NEIGHBOURHOOD MARKET (4 SHOPS)", 161, 9, 2.0, "MP-05-COMMERCIAL")
text("6' ARCADE FACING STREET No.10", 44, 4, 1.4, "MP-05-COMMERCIAL")

# ================================================================ COMMUNITY
zone(R(126, 48, 190, 80), "MP-06-COMMUNITY-FACILITIES", "Community centre", name="Community centre")
text("COMMUNITY CENTRE /", 158, 67, 2.8, "MP-06-COMMUNITY-FACILITIES")
text("MULTIPURPOSE HALL (G+1)", 158, 63, 2.8, "MP-06-COMMUNITY-FACILITIES")
text("hall | skills workshop | clinic | office", 158, 58, 1.6, "MP-06-COMMUNITY-FACILITIES")
line((150, 48), (150, 80), "MP-06-COMMUNITY-FACILITIES")
cs = zone(R(108, 6, 134, 46).intersection(SITE), "MP-08-PEDESTRIAN-PATHWAYS", "Entrance plaza & community square",
          name="Community square")
text("ENTRANCE PLAZA /", 121, 30, 1.5, "MP-08-PEDESTRIAN-PATHWAYS")
text("COMMUNITY SQUARE", 121, 27, 1.5, "MP-08-PEDESTRIAN-PATHWAYS")
text("(weekly bazaar)", 121, 24, 1.6, "MP-08-PEDESTRIAN-PATHWAYS")
gc = zone(R(124, 84, 196, 124), "MP-07-PARKS-LANDSCAPE", "Shared gathering spaces", name="Gathering court")
text("COMMUNITY GATHERING COURT", 160, 108, 2.4, "MP-07-PARKS-LANDSCAPE")
text("shaded lawn | seating | chaupal", 160, 104, 1.6, "MP-07-PARKS-LANDSCAPE")
circle(160, 96, 6, "MP-07-PARKS-LANDSCAPE")
for tx in (132, 188):
    for ty in (92, 116):
        tree(tx, ty, 4.5)

# ================================================================ PARK + PLAYGROUND
park = zone(R(112, 202, 200, 300), "MP-07-PARKS-LANDSCAPE", "Central park & playground", name="Central park")
outline(R(118, 208, 194, 294), "MP-08-PEDESTRIAN-PATHWAYS")       # walking loop (outer)
outline(R(124, 214, 188, 288), "MP-08-PEDESTRIAN-PATHWAYS")       # walking loop (inner)
pg = R(128, 218, 162, 246)
outline(pg, "MP-07-PARKS-LANDSCAPE")
fill(pg, "MP-03A-CLUSTER-COURTYARDS")
text("CHILDREN'S", 145, 234, 2.2, "MP-07-PARKS-LANDSCAPE")
text("PLAYGROUND", 145, 231, 2.2, "MP-07-PARKS-LANDSCAPE")
for (px, py) in ((134, 222), (156, 222), (134, 242), (156, 242)):
    circle(px, py, 2, "MP-07-PARKS-LANDSCAPE")
circle(170, 268, 9, "MP-06-COMMUNITY-FACILITIES")
text("PAVILION", 170, 268, 1.8, "MP-06-COMMUNITY-FACILITIES")
text("CENTRAL COMMUNITY PARK", 156, 282, 3.0, "MP-07-PARKS-LANDSCAPE")
text("open lawn | walking loop | shade trees", 150, 258, 1.6, "MP-07-PARKS-LANDSCAPE")
for (tx, ty) in ((115, 205), (115, 251), (115, 297), (197, 205), (197, 251), (197, 297), (156, 205), (156, 297)):
    tree(tx, ty, 4)

# ================================================================ ROADS (no dedicated parking)
RA = R(84, 0, 108, 200).intersection(SITE)
RB = unary_union([R(6, 176, 366, 200), R(340, 170, 366, 176)]).intersection(SITE)
RC = R(248, 200, 272, 400).intersection(SITE)
ROADS = unary_union([RA, RB, RC])
zone(ROADS, "MP-09-ROADS-CIRCULATION", "Roads & vehicular circulation", name="Roads")
# footpath edges (4') + centre lines
line((88, 0.8), (88, 176), "MP-09-ROADS-CIRCULATION"); line((104, 0.8), (104, 176), "MP-09-ROADS-CIRCULATION")
line((6, 180), (84, 180), "MP-09-ROADS-CIRCULATION"); line((6, 196), (88, 196), "MP-09-ROADS-CIRCULATION")
line((108, 180), (366, 180), "MP-09-ROADS-CIRCULATION"); line((104, 196), (252, 196), "MP-09-ROADS-CIRCULATION")
line((268, 196), (366, 196), "MP-09-ROADS-CIRCULATION")
line((252, 196), (252, 384.5), "MP-09-ROADS-CIRCULATION"); line((268, 196), (268, 384.8), "MP-09-ROADS-CIRCULATION")
CL = "DASHED2" if "DASHED2" in doc.linetypes else None
line((96, 1), (96, 188), "MP-09-ROADS-CIRCULATION", CL)
line((8, 188), (364, 188), "MP-09-ROADS-CIRCULATION", CL)
line((260, 188), (260, 384.5), "MP-09-ROADS-CIRCULATION", CL)
text("MAIN ACCESS STREET  24' R.O.W.", 93, 120, 2.2, "MP-09-ROADS-CIRCULATION", rot=90)
text("INTERNAL SERVICE STREET  24' R.O.W.", 300, 186, 2.2, "MP-09-ROADS-CIRCULATION")
text("INTERNAL SERVICE STREET  24' R.O.W.", 40, 186, 2.2, "MP-09-ROADS-CIRCULATION")
text("NORTH LINK STREET 24' R.O.W.", 257, 300, 2.2, "MP-09-ROADS-CIRCULATION", rot=90)
text("NO DEDICATED PARKING - kerbside drop-off / service only", 225, 191.5, 1.5, "MP-09-ROADS-CIRCULATION")
# traffic-calming tables at pedestrian crossings
for k in range(6):
    line((112 + k * 2, 176.5), (112 + k * 2, 199.5), "MP-08-PEDESTRIAN-PATHWAYS")   # zebra
    line((248.5, 300.5 + k * 0.8), (271.5, 300.5 + k * 0.8), "MP-08-PEDESTRIAN-PATHWAYS")

# ================================================================ PEDESTRIAN NETWORK
PED = [
    ("Green spine", R(112, 46, 122, 176)),
    ("North-west walk", R(106, 202, 112, 400).intersection(SITE)),
    ("West lane", R(8, 286, 106, 294)),
    ("Park promenade", R(112, 300, 246, 305)),
    ("East walk", R(272, 204, 280, 334)),
    ("Spine link", R(122, 46, 192, 48)),
    ("C3 east link", R(246, 305, 248, 384.5).intersection(SITE)),
]
for nm, p in PED:
    zone(p, "MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian pathways", name=nm)
text("PEDESTRIAN GREEN SPINE", 117, 110, 2.2, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("PEDESTRIAN LANE", 57, 290, 1.8, "MP-08-PEDESTRIAN-PATHWAYS")
text("PARK PROMENADE", 180, 302.5, 1.6, "MP-08-PEDESTRIAN-PATHWAYS")
text("PEDESTRIAN WALK", 276, 300, 1.6, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("PEDESTRIAN WALK", 109, 330, 1.6, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
for ty in range(60, 176, 22):
    tree(110, ty, 2.5)

# apartment commons (B) + other landscape pockets
for nm, p, lab in [
    ("Apartment commons", R(280, 308, 370, 334), "APARTMENT COMMONS / TOT-LOT"),
    ("NW kitchen garden", R(8, 366, 106, 384).intersection(SITE).intersection(
        Polygon([(0, 0), (400, 0), (400, 400), (0, 400)])), "COMMUNITY KITCHEN GARDEN"),
    ("Apartment A forecourt", R(124, 124, 198, 128), None),
]:
    if p.is_empty:
        continue
    zone(p, "MP-07-PARKS-LANDSCAPE", "Shared gathering spaces" if "commons" in nm.lower() else
         "Parks, gardens & landscape buffers", name=nm)
    if lab:
        c = p.centroid
        text(lab, c.x + (8 if "KITCHEN" in lab else 0), c.y, 2.0, "MP-07-PARKS-LANDSCAPE")
for tx in (285, 365):
    tree(tx, 321, 4)
circle(325, 321, 5, "MP-07-PARKS-LANDSCAPE")

# ================================================================ SERVICES & UTILITIES
svc = zone(R(6, 48, 33, 170), "MP-10-SERVICES-UTILITIES", "Services & utilities", name="Services strip")
zone(R(6, 40, 84, 48), "MP-10-SERVICES-UTILITIES", "Services & utilities", name="Market service yard")
for (x0, y0, x1, y1, lab) in ((10, 128, 29, 140, "TUBE WELL /\\PUMP ROOM"),
                               (10, 110, 29, 122, "ELEC. SUB-\\STATION"),
                               (10, 88, 29, 102, "WASTE &\\RECYCLING"),
                               (9, 52, 30, 72, "COMPOST /\\NURSERY")):
    p = R(x0, y0, x1, y1)
    outline(p, "MP-10-SERVICES-UTILITIES")
    l1, l2 = lab.split("\\")
    text(l1, (x0 + x1) / 2, (y0 + y1) / 2 + 1.3, 1.4, "MP-10-SERVICES-UTILITIES")
    text(l2, (x0 + x1) / 2, (y0 + y1) / 2 - 1.3, 1.4, "MP-10-SERVICES-UTILITIES")
circle(19.5, 155, 9, "MP-10-SERVICES-UTILITIES")
text("O.H. WATER", 19.5, 156.3, 1.4, "MP-10-SERVICES-UTILITIES")
text("TANK", 19.5, 153.7, 1.4, "MP-10-SERVICES-UTILITIES")
circle(19.5, 80, 3, "MP-10-SERVICES-UTILITIES")
text("RWH RECHARGE WELL", 19.5, 75.5, 1.2, "MP-10-SERVICES-UTILITIES")
text("SERVICES & UTILITIES", 3.5, 109, 2.0, "MP-10-SERVICES-UTILITIES", rot=90)
text("MARKET SERVICE YARD", 44, 44, 1.6, "MP-10-SERVICES-UTILITIES")

# ================================================================ ENTRANCES + CONTEXT (indicative)
def arrow(x, y, ang, L=14, layer="MP-12-ANNOTATION"):
    a = math.radians(ang)
    tip = (x, y)
    tail = (x - L * math.cos(a), y - L * math.sin(a))
    l1 = (x - 4 * math.cos(a - 0.45), y - 4 * math.sin(a - 0.45))
    l2 = (x - 4 * math.cos(a + 0.45), y - 4 * math.sin(a + 0.45))
    line(tail, tip, layer)
    msp.add_lwpolyline([T(*tip), T(*l1), T(*l2)], close=True, dxfattribs={"layer": layer})
    h = msp.add_hatch(color=256, dxfattribs={"layer": layer})
    h.paths.add_polyline_path([T(*tip), T(*l1), T(*l2)], is_closed=True)


arrow(96, 6, 90)
text("MAIN ENTRANCE", 96, -9, 3.0)
text("from STREET No. 10 (SOUTH)", 96, -13, 2.0)
arrow(260, 378, -90)
text("SECONDARY ENTRANCE", 260, 395, 3.0)
text("from CONNECTING ROAD (NORTH)", 260, 391, 2.0)
arrow(109, 378, -90, L=8)
text("PEDESTRIAN GATE", 109, 391, 1.8)
for gx in (82.5, 109.5):           # gate pillars at main entrance
    zone(R(gx - 1.5, 1.2, gx + 1.5, 4), "MP-09-ROADS-CIRCULATION", None, name="gate pillar")
for gx in (246.5, 273.5):
    zone(R(gx - 1.5, 381.5, gx + 1.5, 384.0), "MP-09-ROADS-CIRCULATION", None, name="gate pillar N")

CTX = "MP-00-CONTEXT-INDICATIVE"
line((-30, -2.5), (230, -4.6), CTX); line((-30, -32.5), (230, -34.6), CTX)
text("STREET No. 10  (indicative - road edges not in source CAD)", 120, -24, 2.6, CTX)
line((20, 388), (420, 390.7), CTX); line((20, 418), (420, 420.7), CTX)
text("CONNECTING ROAD  (indicative - road edges not in source CAD)", 220, 410, 2.6, CTX)

# north arrow
NX, NY = 430, 380
msp.add_lwpolyline([T(NX, NY + 16), T(NX - 6, NY - 8), T(NX, NY - 2), T(NX + 6, NY - 8)], close=True,
                   dxfattribs={"layer": "MP-12-ANNOTATION"})
circle(NX, NY + 2, 13, "MP-12-ANNOTATION")
text("N", NX, NY + 21, 5)

# ================================================================ DIMENSIONS (key)
dim((84, 120), (108, 120), (0, 140), 0)
dim((248, 230), (272, 230), (0, 236), 0)
dim((40, 176), (40, 200), (60, 0), 90)
dim((128, 168), (194, 168), (0, 171.5), 0)
dim((288, 376), (354, 376), (0, 379.5), 0)
dim((12, 202), (34.5, 202), (0, 199), 0)
dim((12, 202), (12, 232), (8.5, 0), 90)
dim((280, 204), (302.5, 204), (0, 201.5), 0)
dim((35, 50), (82, 50), (0, 46.5), 0)
dim((112, 300), (112, 202), (106.5, 0), 90)
dim((112, 202), (200, 202), (0, 198.5), 0)
dim((8, 232), (8, 256), (5.5, 0), 90)

# ================================================================ VERIFY
bad = []
for nm, p in INSIDE_CHECK:
    if p.is_empty:
        continue
    if not SITE.buffer(1e-6).contains(p):
        bad.append((nm, round(p.difference(SITE).area, 3)))
if bad:
    raise SystemExit(f"Elements outside site boundary: {bad}")

# overlaps between primary land-use polygons (exclude internal details)
prim_cats = [c for c in AREA]
for i, a in enumerate(prim_cats):
    for b in prim_cats[i + 1:]:
        ov = unary_union(AREA[a]).intersection(unary_union(AREA[b])).area
        if ov > 0.5:
            print(f"WARNING overlap {a} / {b}: {ov:.1f} sft")

# ================================================================ SCHEDULE
site_area = SITE.area
used = unary_union([unary_union(v) for v in AREA.values()])
AREA_SFT = OrderedDict()
order = ["Cluster housing plots", "Cluster shared courtyards", "Apartment building footprints",
         "Single housing plots", "Commercial market", "Community centre", "Entrance plaza & community square",
         "Shared gathering spaces", "Central park & playground", "Parks, gardens & landscape buffers",
         "Pedestrian pathways", "Roads & vehicular circulation", "Services & utilities"]
for c in order:
    AREA_SFT[c] = unary_union(AREA[c]).area if AREA.get(c) else 0.0
AREA_SFT["Parks, gardens & landscape buffers"] += site_area - used.area   # residual margins = landscape
total = sum(AREA_SFT.values())

cl_units = UNITS["2.5M"] + UNITS["3M"] + UNITS["4M"]
apt_units = UNITS["APT"]
all_units = cl_units + apt_units + UNITS["5M-S"]
apt_fp = AREA_SFT["Apartment building footprints"]
schedule = dict(
    site_area_sqft_from_cad=round(site_area, 1),
    site_area_acres_from_cad=round(site_area / 43560, 3),
    site_area_stated_sqft=112505,
    areas_sqft={k: round(v, 0) for k, v in AREA_SFT.items()},
    areas_pct={k: round(100 * v / site_area, 1) for k, v in AREA_SFT.items()},
    units=OrderedDict([("Cluster 2.5 Marla", UNITS["2.5M"]), ("Cluster 3 Marla", UNITS["3M"]),
                       ("Cluster 4 Marla", UNITS["4M"]), ("Cluster total", cl_units),
                       ("Apartments (2 blocks, G+3)", apt_units), ("Single houses 5 Marla", UNITS["5M-S"]),
                       ("TOTAL DWELLINGS", all_units)]),
    shops=SHOPS,
    clusters=CLUSTERS,
    houses=HOUSES,
    cluster_share_of_units_pct=round(100 * cl_units / all_units, 1),
    residential_land_sqft=dict(
        cluster=round(AREA_SFT["Cluster housing plots"] + AREA_SFT["Cluster shared courtyards"]),
        apartments_incl_commons=round(apt_fp + unary_union(
            [p for p in AREA["Shared gathering spaces"] if p.bounds[0] >= 279]).area),
        single=round(AREA_SFT["Single housing plots"])),
    density_du_per_acre=round(all_units / (site_area / 43560), 1),
    est_population_at_6pphh=all_units * 6,
)

# ---- legend + schedule in drawing (to the east of site)
LX, LY = 420, 350
text("KHOKAR TOWN LOW-INCOME HOUSING - MASTERPLAN", LX, LY + 0, 5.0, "MP-13-LEGEND-SCHEDULE",
     align=TextEntityAlignment.LEFT)
text('"Transforming isolated housing into an interconnected habitat where home, work, community and nature coexist."',
     LX, LY - 7, 2.0, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
text("Khokar Town, Lahore  |  Drawing units: inches (1 unit = 1\")  |  Scale 1:500 @ A1", LX, LY - 11, 2.0,
     "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
text("ZONING LEGEND", LX, LY - 22, 3.4, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
legend = [("MP-02-APARTMENTS", "Apartment residential zone (2 blocks, G+3)"),
          ("MP-03-CLUSTER-HOUSES", "Cluster housing - 2.5 / 3 / 4 Marla"),
          ("MP-03A-CLUSTER-COURTYARDS", "Cluster shared courtyards (semi-private)"),
          ("MP-04-SINGLE-HOUSES", "Single housing units - 5 Marla"),
          ("MP-05-COMMERCIAL", "Commercial zone - neighbourhood market"),
          ("MP-06-COMMUNITY-FACILITIES", "Community facilities - centre / hall"),
          ("MP-07-PARKS-LANDSCAPE", "Parks, playground, gardens & gathering spaces"),
          ("MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian pathways, plaza & spine"),
          ("MP-09-ROADS-CIRCULATION", "Roads & vehicular circulation (no parking)"),
          ("MP-10-SERVICES-UTILITIES", "Services & utilities zone")]
yy = LY - 30
for lay, lab in legend:
    sw = R(LX, yy - 2, LX + 8, yy + 2.5)
    fill(sw, lay)
    outline(sw, lay)
    text(lab, LX + 11, yy, 2.2, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.MIDDLE_LEFT)
    yy -= 6.5
line((LX, yy + 1), (LX + 8, yy + 1), "MP-01-SITE-BOUNDARY")
text("Original site boundary (from source CAD - unchanged)", LX + 11, yy + 1, 2.2, "MP-13-LEGEND-SCHEDULE",
     align=TextEntityAlignment.MIDDLE_LEFT)
yy -= 12

text("AREA DISTRIBUTION SCHEDULE", LX, yy, 3.4, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
yy -= 6
def trow(c1, c2, c3, bold=False):
    global yy
    h = 2.2
    text(c1, LX, yy, h, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.MIDDLE_LEFT)
    text(c2, LX + 78, yy, h, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.MIDDLE_RIGHT)
    text(c3, LX + 96, yy, h, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.MIDDLE_RIGHT)
    line((LX, yy - 2.4), (LX + 98, yy - 2.4), "MP-13-LEGEND-SCHEDULE")
    yy -= 5
trow("LAND USE", "AREA (sq ft)", "%")
for k, v in AREA_SFT.items():
    trow(k, f"{v:,.0f}", f"{100 * v / site_area:.1f}")
trow("TOTAL (site as drawn in CAD)", f"{total:,.0f}", "100.0")
text(f"Site area computed from CAD boundary = {site_area:,.0f} sq ft ({site_area / 43560:.2f} acres); "
     f"stated brief area = 112,505 sq ft.", LX, yy, 1.7, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
yy -= 10

text("HOUSING UNIT COUNT", LX, yy, 3.4, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
yy -= 6
trow("TYPOLOGY", "UNITS", "PLOT")
trow("Cluster house 2.5 Marla (C2, C4)", f"{UNITS['2.5M']}", "562.5 sft")
trow("Cluster house 3 Marla (C1, C3)", f"{UNITS['3M']}", "675 sft")
trow("Cluster house 4 Marla (C5)", f"{UNITS['4M']}", "900 sft")
trow("CLUSTER HOUSING SUB-TOTAL", f"{cl_units}", f"{100 * cl_units / all_units:.0f}%")
trow(f"Apartments - 2 blocks x G+3 x {APT_FLATS_PER_FLOOR} flats/floor", f"{apt_units}", "~700 sft")
trow("Single housing units 5 Marla", f"{UNITS['5M-S']}", "1,128 sft")
trow("TOTAL DWELLING UNITS", f"{all_units}", "")
text(f"Gross density {all_units / (site_area / 43560):.1f} DU/acre | est. population ~{all_units * 6} (6 p/hh) | "
     f"market: {SHOPS} shops | 1 Marla = 225 sq ft", LX, yy, 1.7, "MP-13-LEGEND-SCHEDULE",
     align=TextEntityAlignment.LEFT)
yy -= 8
notes = [
    "NOTES",
    "1. Site boundary and original dimensions are the source CAD entities, unchanged (vertex-for-vertex).",
    "2. North assumed = +Y of source drawing. External road edges are indicative only (not in source CAD).",
    "3. Cluster houses G+1: front door on the shared courtyard (semi-private), rear on a service lane/street.",
    "4. Alternate house footprints are set back 1'-6\" extra to articulate courtyard facades.",
    "5. No dedicated parking area is provided; streets allow drop-off, emergency and service access.",
    "6. Apartments placed so their winter shadows fall on streets / commons, not on cluster houses.",
]
for n in notes:
    text(n, LX, yy, 2.0 if n == "NOTES" else 1.7, "MP-13-LEGEND-SCHEDULE", align=TextEntityAlignment.LEFT)
    yy -= 4

doc.header["$INSUNITS"] = 1
doc.saveas(OUT)
with open(OUT.rsplit(".", 1)[0] + "_schedule.json", "w") as f:
    json.dump(schedule, f, indent=1)

print(json.dumps({k: v for k, v in schedule.items() if k not in ("houses", "clusters")}, indent=1))

if PNG:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, LineweightPolicy

    d2 = ezdxf.readfile(OUT)
    fig = plt.figure(figsize=(30, 21))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(d2)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, lineweight_scaling=0.6)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(d2.modelspace(), finalize=True)
    fig.savefig(PNG, dpi=110, facecolor="white")
