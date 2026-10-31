**Build the pan as an experiment in spreading, not as a grain-weight sorter.** Start with a flat floor and almost no internal features. KornKlapp remains the safer hackathon solution because it preserves A4 detection and controls lighting and camera position. The pan could become a simpler product if physical trials demonstrate fewer contacts.

I checked the station README, `ASTRA_DESIGN.md`, and the project’s status, challenge and measurement protocol. Dimensions below are proposed experiments, not validated designs.

**1. What dry panning actually does**

An 800-kernel sample occupies approximately **13,700 mm²** in elliptical projection at 6.6 × 3.3 mm per kernel: only 22% of A4. The challenge is distributing that area without contacts. An A4-equivalent circular floor needs **Ø282 mm**; use **Ø290 mm**, giving 66,052 mm².

- **Sliding versus rolling:** wheat can roll around its long axis, rock over its crease, and slide lengthwise. It will not behave like ball bearings. Collisions and circular walls encourage tangential alignment; grooves can turn this into touching chains.
- **Percolation:** small fragments can fall through gaps in the initial moving heap. Once particles form a monolayer, there is little vertical space for this mechanism.
- **Brazil-nut effect:** larger particles can rise through a repeatedly rearranged, multilayer bed. It does **not** imply that plump kernels form a particular ring.
- **Shape segregation:** rounder kernels may roll farther; flat chaff and angular fragments may stick or become trapped. Direction and strength depend on surface, motion and geometry.
- **Air drag:** chaff’s high area-to-mass ratio matters much more than wheat’s. Gentle horizontal panning provides neither controlled airflow nor reliable winnowing; airborne chaff also risks leaving the sample.
- **“Centrifugal sorting”:** orbiting the pan without spinning it produces a rotating, approximately uniform horizontal inertial force in pan coordinates—not a steady radial centrifugal field. Wall interactions can nevertheless produce circulation and edge accumulation. Even during rotation, both inertial force and Coulomb friction scale with mass: **heavier kernels do not automatically slide outward sooner**.

Horizontal agitation can segregate granular mixtures, but published monolayer experiments do not establish rapid, concentric wheat grading. [Swirling-mixture experiment](https://doi.org/10.1103/PhysRevE.64.041305)

For wheat, one study reports minimum wheat–PP friction **0.443**, with repose measurements around **28–31° at 14% moisture**. Another calibrated wheat–wheat static friction **0.30**, rolling resistance **0.04**, and restitution **0.50**. These are sample/model-dependent values, not universal constants. [PP measurements](https://uwm.edu.pl/wnt/technicalsc/tech_19_1/markows.pdf), [DEM calibration](https://doi.org/10.1002/fsn3.3693)

A plausible hand-motion trial is **15–25 mm orbit radius, 2–3 Hz, 0–5° tilt**. Horizontal acceleration is

\[
a=R(2\pi f)^2.
\]

At **20 mm, 2.5 Hz**, this is **4.93 m/s² = 0.50g**, with speed **0.31 m/s**. Sliding requires roughly \(a>\mu_sg\) on a level floor. Tiny circles can simply carry the heap around unchanged.

**Expected within 10–20 seconds:** heap collapse, rearrangement, some spreading, possible edge piles and weak fragment/chaff enrichment. **Unsupported:** clean weight classes, calibrated size rings, or reliably isolated kernels.

**2. Three model-ready prototypes**

All dimensions are **mm**. Shared geometry:

- Usable floor radius **145**; nominal surface \(z=0\).
- Inner wall: \(z=2(r-145)\), from \(r=145\) to **155**, reaching **20** high; **63.435° above horizontal**.
- Horizontal rim flange: \(r=155–180\), top \(z=20\). **Outer body Ø360**, excluding appendages.
- Floor thickness **3**; wall/flange **2**. Smooth matte ivory PP; prototype in finished PETG, then recalibrate friction. No coarse printed texture.
- Two integral grip tabs at 90°/270°: **50 tangential ×25 radial ×3**, extending from \(r=180\).
- Pour lip at 0°: extend flange **25**, taper width **40→25**, add **3-high side rails**. Keep the retaining wall continuous; pour over it.
- Four matte ArUco markers, black square **18** plus **3** quiet border, centred at \(r=167.5\), angles **45°, 135°, 225°, 315°**, with square axes radial/tangential.

Markers sit **20 mm above the floor**: use calibrated camera pose and known floor geometry, not their planar homography directly. Ignoring that offset causes approximately **5% scale error at 400 mm camera height**. Mask markers, but inspect every sample-bearing surface. Known rim diameter alone is a weaker reference.

| Prototype | Exact interior geometry | Hypothesis and rejection criterion |
|---|---|---|
| **A — flat floor, wall riffles** | Flat Ø290 floor. Two circular wall beads: torus centres \((r,z)=(149,8),(152,14)\); circular cross-section radius **0.75**, united with wall. Meridional pitch **6.71**; exposed projection **0.75**. No floor features. | Wall beads interrupt circulation while leaving the imaging floor clear. Reject if contacts do not improve versus equal-time A4 spreading, or beads retain kernels. Also simulate beads removed to isolate their contribution. |
| **B — low concentric barriers** | Flat floor; smooth wall. Three annular ridges at radii **40,75,110**, pitch **35**, width **3**, height **0.6**. Cross-section \(z=0.3[1+\cos(2\pi(r-r_i)/3)]\) within ±1.5 of each ridge. | Weak barriers might interrupt coherent sliding and distribute kernels among zones. Reject if contact fraction exceeds A, or touching chains form beside ridges. |
| **C — gently crowned floor** | Smooth wall; **zero riffles**. Floor \(z=2[1-(r/145)^2]\): centre **2 higher** than edge, maximum slope **1.58°**. | Mobilized kernels receive a weak outward bias without groove alignment. Reject if outermost 15-mm annulus accumulates more contacts than A or centre depletion worsens uniformity. |

C’s slope cannot overcome static friction alone. B’s 0.6-mm ridges cast approximately **1-mm shadows at 30° light elevation**; the 20-mm wall is potentially much worse. Photograph under broad diffuse illumination.

**3. Blender/Bullet experiment**

Use **800 whole kernels +40 halves +40 chaff flakes**, identical particle identities and starting arrangements across designs. Start with irregular convex wheat meshes around **6.6×3.3×3.0**, halves cut from those meshes, and chaff plates **8×3×0.2**.

At density 1,350 kg/m³, that ellipsoidal wheat approximation gives about **37 g for 800**, not 45 g. Measure actual thickness/volume and sample mass; do not force incompatible dimensions and density. **Bulk density 780 kg/m³ includes voids and must not become particle density.**

These are **initial sensitivity-test settings**, particularly uncertain for chaff:

| Body | Density kg/m³ | Bullet friction setting | Bullet restitution setting |
|---|---:|---:|---:|
| Whole wheat | 1,350 | 0.60 | 0.70 |
| Broken wheat | 1,350 | 0.65 | 0.50 |
| Chaff envelope | 300; sweep 100–800 | 0.80 | 0.15 |
| PP pan, animated | 900; mass irrelevant | 0.75 | 0.43 |
| Supported paper, fixed | Mass irrelevant | 0.80 | 0.30 |

Bullet multiplies body coefficients: these yield wheat–PP **μ=0.45, e=0.30**, wheat–wheat **μ=0.36, e=0.49**. Its standard friction model does not independently reproduce static and kinetic friction. Calibrate against a tilt test and short drop test on the actual finish. [Bullet source](https://raw.githubusercontent.com/bulletphysics/bullet3/master/src/BulletCollision/CollisionDispatch/btManifoldResult.cpp)

**Motion:** drop the sample from **50 mm**, settle **2 s**; ramp to \(x=20\cos(5\pi t), y=20\sin(5\pi t)\) over **1 s**; orbit **12 s**, ramp down **1 s**, settle **2 s**. Keep orientation fixed initially. Separately test slow ±3° rocking and a smoothly stopped/restarted direction reversal. Sweep radius **15/25** and frequency **2/3 Hz**.

**Baselines:** supported A4, same drop, then **15 s** of reproducible paddle spreading; also include KornKlapp and a smooth circular pan. Never substitute randomly placed, already separated kernels for spreading.

Use convex kernel collisions, a concave animated pan collider, **1,200 simulation steps/s**, **50 solver iterations**, disabled sleeping during motion, and effective margins **≤0.05 mm**. Check doubled step resolution and halved margins. Millimetre objects are troublesome; if scaling lengths ×100, also scale gravity ×100 and masses ×10⁶ to preserve time and density. [Blender stability guidance](https://docs.blender.org/manual/en/dev/physics/rigid_body/tips.html)

Report across **≥10 paired seeds**, including worst cases:

- Whole-kernel fraction with projected boundary gap **≤0.2 mm**; physical contacts separately.
- Median/10th-percentile nearest **boundary** distance; overlap/occlusion fraction.
- Area-normalized radial distributions by material and kernel size.
- Kernels supported on ridges/walls; shadowed kernels under fixed lighting.
- Escaped particles and particles remaining after pouring, by class.
- Actual image count error and handling time in physical follow-up.

Bullet can reject obvious traps. It cannot validate chaff airflow, flexibility, electrostatics, dust adhesion, realistic rolling resistance or counting accuracy. Shadows require rendering; performance claims require real photographs.

**4. Verdict**

**Later-product candidate; conditional pitch demonstrator; weight-sorting claim is a trap.** A single washable part is attractive, but this Ø360 pan sacrifices KornKlapp’s A4 compatibility, camera support and hood. Keep KornKlapp for today’s technical submission; advance A only after paired trials show fewer contacts without losses.

Retain the whole sample, while preserving the challenge’s counting classes: broken pieces and chaff are inspected but excluded from kernel count. Removing flagged chaff before weighing is acceptable; remaining excluded material still biases TKG.

Pitch: **„Die Kornpfanne soll die ganze Handvoll mit wenigen Kreisbewegungen fürs Foto verteilen und anschließend vollständig in den Wiegebecher bringen.“**