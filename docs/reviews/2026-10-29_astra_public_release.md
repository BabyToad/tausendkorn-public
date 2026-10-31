> Public-snapshot editorial note: local paths and third-party identities have been anonymised; links to withheld files are shown as text. Original review remains in the private archive.

**Publish a cleaned fresh repository and keep this one private as the development archive.** The main blockers are pairing credentials embedded in screenshots, incomplete asset licensing, and unresolved checkpoint licensing—not an API key found in source.

Reviewed `main` at `12617f3`: 658 tracked files, 181 main-history commits, and 200 commits/1,028 blobs across available refs. I used `git log --all -p`, credential-pattern scans, asset metadata inspection, QR decoding, and GitHub PR metadata/comments. I changed nothing, called no paid APIs, and did not open the prohibited files.

**MUST before public**

- **Remove exposed pairing credentials.** docs/app/screens/09_verlauf.png (nicht im öffentlichen Snapshot enthalten) and docs/app/screens/echt/06_verlauf.png (nicht im öffentlichen Snapshot enthalten) contain readable QR codes encoding LAN URLs with actual six-digit pairing codes. Replace both with screenshots using clearly synthetic pairing details, including the QR image. Rotate the corresponding pairing codes **and device tokens** before further use. `app/server.py:94–103` persists these across restarts. The screenshots entered history in `b7322c1` and `6329ae0`; replacing them does not erase those versions.

- **Exclude both checkpoints from the initial public snapshot pending licensing clarification:** `models/yolo11s-dev.pt` **and** `models/yolo11s-blur.pt`. Each is approximately **18.37 MiB**. Safe inspection of their serialized metadata found:
  - An explicit **Ultralytics AGPL-3.0** license notice.
  - Local `<private training directory>` training paths.
  - Training provenance involving CC BY-NC data.

  Do not describe these weights as simply MIT or CC BY-NC. Training on NC data does not, by itself, settle the checkpoint’s copyright/license status; adding an NC notice also does not resolve its interaction with AGPL terms. Retain training code, hashes and measured results while clarifying redistribution and commercial-use rights. Ultralytics documents its AGPL/Enterprise licensing separately. [Ultralytics licensing](https://www.ultralytics.com/license)

- **Add an explicit license boundary.** There is **no repository `LICENSE` file**. My conservative recommendation for the current codebase, retaining its Ultralytics integration, is **AGPL-3.0-only for your own code**, with contributor agreement. MIT is an option for independently owned app/VLM code, but must not purport to license third-party code or weights.

  Add `DATA_LICENSE.md` and an asset-provenance manifest. Credit **corn1000 — Smart Farming Lab, Universität Leipzig**, link the dataset and CC BY-NC 4.0 license, identify source filenames and modifications, and explicitly exclude dataset material from the code license. CC requires attribution, the license link and modification notices; it permits noncommercial sharing, so blanket removal of all sample images is unnecessary. [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

- **Cover every retained dataset-derived asset, not just `results/overlays/`.** The manifest should include:
  - `app/mock/foto.jpg`, `app/mock/result.json`.
  - `results/teaser.jpg`, `results/overlays/`, `results/befund/`, `results/dev4/` and evaluation JSONs.
  - `docs/befund/*.jpg`, dataset-bearing `docs/app/screens/`.
  - `design/shared/probe.jpg`, `design/shared/sample.js`, design screenshots.
  - `site/img/stack/`, generated site sample images/data.
  - Dataset-bearing `pitch/assets/`, `pitch/web/img/`, rendered slides, PDF and PPTX.
  - `runs/audit/astra_evidence/` contact sheets and crops.

  Keep a small, attributed mock sample and useful evidence. Remove redundant copies. Existing notices in `app/mock/README.md`, `design/README.md`, `results/README.md` and the site footers are a good start; the exported pitch needs a credits/license notice too.

  **Correction to the premise:** committed JSONs contain model-predicted coordinates and copied reference counts. I did not find full original `kernel_points`/`broken_points`/`invalid_points` coordinate arrays; those keys in the audit summary contain aggregate totals. Document this distinction rather than automatically declaring every prediction or statistic CC-licensed.

- **Resolve the pitch’s third-party identity and private drafting content.** pitch/DREHBUCH.md (nicht im öffentlichen Snapshot enthalten) introduces **an unverified presenter** as a presenter/team member, contradicting the stated Jonas/Leon team. This identity also appears in the PPTX speaker notes; the script has a PDF export. Verify the role and permission, or remove the internal scripts/notes from the public package. Keep a corrected, audience-facing deck.

  Remove the “Nachricht an die Veranstalter” draft from [docs/befund/DURUM_COUNT_1000.md](../befund/DURUM_COUNT_1000.md#L58). Keep the scientific observation and counterarguments. Avoid implying that contact occurred when the record only establishes a proposed message.

- **Choose publication scope before changing visibility.** A visibility toggle exposes historical files, remote branches and PR discussions—not merely cleaned `main`. GitHub currently lists **21 branches** and **19 PRs, #12–#30**; #30 is the only open PR. Leave it unmerged as requested. Its latest description explicitly says the seam merge remains unchanged and the development version is unmeasured.

  Actions runs/logs and release assets remain **unverified**: the connector lacked a complete inventory operation and CLI requests were network-blocked. Audit those before toggling this repository public. GitHub explicitly warns that Actions history/logs become public. [GitHub visibility documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)

**SHOULD**

- **Correct stale claims against `docs/RESULTS.md`.** `README.md:79`, `results/README.md:19`, `ABGABE.md:34` and `src/tausendkorn/gpu/yolo.py:11` say the blur model has not been trained/measured. It has: `RESULTS.md` documents its post-submission dev evaluation. Update these statements without mixing those results into the frozen benchmark.

  The headline numbers are sound: I recomputed **MAE 5.93 on 30 holdout images**, **15.83 on six test images**, and ±3% coverage of **26/30** and **5/6**. Preserve the within-session, reused-holdout and small-test caveats. The pitch labels 99.9% as a target, not an achieved result.

- **Expose main’s known limitations at the entry point.** Link the confirmed seam, verification and paper-detection defects from `README.md` to `docs/reviews/2026-10-28_astra_roadmap.md`. Describe the app as a hackathon prototype that can miss or double-count kernels. Publication does not require merging #30, but newcomers should not mistake main for the proposed fixes.

- **Replace internal coordination documents with an archive/status summary.** `docs/STATUS.md` still contains active lane ownership, started sessions, budgets and obsolete PR states. `AGENTS.md` still specifies the expired deadline and concurrent-session workflow. Archive or shorten `docs/GPU_BRIEF.md`, hardware `ASTRA_BRIEF.md` files and unfinished `wissensbank/notes/` templates. Preserve useful reviews as dated engineering evidence.

- **Remove unnecessary personal details and repair links.**
  - Replace absolute links in `docs/reviews/2026-10-28_astra_roadmap.md` and `hardware/pfanne/ASTRA_REVIEW_v0.md` with repository-relative or commit-pinned links.
  - Replace **RTX 3070 workstation** with “RTX 3070 workstation” where the machine identity adds no value.
  - Review **a farmer from the organiser side** and **a challenge representative**, their affiliations and attributed expectations in `docs/CHALLENGE.md`, `docs/IDEEN.md`, `docs/PROBLEMFAELLE.md` and `wissensbank/04_Hackathon_Timeline_Pitch.md`. Public professional credits may remain if accurate; remove unsupported commitments or implied endorsements.
  - Private-archive commit metadata exposes a personal email address. Several PR reviews also contain local Windows paths. A cleanup commit cannot remove either.
  - The PPTX’s `lastModifiedBy` is **Steve Canny**, apparently inherited template metadata; replace it with accurate metadata.

- **Make setup reproducible for a newcomer.** Keep the current mock-first quickstart, adding clone/`cd`, Python **3.12**, and `uv sync --locked`. Explain the separate paths for mock app, paid Gemini counting, dataset evaluation, optional GPU experiments and static-site building. Document `uv run python scripts/build_site.py`: several site assets are intentionally generated and ignored. `pitch/build_assets.py` currently depends on private `runs/final/` paths and a Windows font; adapt it to committed results and a portable font fallback.

  I did not launch the app or run setup because those operations write runtime files.

- **Keep runtime data out of publication.** `data/app/` and `data/app-demo/` contain SQLite databases, pairing codes and device tokens; uploaded photos live under `data/app/photos/`. They are ignored and were not found in tracked history. Retain that exclusion. Add `.claude/` to `.gitignore`; its untracked `launch.json` includes personal paths and temporary-session locations. Export an explicit tracked-file allowlist, not the whole working directory.

**NICE**

- **Reduce repository size.** Tracked files total approximately **204 MiB**; the local Git object store is approximately **213 MiB**. Largest groups: `hardware/` **111.68 MiB**, models **36.73 MiB**, results **25.86 MiB**, pitch **13.45 MiB**. Keep hardware source, one representative render and useful manufacturing outputs; move redundant renders, simulations and export variants out of the initial snapshot. Deleting them in a normal commit will not shrink historical clones.

- **Keep a clear documentation spine:** `README.md`, `docs/CHALLENGE.md`, `docs/PROTOCOL.md`, `docs/RESULTS.md`, selected reviews, `docs/app/{UX,DATA,SAATGUTRECHNER,API,MCP}.md`, `results/README.md`, split lists and provenance manifests. Date design alternatives and exploratory research so readers can distinguish proposals from implemented behavior.

- **Repair secondary documentation.** `wissensbank/03_Tech_Stack_Code.md` references missing `distributions.png`, `correlation.png` and `target_scatter.png`. Explain their generation or remove the links. Correct dataset-sharing wording in `wissensbank/05_Datensatz_corn1000.md`: CC BY-NC permits attributed noncommercial redistribution; “must not enter the repo” is a project packaging choice.

The credential scans found **no API-key literals, private keys, Cloudflare account/zone IDs, or textual token-bearing URLs** in the scanned project files/history. Keyring references such as `tokenkit/GEMINI_API_KEY` are lookup names, not credentials. No `.env*` or `credentials.json` names appeared in the accessible project tree/history. No personal phone numbers or full coding-session transcripts were identified; there are agent-authored reviews, model comments and benchmark logs. The inaccessible `.pytest_cache`, dependency internals, arbitrary encoded binary content and unavailable GitHub artifacts prevent an exhaustive “secret-free” guarantee. The screenshot QR credentials are a confirmed exception to the negative text scans.

**History decision:** no API-key-driven rewrite is indicated. Rotating the exposed pairing credentials makes historical copies unusable, but removing the screenshots, checkpoints, personal email, paths and draft from public history requires more than ordinary deletion. A fresh public repository avoids rewriting this working archive and avoids carrying its PR discussions and experimental branches forward. Preserve the original benchmark commit IDs as provenance, explicitly noting that they refer to the private archive.

Verdict: Publish a cleaned fresh repository after the MUST items; keep BabyToad/tausendkorn private as the development archive.
