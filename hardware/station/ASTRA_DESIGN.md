**Recommendation: build “KornKlapp” — an A4 containment tray with a manual spreading paddle, folding camera stand and removable diffuse hood.** The entire random handful stays together throughout counting and weighing. No cavities, sieves or size-dependent passages.

The repository supports this direction: `adaptive.py` benefits from a clean white background; `blobs.py` distinguishes isolated grains from difficult clusters. However, `agreement.py` explicitly labels its thresholds uncalibrated, and `docs/RESULTS.md` contains development results rather than demonstrated 99.9% accuracy. Hardware benefits below are design hypotheses requiring testing.

**Three concepts**

Costs are engineering estimates in EUR, excluding VAT, phone and scale. Prototype figures assume self-assembly; 1,000-piece figures include assembly and modest fabrication setup.

| Concept | Operation and accuracy levers | Farm suitability and manufacture | Prototype / each at 1,000; principal risks |
|---|---|---|---|
| **A. KornKlapp field tray** | A4 paper in a shallow sealed tray; silicone paddle separates contacts; overhead stand fixes framing and reduces movement. Addresses **contacts, perspective, blur and sample loss**. | Large glove-friendly controls; removable washable tray; stand folds for cab storage. Prototype: sheet aluminium, PP and printed brackets. Series: fabricated sheet parts; moulded brackets later. | **€55–90 / €25–38.** Manual separation takes time; dense oats remain difficult; rim shadows need attention. |
| **B. Hand-cranked spreading platform** | A4 tray on four elastomer mounts; crank eccentric produces approximately **1–2 mm horizontal travel at 2–4 Hz**. Stop and lock before photographing. Addresses **contacts and loss**. | No batteries; enclosed crank tolerates gloves. Approximately **320 × 400 × 70 mm**. Printed mechanism and aluminium base; moulded housing later. More joints to clean. | **€85–140 / €40–65.** Motion may create edge piles, align awned grains or segregate sizes spatially. Separation effectiveness is unverified; never discard any resulting fraction. |
| **C. Folding daylight hood** | Translucent walls and roof surround A4; camera looks through a roof aperture. Addresses **shadows, glare and wind**; optional phone bridge reduces blur. | Wipe-clean PP panels, flat storage, large tabs. Knife-cut prototype; die-cut production. | **€20–40 / €8–16.** Does not separate grains or securely transfer them. Reduces available light; cannot solve a dark barn without an external light source. |

Choose **A with C’s removable hood**. It tackles the largest error source directly while improving capture consistency. Its separation action is visible and controllable; the shaker needs substantial experimentation before it earns its complexity.

**Build specification — all dimensions in mm**

Use the paper centre as **(0,0,0)**; x spans its 210-mm width, y its 297-mm length. Dimensions below are nominal CAD parameters.

| Part | Geometry, material and construction |
|---|---|
| **Base** | **300 × 380 × 2** aluminium plate, corner radius **8**, deburred edges; matte charcoal finish. Four silicone feet **Ø20 × 4**. Target assembled mass **1.2–1.6 kg**; packed envelope approximately **300 × 380 × 55**. |
| **Removable sample cassette** | Outer **230 × 317**, continuous **2-mm PP floor**; internal clear area **212 × 299**. Rim **8 high × 2 thick**, inside corner radius **1**, outside radius **3**. Full white **210 × 297** paper lies flat on a reusable low-tack backing; no clips obscure its corners. The 1-mm perimeter clearance must remain visible and empty before capture. No floor hinge or grain-contact screw holes. |
| **Spreading paddle** | Handle **100 × 22 × 6**; replaceable silicone blade **60 × 20 × 1**, with one rounded **4-mm-wide tip** for nudging individual contacts apart. Smooth paper surface: no grooves, pits or coarse texture that could trap small grains or generate shadows. |
| **Camera gantry** | Two aluminium telescoping posts at **x = ±140, y = 80**. Outer tubes **20 × 20 × 1.5**, length **200**; inner tubes **16 × 16 × 1.5**, length **220**. Crossbar **280 × 20 × 20**. M5 clamps with **30-mm knobs**; minimum tube overlap **60**. Set the actual lens height to **340**. |
| **Fold mechanism** | Each post pivots toward negative y on an **M5 pin**, with a positive 90° stop and locking knob. Printed hinge cheeks **5 thick**, pin bores **5.3**, mating clearance **0.4**. Telescope down and remove crossbar before folding. Hinges stay outside the sample cassette. |
| **Phone rest** | PETG plate **115 × 200 × 4**, underside ribs **6 high × 4 thick**; open **65 × 65 corner notch** for the camera cluster. Three adjustable padded edge stops and a **15-mm silicone retention strap**. Slotted mounting allows **±30 x / ±40 y** adjustment: centre the selected **lens**, not the phone. Interchangeable tablet plate **230 × 310 × 4**, same notch and **10-mm ribs**; proof-load gantry with **1 kg** before mounting an iPad. |
| **Hood** | Four **0.5-mm translucent white PP** walls: two **300 × 300**, two **380 × 300**; roof **300 × 380** with central **100 × 100** aperture. Flexible taped hinges, overlapping seams and **25-mm pull tabs**. Roof sits at **z = 300**. Front opens completely for spreading. Panels unclip and fold flat. |
| **Transfer assembly** | Front rim has a **40-wide × 8-high** opening, closed during imaging by a removable gasketed plug. Clip-on spout: **40-wide inlet**, **50 length**, tapering to **30-mm outlet**. A retaining collar secures a removable **250-ml PP cup** around the outlet during pouring. Exposed joints must open fully for inspection and washing. |

Prototype tonight with cut sheet materials and printed small fittings; avoid printing the entire A4 floor. Production can retain sheet fabrication at 1,000 units. Injection moulding needs separate quotations: tooling can dominate costs at this volume. [Manufacturing cost guidance](https://di1vc2liilbw2.cloudfront.net/guides/injection-molding/)

**Camera geometry**

For a **26-mm-equivalent lens**, assuming diagonal equivalence and a full **4:3 portrait photograph**, the calculated field at **340 mm** is approximately **339 × 453 mm**. This covers the base with approximately **20 mm horizontal and 36 mm vertical margin per side**. The calculation follows standard field-of-view geometry; actual processing crops and lens distortion require checking on the intended device. [Optical geometry](https://www.edmundoptics.com/knowledge-center/tech-tools/imaging-system-parameter-calculator/)

A **13-mm-equivalent ultra-wide** would give approximately the same field at **170 mm**, but that conflicts with this hood. Use the main camera at 340 mm; ultra-wide at that height wastes image resolution on surroundings. Provide **320–380 mm** height adjustment, disable digital zoom, and verify all four corners in preview.

**Fiducials and software**

Place four **ArUco DICT_4X4_50** markers, IDs **0–3**, clockwise from upper-left. Centres: **(−125,+170), (+125,+170), (+125,−170), (−125,−170)**. Each black square is **18 × 18**, surrounded by a **3-mm white quiet zone**. Shim their printed surfaces to the paper plane within **±0.25 mm**; use matte, replaceable labels.

Tonight, the tool works through ordinary photographs and existing A4 detection. Marker support is an **optional software addition**, not present in the three inspected modules: known corner coordinates enable planar rectification; explicitly exclude marker regions from counting. Four distributed markers provide a stronger geometric reference than one corner marker. [OpenCV board documentation](https://github.com/opencv/opencv/blob/5.x/doc/tutorials/objdetect/aruco_board_detection/aruco_board_detection.markdown)

Fixed height improves repeatability; it does **not** establish universal pixels/mm across devices. Avoid white hardware surrounding the sheet: it could contaminate the bright-region area estimate in `adaptive.py`.

**Winner BOM**

| Item | Prototype | Each at 1,000 |
|---|---:|---:|
| Base, cassette and rim | €22 | €7 |
| Gantry tubes | €16 | €8 |
| Printed/moulded fittings and phone rest | €8 | €4 |
| Hood | €10 | €4 |
| Spout, plug and cup | €7 | €3 |
| Fasteners, pads, paddle and strap | €12 | €6 |
| Paper and markers | €3 | €1 |
| Assembly and setup allowance | DIY | €11 |
| **Total** | **€78** | **€44** |

Allow roughly **±30%** pending supplier quotes; tablet rest adds approximately **€8 / €4**.

**Farmer workflow — six steps**

1. Unfold on a stationary surface; fit clean paper and tare the empty cup.
2. Put the **entire random handful** onto the paper.
3. Spread gently; use the paddle to separate contacts and return edge grains onto A4.
4. Close hood, photograph, inspect the count overlay; reposition contacts and repeat if needed.
5. Remove cassette, dock cup, open plug and tilt **40–60°**. Sweep remaining grains through; inspect paper, corners, plug and spout before weighing.
6. Enter sample mass and germination; read TKW and kg/ha, then return the cup contents to the sack.

Transfer is designed to prevent loss, but requires that final visual check. Chaff and broken kernels remain with the sample: because challenge counting excludes them, appreciable contamination makes gross-mass TKW biased and must be flagged.

Before claiming improvement, compare identical handfuls on bare paper and KornKlapp, including dense oats, and check count error, contacts, capture time and retained grains. **99.9% remains a target.**

**Pitch:** „Eine zufällige Handvoll aufs Blatt, fotografieren, wiegen – KornKlapp hält die Probe zusammen und macht daraus mit Tausendkorn Ihre Aussaatmenge.“

- **Weniger Kornkontakte:** gezielt auseinanderstreichen, ohne Größen auszuwählen.
- **Verlässlichere Fotos:** feste Kameraposition, sichtbares A4 und diffuseres Licht.
- **Dieselbe Probe bis zur Waage:** Rand, Ausgießer und befestigter Becher halten sie zusammen.