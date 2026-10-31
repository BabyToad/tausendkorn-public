"""
merge_labels.py - Bild-Feature-Tabelle (summary.csv) mit Label-Tabelle (z.B. TKM je Bild) verbinden.

Dateinamen werden normalisiert (ohne Endung, klein, ohne Leerzeichen/Bindestriche), damit
"IMG_001.jpg" und "img-001" zusammenpassen.

Aufruf:
  python merge_labels.py --features ../outputs/seg/summary.csv --labels ../data/raw/labels.xlsx \
         --features-key image --labels-key Probe --out ../outputs/train_table.csv
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from eda_tabular import load_table


def norm(name) -> str:
    stem = Path(str(name)).stem
    return re.sub(r"[\s_\-]+", "", stem).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--features-key", default="image")
    ap.add_argument("--labels-key", default="image")
    ap.add_argument("--out", default="../outputs/train_table.csv")
    a = ap.parse_args()

    f = load_table(a.features)
    l = load_table(a.labels, a.sheet)
    f["_key"] = f[a.features_key].map(norm)
    l["_key"] = l[a.labels_key].map(norm)
    if l["_key"].duplicated().any():
        print("WARNUNG: Doppelte Schluessel in Labels:", l.loc[l["_key"].duplicated(), a.labels_key].tolist())
    m = f.merge(l.drop(columns=[a.labels_key]), on="_key", how="left", suffixes=("", "_label"))
    missing = m[m.drop(columns=["_key"]).columns.difference(f.columns)].isna().all(axis=1)
    print(f"Bilder: {len(f)} | Labels: {len(l)} | zugeordnet: {int((~missing).sum())} | ohne Label: {int(missing.sum())}")
    if missing.any():
        print("Ohne Label:", m.loc[missing, a.features_key].tolist()[:20])
    unused = set(l["_key"]) - set(f["_key"])
    if unused:
        print(f"Labels ohne Bild: {len(unused)} (Beispiele: {list(unused)[:5]})")
    m.drop(columns=["_key"]).to_csv(a.out, index=False)
    print("->", Path(a.out).resolve())


if __name__ == "__main__":
    main()
