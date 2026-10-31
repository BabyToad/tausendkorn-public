"""
eda_tabular.py - Schnelle explorative Datenanalyse fuer CSV/Excel (deutsche Formate inklusive).

Aufruf:
  python eda_tabular.py --csv ../data/raw/messwerte.xlsx --target tkm_g --out ../outputs/eda
  python eda_tabular.py --csv ../data/raw/daten.csv            (ohne Zielvariable)

Erzeugt: eda_report.md + PNGs (Verteilungen, Korrelationen, Scatter, Boxplots)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_DE_NUM = re.compile(r"^\s*-?\d{1,3}(\.\d{3})*(,\d+)?\s*$|^\s*-?\d+(,\d+)?\s*$")


def load_table(path, sheet=None) -> pd.DataFrame:
    """Liest CSV/TSV/XLSX; erkennt Trennzeichen, Encoding und Dezimalkomma automatisch."""
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(p, sheet_name=sheet or 0)
    else:
        df = None
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(p, sep=None, engine="python", encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        if df is None:
            raise ValueError(f"Encoding nicht erkennbar: {p}")
    df.columns = [str(c).strip() for c in df.columns]
    # Dezimalkomma ("45,3") -> float
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) or not (
                pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])):
            continue                                    # pandas>=3: Textspalten haben Dtype "str", nicht "object"
        s = df[c].dropna().astype(str)
        if len(s) and s.map(lambda x: bool(_DE_NUM.match(x))).mean() > 0.9:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                errors="coerce")
    return df


def iqr_outliers(s: pd.Series) -> int:
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())


def run_eda(df: pd.DataFrame, target: str | None, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    num = df.select_dtypes(include="number")
    cat = df.select_dtypes(exclude="number")
    L = ["# EDA-Report", "", f"- Zeilen: **{len(df)}**, Spalten: **{df.shape[1]}**",
         f"- Duplikate (komplette Zeilen): {int(df.duplicated().sum())}",
         f"- Numerisch: {len(num.columns)}, Kategorial/Text: {len(cat.columns)}", ""]

    miss = (df.isna().mean() * 100).round(1)
    L += ["## Fehlende Werte (%)", "", miss[miss > 0].to_frame("missing_%").to_markdown() if (miss > 0).any()
          else "Keine fehlenden Werte.", ""]
    L += ["## Numerische Statistik", "", num.describe().T.round(3).to_markdown(), ""]
    out_counts = {c: iqr_outliers(num[c].dropna()) for c in num.columns if num[c].nunique() > 5}
    L += ["## Ausreisser (IQR-Regel, Anzahl)", "",
          pd.Series(out_counts, name="n_outliers").to_frame().to_markdown() if out_counts else "-", ""]
    if len(cat.columns):
        L += ["## Kategoriale Spalten", ""]
        for c in cat.columns:
            L.append(f"- **{c}**: {df[c].nunique()} Werte; Top: {df[c].value_counts().head(5).to_dict()}")
        L.append("")

    # Verteilungen
    if len(num.columns):
        cols = list(num.columns[:24])
        n = len(cols)
        r, k = int(np.ceil(n / 4)), min(4, n)
        fig, axes = plt.subplots(r, k, figsize=(4 * k, 2.8 * r), squeeze=False)
        for ax, c in zip(axes.ravel(), cols):
            ax.hist(num[c].dropna(), bins=30, color="#4C78A8")
            ax.set_title(c, fontsize=9)
        for ax in axes.ravel()[n:]:
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(out / "distributions.png", dpi=110)
        plt.close(fig)
        L += ["## Verteilungen", "", "![](distributions.png)", ""]

    # Korrelationen
    if len(num.columns) >= 2:
        corr = num.corr(numeric_only=True)
        fig, ax = plt.subplots(figsize=(min(14, 0.5 * len(corr) + 4),) * 2)
        im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)), corr.columns, rotation=90, fontsize=7)
        ax.set_yticks(range(len(corr)), corr.columns, fontsize=7)
        fig.colorbar(im, shrink=0.7)
        fig.tight_layout()
        fig.savefig(out / "correlation.png", dpi=110)
        plt.close(fig)
        L += ["## Korrelationen", "", "![](correlation.png)", ""]

    # Zielvariable
    if target and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
        pear = num.corr()[target].drop(target).dropna()
        spear = num.corr(method="spearman")[target].drop(target).dropna()
        tab = pd.DataFrame({"pearson": pear, "spearman": spear}).sort_values("pearson", key=abs, ascending=False)
        L += [f"## Zusammenhang mit Ziel `{target}`", "", tab.head(15).round(3).to_markdown(), ""]
        top = tab.index[:6]
        fig, axes = plt.subplots(2, 3, figsize=(12, 7))
        for ax, c in zip(axes.ravel(), top):
            ax.scatter(num[c], df[target], s=14, alpha=0.7)
            ax.set_xlabel(c)
            ax.set_ylabel(target)
        fig.tight_layout()
        fig.savefig(out / "target_scatter.png", dpi=110)
        plt.close(fig)
        L += ["![](target_scatter.png)", ""]
        for c in cat.columns:
            if 1 < df[c].nunique() <= 12:
                g = df.groupby(c)[target].agg(["count", "mean", "std"]).round(3)
                L += [f"### `{target}` nach `{c}`", "", g.to_markdown(), ""]

    rp = out / "eda_report.md"
    rp.write_text("\n".join(L), encoding="utf-8")
    return rp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="CSV oder Excel-Datei")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--target", default=None)
    ap.add_argument("--out", default="../outputs/eda")
    a = ap.parse_args()
    df = load_table(a.csv, a.sheet)
    print(df.head(), "\n", df.dtypes)
    print("->", run_eda(df, a.target, Path(a.out)).resolve())


if __name__ == "__main__":
    main()
