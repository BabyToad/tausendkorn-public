# Audience-facing web deck

Serve the repository with `uv run python -m http.server 8020` and open
<http://localhost:8020/pitch/web/>. The deck carries visible dataset attribution on
each slide. Hidden speaker notes have been removed.

PDF/PPTX exports, slide renders and internal speaker scripts are excluded from this
snapshot. The private export was not retained because its licensing line and embedded
notes/metadata were not cleared here.

With the dataset downloaded as described in the main README, regenerate assets using:

```bash
uv run python pitch/build_assets.py
uv run python pitch/build_web_data.py
```

These scripts read committed `results/argon_v1.0.2/` predictions. The hardware image
builder uses the retained representative CAD render; the current pitch image remains
the original audience-facing image. Photos and embedded data: see
[DATA_LICENSE.md](../DATA_LICENSE.md).
