"""
Khokar Town Low-Income Housing — MASTERPLAN REFINEMENT (v2)
Develops the student's own DXF (site_khoker.dxf, layer "2") into a complete
editable masterplan.

    pip install ezdxf shapely matplotlib
    python refine_masterplan.py site_khoker_v2_input.dxf Khokar_Town_Masterplan_v2.dxf [preview.png]

Principles
* The input DXF is the base drawing. The site-boundary LWPOLYLINE and its 7 DIMENSIONs
  are kept vertex-for-vertex (only re-layered).
* All of the student's road / lane edges, the roundabout arcs and the central circle
  are kept unchanged (re-layered to MP-09A / MP-06).
* The student's 44 houses (drawn as loose LINE pairs = 9" walls) are detected and
  re-drawn as CLOSED POLYLINES (outer + inner wall face) at the SAME coordinates.
  Exception (documented): 6 pinwheel "middle" units are widened 2'-9" into their
  courtyard to create the 3 Marla type that the drawing did not contain.
* Units: inches. Design set out in feet, local origin = min-x/min-y of boundary.
* North is assumed = +Y (file has no north arrow / geo-location; verify on survey).
"""
import itertools
import json
import math
import sys
from collections import OrderedDict, defaultdict

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

SRC = sys.argv[1] if len(sys.argv) > 1 else "site_khoker_v2_input.dxf"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Khokar_Town_Masterplan_v2.dxf"
PNG = sys.argv[3] if len(sys.argv) > 3 else None
MARLA = 225.0  # sq ft (LDA standard)

doc = ezdxf.readfile(SRC)
msp = doc.modelspace()

# ------------------------------------------------------------------ site
_b = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
assert len(_b) == 1
BND = _b[0]
RAW = [tuple(p) for p in BND.get_points("xy")]
OX, OY = min(p[0] for p in RAW), min(p[1] for p in RAW)


def T(x, y):
    return (OX + 12.0 * x, OY + 12.0 * y)


def Lc(x, y):
    return ((x - OX) / 12.0, (y - OY) / 12.0)


SITE = Polygon([Lc(*p) for p in RAW])

# ------------------------------------------------------------------ layers
LAYERS = OrderedDict([
    ("MP-00-CONTEXT-INDICATIVE", (150, 150, 150)),
    ("MP-01-SITE-BOUNDARY", (220, 20, 20)),
    ("MP-02-APARTMENT-BLOCKS", (170, 55, 40)),
    ("MP-03-CLUSTER-HOUSE-2.5M", (205, 125, 0)),
    ("MP-03-CLUSTER-HOUSE-3M", (190, 95, 0)),
    ("MP-03-CLUSTER-HOUSE-4M", (165, 70, 0)),
    ("MP-03A-CLUSTER-COURTYARDS", (185, 150, 60)),
    ("MP-04-SINGLE-HOUSE-2.5M", (150, 80, 160)),
    ("MP-04-SINGLE-HOUSE-3M", (125, 60, 145)),
    ("MP-04-SINGLE-HOUSE-4M", (100, 40, 125)),
    ("MP-04A-SINGLE-HOUSE-PLOTS", (150, 110, 160)),
    ("MP-05-MOSQUE", (0, 115, 80)),
    ("MP-06-COMMUNITY-PLAZA-GATHERING", (190, 120, 30)),
    ("MP-07-PARKS-GREEN-SPACES", (55, 130, 45)),
    ("MP-07A-LANDSCAPE-TREES", (40, 110, 40)),
    ("MP-08-PEDESTRIAN-PATHWAYS", (160, 115, 70)),
    ("MP-09-ROADS-CIRCULATION", (95, 95, 95)),
    ("MP-09A-ORIGINAL-ROAD-EDGES", (60, 60, 60)),
    ("MP-10-SERVICES-UTILITIES", (0, 125, 140)),
    ("MP-11-DIMENSIONS", (0, 0, 0)),
    ("MP-12-ANNOTATION", (0, 0, 0)),
    ("MP-13-LEGEND-SCHEDULE", (0, 0, 0)),
])
FILL = {
    "MP-02-APARTMENT-BLOCKS": (225, 120, 100),
    "MP-03-CLUSTER-HOUSE-2.5M": (250, 205, 120),
    "MP-03-CLUSTER-HOUSE-3M": (243, 180, 85),
    "MP-03-CLUSTER-HOUSE-4M": (232, 155, 60),
    "MP-03A-CLUSTER-COURTYARDS": (250, 238, 200),
    "MP-04-SINGLE-HOUSE-2.5M": (215, 185, 225),
    "MP-04-SINGLE-HOUSE-3M": (200, 160, 215),
    "MP-04-SINGLE-HOUSE-4M": (180, 135, 200),
    "MP-04A-SINGLE-HOUSE-PLOTS": (238, 228, 242),
    "MP-05-MOSQUE": (120, 200, 165),
    "MP-06-COMMUNITY-PLAZA-GATHERING": (245, 215, 160),
    "MP-07-PARKS-GREEN-SPACES": (175, 215, 145),
    "MP-08-PEDESTRIAN-PATHWAYS": (232, 218, 196),
    "MP-09-ROADS-CIRCULATION": (205, 205, 205),
    "MP-10-SERVICES-UTILITIES": (150, 210, 215),
}
for n, rgb in LAYERS.items():
    lay = doc.layers.get(n) if n in doc.layers else doc.layers.add(n)
    lay.rgb = rgb
for n, rgb in FILL.items():
    fn = n + "-FILL"
    lay = doc.layers.get(fn) if fn in doc.layers else doc.layers.add(fn)
    lay.rgb = rgb
if "MP-TEXT" not in doc.styles:
    doc.styles.add("MP-TEXT", font="arial.ttf")
if "MP-ARCH" not in doc.dimstyles:
    ds = doc.dimstyles.new("MP-ARCH")
    for k, v in dict(dimtxt=16, dimasz=10, dimexo=4, dimexe=4, dimgap=3, dimblk="ARCHTICK",
                     dimlunit=4, dimtad=1, dimtxsty="MP-TEXT", dimdec=0).items():
        ds.dxf.set(k, v)

BND.dxf.layer = "MP-01-SITE-BOUNDARY"
for e in msp.query("DIMENSION"):
    e.dxf.layer = "MP-11-DIMENSIONS"

# ------------------------------------------------------------------ helpers
AREA = defaultdict(list)
CHECK = []


def cs(p):
    return list(p.exterior.coords)[:-1]


def pl(pts, layer, closed=True, lt=None):
    a = {"layer": layer}
    if lt:
        a["linetype"] = lt
    return msp.add_lwpolyline([T(*q) for q in pts], close=closed, dxfattribs=a)


def hatch(poly, layer):
    polys = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for p in polys:
        if p.area < 0.5:
            continue
        h = msp.add_hatch(color=256, dxfattribs={"layer": layer + "-FILL"})
        h.paths.add_polyline_path([T(*q) for q in cs(p)], is_closed=True, flags=1)
        for r in p.interiors:
            h.paths.add_polyline_path([T(*q) for q in list(r.coords)[:-1]], is_closed=True)


def zone(poly, layer, cat=None, fill=True, outline=True, name=""):
    CHECK.append((name or layer, poly))
    if fill:
        hatch(poly, layer)
    if outline:
        for p in ([poly] if poly.geom_type == "Polygon" else list(poly.geoms)):
            if p.area >= 0.5:
                pl(cs(p), layer)
    if cat:
        AREA[cat].append(poly)
    return poly


def R(x0, y0, x1, y1):
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def text(s, x, y, h=2.0, layer="MP-12-ANNOTATION", rot=0.0, al=TA.MIDDLE_CENTER):
    t = msp.add_text(s, height=12.0 * h, rotation=rot, dxfattribs={"layer": layer, "style": "MP-TEXT"})
    t.set_placement(T(x, y), align=al)


def circ(x, y, r, layer):
    msp.add_circle(T(x, y), 12.0 * r, dxfattribs={"layer": layer})


def ln(p, q, layer):
    msp.add_line(T(*p), T(*q), dxfattribs={"layer": layer})


def tree(x, y, r=4.0):
    circ(x, y, r, "MP-07A-LANDSCAPE-TREES")
    circ(x, y, 0.6, "MP-07A-LANDSCAPE-TREES")


def dim(p1, p2, base, ang=0):
    msp.add_linear_dim(base=T(*base), p1=T(*p1), p2=T(*p2), angle=ang, dimstyle="MP-ARCH",
                       dxfattribs={"layer": "MP-11-DIMENSIONS"}).render()


# ================================================================== 1. read student geometry
src = [e for e in msp.query("LINE") if e.dxf.layer == "2"]
H, V = [], []
for e in src:
    a, c = Lc(e.dxf.start.x, e.dxf.start.y), Lc(e.dxf.end.x, e.dxf.end.y)
    if abs(a[1] - c[1]) < 0.02:
        H.append((min(a[0], c[0]), max(a[0], c[0]), (a[1] + c[1]) / 2, e))
    elif abs(a[0] - c[0]) < 0.02:
        V.append((min(a[1], c[1]), max(a[1], c[1]), (a[0] + c[0]) / 2, e))
TOL = 0.05


def uniq(vals):
    out = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > 0.01:
            out.append(v)
    return out


XS, YS = uniq(v[2] for v in V), uniq(h[2] for h in H)
hcov = lambda x0, x1, y: any(abs(h[2] - y) < TOL and h[0] <= x0 + TOL and h[1] >= x1 - TOL for h in H)
vcov = lambda y0, y1, x: any(abs(v[2] - x) < TOL and v[0] <= y0 + TOL and v[1] >= y1 - TOL for v in V)
rects = []
for h in H:
    cand = [x for x in XS if h[0] - TOL <= x <= h[1] + TOL]
    for x0, x1 in itertools.combinations(cand, 2):
        if not 5 < x1 - x0 < 40:
            continue
        for y1 in YS:
            y0 = h[2]
            if 5 < y1 - y0 < 40 and hcov(x0, x1, y0) and hcov(x0, x1, y1) and vcov(y0, y1, x0) and vcov(y0, y1, x1):
                if not any(all(abs(a - b) < 0.01 for a, b in zip((x0, y0, x1, y1), r)) for r in rects):
                    rects.append((x0, y0, x1, y1))
EXIST = []
for r in rects:
    inner = (r[0] + .75, r[1] + .75, r[2] - .75, r[3] - .75)
    if any(all(abs(a - b) < 0.03 for a, b in zip(inner, q)) for q in rects):
        EXIST.append(r)
assert len(EXIST) == 44, f"expected 44 student houses, found {len(EXIST)}"

# lines that are wall faces of those houses -> replaced by closed polylines
house_edges = []
for r in EXIST:
    for q in (r, (r[0] + .75, r[1] + .75, r[2] - .75, r[3] - .75)):
        house_edges.append(q)


def on_house(e):
    a, c = Lc(e.dxf.start.x, e.dxf.start.y), Lc(e.dxf.end.x, e.dxf.end.y)
    for (x0, y0, x1, y1) in house_edges:
        for (p, q) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            seg_h = abs(p[1] - q[1]) < 1e-9
            if seg_h and abs(a[1] - p[1]) < TOL and abs(c[1] - p[1]) < TOL and \
                    min(p[0], q[0]) - TOL <= min(a[0], c[0]) and max(a[0], c[0]) <= max(p[0], q[0]) + TOL:
                return True
            if not seg_h and abs(a[0] - p[0]) < TOL and abs(c[0] - p[0]) < TOL and \
                    min(p[1], q[1]) - TOL <= min(a[1], c[1]) and max(a[1], c[1]) <= max(p[1], q[1]) + TOL:
                return True
    return False


n_conv = n_keep = 0
for e in src:
    if on_house(e):
        msp.delete_entity(e)
        n_conv += 1
    else:
        e.dxf.layer = "MP-09A-ORIGINAL-ROAD-EDGES"
        n_keep += 1
for e in msp.query("ARC"):
    if e.dxf.layer == "2":
        e.dxf.layer = "MP-09A-ORIGINAL-ROAD-EDGES"
for e in msp.query("CIRCLE"):
    if e.dxf.layer == "2":
        e.dxf.layer = "MP-06-COMMUNITY-PLAZA-GATHERING"
        RING_C = Lc(e.dxf.center.x, e.dxf.center.y)
        PLAZA_R = e.dxf.radius / 12.0
ARCS = [e for e in msp.query("ARC")]
RING_R = ARCS[0].dxf.radius / 12.0

# ================================================================== 2. typologies
CLUSTERS = OrderedDict([   # bbox of the student's clusters
    ("A", dict(bb=(21, 285, 92, 379), name="NEEM COURT")),
    ("B", dict(bb=(102, 288, 225, 379), name="SHISHAM COURT")),
    ("C", dict(bb=(235, 289, 358, 380), name="AMALTAS COURT")),
    ("D", dict(bb=(165, 174, 223, 265), name="JAMAN COURT")),
    ("E", dict(bb=(235, 170.9, 358, 262), name="KACHNAR COURT")),
])
# pinwheel middle units widened 2'-9" into their own courtyard -> 3 Marla (21'-6" x 31'-6")
WIDEN = {(128.38, 322.06): +1, (180.63, 322.06): -1, (260.98, 322.73): +1,
         (313.23, 322.73): -1, (260.98, 204.34): +1, (313.23, 204.34): -1}
HOUSES = []
for (x0, y0, x1, y1) in EXIST:
    key = (round(x0, 2), round(y0, 2))
    mod = WIDEN.get(key)
    if mod == +1:
        x1 += 2.75
    elif mod == -1:
        x0 -= 2.75
    a = (x1 - x0) * (y1 - y0)
    typ = "4M" if a > 850 else ("3M" if a > 640 else "2.5M")
    cl = next((k for k, c in CLUSTERS.items() if c["bb"][0] <= x0 and x1 <= c["bb"][2] + 0.1
               and c["bb"][1] <= y0 and y1 <= c["bb"][3]), None)
    HOUSES.append(dict(x0=x0, y0=y0, x1=x1, y1=y1, type=typ, cluster=cl, origin="existing",
                       modified=bool(mod)))

# --- single-housing zone (south-west): student's 3 units + 10 new terraced units on a 12' lane
D25, D3, D4 = (18.75, 31.5), (21.5, 31.5), (25.5, 35.5)   # frontage x depth (ft)
y = 80.0
for typ in ("4M", "3M", "2.5M", "3M", "2.5M"):          # west row, fronts east at x=39
    w, d = {"4M": D4, "3M": D3, "2.5M": D25}[typ]
    HOUSES.append(dict(x0=39 - d, y0=y, x1=39, y1=y + w, type=typ, cluster=None, origin="new", modified=False))
    y += w
y = 80.0
for typ in ("3M", "2.5M", "2.5M", "3M", "2.5M"):        # east row, fronts west at x=56.5
    w, d = {"3M": D3, "2.5M": D25}[typ]
    HOUSES.append(dict(x0=56.5, y0=y, x1=56.5 + d, y1=y + w, type=typ, cluster=None, origin="new", modified=False))
    y += w

# ================================================================== 3. circulation (student's edges kept)
cx, cy = RING_C
RING = Point(cx, cy).buffer(RING_R, 128)
PLAZA = Point(cx, cy).buffer(PLAZA_R, 128)
EW = Polygon([(0, 266.09 - 3.34 * 0.00315), (390, 266.09 + (390 - 3.34) * 0.00315),
              (390, 281.14 + (390 - 21.52) * 0.003145), (0, 281.14 - 21.52 * 0.003145)])
ROAD_ENTRY = R(88.77, -5, 103.77, 190)
SINGLE_LANE = unary_union([R(43, 66, 55, 268), R(43, 66, 88.77, 78)])
ROADS = unary_union([ROAD_ENTRY, RING.difference(PLAZA), EW, SINGLE_LANE]).difference(PLAZA).intersection(SITE)
LANES = unary_union([R(-5, 270, 13.52, 372.16), R(91.27, 270, 102.88, 378.9),
                     R(224.88, 270, 235.48, 400), R(365.48, 160, 400, 400)]).intersection(SITE).difference(ROADS)

# ================================================================== 4. draw houses
HS = {"cluster": defaultdict(int), "single": defaultdict(int)}
house_polys = []
for i, h in enumerate(sorted(HOUSES, key=lambda h: (h["cluster"] or "Z", -h["y0"], h["x0"]))):
    p = R(h["x0"], h["y0"], h["x1"], h["y1"])
    house_polys.append(p)
    h["poly"] = p
CL_IDX = defaultdict(int)
S_IDX = 0
COURTS = {}
for k, c in CLUSTERS.items():
    x0, y0, x1, y1 = c["bb"]
    hs = [h["poly"] for h in HOUSES if h["cluster"] == k]
    bb = unary_union(hs).envelope
    court = bb.difference(unary_union(hs)).difference(ROADS).difference(LANES).intersection(SITE)
    if k == "D":   # half-pinwheel: court opens west onto the green beside the plaza
        court = unary_union([court, R(150, 199.5, 165.27, 239).difference(RING)])
    court = unary_union([g for g in (court.geoms if court.geom_type != "Polygon" else [court]) if g.area > 25])
    COURTS[k] = court

for h in sorted(HOUSES, key=lambda h: (h["cluster"] or "Z", -h["y0"], h["x0"])):
    p = h["poly"]
    single = h["cluster"] is None
    lay = ("MP-04-SINGLE-HOUSE-" if single else "MP-03-CLUSTER-HOUSE-") + h["type"]
    if single:
        S_IDX += 1
        hid = f"S-{S_IDX:02d}"
        HS["single"][h["type"]] += 1
        cat = "Single houses (footprints)"
    else:
        CL_IDX[h["cluster"]] += 1
        hid = f"{h['cluster']}-{CL_IDX[h['cluster']]:02d}"
        HS["cluster"][h["type"]] += 1
        cat = "Cluster houses (footprints)"
    h["id"] = hid
    inner = R(h["x0"] + .75, h["y0"] + .75, h["x1"] - .75, h["y1"] - .75)
    zone(p, lay, cat, name=hid)
    pl(cs(inner), lay)
    # front door: side facing courtyard > lane/road
    best, bs = None, -1
    mx, my = (h["x0"] + h["x1"]) / 2, (h["y0"] + h["y1"]) / 2
    for side, (px, py) in {"N": (mx, h["y1"] + 2.5), "S": (mx, h["y0"] - 2.5),
                           "E": (h["x1"] + 2.5, my), "W": (h["x0"] - 2.5, my)}.items():
        pt = Point(px, py)
        sc = 0
        if not single and COURTS[h["cluster"]].buffer(0.3).contains(pt):
            sc = 3
        elif single and (SINGLE_LANE.buffer(4.5).contains(pt)):
            sc = 3
        elif LANES.buffer(1).contains(pt) or ROADS.buffer(1).contains(pt):
            sc = 1
        elif SITE.contains(pt) and not any(q.contains(pt) for q in house_polys):
            sc = 0.5
        if sc > bs:
            best, bs = side, sc
    h["front"] = best
    door = {"N": [(mx - 1.5, h["y1"]), (mx + 1.5, h["y1"]), (mx, h["y1"] + 2.2)],
            "S": [(mx - 1.5, h["y0"]), (mx + 1.5, h["y0"]), (mx, h["y0"] - 2.2)],
            "E": [(h["x1"], my - 1.5), (h["x1"], my + 1.5), (h["x1"] + 2.2, my)],
            "W": [(h["x0"], my - 1.5), (h["x0"], my + 1.5), (h["x0"] - 2.2, my)]}[best]
    pl(door, lay)
    vert = (h["y1"] - h["y0"]) > (h["x1"] - h["x0"])
    rot = 90 if vert else 0
    if vert:
        text(hid, mx - 1.8, my, 1.6, lay, rot=90)
        text(h["type"].replace("M", " MARLA"), mx + 1.8, my, 1.4, lay, rot=90)
    else:
        text(hid, mx, my + 1.8, 1.6, lay)
        text(h["type"].replace("M", " MARLA"), mx, my - 1.8, 1.4, lay)
    if single:
        # private plot: house + front threshold to the lane (+ rear yard on west row)
        if h["x1"] <= 40:
            plot = R(max(h["x0"] - (0 if h["type"] == "4M" else 4), 3.5), h["y0"], 43, h["y1"])
        elif h["x0"] >= 56:
            plot = R(55, h["y0"], h["x1"], h["y1"])
        else:       # student's 3 units
            plot = R(h["x0"], h["y0"], 43, h["y1"])
        zone(plot.difference(p), "MP-04A-SINGLE-HOUSE-PLOTS", "Single-house private yards & thresholds",
             outline=False, name=hid + " plot")
        pl(cs(plot), "MP-04A-SINGLE-HOUSE-PLOTS")

# ---- courtyards (semi-private) + centre features
FEAT = {"A": (56.4, 332.2), "B": (163.88, 333.8), "C": (296.48, 334.48), "D": (159, 219.25), "E": (296.48, 216.09)}
for k, c in CLUSTERS.items():
    zone(COURTS[k], "MP-03A-CLUSTER-COURTYARDS", "Cluster courtyards (semi-private)", name="court " + k)
    fx, fy = FEAT[k]
    n = sum(1 for h in HOUSES if h["cluster"] == k)
    mix = ", ".join(f"{sum(1 for h in HOUSES if h['cluster'] == k and h['type'] == t)}x{t}"
                    for t in ("2.5M", "3M", "4M") if any(h["cluster"] == k and h["type"] == t for h in HOUSES))
    if k == "A":
        circ(fx, fy, 6.5, "MP-03A-CLUSTER-COURTYARDS"); tree(fx, fy, 4)
        lab = (fx, fy - 11.5)
    elif k == "B":
        pl(cs(R(fx - 5, fy - 5, fx + 5, fy + 5)), "MP-03A-CLUSTER-COURTYARDS"); tree(fx, fy, 3.5)
        circ(fx + 9, fy + 12, 1.2, "MP-10-SERVICES-UTILITIES")
        text("hand pump / wash slab", fx + 9, fy + 9.5, 1.1, "MP-10-SERVICES-UTILITIES")
        lab = (fx, fy - 11.5)
    elif k == "C":
        pl(cs(R(fx - 7, fy + 1, fx + 7, fy + 13)), "MP-03A-CLUSTER-COURTYARDS")
        text("play patch", fx, fy + 7, 1.3, "MP-03A-CLUSTER-COURTYARDS"); tree(fx, fy - 12, 3.5)
        lab = (fx, fy - 3.5)
    elif k == "D":
        tree(171.6, 230, 3.5); tree(171.6, 207, 3.5)
        lab = (fx, fy)
    else:
        for j in range(3):
            pl(cs(R(fx - 9 + j * 6.5, fy + 6, fx - 4.5 + j * 6.5, fy + 14)), "MP-03A-CLUSTER-COURTYARDS")
        text("kitchen-garden beds", fx, fy + 16, 1.2, "MP-03A-CLUSTER-COURTYARDS"); tree(fx, fy - 12, 3.5)
        lab = (fx, fy - 1)
    if k == "D":
        text(f"CLUSTER {k}", lab[0] - 2, lab[1], 1.9, "MP-12-ANNOTATION", rot=90)
        text(c["name"], lab[0] + 0.8, lab[1], 1.4, "MP-12-ANNOTATION", rot=90)
        text(f"{n} houses: {mix}", lab[0] + 3.2, lab[1], 1.2, "MP-12-ANNOTATION", rot=90)
    else:
        text(f"CLUSTER {k}", lab[0], lab[1] + 2.4, 1.9, "MP-12-ANNOTATION")
        text(c["name"], lab[0], lab[1], 1.4, "MP-12-ANNOTATION")
        text(f"{n} houses: {mix}", lab[0], lab[1] - 2.0, 1.1, "MP-12-ANNOTATION")

# ================================================================== 5. roads & lanes
zone(ROADS, "MP-09-ROADS-CIRCULATION", "Roads (vehicular / shared surface)", name="roads")
zone(LANES, "MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian & service lanes", name="lanes")
text("MAIN ENTRY STREET 15' (existing)", 96.27, 120, 1.7, "MP-09-ROADS-CIRCULATION", rot=90)
text("INTERNAL STREET 15' (existing) - shared surface", 300, 274, 1.7, "MP-09-ROADS-CIRCULATION")
text("INTERNAL STREET 15' (existing)", 170, 274, 1.7, "MP-09-ROADS-CIRCULATION")
text("SINGLE-HOUSING LANE 12'", 49, 125, 1.6, "MP-09-ROADS-CIRCULATION", rot=90)
text("SHARED-SURFACE RING (raised, paved)", cx, cy - RING_R + 7.0, 1.2, "MP-09-ROADS-CIRCULATION")
text("PEDESTRIAN / SERVICE LANE", 97.1, 345, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("PEDESTRIAN / SERVICE LANE", 8.5, 330, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("NORTH GATE LANE 10'-7\"", 230.2, 335, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("SERVICE LANE (east)", 371, 230, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
text("NO DEDICATED PARKING: streets for access, drop-off, emergency & service only", 300, 268.3, 1.1,
     "MP-09-ROADS-CIRCULATION")
for k in range(7):   # raised zebra tables on the ring (north + south mouths)
    ln((89.5 + k * 2.1, 184.5), (89.5 + k * 2.1, 187.5), "MP-08-PEDESTRIAN-PATHWAYS")
    ln((89.5 + k * 2.1, 271.5), (89.5 + k * 2.1, 276.5), "MP-08-PEDESTRIAN-PATHWAYS")
    ln((223.5 + k * 1.9, 267.5), (223.5 + k * 1.9, 280.5), "MP-08-PEDESTRIAN-PATHWAYS")

# ================================================================== 6. community plaza (student's circle)
zone(PLAZA, "MP-06-COMMUNITY-PLAZA-GATHERING", "Community plaza (central circle)", outline=False, name="plaza")
circ(cx, cy, 7, "MP-06-COMMUNITY-PLAZA-GATHERING")
circ(cx, cy, 19, "MP-06-COMMUNITY-PLAZA-GATHERING")
tree(cx, cy, 5)
for j in range(8):
    a = math.radians(22.5 + 45 * j)
    tree(cx + 26 * math.cos(a), cy + 26 * math.sin(a), 3.2)
for a in (90, 270, 0, 180):
    r = math.radians(a)
    ln((cx + 7 * math.cos(r), cy + 7 * math.sin(r)), (cx + 19 * math.cos(r), cy + 19 * math.sin(r)),
       "MP-06-COMMUNITY-PLAZA-GATHERING")
text("COMMUNITY PLAZA", cx, cy + 11, 2.2, "MP-06-COMMUNITY-PLAZA-GATHERING")
text("(central chowk)", cx, cy + 8.6, 1.4, "MP-06-COMMUNITY-PLAZA-GATHERING")
text("shade-tree chabutra | seating ring", cx, cy - 10, 1.2, "MP-06-COMMUNITY-PLAZA-GATHERING")
text("weekly bazaar | events | gathering", cx, cy - 12.2, 1.2, "MP-06-COMMUNITY-PLAZA-GATHERING")

# ================================================================== 7. south leg: civic + housing development
# Apartment blocks (exactly two) - G+3, 3 flats/floor, single-loaded north gallery
APT_FLOORS, APT_FPF = 4, 3
APTS = [("APARTMENT BLOCK 01", R(14.5, 10, 78.5, 44), "E"),
        ("APARTMENT BLOCK 02", R(114, 10, 178, 44), "W")]
for nm, p, core_side in APTS:
    zone(p, "MP-02-APARTMENT-BLOCKS", "Apartment blocks (footprints)", name=nm)
    x0, y0, x1, y1 = p.bounds
    cx0, cx1 = (x1 - 12, x1) if core_side == "E" else (x0, x0 + 12)
    core = R(cx0, y0 + 10, cx1, y1)
    pl(cs(core), "MP-02-APARTMENT-BLOCKS")
    ln((cx0, y0 + 10), (cx1, y1), "MP-02-APARTMENT-BLOCKS"); ln((cx1, y0 + 10), (cx0, y1), "MP-02-APARTMENT-BLOCKS")
    gx0, gx1 = (x0, cx0) if core_side == "E" else (cx1, x1)
    ln((gx0, y1 - 4.5), (gx1, y1 - 4.5), "MP-02-APARTMENT-BLOCKS")          # access gallery
    bw = (gx1 - gx0) / 3
    for j in range(1, 3):
        ln((gx0 + j * bw, y0), (gx0 + j * bw, y1 - 4.5), "MP-02-APARTMENT-BLOCKS")
    for j in range(3):
        text(f"FLAT {j + 1}", gx0 + (j + .5) * bw, y0 + 13, 1.2, "MP-02-APARTMENT-BLOCKS")
    text("STAIR", (cx0 + cx1) / 2, y1 - 6, 1.1, "MP-02-APARTMENT-BLOCKS")
    ex = cx1 if core_side == "E" else cx0
    pl([(ex, y1 - 9), (ex, y1 - 3), (ex + (2.5 if core_side == "E" else -2.5), y1 - 6)], "MP-02-APARTMENT-BLOCKS")
    text(nm, (gx0 + gx1) / 2, y0 + 27, 2.4, "MP-02-APARTMENT-BLOCKS")
    text(f"G+{APT_FLOORS - 1}  |  {APT_FLOORS * APT_FPF} FLATS (3 / floor, ~510 sft)", (gx0 + gx1) / 2, y0 + 23.5,
         1.4, "MP-02-APARTMENT-BLOCKS")
    text("north access gallery - cross-ventilated flats", (gx0 + gx1) / 2, y0 + 20.8, 1.1,
         "MP-02-APARTMENT-BLOCKS")
zone(R(78.5, 6, 88.77, 48), "MP-08-PEDESTRIAN-PATHWAYS", "Forecourts & plazas", name="Apt01 forecourt")
zone(R(108, 6, 114, 48), "MP-08-PEDESTRIAN-PATHWAYS", "Forecourts & plazas", name="Apt02 forecourt")

# Civic spine footpath (primary pedestrian route) on the east side of the entry street
SPINE = R(103.77, 0, 108, 200).intersection(SITE).difference(RING)
zone(SPINE, "MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian pathways (new)", name="civic spine")
text("CIVIC SPINE - PRIMARY FOOTPATH", 105.9, 95, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)

# Central community park + children's playground
PARK = R(108, 48, 194, 114)
zone(PARK, "MP-07-PARKS-GREEN-SPACES", "Central community park & playground", name="park")
pl(cs(R(113, 53, 189, 109)), "MP-08-PEDESTRIAN-PATHWAYS")
pl(cs(R(117, 57, 185, 105)), "MP-08-PEDESTRIAN-PATHWAYS")
PG = R(156, 61, 182, 85)
hatch(PG, "MP-06-COMMUNITY-PLAZA-GATHERING"); pl(cs(PG), "MP-07-PARKS-GREEN-SPACES")
for (px, py) in ((161, 66), (177, 66), (161, 80), (177, 80), (169, 73)):
    circ(px, py, 1.8, "MP-07-PARKS-GREEN-SPACES")
text("CHILDREN'S", 169, 76.2, 1.6, "MP-07-PARKS-GREEN-SPACES")
text("PLAYGROUND", 169, 70, 1.6, "MP-07-PARKS-GREEN-SPACES")
circ(132, 90, 7, "MP-06-COMMUNITY-PLAZA-GATHERING")
text("PAVILION", 132, 90, 1.3, "MP-06-COMMUNITY-PLAZA-GATHERING")
text("CENTRAL COMMUNITY PARK", 140, 72, 2.2, "MP-07-PARKS-GREEN-SPACES")
text("lawn | walking loop | shade trees", 137, 68, 1.2, "MP-07-PARKS-GREEN-SPACES")
for (tx, ty) in ((111, 51), (111, 81), (111, 111), (150, 51), (191, 51), (191, 111), (150, 111), (191, 92)):
    tree(tx, ty, 3.5)
zone(R(108, 114, 194, 118), "MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian pathways (new)", name="park-mosque walk")

# ---------------- MOSQUE (Qibla-oriented)
LAT, LON = 31.52, 74.36            # Lahore (Khokar Town)
KLAT, KLON = 21.4225, 39.8262      # Ka'bah
p1, p2, dl = math.radians(LAT), math.radians(KLAT), math.radians(KLON - LON)
QIBLA = (math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                 math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) + 360) % 360
qv = (math.sin(math.radians(QIBLA)), math.cos(math.radians(QIBLA)))      # unit vector to Qibla (x=E, y=N)
uang = math.degrees(math.atan2(-qv[1], -qv[0]))                          # building axis u = away from Qibla


def mq(s0, t0, s1, t1):
    """rectangle in mosque frame (s along axis away from qibla, t across) -> site polygon (unplaced)"""
    return affinity.rotate(R(s0, t0, s1, t1), uang, origin=(0, 0))


M_PARTS = OrderedDict([
    ("PRAYER HALL", mq(-16, -20, 16, 20)),
    ("MIHRAB", mq(-19, -3, -16, 3)),
    ("SAHN (COURTYARD)", mq(16, -20, 38, 20)),
    ("WUZU / TOILETS", mq(38, 6, 48, 20)),
    ("MINARET", mq(38, -20, 45, -13)),
])
allm = unary_union(list(M_PARTS.values()))
dx, dy = 110 - allm.bounds[0], 119.5 - allm.bounds[1]
for k in M_PARTS:
    M_PARTS[k] = affinity.translate(M_PARTS[k], dx, dy)
MOSQUE_PLOT = R(108, 118, 197, 172).intersection(SITE)
mosque_built = unary_union([M_PARTS["PRAYER HALL"], M_PARTS["MIHRAB"], M_PARTS["WUZU / TOILETS"], M_PARTS["MINARET"]])
for k, p in M_PARTS.items():
    if k == "SAHN (COURTYARD)":
        zone(p, "MP-05-MOSQUE", "Mosque (built + sahn)", fill=False, name="sahn")
    else:
        zone(p, "MP-05-MOSQUE", "Mosque (built + sahn)", name=k)
AREA["Mosque (built + sahn)"].append(M_PARTS["SAHN (COURTYARD)"])
hatch(M_PARTS["SAHN (COURTYARD)"], "MP-06-COMMUNITY-PLAZA-GATHERING")
FORE = MOSQUE_PLOT.difference(unary_union(list(M_PARTS.values())))
zone(FORE, "MP-08-PEDESTRIAN-PATHWAYS", "Forecourts & plazas", name="mosque forecourt")


def mpt(s, t):
    x, y = affinity.rotate(Point(s, t), uang, origin=(0, 0)).coords[0]
    return (x + dx, y + dy)


# prayer rows (saffs) parallel to qibla wall + qibla arrow
for s in (-12, -7, -2, 3, 8, 13):
    ln(mpt(s, -18.5), mpt(s, 18.5), "MP-05-MOSQUE")
hx, hy = M_PARTS["PRAYER HALL"].centroid.coords[0]
text("MOSQUE", hx, hy + 3, 2.6, "MP-05-MOSQUE", rot=uang - 90 + 180 if False else 0)
text("PRAYER HALL ~1,280 sft (~150 musallis)", hx, hy - 0.5, 1.15, "MP-05-MOSQUE")
text("+ ladies' mezzanine", hx, hy - 2.6, 1.15, "MP-05-MOSQUE")
sx, sy = M_PARTS["SAHN (COURTYARD)"].centroid.coords[0]
text("SAHN", sx, sy + 1.5, 1.6, "MP-05-MOSQUE")
text("(overflow ~100)", sx, sy - 1.2, 1.1, "MP-05-MOSQUE")
wx, wy = M_PARTS["WUZU / TOILETS"].centroid.coords[0]
text("WUZU", wx, wy + 0.9, 1.1, "MP-05-MOSQUE"); text("+ WC", wx, wy - 1.0, 1.0, "MP-05-MOSQUE")
mx_, my_ = M_PARTS["MINARET"].centroid.coords[0]
circ(mx_, my_, 2.2, "MP-05-MOSQUE")
gate = mpt(38, -6.5)
tip = mpt(46, -6.5)
ln(tip, gate, "MP-05-MOSQUE")
q0 = mpt(-19.5, 0)
q1 = (q0[0] + 9 * qv[0], q0[1] + 9 * qv[1])
ln(q0, q1, "MP-05-MOSQUE")
pl([q1, (q1[0] - 2 * qv[0] + 1.2 * qv[1], q1[1] - 2 * qv[1] - 1.2 * qv[0]),
    (q1[0] - 2 * qv[0] - 1.2 * qv[1], q1[1] - 2 * qv[1] + 1.2 * qv[0])], "MP-05-MOSQUE")
text(f"QIBLA {QIBLA:.1f} deg", 113, 172.8, 1.3, "MP-05-MOSQUE")
text("MOSQUE FORECOURT / GATHERING", 176, 126, 1.4, "MP-08-PEDESTRIAN-PATHWAYS")
text("main gate", tip[0] + 4.5, tip[1], 1.1, "MP-05-MOSQUE")

# ---------------- single-housing zone open spaces
zone(R(2, 48, 88.77, 66).intersection(SITE).difference(R(78.5, 48, 88.77, 66)).union(
    R(2, 66, 43, 80).intersection(SITE)),
    "MP-07-PARKS-GREEN-SPACES", "Neighbourhood greens & tot-lots", name="SW green")
text("NEIGHBOURHOOD GREEN / TOT-LOT", 40, 57.5, 1.6, "MP-07-PARKS-GREEN-SPACES")
for (tx, ty) in ((8, 52), (30, 61), (60, 52), (8, 75), (30, 75)):
    tree(tx, ty, 3)
pl(cs(R(66, 51, 76, 61)), "MP-07-PARKS-GREEN-SPACES")
text("tot-lot", 71, 56, 1.1, "MP-07-PARKS-GREEN-SPACES")
text("SINGLE-HOUSING ZONE", 49, 196, 2.0, "MP-04-SINGLE-HOUSE-3M", rot=90)
text("13 houses - 2.5 / 3 / 4 Marla (S-01 to S-13)", 51.8, 196, 1.2, "MP-04-SINGLE-HOUSE-3M", rot=90)

# ---------------- greens north of the mosque (beside the plaza) + green link + buffers
G2 = R(108, 172, 165.27, 266.09).difference(RING).difference(COURTS["D"]).difference(Point(155, 255).buffer(5)).intersection(SITE)
zone(G2, "MP-07-PARKS-GREEN-SPACES", "Neighbourhood greens & tot-lots", name="plaza green")
text("PLAZA GREEN", 148, 190, 1.8, "MP-07-PARKS-GREEN-SPACES")
text("neighbourhood lawn", 148, 187, 1.2, "MP-07-PARKS-GREEN-SPACES")
for (tx, ty) in ((158, 182), (158, 258), (140, 250), (126, 180)):
    tree(tx, ty, 3.5)
LINK = R(222.27, 160, 235.48, 266.09).intersection(SITE)
zone(LINK, "MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian pathways (new)", name="green link")
text("GREEN LINK (to north gate)", 228.9, 218, 1.3, "MP-08-PEDESTRIAN-PATHWAYS", rot=90)
for ty in (178, 198, 240, 258):
    tree(228.9, ty, 2.5)

# ---------------- services
UT = R(180, 8, 191.5, 44)
zone(UT, "MP-10-SERVICES-UTILITIES", "Services & utilities", name="utilities")
for (y0_, y1_, lab) in ((10, 20, "PMT"), (22, 31, "TUBE WELL"), (33, 42, "WASTE")):
    pl(cs(R(181, y0_, 190.5, y1_)), "MP-10-SERVICES-UTILITIES")
    text(lab, 185.75, (y0_ + y1_) / 2, 1.0, "MP-10-SERVICES-UTILITIES")
circ(155, 255, 5, "MP-10-SERVICES-UTILITIES")
text("O.H.", 155, 256, 1.1, "MP-10-SERVICES-UTILITIES"); text("TANK", 155, 254, 1.1, "MP-10-SERVICES-UTILITIES")
AREA["Services & utilities"].append(Point(155, 255).buffer(5))

# ================================================================== 8. entrances, context, north, scale
def arrow(x, y, ang, L=12):
    a = math.radians(ang)
    tail = (x - L * math.cos(a), y - L * math.sin(a))
    ln(tail, (x, y), "MP-12-ANNOTATION")
    tri = [(x, y), (x - 4 * math.cos(a - .45), y - 4 * math.sin(a - .45)),
           (x - 4 * math.cos(a + .45), y - 4 * math.sin(a + .45))]
    h = msp.add_hatch(color=256, dxfattribs={"layer": "MP-12-ANNOTATION"})
    h.paths.add_polyline_path([T(*q) for q in tri], is_closed=True)


arrow(96.27, 8, 90)
text("MAIN ENTRANCE", 96.27, -9, 3.0)
text("STREET No. 10 (SOUTH) - existing entry kept", 96.27, -13, 1.8)
arrow(230.18, 380, -90)
text("SECONDARY ENTRANCE", 230.18, 397, 3.0)
text("CONNECTING ROAD (NORTH) - existing lane kept", 230.18, 393, 1.8)
arrow(371, 380, -90, 8)
text("SERVICE GATE", 371, 392, 1.6)
CTX = "MP-00-CONTEXT-INDICATIVE"
ln((-25, -2.6), (230, -4.7), CTX); ln((-25, -30.6), (230, -32.7), CTX)
text("STREET No. 10 (indicative - not drawn in source CAD)", 120, -24, 2.2, CTX)
ln((20, 388), (420, 390.7), CTX); ln((20, 416), (420, 418.7), CTX)
text("CONNECTING ROAD (indicative - not drawn in source CAD)", 300, 409, 2.2, CTX)

NX, NY = 420, 375
pl([(NX, NY + 15), (NX - 5.5, NY - 7), (NX, NY - 2), (NX + 5.5, NY - 7)], "MP-12-ANNOTATION")
circ(NX, NY + 2, 12, "MP-12-ANNOTATION")
text("N", NX, NY + 19.5, 4.5)
text("(assumed = drawing +Y)", NX, NY - 13, 1.3)
qx, qy = NX, NY + 2
ln((qx, qy), (qx + 11 * qv[0], qy + 11 * qv[1]), "MP-05-MOSQUE")
text("Qibla", qx + 14 * qv[0], qy + 14 * qv[1] - 1.5, 1.4, "MP-05-MOSQUE")
SBX, SBY = 440, 362
for j, L_ in enumerate((0, 10, 20, 50, 100)):
    ln((SBX + L_, SBY), (SBX + L_, SBY + 2), "MP-12-ANNOTATION")
    text(f"{L_}'", SBX + L_, SBY + 4, 1.4)
ln((SBX, SBY), (SBX + 100, SBY), "MP-12-ANNOTATION")
for a_, b_ in ((0, 10), (20, 50)):
    h = msp.add_hatch(color=256, dxfattribs={"layer": "MP-12-ANNOTATION"})
    h.paths.add_polyline_path([T(SBX + a_, SBY), T(SBX + b_, SBY), T(SBX + b_, SBY + 1), T(SBX + a_, SBY + 1)],
                              is_closed=True)
text("GRAPHIC SCALE (feet)  |  SCALE 1:400 @ A1  |  drawing units = inches", SBX + 50, SBY - 3.5, 1.4)

# ================================================================== 9. dimensions
dim((88.77, 30), (103.77, 30), (0, 50.5))
dim((43, 150), (55, 150), (0, 152))
dim((224.88, 330), (235.48, 330), (0, 340))
dim((14.5, 44), (78.5, 44), (0, 46.5))
dim((78.5, 10), (78.5, 44), (82, 0), 90)
dim((114, 44), (178, 44), (0, 46.5))
dim((7.5, 128.5), (39, 128.5), (0, 127.3))
dim((56.5, 80), (56.5, 101.5), (54.5, 0), 90)
dim((39, 80), (39, 105.5), (41, 0), 90)
dim((56.5, 101.5), (56.5, 120.25), (54.5, 0), 90)
dim((21.52, 375.54), (47.02, 375.54), (0, 377.5))
dim((128.38, 322.06), (149.88, 322.06), (0, 319.5))
dim((cx - PLAZA_R, cy), (cx + PLAZA_R, cy), (0, cy - 2))
dim((108, 48), (194, 48), (0, 46))
dim((194, 48), (194, 114), (196, 0), 90)

# ================================================================== 10. verify
bad = [(n, round(p.difference(SITE).area, 3)) for n, p in CHECK if not p.is_empty and not SITE.buffer(1e-6).contains(p)]
for h in HOUSES:
    if not SITE.contains(h["poly"]):
        bad.append((h["id"], round(h["poly"].difference(SITE).area, 3)))
if bad:
    raise SystemExit(f"outside boundary: {bad}")
hp = [h["poly"] for h in HOUSES]
for i, a in enumerate(hp):
    for b in hp[i + 1:]:
        assert a.intersection(b).area < 0.01, "house overlap"
assert sum(1 for n, _ in CHECK if n.startswith("APARTMENT BLOCK")) == 2
built = unary_union(hp + [p for _, p, _ in APTS] + [mosque_built])
for nm, geom in (("roads", ROADS), ("lanes", LANES)):
    ov = built.intersection(geom).area
    assert ov < 0.5, f"buildings overlap {nm}: {ov}"
cats = list(AREA)
for i, a in enumerate(cats):
    for b in cats[i + 1:]:
        ov = unary_union(AREA[a]).intersection(unary_union(AREA[b])).area
        if ov > 1:
            print(f"WARNING overlap {a} / {b}: {ov:.1f}")

# ================================================================== 11. schedule
site_area = SITE.area
used = unary_union([unary_union(v) for v in AREA.values()])
ORDER = ["Cluster houses (footprints)", "Cluster courtyards (semi-private)", "Single houses (footprints)",
         "Single-house private yards & thresholds", "Apartment blocks (footprints)", "Mosque (built + sahn)",
         "Forecourts & plazas", "Community plaza (central circle)", "Central community park & playground",
         "Neighbourhood greens & tot-lots", "Pedestrian pathways (new)", "Pedestrian & service lanes",
         "Roads (vehicular / shared surface)", "Services & utilities"]
A = OrderedDict((c, unary_union(AREA[c]).area if AREA.get(c) else 0.0) for c in ORDER)
A["Green buffers & landscape margins"] = site_area - used.area
cl_n = sum(HS["cluster"].values())
s_n = sum(HS["single"].values())
apt_n = 2 * APT_FLOORS * APT_FPF
tot = cl_n + s_n + apt_n
open_sp = sum(A[k] for k in ("Cluster courtyards (semi-private)", "Community plaza (central circle)",
                             "Central community park & playground", "Neighbourhood greens & tot-lots",
                             "Green buffers & landscape margins", "Forecourts & plazas"))
builtfp = A["Cluster houses (footprints)"] + A["Single houses (footprints)"] + A["Apartment blocks (footprints)"] + \
    unary_union([mosque_built]).area
SCHED = dict(
    site_area_sqft_cad=round(site_area), site_area_acres_cad=round(site_area / 43560, 3), stated_sqft=112505,
    areas_sqft={k: round(v) for k, v in A.items()},
    areas_pct={k: round(100 * v / site_area, 1) for k, v in A.items()},
    units=OrderedDict([("Cluster 2.5 Marla", HS["cluster"]["2.5M"]), ("Cluster 3 Marla", HS["cluster"]["3M"]),
                       ("Cluster 4 Marla", HS["cluster"]["4M"]), ("Cluster total", cl_n),
                       ("Single 2.5 Marla", HS["single"]["2.5M"]), ("Single 3 Marla", HS["single"]["3M"]),
                       ("Single 4 Marla", HS["single"]["4M"]), ("Single total", s_n),
                       ("Apartments (2 blocks G+3 x 3 flats/floor)", apt_n), ("TOTAL DWELLINGS", tot)]),
    cluster_share_pct=round(100 * cl_n / tot, 1),
    ground_coverage_pct=round(100 * builtfp / site_area, 1),
    open_space_pct=round(100 * open_sp / site_area, 1),
    density_du_acre=round(tot / (site_area / 43560), 1), population_6pphh=tot * 6,
    qibla_bearing_deg=round(QIBLA, 2),
    lines_converted_to_house_polylines=n_conv, original_road_lines_kept=n_keep,
    houses=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items() if k != "poly"} for h in HOUSES],
)

LX, LY = 410, 340
LG = "MP-13-LEGEND-SCHEDULE"
text("KHOKAR TOWN LOW-INCOME HOUSING - REFINED MASTERPLAN", LX, LY, 4.0, LG, al=TA.LEFT)
text("Development of the student's site layout | Khokar Town, Lahore | drawing units: inches", LX, LY - 5, 1.7, LG,
     al=TA.LEFT)
yy = LY - 14
text("ZONING LEGEND", LX, yy, 2.8, LG, al=TA.LEFT); yy -= 6
LEG = [("MP-03-CLUSTER-HOUSE-2.5M", "Cluster house 2.5 Marla (private)"),
       ("MP-03-CLUSTER-HOUSE-3M", "Cluster house 3 Marla (private)"),
       ("MP-03-CLUSTER-HOUSE-4M", "Cluster house 4 Marla (private)"),
       ("MP-03A-CLUSTER-COURTYARDS", "Cluster courtyard (semi-private)"),
       ("MP-04-SINGLE-HOUSE-3M", "Single houses 2.5 / 3 / 4 Marla (private)"),
       ("MP-04A-SINGLE-HOUSE-PLOTS", "Single-house threshold & rear yard (private)"),
       ("MP-02-APARTMENT-BLOCKS", "Apartment blocks 01 & 02 (G+3)"),
       ("MP-05-MOSQUE", "Mosque (Qibla-oriented)"),
       ("MP-06-COMMUNITY-PLAZA-GATHERING", "Community plaza / gathering (public)"),
       ("MP-07-PARKS-GREEN-SPACES", "Park, playground & neighbourhood greens (public)"),
       ("MP-08-PEDESTRIAN-PATHWAYS", "Pedestrian paths, lanes & forecourts (semi-public)"),
       ("MP-09-ROADS-CIRCULATION", "Streets - vehicular / shared surface (public)"),
       ("MP-10-SERVICES-UTILITIES", "Services & utilities")]
for lay, lab in LEG:
    sw = R(LX, yy - 1.8, LX + 7, yy + 2)
    hatch(sw, lay); pl(cs(sw), lay)
    text(lab, LX + 10, yy, 1.8, LG, al=TA.MIDDLE_LEFT); yy -= 5.2
ln((LX, yy + .2), (LX + 7, yy + .2), "MP-01-SITE-BOUNDARY")
text("Site boundary - original, unchanged", LX + 10, yy + .2, 1.8, LG, al=TA.MIDDLE_LEFT); yy -= 10


def row(c1, c2, c3):
    global yy
    text(c1, LX, yy, 1.75, LG, al=TA.MIDDLE_LEFT)
    text(c2, LX + 74, yy, 1.75, LG, al=TA.MIDDLE_RIGHT)
    text(c3, LX + 90, yy, 1.75, LG, al=TA.MIDDLE_RIGHT)
    ln((LX, yy - 2), (LX + 92, yy - 2), LG)
    yy -= 4.2


text("AREA DISTRIBUTION SCHEDULE", LX, yy, 2.8, LG, al=TA.LEFT); yy -= 5.5
row("LAND USE", "AREA (sq ft)", "%")
for k, v in A.items():
    row(k, f"{v:,.0f}", f"{100 * v / site_area:.1f}")
row("TOTAL - site as drawn in CAD", f"{site_area:,.0f}", "100.0")
text(f"Brief states 112,505 sq ft; CAD boundary measures {site_area:,.0f} sq ft ({site_area / 43560:.2f} ac).",
     LX, yy, 1.4, LG, al=TA.LEFT); yy -= 3.4
text(f"Ground coverage {SCHED['ground_coverage_pct']}% | open & green {SCHED['open_space_pct']}% | "
     f"{SCHED['density_du_acre']} DU/acre | ~{tot * 6} people", LX, yy, 1.4, LG, al=TA.LEFT); yy -= 8

text("HOUSING UNIT COUNT", LX, yy, 2.8, LG, al=TA.LEFT); yy -= 5.5
row("TYPOLOGY  (1 Marla = 225 sq ft)", "UNITS", "SIZE")
row("Cluster house 2.5 Marla", f"{HS['cluster']['2.5M']}", "18'9\"x31'6\"")
row("Cluster house 3 Marla", f"{HS['cluster']['3M']}", "21'6\"x31'6\"")
row("Cluster house 4 Marla", f"{HS['cluster']['4M']}", "25'6\"x35'6\"")
row("CLUSTER HOUSING (dominant)", f"{cl_n}", f"{100 * cl_n / tot:.0f}%")
row("Single house 2.5 Marla", f"{HS['single']['2.5M']}", "18'9\"x31'6\"")
row("Single house 3 Marla", f"{HS['single']['3M']}", "21'6\"x31'6\"")
row("Single house 4 Marla", f"{HS['single']['4M']}", "25'6\"x35'6\"")
row("SINGLE HOUSING (was 3)", f"{s_n}", f"{100 * s_n / tot:.0f}%")
row("Apartment Block 01 + 02 (G+3, 3 flats/floor)", f"{apt_n}", f"{100 * apt_n / tot:.0f}%")
row("TOTAL DWELLING UNITS", f"{tot}", "")
yy -= 3
NOTES = ["NOTES",
         "1. Boundary, its 7 dimensions and all student road/lane edges, arcs and circle are the source entities, unchanged.",
         "2. Student's 44 houses redrawn as closed polylines at identical coordinates; 6 pinwheel middle units widened",
         "   2'-9\" into their courtyard to form the 3 Marla type (not present in source drawing).",
         "3. North assumed = +Y of drawing (no north point / geo-reference in file). Qibla "
         f"{QIBLA:.1f} deg from true north - re-check on survey.",
         "4. External road edges are indicative only. 15' streets / 10'-7\" north lane are the student's widths.",
         "5. No dedicated parking area. Streets: access, drop-off, emergency and service only.",
         "6. Hierarchy: public (streets, plaza, park, mosque forecourt) > semi-public (lanes, greens, link) >",
         "   semi-private (cluster courtyards) > private (houses, single-house thresholds/yards)."]
for n_ in NOTES:
    text(n_, LX, yy, 1.9 if n_ == "NOTES" else 1.35, LG, al=TA.LEFT); yy -= 3.3

doc.saveas(OUT)
json.dump(SCHED, open(OUT.rsplit(".", 1)[0] + "_schedule.json", "w"), indent=1)
print(json.dumps({k: v for k, v in SCHED.items() if k != "houses"}, indent=1))

if PNG:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    d2 = ezdxf.readfile(OUT)
    fig = plt.figure(figsize=(30, 20))
    ax = fig.add_axes([0, 0, 1, 1])
    Frontend(RenderContext(d2), MatplotlibBackend(ax),
             config=Configuration(background_policy=BackgroundPolicy.WHITE, lineweight_scaling=0.5)
             ).draw_layout(d2.modelspace(), finalize=True)
    fig.savefig(PNG, dpi=120, facecolor="white")
