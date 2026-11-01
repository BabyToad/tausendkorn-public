# Archive status

Public-release snapshot of private development `main` at `2a72c7a`, prepared after the Smart Farming Lab hackathon, Universität Leipzig, 27–28 October 2026. Team Goldpfanne: Leon Böhlau and Jonas Heinke.

Built: adaptive-tile Gemini counting, a FastAPI field app with mock mode, review/edit workflow, TKG and sowing-rate calculator, REST/MCP interfaces, a static project site, a web pitch and exploratory hardware concepts. YOLO experiments were evaluated separately and are not integrated into the app.

The frozen v1.0.2 benchmark is documented in [RESULTS.md](RESULTS.md), with rules and caveats in [PROTOCOL.md](PROTOCOL.md). Predictions, logs and final overlays are in [results](../results/README.md). Post-submission blur training was measured on dev only and does not replace that benchmark. Weights are withheld; see [models](../models/README.md).

This is a hackathon prototype that can miss or double-count kernels. Confirmed seam, verification and paper-detection defects remain; see the dated [engineering review](reviews/2026-10-28_astra_roadmap.md). Proposals in roadmap/design documents are not promises of implemented behavior. No open-branch or PR work is included.

Project code is licensed [AGPL-3.0-only](../LICENSE). Dataset-derived assets have a separate [license and provenance record](../DATA_LICENSE.md).
