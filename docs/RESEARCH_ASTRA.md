**Tausendkorn — research and build recommendation, 27 October 2026**

**Recommendation: build a tiled, domain-trained object counter; benchmark a modern few-shot counter alongside it; use a pointing VLM to inspect disagreements.** Near-zero error requires locating and classifying individual kernels, preserving image detail, and exposing uncertain objects for correction.

I read `AGENTS.md` and `docs/CHALLENGE.md` first. Dataset figures and counting rules below follow those files and your brief; the [Hugging Face dataset page](https://huggingface.co/datasets/SmartFarmingLab/corn1000) could not be independently retrieved during this research. No models were run, so **accuracy forecasts and implementation times below are engineering judgments, not benchmark results**.

**1. What to build tonight**

| Rank | Approach | Expected accuracy on corn1000 | Estimated effort | Main risk |
|---|---|---|---|---|
| **1** | **Tiled YOLO26s/YOLO11s, fine-tuned on point-derived boxes; separate kernel/broken/invalid classes; segmentation cross-check** | Best chance of low error after adaptation. **Numeric accuracy remains unverified.** Set an ambitious acceptance target of MAE ≤2 kernels and p95 error ≤5 on 1,000-kernel photos; report the achieved result honestly. | **3–4 hours**, including a proposed 45–120-minute training allocation | Incorrect pseudo-boxes; rare contaminants; session leakage |
| **2** | **GeCo2 with visual exemplars**, optionally CountGD++ with positive and negative exemplars | Strongest practical no-training challenger. Could outperform a rushed detector, but no verified corn1000 result supports a percentage forecast. | **1–2 hours**, with a strict installation cutoff | Domain mismatch; confusing broken kernels with intact ones; CUDA dependencies |
| **3** | **Tiled Gemini pointing**, initially 10–20 kernels per core tile; use it primarily on uncertain regions | Useful independent evidence, but insufficient evidence for near-zero whole-sheet error—even if most tiles are correct. | **0.5–1.5 hours** for API, coordinate mapping and evaluation | Missed/duplicate points, semantic mistakes, latency, network dependence |

These choices build on available [Ultralytics detection/export tooling](https://docs.ultralytics.com/models/yolo26/), [GeCo2 code and weights](https://github.com/jerpelhan/GECO2), [CountGD++](https://github.com/niki-amini-naieni/CountGDPlusPlus/) and [Gemini’s documented pointing capability](https://developers.googleblog.com/en/gemini-25-for-robotics-and-embodied-intelligence/).

**Do not run three substantial development projects.** Implement one shared tiling/evaluation system, run approach 2 as an early challenger, and restrict approach 3 to an experiment plus disagreement verification. Select the primary model using held-out results.

A modern model does not automatically establish superiority here. The published **GrainNet** wheat counter reports **MAE 5.97 and “counting accuracy” 94.47% on its own dataset**—useful evidence that grain detection works, but far from proof of near-zero error on your images. Its accuracy definition and image distribution must not be transferred to corn1000. [GrainNet paper](https://link.springer.com/article/10.1186/s13007-025-01363-y)

**2. Existing products: the problem is already partly solved**

Vendor claims below are identified as such; I found no independent comparison of these products on corn1000.

| Product / workflow | What it does | Accuracy evidence and relevance |
|---|---|---|
| **MARViN / MARViTECH**, associated with the GTA seed-analysis product family | Controlled imaging, count, length, width, projected area and size distribution; external weighing supports TKW | Vendor specifies **≥99.5% under defined conditions**, typically **3–5 seconds**, with dry, non-overlapping objects. Strong laboratory comparator, not a handheld-photo benchmark. [Specifications](https://www.marvitech.de/systems-for-seed-analysis-and-measurement/) |
| **Pfeuffer CONTADOR** | Dedicated seed counter using a feeding channel and optical counting; supported by SeedCount software | Established hardware alternative. No numeric error guarantee verified on the examined page. [Product](https://www.pfeuffer.com/product/contador) |
| **Next Instruments SeedCount SC6000** | Scanner/tray-based grain analysis, dimensions, colour and damaged-grain attributes | Relevant laboratory comparator; no verified near-zero handheld-photo claim. [Manufacturer brochure](https://www.nextinstruments.net/index.php/download_file/view/575/145/) |
| **SeedCounter, Android** | White-paper photograph, OpenCV-based counting and morphometry; BSD-licensed research software | Published study reports count MAEs **0.125–1.425** across conditions, but used small samples rather than 1,000 grains. Touching grains and poor lighting caused errors. The paper has confusing units/percentage labels, so do not turn this into a “99.9%” claim. [Study](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2016.01990/full), [app](https://play.google.com/store/apps/details?id=org.wheatdb.seedcounter) |
| **CountThings from Photos** | Commercial counting templates, including seeds; editable detection markers; iOS/Android/Windows | Vendor documents offline processing. No universal seed-count accuracy verified. Offline and manual correction are therefore **not unique differentiators** for us. [FAQ](https://www.countthings.com/en/faq) |
| **Petiole Pro Seed QA** | Seed photographs, calibration reference, size/area statistics and reports | Relevant seed-quality workflow. No independently validated near-zero count accuracy found. [Product](https://www.petiolepro.com/seed-qa/) |
| **PCS SeedCount** | Web workflow advertising A4-photo counting, dimensions and TKW | Very close conceptually; no documented benchmark verified. [Application](https://seedcount.pcs-agri.com/) |
| **ImageJ / SmartGrain / GrainScan / GridFree** | Thresholding, particle measurements, scanner/image-based seed phenotyping; some interactive segmentation | Useful implementation references and auditors. Their existence makes “AI counts seeds from a photo” a weak novelty claim. [ImageJ](https://imagej.net/imaging/particle-analysis), [SmartGrain](https://doi.org/10.1104/pp.112.205120), [GrainScan](https://plantmethods.biomedcentral.com/counter/pdf/10.1186/1746-4811-10-23), [GridFree](https://github.com/12HuYang/GridFree) |
| **KWS / Väderstad / Horsch** | Sowing-rate and machine-setting calculators using inputs such as TKW and germination | These address the downstream calculation; they are potential workflow complements. Väderstad explicitly supports phone/iPad use. [KWS](https://www.kws.com/de/de/digitale-services/), [Väderstad](https://www.vaderstad.com/uk/about-us/news/news-archive/2024/international/new-seed-rate-calculator-available), [Horsch](https://www.horsch.com/us/products/intelligence/digital-solutions/smartclip-guide) |
| **LEMKEN / AMAZONE** | LEMKEN offers remote drill-calibration functions; AMAZONE has photo-assisted fertiliser identification/distribution tools | Adjacent agricultural imaging and calibration, not verified equivalents of cereal-kernel photo counting. [LEMKEN](https://lemken.com/en-en/agricultural-machines/sowing/seed-drills/pneumatic-seed-drills/solitair-xmf), [AMAZONE EasyMatch](https://amazone.net/en/service-support/for-the-press/press-releases/latest/amazone-easymatch-to-be-in-the-myspreader-app-from-january--2117344) |
| **Bayer / BASF** | Reviewed materials describe other agronomic tools, including scouting and seed-rate/quality information | **No matching A4 kernel-counting product verified.** This is a search limitation, not proof that none exists. [Bayer material](https://agrar.bayer.de/-/media/BCSD/Resources/Downloads/Files/Broschueren%202025/Broschuere_Rapssaatgut_SUED_WEST_07_2025.pdf), [BASF material](https://agriculture.basf.com/dam/jcr%3A73d18feb-0338-46e2-9e3f-d9a6bbab587d/basf/agriculture/br/assets/e-books-/IPC_Credenz_E-book_2025.pdf) |

For “what farmers use today,” distinguish **available workflows** from market-share evidence. Manual counting and weighing, counting machines, supplied TKW values and sowing calculators are established options; I did not verify adoption percentages. ISTA describes manual replicated counts and machine-counted pure-seed fractions. [ISTA purity FAQ](https://www.seedtest.org/en/technical-committees/purity-committee/faq-purity-committee.html)

**3. Models, repositories and usable weights**

“Available weights” means a checkpoint/download is documented, not that I downloaded or validated it. Licenses apply to the linked release; dependency and dataset terms remain separate.

| Model / repository | License; weights | Fit and decision for tonight |
|---|---|---|
| **[YOLO26](https://docs.ultralytics.com/models/yolo26/) / [YOLO11](https://docs.ultralytics.com/models/yolo11/)** | AGPL-3.0 or enterprise; pretrained weights available | **Primary candidate.** Train whole/broken/invalid detection. Requires boxes: point labels need conversion. YOLO11 is a reasonable fallback if already working. |
| **[GeCo2](https://github.com/jerpelhan/GECO2)** | MIT; checkpoint available | **First few-shot challenger.** Exemplar-based dense detection/counting; optional SAM2 refinement. Use several representative intact grains. |
| **[CountGD++](https://github.com/niki-amini-naieni/CountGDPlusPlus/)** | MIT; 1.25-GB checkpoint available | Particularly relevant **positive and negative exemplars**. CUDA/Detectron2 installation risk. Demo omits adaptive cropping and pseudo-exemplars; paper reproduction uses externally enhanced crops. Use native-resolution crops for our evaluation. |
| **[CountGD](https://github.com/niki-amini-naieni/CountGD)** | MIT; pretrained weights available | Text plus visual exemplars, point outputs. Useful fallback if its environment is already available. |
| **[GeCo](https://github.com/jerpelhan/GeCo) / [DAVE](https://github.com/jerpelhan/DAVE)** | MIT; weights available | GeCo2 is the more current starting point; DAVE’s detect-and-verify approach is relevant to rejecting outliers. |
| **[P2PNet](https://github.com/TencentYoutuResearch/CrowdCounting-P2PNet)** | Academic-research-only license; crowd checkpoints available | **Direct fit to point supervision.** Individual point proposals are attractive, but old dependencies and crowd-domain weights add adaptation work. |
| **[CSRNet](https://github.com/leeyeehoo/CSRNet-pytorch)** | License not verified in original repository; crowd weights linked | Density-map baseline; original environment is very old. Poorer fit for auditable individual exclusions and morphometry. |
| **[FamNet](https://github.com/cvlab-stonybrook/LearningToCountEverything) / [CounTR](https://github.com/Verg-Avesta/CounTR)** | MIT; pretrained counting weights available | Few-shot density counters. Worth comparing if ready to run, but not first choice for exact instance-level classification. |
| **[Grounding DINO](https://github.com/IDEA-Research/GroundingDINO)** | Apache-2.0; weights available | Text-conditioned boxes; useful component. Default 900 box proposals make a single whole-image pass unsuitable for 1,000 objects. Tile it. |
| **[T-Rex2](https://github.com/IDEA-Research/T-Rex/tree/trex2)** | IDEA License 1.0; API/demo documented; full local weights not verified | Strong visual-prompt concept; API dependence and access make it a secondary experiment. |
| **[SAM](https://github.com/facebookresearch/segment-anything) / [SAM2](https://github.com/facebookresearch/sam2)** | Apache-2.0; weights available | **Use for masks and pseudo-boxes.** Automatic mask count is not automatically object count: paper, parts and duplicate masks require filtering. |
| **[SAM3](https://github.com/facebookresearch/sam3)** | Custom SAM License; gated checkpoints | Text/exemplar-based instance segmentation is highly relevant. Test if access already works, but do not let checkpoint approval or environment setup consume the afternoon. |
| **[Cellpose](https://github.com/MouseLand/cellpose) / [StarDist](https://github.com/stardist/stardist)** | BSD-3-Clause; biological-image weights available | Promising for touching-object separation. Cell/nucleus weights are not grain weights; domain adaptation generally needs masks. |
| **[GrainNet](https://github.com/1371530728/grainnet/tree/master/gainnet)** | Repository license content not retrievable; `best.pt` present | Actual wheat-specific YOLOv7 derivative. Worth a quick inference test; packaging and rights are less clear than the leading options. [Weights directory](https://github.com/1371530728/grainnet/tree/master/gainnet/runs/train/grainnet/weights) |
| **[DINOv2](https://github.com/facebookresearch/dinov2) / [DINOv3](https://github.com/facebookresearch/dinov3)** | DINOv2 general models: Apache-2.0; DINOv3: custom license, gated weights | Strong feature backbones for a small point/classification head. Neither is a ready-made grain counter. |
| **[I-JEPA](https://github.com/facebookresearch/ijepa) / [V-JEPA2](https://github.com/facebookresearch/vjepa2)** | I-JEPA: CC-BY-NC-4.0; V-JEPA2 repository predominantly MIT, check checkpoint terms; weights available | Representation-learning research, not turnkey counting. V-JEPA’s video emphasis is a poor reason to select it for one still photograph. |

Two practical conclusions:

- **Detection and counting metrics are different.** A wheat YOLOv8 study reports high detection mAP, but that does not establish exact counts or performance on your five species and contaminants. Evaluate counts and matched objects explicitly. [YOLOv8 grain study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10934596/)
- **Class-agnostic counting needs semantic stress tests.** Counting intact grains while excluding similar fragments is harder than counting everything resembling an exemplar. Distractor-focused work such as PairTally is directly relevant. [PairTally benchmark](https://github.com/bbvisual/PairTally_Benchmark)

**4. The chessboard/VLM idea: technically sound, accuracy unproven**

**Use coordinate outputs and deterministic aggregation.** A model returning “23” offers no way to distinguish an omission from an extra fragment; a list of 23 points can be inspected.

| Model/API | Grounding capability and availability | Assessment |
|---|---|---|
| **Gemini 2.5 / 3 family** | Proprietary API. Google documents point outputs and normalised coordinates; Gemini 2.5 examples use **`[y,x]` on a 0–1000 scale**. [Pointing documentation](https://developers.googleblog.com/en/gemini-25-for-robotics-and-embodied-intelligence/) | Best low-friction API experiment. Validate the specific model/version and coordinate convention. Newer model names alone do not establish better counting. |
| **Qwen2.5-VL-7B / Qwen3-VL-4B** | Apache-2.0 for these specific checkpoints; open weights, spatial grounding. [Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [Qwen3](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | Credible local experiments. Coordinate and resizing conventions are model-specific; benchmark actual throughput before committing. |
| **MolmoPoint-8B** | Apache-2.0 model release; dedicated grounding tokens and point extraction. [Model](https://huggingface.co/allenai/MolmoPoint-8B) | **Most interesting specialised open VLM for this experiment.** More directly designed for pointing than generic chat vision. |
| **Florence-2** | MIT; base/large weights; structured detection and grounding tasks. [Model](https://huggingface.co/microsoft/Florence-2-large) | Compact candidate for boxes, but no verified near-zero grain-count benchmark. |
| **Moondream** | Hosted `point`/`detect` endpoints. Older moondream2 weights Apache-2.0; current hosted/self-hosted releases have separate terms. [API](https://docs.moondream.ai/api/), [moondream2](https://huggingface.co/vikhyatk/moondream2), [current terms/pricing](https://moondream.ai/pricing) | Practical, structured API challenger. Do not assume the older model’s license covers every current release. |
| **GPT vision / Claude vision** | Proprietary APIs; can produce structured responses. Both vendors document counting/spatial limitations. [OpenAI](https://developers.openai.com/api/docs/guides/images-vision), [Anthropic](https://platform.claude.com/docs/en/build-with-claude/vision) | Useful for explaining/classifying ambiguous crops. No verified basis for treating a full-sheet answer as exact. |
| **Roboflow hosted models** | Deployment service; model weights and licenses depend on the selected model. [Serverless inference](https://docs.roboflow.com/deployment/roboflow-cloud/serverless-api.md) | Convenient hosting for a trained detector, not a separate counting algorithm or accuracy guarantee. |

**What the evidence actually says:** MolmoPoint reports a **74.5 PointBench Count-category score**, versus **59.2 for Gemini 2.5 Pro** and **95.6 for humans**. These are benchmark scores—not percentages of correctly counted cereal kernels, and not exact-count rates for 10–50-object tiles. They justify testing specialised pointing, not promising near-zero error. [MolmoPoint paper](https://arxiv.org/html/2603.28069v1)

VLMCountBench also finds failures on controlled counting tasks, particularly when object types are mixed. Its results cannot be directly extrapolated to separated wheat grains. **I found no trustworthy benchmark establishing reliable exact counts across your proposed 10–50-kernel tiles.** [VLMCountBench](https://arxiv.org/abs/2510.04401)

**Proposed border-safe implementation**

1. Start with an **8×8 grid of ownership regions**: 1,000 evenly distributed kernels would average 15.6 per region.
2. Expand each crop with a **halo large enough to contain a complete boundary grain plus context**. Determine its width from observed grain dimensions.
3. Ask for one point per intact kernel in the entire expanded crop. Obtain broken/invalid points separately where supported.
4. Convert points back to the original coordinate system, undoing all resizing and padding.
5. Count a point only in its owning core: `x0 ≤ x < x1`, `y0 ≤ y < y1`.
6. **Handle seam ambiguity explicitly.** Different predictions can place the same grain’s centre on opposite sides of a boundary. Reprocess a seam crop or match overlapping predictions, fuse their centre, and then assign ownership.
7. Use one-to-one matching with distance **and appearance/mask evidence**. A broad radius-based merge can wrongly combine two touching grains.
8. Sum accepted point records in code. Detect truncated responses and retry. Never provide the expected whole-sheet count to the model.

This is an engineering proposal; half-open ownership prevents deterministic duplication, but cannot fix missed or mislocated model predictions.

The reliability requirement is severe: if each of 64 tiles is exactly correct with probability 99%, and errors are independent, the probability that **all tiles** are correct is only `0.99^64 ≈ 52.6%`. Reaching 95% all-tile correctness would require about **99.92% correctness per tile**. Total-count errors can cancel, so total accuracy alone can conceal failures.

**Illustrative API cost, not a measured bill**

Assume **1,000 input tokens and 400 output tokens per tile**, including image input in the assumed input budget; 50–100 tiles; no caching, retries or additional reasoning tokens. Actual image tokenisation and output length must be measured.

| API/version | USD per million input/output tokens | Calculated cost per 50–100-tile photograph |
|---|---:|---:|
| Gemini 2.5 Flash | $0.30 / $2.50 | **$0.065–0.13** |
| Gemini 3 Flash Preview | $0.50 / $3.00 | **$0.085–0.17** |
| Gemini 3.8 Flash, current introductory pricing | $0.75 / $3.75 | **$0.113–0.225** |
| Gemini 3.1 Pro, short-context tier | $2 / $12 | **$0.34–0.68** |
| Moondream 3.1 | $0.30 / $1.00 | **$0.035–0.07** |
| GPT-4.1, reference comparator | $2 / $8 | **$0.26–0.52** |
| Claude Sonnet 5.5 | $2 / $10 | **$0.30–0.60** |

Sources: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing), [Moondream pricing](https://moondream.ai/pricing), [GPT-4.1 pricing](https://developers.openai.com/api/docs/models/gpt-4.1), [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing). Older requested versions are included deliberately; they are not all current flagships.

**Latency is unverified.** As a planning scenario, 3–10 seconds per tile with eight concurrent requests yields approximately **21–130 seconds** for 50–100 tiles, before upload, throttling and retries. Benchmark 20 representative tiles, including empty tiles, touching grains and debris. For normal operation, send only disputed crops; full-sheet VLM processing is the expensive challenger.

**5. “JEV-style models”: likely JEPA, but DINO is the more practical interpretation**

“JEV” is not a model name I could verify. The likely intended family is **JEPA**, especially Meta’s **I-JEPA or V-JEPA**. I-JEPA learns image representations by predicting masked representations; V-JEPA focuses on visual/video representation learning. Neither supplies a ready-made grain-counting head. [I-JEPA](https://github.com/facebookresearch/ijepa), [V-JEPA2](https://github.com/facebookresearch/vjepa2)

**DINOv2/v3 are different self-supervised approaches**, and Grounding DINO is a different detection system again. For this still-image task, a pretrained DINO backbone plus a small point head is a more direct experiment than adopting a video model. DINOv2 offers ViT-S/14; DINOv3 offers ViT-S/16 and dense feature applications. [DINOv2](https://github.com/facebookresearch/dinov2), [DINOv3](https://github.com/facebookresearch/dinov3)

Proposed implementation:

- Preserve enough crop resolution that a kernel spans several backbone patches.
- Freeze the encoder initially; train an upsampling head producing **kernel/broken/invalid centre heatmaps and subpixel offsets**.
- Train from the supplied points; detect local maxima and classify them.
- If training a density map instead, normalise each target kernel to integrate to one. An arbitrary confidence heatmap cannot simply be summed as a count.
- Use object-crop embeddings for a small intact/broken/foreign classifier if full point-head development is too slow.

**Could it beat the detector? Yes, plausibly; is that established here? No.** It avoids pseudo-box errors but introduces custom training, peak extraction and small-object resolution choices. Tonight I would make it the contingency if point-to-box conversion fails—not pretrain JEPA/DINO on 836 photographs.

**6. Concrete primary pipeline**

The following is the proposed implementation, with libraries and failure checks.

**A. Canonical image and paper geometry**

Use Pillow’s `ImageOps.exif_transpose` once. The project says labels refer to upright images: verify overlays and avoid applying orientation twice. Detect the paper quadrilateral with OpenCV, with a four-corner tap fallback. Warp to a known A4 coordinate plane for measurements; retain original imagery and transform mappings. [Pillow orientation](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html), [OpenCV transforms](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html)

For example, a 2,100×2,970 working plane represents 10 pixels/mm; resampling does **not** create additional optical detail. Exclude the fiducial from candidate objects. Use ArUco detection only after identifying the actual marker dictionary; “fiducial” does not automatically mean ArUco. [OpenCV ArUco](https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html)

**B. Split before generating crops or pseudo-labels**

Hold out complete **sessions**, following the repository rules. Do not let neighbouring crops or repeat photographs of the same arrangement cross the split. Audit annotation completeness and class frequencies before treating every unlabelled region as background.

Use point-labelled images for supervised localisation. The remaining count-labelled images can support separate evaluation; adding weakly supervised training tonight is optional, not essential.

**C. Convert points to reliable object boxes**

Use annotated points as seeds:

- For isolated objects, foreground segmentation and connected components provide a candidate mask.
- For touching clusters, use point-seeded watershed or SAM2 with the target point positive and neighbouring grain points negative.
- Reject masks that contain several labelled objects or obviously include paper.
- Generate a bounding box per accepted object and inherit its point-label class.
- Inspect a stratified sample across species, lighting and contaminants before training.

This combines a modern trainable detector with targeted mask generation. Watershed and SAM2 provide the relevant mechanisms. [OpenCV watershed](https://docs.opencv.org/4.x/d3/db4/tutorial_py_watershed.html), [SAM2](https://github.com/facebookresearch/sam2)

**D. Fine-tune on Kaggle T4**

Use `uv` for project Python tooling. Start with pretrained **YOLO26s**, or YOLO11s if that environment already works. Proposed starting settings: 640–1,024-pixel crops, mixed precision, batch size adjusted to memory, 30–80 epochs with held-out early selection. These are starting parameters, not measured optimal settings. [Ultralytics training](https://docs.ultralytics.com/modes/train/)

Augment rotation, exposure, mild blur and scale; oversample broken/invalid examples and difficult clusters. Avoid transforms that make the training task unlike the actual paper photographs.

Preserve local detail through tiling. Check detection caps: Ultralytics commonly defaults to **`max_det=300`**, which is inadequate for a full 1,000-object image. Set an explicit sufficient cap and verify exported inference too. [Configuration reference](https://docs.ultralytics.com/usage/cfg/)

**E. Fuse spatial predictions and inspect disagreements**

Apply the same core/halo ownership scheme as above. Maintain one record per object:

`centre, class, confidence, source tile, optional mask, review status`

Run an independent foreground/connected-component audit. Flag:

- foreground regions with no detected object;
- multiple detections inside a plausible single-object mask;
- touching clusters;
- disagreement between the trained model and GeCo2/VLM;
- uncertain whole-versus-broken classification.

Do not average two total counts. Resolve object-level disagreements. Keep human corrections separate from the automatic result when reporting performance.

**F. Evaluate the real task**

**The 85-image test set has a structural trap: every true count is 1,000.** A constant-output program would obtain perfect count error without examining pixels. Therefore:

- Select thresholds/models only on a **session-held-out, variable-count validation set**.
- Freeze the pipeline, then evaluate the required `count_1000` test.
- Report MAE, median/p95/max absolute error, signed bias, exact-count rate and fractions within ±1/±2/±5.
- Where point labels exist, report one-to-one matched precision/recall and class confusion.
- Show per-species and difficult-case results where metadata permits.
- Keep a few independently checked overlays: equal totals can hide one omission plus one false positive.

The all-1,000 fact comes from your supplied dataset description; the evaluation consequences above are mathematical deductions.

**7. Broken kernels, foreign material and useful measurements**

**Learn exclusions from examples, not a single area threshold.** Small intact kernels must remain countable under your challenge rules. A size threshold can confuse them with fragments; MARViN’s documented size-based broken-grain filtering illustrates why a product’s settings are not automatically your scoring rules. [MARViN FAQ](https://www.marvitech.de/service/faq/)

Use the existing three annotation classes as the initial taxonomy. Add visually diverse training crops of awns, chaff, stones and foreign seeds to `invalid` where labels permit. Do not claim reliable subcategories without corresponding ground truth. CountGD++ negative exemplars offer a useful no-training test of this distinction. [CountGD++](https://github.com/niki-amini-naieni/CountGDPlusPlus/)

For morphometry, use masks on the corrected paper plane: projected length, width, area, aspect ratio and distributions. Report uniformity as a named statistic—for example, coefficient of variation of width—not a vague quality score. Bounding boxes alone are a poor substitute for shape measurements. Grain phenotyping tools already demonstrate these image-derived measurements. [GrainScan](https://plantmethods.biomedcentral.com/counter/pdf/10.1186/1746-4811-10-23), [GridFree](https://academic.oup.com/plphys/article/186/4/2239/6274909)

**Weight and germination remain external inputs.** TKW requires the mass of the same accepted grain population that was counted:

\[
\mathrm{TKW\ [g]}=\frac{1000\,m_{\text{accepted grains}}\,[g]}{N_{\text{accepted grains}}}
\]

If fragments are excluded from the count but included in the weighing, TKW is biased. Clean/reweigh the accepted fraction or explicitly identify that limitation. ISTA’s method uses the pure-seed fraction. [ISTA guidance](https://www.seedtest.org/api/rm/2346XE3QX287V56/guidelines-for-the-establishment-and-management-of.pdf)

For target established plants \(P\) per m², germination fraction \(g\), and establishment fraction \(e\):

\[
\mathrm{kg/ha}=\frac{P\cdot \mathrm{TKW}}{100\,g\,e}
\]

If the input is already **seeds to sow per m²**, do not apply germination again. Väderstad’s calculator distinguishes relevant sowing inputs and losses. [Seed-rate calculator](https://www.vaderstad.com/us-en/products/vaderstad-seedeye/seed-rate-calculator)

A terminology correction matters for the pitch: the official **ISO 520 scope explicitly excludes seed lots for sowing**. Implement the challenge’s supplied counting rules, but do not describe the prototype as ISO-certified seed testing. I did not inspect the full standard. [ISO scope](https://committee.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/05/22/52270.html?browse=ics)

**8. iPad and offline deployment**

**Tonight’s practical route:** a simple German web interface, initially connected to the working inference backend; export the small detector to ONNX and attempt local inference only after the counting pipeline is stable. Ultralytics supports ONNX and CoreML exports. [Export documentation](https://docs.ultralytics.com/modes/export/)

For genuine on-device operation:

- Cache the application, model and runtime assets.
- Use ONNX Runtime Web; feature-detect WebGPU and retain a WASM fallback.
- Test the exact exported operators and actual iPad.
- Reload and perform a complete count in airplane mode.

**Safari 26 supports WebGPU**, including on iPadOS. ONNX Runtime’s published browser table still lists Safari WebGPU as unsupported, so the documentation conflicts; actual runtime/model testing is essential. [WebKit Safari 26 announcement](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/), [ONNX Runtime Web](https://onnxruntime.ai/docs/get-started/with-javascript/web.html)

CoreML is a strong native deployment path using Apple hardware, but a new native application adds build/signing/integration work. TF.js offers browser WebGL/WASM options, although ONNX is the more direct proposed export path here. [CoreML](https://developer.apple.com/documentation/coreml), [TF.js backends](https://www.tensorflow.org/js/guide/platform_environment)

A laptop inference server over local Wi-Fi can work without internet, but should be described accurately as **local-network operation**, not on-device inference.

Proposed farmer flow: **Foto → markierte Körner prüfen → Gewicht/Keimfähigkeit eingeben → TKG und kg/ha**. Show only disputed objects prominently; keep an optional complete overlay.

**9. Work allocation and five-minute pitch**

Proposed remaining-afternoon schedule, working backwards from 22:00:

| Period | Person A: counting | Person B: delivery/evaluation |
|---|---|---|
| First 45 minutes | Session split, annotation overlays, pseudo-box quality check | Shared evaluator, image/EXIF pipeline, minimal German UI |
| Next 90 minutes | Start detector training | GeCo2 challenger; small Gemini tile benchmark |
| Until 20:00 | Inspect errors, one targeted improvement | Border handling, review UI, TKW/rate calculation |
| **20:00–20:30** | Select and freeze model/thresholds | Run required test and assemble evidence |
| **20:30–21:15** | Export/deployment support | Test actual iPad; attempt offline route if feasible |
| **21:15–22:00** | Fix demonstrated failures only | Rehearse demo; preserve a working fallback |

Use strict installation cutoffs: an unavailable checkpoint or broken research environment must not consume the integration window.

The strongest pitch is **a measured, inspectable path from the farmer’s own grain sample to a sowing decision**. Existing products already count seeds, measure dimensions and calculate rates; the proposed advantage must be demonstrated through your combination of accuracy, exclusions, simple operation and low equipment needs. [MARViN](https://www.marvitech.de/systems-for-seed-analysis-and-measurement/), [CountThings](https://www.countthings.com/en/faq), [Väderstad](https://www.vaderstad.com/uk/about-us/news/news-archive/2024/international/new-seed-rate-calculator-available)

Suggested five-minute sequence:

1. **Problem:** “Die eigene Partie hat ihr eigenes Tausendkorngewicht.”
2. **Live workflow:** photograph, visible kernel markers, one disputed fragment corrected.
3. **Evidence:** actual held-out count errors and failure examples—automatic results clearly separated from corrected results.
4. **Decision:** measured sample weight → TKG → understandable sowing rate.
5. **Practicality:** demonstrate the actual iPad deployment and state its connectivity requirement precisely.

A suitable promise is: **“Jedes gezählte Korn ist sichtbar. Unsichere Stellen prüfen Sie gezielt.”** Claims of higher accuracy than commercial products, ISO certification or fully offline operation should wait for the corresponding evidence.