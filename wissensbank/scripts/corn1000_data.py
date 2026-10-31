"""
corn1000_data.py - Datensatz SmartFarmingLab/corn1000 lokal bereitstellen und sauber splitten.

Warum exportieren statt immer load_dataset? Einmal sauber als JPEG + Tabelle ablegen, dann arbeiten alle
Skripte (OpenCV, pandas, Kaggle, iPad-Demo) offline und schnell auf denselben Dateien.

    python corn1000_data.py export --out ../../data/corn1000_export            (laedt aus dem Hub)
    python corn1000_data.py export --out ... --limit 40 --sessions S04         (Schnelltest)
    python corn1000_data.py export --out ... --from-disk <save_to_disk-Ordner> (offline/Kaggle-Cache)
    python corn1000_data.py index  --src ../../data/corn1000 --out ../../data/corn1000_index   (bereits heruntergeladener Ordner)
    python corn1000_data.py info   --meta ../../data/corn1000_export/metadata.csv

Ergebnis in <out>/:  images/<session>/<datei>.jpg · metadata.csv · points.jsonl · export_info.json
`index` kopiert keine Bilder: es liest den Hub-Download (`<src>/data/<split>/metadata.jsonl`, wie in src/tausendkorn/eval.py)
und schreibt nur metadata.csv + points.jsonl (Bildpfade zeigen auf die Originale).
Im Code:
    from corn1000_data import load_meta, load_points, session_folds, holdout_sessions
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATASET_ID = "SmartFarmingLab/corn1000"
POINT_COLS = ["kernel_points", "broken_points", "invalid_points"]
META_COLS = ["count", "arrangement_id", "session", "step", "take", "species", "pollution", "camera", "taken_at"]


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def _load_ds(from_disk: str | None, split: str, token: str | None):
    if from_disk:
        from datasets import load_from_disk
        ds = load_from_disk(from_disk)
        return ds[split] if hasattr(ds, "keys") and split in ds else ds
    from datasets import load_dataset
    return load_dataset(DATASET_ID, split=split, token=token)


def export(out: Path, split: str = "train", sessions=None, limit: int | None = None,
           from_disk: str | None = None, quality: int = 95, max_side: int | None = None, token: str | None = None):
    """Schreibt Bilder (EXIF-korrigiert, ohne EXIF-Tag), metadata.csv und points.jsonl."""
    from PIL import ImageOps

    ds = _load_ds(from_disk, split, token)
    cols = set(ds.column_names)
    missing = {"image", "count", "session"} - cols
    if missing:
        raise SystemExit(f"Erwartete Spalten fehlen: {missing}. Vorhanden: {sorted(cols)}")
    out = Path(out)
    (out / "images").mkdir(parents=True, exist_ok=True)

    rows, n_written = [], 0
    with open(out / "points.jsonl", "w", encoding="utf-8") as fp:
        for i in range(len(ds)):
            r = ds[i]
            if sessions and r["session"] not in sessions:
                continue
            if limit and n_written >= limit:
                break
            img = ImageOps.exif_transpose(r["image"]).convert("RGB")     # idempotent; Punkte gelten im aufrechten Bild
            scale = 1.0
            if max_side and max(img.size) > max_side:
                scale = max_side / max(img.size)
                img = img.resize((round(img.width * scale), round(img.height * scale)))
            sess = str(r["session"])
            (out / "images" / sess).mkdir(exist_ok=True)
            stem = f"{r.get('arrangement_id') or 'x'}_{i:04d}"
            rel = f"images/{sess}/{stem}.jpg"
            img.save(out / rel, quality=quality)

            pts = {k: ([[float(x) * scale, float(y) * scale] for x, y in r[k]] if r.get(k) else None) for k in POINT_COLS}
            fp.write(json.dumps({"file": rel, **pts}) + "\n")
            row = {"file": rel, "row": i, "width": img.width, "height": img.height, "scale": scale}
            row.update({c: r.get(c) for c in META_COLS})
            for k in POINT_COLS:
                row[f"n_{k}"] = len(pts[k]) if pts[k] is not None else np.nan
            rows.append(row)
            n_written += 1
            if n_written % 50 == 0:
                print(f"  {n_written} Bilder ...")
    meta = pd.DataFrame(rows)
    meta.to_csv(out / "metadata.csv", index=False)
    json.dump({"dataset": DATASET_ID, "split": split, "n_images": len(meta), "sessions": sessions,
               "limit": limit, "max_side": max_side, "points_in_upright_pixel_coords": True},
              open(out / "export_info.json", "w"), indent=2)
    print(f"{len(meta)} Bilder -> {out.resolve()}")
    return meta


# --------------------------------------------------------------------------- #
# Index: bereits heruntergeladener Ordner (hf download --local-dir data/corn1000)
# --------------------------------------------------------------------------- #
def _as_points(v):
    """Punktlisten koennen als Liste, JSON-String oder None vorliegen."""
    if v is None or v == "":
        return None
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return None
    return [[float(x), float(y)] for x, y in v] if v else None


def index_local(src: Path, out: Path, splits=None):
    """
    Liest <src>/data/<split>/metadata.jsonl (oder <src>/<split>/metadata.jsonl) ohne Bilder zu kopieren.
    Schreibt <out>/metadata.csv (mit Spalte `split`) und <out>/points.jsonl.
    """
    from PIL import Image
    src, out = Path(src), Path(out)
    base = src / "data" if (src / "data").is_dir() else src
    out.mkdir(parents=True, exist_ok=True)
    found = [d for d in sorted(base.iterdir()) if d.is_dir() and (d / "metadata.jsonl").exists()]
    if splits:
        found = [d for d in found if d.name in splits]
    if not found:
        raise SystemExit(f"Keine <split>/metadata.jsonl unter {base} gefunden. Ordnerinhalt: {[x.name for x in base.iterdir()][:10]}")
    rows = []
    with open(out / "points.jsonl", "w", encoding="utf-8") as fp:
        for d in found:
            for line in open(d / "metadata.jsonl", encoding="utf-8"):
                r = json.loads(line)
                path = d / r["file_name"]
                with Image.open(path) as im:
                    w, h = im.size
                    if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):           # EXIF: Bild liegt seitlich gespeichert
                        w, h = h, w
                rel = Path(os.path.relpath(path, out)).as_posix()
                pts = {k: _as_points(r.get(k)) for k in POINT_COLS}
                fp.write(json.dumps({"file": rel, **pts}) + "\n")
                row = {"file": rel, "split": d.name, "width": w, "height": h}
                row.update({c: r.get(c) for c in META_COLS})
                for k in POINT_COLS:
                    row[f"n_{k}"] = len(pts[k]) if pts[k] is not None else np.nan
                rows.append(row)
    meta = pd.DataFrame(rows)
    meta.to_csv(out / "metadata.csv", index=False)
    print(f"{len(meta)} Bilder in {len(found)} Splits ({', '.join(d.name for d in found)}) -> {out.resolve()}")
    return meta


# --------------------------------------------------------------------------- #
# Laden / Splits
# --------------------------------------------------------------------------- #
def load_meta(meta_csv) -> pd.DataFrame:
    """metadata.csv laden; fuegt absoluten Pfad `path` hinzu."""
    p = Path(meta_csv)
    df = pd.read_csv(p)
    df["path"] = [str(p.parent / f) for f in df["file"]]
    return df


def load_points(meta_csv) -> dict[str, dict]:
    """{file: {kernel_points, broken_points, invalid_points}} aus points.jsonl neben metadata.csv."""
    out = {}
    with open(Path(meta_csv).parent / "points.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out[d.pop("file")] = d
    return out


def session_folds(df: pd.DataFrame):
    """Leave-one-session-out: erzeugt (val_session, train_idx, val_idx). Verhindert Leckage durch Wiederholungsfotos."""
    for s in sorted(df["session"].unique()):
        yield s, df.index[df["session"] != s].to_numpy(), df.index[df["session"] == s].to_numpy()


def holdout_sessions(df: pd.DataFrame, val_sessions):
    """Festes Hold-out: val = angegebene Sessions, Rest = train."""
    val = df["session"].isin(list(val_sessions))
    return df.index[~val].to_numpy(), df.index[val].to_numpy()


def describe(df: pd.DataFrame) -> str:
    g = df.groupby("session").agg(bilder=("file", "count"), arrangements=("arrangement_id", "nunique"),
                                  art=("species", lambda s: ",".join(sorted(set(map(str, s))))),
                                  verschmutzung=("pollution", lambda s: ",".join(sorted(set(map(str, s))))),
                                  min_count=("count", "min"), max_count=("count", "max"),
                                  mit_punkten=("n_kernel_points", lambda s: int(s.notna().sum())))
    lines = [g.to_string(), ""]
    if "split" in df.columns:
        lines.append(f"Splits: {df['split'].value_counts().to_dict()}")
    lines += [f"Gesamt: {len(df)} Bilder, {df['arrangement_id'].nunique()} Arrangements",
             f"Kameras: {df['camera'].value_counts().to_dict()}"]
    if (df["count"] == 1000).any():
        lines.append(f"Bilder mit count == 1000: {(df['count'] == 1000).sum()} (Test-Split `count_1000`)")
    else:
        lines.append("Hinweis: kein Bild mit count == 1000 (nur train-Sessions, max. 800 Koerner; der Test-Split liegt in data/test).")
    d = (df["n_kernel_points"] - df["count"]).dropna()
    if len(d):
        lines.append(f"Punkt-Labels vs. count: Differenz im Mittel {d.mean():+.2f}, |max| {d.abs().max():.0f} (count bleibt das Label)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--out", required=True)
    e.add_argument("--split", default="train")
    e.add_argument("--sessions", nargs="*", default=None)
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--from-disk", default=None)
    e.add_argument("--max-side", type=int, default=None, help="laengste Bildkante begrenzen (z.B. 3000), spart Platz/Zeit")
    e.add_argument("--token", default=None)
    x = sub.add_parser("index", help="bereits heruntergeladenen Ordner (data/<split>/metadata.jsonl) indizieren")
    x.add_argument("--src", required=True, help="z.B. ../../data/corn1000")
    x.add_argument("--out", required=True)
    x.add_argument("--splits", nargs="*", default=None)
    i = sub.add_parser("info")
    i.add_argument("--meta", required=True)
    a = ap.parse_args()
    if a.cmd == "export":
        export(Path(a.out), a.split, a.sessions, a.limit, a.from_disk, max_side=a.max_side, token=a.token)
    elif a.cmd == "index":
        index_local(Path(a.src), Path(a.out), a.splits)
    else:
        print(describe(load_meta(a.meta)))


if __name__ == "__main__":
    main()
