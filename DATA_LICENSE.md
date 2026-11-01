# Dataset attribution and asset provenance

**corn1000 — Smart Farming Lab, Universität Leipzig.**

- Dataset: <https://huggingface.co/datasets/SmartFarmingLab/corn1000>
- License: [Creative Commons Attribution–NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/)
- Modification notice: **modified: resized, cropped, marks/overlays added**. Some images were EXIF-rotated and JPEG-reencoded; screenshots embed these images in the app UI.

Dataset-derived files are CC BY-NC 4.0 and are excluded from the code license (AGPL-3.0-only, see `LICENSE`). Retain this credit, the dataset and license links, and the modification notice when sharing those assets. The full dataset is excluded as a packaging choice. The code license remains undecided before publication; this document does not license third-party components, model weights, or independently owned code.

The retained JSONs contain model-predicted coordinates, model comments, evaluation statistics, and copied reference counts/metadata. They do not contain the full original `kernel_points`, `broken_points` or `invalid_points` annotation arrays; identically named fields in audit summaries are aggregate totals. Attribution applies to the copied dataset material. We do not assert that every independently generated prediction or statistic acquires a CC license merely because it was evaluated against the dataset.

## Retained assets

Paths below cover every retained dataset-bearing asset or folder. Paths containing only code are not listed as data assets. Source filenames are explicit below or preserved in the individual JSON's `file_name`/`photo_original` field and filenames. Split names refer to corn1000's `data/train` or `data/test` layout.

| Retained path | Source and modifications |
|---|---|
| `app/mock/foto.jpg` | `train/S03/S03-014_galaxy-tab-s6-lite_20260916_162825.jpg`; EXIF rotation and JPEG reencoding. One functional mock sample. |
| `app/mock/result.json` | Same S03-014 photo; predicted points and review regions, copied reference count 410; original path in `photo_original`. |
| `design/shared/probe.jpg`, `design/shared/sample.js` | Same S03-014 photo; resized/cropped study image and scaled predictions from the mock result. Required by the three HTML design studies. Redundant screenshot exports excluded. |
| `docs/app/screens/01_neue_probe.png` through `08_foto_warnung.png` | Mock UI screenshots using S03-014 above where a grain photo appears; overlays and example inputs added. Pairing-history screenshot excluded. |
| `docs/app/screens/echt/pc_02_foto.png` through `pc_05_alle_markierungen.png` | `train/S04/S04-014_galaxy-tab-s6-lite_IMG_20261015_140950.jpg`; PC upload/count screenshots, predicted marks and example inputs. |
| `docs/app/screens/echt/01_neue_probe.png` through `05_alle_markierungen.png` | Live app screenshots: own winter-barley iPad photo (Team Goldpfanne), as recorded in `docs/RESULTS.md`; no claim that this team photo belongs to corn1000. Any corn1000-derived UI/sample content remains covered by this attribution. Pairing-history screenshot excluded. |
| `results/teaser.jpg` | Crop from the barley holdout overlay `train/S03/S03-006_iphone-8_IMG_6228.jpg`; matched predictions/reference marks added. Source identified by image-feature matching against the retained overlays (298 matches; other barley candidates 5–12). |
| `results/overlays/` | All 36 final Argon benchmark photos: 30 holdout inputs from train, six test inputs. Exact source names in the `holdout__`/`test__` filenames and matching `results/argon_v1.0.2/{holdout,test}/*.jpg.json`. Resized images with TP/FP/FN or predicted marks. |
| `results/befund/` | `durum_crop.jpg`, `durum_timeline.jpg`, `test_durum_outlier.jpg`: Hartweizen `test/count_1000/count_1000-001_*` series (17 photos), including `count_1000-001_galaxy-s23_IMG_20261026_165756.jpg`; crops/contact timeline and Argon/YOLO marks. Duplicate copies under docs were removed. |
| `results/argon_v1.0.2/` | Final 30 holdout and six test prediction JSONs, manifests and logs. Source filenames/reference counts in each record; model output and evaluation statistics are distinguished from original labels above. |
| `results/yolo11s/` | 40 holdout and 85 test prediction JSONs. Source filenames in record names/fields; predictions, copied counts and evaluation metadata. No weights included. |
| `results/dev4/` | Prediction JSONs for `S02/S02-014_galaxy-s23_20261002_160345.jpg`, `S03/S03-014_galaxy-tab-s6-lite_20260916_162825.jpg`, `S04/S04-014_galaxy-tab-s6-lite_IMG_20261015_140950.jpg`, `S05/S05-014_iphone-8_IMG_6604.jpg`. Includes model comments/traces and copied reference counts; redundant overlay JPGs removed. |
| `runs/audit/astra_evidence/{summary,box_stats,coverage}.json` | Only the three committed aggregate audit-statistics files. Dataset splits, filenames and aggregate annotation/coverage statistics; image contact sheets/crops and all other runs excluded. |
| `site/img/stack/` | Six explanatory images derived from `train/S02/S02-008_galaxy-s23_20261002_150020.jpg`: EXIF, mask, quadtree, tile, review spot and result illustrations. Reproduction: `scripts/build_stack_images.py`. |
| `pitch/web/img/{roggen_997,roggen_clean,titel_roggen}.jpg` | `test/count_1000/count_1000-002_galaxy-s23_IMG_20261026_184810.jpg`; cropped/resized, with predicted marks where shown. |
| `pitch/web/img/{hafer_pruefstelle,hafer_zoom,hafer_stelle_clean}.jpg` | `train/S02/S02-008_galaxy-s23_20261002_150020.jpg`; cropped/resized, predicted marks/review regions where shown. |
| `pitch/web/data.js` | Scaled model points, tile and check regions, and copied counts for the rye and oat photos above. |
| `results/index.html` | Generated gallery summary and reference counts from the retained benchmark records; embeds the separately attributed result images. |
| `splits/{train,dev,holdout}.txt` | Dataset source filenames selected for the project splits; no image pixels or original point arrays. |

`pitch/web/img/pfanne.jpg` and `hardware/` renders depict synthetic CAD concepts, not corn1000 photos. `site/img/team/` contains team portraits, not dataset images. Other HTML/CSS/JS UI code embeds the assets listed above without adding further retained image copies.

## Generated assets (not included in this snapshot)

`uv run python scripts/build_site.py`, after a local dataset download, creates `site/img/s/` (benchmark photos and thumbnails), `site/data/s/` (scaled model predictions), `site/data/samples.json` (copied counts and predictions), `site/img/app/` (cropped mock screenshots), `site/img/og.jpg` (rye pitch crop), and `site/pitch/` (copy of the attributed web deck). These are covered by the corresponding source entries above and must carry the same attribution when distributed. `site/tokens.css` is generated code, not dataset material.

The pitch image/data builders read committed `results/argon_v1.0.2/` records and the local dataset; `build_assets.py` uses a portable font fallback. PDF/PPTX exports, rendered slides, internal scripts and duplicate `pitch/assets/` are not distributed. No exported presentation is implied to be cleared for redistribution.
