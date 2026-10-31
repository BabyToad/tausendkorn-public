# Astra-Abschlussreview B: Code, Sicherheit, Schnellstart

GPT-6 Astra (Codex, nur lesend), 27.10.2026 21:33, Stand 52ca19c. Pflichtpunkt (Mock-Foto) ging an die App-Lane; „after submission“ ist die offene Liste.

**Verdict: FIX BEFORE UPLOAD — one reproducible ZIP-demo defect on `main` (`52ca19c`).**

**must fix before upload (≤5, file:line, concrete fix)**

1. **[app/server.py:277](../../app/server.py), [app/mock/result.json:1](../../app/mock/result.json): Mock photo missing from ZIP.** The fixture references an untracked `data/corn1000/...jpg`. On a fresh checkout, the app silently keeps the reviewer’s uploaded photo but overlays the fixture’s 411 unrelated kernel coordinates. **Fix:** commit the matching photo under `app/mock/`, update the fixture path, and fail clearly if it is missing. Verify one complete mock upload from an extracted ZIP without `data/`.

**after submission**

- **Correction validation:** [app/server.py:602](../../app/server.py) accepts events missing `id` or `of`; `replay()` then raises `KeyError`. Reproduced with pure-function checks. Use typed event schemas, bounded coordinates and validated references.
- **Upload limits:** [app/server.py:436](../../app/server.py) checks 30 MB after multipart parsing has already spooled the upload. Enforce a request-body limit before parsing.
- **CSV formula injection:** [app/server.py:651](../../app/server.py) exports user-controlled text unchanged. Neutralize spreadsheet formula prefixes in text fields.
- Add fresh-ZIP upload/overlay and pipeline-failure tests; existing tests primarily cover REST/MCP using synthetic database rows.
- Housekeeping: 624 tracked files, **172.5 MB uncompressed**, largest 7.2 MB; 49 historical `runs/` files remain tracked despite `.gitignore`.

Read-only checks: all tracked Python files parse; pipeline, MCP and required runtime imports succeed in the existing environment; project dependency declarations match lockfile metadata. No recognizable secrets or credential files found; required ignore rules are present.

**Fresh-machine installation and full pytest execution were not run:** they require filesystem writes. Startup appears structurally sound, but `uv sync` success is not independently verified.