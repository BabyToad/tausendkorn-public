# Astra: Roadmap und Fehlersuche Zählpipeline (28.10.2026)

Auftrag: Roadmap-Ideen aus der Lernsession bewerten, Code nach neuen Fehlern durchsuchen, Ursache der iPad-Doppelmarken klären. Read-only, keine API-Aufrufe. Die Seam-Befunde (Ecke, Reihenfolge) hat die Hauptsession synthetisch nachgestellt: reproduzierbar.

**Cause (1) is strongly supported by the saved iPad run. I also found new, reproducible seam-merging and verification defects.** I would fix those and add duplicate highlighting before investing in an agent.

I read the requested files, challenge/protocol documents and yesterday’s reviews. All checks were read-only, with synthetic model responses where needed; no API calls or secrets accessed. References below use checkout `8ba69b2`. Its current fingerprint is `96ab0b87a763`, reflecting subsequent experimental additions; the seam, verification and tiling logic implicated below also exists in the frozen version.

**A. Confirmed defects**

1. **High: seam matching can both invent an extra count and collapse two real kernels into one.**
   Locations: [bench_vlm.py:341](../../src/tausendkorn/bench_vlm.py#L341), [bench_vlm.py:347](../../src/tausendkorn/bench_vlm.py#L347), [bench_vlm.py:469](../../src/tausendkorn/bench_vlm.py#L469).

   Two distinct synthetic failures reproduce:

   - **Four-tile corner:** one kernel produces one owned observation and three margin observations. The owned point consumes one margin partner; the two remaining margins pair with each other, creating another count. With `L=100`, observations `(85,85)`, `(84,85)`, `(100,90)`, `(103,90)` produce `(84.5,85)` and `(101.5,90)`. Both survive the 5-pixel dedup radius.
   - **Order-dependent undercount:** two owned points at `(90,80)` and `(90,110)` encounter margin observations at `(90,120)` and `(90,95)`. First-match pairing produces averages `(90,100)` and `(90,102.5)`; dedup deletes one. Reversing only the margin observations produces `(90,87.5)` and `(90,115)`, preserving both kernels.

   Thus, “two owned points are never merged” does **not** protect them from being moved together and subsequently deduplicated. Thread completion order is not responsible—`ex.map` preserves tile order—but model point ordering can change the result.

   **Fix:** preserve owned-point identities and coordinates. Associate margin observations as supporting evidence; do not let independent pair averages become the count representation. Flag ambiguous associations and margin-only groups. Avoid replacing this with unrestricted connected-component merging: chains can swallow adjacent oats.

2. **Medium: verification silently ignores corrections, then accepts confidence based on those unapplied corrections.**
   Locations: [verify.py:116](../../src/tausendkorn/verify.py#L116), [verify.py:132](../../src/tausendkorn/verify.py#L132), [pipeline.py:64](../../src/tausendkorn/pipeline.py#L64).

   Removal validation requires an ID to be visible in the crop, but application additionally requires ownership by the core. A response removing a visible halo marker therefore validates, gets silently ignored, and is recorded as `removed: 1`. If confidence is `1.0`, no check flag remains.

   I reproduced that exact outcome. I also reproduced an addition at normalized coordinate `1050`: the parser accepts it, application discards it outside the core, the note reports `added: 1`, and confidence `1.0` suppresses review.

   **Fix:** validate proposed edits against the region where they can actually be applied before accepting the response. Retry or flag inconsistent edits; record proposed and applied edits separately. Never clear uncertainty using confidence conditional on a correction that was not performed.

3. **Medium: a correctly visible white sheet can be rejected because the brightness threshold excludes tied values.**
   Location: [adaptive.py:25](../../src/tausendkorn/adaptive.py#L25).

   `L > percentile(L, 60)` produces no bright pixels when the percentile equals the maximum. A synthetic dark background with a large white A4-like rectangle and a visible brown kernel raises `ValueError("no white sheet found in the photo")`. Uniform off-white paper also reproduces it.

   This is relevant to clipped highlights and flat backgrounds, not only an empty-sheet curiosity.

   **Fix:** handle percentile ties explicitly, with a fallback that still checks brightness and region size. Merely changing `>` to `>=` without safeguards could classify a uniform dark image as paper. Test blank paper, clipped white paper, uniform dark input and ordinary textured photographs.

4. **Medium: evaluation and the app disagree about whether failed verification makes a result usable.**
   Locations: [pipeline.py:61](../../src/tausendkorn/pipeline.py#L61), [final.py:50](../../src/tausendkorn/final.py#L50), [server.py:261](../../app/server.py#L261).

   The pipeline intentionally retains first-pass points after exhausted verification retries and flags the region. `final.complete()` accepts that result. The app rejects the same result because a note contains `failed`.

   A synthetic result with successful first-pass tiles and one failed verification returns **complete in evaluation, incomplete in the app**.

   **Fix:** define one shared contract separating *count coverage complete* from *verification completed*. Given the existing pipeline behavior, a complete first-pass count with mandatory human review is reasonable. If the product instead requires rejection, evaluation must report that rejection too.

   This is a contract defect; I have not established that it affected the published measurements.

5. **Medium: paid failed attempts disappear from app cost accounting.**
   Location: [server.py:300](../../app/server.py#L300).

   `IncompleteCount` carries `cost_usd`, but the exception handler stores only status and error. Injecting `IncompleteCount(..., cost_usd=0.37)` confirmed that the update omits the cost. A later successful retry records its own cost, leaving the earlier spend unaccounted for.

   **Fix:** persist each attempt’s cost and outcome, including exceptions, and expose cumulative sample cost separately from the latest attempt. Unexpected failures after paid work also need a way to preserve accrued usage.

**Plausible risks and checked boundaries**

- **The A4 estimate is not only a tiling aid.** `L` also controls margin retention, automatic seam matching and deduplication. An incorrect paper hull therefore changes counting decisions. Perspective makes a single global `L` questionable. This strengthens the case for advisory highlighting rather than a larger automatic merge radius.
- **Retries and budgets are not tightly bounded.** Three outer attempts can each invoke four HTTP attempts with 600-second timeouts. `final.py` checks an estimated cost before each image, not an enforceable per-image ceiling. Add a deadline and explicit attempt budget before adding agent rounds.
- **App preprocessing differs from benchmark preprocessing.** [server.py:254](../../app/server.py#L254) recompresses the uploaded image to JPEG before counting; benchmark input goes directly through `load_image`. Dimensions remain consistent, but pixels change. Any effect on counts remains unmeasured.
- I found no demonstrated `[y,x]` swap error: pass one swaps Gemini output once; verification explicitly consumes `[y,x]`. EXIF orientation and full-resolution coordinate use are consistent.
- Adaptive boundary anchoring preserves outer coverage. Dense leaves can exceed the nominal 15-kernel estimate because the minimum-side stop takes precedence; this is a soft target, not a hard guarantee.
- Standalone dedup is order-dependent for chains: `[0,4,8]` at radius 5 retains two points, while `[4,0,8]` retains one. That is a general limitation of greedy suppression; the more consequential confirmed defect is seam averaging creating such collisions.

**B. What happened on the iPad**

I inspected the saved sample and correction events in the application database, reconstructed the adaptive cores from the stored full-resolution photo, and inspected the matching call log.

For sample 2, `L ≈ 74.82 px`:

| Pair | Separation | Reconstructed core IDs | Shared seam | User removed |
|---|---:|---|---:|---|
| `m155`, `m168` | 5.52 px = **0.0737 L** | 72 / 78 | `x = 1888` | `m155` |
| `m176`, `m179` | 6.23 px = **0.0833 L** | 80 / 81 | `x = 1700` | `m179` |

Both pairs straddle a seam and sit just beyond the **0.05 L** dedup threshold. The next-closest pair is approximately **0.572 L** apart. A **0.3 L highlight would flag exactly these two pairs on this photograph**, without changing the count.

The matching log contains **103 successful compact calls, all attempt 0, and no verification calls**.

My ranking is therefore:

1. **Cause (1): strongly supported.** Both suspect pairs sit across ownership boundaries exactly where the protection against merging two owned points applies.
2. **Cause (2): still possible, but less supported.** Raw observations and merge associations were not retained, so a more complicated same-tile duplication pathway cannot be excluded.
3. **Cause (3): ruled out for this run.** There was no verification pass.

One correction to the premise: **cores reconstruct geometric ownership, not necessarily source-tile provenance.** Averaging can move a merged point across a core boundary. The saved evidence strongly supports cause (1), but cannot prove the exact sequence of source observations.

The offline investigation above needs no API. For definitive future diagnosis, save raw mapped observations with tile ID and `own`, merge associations, dedup decisions, and verification edits. The app currently discards even much of the diagnostic information returned by `count_kernels`. A compact trace sidecar is sufficient.

**C. Roadmap ranking and critique**

Ranking your six ideas by practical value relative to effort:

| Rank | Idea | Recommendation |
|---|---|---|
| 1 | **1 — Duplicate highlighting** | Ship after the basic geometry fixes. High value, small implementation. |
| 2 | **4 — Confidence calibration** | Essential before treating the 0.9 gate as meaningful. |
| 3 | **2 — Distance calibration** | Useful support for highlighting; insufficient justification for automatic merging. |
| 4 | **6 — Protocol and datasets as durable assets** | Strong strategy; strengthen reproducibility and collect fresh sessions. |
| 5 | **3 — Structured flags** | Add only codes with a measured, useful downstream action. |
| 6 | **5 — Agent escalation** | Defer until a simpler bounded escalation has demonstrable shortcomings. |

**1. Highlighting:** I agree with the asymmetric-cost argument. Group nearby suspect pairs into one review region, retain both marks, and let the farmer remove one or confirm both. Do not flood the interface with every edge in a cluster. Measure review burden as well as detection: flagged groups per photo, duplicates found, duplicates missed, and accidental deletions of genuine kernels. False highlights stop being cheap when users learn to dismiss them.

**2. Threshold calibration:** Label nearest-neighbour distances tell you how close *real distinct kernels* can be. They do not tell you how far apart duplicate predictions can land. You need both distributions: true neighbours and manually classified duplicate predictions from cached development runs. Use image/species summaries rather than treating thousands of correlated points as independent evidence. A low percentile still permits real neighbours below it, so it cannot establish a safe merge threshold. Keep oats as a required stress case.

**3. Structured flags:** Prefer a small set of actionable flags over a taxonomy. `CLUSTER` and `OCCLUDED` could help direct inspection. `SEAM` is already available geometrically and need not consume model output. A model-generated `BLUR` flag should initially suggest inspection or another photo, not automatically reject the image without calibration. Missing flags must never mean “safe.” Evaluate whether the changed prompt affects point accuracy.

**4. Confidence calibration:** Use **one-to-one point matching**, not count agreement, to define a correct tile: a miss and a duplicate can cancel numerically. Measure two separate things:

- How well confidence identifies errors, including confidently wrong tiles.
- Whether verification actually repairs those errors, and how often it introduces new ones.

A reliability curve alone does not establish that verification helps. Include a preselected sample of high-confidence tiles in future development experiments; the existing gate otherwise hides that evidence.

**5. Agent escalation:** Start with one deterministic escalation step: show a flagged region, its neighbouring seam context and all existing marks, then request bounded structured edits. Compare that with an independent local detector’s disagreement signal. Only introduce an agent if choosing additional views or tools improves outcomes enough to justify the extra latency and failure paths.

The existing agent experiments already show why caution is justified: reported confidence, stopping behavior and mark counts are unreliable in some runs. An agent should never modify its production policy during evaluation. Freeze its tools, prompts, budgets and termination rules just as you freeze the ordinary pipeline.

**6. Strategic bet:** The durable-asset argument is sound; the disappearance of tiling is speculative. Whole-image spatial resolution, coverage and auditability may remain valuable even as models improve. Let measurements retire components.

Also, a source fingerprint is necessary but insufficient: record model identifier/revision where available, request settings, preprocessing, dependency versions, input hash and raw responses. Current source hashing includes unrelated experiments yet cannot freeze a hosted model’s behavior.

**Minimal post-pitch sequence**

1. **Make failures replayable and fix the confirmed defects.** Preserve compact traces; add offline regression cases for corner multiplicity, ordering, ignored verification edits and failure accounting. Keep the published v1.0.2 artifacts unchanged.
2. **Add advisory duplicate highlighting.** Start from cached development predictions, validate across species, and retain explicit human decisions. Do not enlarge automatic dedup.
3. **Evaluate the verification gate and its actual benefit.** Include high-confidence errors and point-level outcomes. In parallel, collect genuinely new sessions with independently established counts and varying sample sizes.
4. **Only then trial structured flags or one bounded escalation step.** An open-ended agent remains optional.

The most valuable missing work is **trace retention plus fresh, independent field data**. Both improve every future model comparison without adding another counting subsystem.

Verdict: The most important new defect is order-dependent seam pairing that can create extra counts or collapse distinct kernels; top-3 roadmap items are replayable traces and geometry fixes, calibrated duplicate highlighting, and measurement of confidence-gated verification.
