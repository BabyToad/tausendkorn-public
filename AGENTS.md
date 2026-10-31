# Tausendkorn contributor guidance

Hackathon prototype: count cereal kernels in an A4 photo and calculate thousand-kernel weight and sowing rate. User-facing language is German; keep the field workflow simple.

- Read `docs/STATUS.md` and `docs/CHALLENGE.md` before changing model or UI behavior.
- Follow `docs/PROTOCOL.md`: choose parameters on dev only. Preserve the frozen v1.0.2 benchmark and report new experiments separately. The reused holdout and small test set are not fresh validation data.
- Use Python 3.12 and uv. Run `uv run pytest -q` for app/API changes.
- Keep datasets, runtime databases, uploaded photos, tokens, weights and experiments under ignored `data/`, `models/` or `runs/`. Never commit credentials or pairing QR screenshots.
- Check `DATA_LICENSE.md` before copying or publishing dataset-derived assets. Code licensing is pending the owner's decision.
- Known defects and proposed fixes are in `docs/reviews/2026-10-28_astra_roadmap.md`; this snapshot preserves main's implementation.
