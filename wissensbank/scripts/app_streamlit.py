"""
app_streamlit.py - Interaktive Demo: Bild hochladen -> Koerner zaehlen/vermessen -> TKM schaetzen.

Start (PowerShell, im Ordner scripts):   streamlit run app_streamlit.py
"""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from grain_segmentation import (SegConfig, aggregate_image_features, analyze_image,
                                calibrate_mass_factor, estimate_tkm)
from tkm_utils import (TKM_REFERENCE_G, plausibility_check, sieve_fractions, tkm_from_sample,
                       tkm_to_reference_moisture)

st.set_page_config(page_title="Tausendkorn-Analyse", layout="wide")
st.title("Tausendkorn-Analyse")
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "images"


@st.cache_data(show_spinner="Segmentiere ...")
def run_analysis(img_bytes: bytes, cfg_dict: dict):
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    df, overlay, summary = analyze_image(img, SegConfig(**cfg_dict))
    return df, cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), summary


# ------------------------------ Sidebar ------------------------------------ #
with st.sidebar:
    st.header("Skalierung")
    scale_mode = st.radio("Massstab", ["mm/px direkt", "Referenzmuenze im Bild", "keiner (nur Pixel)"])
    mm_per_px = st.number_input("mm pro Pixel", 0.001, 1.0, 0.1, 0.001, format="%.4f") \
        if scale_mode == "mm/px direkt" else None
    ref_mm = st.number_input("Muenzdurchmesser [mm]", 5.0, 60.0, 25.75, 0.05) \
        if scale_mode == "Referenzmuenze im Bild" else None

    st.header("Segmentierung")
    channel = st.selectbox("Kanal", ["auto", "gray", "S", "b", "a", "L", "R", "G", "B"])
    method = st.selectbox("Schwellwert", ["otsu", "adaptive", "fixed"])
    fixed_t = st.slider("Fixer Schwellwert", 0, 255, 128) if method == "fixed" else 128
    watershed = st.checkbox("Beruehrende Koerner trennen (Watershed)", True)
    flat = st.checkbox("Beleuchtung korrigieren (Flatfield)", False)
    drop_border = st.checkbox("Randkoerner ausschliessen", True)
    blur = st.slider("Glaettung (Sigma)", 0.0, 4.0, 1.5, 0.1)

    st.header("TKM")
    tkm_mode = st.radio("Methode", ["A: Wiegen + Zaehlen", "B: Flaechenmodell (Masse-kalibriert)", "Nur Geometrie"])
    total_mass = st.number_input("Gewogene Probenmasse [g]", 0.0, 10000.0, 0.0, 0.1) \
        if tkm_mode != "Nur Geometrie" else 0.0
    crop = st.selectbox("Kultur (Plausibilitaet)", ["-"] + list(TKM_REFERENCE_G))
    moist = st.number_input("Kornfeuchte [%]", 0.0, 40.0, 14.0, 0.5)
    ref_moist = st.number_input("Bezugsfeuchte [%] (0 = TS)", 0.0, 40.0, 14.0, 0.5)

cfg = dict(channel=channel, method=method, fixed_threshold=fixed_t, watershed=watershed,
           flatfield=flat, drop_border=drop_border, blur_sigma=blur,
           mm_per_px=mm_per_px, ref_diameter_mm=ref_mm)

# ------------------------------ Eingabe ------------------------------------ #
files = st.file_uploader("Bilder (JPG/PNG/TIF)", type=["jpg", "jpeg", "png", "tif", "tiff"],
                         accept_multiple_files=True)
use_sample = st.checkbox("Synthetisches Beispielbild verwenden", value=False)
inputs: list[tuple[str, bytes]] = [(f.name, f.getvalue()) for f in files]
if use_sample and SAMPLE_DIR.exists():
    first = sorted(SAMPLE_DIR.glob("*.png"))[:1]
    inputs += [(p.name, p.read_bytes()) for p in first]
if not inputs:
    st.info("Bild hochladen oder Beispielbild aktivieren.")
    st.stop()

all_grains, all_summaries = [], []
for name, data in inputs:
    df, overlay, s = run_analysis(data, cfg)
    st.subheader(name)
    c1, c2 = st.columns([3, 2])
    c1.image(overlay, caption="gruen = Einzelkorn, orange = per Watershed getrennt, rot = ungeloester Cluster")
    if len(df) == 0:
        c2.error("Keine Koerner gefunden - Kanal/Schwellwert aendern.")
        continue
    n_corr = int(s["n_grains_blob_corrected"])
    c2.metric("Koerner (erkannt)", s["n_grains"])
    c2.metric("Koerner (Cluster-korrigiert)", n_corr)
    if s.get("mm_per_px"):
        c2.metric("mm/px", f"{s['mm_per_px']:.4f}")
        c2.write(f"Laenge {s['mean_length_mm']:.2f} mm | Breite {s['mean_width_mm']:.2f} mm")

    tkm = None
    if tkm_mode.startswith("A") and total_mass > 0:
        tkm = tkm_from_sample(total_mass, n_corr)
        c2.metric("TKM (Wiegen+Zaehlen)", f"{tkm:.1f} g")
    elif tkm_mode.startswith("B") and total_mass > 0 and "area_mm2" in df:
        k = calibrate_mass_factor(df, total_mass)
        tkm, lo, hi = estimate_tkm(df, k)
        c2.metric("TKM (Flaechenmodell)", f"{tkm:.1f} g", f"95%-KI {lo:.1f}-{hi:.1f}")
    if tkm is not None:
        tkm_ref = tkm_to_reference_moisture(tkm, moist, ref_moist)
        c2.write(f"Auf {ref_moist:.0f} % Bezugsfeuchte: **{tkm_ref:.1f} g**")
        if crop != "-":
            c2.caption(plausibility_check(crop, tkm_ref))

    if "width_mm" in df:
        fr = sieve_fractions(df["width_mm"].values)
        c2.write("Siebfraktionen nach Kornbreite [%]:")
        c2.dataframe(pd.Series(fr, name="Anteil %").round(1).to_frame())

    df.insert(0, "image", name)
    all_grains.append(df)
    s.update(aggregate_image_features(df))
    s["image"] = name
    all_summaries.append(s)
    with st.expander("Einzelkorn-Tabelle & Verteilungen"):
        st.dataframe(df)
        col = "area_mm2" if "area_mm2" in df else "area_px"
        st.bar_chart(np.histogram(df[col], bins=30)[0])

if all_grains:
    st.divider()
    buf = io.StringIO()
    pd.concat(all_grains).to_csv(buf, index=False)
    st.download_button("Einzelkoerner (CSV)", buf.getvalue(), "grains.csv", "text/csv")
    buf2 = io.StringIO()
    pd.DataFrame(all_summaries).to_csv(buf2, index=False)
    st.download_button("Bild-Features (CSV)", buf2.getvalue(), "image_features.csv", "text/csv")
