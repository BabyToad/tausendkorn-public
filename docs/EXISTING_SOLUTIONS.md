# Existing solutions: seed/kernel counting from photos

Research date 2026-10-27. Every claim cites a source. **[unverified]** marks vendor
claims nobody has checked independently, my inferences, or details I took from
memory and did not fetch. No accounts were created and no forms were submitted. The
SeedCount analysis below comes only from public HTML, the JS bundle, and the public
Swagger/OpenAPI file.

---

## 1. Seed Count by PCS AGRI (seedcount.pcs-agri.com): the direct competitor

**Who:** PCS AGRI, a start-up in Agadir, Morocco ("Innovation City Sous Massa, Office
A210"; JS bundle i18n footer). CEO Tahar Hamdani
([FreshPlaza, 11 Feb 2026](https://www.freshplaza.com/north-america/article/9810005/we-develop-ai-based-solutions-for-growers-and-nurseries/)).
The company focuses on growers and **nurseries**. Its sister products include "Track
Yields" for tomato and blueberry fruit counting. FreshPlaza says the company's apps are
"patented in Morocco, Europe and the US" **[unverified]**. The iOS app v1.0.0 shipped on
18 Nov 2025 and the latest is v1.3.15
([App Store](https://apps.apple.com/ma/app/seed-count/id6755075770)). The Android
package is `com.pcsagri.seedcount`
([Play](https://play.google.com/store/apps/details?id=com.pcsagri.seedcount)).

**Tech stack (from page source and bundle `/assets/index-CoiRCVLj.js`, 1.3 MB):**
- The front end is a **Lovable**-generated React/Vite SPA (`twitter:site @lovable_dev`
  in `index.html`) built with Radix/shadcn, lucide icons, react-query and SheetJS for
  Excel export. It is served behind Cloudflare.
- The bundle contains **no on-device ML**: no ONNX, TFJS or OpenCV.js. All inference runs
  on the server.
- The backend is **PHP 8.2** (`x-powered-by: PHP/8.2.35`, and the 404 page is
  Laravel-style) at `https://seedcount.pcs-agri.com/api`. Its OpenAPI spec lists a
  `502 ServiceUnavailable` on analyze, which suggests that PHP proxies to a separate ML
  service **[inference]**.
- Public Swagger: <https://seedcount.pcs-agri.com/api/docs>, spec
  <https://seedcount.pcs-agri.com/api/docs/openapi.yaml> ("Seed Count Public API" v1.0.0,
  JWT with 2 h expiry, analyze rate limit 10/min/user).
- Endpoints found in the bundle: `/analyze-image`, `/images`, `/images/treated/{name}`
  (annotated output image), `/images/{id}/seeds`, `/crops`, `/varieties`, `/lots`,
  `/site-productions`, `/qr-codes` (+CSV import), `/tickets` (support), plus admin/staff
  endpoints.

**UX flow (reconstructed from bundle code and i18n strings):**
1. Log in. Accounts are B2B. The site invites visitors to "Book Demo" via Zoho Bookings.
2. Fill in "New analysis" with crop, variety, lot number, production site, sample name and
   an optional **seed weight (g)**. The image-format selector offers **A4 (default) / A3 /
   A5 / Without**.
3. Upload JPG/PNG (UI says "max 50 MB"). The image is re-encoded client-side at JPEG
   q=0.92.
4. **Manual corner-point step:** "Select Image Corner Points. Drag the polygon handles to
   the image corners. Use zoom and pan." The client derives `top_left/top_right/
   bottom_left/bottom_right` from the polygon and posts them with the image. Because the
   **user places the sheet corners by hand**, the server only has to apply a homography
   with the known paper size to get mm/px. There is no automatic sheet detection in the
   web client.
5. POST multipart to `/analyze-image`. The client timeout is **20 min** (`12e5` ms). The
   app then redirects to `/analysis/{id}`.
6. The report shows the annotated image ("{count} grains detected"), total grains, a
   "purity score", saved weight, **weight of 1000 seeds**, seeds/gram, average and std
   of width, length, area and perimeter (cm), and a surface-area distribution histogram.
   It shows a "Detection Issues Found – Some grains might have been missed" banner with a
   "Report Issue" button. Excel export is in the bundle. The FAQ also claims PDF export.
7. Per-seed data: `GET /images/{id}/seeds` returns `seed_index, width_cm, length_cm,
   area_cm2, perimeter_cm`. TKW = entered weight / count × 1000. **TKW is not estimated
   from the image.**
8. The dashboard lists all analyses with filters by lot, crop, site, date and purity
   (>98 / 95–98 / <95 %). Mobile app versions add QR-code scanning of lots (v1.1.9),
   an image cropper and an improved camera (v1.3.15)
   ([App Store history](https://apps.apple.com/ma/app/seed-count/id6755075770)).

**Outputs:** count, TKW, seeds/g, size statistics, per-seed CSV, "purity" (the API example
returns `"purity": "N/A"`, so it may be unimplemented or crop-specific **[inference]**),
and an annotated image.

**Accuracy evidence:**
- The FAQ claims "98%+ accuracy, validated against laboratory measurements … trained on
  millions of seed images" (bundle i18n) **[unverified, marketing]**.
- A LinkedIn post by the CEO claims ">99% counting accuracy" after a model upgrade
  (surfaced in a search snippet; I did not open the post) **[unverified]**.
- The landing page says "1000+ Farmers Trust Us, 4.8 Rating", yet the App Store shows "not
  enough ratings" ([App Store](https://apps.apple.com/ma/app/seed-count/id6755075770)).
- No paper, dataset or benchmark is published.
- Example crops named in the FAQ are **"Tomato, Melon, watermelon"**. The focus is
  vegetable and nursery seed. The API example uses wheat with 168 grains.

**Pricing (bundle i18n; no prices shown, quote/demo only):**
- Starter: 2 crops, 5,000 pictures/yr, 2 users.
- Standard: 5 crops, 20,000 pictures/yr, 4 users, QR codes.
- Pro: unlimited crops, 80,000 pictures/yr, plus "200 h of specific development".
- Free trial requires no credit card.
- The app itself is free to download.

**Copy:** the A4/A3/A5 paper-size selector; the per-lot/variety metadata and history;
per-seed size distribution (uniformity is valuable to farmers, see CHALLENGE.md); the
"weight entered → TKW + seeds/g" pattern; the annotated output image; Excel export; and
an honest "issues found" banner.

**Beat:**
1. They need **manual corner dragging**, where we can auto-detect the A4 sheet. Manual
   fallback should exist only if detection fails.
2. They are **cloud-only**, with a 20-minute timeout and paid tiers. A barn has no
   internet, so we should run offline/on-device or on a laptop.
3. They have **no seeding-rate calculator**, and their workflow stops at TKW.
4. They target vegetable seed, with no broken-kernel or foreign-material handling under
   cereal rules such as ISO 520 (twins count double, husked barley and oats).
5. They publish no evidence. We can show MAE on a held-out 1000-kernel test set.
6. Their UX is heavy B2B lab software. Ours can be one-screen and farmer-first.

---

## 2. SeedCounter (wheatdb.org, Komyshev/Genaev/Afonnikov, ICG Novosibirsk)

- **Paper:** "Evaluation of the SeedCounter, A Mobile Application for Grain Phenotyping",
  *Front. Plant Sci.* 7:1990, published 4 Jan 2017
  ([PMC5209368](https://pmc.ncbi.nlm.nih.gov/articles/PMC5209368/)).
- **App:** free Android app `org.wheatdb.seedcounter`; its
  [Play page](https://play.google.com/store/apps/details?id=org.wheatdb.seedcounter) still
  returns HTTP 200. The app uses OpenCV (BSD). The paper gives no source repository.
- **Method:** classical CV.
  1. Grayscale, then adaptive threshold, then Canny.
  2. **Paper detection:** Hough line segments (20–80 % of the image side) are clustered
     into 4 sides, the vertices are computed, and a perspective transform is applied.
  3. **Scale comes from the known paper size** (A4, Letter, Legal, A3, A5, B4–B6 or
     custom).
  4. `findContours`, plus local HSV binarization against shadows.
  5. Optional marker-based watershed for touching grains.
  6. An ellipse fit gives length and width.
- **UX:** calibrate by photographing one seed and checking its red outline. Settings
  cover paper size, resolution, touching-grain separation and HSV. Results are stored as
  XML, exported as TSV, or uploaded to the wheatdb web server.
- **Accuracy:**
  - Counting used about 50 grains per image: MAE 0.06–1.4 grains, r 0.992–0.999.
  - Size vs microscope: MAE ≈ 0.31 mm, MAPE ≈ 8 %. SmartGrain was slightly better on
    width.
  - **Lighting significantly affects error** (p=0.004), device does not. Direct sunlight
    biases length.
  - Speed is 30–60 s per image on 2016 phones.
- **No TKW computation** in the app.
- **Copy:** the A4 perspective-rectification pipeline is the canonical "known-paper-size
  scale" method; it is cheap, deterministic, and gives mm/px for free. Tell users to avoid
  direct sun and use diffuse light.
- **Beat:** it was validated only at about 50 sparse grains. Our 170–1000 kernels per A4
  page means dense touching clusters, where watershed degrades. A learned
  detector/density model wins there.

## 3. GrainNet (Plant Methods 2025): code and weights are public

- **Paper:** Wang et al., "GrainNet: efficient detection and counting of wheat grains
  based on an improved YOLOv7", *Plant Methods* 21 (2025), doi 10.1186/s13007-025-01363-y
  ([Europe PMC PMC11934480](https://europepmc.org/article/PMC/PMC11934480)).
- **Method:** a YOLOv7 box detector with EMA attention and an ASF-Gather-and-Distribute
  neck.
- **Data:** 1,198 original images (LabelImg boxes) of 3 Chinese wheat varieties, labelled
  by **colour class "Y/G/B" (yellow/green/brown)**. The classes are varieties, not quality
  classes.
- **Density levels:** low (2–20 per local area), medium (21–50), high (>50). Imaging
  heights and backgrounds were varied, and several devices were used.
- **Results:**
  - mAP 93.15 %, F1 0.946, 29 FPS.
  - Against manual counts: **R² 0.93, MAE 5.97 grains, "counting accuracy" 94.47 %**.
    That is far from our needs: about 6 kernels off per image, and a 1000-kernel image is
    harder.
- **Repo:** <https://github.com/1371530728/grainnet>, last pushed Feb 2025. The code is
  under `gainnet/`.
  - **Trained weights committed:** `gainnet/runs/train/grainnet/weights/best.pt` (62.7 MB)
    plus the `yolov7.pt` base.
  - **License GPL-3.0** (`gainnet/LICENSE.md`, inherited from YOLOv7).
  - The dataset is only on Baidu Netdisk (`gainnet/dataset/images.txt`).
  - `data.yaml`: `nc: 3, names: ['Y','G','B']`.
  - Checked via the GitHub API tree.
- **Copy:** the density stratification for evaluation (report error by crowding level);
  augmentations (mosaic, mixup, cutout, brightness).
- **Beat:** box detection at 94 % is not good enough for TKW, where 1 % count error equals
  1 % TKW error. With points supervision and tiling we should beat MAE 6.

## 4. SmartGrain (NIAS/NARO Japan, Tanabata et al. 2012)

- **Paper:** *Plant Physiol.* 160:1871 (doi 10.1104/pp.112.205120).
- **Platform:** Windows-only freeware
  ([NARO page](https://www.naro.affrc.go.jp/archive/nias/eng/research/h24/nias2012-03.htm)).
- **Method:** classical segmentation of seeds photographed or scanned on a contrasting
  background. It measures area, perimeter, length, width, circularity, L/W ratio,
  center-of-gravity offset (IS-CG distance), and exports CSV. It does not measure colour
  (summary via [Frontiers 2020, SeedExtractor](https://www.frontiersin.org/articles/10.3389/fpls.2020.581546/full)).
- **Accuracy:**
  - Width was slightly better than SeedCounter (MAPE 6.97 % vs 8 %;
    [PMC5209368](https://pmc.ncbi.nlm.nih.gov/articles/PMC5209368/)).
  - Size "accuracy" 0.871–0.947, the lowest in the GrainScan comparison
    ([PMC4105244](https://pmc.ncbi.nlm.nih.gov/articles/PMC4105244/)).
- **Copy:** its shape-descriptor set is a ready-made "uniformity" panel.
- **Beat:** it is desktop-only with no phone workflow.

## 5. GrainScan (CSIRO, Whan et al. 2014)

- **Paper:** *Plant Methods* 10:23 ([PMC4105244](https://pmc.ncbi.nlm.nih.gov/articles/PMC4105244/)).
  Uses a flatbed scanner at 300 dpi. The executable is free at
  doi 10.4225/08/536302C43FC28. The license is not stated.
- **Method (the best-documented classical pipeline for dense wheat):**
  1. Take the (R+G)/2 grey image and apply Gaussian smoothing.
  2. Attribute morphology: a closing fills the **grain crease**, and openings remove thin
     and thick **debris**.
  3. Global threshold chosen automatically from a grey-level × gradient histogram.
  4. **Touching grains split at troughs between regional maxima of the smoothed distance
     transform.**
  5. An area filter removes fragments.
  6. Ellipse axes give length and width.
- **Colour calibration:** scan a Munsell ColorChecker Mini, then regress RGB to CIELAB.
- **Scale:** comes from scanner dpi.
- **Data:** 382–985 wheat seeds per scan (mean 654), the same density as ours. About
  101 s per sample.
- **Accuracy:** size accuracy 0.981–0.996, comparable to the commercial SeedCount
  (0.991–0.994).
- **Copy:**
  - The distance-transform peak splitting is a strong classical baseline for touching
    kernels.
  - The area filter, together with the median kernel area, flags **broken kernels (area
    much smaller than median) and doubles/clusters (area ≈ 2× median)**.
  - An optional colour card gives CIELAB, if we want colour or quality claims.
- **Beat:** it needs a scanner. Phones introduce perspective, uneven light and shadows,
  which our A4 rectification and learned model handle.

## 6. SeedCount (Next Instruments, Australia): the commercial lab benchmark

- **What it is:** a lab image-analysis instrument. Seeds sit in wells of a **sample
  tray**, and the system returns per-seed size, CIELAB colour and disease state.
  - Cost about **AUD 15,000**, about 210 s per sample, mostly spent laying seeds in the
    tray.
  - Source: [GrainScan paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4105244/).
  - A brochure exists ([LabWrench PDF](https://cdn.labwrench.com/eMan/manualNo/10873/seedcount%20image%20analyzer%20brochure.pdf)),
    which I have not opened **[unverified]**.
- **Pitch use:** our phone app delivers lab-grade counting for €0 versus a
  roughly AUD 15k instrument.

## 7. SeedMetrics (iOS, Brazil)

- **Vendor:** Seedmetrics Ltda
  ([App Store](https://apps.apple.com/us/app/-/id6479868736)).
- **Release history:** v0.5.40 dated "04/12/2024" (day/month order is ambiguous), v0.5.92 on 4 Jun.
- **Function:** AI kernel counting of loose kernels **and kernels on ears**. Crops are
  corn, sorghum, soy and vegetables. It computes PMS (= TKW), records weight, batch and
  contract, offers GPS and offline handling, and mentions ERP integration.
- **Business model:** free download with "app licenses". It has 1 rating.
- **Reference:** no reference object is mentioned. The method and accuracy are not
  public.
- **Copy:** offline queueing and lot/contract metadata.
- **Beat:** it has no cereal small-grain focus and no published accuracy.

## 8. CountThings (Dynamic Ventures)

- **Method:** generic template-based counting. You pick a template from a library or the
  vendor builds a custom one "in most cases free of charge". It **runs locally on the
  device and offline**. Workflow: Camera → Count → Review and Save.
- **Platforms:** iOS, Android, Windows.
- **Pricing:** $120/month or **$1,200/year per device**, $24 per 24 h, or $0.80 per count
  ([countthings.com/solutions](https://www.countthings.com/en/solutions)).
- **Accuracy:** no published grain accuracy. The vendor says "if you are not getting 100%
  accuracy, contact us". A sagebrush-seed article notes it was not yet tested for small,
  variable seeds ([U. Wisconsin Press](https://muse.jhu.edu/article/851133)).
- **Copy:** the review/correction step before saving. It also shows that farmers and
  industry will pay for counting.
- **Beat:** it is expensive and generic. It has no scale, no TKW and no seeding rate.

## 9. Petiole Pro / Petiole Spruce

- **Petiole Pro:** an Android app for leaf area and plant measurements using a printed
  **calibration plate**. It claims "98.23 % precision" in general.
- **Seeds:** the only seed-related offer is **germination counting** in seedling trays,
  via enterprise Spruce. I found **no thousand-seed-weight or seed-count-on-paper
  feature** ([petiole.pro](https://petiole.pro/)).
- **Copy:** printed calibration targets as a robust scale reference. A plain A4 sheet
  already does that job.

## 10. Hardware counters (context for the jury)

- Wintersteiger Seed Count R-25+/R-60+/S-25+ claim "almost 100 %" accuracy and compute TGW
  automatically when linked to a scale
  ([Wintersteiger](https://www.wintersteiger.com/en/Plant-Breeding-and-Research/Products/Product-range/Laboratory-preparation/67-Seed-Count-R-60plus)).
- A Serbian study found that lab counters at maximum speed bias toward small seeds
  ([JPEA 2022](https://www.aseestant.ceon.rs/index.php/jpea/article/view/36855)).
- Krishnan et al. 2023 built an ImageJ counting setup for TGW in wheat with **r = 0.99 vs
  manual TGW** ([IJGPB](https://isgpb.org/journal/index.php/IJGPB/article/view/3968)).
  Classical image counting is therefore already "good enough" for TKW in controlled
  setups. Our challenge is phones and dense layouts.
- GainTKW (Agronomy 2018, an Android app combining weighing and counting,
  [doi](https://dx.doi.org/10.3390/agronomy8090178)) is close prior art for "phone + scale
  → TKW" **[abstract only, not read]**.

## 11. Data for broken-kernel / foreign-material detection

- **GrainSet**
  - Fan et al., *Sci Data* 10:778 (2023)
    ([PMC10632488](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10632488/),
    [arXiv html](https://arxiv.org/html/2401.08599v1),
    [repo](https://github.com/hellodfan/GrainSet)).
  - More than 350k **single-kernel** crops with masks: wheat 200k, maize 19k, sorghum
    102k, rice 31k.
  - Labels: normal (NOR), damaged/unsound classes (F&S fusarium/shrivelled, SD sprouted,
    MY mouldy, **BN broken**, AP pest-attacked, BP black point, HD heat-damaged, UN
    unripe), and **IM impurities**.
  - Imaging used dual industrial cameras at about 860 dpi on a transparent plate, which is
    a different domain from phone photos.
  - Data license **CC BY 4.0** on Figshare. Wheat:
    doi 10.6084/m9.figshare.22992317.v2. Tiny 2 % preview: doi 10.6084/m9.figshare.22989029.v1.
  - The reported wheat accuracy of 99.9 % applies to their own imaging domain.
  - The repo has no LICENSE file for code (the GitHub API returns `license: null`).
- **GrainSpace:** CVPR 2022 by the same group
  ([arXiv 2203.05306](https://ar5iv.labs.arxiv.org/html/2203.05306)).
- **Use tonight:** pretrain or fine-tune a small kernel-crop classifier for normal vs
  broken vs impurity. Expect a domain gap: their crops are about 860 dpi, and ours are
  roughly 4000 px over 297 mm ≈ 340 dpi. Downsample their crops to match.
- **Roboflow Universe** wheat/seed datasets are small (16–1,663 images) and of mixed
  quality ([search](https://universe.roboflow.com/chloe-works/countobject-nnuzx),
  [seed_count](https://universe.roboflow.com/seedcount/seed_count-dnlqr/model/7)). They
  are low value next to our own `corn1000`.

## 12. Other repos seen (low value)

- `mramanindia/Rice_grains_Analysis`: an OpenCV notebook doing watershed for touching
  grains and broken-rice detection by size. It needs a black background and has no
  license
  ([repo](https://github.com/mramanindia/Rice_grains_Analysis)). Use it as a reference
  only.
- `UTokyo-FieldPhenomics-Lab/P2PNet-Soy`: point-annotation (P2PNet) soybean seed counting
  in field images, with no license
  ([repo](https://github.com/UTokyo-FieldPhenomics-Lab/P2PNet-Soy)). It is relevant
  because **our 158 point-labelled images match P2PNet-style supervision**.
- GitHub search for "seed counting", "grain counting", "kernel counting" and "thousand
  kernel weight" (GitHub API, 2026-10-27) turned up only toy repos with 0–1 stars, such
  as `yelpchen/seed-counting` and `ajgquional/rice-seed-counter-yolo`.
- Hugging Face model and space search for seed, grain, kernel and wheat found **no
  relevant counting models**. Only an unexamined `fazzam/GrainSight` space showed up.

---

## Repos/weights we could run tonight

| Option | License | What it gives | Quick start | Fit |
|---|---|---|---|---|
| **Classical baseline** (SeedCounter/GrainScan recipe): A4 contour → homography → threshold (Otsu on (R+G)/2 or LAB-b) → distance-transform peaks → watershed → area filter | OpenCV Apache-2.0 | Count, per-kernel size and mm/px, plus broken (area ≪ median) and twin (≈2× median) heuristics | `uv add opencv-python-headless scikit-image`, then `cv2.findContours` on the white-paper mask, `approxPolyDP` to 4 points, `getPerspectiveTransform` to 2100×2970 px (0.1 mm/px), `ndi.distance_transform_edt` + `peak_local_max` + `watershed` | Must-have fallback and the scale source. CPU-only, offline, under 1 s. Use **median-area division** (`count ≈ Σ blob_area / median_single_area`) to rescue touching clusters |
| **Cellpose-SAM** (`cpsam`, Cellpose ≥4) | Code BSD-3. Weights include a SAM ViT-L encoder; check the weight terms **[unverified]** | Generalist instance masks for blobs of any size, fine-tunable with a few dozen masks | `uv add cellpose`, then `models.CellposeModel(gpu=True).eval(img, diameter=None)`; [repo](https://github.com/MouseLand/cellpose), [Colab notebook](https://github.com/MouseLand/cellpose/blob/main/notebooks/run_Cellpose-SAM.ipynb) | Strong zero-shot candidate for touching kernels on white paper. Heavy on CPU; run it on a Kaggle T4 |
| **StarDist** | BSD-3 | Star-convex polygons, designed for round or elliptical touching objects. The pretrained `2D_versatile_he` takes RGB | `uv add stardist tensorflow`, then `StarDist2D.from_pretrained('2D_versatile_he')` ([repo](https://github.com/stardist/stardist)) | Kernels are near-ellipses, a good inductive bias. Fine-tune on our point labels after converting to small disks |
| **SAM 2 automatic mask generator** | Apache-2.0 | Class-agnostic masks | [facebookresearch/sam2](https://github.com/facebookresearch/sam2) | Too slow and over-segments at 1000 objects. Better as an **annotation helper** than as the counter |
| **GrainNet weights** | **GPL-3.0** | Trained YOLOv7 wheat-grain detector, 3 colour classes | `git clone https://github.com/1371530728/grainnet`, then `python detect.py --weights gainnet/runs/train/grainnet/weights/best.pt --source img.jpg --img 640` (YOLOv7 CLI) | Quick zero-shot test on wheat. Expect a domain gap (Chinese varieties, MAE about 6). GPL is fine for a hackathon demo but taints a closed app |
| **Ultralytics YOLO11/26 det/seg** | **AGPL-3.0** | Fine-tune a detector from our point labels (fixed-size boxes) on tiles | `uv add ultralytics`, then `yolo train model=yolo11s.pt data=kernels.yaml imgsz=1024` | Fast to train on a T4. AGPL applies if served. Tile at 640–1024 for 1000 objects |
| **CountGD / GeCo** (low-shot counting with 1–3 exemplar boxes or text) | MIT | Count from "click one kernel" without training | [CountGD](https://github.com/niki-amini-naieni/CountGD), [GeCo](https://github.com/jerpelhan/GeCo), NeurIPS 2024 | Nice UX demo ("tap one kernel"). Accuracy at 1000 dense objects is unknown **[unverified]**. Needs a GPU |
| **P2PNet-style point regression** | P2PNet-Soy has no license; original P2PNet code [unverified] | Directly uses our `kernel_points` | [P2PNet-Soy](https://github.com/UTokyo-FieldPhenomics-Lab/P2PNet-Soy) | Best match to our labels, but more setup time |
| **GrainSet** classifier data | CC BY 4.0 (data) | Broken (BN) and impurity (IM) kernel crops | Download the tiny split first (doi 10.6084/m9.figshare.22989029.v1); a ResNet-18/MobileNet `timm` fine-tune | For the broken and foreign-material head on per-kernel crops from our segmentation |

**Suggested stack:** classical A4 rectification gives the mm/px scale. Then run Cellpose-SAM
or StarDist, or a YOLO detector fine-tuned on tiles, as the counter. Cross-check against
median-area division. Flag outliers by area and shape for broken and foreign material.
Benchmark everything against `count_1000` (RESULTS.md).

---

## Pitch differentiation

1. **Built for cereals and farmers, not vegetable-seed labs.**
   - PCS Seed Count's examples are tomato and melon, and its workflow assumes a lab with
     lots and varieties.
   - We follow ISO 520 counting rules: twins count double, husked barley and oats count,
     broken kernels and chaff do not.
   - We cover the five cereals in the challenge.
2. **One photo to seeding rate.**
   - Competitors stop at TKW (SeedCount, SeedMetrics) or at the count (CountThings).
   - We continue: TKW → germination input → **kg/ha drill setting**
     (`Körner/m² × TKG / Keimfähigkeit`, CHALLENGE.md).
   - We show the result per trailer and per variety, since farmers recount at every load.
3. **No corner dragging.** The A4 sheet is detected automatically. PCS requires manually
   placing 4 corner handles.
4. **Offline on the farm.** PCS is cloud-only (20 min timeout), and SeedMetrics and
   CountThings are paid per device. We can run on an iPad or laptop without a network.
5. **Published evidence.**
   - We have MAE on the held-out `count_1000` split (every image exactly 1000
     kernels; the dataset has 836 images from 4 phones and tablets).
   - Competitors offer only marketing claims ("98 %+", ">99 %"). GrainNet's peer-reviewed
     result is 94.5 % accuracy (MAE about 6).
   - Error matters directly: 1 % count error equals 1 % TKW error equals 1 % seeding-rate
     error.
6. **Quality signals from the same photo.**
   - Broken-kernel and foreign-material share, plus a size-uniformity histogram (the
     cyclone already grades the seed, and uniformity is valuable).
   - Shown as a traffic light, not a lab report.
7. **Price story:** a lab instrument costs about AUD 15k (Next SeedCount), CountThings
   about $1,200/yr/device, PCS is quote-only. Our answer: phone plus an A4 sheet, free.

**ISTA TKW reference:** ISTA rules use 8 × 100-seed replicates with a coefficient of
variation ≤ 4 % (≤ 6 % for chaffy seeds) **[from memory, unverified; check the ISTA
Rules ch. 10]**. This supports a "photograph about 1000 kernels, so the count error is
the dominant TKW error" argument.
