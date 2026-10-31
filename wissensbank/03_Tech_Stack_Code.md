# 03 – Tech-Stack und wiederverwendbarer Code

Stack: Python 3.11+ · OpenCV · scikit-image · SciPy · NumPy · pandas · scikit-learn · matplotlib · Streamlit.
Alle Skripte liegen in `scripts/`, sind an synthetischen Daten getestet (`python selftest.py`; Download und echte Fotos von corn1000 nicht) und unten vollständig abgedruckt (Quelle der Wahrheit bleibt die Datei, nicht dieses Dokument).

---

## 1. Einrichtung

```powershell
cd wissensbank
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd scripts
python selftest.py
```

| Problem | Lösung |
|---|---|
| `Activate.ps1` blockiert | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` und erneut aktivieren |
| `py` nicht gefunden | `python -m venv .venv` oder Python über Microsoft Store/python.org installieren |
| `pip` hinter Proxy/WLAN langsam | Hotspot nutzen; Pakete vorab installieren (vor 14:00) |
| `cv2` meldet GUI-Fehler | `pip uninstall opencv-python` und `pip install opencv-python-headless` (wir brauchen keine OpenCV-Fenster) |
| `streamlit` startet nicht | `python -m streamlit run app_streamlit.py` |
| Excel (`.xlsx`) lässt sich nicht lesen | `pip install openpyxl` (steht in requirements) |
| `UnicodeDecodeError` | `load_table` probiert utf-8, cp1252, latin-1 automatisch; sonst Datei in Excel als „CSV UTF-8“ speichern |

---

## 2. Projektstruktur

```
tausendkorn/                 Repo-Wurzel (Team-Code: src/, app/, notebooks/, pitch/)
└── wissensbank/
    ├── README.md            Einstieg, Schnellstart, Reihenfolge
    ├── 01_Domain_Wissen.md … 05_Datensatz_corn1000.md
    ├── requirements.txt
    ├── notes/               00_Antworten… · 01_Datenset_Erstblick · 02_Entscheidungslog
    ├── scripts/             tkm_utils · a4_sheet · grain_segmentation · make_synthetic_data
    │                        corn1000_data · evaluate_counting · classical_counter · merge_labels
    │                        eda_tabular
    │                        train_model · app_streamlit · selftest
    ├── data/                (lokal, nicht im Repo) raw · processed · synthetic
    └── outputs/             (lokal, nicht im Repo) Ergebnisse seg, eda, model
```

---

## 3. Skriptübersicht

| Skript | Zweck | Eingabe → Ausgabe | Getestet |
|---|---|---|---|
| `tkm_utils.py` | TKM, Feuchte, Saatstärke, Ertrag, Stichprobe, Siebfraktionen, Referenzwerte | Zahlen → Zahlen | Selbsttest |
| `a4_sheet.py` | A4-Blatt finden, entzerren, mm/px ableiten, Punkte zwischen Original und entzerrtem Bild umrechnen | Foto → entzerrtes Blatt + Homographie | Attrappe (perspektivisch verzerrte A4-Szenen) |
| `grain_segmentation.py` | Körner zählen, vermessen, Farbe, Cluster-Splitting, Maßstab (Münze), TKM-Methoden | Bilder → `grains.csv`, `summary.csv`, Overlays | synthetisch (Weizen- und Rundkorn-ähnlich) |
| `make_synthetic_data.py` | Synthetische Bilder mit bekannter Wahrheit; mit `--corn1000-mock` perspektivische A4-Szenen im Exportformat | Seed → PNG/JPEG + Labels | ja |
| `corn1000_data.py` | Datensatz `SmartFarmingLab/corn1000` exportieren (JPEG, `metadata.csv`, `points.jsonl`), Session-Folds | Hub/`save_to_disk` → Ordner | Attrappe + nachgebauter HF-Datensatz; **Hub-Download selbst nicht** |
| `classical_counter.py` | Adapter: klassische Pipeline als Zähler für `python -m tausendkorn.eval` (Schnittstelle `count(image) -> {count, points}`) | PIL-Bild → Zahl + Punkte | Attrappe, Aufruf über Team-Eval |
| `evaluate_counting.py` | Zähl-Baseline auf corn1000: A4-Entzerrung, Zählung, MAE/MAPE/Bias, Punkt-Precision/Recall, Zeile für `docs/RESULTS.md` | `metadata.csv` → `predictions.csv`, `metrics.json`, Overlays | Attrappe |
| `merge_labels.py` | Bild-Features mit Label-Tabelle verbinden (Namensnormalisierung) | CSV/XLSX → `train_table.csv` | ja (Semikolon, Dezimalkomma) |
| `eda_tabular.py` | Schnelle Datenübersicht, Korrelationen, Ausreißer, Grafiken | CSV/XLSX → `eda_report.md` + PNG | ja |
| `train_model.py` | Regression/Klassifikation, CV (LOO/Gruppen), Baseline-Vergleich, Importance | CSV/XLSX → Modell + Metriken + Grafik | ja (Regression); Klassifikation nur Code-Pfad |
| `app_streamlit.py` | Interaktive Demo | Bild hoch → Overlay, Kennzahlen, CSV | headless (AppTest) |
| `selftest.py` | Gesamtprüfung in ca. 20–30 s | – | – |

---

## 4. Befehlsrezepte

Siehe `README.md` (Tabelle nach Datenlage). Zusätzlich:

```powershell
# corn1000: exportieren, auswerten (Details und Fallstricke in 05_Datensatz_corn1000.md)
python corn1000_data.py index  --src ..\..\data\corn1000 --out ..\..\data\corn1000_index      # nach hf download
python corn1000_data.py info   --meta ..\..\data\corn1000_index\metadata.csv
python evaluate_counting.py --meta ..\..\data\corn1000_index\metadata.csv --out ..\outputs\count_baseline --jobs 4
# Alternative ohne Vorab-Download: corn1000_data.py export --out ..\..\data\corn1000_export --max-side 3000

# Gruppenvalidierung (mehrere Bilder je Partie) – verhindert Leckage
python train_model.py --csv ..\outputs\train_table.csv --target TKM --drop image --group partie

# Klassifikation (z. B. Qualitätsklasse)
python train_model.py --csv daten.xlsx --target klasse --task clf --drop id

# Segmentierung variieren
python grain_segmentation.py --input ..\data\raw --out ..\outputs\seg_v2 --channel S --method adaptive --flatfield
python grain_segmentation.py --input ..\data\raw --out ..\outputs\seg_v3 --no-watershed        # Vergleich ohne Splitting
```

---

## 5. Parameter-Cheatsheet (`SegConfig`)

| Parameter | Wirkung | Wann ändern |
|---|---|---|
| `channel` (`auto`, `gray`, `S`, `b`, `a`, `L`, `R`,`G`,`B`) | Bildkanal für die Schwelle | Körner fehlen/Schatten wird Korn |
| `method` (`otsu`, `adaptive`, `fixed`) | Schwellwertverfahren | Beleuchtungsgradient → `adaptive` oder `flatfield` |
| `invert` (`auto`,`yes`,`no`) | Vordergrund umkehren | Maske zeigt Hintergrund |
| `blur_sigma` | Glättung | stark verrauscht ↑, feine Konturen ↓ |
| `open_px`, `close_px` | Entrauschen / Löcher füllen | Staub ↑ open; Furche zerreißt Korn ↑ close |
| `min_area_px`, `min_rel_area` | Kleinstobjekte entfernen | Staub bleibt / Bruchkörner fehlen |
| `max_rel_area_single` | Ab wann Cluster-Verdacht | Splitting setzt zu spät/zu früh ein |
| `h_frac` | Empfindlichkeit des Watershed (0,15–0,5) | ↑ weniger Teilungen, ↓ mehr Teilungen |
| `drop_border` | Randkörner ausschließen | Körner sollen auch am Rand zählen: `False` |
| `mm_per_px` / `ref_diameter_mm` | Maßstab manuell / über Münze | Münze nur wenn voll im Bild (Randkontakt wird verworfen) |

Programmatische Nutzung:

```python
from grain_segmentation import SegConfig, read_image, analyze_image
df, overlay, summary = analyze_image(read_image("../data/raw/probe01.jpg"), SegConfig(mm_per_px=0.1))
```

---

## 6. Kurzsnippets

**Bland-Altman (Übereinstimmung Messung vs. Modell)**

```python
import numpy as np, matplotlib.pyplot as plt
def bland_altman(y_true, y_pred, path="bland_altman.png"):
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    mean, diff = (y_true + y_pred) / 2, y_pred - y_true
    bias, sd = diff.mean(), diff.std(ddof=1)
    plt.figure(figsize=(6, 4)); plt.scatter(mean, diff, s=18)
    for v, ls in [(bias, "-"), (bias + 1.96 * sd, "--"), (bias - 1.96 * sd, "--")]:
        plt.axhline(v, color="k", ls=ls, lw=1)
    plt.xlabel("Mittelwert [g]"); plt.ylabel("Modell - Messung [g]")
    plt.title(f"Bias {bias:.2f} g, Grenzen {bias-1.96*sd:.2f} … {bias+1.96*sd:.2f} g")
    plt.tight_layout(); plt.savefig(path, dpi=130); return bias, sd
# Aufruf mit den Out-of-fold-Vorhersagen: oof = pd.read_csv("../outputs/model/oof_predictions.csv")
```

**Verfärbung / Besatz ohne Labels (unüberwacht)**

```python
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
X = df[["L", "a", "b"]].values
df["farbcluster"] = KMeans(n_clusters=3, n_init=10, random_state=0).fit_predict(X)
feat = df[["area_px", "aspect", "solidity", "L", "a", "b"]]
df["ausreisser"] = IsolationForest(contamination=0.03, random_state=0).fit_predict(feat) == -1
```

**Video → Einzelbilder (jedes 10. Bild)**

```python
import cv2
from pathlib import Path
from grain_segmentation import write_image          # Windows-/Umlaut-sicheres Schreiben
src, out = Path("../data/raw/video.mp4"), Path("../data/processed")
cap = cv2.VideoCapture(str(src))
assert cap.isOpened(), f"Video nicht lesbar: {src.resolve()}"   # sonst bleibt der Fehler still
i = k = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if i % 10 == 0:
        write_image(out / f"frame_{k:04d}.png", frame)
        k += 1
    i += 1
print(k, "Einzelbilder gespeichert")
```

**Mehrere Teilproben je Bild/Partie aggregieren (Pandas)**

```python
g = df.groupby("image").agg(n=("grain_id", "count"), area=("area_mm2", "mean"), length=("length_mm", "mean"))
```

**Cellpose als Notnagel bei starker Überlappung (ungetestet; Installation und API vorher prüfen)**

```python
# pip install cellpose   (große Downloads; Verfügbarkeit/Version prüfen)
# from cellpose import models
# model = models.CellposeModel(gpu=False)
# masks = model.eval(img_rgb, diameter=None)[0]      # Rückgabeformat je nach Version prüfen
# Danach: labels = masks; extract_features(img_bgr, labels, set(), med_area, mm_per_px)
```

---

## 7. Quellcode

Reihenfolge nach Abhängigkeit. Dateien bei Änderungen im Projektordner pflegen, nicht hier.

### 7.1 `tkm_utils.py`: Fachformeln

```python
"""
tkm_utils.py - Fachformeln rund um Tausendkornmasse (TKM), Saatstaerke, Ertrag, Siebfraktionen.

Alle Funktionen sind reine Python/NumPy-Funktionen ohne Seiteneffekte.
Selbsttest:  python tkm_utils.py
"""
from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------- #
# 1) TKM aus Probe
# --------------------------------------------------------------------------- #

def tkm_from_sample(mass_g: float, n_grains: int) -> float:
    """TKM [g] aus gewogener Probe: Gesamtmasse [g] / Kornzahl * 1000."""
    if n_grains <= 0:
        raise ValueError("n_grains muss > 0 sein")
    return mass_g / n_grains * 1000.0


def mass_from_tkm(tkm_g: float, n_grains: int) -> float:
    """Erwartete Probenmasse [g] bei gegebener TKM und Kornzahl."""
    return tkm_g * n_grains / 1000.0


def grains_per_gram(tkm_g: float) -> float:
    """Koerner pro Gramm (Kehrwert der Einzelkornmasse)."""
    return 1000.0 / tkm_g


# --------------------------------------------------------------------------- #
# 2) Feuchtekorrektur
# --------------------------------------------------------------------------- #

def tkm_to_reference_moisture(tkm_g: float, moisture_pct: float,
                              ref_moisture_pct: float = 0.0) -> float:
    """
    Rechnet eine bei `moisture_pct` % Kornfeuchte gemessene TKM auf eine
    Bezugsfeuchte um.  ref=0  -> Trockensubstanz-Basis (TS).
                       ref=14 -> uebliche Handels-/Lagerfeuchte (Getreide).
    Trockenmasse = m * (1 - w/100);  m_ref = Trockenmasse / (1 - w_ref/100)
    """
    dry = tkm_g * (1.0 - moisture_pct / 100.0)
    return dry / (1.0 - ref_moisture_pct / 100.0)


# --------------------------------------------------------------------------- #
# 3) Saatstaerke & Ertrag
# --------------------------------------------------------------------------- #

def seed_rate_kg_ha(target_plants_m2: float, tkm_g: float,
                    germination_pct: float = 100.0,
                    field_emergence_pct: float = 100.0) -> float:
    """
    Saatstaerke [kg/ha].
    Koerner/m2 = Zielpflanzen / (Keimfaehigkeit * Feldaufgang)
    kg/ha      = Koerner/m2 * TKM / 100        (1 g/m2 = 10 kg/ha)
    Beispiel: 350 Pfl./m2, TKM 45 g, KF 95 %, FA 100 %  ->  ~165.8 kg/ha
    """
    kernels_m2 = target_plants_m2 / ((germination_pct / 100.0) * (field_emergence_pct / 100.0))
    return kernels_m2 * tkm_g / 100.0


def yield_dt_ha(ears_per_m2: float, grains_per_ear: float, tkm_g: float) -> float:
    """
    Ertrag [dt/ha] = Aehren/m2 * Koerner/Aehre * TKM.
    g/m2 = Aehren * Koerner * TKM / 1000;   1 g/m2 = 0.1 dt/ha
    Beispiel: 600 * 35 * 45 g  ->  94.5 dt/ha
    """
    g_per_m2 = ears_per_m2 * grains_per_ear * tkm_g / 1000.0
    return g_per_m2 * 0.1


def yield_sensitivity(ears_per_m2: float, grains_per_ear: float, tkm_g: float,
                      delta_tkm_g: float = 1.0) -> float:
    """Ertragsaenderung [dt/ha], wenn die TKM um `delta_tkm_g` steigt (alles andere fix)."""
    return yield_dt_ha(ears_per_m2, grains_per_ear, tkm_g + delta_tkm_g) - \
           yield_dt_ha(ears_per_m2, grains_per_ear, tkm_g)


# --------------------------------------------------------------------------- #
# 4) Statistik: Stichprobe & Konfidenzintervall
# --------------------------------------------------------------------------- #

def required_sample_size(cv_pct: float, rel_error_pct: float, z: float = 1.96) -> int:
    """
    Benoetigte Kornzahl, damit der Mittelwert der Einzelkornmasse mit
    Sicherheit z (1.96 = 95 %) auf +-rel_error_pct genau ist:  n = (z*CV/err)^2
    """
    return int(np.ceil((z * cv_pct / rel_error_pct) ** 2))


def bootstrap_ci(values, stat=np.mean, n_boot: int = 2000, conf: float = 0.95,
                 seed: int = 0) -> tuple[float, float, float]:
    """(Schaetzwert, untere, obere Grenze) per Bootstrap ueber Einzelwerte."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return (float("nan"),) * 3
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(v), size=(n_boot, len(v)))
    boots = stat(v[idx], axis=1)
    lo, hi = np.percentile(boots, [(1 - conf) / 2 * 100, (1 + conf) / 2 * 100])
    return float(stat(v)), float(lo), float(hi)


# --------------------------------------------------------------------------- #
# 5) Siebfraktionen (Sortierung)
# --------------------------------------------------------------------------- #

def sieve_fractions(widths_mm, edges_mm=(2.0, 2.2, 2.5, 2.8), weights=None) -> dict[str, float]:
    """
    Anteil [%] je Siebfraktion anhand der Kornbreite (Spaltsieb ~ kleine Achse).
    Gewichtung optional (z.B. Einzelkornmasse -> Masseanteile statt Zahlenanteile).
    Typisch: Braugerste 'Vollgerste' = Anteil > 2.5 mm.
    """
    w = np.asarray(widths_mm, dtype=float)
    wt = np.ones_like(w) if weights is None else np.asarray(weights, dtype=float)
    ok = ~np.isnan(w) & ~np.isnan(wt)
    w, wt = w[ok], wt[ok]
    total = wt.sum()
    if total == 0:
        return {}
    edges = list(edges_mm)
    out = {f"<{edges[0]}": float(wt[w < edges[0]].sum() / total * 100)}
    for lo, hi in zip(edges[:-1], edges[1:]):
        out[f"{lo}-{hi}"] = float(wt[(w >= lo) & (w < hi)].sum() / total * 100)
    out[f">={edges[-1]}"] = float(wt[w >= edges[-1]].sum() / total * 100)
    return out


# --------------------------------------------------------------------------- #
# 6) Richtwerte (Quelle: Kulturpflanzenjournal/Bundessortenamt-Daten 2011-2018,
#    Saatgutpartien; 5.-95. Perzentil in g). Bei Bedarf vor Ort verifizieren.
# --------------------------------------------------------------------------- #
TKM_REFERENCE_G = {
    "Winterweizen":   {"mean": 49.2,  "p5": 38.8, "p95": 58.8},
    "Sommerweizen":   {"mean": 47.0,  "p5": 38.0, "p95": 55.0},
    "Wintergerste":   {"mean": 55.5,  "p5": 44.5, "p95": 67.0},
    "Sommergerste":   {"mean": 56.4,  "p5": 47.0, "p95": 65.0},
    "Winterroggen":   {"mean": 37.3,  "p5": 28.3, "p95": 47.7},
    "Wintertriticale": {"mean": 52.6, "p5": 40.2, "p95": 64.0},
    "Hafer":          {"mean": 43.6,  "p5": 36.0, "p95": 52.8},
    "Winterraps":     {"mean": 5.58,  "p5": 4.00, "p95": 7.84},
    "Mais":           {"mean": 289.8, "p5": 224.9, "p95": 353.0},
    "Futtererbse":    {"mean": 246.0, "p5": 179.0, "p95": 309.5},
    "Soja":           {"mean": 202.3, "p5": 154.0, "p95": 240.0},
}


def plausibility_check(crop: str, tkm_g: float) -> str:
    ref = TKM_REFERENCE_G.get(crop)
    if ref is None:
        return f"Keine Referenz fuer '{crop}' hinterlegt."
    if ref["p5"] <= tkm_g <= ref["p95"]:
        return f"plausibel ({tkm_g:.1f} g im 5-95%-Bereich {ref['p5']}-{ref['p95']} g)"
    return f"AUSREISSER-VERDACHT ({tkm_g:.1f} g ausserhalb {ref['p5']}-{ref['p95']} g)"


if __name__ == "__main__":
    assert abs(tkm_from_sample(4.5, 100) - 45.0) < 1e-9
    assert abs(seed_rate_kg_ha(350, 45, 95) - 165.789) < 0.01
    assert abs(yield_dt_ha(600, 35, 45) - 94.5) < 1e-9
    assert abs(tkm_to_reference_moisture(45, 14, 0) - 38.7) < 1e-9
    assert required_sample_size(12, 2) == 139
    print("tkm_utils Selbsttest OK")
    print(plausibility_check("Winterweizen", 46.0))
```

### 7.2 `a4_sheet.py`: A4-Blatt erkennen und entzerren

```python
"""
a4_sheet.py - A4-Blatt im Foto finden, entzerren, Massstab ableiten.

Die corn1000-Fotos zeigen Koerner auf einem weissen A4-Blatt (210 x 297 mm) vor dunklem/kontrastreichem
Untergrund. Das Blatt liefert den Massstab (mm/px) und schneidet den Hintergrund weg.

    warped, info = rectify_a4(img_bgr)           # None-Info, falls kein Blatt gefunden
    info["H"]            3x3 Homographie Original -> entzerrt
    info["mm_per_px"]    Massstab im entzerrten Bild
    to_original(pts, info)   Punkte aus dem entzerrten Bild ins Originalbild zurueckrechnen
"""
from __future__ import annotations

import cv2
import numpy as np

A4_W_MM, A4_H_MM = 210.0, 297.0


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Sortiert 4 Punkte: oben-links, oben-rechts, unten-rechts, unten-links."""
    pts = np.asarray(pts, np.float32).reshape(4, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)


def find_a4_corners(img_bgr: np.ndarray, min_area_frac: float = 0.15, max_side: int = 1200):
    """
    Findet das hellste grosse Viereck (Papier). Rueckgabe: 4x2 Eckpunkte im Originalmassstab oder None.
    Rechnet auf verkleinertem Bild (schnell); Koerner im Papier stoeren nicht (Kontur wird gefuellt).
    """
    h, w = img_bgr.shape[:2]
    f = min(1.0, max_side / max(h, w))
    small = cv2.resize(img_bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else img_bgr
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (0, 0), 3)
    _, m = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < min_area_frac * small.shape[0] * small.shape[1] or area <= best_area:
            continue
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        quad = None
        for eps in (0.02, 0.03, 0.05, 0.08):
            ap = cv2.approxPolyDP(hull, eps * peri, True)
            if len(ap) == 4:
                quad = ap
                break
        if quad is None:                                   # Notnagel: gedrehtes Rechteck
            quad = cv2.boxPoints(cv2.minAreaRect(hull)).reshape(-1, 1, 2)
        q = _order_corners(quad)
        e = [np.linalg.norm(q[i] - q[(i + 1) % 4]) for i in range(4)]
        long_s, short_s = max(e[0], e[2], e[1], e[3]), min(e[0], e[2], e[1], e[3])
        ratio = long_s / max(short_s, 1e-6)
        if not (1.15 <= ratio <= 1.75):                    # A4 = 1,414; Perspektive streut
            continue
        best, best_area = q, area
    return None if best is None else best / f


def rectify_a4(img_bgr: np.ndarray, mm_per_px: float = 0.1, margin_mm: float = 0.0):
    """
    Entzerrt das Blatt auf feste Groesse (Hochformat, 210 x 297 mm). Rueckgabe (bild, info) oder (None, None).
    mm_per_px = 0.1 -> 2100 x 2970 px (reicht fuer ca. 60 px je Kornbreite; kleiner = schneller).
    """
    q = find_a4_corners(img_bgr)
    if q is None:
        return None, None
    e01, e12 = np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[1])
    if e01 > e12:                                          # Blatt liegt quer -> Ecken so rotieren, dass lange Seite vertikal wird
        q = np.roll(q, -1, axis=0)
    W, H = int(round(A4_W_MM / mm_per_px)), int(round(A4_H_MM / mm_per_px))
    dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], np.float32)
    Hm = cv2.getPerspectiveTransform(q.astype(np.float32), dst)
    warped = cv2.warpPerspective(img_bgr, Hm, (W, H), flags=cv2.INTER_AREA if mm_per_px > 0.05 else cv2.INTER_LINEAR)
    if margin_mm > 0:                                      # Papierkante (Schatten, Rand) wegschneiden
        m = int(round(margin_mm / mm_per_px))
        warped = warped[m:H - m, m:W - m]
    return warped, {"H": Hm, "mm_per_px": mm_per_px, "corners": q, "margin_px": int(round(margin_mm / mm_per_px))}


def to_original(points_xy, info) -> np.ndarray:
    """Punkte (N,2) aus dem entzerrten Bild ins Originalbild zurueckrechnen."""
    pts = np.asarray(points_xy, np.float32).reshape(-1, 1, 2)
    if len(pts) == 0:
        return np.zeros((0, 2), np.float32)
    pts = pts + info.get("margin_px", 0)
    inv = np.linalg.inv(info["H"])
    return cv2.perspectiveTransform(pts, inv).reshape(-1, 2)


def to_rectified(points_xy, info) -> np.ndarray:
    """Punkte (N,2) aus dem Originalbild ins entzerrte Bild."""
    pts = np.asarray(points_xy, np.float32).reshape(-1, 1, 2)
    if len(pts) == 0:
        return np.zeros((0, 2), np.float32)
    out = cv2.perspectiveTransform(pts, info["H"]).reshape(-1, 2)
    return out - info.get("margin_px", 0)
```

### 7.3 `grain_segmentation.py`: Segmentierung, Features, TKM-Methoden

```python
"""
grain_segmentation.py - Klassische CV-Pipeline: Koerner zaehlen, vermessen, TKM schaetzen.

Pipeline:  Bild laden -> Kanal waehlen -> (Flatfield) -> Blur -> Schwellwert (Otsu/adaptiv/fix)
           -> Morphologie -> Hole-Fill -> Labeling -> Referenzobjekt (Muenze) optional
           -> Cluster-Splitting (Distanztransformation + h-Maxima + Watershed)
           -> Features je Korn (Geometrie, Farbe) -> Overlay + CSV.

CLI-Beispiele:
  python grain_segmentation.py --input ../data/raw --out ../outputs/seg --mm-per-px 0.1
  python grain_segmentation.py --input bild.jpg --out ../outputs/seg --ref-diameter-mm 25.75
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def _axes(p):
    """(Hauptachse, Nebenachse) - kompatibel mit alten und neuen scikit-image-Versionen."""
    maj = getattr(p, "axis_major_length", None)
    mino = getattr(p, "axis_minor_length", None)
    if maj is None:
        maj, mino = p.major_axis_length, p.minor_axis_length
    return maj, mino


def _remove_small(labels: np.ndarray, min_px: int) -> np.ndarray:
    counts = np.bincount(labels.ravel())
    small = counts < min_px
    small[0] = False
    out = labels.copy()
    out[small[labels]] = 0
    return out


# --------------------------------------------------------------------------- #
# I/O (Windows-/Umlaut-sicher: cv2.imread scheitert an Nicht-ASCII-Pfaden)
# --------------------------------------------------------------------------- #
def read_image(path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Bild nicht lesbar: {path}")
    return img


def write_image(path, img: np.ndarray) -> None:
    ext = Path(path).suffix or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise ValueError(f"Bild nicht schreibbar: {path}")
    buf.tofile(str(path))


def list_images(path) -> list[Path]:
    p = Path(path)
    if p.is_file():
        return [p]
    return sorted(f for f in p.rglob("*") if f.suffix.lower() in IMG_EXT)


# --------------------------------------------------------------------------- #
# Konfiguration
# --------------------------------------------------------------------------- #
@dataclass
class SegConfig:
    channel: str = "auto"            # auto | gray | L | a | b | S | R | G | B
    method: str = "otsu"             # otsu | adaptive | fixed
    fixed_threshold: int = 128
    invert: str = "auto"             # auto | yes | no  (Vordergrund = Koerner)
    flatfield: bool = False          # Beleuchtungsgradient herausrechnen
    blur_sigma: float = 1.5
    open_px: int = 2
    close_px: int = 2
    min_area_px: int = 40
    min_rel_area: float = 0.30       # < 30 % der Median-Kornflaeche -> Rauschen
    max_rel_area_single: float = 1.45  # groesser -> Cluster-Verdacht
    watershed: bool = True
    h_frac: float = 0.25             # h-Maxima-Hoehe als Anteil des Korn-Innenradius
    drop_border: bool = True         # angeschnittene Koerner am Bildrand ausschliessen
    mm_per_px: float | None = None
    ref_diameter_mm: float | None = None  # z.B. 2-Euro-Muenze 25.75 mm


# --------------------------------------------------------------------------- #
# Vorverarbeitung
# --------------------------------------------------------------------------- #
def get_channel(img_bgr: np.ndarray, name: str) -> np.ndarray:
    if name == "gray":
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if name in ("L", "a", "b"):
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        return lab[..., {"L": 0, "a": 1, "b": 2}[name]]
    if name == "S":
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)[..., 1]
    if name in ("R", "G", "B"):
        return img_bgr[..., {"B": 0, "G": 1, "R": 2}[name]]
    raise ValueError(f"Unbekannter Kanal: {name}")


def otsu_separability(ch: np.ndarray) -> float:
    """Anteil der Varianz, den Otsu erklaert (0..1). Hoeher = besser trennbar."""
    t, _ = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fg, bg = ch[ch > t], ch[ch <= t]
    if len(fg) == 0 or len(bg) == 0:
        return 0.0
    w1 = len(fg) / ch.size
    return float(w1 * (1 - w1) * (fg.mean() - bg.mean()) ** 2 / (ch.var() + 1e-9))


def choose_channel(img_bgr: np.ndarray) -> str:
    cands = ["gray", "S", "b", "a", "L"]
    scores = {c: otsu_separability(get_channel(img_bgr, c)) for c in cands}
    return max(scores, key=scores.get)


def flatfield(ch: np.ndarray) -> np.ndarray:
    """Teilt durch stark geglaettetes Hintergrundbild (korrigiert Beleuchtungsgradient)."""
    sigma = max(ch.shape) / 6
    bg = cv2.GaussianBlur(ch.astype(np.float32), (0, 0), sigma)
    out = ch.astype(np.float32) / (bg + 1e-6) * float(np.mean(bg))
    return np.clip(out, 0, 255).astype(np.uint8)


def make_mask(img_bgr: np.ndarray, cfg: SegConfig) -> tuple[np.ndarray, str]:
    name = choose_channel(img_bgr) if cfg.channel == "auto" else cfg.channel
    ch = get_channel(img_bgr, name)
    if cfg.flatfield:
        ch = flatfield(ch)
    if cfg.blur_sigma > 0:
        ch = cv2.GaussianBlur(ch, (0, 0), cfg.blur_sigma)

    if cfg.method == "otsu":
        _, m = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif cfg.method == "adaptive":
        block = int(min(ch.shape) / 8) // 2 * 2 + 1
        m = cv2.adaptiveThreshold(ch, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, block, 5)
    elif cfg.method == "fixed":
        _, m = cv2.threshold(ch, cfg.fixed_threshold, 255, cv2.THRESH_BINARY)
    else:
        raise ValueError(cfg.method)

    mask = m > 0
    if cfg.invert == "yes" or (cfg.invert == "auto" and mask.mean() > 0.5):
        mask = ~mask

    mu8 = mask.astype(np.uint8) * 255
    if cfg.open_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cfg.open_px + 1,) * 2)
        mu8 = cv2.morphologyEx(mu8, cv2.MORPH_OPEN, k)
    if cfg.close_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cfg.close_px + 1,) * 2)
        mu8 = cv2.morphologyEx(mu8, cv2.MORPH_CLOSE, k)
    return ndi.binary_fill_holes(mu8 > 0), name


# --------------------------------------------------------------------------- #
# Referenzobjekt (Muenze) fuer Massstab
# --------------------------------------------------------------------------- #
def find_reference_disc(labels: np.ndarray, med_area: float):
    """Groesstes sehr rundes, sehr konvexes Objekt (> 4x Kornflaeche) = Muenze."""
    best = None
    H, W = labels.shape
    for r in measure.regionprops(labels):
        if r.area < 4 * med_area or r.perimeter == 0:
            continue
        minr, minc, maxr, maxc = r.bbox
        if minr == 0 or minc == 0 or maxr == H or maxc == W:
            continue                      # am Bildrand angeschnitten -> Durchmesser unzuverlaessig
        circ = 4 * np.pi * r.area / r.perimeter ** 2
        if circ > 0.85 and r.solidity > 0.97 and (best is None or r.area > best.area):
            best = r
    return best


def detect_scale_disc(img_bgr, med_area, cfg, main_channel):
    """Sucht die Referenzmuenze in mehreren Kanaelen (graue Muenze fehlt z.B. im S-Kanal)."""
    from dataclasses import replace
    tried = []
    for ch_name in [main_channel, "gray", "L", "S", "b"]:
        if ch_name in tried:
            continue
        tried.append(ch_name)
        m, _ = make_mask(img_bgr, replace(cfg, channel=ch_name))
        ref = find_reference_disc(measure.label(m, connectivity=1), med_area)
        if ref is not None:
            return ref
    return None


# --------------------------------------------------------------------------- #
# Cluster-Splitting
# --------------------------------------------------------------------------- #
def robust_single_stats(labels: np.ndarray) -> tuple[float, float]:
    """(Median-Einzelkornflaeche, Median-Innenradius) aus 'unauffaelligen' Objekten."""
    props = measure.regionprops(labels)
    areas = np.array([p.area for p in props], dtype=float)
    if len(areas) == 0:
        return 0.0, 0.0
    med = float(np.median(areas))
    singles = [p for p in props if 0.6 * med <= p.area <= 1.4 * med and p.solidity >= 0.9]
    if len(singles) >= 5:
        med = float(np.median([p.area for p in singles]))
    else:
        singles = props
    radii = []
    for p in singles:
        crop = np.pad(p.image, 1)
        radii.append(ndi.distance_transform_edt(crop).max())
    return med, float(np.median(radii))


def split_clusters(mask: np.ndarray, labels: np.ndarray, med_area: float,
                   r_single: float, cfg: SegConfig):
    """Gibt (neue Labels, Menge der gesplitteten Label-IDs) zurueck."""
    out = np.zeros_like(labels)
    next_id = 1
    split_ids: set[int] = set()
    for p in measure.regionprops(labels):
        suspect = (p.area > cfg.max_rel_area_single * med_area) or \
                  (p.solidity < 0.88 and p.area > 1.1 * med_area)
        minr, minc, maxr, maxc = p.bbox
        sl = (slice(minr, maxr), slice(minc, maxc))
        region = p.image
        if not (cfg.watershed and suspect):
            out[sl][region] = next_id
            next_id += 1
            continue
        crop = np.pad(region, 2)
        dist = ndi.distance_transform_edt(crop)
        dist_s = ndi.gaussian_filter(dist, 1.0)
        h = max(cfg.h_frac * r_single, 0.5)
        markers = measure.label(morphology.h_maxima(dist_s, h))
        if markers.max() <= 1:
            out[sl][region] = next_id
            next_id += 1
            continue
        ws = segmentation.watershed(-dist_s, markers, mask=crop)[2:-2, 2:-2]
        for k in range(1, ws.max() + 1):
            piece = (ws == k) & region
            if piece.sum() == 0:
                continue
            out[sl][piece] = next_id
            split_ids.add(next_id)
            next_id += 1
    return out, split_ids


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #
def extract_features(img_bgr: np.ndarray, labels: np.ndarray, split_ids: set[int],
                     med_area: float, mm_per_px: float | None) -> pd.DataFrame:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    H, W = labels.shape
    rows = []
    for p in measure.regionprops(labels):
        rr, cc = p.coords[:, 0], p.coords[:, 1]
        minr, minc, maxr, maxc = p.bbox
        per = p.perimeter if p.perimeter > 0 else np.nan
        maj, mino = _axes(p)
        row = {
            "grain_id": p.label,
            "cx": p.centroid[1], "cy": p.centroid[0],
            "area_px": p.area,
            "perimeter_px": per,
            "major_px": maj,
            "minor_px": mino,
            "aspect": maj / max(mino, 1e-6),
            "eccentricity": p.eccentricity,
            "solidity": p.solidity,
            "extent": p.extent,
            "circularity": 4 * np.pi * p.area / per ** 2 if per == per else np.nan,
            "orientation_deg": np.degrees(p.orientation),
            "touches_border": bool(minr == 0 or minc == 0 or maxr == H or maxc == W),
            "was_split": p.label in split_ids,
            "n_est_blob": max(1, int(round(p.area / med_area))) if med_area > 0 else 1,
            "L": lab[rr, cc, 0].mean() * 100 / 255, "a": lab[rr, cc, 1].mean() - 128,
            "b": lab[rr, cc, 2].mean() - 128,
            "hue": hsv[rr, cc, 0].mean() * 2, "sat": hsv[rr, cc, 1].mean() / 255,
            "val": hsv[rr, cc, 2].mean() / 255,
        }
        if mm_per_px:
            row["area_mm2"] = p.area * mm_per_px ** 2
            row["length_mm"] = maj * mm_per_px
            row["width_mm"] = mino * mm_per_px
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Haupt-Analyse
# --------------------------------------------------------------------------- #
def analyze_image(img_bgr: np.ndarray, cfg: SegConfig | None = None):
    """Gibt (df, overlay_bgr, summary_dict) zurueck."""
    cfg = cfg or SegConfig()
    mask, ch_name = make_mask(img_bgr, cfg)
    labels = measure.label(mask, connectivity=1)
    labels = _remove_small(labels, cfg.min_area_px)
    labels, _, _ = segmentation.relabel_sequential(labels)

    mm_per_px = cfg.mm_per_px
    ref_info = None
    if cfg.ref_diameter_mm and labels.max() > 0:
        med0 = float(np.median([p.area for p in measure.regionprops(labels)]))
        ref = detect_scale_disc(img_bgr, med0, cfg, ch_name)
        if ref is not None:
            d_px = getattr(ref, "equivalent_diameter_area", None) or ref.equivalent_diameter
            cy, cx = ref.centroid
            mm_per_px = cfg.ref_diameter_mm / d_px
            ref_info = {"ref_diameter_px": float(d_px), "ref_center": (cx, cy)}
            # evtl. in der Kornmaske enthaltene Muenze entfernen
            for p in measure.regionprops(labels):
                if np.hypot(p.centroid[0] - cy, p.centroid[1] - cx) < 0.6 * d_px:
                    labels[labels == p.label] = 0
            labels, _, _ = segmentation.relabel_sequential(labels)

    if labels.max() == 0:
        return pd.DataFrame(), img_bgr.copy(), {"n_grains": 0, "channel": ch_name}

    med_area, r_single = robust_single_stats(labels)
    labels, split_ids = split_clusters(mask, labels, med_area, r_single, cfg)

    df = extract_features(img_bgr, labels, split_ids, med_area, mm_per_px)
    # Rauschen raus (relativ zur Median-Kornflaeche)
    df = df[df["area_px"] >= cfg.min_rel_area * med_area].copy()
    if cfg.drop_border:
        df = df[~df["touches_border"]].copy()
    df = df.reset_index(drop=True)

    summary = {
        "n_grains": int(len(df)),
        "n_grains_blob_corrected": int(df["n_est_blob"].sum()) if len(df) else 0,
        "n_split": int(df["was_split"].sum()) if len(df) else 0,
        "median_area_px": float(df["area_px"].median()) if len(df) else np.nan,
        "area_cv_pct": float(df["area_px"].std() / df["area_px"].mean() * 100) if len(df) > 1 else np.nan,
        "channel": ch_name,
        "mm_per_px": mm_per_px,
        "ref_found": ref_info is not None,
    }
    if mm_per_px and len(df):
        summary.update({
            "mean_length_mm": float(df["length_mm"].mean()),
            "mean_width_mm": float(df["width_mm"].mean()),
            "mean_area_mm2": float(df["area_mm2"].mean()),
        })
    overlay = draw_overlay(img_bgr, labels, df, summary)
    return df, overlay, summary


def draw_overlay(img_bgr: np.ndarray, labels: np.ndarray, df: pd.DataFrame, summary: dict) -> np.ndarray:
    ov = img_bgr.copy()
    keep = set(df["grain_id"]) if len(df) else set()
    status = dict(zip(df["grain_id"], zip(df["was_split"], df["n_est_blob"]))) if len(df) else {}
    for gid in keep:
        m = (labels == gid).astype(np.uint8)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        was_split, n_est = status[gid]
        color = (0, 200, 0)              # gruen: einzelnes Korn
        if was_split:
            color = (0, 165, 255)        # orange: per Watershed getrennt
        if n_est > 1:
            color = (0, 0, 255)          # rot: ungeloester Cluster
        cv2.drawContours(ov, cnts, -1, color, 2)
    txt = f"n={summary['n_grains']} (blob-korr. {summary.get('n_grains_blob_corrected', '-')})"
    cv2.rectangle(ov, (5, 5), (5 + 11 * len(txt), 38), (255, 255, 255), -1)
    cv2.putText(ov, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    return ov


# --------------------------------------------------------------------------- #
# TKM-Schaetzung
# --------------------------------------------------------------------------- #
def calibrate_mass_factor(df: pd.DataFrame, total_mass_g: float,
                          col: str = "area_mm2", power: float = 1.5) -> float:
    """
    Modell Einzelkornmasse m_i = k * A_i^power (Volumen ~ Flaeche^1.5).
    k wird so kalibriert, dass Summe(m_i) = gewogene Gesamtmasse (nur Einzelkoerner).
    Rueckgabe: k in g / mm^(2*power).
    """
    d = df[df["n_est_blob"] == 1]
    return total_mass_g / float((d[col] ** power).sum())


def estimate_tkm(df: pd.DataFrame, k: float, col: str = "area_mm2", power: float = 1.5):
    """TKM [g] mit Bootstrap-95%-KI aus dem kalibrierten Flaechenmodell."""
    from tkm_utils import bootstrap_ci
    d = df[df["n_est_blob"] == 1]
    m_g = k * d[col] ** power
    mean_g, lo, hi = bootstrap_ci(m_g.values)
    return mean_g * 1000, lo * 1000, hi * 1000


# --------------------------------------------------------------------------- #
# Aggregation: ein Feature-Vektor je Bild/Probe (Eingabe fuer Regression auf TKM)
# --------------------------------------------------------------------------- #
def aggregate_image_features(df: pd.DataFrame) -> dict:
    """Aggregiert Einzelkorn-Features zu einer Zeile je Bild (nur Einzelkoerner, n_est_blob == 1)."""
    if len(df) == 0:
        return {}
    d = df[df["n_est_blob"] == 1]
    if len(d) == 0:
        d = df
    out = {"n_objects": int(len(df)), "n_single": int(len(d)),
           "n_blob_corrected": int(df["n_est_blob"].sum())}
    cols = [c for c in ["area_mm2", "length_mm", "width_mm", "area_px", "major_px", "minor_px",
                        "aspect", "solidity", "circularity", "L", "a", "b", "hue", "sat", "val"]
            if c in d.columns]
    for c in cols:
        out[f"{c}_mean"] = float(d[c].mean())
        out[f"{c}_std"] = float(d[c].std())
        out[f"{c}_p10"] = float(d[c].quantile(0.10))
        out[f"{c}_p90"] = float(d[c].quantile(0.90))
    if "area_mm2" in d.columns:
        out["area15_mean"] = float((d["area_mm2"] ** 1.5).mean())            # Volumen-Proxy A^1.5
        out["lw2_mean"] = float((d["length_mm"] * d["width_mm"] ** 2).mean())  # Ellipsoid-Proxy L*W^2
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Koerner segmentieren und vermessen")
    ap.add_argument("--input", required=True, help="Bild oder Ordner")
    ap.add_argument("--out", default="../outputs/seg")
    ap.add_argument("--mm-per-px", type=float, default=None)
    ap.add_argument("--ref-diameter-mm", type=float, default=None)
    ap.add_argument("--channel", default="auto")
    ap.add_argument("--method", default="otsu", choices=["otsu", "adaptive", "fixed"])
    ap.add_argument("--no-watershed", action="store_true")
    ap.add_argument("--flatfield", action="store_true")
    ap.add_argument("--keep-border", action="store_true")
    a = ap.parse_args()

    cfg = SegConfig(channel=a.channel, method=a.method, mm_per_px=a.mm_per_px,
                    ref_diameter_mm=a.ref_diameter_mm, watershed=not a.no_watershed,
                    flatfield=a.flatfield, drop_border=not a.keep_border)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    all_rows, summaries = [], []
    for f in list_images(a.input):
        img = read_image(f)
        df, ov, s = analyze_image(img, cfg)
        write_image(out / f"{f.stem}_overlay.png", ov)
        if len(df):
            df.insert(0, "image", f.name)
            all_rows.append(df)
        s["image"] = f.name
        s.update(aggregate_image_features(df))
        summaries.append(s)
        print(f"{f.name}: n={s['n_grains']} (blob-korr. {s.get('n_grains_blob_corrected')}), "
              f"Kanal={s['channel']}, mm/px={s.get('mm_per_px')}")
    if all_rows:
        pd.concat(all_rows).to_csv(out / "grains.csv", index=False)
    pd.DataFrame(summaries).to_csv(out / "summary.csv", index=False)  # = Bild-Feature-Tabelle
    print(f"-> {out.resolve()}")


if __name__ == "__main__":
    main()
```

### 7.4 `make_synthetic_data.py`: Testdaten mit bekannter Wahrheit

```python
"""
make_synthetic_data.py - Synthetische Koernerbilder MIT bekannter Wahrheit (Anzahl, Masse, TKM).

Zweck: Pipeline testen/entwickeln, bevor das echte Datenset da ist; Pitch-Demo-Fallback.
Aufruf: python make_synthetic_data.py --out ../data/synthetic --n-images 8 --seed 42
Erzeugt: <out>/images/*.png  und  <out>/labels.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

DENSITY_MG_MM3 = 1.30          # Korndichte ~1.3 g/cm3
COIN_DIAMETER_MM = 25.75       # 2-Euro-Muenze


def make_image(rng, n_grains, length_mm, width_mm, mm_per_px=0.1, size=(1500, 2000),
               touch_prob=0.15, with_coin=True, touch_dist=0.82, return_centers=False, paper=None):
    h, w = size
    bg = np.full((h, w, 3), paper if paper is not None else (205, 208, 210), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    grad = 1.0 - 0.18 * ((xx / w) * 0.6 + (yy / h) * 0.4)            # Beleuchtungsgradient
    img = bg * grad[..., None]

    centers, gt = [], []
    coin_r = COIN_DIAMETER_MM / mm_per_px / 2
    coin_c = max(200, int(coin_r + 40))                                 # Muenze voll im Bild
    margin = 120
    tries = 0
    while len(centers) < n_grains and tries < n_grains * 200:
        tries += 1
        L = max(rng.normal(length_mm, 0.07 * length_mm), 0.6 * length_mm)
        W = max(rng.normal(width_mm, 0.07 * width_mm), 0.6 * width_mm)
        Lpx, Wpx = L / mm_per_px, W / mm_per_px
        if centers and rng.random() < touch_prob:                    # beruehrend platzieren
            base = np.array(centers[rng.integers(len(centers))])
            ang = rng.uniform(0, 2 * np.pi)
            c = base + touch_dist * Lpx * np.array([np.cos(ang), np.sin(ang)])   # 0.82 = deutlich ueberlappend, 1.0 = beruehrend
        else:
            c = np.array([rng.uniform(margin, w - margin), rng.uniform(margin, h - margin)])
            if any(np.hypot(*(c - np.array(o))) < 1.15 * Lpx for o in centers):
                continue
        if not (margin / 2 < c[0] < w - margin / 2 and margin / 2 < c[1] < h - margin / 2):
            continue
        if with_coin and c[0] < 360 and c[1] < 360:                    # Muenzenecke freihalten
            continue
        if with_coin and mm_per_px < 0.08 and \
                np.hypot(c[0] - coin_c, c[1] - coin_c) < coin_r + 1.2 * Lpx:
            continue                                                   # grosse Muenze (kleiner mm/px): Zone mitskalieren
        angle = rng.uniform(0, 180)
        base_col = np.array([rng.normal(95, 8), rng.normal(140, 8), rng.normal(185, 8)])  # BGR goldbraun
        cv2.ellipse(img, (int(c[0]), int(c[1])), (int(Lpx / 2), int(Wpx / 2)), angle, 0, 360,
                    base_col.tolist(), -1, cv2.LINE_AA)
        # Laengsfurche + Glanzlicht
        a = np.radians(angle)
        d = np.array([np.cos(a), np.sin(a)]) * Lpx * 0.38
        cv2.line(img, tuple((c - d).astype(int)), tuple((c + d).astype(int)),
                 (base_col * 0.7).tolist(), 2, cv2.LINE_AA)
        centers.append(tuple(c))
        T = 0.85 * W * rng.normal(1.0, 0.05)                            # Dicke
        vol = np.pi / 6 * L * W * T
        gt.append(vol * DENSITY_MG_MM3)                                 # mg

    if with_coin:
        cv2.circle(img, (coin_c, coin_c), int(coin_r), (150, 155, 158), -1, cv2.LINE_AA)
        cv2.circle(img, (coin_c, coin_c), int(coin_r), (110, 112, 115), 4, cv2.LINE_AA)

    img += rng.normal(0, 3.0, img.shape)                                # Sensorrauschen
    img = cv2.GaussianBlur(img, (0, 0), 1.0)
    out = np.clip(img, 0, 255).astype(np.uint8)
    if return_centers:
        return out, np.array(gt), np.array(centers, np.float32)
    return out, np.array(gt)


def make_a4_scene(rng, n_grains, mm_per_px=0.1, out_size=(3000, 4000)):
    """
    Foto-aehnliche Szene: weisses A4-Blatt (210 x 297 mm) mit Koernern, perspektivisch verzerrt, leicht gedreht,
    auf dunklem Untergrund. Rueckgabe: (bild, masse_mg_je_korn, kornmitten_xy_im_bild).
    """
    L, W = rng.uniform(5.8, 7.6), rng.uniform(2.7, 3.6)
    sheet_h, sheet_w = int(297 / mm_per_px), int(210 / mm_per_px)
    sheet, gt, centers = make_image(rng, n_grains, L, W, mm_per_px, size=(sheet_h, sheet_w), touch_prob=0.04,
                                    with_coin=False, touch_dist=1.0, return_centers=True, paper=(232, 235, 236))
    Wd, Hd = out_size
    ang = np.radians(rng.uniform(-12, 12))
    sx, sy = rng.uniform(0.62, 0.72) * Wd / sheet_w, rng.uniform(0.62, 0.72) * Hd / sheet_h
    base = np.array([[0, 0], [sheet_w, 0], [sheet_w, sheet_h], [0, sheet_h]], np.float32) - [sheet_w / 2, sheet_h / 2]
    R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]], np.float32)
    dst = (base * [sx, sy]) @ R.T + [Wd / 2, Hd / 2] + rng.uniform(-0.03, 0.03, (4, 2)) * [Wd, Hd]
    dst += rng.uniform(-0.025, 0.025, (4, 2)).astype(np.float32) * [Wd, Hd]                # Perspektive
    Hm = cv2.getPerspectiveTransform(np.array([[0, 0], [sheet_w, 0], [sheet_w, sheet_h], [0, sheet_h]], np.float32), dst.astype(np.float32))
    table = np.full((Hd, Wd, 3), (38, 42, 40), np.uint8)
    table = np.clip(table + rng.normal(0, 4, table.shape), 0, 255).astype(np.uint8)
    warped = cv2.warpPerspective(sheet, Hm, (Wd, Hd), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
    mask = cv2.warpPerspective(np.full(sheet.shape[:2], 255, np.uint8), Hm, (Wd, Hd), flags=cv2.INTER_NEAREST)
    scene = np.where(mask[..., None] > 0, warped, table)
    pts = cv2.perspectiveTransform(centers.reshape(-1, 1, 2), Hm).reshape(-1, 2)
    return scene, gt, pts


def make_corn1000_mock(out: Path, n_images=6, seed=7):
    """Attrappe im Exportformat von corn1000_data.py (images/, metadata.csv, points.jsonl) fuer Tests ohne echte Daten."""
    import json
    rng = np.random.default_rng(seed)
    out = Path(out)
    rows = []
    with open(out / "points.jsonl", "w") as fp:
        (out / "images" / "S90").mkdir(parents=True, exist_ok=True)
        for i in range(n_images):
            n = int(rng.integers(180, 420))
            img, gt, pts = make_a4_scene(rng, n)
            rel = f"images/S90/mock_{i:02d}.jpg"
            cv2.imwrite(str(out / rel), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            has_pts = i % 2 == 0
            fp.write(json.dumps({"file": rel, "kernel_points": pts.tolist() if has_pts else None,
                                 "broken_points": None, "invalid_points": None}) + "\n")
            rows.append({"file": rel, "row": i, "width": img.shape[1], "height": img.shape[0], "scale": 1.0, "count": len(gt),
                         "arrangement_id": f"S90-{i:02d}", "session": "S90", "step": i, "take": 0, "species": "wheat-w",
                         "pollution": "none", "camera": "mock", "taken_at": "", "n_kernel_points": len(pts) if has_pts else np.nan,
                         "n_broken_points": np.nan, "n_invalid_points": np.nan})
    pd.DataFrame(rows).to_csv(out / "metadata.csv", index=False)
    print(f"{n_images} Attrappen-Bilder -> {out.resolve()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../data/synthetic")
    ap.add_argument("--n-images", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mm-per-px", type=float, default=0.1)
    ap.add_argument("--corn1000-mock", action="store_true", help="A4-Fotoszenen im corn1000-Exportformat statt Muenzbilder")
    a = ap.parse_args()
    if a.corn1000_mock:
        make_corn1000_mock(Path(a.out), a.n_images, a.seed)
        return

    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(a.n_images):
        # unterschiedliche "Sorten/Partien" -> unterschiedliche TKM
        L = rng.uniform(5.8, 7.6)
        W = rng.uniform(2.7, 3.6)
        n = int(rng.integers(70, 160))
        img, masses_mg = make_image(rng, n, L, W, a.mm_per_px)
        name = f"synth_{i:02d}.png"
        cv2.imwrite(str(out / "images" / name), img)
        rows.append({"image": name, "n_grains_true": len(masses_mg),
                     "total_mass_g": masses_mg.sum() / 1000,
                     "tkm_true_g": masses_mg.mean(),          # mg/Korn == g/1000 Koerner
                     "mm_per_px_true": a.mm_per_px, "mean_length_mm_true": L, "mean_width_mm_true": W})
        print(name, "n =", len(masses_mg), "TKM =", round(masses_mg.mean(), 1), "g")
    pd.DataFrame(rows).to_csv(out / "labels.csv", index=False)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
```

### 7.5 `corn1000_data.py`: Datensatz indizieren, exportieren, splitten

```python
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
```

### 7.6 `evaluate_counting.py`: Zähl-Baseline auswerten

```python
"""
evaluate_counting.py - Zaehl-Baseline (klassische Pipeline) auf corn1000 auswerten.

Pro Bild: A4-Blatt finden und entzerren -> segmentieren -> Kornzahl (Cluster-korrigiert) vs. Label `count`.
Optional: Treffergenauigkeit gegen Punkt-Labels (Precision/Recall, wenn kernel_points vorhanden).

    python evaluate_counting.py --meta ../../data/corn1000_export/metadata.csv --out ../outputs/count_baseline
    python evaluate_counting.py --meta ... --sessions S04 --limit 30 --jobs 4
    python evaluate_counting.py --meta ... --channel gray --margin-mm 10 --mm-per-px 0.12

Ausgabe: predictions.csv · metrics.json · results_row.md (Zeile fuer docs/RESULTS.md) · overlays/*.png (schlechteste + erste)
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from a4_sheet import rectify_a4, to_original
from corn1000_data import load_meta, load_points
from grain_segmentation import SegConfig, analyze_image, read_image, write_image


# --------------------------------------------------------------------------- #
# Pro Bild
# --------------------------------------------------------------------------- #
def predict_image(path: str, cfg: SegConfig, mm_per_px: float, margin_mm: float, want_overlay: bool = False):
    img = read_image(path)
    warped, info = rectify_a4(img, mm_per_px=mm_per_px, margin_mm=margin_mm)
    sheet_found = warped is not None
    if not sheet_found:                                    # Fallback: ganzes Bild, kein Massstab
        warped, info = img, None
        c = replace(cfg, mm_per_px=None)
    else:
        c = replace(cfg, mm_per_px=mm_per_px)
    t0 = time.time()
    df, ov, s = analyze_image(warped, c)
    out = {"sheet_found": sheet_found, "pred_count": int(s["n_grains_blob_corrected"]), "pred_raw": int(s["n_grains"]),
           "n_split": int(s.get("n_split", 0)), "channel": s["channel"], "seconds": round(time.time() - t0, 2),
           "median_area_mm2": float(df["area_mm2"].median()) if len(df) and "area_mm2" in df else np.nan,
           "pts_orig": None, "overlay": ov if want_overlay else None}
    if len(df) and info is not None:
        out["pts_orig"] = to_original(df[["cx", "cy"]].to_numpy(), info)
        out["n_est"] = df["n_est_blob"].to_numpy()
    return out


def _work(args):
    return predict_image(*args)


# --------------------------------------------------------------------------- #
# Metriken
# --------------------------------------------------------------------------- #
def count_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    e = p - y
    ae = np.abs(e)
    return {"n": int(len(y)), "MAE": float(ae.mean()), "RMSE": float(np.sqrt((e ** 2).mean())),
            "MAPE_pct": float((ae / y).mean() * 100), "bias": float(e.mean()), "max_abs_err": float(ae.max()),
            "within_1pct": float((ae / y <= 0.01).mean() * 100), "within_2pct": float((ae / y <= 0.02).mean() * 100),
            "within_5pct": float((ae / y <= 0.05).mean() * 100)}


def point_scores(pred_xy: np.ndarray, gt_xy: np.ndarray):
    """Precision/Recall/F1 mit eindeutiger Zuordnung (ungarisch); Radius = 0,5 x medianer Nachbarabstand der GT-Punkte."""
    gt_xy = np.asarray(gt_xy, float)
    if len(gt_xy) < 3 or len(pred_xy) == 0:
        return None
    d, _ = cKDTree(gt_xy).query(gt_xy, k=2)
    r = 0.5 * float(np.median(d[:, 1]))
    D = np.linalg.norm(pred_xy[:, None, :] - gt_xy[None, :, :], axis=2)
    D[D > r] = 1e6
    ri, ci = linear_sum_assignment(D)
    tp = int((D[ri, ci] < 1e6).sum())
    prec, rec = tp / len(pred_xy), tp / len(gt_xy)
    return {"tp": tp, "precision": prec, "recall": rec, "f1": 2 * prec * rec / max(prec + rec, 1e-9), "radius_px": r}


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta", required=True, help="metadata.csv aus corn1000_data.py export")
    ap.add_argument("--out", default="../outputs/count_baseline")
    ap.add_argument("--sessions", nargs="*", default=None)
    ap.add_argument("--splits", nargs="*", default=None, help="nur bei `index`-Metadaten: z.B. test")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--mm-per-px", type=float, default=0.15, help="Aufloesung des entzerrten Blatts (kleiner = genauer, langsamer)")
    ap.add_argument("--margin-mm", type=float, default=8.0, help="Blattrand abschneiden (Schatten, Papierkante)")
    ap.add_argument("--channel", default="auto")
    ap.add_argument("--method", default="otsu")
    ap.add_argument("--no-watershed", action="store_true")
    ap.add_argument("--n-overlays", type=int, default=12)
    a = ap.parse_args()

    meta = load_meta(a.meta)
    if a.sessions:
        meta = meta[meta["session"].isin(a.sessions)]
    if a.splits and "split" in meta.columns:
        meta = meta[meta["split"].isin(a.splits)]
    if a.limit:
        meta = meta.head(a.limit)
    meta = meta.reset_index(drop=True)
    points = load_points(a.meta)
    cfg = SegConfig(channel=a.channel, method=a.method, watershed=not a.no_watershed, drop_border=False)
    out = Path(a.out)
    (out / "overlays").mkdir(parents=True, exist_ok=True)

    jobs = [(p, cfg, a.mm_per_px, a.margin_mm, False) for p in meta["path"]]
    t0 = time.time()
    if a.jobs > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            res = list(ex.map(_work, jobs, chunksize=2))
    else:
        res = []
        for k, j in enumerate(jobs):
            res.append(_work(j))
            if (k + 1) % 20 == 0:
                print(f"  {k + 1}/{len(jobs)} ({time.time() - t0:.0f} s)")
    print(f"{len(res)} Bilder in {time.time() - t0:.0f} s")

    pred = meta[["file", "session", "species", "pollution", "camera", "count"]].copy()
    for key in ["sheet_found", "pred_count", "pred_raw", "n_split", "channel", "seconds", "median_area_mm2"]:
        pred[key] = [r[key] for r in res]
    pred["error"] = pred["pred_count"] - pred["count"]
    pred["abs_error"] = pred["error"].abs()
    pred["rel_error_pct"] = pred["error"] / pred["count"] * 100

    # Punkt-Treffer
    ps = []
    for r, f in zip(res, meta["file"]):
        gt = points.get(f, {}).get("kernel_points")
        ps.append(point_scores(r["pts_orig"], gt) if (gt and r["pts_orig"] is not None) else None)
    for k in ["precision", "recall", "f1"]:
        pred[f"pt_{k}"] = [s[k] if s else np.nan for s in ps]

    pred.to_csv(out / "predictions.csv", index=False)
    y, p = pred["count"].to_numpy(float), pred["pred_count"].to_numpy(float)
    metrics = {"overall": count_metrics(y, p),
               "per_session": {s: count_metrics(g["count"].to_numpy(float), g["pred_count"].to_numpy(float))
                               for s, g in pred.groupby("session")},
               "per_species": {s: count_metrics(g["count"].to_numpy(float), g["pred_count"].to_numpy(float))
                               for s, g in pred.groupby("species")},
               "sheet_found_pct": float(pred["sheet_found"].mean() * 100),
               "seconds_per_image": float(pred["seconds"].mean()),
               "points": {k: float(np.nanmean(pred[f"pt_{k}"])) for k in ["precision", "recall", "f1"]} if pred["pt_f1"].notna().any() else None,
               "config": {"mm_per_px": a.mm_per_px, "margin_mm": a.margin_mm, "channel": a.channel, "method": a.method,
                          "watershed": not a.no_watershed}}
    json.dump(metrics, open(out / "metrics.json", "w"), indent=2)

    m = metrics["overall"]
    row = (f"| {time.strftime('%Y-%m-%d %H:%M')} | (Name) | Klassisch: A4-Entzerrung + Otsu + Watershed "
           f"({'/'.join(a.sessions) if a.sessions else 'alle Sessions'}, n={m['n']}) | {m['MAE']:.1f} | {m['max_abs_err']:.0f} | "
           f"MAPE {m['MAPE_pct']:.1f} %, Bias {m['bias']:+.1f}, ±2 %: {m['within_2pct']:.0f} % der Bilder |")
    (out / "results_row.md").write_text(row + "\n", encoding="utf-8")

    # Overlays: schlechteste zuerst, dann die ersten
    order = list(pred.sort_values("abs_error", ascending=False).index[:a.n_overlays // 2]) + list(pred.index[:a.n_overlays - a.n_overlays // 2])
    for idx in dict.fromkeys(order):
        r = predict_image(meta.loc[idx, "path"], cfg, a.mm_per_px, a.margin_mm, want_overlay=True)
        ov = r["overlay"]
        cv2.putText(ov, f"label {int(pred.loc[idx, 'count'])}  pred {int(pred.loc[idx, 'pred_count'])}", (10, ov.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)
        write_image(out / "overlays" / f"{Path(meta.loc[idx, 'file']).stem}.jpg", cv2.resize(ov, None, fx=0.5, fy=0.5))

    print(f"\nGesamt: MAE {m['MAE']:.2f} | MAPE {m['MAPE_pct']:.2f} % | Bias {m['bias']:+.2f} | max {m['max_abs_err']:.0f} | "
          f"Blatt gefunden {metrics['sheet_found_pct']:.0f} %")
    for s, v in metrics["per_session"].items():
        print(f"  {s}: MAE {v['MAE']:.2f}, MAPE {v['MAPE_pct']:.2f} %, Bias {v['bias']:+.2f} (n={v['n']})")
    print("Zeile fuer docs/RESULTS.md:\n" + row)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
```

### 7.7 `classical_counter.py`: Adapter für tausendkorn.eval

```python
"""
classical_counter.py - Adapter: klassische Pipeline als Zaehler fuer `python -m tausendkorn.eval` (src/tausendkorn/eval.py).

Schnittstelle des Teams: count(image: PIL.Image.Image) -> int | {"count": int, "points": [[x, y], ...]}
Die Punkte liegen im Originalbild (aufrecht), wie die Labels.

    cd <Repo-Wurzel>
    PYTHONPATH=wissensbank/scripts uv run python -m tausendkorn.eval classical_counter:count --split test --name classical-otsu
(opencv-python, scipy, scikit-image, pandas muessen installiert sein: pip install -r wissensbank/requirements.txt)

Einstellungen per Umgebungsvariable: CC_MM_PER_PX (0.15), CC_MARGIN_MM (8), CC_CHANNEL (auto).
"""
from __future__ import annotations

import os
from dataclasses import replace

import cv2
import numpy as np

from a4_sheet import rectify_a4, to_original
from grain_segmentation import SegConfig, analyze_image

_MM = float(os.environ.get("CC_MM_PER_PX", "0.15"))
_MARGIN = float(os.environ.get("CC_MARGIN_MM", "8"))
_CFG = SegConfig(channel=os.environ.get("CC_CHANNEL", "auto"), drop_border=False)


def count(image) -> dict:
    bgr = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    warped, info = rectify_a4(bgr, mm_per_px=_MM, margin_mm=_MARGIN)
    if warped is None:                                          # Blatt nicht gefunden: ganzes Bild, ohne Massstab
        df, _, s = analyze_image(bgr, replace(_CFG, mm_per_px=None))
        pts = df[["cx", "cy"]].to_numpy() if len(df) else np.zeros((0, 2))
    else:
        df, _, s = analyze_image(warped, replace(_CFG, mm_per_px=_MM))
        pts = to_original(df[["cx", "cy"]].to_numpy(), info) if len(df) else np.zeros((0, 2))
    return {"count": int(s["n_grains_blob_corrected"]), "points": pts.round(1).tolist()}
```

### 7.8 `eda_tabular.py`: Tabellenanalyse und Datenimport

```python
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
```

### 7.9 `merge_labels.py`: Bild-Features und Labels verbinden

```python
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
```

### 7.10 `train_model.py`: Modelltraining und Evaluation

```python
"""
train_model.py - Generische sklearn-Pipeline fuer Regression (z.B. TKM) und Klassifikation (z.B. Qualitaetsklasse).

Aufruf:
  python train_model.py --csv ../outputs/seg/image_features.csv --target tkm_g --drop image
  python train_model.py --csv daten.xlsx --target klasse --group feld_id

Prinzip: Baseline (Mittelwert/Mehrheit) vs. Ridge/LogReg vs. RandomForest vs. HistGradientBoosting,
         Kreuzvalidierung (bei kleinen n: Leave-One-Out), Out-of-fold-Vorhersagen, Bestes Modell speichern.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, r2_score)
from sklearn.model_selection import GroupKFold, KFold, LeaveOneOut, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from eda_tabular import load_table

RANDOM_STATE = 42


def infer_task(y: pd.Series) -> str:
    """Text/Kategorie/Bool -> Klassifikation; Ganzzahl mit <= 10 Werten -> Klassifikation; sonst Regression."""
    if not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y):
        return "clf"
    if pd.api.types.is_integer_dtype(y) and y.nunique() <= 10:
        return "clf"
    return "reg"


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    num = X.select_dtypes(include="number").columns.tolist()
    cat = [c for c in X.columns if c not in num]
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat),
    ])


def clean_features(X: pd.DataFrame) -> pd.DataFrame:
    """Entfernt konstante, fast leere und ID-artige Spalten (z.B. Dateinamen)."""
    drop = [c for c in X.columns
            if X[c].isna().mean() > 0.5 or X[c].nunique(dropna=True) <= 1
            or (not pd.api.types.is_numeric_dtype(X[c]) and X[c].nunique() == len(X))]
    if drop:
        print("Entfernte Spalten:", drop)
    return X.drop(columns=drop)


def candidate_models(task: str) -> dict:
    if task == "reg":
        return {
            "baseline_mean": DummyRegressor(strategy="mean"),
            "ridge": Ridge(alpha=1.0),
            "random_forest": RandomForestRegressor(n_estimators=400, min_samples_leaf=2,
                                                   random_state=RANDOM_STATE, n_jobs=-1),
            "hist_gb": HistGradientBoostingRegressor(max_depth=4, learning_rate=0.06,
                                                     min_samples_leaf=5, random_state=RANDOM_STATE),
        }
    return {
        "baseline_majority": DummyClassifier(strategy="most_frequent"),
        "logreg": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(n_estimators=400, class_weight="balanced",
                                                random_state=RANDOM_STATE, n_jobs=-1),
        "hist_gb": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.06,
                                                  random_state=RANDOM_STATE),
    }


def make_cv(task, n, y, groups, n_splits):
    if groups is not None:
        return GroupKFold(n_splits=min(n_splits, groups.nunique()))
    if task == "reg":
        return LeaveOneOut() if n < 40 else KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    min_class = y.value_counts().min()
    return StratifiedKFold(n_splits=max(2, min(n_splits, int(min_class))), shuffle=True,
                           random_state=RANDOM_STATE)


def score(task, y_true, y_pred) -> dict:
    if task == "reg":
        return {"r2": r2_score(y_true, y_pred), "mae": mean_absolute_error(y_true, y_pred),
                "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
                "mape_pct": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)}
    return {"accuracy": accuracy_score(y_true, y_pred), "f1_macro": f1_score(y_true, y_pred, average="macro")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--target", required=True)
    ap.add_argument("--task", default="auto", choices=["auto", "reg", "clf"])
    ap.add_argument("--drop", nargs="*", default=[], help="Spalten ohne Vorhersagewert (IDs, Leckage!)")
    ap.add_argument("--group", default=None, help="Gruppenspalte (z.B. Feld/Partie) gegen Leckage")
    ap.add_argument("--cv", type=int, default=5)
    ap.add_argument("--out", default="../outputs/model")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = load_table(a.csv, a.sheet)
    if a.target not in df.columns:
        raise SystemExit(f"Zielspalte '{a.target}' nicht gefunden. Vorhanden: {list(df.columns)[:30]}")
    df = df.dropna(subset=[a.target]).reset_index(drop=True)
    unknown = [c for c in a.drop if c not in df.columns]
    if unknown:
        print("Hinweis: --drop-Spalten nicht vorhanden (ignoriert):", unknown)
    a.drop = [c for c in a.drop if c in df.columns]
    y = df[a.target]
    task = infer_task(y) if a.task == "auto" else a.task
    groups = df[a.group] if a.group else None
    X = clean_features(df.drop(columns=[a.target] + a.drop + ([a.group] if a.group else [])))
    print(f"Aufgabe: {'Regression' if task == 'reg' else 'Klassifikation'} | n={len(X)} | Features={X.shape[1]}")

    cv = make_cv(task, len(X), y, groups, a.cv)
    results, oof = {}, {}
    for name, model in candidate_models(task).items():
        pipe = Pipeline([("prep", build_preprocessor(X)), ("model", model)])
        pred = cross_val_predict(pipe, X, y, cv=cv, groups=groups)
        results[name] = score(task, y, pred)
        oof[name] = pred
        print(f"{name:18s}", {k: round(float(v), 4) for k, v in results[name].items()})

    key = "rmse" if task == "reg" else "f1_macro"
    non_base = {k: v for k, v in results.items() if not k.startswith("baseline")}
    best = (min if task == "reg" else max)(non_base, key=lambda k: non_base[k][key])
    print("Bestes Modell:", best)

    best_pipe = Pipeline([("prep", build_preprocessor(X)), ("model", candidate_models(task)[best])]).fit(X, y)
    joblib.dump({"pipeline": best_pipe, "features": list(X.columns), "target": a.target, "task": task},
                out / "best_model.joblib")
    pd.DataFrame({"y_true": y, **{f"oof_{k}": v for k, v in oof.items()}}).to_csv(out / "oof_predictions.csv",
                                                                                   index=False)
    json.dump({"best": best, "task": task, "n": len(X),
               "results": {k: {m: float(v) for m, v in r.items()} for k, r in results.items()}},
              open(out / "metrics.json", "w"), indent=2)

    # Permutation Importance (in-sample, nur zur Orientierung!)
    imp = permutation_importance(best_pipe, X, y, n_repeats=10, random_state=RANDOM_STATE,
                                 scoring="r2" if task == "reg" else "f1_macro")
    imp_df = pd.DataFrame({"feature": X.columns, "importance": imp.importances_mean}).sort_values(
        "importance", ascending=False)
    imp_df.to_csv(out / "feature_importance.csv", index=False)
    print(imp_df.head(10).round(4).to_string(index=False))

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    if task == "reg":
        ax[0].scatter(y, oof[best], s=22)
        lim = [min(y.min(), oof[best].min()), max(y.max(), oof[best].max())]
        ax[0].plot(lim, lim, "k--", lw=1)
        ax[0].set_xlabel(f"{a.target} (gemessen)")
        ax[0].set_ylabel("Vorhersage (out-of-fold)")
        ax[0].set_title(f"{best}: R2={results[best]['r2']:.3f}, MAE={results[best]['mae']:.2f}")
    else:
        cm = confusion_matrix(y, oof[best])
        ax[0].imshow(cm, cmap="Blues")
        ax[0].set_title(f"{best}: Confusion Matrix")
    top = imp_df.head(10)[::-1]
    ax[1].barh(top["feature"], top["importance"])
    ax[1].set_title("Permutation Importance (in-sample)")
    fig.tight_layout()
    fig.savefig(out / "model_overview.png", dpi=120)
    print("->", out.resolve())


if __name__ == "__main__":
    main()
```

### 7.11 `app_streamlit.py`: Demo-Oberfläche

```python
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
```

### 7.12 `selftest.py`: Gesamtprüfung

```python
"""
selftest.py - Ein-Minuten-Gesundheitscheck des gesamten Stacks (nach Setup ausfuehren).

    python selftest.py

Prueft: Formeln, synthetische Bilder, Segmentierung (Zaehlung, Massstab, TKM Methode A),
        deutsches CSV-Format + Label-Merge, EDA, Modelltraining, Streamlit-App kompiliert.
Alle Pruefungen laufen in einem temporaeren Ordner; nichts im Projekt wird ueberschrieben.
"""
from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
results: list[tuple[str, bool, str]] = []


def run(args: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, "-W", "ignore", *args], cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
    return r


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK ' if ok else 'FAIL'}] {name} {detail}")


def main():
    # 1) Formeln
    import tkm_utils as tu
    check("tkm_utils Formeln",
          abs(tu.tkm_from_sample(4.5, 100) - 45) < 1e-9 and abs(tu.seed_rate_kg_ha(350, 45, 95) - 165.789) < 0.01
          and abs(tu.yield_dt_ha(600, 35, 45) - 94.5) < 1e-9 and tu.required_sample_size(12, 2) == 139)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # 2) Synthetische Bilder + Segmentierung
        r = run(["make_synthetic_data.py", "--out", str(td / "syn"), "--n-images", "4", "--seed", "42"])
        check("Synthetische Bilder erzeugt", r.returncode == 0)
        r = run(["grain_segmentation.py", "--input", str(td / "syn" / "images"), "--out", str(td / "seg"),
                 "--ref-diameter-mm", "25.75"])
        check("Segmentierung laeuft", r.returncode == 0)
        s = pd.read_csv(td / "seg" / "summary.csv")
        lab = pd.read_csv(td / "syn" / "labels.csv")
        m = s.merge(lab, on="image")
        cnt_err = (m["n_grains_blob_corrected"] - m["n_grains_true"]).abs()
        check("Zaehlfehler <= 4 Koerner je Bild", cnt_err.max() <= 4, f"(max {int(cnt_err.max())})")
        scale_err = ((m["mm_per_px"] / m["mm_per_px_true"] - 1).abs() * 100)
        check("Massstab ueber Muenze < 3 %", scale_err.max() < 3, f"(max {scale_err.max():.2f} %)")
        tkm_a = m["total_mass_g"] / m["n_grains_blob_corrected"] * 1000
        a_err = ((tkm_a / m["tkm_true_g"] - 1).abs() * 100)
        check("TKM Methode A Fehler < 3 %", a_err.max() < 3, f"(max {a_err.max():.2f} %)")

        # 3b) corn1000-Workflow: Attrappe im Exportformat -> A4-Entzerrung -> Zaehlung -> Metriken
        mock = td / "mock"
        (mock / "images").mkdir(parents=True)
        r = run(["make_synthetic_data.py", "--out", str(mock), "--corn1000-mock", "--n-images", "3", "--seed", "7"])
        check("corn1000-Attrappe erzeugt", r.returncode == 0 and (mock / "metadata.csv").exists())
        r = run(["evaluate_counting.py", "--meta", str(mock / "metadata.csv"), "--out", str(td / "cnt"), "--n-overlays", "2"])
        mj = json.load(open(td / "cnt" / "metrics.json")) if r.returncode == 0 else {}
        ov = mj.get("overall", {})
        check("A4-Blatt in allen Attrappen gefunden", mj.get("sheet_found_pct") == 100.0)
        check("Zaehlbaseline MAPE < 3 % auf Attrappe", bool(ov) and ov["MAPE_pct"] < 3, f"(MAPE {ov.get('MAPE_pct', float('nan')):.2f} %)")
        from PIL import Image
        import classical_counter
        from corn1000_data import load_meta, session_folds
        mm = load_meta(mock / "metadata.csv")
        r0 = mm.iloc[0]
        res = classical_counter.count(Image.open(r0["path"]))
        check("Adapter classical_counter.count (Schnittstelle des Team-Evals)",
              isinstance(res, dict) and abs(res["count"] - r0["count"]) <= 0.03 * r0["count"] and len(res["points"]) > 0,
              f"(pred {res['count']} vs {int(r0['count'])})")
        check("Session-Folds ohne Ueberlappung", all(set(t).isdisjoint(v) for _, t, v in session_folds(mm)))

        # 3) Deutsches Tabellenformat, Label-Merge, EDA, Training
        rng = np.random.default_rng(0)
        labels = pd.DataFrame({"Probe": [Path(i).stem.upper().replace("_", "-") for i in s["image"]],
                               "TKM": np.round(rng.normal(45, 4, len(s)), 2)})
        labels["TKM"] = labels["TKM"].astype(str).str.replace(".", ",", regex=False)
        labels.to_csv(td / "labels_de.csv", sep=";", index=False, encoding="cp1252")
        r = run(["merge_labels.py", "--features", str(td / "seg" / "summary.csv"), "--labels",
                 str(td / "labels_de.csv"), "--labels-key", "Probe", "--out", str(td / "merged.csv")])
        mg = pd.read_csv(td / "merged.csv") if r.returncode == 0 else pd.DataFrame()
        check("Label-Merge (Semikolon, Dezimalkomma, andere Namen)",
              r.returncode == 0 and len(mg) == len(s) and pd.api.types.is_float_dtype(mg["TKM"]))

        tab = pd.DataFrame({"x1": rng.normal(size=80), "x2": rng.normal(size=80),
                            "sorte": rng.choice(["A", "B", "C"], 80)})
        tab["y"] = 3 * tab["x1"] - 2 * tab["x2"] + (tab["sorte"] == "B") * 2 + rng.normal(0, 0.3, 80)
        tab.to_csv(td / "tab.csv", index=False)
        r = run(["eda_tabular.py", "--csv", str(td / "tab.csv"), "--target", "y", "--out", str(td / "eda")])
        check("EDA-Report erzeugt", r.returncode == 0 and (td / "eda" / "eda_report.md").exists())
        r = run(["train_model.py", "--csv", str(td / "tab.csv"), "--target", "y", "--out", str(td / "model")])
        ok = r.returncode == 0 and (td / "model" / "metrics.json").exists()
        r2 = json.load(open(td / "model" / "metrics.json"))["results"] if ok else {}
        best_r2 = max((v["r2"] for k, v in r2.items() if not k.startswith("baseline")), default=-1)
        check("Modelltraining (Regression, R2 > 0.8)", ok and best_r2 > 0.8, f"(R2 {best_r2:.3f})")

    # 4) App kompiliert
    try:
        py_compile.compile(str(HERE / "app_streamlit.py"), doraise=True)
        check("Streamlit-App syntaktisch korrekt", True)
    except py_compile.PyCompileError as e:
        check("Streamlit-App syntaktisch korrekt", False, str(e))

    failed = [n for n, ok, _ in results if not ok]
    print("\n" + ("ALLE PRUEFUNGEN BESTANDEN" if not failed else f"FEHLGESCHLAGEN: {failed}"))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
```

### 7.13 `requirements.txt`: Abhängigkeiten

```text
numpy>=1.24
pandas>=2.0
scipy>=1.10
scikit-learn>=1.3
scikit-image>=0.21
opencv-python>=4.8
matplotlib>=3.7
joblib>=1.3
openpyxl>=3.1
tabulate>=0.9
streamlit>=1.35
pillow>=10.0
datasets>=2.19        # nur fuer corn1000_data.py export (Hub-Download)
# Optional (nur bei Bedarf, grosse Downloads, Version/API vorher pruefen):
# cellpose
# ultralytics
# torch
```

Die Dateinamen distributions.png, correlation.png und target_scatter.png im eingebetteten EDA-Skript sind generierte Ausgaben, keine mitgelieferten Abbildungen. Erzeugen mit `uv run --no-project --with pandas --with matplotlib --with seaborn python wissensbank/scripts/eda_tabular.py --help` (Argumente dort); Ausgaben unter einem lokalen Arbeitsordner ablegen.
