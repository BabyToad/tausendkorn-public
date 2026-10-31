**Build v1 as a shallow, removable 500-well wheat cassette, used twice. Print a small filling trial before committing to the full cassette.** The concept is credible, but v0 does not establish reliable singulation—and a perfectly counted, size-selected sample can still give the wrong TKW.

I read the brief, build script and challenge rules. Dimensions below are **prototype starting values, not validated performance specifications**.

1. **The biggest risk is selective sampling, not empty wells.**

   Large kernels may never enter; small kernels may enter more readily, settle underneath others or survive pouring better. The resulting 1000 kernels can have a biased mean weight even when their count is correct. Your pregraded seed helps, but does not eliminate this.

   Take a mixed sample from several locations in the lot, then feed the pan from that sample. A scoop from the accessible surface of a trailer is not enough to establish representative TKW. Official seed-testing guidance likewise stresses sampling across multiple locations. [Minnesota Department of Agriculture](https://www.mda.state.mn.us/testing-services-submissions)

   Validate the pan against **randomly hand-counted samples from the same mixed material**, comparing TKW as well as count. Examine the overflow: persistent enrichment in large, small or shrivelled kernels is a failure.

2. **Scooping, shaking and removing surplus can work—but v0’s deep rectangular grid is a poor starting geometry.**

   Commercial counting boards use this general workflow, with hole sizes chosen for the seed. That supports the principle, not the reliability of these dimensions. [Hoffman counting boards](https://www.hoffmanmfg.com/products/seed-counting-and-planting-trays/)

   In your script, the rendered kernels are identical **3.2 × 6.6 × 2.8 mm** objects placed directly into wells. Some sites are deliberately left empty. There is no filling simulation, size distribution, double occupancy or broken material.

   My wheat starting geometry:

   - **Elongated rounded rectangle:** 4.4 × 8.2 mm seating opening, 1.0 mm corner radius. Rounded corners remove fragment traps while retaining room for blunt kernels. A full capsule may constrain broad kernel ends; a teardrop introduces unnecessary head/tail orientation and a pointed trap.
   - **Depth 1.8 mm**, reduced from 3.0 mm. Normal kernels protrude, making stacked kernels more exposed and allowing light into the well. Test 1.6, 1.8 and 2.0 mm; shallower wells also increase spill risk.
   - **Ribs 1.2 mm below the chamfer**, with 0.4 × 0.4 mm, 45° chamfers on both edges. This leaves a 0.4 mm crest instead of a broad parking surface. Chamfer intersections too.
   - **Flat floor and vertical lower walls for tonight.** FDM needs no mould-release draft. The entry chamfer provides the useful lead-in; a deep funnel encourages wedging.
   - Keep the **long axis parallel to the forward pouring direction**, as in v0. It gives flowing kernels an opportunity to align. Use small sideways and circular movements during filling.

   Two shrivelled kernels can still fit beside one another, and a fragment can hide beneath an intact kernel. Larger openings improve acceptance of large kernels but increase doubles. **There is no universal passive well that resolves that trade-off for every lot.**

3. **A photograph cannot verify a kernel that is completely hidden under another.**

   Empty cells are relatively easy. Overlapping doubles and fragments underneath kernels are fundamentally harder; an overhead silhouette can be indistinguishable from a single kernel.

   Define the target precisely:

   - **99.9% count accuracy** permits one error per 1000.
   - **99.9% probability of an exactly correct batch** is much stricter.
   - If each of 1000 cells were independently correct with probability 99.9%, only \(0.999^{1000}\approx36.8\%\) of trays would be entirely correct.

   The app should identify **empty / single / suspicious / unknown**, inspect ribs and borders for loose kernels, and require correction of suspicious cells before accepting an exact-count batch. A second oblique image can help expose stacks, but cannot guarantee detection of complete occlusion.

   Follow the challenge definition: intact shrivelled kernels count; broken kernels do not. **Remove excluded material physically before weighing.** Excluding a fragment from the image count while leaving its mass in the pan inflates TKW.

4. **500 × 2 is the best first farmer version; 100 wells is the best first physical experiment.**

   | Configuration | Advantage | Main cost | Recommendation |
   |---|---|---|---|
   | 1000 in one pan | One fill, photo and weighing | Large print, wrist torque, more cells to inspect | Later, after geometry validation |
   | 500, used twice | Smaller cassette; easier printing, handling and imaging | Two verified batches | **Farmer v1** |
   | 100, used eight times | Small hardware; replicate weights reveal variation | Eight fills and separate weighings; finer scale desirable | Lab workflow / validation |
   | 100, used ten times | Exactly 1000 kernels with minimal hardware | Too many handling steps for routine use | Tonight’s fallback |

   ISTA’s published guidance includes eight separately weighed 100-seed replicates, calculation of variability, and additional replicates when limits are exceeded. Eight sectors photographed together are not equivalent to eight separately weighed replicates. Do not present the prototype as ISTA-compliant solely because it has 100-well modules. [ISTA laboratory guidelines, §7.5](https://www.seedtest.org/api/rm/2346XE3QX287V56/guidelines-for-the-establishment-and-management-of.pdf)

   The v0 insert is **237.2 × 246.7 mm**; the body is **242 × 296.5 mm**, excluding the handle. Its insert geometry alone represents approximately **222 g of solid PLA**, before slicer infill choices. The 45 g of wheat is a minority of the handled mass.

   One-handed carrying is plausible. Repeated controlled shaking from the rear handle is less attractive: a hypothetical 400 g assembly with its centre of mass 180 mm from the hand produces approximately **0.71 N·m static wrist torque**, before shaking.

5. **Make loading controlled; avoid pushing the precision cassette deep into a sack.**

   Use a small scoop to load from the mixed sample bowl. The pan’s lip remains useful for shallow scooping and returning surplus, but a wide cassette pushed into packed seed creates unnecessary force and flooding.

   Concrete ergonomic changes:

   - Separate **25 mm loading/discharge apron**, with a rounded, approximately 0.8 mm leading edge and a smooth transition to the insert.
   - Remove the raised obstacle across the discharge path. Retain the cassette using side clips instead.
   - Reduce walls from 22 to **12 mm above the cassette**, retaining taller walls only if trials show spilling.
   - Use a detachable **110 × 34 × 18 mm rounded handle**, rising 10–15°, with a thumb rest and reinforced, mechanically fastened root.
   - Add a front underside finger support for two-handed shaking. Keep the rear handle for carrying and pouring.
   - Pour surplus into a **wide catch bowl beneath the entire front edge**. Do not depend on hitting a narrow sack mouth.

   Starting motion to test: nearly level, 5–10 mm horizontal strokes at roughly 2–3 Hz, then progressively tilt forward with gentle taps. Establish experimentally whether surplus clears **before seated kernels escape**. If those operating ranges overlap badly, revise the geometry; do not compensate with stronger shaking.

6. **Build a simple photo station; shallow wells matter more than elaborate lighting.**

   Use an independent phone/iPad stand, starting approximately **300–400 mm above the cassette**, with the main camera perpendicular and the whole cassette filling most of the image. Adjust height for the actual camera. Capture at original resolution; aim for at least roughly **20 pixels across the narrowest kernel** in the processed crop.

   Replace four identical white squares with orientation-distinguishable fiducials. Include cassette/species identity and known grid geometry. Keep markers flush and outside the grain field.

   Matte charcoal is a good starting background for pale wheat. For darker rye, durum or treated seed, test **matte light grey or blue** against actual kernels. Avoid glossy filament, direct flash and a single low-angle lamp; use broad diffuse illumination from two sides. “Matte” should describe optical behaviour, not a rough surface that catches husks.

   Backlighting is a worthwhile later experiment: an opaque perforated grid over a translucent floor could produce clear occupancy silhouettes. It requires a light source and access through the carrier floor, and does not resolve overlapping doubles. **Skip it for tonight’s first build.**

   The existing A4-image evaluation remains necessary. Pan photos introduce a new background, grid and occlusion pattern; performance on the challenge’s `count_1000` split does not validate pan inspection.

7. **Weigh the removable cassette directly, with a fresh tare.**

   Engraved tare is an identification/reference value. Dust, labels, moisture and residual kernels can change actual tare.

   Preferred sequence: clean and tare empty cassette → fill and correct → photograph → weigh that same cassette. Use a stable support entirely on the scale platform, with no contact against the scale housing. Keep the handle and carrier off the balance.

   \[
   \mathrm{TKW}=\frac{1000\,m_\text{net}}{N}
   \]

   | Verified count | Mass at 45 g TKW | Mass error corresponding to 0.5% | Recommended readability |
   |---|---:|---:|---:|
   | 1000 | 45 g | 0.225 g | **0.01 g** |
   | 500 | 22.5 g | 0.1125 g | **0.01 g** |
   | 100 | 4.5 g | 0.0225 g | **0.001 g preferred** for separate replicates |

   A 0.1 g scale can satisfy the arithmetic budget for one 1000-kernel weighing. It leaves little margin when combining two independently tared 500-kernel batches: conservative rounding of four readings alone can contribute up to 0.2 g, or 0.44% of 45 g.

   **Readability is not accuracy.** Check repeatability and known added weights at the actual cassette load. Sampling variation and count errors also consume the overall error budget.

   For two exact 500-kernel batches, **TKW = \(m_1+m_2\)** in grams. If transferring seeds into a weighing cup instead, inspect the cassette afterward for retained kernels and account for spills.

8. **Split the hardware before printing; the current exports are not manufacturing-ready by inspection.**

   The v0 insert fits nominally on a 256 × 256 mm Bambu bed, with limited brim margin. Its **296.5 mm body does not fit flat**. Also, a Prusa MK4S has a **250 × 210 mm XY bed**; 220 mm is its Z dimension. [Bambu P1S specifications](https://us.store.bambulab.com/products/p1s?skr=yes), [Prusa MK4S specifications](https://www.prusa3d.com/product/original-prusa-mk4s-3d-printer-7/?gQT=2)

   Print cassette, carrier, apron and handle separately. Keep any cassette seam outside the well field; seams through wells create extra traps and ambiguous image regions.

   A 0.4 mm nozzle commonly uses approximately 0.45 mm extrusion width. **1.2 mm ribs are reasonable; 0.9 mm is a practical lower trial limit**, subject to the slicer’s actual toolpaths. Keep the narrow crest supported by the wider rib beneath it. [Prusa extrusion-width guidance](https://help.prusa3d.com/article/creating-profiles-for-different-nozzles_127540?product=mini-2)

   Use PLA for tonight’s dimensional trial; consider PETG for subsequent tougher, washable hardware after checking stringing and well dimensions. Start with 0.20 mm layers and no supports in the wells.

   Rough planning allowances—not sliced estimates—are **30–60 minutes for a 100-well coupon**, **2–4 hours for a 500-well cassette on a fast printer**, and several additional hours for the carrier and handle. Older machines may take substantially longer. Slice before promising a complete assembly by 22:00.

   For laser cutting, use a **1.5–2 mm perforated sheet over a smooth backing**, with kerf-compensated rounded openings. This is a credible rapid geometry trial, but lacks the chamfered entry of the FDM design. Test filling separately.

   Two concrete issues in [build_pfanne.py](build_pfanne.py):

   - `join()` combines objects without Boolean-unioning intersecting solids; `union_all()` is never called. Inspect and repair the exported solids and sliced toolpaths.
   - The lip-wall test compares local vertex `y` against a world-position threshold. With the current dimensions, the intended taper condition never fires.

   The insert also has no deliberate fit clearance. Add it explicitly.

9. **Tonight’s go/no-go test should precede the full print.**

   Print small wheat test patches covering **4.0 / 4.4 / 4.8 mm width** and **1.6 / 2.0 mm depth**, with the same rounded shape and chamfer. Use actual seed, including its small and large tails.

   Record filling time, vacancies, doubles, kernels on ribs, losses during surplus removal and manual correction count. Deliberately challenge the inspection with stacked kernels and fragments.

   A useful initial usability gate is **at least 98% single occupancy after a short fill cycle**, followed by straightforward correction and no losses during ordinary transfer to the photo/scale station. This is a proposed engineering gate, **not evidence of 99.9% reliability**. If filling requires repeated aggressive shaking or selects visibly different kernels, retain A4 counting as the working method.

The **v1 wheat parameter table** below assumes a 500-well cassette. All linear dimensions are millimetres. `WELL_W/L` describe the clear opening **below the entry chamfer**; the chamfer enlarges the top mouth. New shape and assembly parameters require corresponding geometry changes—the current box-rib generator cannot produce them merely by changing constants.

| Parameter | v1 value | Implementation meaning |
|---|---:|---|
| `COLS, ROWS` | `25, 20` | 500 wells; two accepted batches |
| `WELL_W, WELL_L` | `4.4, 8.2` | Seating opening, across / along pour |
| `WELL_D` | `1.8` | Floor to rib crest |
| `WELL_SHAPE` | `"ROUNDED_RECT"` | Symmetric elongated pocket |
| `WELL_CORNER_R` | `1.0` | Internal plan-view corner radius |
| `WELL_DRAFT_DEG` | `0.0` | Vertical walls below chamfer |
| `RIB` | `1.2` | Web width below chamfer |
| `RIB_CHAMFER_X, RIB_CHAMFER_Z` | `0.4, 0.4` | Each side, 45° |
| `RIB_TOP_W` | `0.4` | Derived crest width |
| `INSERT_FLOOR` | `1.2` | Six layers at 0.20 mm |
| `PAD` | `10.0` | Border width using existing formula |
| `MARKER_PATCH` | `10.0` | Flush printed marker, including quiet zone |
| `INSERT_CLEARANCE` | `0.3` | Per side between cassette and carrier |
| `WALL` | `2.0` | Carrier wall |
| `RIM_H` | `12.0` | Above cassette crest |
| `BASE_T` | `1.6` | Carrier floor; support cassette against flex |
| `LIP_LEN` | `25.0` | Separate apron |
| `LIP_EDGE_T, LIP_EDGE_R` | `0.8, 0.4` | Rounded leading edge |
| `FRONT_STOP_ABOVE_INSERT` | `0.0` | Use side retention; unobstructed discharge |
| `HANDLE_LEN, HANDLE_W, HANDLE_T` | `110, 34, 18` | Separate rounded handle |
| `HANDLE_ANGLE_DEG` | `12` | Upward from pan plane |
| `FIELD_W, FIELD_L` | **141.2 × 189.2** | Derived using existing pitch formula |
| `INSERT_W, INSERT_L` | **161.2 × 209.2** | Derived |
| `CARRIER_W, CARRIER_L` | **165.8 × 213.8** | Includes clearance/walls; excludes apron and mounting tabs |

This carrier fits a 220 mm square bed with modest margins; rotate it on a 250 × 210 mm Prusa bed. Place fasteners and mounting features within that envelope or print them separately.

For **species trials**, use these seating dimensions with the same chamfer concept. These are my proposed starting geometries, not published universal seed dimensions:

| Species | `WELL_W` | `WELL_L` | `WELL_D` | Corner radius | Reason / main risk |
|---|---:|---:|---:|---:|---|
| Bread wheat | 4.4 | 8.2 | 1.8 | 1.0 | Broad kernels; small kernels can double |
| Durum | 4.4 | 9.2 | 1.8 | 1.0 | Extra longitudinal allowance; confirm cultivar fit |
| Rye | 3.6 | 10.0 | 1.6 | 0.9 | Narrower, elongated; shrivelled kernels particularly troublesome |
| Barley, hull retained | 4.8 | 12.0 | 2.0 | 1.2 | Hull/tip allowance; awn remnants can bridge |
| Oats, hull retained | 4.2 | 15.0 | 1.6 | 1.0 | Long, slender units; overlap and hull bridging are major risks |

Published measurements illustrate why one insert cannot serve all four shapes: one study reported mean lengths of **6.8 mm wheat, 8.0 mm rye, 8.4 mm barley and 11.8 mm oats**, with substantial variation. Durum studies also show cultivar-dependent dimensions. These means are not design limits. [Cereal physical-properties study](https://onlinelibrary.wiley.com/doi/10.1155/2020/6639233), [durum cultivar study](https://www.mdpi.com/2077-0472/15/4/359)

Measure the actual lot before selecting an insert. Start with approximately **0.4 mm total width clearance and 0.6 mm total length clearance** beyond the largest intact kernels in the trial sample, then test doubles. If accommodating large kernels makes small-kernel singulation unreliable, use the A4 workflow for that lot.

For the longer species, begin with **10 × 10 trial inserts**; do not retain `25 × 20` and assume they fit the wheat carrier. A wheat-only physical demonstration is the defensible scope tonight.

Three pitch sentences:

> „Die Tausendkorn-Pfanne bringt Saatkörner in ein geordnetes Raster, damit Fehlstellen und auffällige Belegungen gezielt geprüft werden können.“
> „Aus geprüfter Kornzahl und gewogenem Saatgut berechnet Tausendkorn das Tausendkorngewicht und die passende Aussaatmenge.“
> „Unser Prototyp kombiniert wechselbare Einsätze mit der Fotoauswertung – als Präzisionsmodus neben dem einfachen A4-Foto.“
