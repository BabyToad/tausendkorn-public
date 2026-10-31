# 05 – Datensatz `SmartFarmingLab/corn1000`: Aufbau, Einbindung, Auswertung

Quellen: Dataset-Card auf Hugging Face (Stand 27.10.2026, Seite zuletzt am 26.10. aktualisiert), Handout Team 1, `../docs/CHALLENGE.md`.
**Der Datensatz selbst wurde hier nicht heruntergeladen** (Hugging Face war aus der Entwicklungsumgebung nicht erreichbar). Alles Folgende beruht auf der Dataset-Card; die Werkzeuge sind an einer Attrappe im selben Format getestet (siehe Abschnitt 8).

---

## 1. Auf einen Blick

Stand: Dataset-Card auf dem Hub, geprüft am 27.10.2026 (Karte zuletzt am 26.10. aktualisiert). Frühere Fassungen nannten 751 Bilder und nur `train`; das ist überholt.

| Merkmal | Inhalt |
|---|---|
| Motiv | Getreidekörner auf weißem A4-Blatt (dunkler oder kontrastreicher Untergrund), Handyfoto |
| Label | `count` = exakte Kornzahl auf dem Blatt (ISO 520:2010) |
| Umfang | **836 Bilder**, 128 Arrangements, 170–1000 Körner je Bild |
| Punkt-Labels | 158 Bilder mit Kornmitten (`kernel_points`), Bruchkorn (`broken_points`), sonstige Objekte (`invalid_points`); Punktzahl weicht von `count` um wenige Körner ab, `count` bleibt das Label |
| Arten | `oats-s`, `barley-w`, `wheat-w`, `durum-w`, `rye-w` (fünf Arten) |
| Kameras | Galaxy S23, Galaxy Tab S6 Lite, iPhone 8, Pixel 9 |
| Roh-Dateien | Ordner `raw/` mit DNG-Originalen; `data/` enthält die entwickelten JPEGs (rawpy, Qualität 95). Entwickelte DNG-Farben weichen von den Handy-JPEGs ab |
| Lizenz | CC BY-NC 4.0 |

### Splits (laut Card)

| Split | Inhalt | Bilder | Körner je Bild |
|---|---|---|---|
| `train` | Sessions S02 Hafer (124), S03 Gerste (231), S04 Weizen (131), S05 Hartweizen (265) | 751 | 170–800 |
| `test` | Session `count_1000`: alle fünf Arten (auch Roggen), je Bild genau 1000 Körner, 13–21 Fotos je Art, nur ein Arrangement je Art, 26.10. mit Galaxy S23 und iPhone 8 | 85 | 1000 |

Folgen für die Arbeit:
- Der Test ist **anders als das Training**: höhere Dichte (1000 statt höchstens 800 Körner) und mit Roggen eine Art, die im Training fehlt. Modelle, die Dichte nicht extrapolieren können (feste Obergrenze, Regression auf wenige Bilder), brechen hier ein. Ein Modell, das Körner einzeln erkennt oder zählt, ist im Vorteil.
- Für das Training nach `session` splitten; als Validierung zusätzlich eine dichte Session (S04 mit bis zu 800 Körnern) verwenden und prüfen, ob der Fehler mit der Dichte wächst.
- Im Test-Split sind die Arten nach Aufnahmezeit zugeordnet (keine Kartenfotos), und alle Bilder desselben Arrangements zählen als eine Beobachtung: 85 Bilder, aber nur 5 unabhängige Layouts. Genauigkeitszahlen darauf sind also grob; Bias je Art ansehen.
- Gerste im Test ist leicht verschmutzt, die übrigen sind sauber.
- `src/tausendkorn/eval.py` liest `data/corn1000/data/<split>/metadata.jsonl`; das passt zur Card (`data/train/**`, `data/test/**`).

**Erste Aktion nach dem Download** (Abschnitt 3.3)

---|---|---|
| Bilder | 751 | 836 |
| Arrangements | 123 | 128 |
| Kornzahl je Bild | 170–800 | 170–1000 |
| Test-Split | keiner genannt, nur `train` | `test` = `count_1000` (je Bild genau 1000 Körner) |
| Kornarten | 5 Codes, Sessions S02–S05 decken 4 Arten ab (`rye-w` ohne Session) | Handout: „vier Kornarten“; Challenge-Datei: fünf Arten |
| Bilder mit Punkten | 158 | Handout: „ca. 200“; Challenge-Datei: 158 |

Hinweis: `src/tausendkorn/eval.py` des Teams erwartet im lokalen Download die Ordner `data/corn1000/data/<split>/metadata.jsonl` (Standard `--split test`). Das spricht dafür, dass im Hub-Repository neben `train` auch ein `test`-Ordner liegt, den die Dataset-Card (Splits-Abschnitt) nicht aufführt. Welche Zahlen stimmen, zeigt der lokale Download. **Erste Aktion nach dem Download** (Abschnitt 3.3): Zeilenzahl, Sessions und `count`-Maximum selbst nachzählen und `docs/CHALLENGE.md` korrigieren, falls nötig. Wenn es keinen `count_1000`-Split gibt, braucht das Team eine eigene Evaluationsregel (Abschnitt 5).

---

## 2. Spalten

| Spalte | Typ | Bedeutung | Hinweis |
|---|---|---|---|
| `image` | Bild (JPEG) | Foto | EXIF-Drehung beachten (Abschnitt 6) |
| `count` | int | Kornzahl, **das Label** | Zielgröße für die Auswertung |
| `arrangement_id` | string | ein physisches Kornlayout, `<session>-<step>[-<take>]` | pro Arrangement 2–22 Fotos |
| `session` | string | z. B. `S02` | **Split-Schlüssel** |
| `step` | int | Kartennummer in der Session | |
| `take` | int | Wiederholungsnummer nach REDO | |
| `species` | string | Art-Code (siehe oben) | je Session eine Art |
| `pollution` | string | `none`, `light`, `heavy` | Fremdmaterial, wird nie mitgezählt |
| `camera` | string | Kameramodell (EXIF) | Domänenunterschiede |
| `taken_at` | string | Aufnahmezeit (EXIF, ohne Zeitzone) | |
| `raw_file` | string | Pfad zur DNG-Originaldatei, sonst leer | für uns meist irrelevant |
| `kernel_points` | Liste `[x, y]` | Mitte jedes gezählten Korns | `null`, wenn nicht annotiert |
| `broken_points` | Liste `[x, y]` | Bruchkörner (nicht gezählt) | |
| `invalid_points` | Liste `[x, y]` | andere nicht zählbare Objekte | |

### Zählregeln (ISO 520:2010), wichtig für jedes Modell

- Gezählt: intakte Körner **inklusive Schrumpfkörner**; Gerste und Hafer **mit Spelze**; Zwillinge zählen doppelt.
- Nicht gezählt: Bruchkorn, Spreu, Stroh, Grannen, Fremdsamen, Staub, Steine, Büromaterial.
- Grenzfälle wurden bei der Aufnahme aussortiert, damit die Zahl exakt stimmt.

Folgerungen: Ein Modell muss **intakt von gebrochen** unterscheiden. Eine reine Flächenzählung zählt Bruchstücke und Spreu falsch mit. Zwillinge (zwei zusammengewachsene Körner) sehen wie ein großes Korn aus und zählen doppelt. Für das Qualitätsmerkmal Bruchkorn liefern `broken_points` direkt Trainingsdaten.

### Punkt-Labels

- Koordinaten in Pixeln des **aufrechten** Bildes (nach EXIF-Drehung), Ursprung oben links.
- Handarbeit in CVAT. `len(kernel_points)` kann um einige Körner von `count` abweichen (verpasst oder am Bildrand). **`count` bleibt das Label**; Punkte dienen zum Training/Lokalisieren.

---

## 3. Einbinden: drei Wege

### 3.1 Übersicht

| Weg | Wann | Vorteil | Nachteil |
|---|---|---|---|
| **D. Lokaler Download und Index** (Team-Standard laut Haupt-README: `hf download … --local-dir data/corn1000`) | Arbeit am PC mit `uv run python -m tausendkorn.eval`, klassische Baseline, App | keine Kopie nötig; passt zu `src/tausendkorn/eval.py`; `corn1000_data.py index` schreibt nur `metadata.csv` und `points.jsonl` (Pfade zeigen auf die Originale) | Originalauflösung (groß), kein Verkleinern |
| **A. Export aus dem Hub** (`corn1000_data.py export`) | wenn nur `load_dataset` genutzt wird oder Bilder verkleinert werden sollen (`--max-side`) | plain JPEG + CSV, EXIF bereinigt, filterbar nach Session | zweiter Download/Platz |
| **B. Direkt `load_dataset` (Kaggle)** | GPU-Training in Kaggle (T4 ×2) | laut Handout vorgesehen, kein Token nötig | Notebook-Sitzung flüchtig, „Save Version“ nicht vergessen |

Empfehlung: **D für die tägliche Arbeit am PC** (ein Download, alle Werkzeuge nutzen dieselben Dateien), **B nur für das GPU-Training**. Vorhersagen aus Kaggle als CSV mit Spalte `file_name` oder `file` zurückholen und mit denselben Kennzahlen wie die lokalen Läufe auswerten.

### 3.2a Weg D: Download und Index

```bash
# aus der Repo-Wurzel (Anleitung der Haupt-README)
uvx --from huggingface_hub hf download SmartFarmingLab/corn1000 --repo-type dataset --local-dir data/corn1000

cd wissensbank/scripts
python corn1000_data.py index --src ../../data/corn1000 --out ../../data/corn1000_index
python corn1000_data.py info  --meta ../../data/corn1000_index/metadata.csv       # Splits, Sessions, Arten, count_1000?
python evaluate_counting.py --meta ../../data/corn1000_index/metadata.csv --splits test --out ../outputs/count_test --jobs 4
```

`index` liest `data/corn1000/data/<split>/metadata.jsonl` (Schema wie in `eval.py`: `file_name`, `count`, `session`, `species`, `camera`, optional Punktlisten). Fehlen Spalten, meldet das Skript den Ordnerinhalt; die Punktspalten dürfen Listen oder JSON-Texte sein. **Dieses Layout ist aus `eval.py` abgeleitet und nur an einem Nachbau getestet.**

**Mit dem Team-Evaluationsskript:** `wissensbank/scripts/classical_counter.py` erfüllt dessen Schnittstelle (`count(image) -> {"count", "points"}`):

```bash
PYTHONPATH=wissensbank/scripts uv run python -m tausendkorn.eval classical_counter:count --split test --name classical-otsu
```

Dafür müssen `opencv-python`, `scipy`, `scikit-image`, `pandas` in der Umgebung liegen (`uv pip install -r wissensbank/requirements.txt`). Beide Auswertungen sind gleichwertig: `eval.py` schreibt `runs/<name>.csv` (MAE, MAPE, Bias je Art), `evaluate_counting.py` rechnet zusätzlich ±x-%-Quoten, Punkt-Treffer und Overlays. Neue Modelle als `module:function` an `eval.py` anhängen, damit alle Ansätze gleich bewertet werden.

### 3.2 Weg A: Export aus dem Hub

Vorbereitung (einmalig, Internet nötig): `pip install -r requirements.txt` (enthält `datasets`, `pillow`).

```bash
cd wissensbank/scripts
# kleiner Probelauf zuerst (3 Bilder aus Session S04)
python corn1000_data.py export --out ../../data/corn1000_export --sessions S04 --limit 3
python corn1000_data.py info   --meta ../../data/corn1000_export/metadata.csv

# vollständiger Export; --max-side 3000 verkleinert grosse Fotos (Punkte werden mitskaliert)
python corn1000_data.py export --out ../../data/corn1000_export --max-side 3000
```

Ergebnis:

```
data/corn1000_export/
├── images/<session>/<arrangement>_<zeile>.jpg    aufrecht, ohne EXIF-Tag
├── metadata.csv                                  eine Zeile je Bild (+ Pfad, Größe, Punktanzahlen)
├── points.jsonl                                  kernel_points / broken_points / invalid_points je Datei
└── export_info.json
```

`data/` liegt im Repo-Stamm und ist per `.gitignore` ausgeschlossen. Der vollständige Datensatz wird aus Größen- und Verpackungsgründen nicht mitgeliefert. CC BY-NC 4.0 erlaubt nichtkommerzielle Weitergabe mit Namensnennung, Lizenzlink und Änderungsangabe; siehe ../DATA_LICENSE.md. (Nicht verwechseln: das Skript `export` lädt über `load_dataset`; wer schon `hf download` gemacht hat, nimmt Weg D.)
Bereits mit `load_dataset` geladen: der Hugging-Face-Cache wird wiederverwendet, es gibt keinen zweiten Download. `--from-disk` gilt nur für Ordner aus `Dataset.save_to_disk`. Ein mit `hf download … --local-dir` geladener Ordner wird mit `index` gelesen (Weg D).

Lesen im Code:

```python
from corn1000_data import load_meta, load_points, session_folds, holdout_sessions
meta = load_meta("../../data/corn1000_export/metadata.csv")     # DataFrame mit Spalte `path`
pts  = load_points("../../data/corn1000_export/metadata.csv")   # {file: {kernel_points, broken_points, invalid_points}}
for val_session, train_idx, val_idx in session_folds(meta):     # Leave-one-session-out
    ...
```

### 3.3 Erstblick-Prüfung (zuerst ausführen, 2 Minuten)

```python
from datasets import load_dataset
ds = load_dataset("SmartFarmingLab/corn1000", split="train")   # test: split="test"
print(ds)                                    # erwartet: 751 Zeilen (train); test: 85
import pandas as pd
m = ds.remove_columns(["image", "kernel_points", "broken_points", "invalid_points"]).to_pandas()
print(m.groupby("session").agg(n=("count", "size"), arr=("arrangement_id", "nunique"), art=("species", "first"),
                               cmin=("count", "min"), cmax=("count", "max")))
print((m["count"] == 1000).sum(), "Bilder mit count == 1000 (erwartet 0 in train)")
print(ds.features["kernel_points"])          # Listentyp und Punktformat bestätigen
```

Ergebnis in `notes/01_Datenset_Erstblick.md` eintragen; weicht es von Abschnitt 1 ab, dort korrigieren.

### 3.4 Weg B: Kaggle

Aus dem Handout (Kaggle: Telefonnummer verifizieren, sonst weder GPU noch Internet; Accelerator „GPU T4 ×2“, Internet „On“; ca. 30 h GPU pro Woche und Person; „Save Version“ nutzen; Mitglieder unter Share → Collaborators):

```python
from datasets import load_dataset
ds = load_dataset("SmartFarmingLab/corn1000", split="train")   # test: split="test"      # lädt mehrere GB, einige Minuten
```

Weitere Hinweise:
- Kein Account oder Token für den Download nötig.
- Den Datensatz nur einmal pro Session laden; für Wiederholungen den Export (Weg A) als Kaggle-Dataset hochladen oder `ds.save_to_disk("/kaggle/working/corn1000")` und Versionen sichern.
- `pip install datasets` ist in Kaggle-Notebooks meist schon vorhanden (nicht geprüft).
- Hinweis zur Lizenz: CC BY-NC 4.0, nichtkommerzielle Weitergabe auch außerhalb des Events mit Namensnennung, Lizenzlink und Änderungsangabe erlaubt.

---

## 4. Fallstricke (aus der Dataset-Card abgeleitet)

| Fallstrick | Wirkung | Gegenmaßnahme |
|---|---|---|
| **Leckage durch Wiederholungsfotos** | je Arrangement 2–22 Fotos, aufeinanderfolgende Arrangements teilen die meisten Körner → zufälliger Split ergibt viel zu gute Werte | immer nach `session` splitten (`session_folds`) |
| **Session = Art** | Sessions und Arten fallen zusammen; Session-Split heißt zugleich „unbekannte Art“ | bewusst so berichten (Abschnitt 5) |
| **EXIF-Drehung** | `PIL.Image.open` dreht nicht, `datasets` und `cv2.imread` schon; Punkte gelten im gedrehten Bild | `ImageOps.exif_transpose` bzw. unser Export (idempotent) |
| **Farbunterschiede durch DNG** | S03 und S05 (Galaxy S23) als DNG mit LibRaw entwickelt, Farben weichen von Handy-JPEG ab | Farb-Augmentierung; Farbmerkmale nicht über Sessions vergleichen |
| **Verschmutzung ist Absicht** | Spreu, Grannen, Bruch, Steine, Staub sind im Bild, zählen aber nicht | Klassen für Bruch/Fremdkörper, Punkt-Labels nutzen |
| **Punkte ≠ `count`** | Punktanzahl weicht um wenige Körner ab | Evaluation immer gegen `count` |
| **Hohe Auflösung** | bis ca. 800 Körner auf einem Foto, Körner nur wenige 10 px breit | Kacheln (Tiling) statt starkes Herunterskalieren |
| **S04: Tablet-Fotos** | Zuordnung bei Karten 0, 3, 8, 14, 15 von Hand korrigiert | bei Auffälligkeiten dort prüfen |
| **Nur 4 Kameras / 4 Sessions** | wenig Gerätevielfalt, ein Landwirt-iPad kommt nicht vor | Augmentierung, Grenzen im Pitch nennen |
| **Lizenz CC BY-NC 4.0** | nicht kommerziell | im Pitch erwähnen, Quelle nennen |

---

## 5. Auswertung: Regeln und Kennzahlen

Hauptkriterium der Technikjury ist die **Zählgenauigkeit** (Handout und `AGENTS.md`).

### Splits

| Zweck | Vorgehen |
|---|---|
| Entwicklung, schnelles Feedback | festes Hold-out, z. B. `holdout_sessions(meta, ["S04"])` (Weizen, Zielkultur) |
| Aussagekräftige Gesamtzahl | **Leave-one-session-out** (`session_folds`), alle vier Folds berichten |
| Offizieller Test | Split `test` (= Session `count_1000`, 85 Bilder, je 1000 Körner, Abschnitt 1) |
| Finale Modelle | auf allen Sessions trainieren, nur die Werte aus der Kreuzvalidierung berichten |

Beachten: Leave-one-session-out prüft die Übertragung auf eine **unbekannte Art** (z. B. Hafer, wenn nur Gerste, Weizen, Hartweizen im Training sind). Das ist strenger als der Praxisfall, in dem der Landwirt Gerste oder Weizen fotografiert, deren Arten im Training vorkommen. Beides berichten:
(1) Leave-one-session-out als Untergrenze,
(2) innerhalb einer Session nach `arrangement_id` gruppiert validieren (Zusatzsicht, kenntlich machen, dass es optimistischer ist).

### Kennzahlen

| Kennzahl | Bedeutung | Funktion |
|---|---|---|
| MAE (Körner) | mittlerer absoluter Fehler | `evaluate_counting.count_metrics` |
| MAPE (%) | relativer Fehler, 1 % Zählfehler = 1 % TKG-Fehler | dto. |
| Bias | systematische Über-/Unterzählung | dto. |
| max. Fehler | schlimmster Fall | dto. |
| ±1 % / ±2 % / ±5 % Trefferquote | Anteil Bilder innerhalb der Toleranz | dto. |
| Precision/Recall/F1 gegen Punkte | Lokalisierung (nur Bilder mit Punkt-Labels) | `evaluate_counting.point_scores` |
| Fehler je Session/Art/Kamera/Verschmutzung | wo versagt das Modell | `metrics.json` |
| Sekunden je Bild | Alltagstauglichkeit | `predictions.csv` |

Ergebnisse (eine Zeile je Modell) in `../docs/RESULTS.md` eintragen: `evaluate_counting.py` schreibt die Zeile als `results_row.md`.

---

## 6. Bildformat und Vorverarbeitung

```python
from PIL import Image, ImageOps
img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")   # nur nötig bei PIL; cv2.imread dreht selbst
```

- Alle Funktionen in `scripts/` lesen Bilder über `read_image` (OpenCV, EXIF-korrekt, Windows-Pfade mit Umlauten).
- **A4-Blatt als Maßstab:** `a4_sheet.rectify_a4` findet das helle Viereck, entzerrt auf 210 × 297 mm und liefert mm/px. Dadurch sind Kornfläche und Länge in Millimetern vergleichbar, auch über Kameras hinweg. Fehlt das Blatt, fällt die Auswertung auf das ganze Bild ohne Maßstab zurück (`sheet_found = False` in `predictions.csv`).
- Hinweise für KI-Modelle: bei hohen Zahlen Kacheln mit Überlappung (z. B. 640 px, 20 % Überlappung), Punkte in Kachel-Koordinaten umrechnen, doppelte Treffer in Überlappungszonen entfernen; Entzerrung auf das A4-Blatt vereinheitlicht Größe und Perspektive und verkleinert das Suchgebiet.

---

## 7. Modellierungsansätze passend zum Datensatz

Die Reihenfolge folgt dem Zeitbudget (Handout: Arbeitsphasen 15:45–18:00 und 19:00–22:00).

| Stufe | Ansatz | Labels | Aufwand | Erwartung |
|---|---|---|---|---|
| 1 | **Klassische Baseline** (A4-Entzerrung, Schwellwert, Watershed, Cluster-Korrektur), `evaluate_counting.py` | nur `count` zur Prüfung | gering, läuft sofort | gute Vergleichszahl; Schwächen bei Bruch, Spreu, Zwillingen, Berührung (nur an Attrappen geprüft) |
| 2 | **Korrektur per Regression**: Bildfeatures (Anzahl Objekte, Flächen-Summe, Blob-Schätzung, Verteilungen) → `count` mit Ridge/GBM, Session-Folds | `count` | gering | kann systematische Fehler der Baseline (Bias je Art) entfernen |
| 3 | **Punkt-überwachtes Zählnetz** (z. B. Dichtekarte aus Kornmitten mit Gauß-Kernen oder Punkt-Detektor, Backbone vortrainiert), Training in Kaggle | `kernel_points` (158 Bilder), `count` für alle | mittel bis hoch | höchste Genauigkeit zu erwarten, aber nur 158 Bilder mit Punkten → Augmentierung (Spiegeln, 90°-Drehung, Helligkeit), Kacheln |
| 4 | **Bruch-/Fremdkörper-Klasse** | `broken_points`, `invalid_points` | mittel | Qualitätsmerkmale und genauere Zählung (Bruch nicht mitzählen) |
| 5 | Vorgefertigte Zero-Shot-Segmentierer (SAM, Cellpose) | – | mittel, Installation prüfen | Alternative, wenn Training scheitert; langsam, nicht getestet |

Bekannt aus der Literatur zum Zählen mit Punktlabels (Dichtekarten-Regression, Punkt-Detektoren) ist, dass die Summe über die Dichtekarte die Kornzahl liefert und Fehler in dicht belegten Bereichen wachsen; konkrete Modelle und Versionen vor dem Einsatz prüfen, nichts davon habe ich hier ausgeführt.

Stufe 1 ist die einzige Methode, die hier lauffähig getestet ist (Attrappe). Auf den echten Bildern sind Staub, Spreu, Schatten und die Berührung von Körnern zu erwarten; Parameter nur anhand von Overlays und Session-Auswertung anpassen, nicht pro Bild.

### Zählung → TKG → Aussaatstärke (Anwendungsschicht)

```
Probenmasse [g] gewogen, Kornzahl (Modell)  →  TKG = Masse / Anzahl × 1000          (tkm_utils.tkm_from_sample)
Zielbestand ca. 200 Körner/m², Keimfähigkeit KF  →  kg/ha = 200 × TKG / 100 / KF     (tkm_utils.seed_rate_kg_ha)
Beispiel: TKG 45 g, KF 95 %  →  94,7 kg/ha
```

Eingaben der App für Landwirt:innen: Probenmasse (Waage), Keimfähigkeit (aus dem 100-Körner-Test), Zielbestand je m², Art. Keimfähigkeit lässt sich nicht aus dem Foto bestimmen (Ask-the-Farmer-Notiz in `../docs/CHALLENGE.md`).

---

## 8. Test der Werkzeuge ohne echte Daten (Attrappe)

Der Datensatz war aus der Entwicklungsumgebung nicht erreichbar. Deshalb gibt es eine **Attrappe im Exportformat** (perspektivisch verzerrte A4-Szene mit synthetischen Körnern, dunkler Tisch, bekannte Kornmitten):

```bash
python make_synthetic_data.py --out ../data/mock --corn1000-mock --n-images 6
python evaluate_counting.py --meta ../data/mock/metadata.csv --out ../outputs/count_mock
```

Getestet (Selbsttest `python selftest.py`):

| Prüfung | Ergebnis |
|---|---|
| A4-Blatt in Attrappen gefunden | 100 % (6 von 6) |
| Zählung auf Attrappen | 6 Bilder mit 264–407 Körnern: MAE 1,0 Korn, MAPE 0,25 % (nur Aussage über Plumbing, nicht über echte Fotos) |
| Punktabgleich (Hungarian) | Precision 0,997–1,0, Recall 0,95–0,99 auf den Bildern mit Punkten |
| Zeit | ca. 2 s je Bild bei 0,15 mm/px (Einzelkern, ohne GPU) |
| Index des Ordnerlayouts `data/corn1000/data/<split>/metadata.jsonl` und Lauf von `tausendkorn.eval` mit `classical_counter` an einem Nachbau | läuft durch (Zählung auf 2 Test-Attrappen: Abweichung 0) |
| Export mit nachgebautem Hugging-Face-Datensatz | Spalten, Punkte, EXIF-Drehung (Hochkant-Bild mit Orientierung 6) korrekt, Sessions-Folds ohne Überlappung |

Nicht getestet: der Download vom Hub, echte Fotos (Schatten, Spiegelungen, Papierwellen, Hintergrundmuster), DNG-Sessions, Laufzeit auf 836 Bildern (hochgerechnet ca. 25 Minuten ohne Parallelisierung; `--jobs 4` nutzt mehrere Kerne).

---

## 9. Checkliste nach dem Download

- [ ] Erstblick-Code (3.3) ausgeführt, Zahlen mit Abschnitt 1 verglichen, `docs/CHALLENGE.md` angepasst
- [ ] Download (Weg D) und `corn1000_data.py index`, danach `info` (oder Export, Weg A, mit `--limit 3` zum Probieren)
- [ ] 10 Bilder mit Punkten über die Bilder gelegt: Koordinaten passen zur Bildorientierung?
- [ ] `evaluate_counting.py --sessions S04 --limit 30` ausgeführt, Overlays angesehen
- [ ] Parameter (Kanal, `margin-mm`, `mm-per-px`) je Aufbau festgelegt und im Entscheidungslog notiert
- [ ] Baseline-Zeile in `docs/RESULTS.md`
- [ ] Entscheidung: reicht die klassische Baseline, oder Training in Kaggle (Stufe 3)?
