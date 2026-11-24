# Khokar Town Low-Income Housing — Masterplan (editable DXF)

> "Transforming isolated housing into an interconnected habitat where home, work, community and nature coexist."

| File | What it is |
|---|---|
| `Khokar_Town_Masterplan.dxf` | Editable 2D masterplan (AutoCAD 2018 DXF, units = inches). Open in AutoCAD and `SAVEAS` → DWG. |
| `Khokar_Town_Masterplan_preview.png` | Preview render |
| `Khokar_Town_Masterplan_schedule.json` | Area schedule, unit counts, per-house list |
| `generate_masterplan.py` | Script that builds the DXF on top of the site file |
| `site_khoker.dxf` | Original site file (input) |

## Regenerate
```bash
pip install ezdxf shapely matplotlib
```
```bash
python generate_masterplan.py site_khoker.dxf Khokar_Town_Masterplan.dxf Khokar_Town_Masterplan_preview.png
```

## Site (from the CAD file)
* One closed boundary polyline with 8 vertices (the last repeats the first) and 7 dimensions: 350'-3", 32'-7" (chamfer), 365'-2", 192'-7", 171'-11", 167'-11", 222'-5".
* Area computed from the boundary: **113,979 sq ft (2.62 ac)**. The brief states 112,505 sq ft (about 1.3 % less). The CAD geometry is used as drawn.
* The masterplan is drawn **inside the original file**. The boundary polyline and its 7 dimensions are the source entities, unchanged vertex for vertex (only moved to layer `MP-01-SITE-BOUNDARY` / `MP-11-DIMENSIONS`). The script checks this and aborts if any element falls outside the boundary.
* North = +Y. The source file contains **no road or context lines**, so Street No. 10 and the Connecting Road are drawn as *indicative* lines on `MP-00-CONTEXT-INDICATIVE`. Verify them on site.

## Layers
`MP-01-SITE-BOUNDARY`, `MP-02-APARTMENTS`, `MP-03-CLUSTER-HOUSES`, `MP-03A-CLUSTER-COURTYARDS`, `MP-04-SINGLE-HOUSES`, `MP-05-COMMERCIAL`, `MP-06-COMMUNITY-FACILITIES`, `MP-07-PARKS-LANDSCAPE`, `MP-08-PEDESTRIAN-PATHWAYS`, `MP-09-ROADS-CIRCULATION`, `MP-10-SERVICES-UTILITIES`, `MP-11-DIMENSIONS`, `MP-12-ANNOTATION`, `MP-13-LEGEND-SCHEDULE`, `MP-00-CONTEXT-INDICATIVE`. Each coloured zone also has a `…-FILL` hatch layer that can be frozen for line-only plots.

## Planning concept
* **South leg (192 ft on Street No. 10):** main gate, with a neighbourhood market (10 shops, 6 ft arcade) on both sides of an entrance plaza / community square. Shops face the street, so market traffic never enters the housing. Behind are the community centre (G+1 hall, skills workshop, clinic), a gathering court and **Apartment Block A** (the south gateway). A pedestrian green spine runs north from the plaza to the park. The west edge holds 5 **single 5 Marla houses** on the main street and a services strip (overhead tank, tube well, substation, waste/recycling, rain-water recharge, compost/nursery).
* **Knee of the L:** an east–west internal service street (24 ft). The **central community park and children's playground** sit at the centre of the L, the most connected point.
* **North band:** five courtyard clusters on the park and pedestrian lanes. **Apartment Block B** marks the north gate. Both blocks are placed so their winter shadows fall on streets or commons, not on houses.
* **Cluster logic:** front doors open onto a *shared courtyard* (semi-private) and rears onto a *service lane or street*, which separates pedestrian and service movement and gives every house cross-ventilation. Alternate footprints step back 1'-6" to break up the courtyard façades. The clusters vary: E–W courtyards (C1, C2, C3, C5) and a U-cluster opening onto the park (C4).
* No dedicated parking area. Streets allow drop-off, emergency and service access only.

## Housing unit count
| Typology | Units | Plot |
|---|---:|---|
| Cluster 2.5 Marla (C2, C4) | 14 | 562.5 sq ft |
| Cluster 3 Marla (C1, C3) | 18 | 675 sq ft |
| Cluster 4 Marla (C5) | 8 | 900 sq ft |
| **Cluster sub-total** | **40 (58 %)** | |
| Apartments: 2 blocks × G+3 × 3 flats/floor | 24 | ~700 sq ft flats |
| Single houses 5 Marla | 5 | 1,128 sq ft |
| **Total dwellings** | **69** | 26.4 DU/acre, ~414 people |

## Area distribution (sq ft, of the 113,979 sq ft drawn site)
| Land use | Area | % |
|---|---:|---:|
| Cluster housing plots | 27,225 | 23.9 |
| Cluster shared courtyards | 10,328 | 9.1 |
| Apartment building footprints | 5,412 | 4.7 |
| Single housing plots | 5,640 | 4.9 |
| Commercial market | 4,284 | 3.8 |
| Community centre | 2,048 | 1.8 |
| Entrance plaza & community square | 1,040 | 0.9 |
| Shared gathering spaces | 5,220 | 4.6 |
| Central park & playground | 8,624 | 7.6 |
| Parks, gardens & landscape buffers | 17,606 | 15.4 |
| Pedestrian pathways | 5,186 | 4.6 |
| Roads & vehicular circulation | 17,447 | 15.3 |
| Services & utilities | 3,918 | 3.4 |

Cluster land (plots + courtyards) is 37,553 sq ft, about 5× the apartment land (7,752 sq ft including its commons).

## Final checklist
- [x] Original boundary unchanged (vertices compared programmatically against the source)
- [x] Exactly two apartment buildings (A, B)
- [x] Cluster housing is the majority (40 of 69 units, and the largest land use)
- [x] 2.5, 3 and 4 Marla cluster houses all present
- [x] Single housing units included (5 × 5 Marla)
- [x] Central park, playground, community centre, gathering spaces and market included
- [x] Main entrance from Street No. 10 (south); secondary entrance from the Connecting Road (north)
- [x] No dedicated parking area
