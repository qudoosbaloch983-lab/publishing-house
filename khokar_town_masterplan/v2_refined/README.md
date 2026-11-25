# Khokar Town Low-Income Housing — Refined Masterplan (v2)

This develops the student's own layout (`site_khoker_v2_input.dxf`). It does not start again.

| File | |
|---|---|
| `Khokar_Town_Masterplan_v2.dxf` | **Final editable CAD drawing** (AutoCAD 2018 DXF, units = inches). Open in AutoCAD and use `SAVEAS` → DWG; a DWG converter isn't available in this environment. |
| `Khokar_Town_Masterplan_v2_preview.png` | Preview render |
| `Khokar_Town_Masterplan_v2_schedule.json` | Areas, unit counts, every house (id, type, coordinates, origin) |
| `refine_masterplan.py` | Script that builds the DXF on top of the input file |
| `site_khoker_v2_input.dxf` | The student's DXF (input, untouched) |

```bash
pip install ezdxf shapely matplotlib
```
```bash
python refine_masterplan.py site_khoker_v2_input.dxf Khokar_Town_Masterplan_v2.dxf preview.png
```

## 1. Analysis of the input drawing
* **Units:** inches. **Boundary:** one closed 8-vertex polyline (`1.WALLS`) with 7 dimensions. The shape matches the earlier site file exactly, but the whole drawing has been **moved by (+12,972.60", +7,482.23")**. This file's coordinates are used throughout.
* **Area from the CAD boundary:** **113,979 sq ft (2.62 ac)**. The brief says 112,505 sq ft.
* **Student design** (layer `2`: 380 lines, 2 arcs, 1 circle):
  * **Streets:** a 15' entry street from the south ending in a roundabout (outer R 47'-11½"), around a central circle (R 32'-11½"). A 15' east–west internal street.
  * **Lanes:** north–south lanes 9'–12' wide. The **10'-7" lane at x≈225–235'** is the only opening onto the north boundary apart from the east service lane, so it is taken as the secondary entrance.
  * **44 houses** drawn as double lines (9" walls):
    * 4 Marla: 25'-6" × 35'-6" (905 sq ft), 20 units.
    * 2.5 Marla: 18'-9" × 31'-6" (591 sq ft), 24 units.
    * **No 3 Marla house exists in the drawing.**
  * **Clusters:** A (2 rows of 3), B and C (10-house pinwheels), D (half pinwheel beside the roundabout), E (10-house pinwheel), and 3 single houses at the west edge.
  * **Empty:** the whole south leg (about 190' × 170'), apart from the entry street.

## 2. What was kept (unchanged geometry)
* The boundary and its 7 dimensions, vertex for vertex.
* All 34 of the student's road and lane edge lines, the 2 roundabout arcs and the central circle. They are only moved to new layers (`MP-09A-ORIGINAL-ROAD-EDGES`, `MP-06-…`).
* Both entrance positions: the south entry street and the north lane.
* 38 of the 44 houses at identical coordinates. They are converted from loose lines to **closed polylines** (outer and inner wall faces) on typology layers.

## 3. What was refined or added, and why
| Change | Reason |
|---|---|
| 6 pinwheel "middle" units (B ×2, C ×2, E ×2) widened 2'-9" into their own courtyard, giving **21'-6" × 31'-6" = 677 sq ft (3 Marla)** | The brief needs 3 Marla cluster houses and the drawing had none. Each courtyard keeps a 28' clear width. |
| Each cluster's open space defined as a **semi-private courtyard** with a name and a centre feature (A Neem Court: tree platform; B Shisham Court: hand pump / wash slab; C Amaltas Court: play patch; D Jaman Court: opens onto the plaza green; E Kachnar Court: kitchen-garden beds). Every front door is marked facing the courtyard. | Clear house-to-courtyard relationship and a distinct identity for each cluster, without moving the student's houses. |
| **Single-housing zone** in the south-west: a new 12' lane joining the roundabout and the entry street. The student's 3 units now front it, and 10 new terraced units are added (west and east rows) with front thresholds and rear light yards. | Increase from **3 to 13**, using 2.5 / 3 / 4 Marla sizes consistent with the student's own dimensions. No wasted gaps between houses. |
| **Apartment Block 01 and 02** (G+3, 3 flats per floor, ~510 sq ft, north access gallery) on either side of the main entrance | Frame the south gateway on the street frontage. Their winter shadows fall on the street, greens and park, not on cluster courtyards. |
| **Mosque**: prayer hall ~1,280 sq ft (~150 worshippers plus a women's mezzanine), sahn (~100 overflow), wuzu and WC block, minaret, and a forecourt for gatherings | On the civic spine between the park and the central plaza, so it is reachable from every zone and away from private courtyards. The hall is turned to the **Qibla: 260.4° from north** (great-circle bearing from Lahore). |
| Central circle becomes the **Community Plaza (chowk)**: shade-tree platform, seating ring, ring of trees. The roundabout becomes a raised shared-surface ring with zebra tables. | Gives the student's circle a clear civic function and puts pedestrians first. |
| **Central community park** with children's playground, pavilion and walking loop. **Neighbourhood greens** (tot-lot in the south-west, plaza green). **Green link** from the north gate to the south-east cluster. Green buffers along the edges. | A connected open-space system, used strategically rather than greening the whole site. |
| **Civic spine** footpath from Street No. 10 to the plaza, and a park–mosque walk | Primary pedestrian route. Lanes and courtyard gateways form the secondary and tertiary routes. |
| **Services**: substation (PMT), tube well and waste point on Street No. 10; overhead water tank in the plaza green | Service access from the street without entering the residential lanes. |

**Space hierarchy:**
- **Public:** streets, plaza, park, mosque forecourt.
- **Semi-public:** lanes, greens, green link.
- **Semi-private:** cluster courtyards.
- **Private:** houses, single-house thresholds and yards.

## 4. Housing unit count (1 Marla = 225 sq ft)
| Typology | Size | Cluster | Single | Total |
|---|---|---:|---:|---:|
| 2.5 Marla | 18'-9" × 31'-6" | 17 | 6 | 23 |
| 3 Marla | 21'-6" × 31'-6" | 6 | 4 | 10 |
| 4 Marla | 25'-6" × 35'-6" | 18 | 3 | 21 |
| Apartments, Blocks 01 + 02 (G+3 × 3 flats per floor) | ~510 sq ft | | | 24 |
| **Total** | | **41 (53%)** | **13** | **78** |

Density is 29.8 dwellings per acre, about 468 people at 6 per household. Ground coverage is 39.7%; open and green space is 38.7%.

## 5. Area distribution (sq ft, of the 113,979 sq ft CAD site)
| Land use | Area | % |
|---|---:|---:|
| Cluster houses (footprints) | 30,399 | 26.7 |
| Cluster courtyards (semi-private) | 14,835 | 13.0 |
| Single houses (footprints) | 8,968 | 7.9 |
| Single-house yards & thresholds | 1,067 | 0.9 |
| Apartment blocks (footprints) | 4,352 | 3.8 |
| Mosque (built + sahn) | 2,367 | 2.1 |
| Forecourts & plazas | 3,122 | 2.7 |
| Community plaza (central circle) | 3,412 | 3.0 |
| Central community park & playground | 5,676 | 5.0 |
| Neighbourhood greens & tot-lots | 4,255 | 3.7 |
| Pedestrian pathways (new) | 2,380 | 2.1 |
| Pedestrian & service lanes | 5,569 | 4.9 |
| Roads (vehicular / shared surface) | 14,241 | 12.5 |
| Services & utilities | 492 | 0.4 |
| Green buffers & landscape margins | 12,843 | 11.3 |

(Exact figures are in the schedule JSON and in the drawing.)

## 6. Missing or unverified information (not invented)
1. **True north:** the file has no north point or geo-reference. North is assumed to be +Y, so the **Qibla orientation must be re-checked against a survey north point** before construction.
2. **Site area:** the CAD boundary gives 113,979 sq ft against 112,505 sq ft in the brief (+1.3%).
3. **Marla standard:** 225 sq ft is assumed. On the 272.25 sq ft standard, the student's 24' × 34' interior would read as 3 Marla instead.
4. **External roads:** Street No. 10 and the Connecting Road are not drawn in the file. They are shown as indicative only, and their widths are unknown.
5. **Street widths** are the student's (15' streets, 10'-7" north lane). These are narrow for fire-tender access; confirm with the LDA / authority bye-laws.
6. **East service lane:** it meets the inner southern boundary at y≈164'. What lies beyond is unknown.
7. **Building heights:** cluster houses are assumed G+1 and the apartments G+3. No survey levels are given.

## 7. Verification (checked programmatically against the input file)
- [x] Boundary identical vertex for vertex; original 7 dimensions kept
- [x] Exactly two apartment buildings: APARTMENT BLOCK 01 and 02
- [x] Cluster housing dominant (41 of 78 units, and the largest land use)
- [x] Single houses increased from 3 to 13
- [x] 2.5, 3 and 4 Marla all present
- [x] Exactly one mosque, Qibla-oriented, with forecourt and wuzu
- [x] Central park, neighbourhood greens, playground, plaza and gathering spaces
- [x] Main entrance (south) and secondary entrance (north) kept at the student's positions
- [x] No dedicated parking area
- [x] All buildings inside the boundary; no building overlaps another, a street or a lane; DXF audit reports 0 errors
