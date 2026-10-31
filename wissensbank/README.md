# Wissensbank

Fachwissen, Methodik, Code und Fahrplan für den Tausendkorn-Hackathon. Ergänzt den Team-Code
im Repo (`src/`, `app/`, `notebooks/`, `pitch/`) und die Challenge-Beschreibung in
[`../docs/CHALLENGE.md`](../docs/CHALLENGE.md). Dort stehen die verbindlichen Anforderungen,
hier das Hintergrundwissen und ein getesteter Werkzeugkasten.

## Welche Datei wofür?

| Ich will … | Datei |
|---|---|
| verstehen, was TKM/TKG ist, Formeln, Richtwerte je Kultur, Qualitätsmerkmale, Nutzenargumente | [01_Domain_Wissen.md](01_Domain_Wissen.md) |
| wissen, wie man Körner per Bildverarbeitung zählt und vermisst, Fehler diagnostiziert, Ergebnisse validiert | [02_Computer_Vision_Pipeline.md](02_Computer_Vision_Pipeline.md) |
| Code, Parameter und Befehle nachschlagen (alle Skripte vollständig abgedruckt) | [03_Tech_Stack_Code.md](03_Tech_Stack_Code.md) |
| Fahrplan (nach Handout), Meilensteine, Rollen, Fragenkatalog, Plan B, Pitch (5 min, 5 Folien) | [04_Hackathon_Timeline_Pitch.md](04_Hackathon_Timeline_Pitch.md) |
| den Datensatz `corn1000` verstehen, laden, exportieren, sauber splitten und auswerten | [05_Datensatz_corn1000.md](05_Datensatz_corn1000.md) |
| Notizen festhalten (Antworten, Datenset-Erstblick, Entscheidungen) | notes/ (nicht im öffentlichen Snapshot enthalten) |
| lauffähige Skripte | [scripts/](scripts/) |

## Einordnung zur tatsächlichen Challenge

Die Wissensbank entstand vor Beginn des Hackathons und ist bewusst allgemein gehalten. Die
Challenge (siehe `docs/CHALLENGE.md`) konkretisiert:

- **Aufgabe:** Kornzahl aus einem A4-Foto, Hauptkriterium ist die Zählgenauigkeit
  (Test-Split `count_1000`, genau 1000 Körner je Bild). Das TKG selbst folgt aus Masse ÷ Anzahl × 1000.
- **Daten:** `SmartFarmingLab/corn1000` mit Punkt-Labels für einen Teil der Bilder. Es gibt
  also Labels für ein überwachtes Zählmodell, nicht nur für die klassische Pipeline.
  **Stand der Dataset-Card (26.10.): 836 Bilder, `train` 751 Bilder (bis 800 Körner), `test` = `count_1000` mit 85 Bildern à genau 1000 Körnern, fünf Arten.** Test ist dichter als Training und enthält Roggen: siehe `05`, Abschnitt 1.
- **Validierung:** immer nach `session` splitten (steht auch in `AGENTS.md`).
- **Saatstärke:** `kg/ha = Körner/m² × TKG / 100 / Keimfähigkeit` (Beispiel 200 Körner/m², 45 g, 95 %
  → 94,7 kg/ha). Entspricht `seed_rate_kg_ha` in `scripts/tkm_utils.py`.
- Viele Fragen aus dem Fragenkatalog in `04` („Ask the Farmer“) sind durch die Challenge-Unterlagen bereits beantwortet.

Was das für die Nutzung heißt:

| Baustein | Nutzen für die Challenge |
|---|---|
| Klassische Pipeline (`grain_segmentation.py`) | schnelle Baseline und Vergleichswert, Cluster-/Watershed-Logik, Features für Bruchkorn und Größenverteilung. **Nur an synthetischen Bildern getestet**, auf `corn1000` noch nicht |
| `tkm_utils.py` | Saatstärke, TKG, Feuchtekorrektur, Stichprobenrechnung, Plausibilitätsprüfung |
| `merge_labels.py`, `eda_tabular.py`, `train_model.py` | Tabellen und Label-Handling, falls Zusatzdaten (Gewichte, Keimrate) vorliegen |
| `corn1000_data.py`, `a4_sheet.py`, `evaluate_counting.py`, `classical_counter.py` | Index/Export des Datensatzes, A4-Entzerrung, Zählauswertung, Adapter für `tausendkorn.eval` (Baseline, MAE/MAPE/Bias, Punkt-Treffer). **Gegen Attrappen getestet, echte Fotos noch nicht** |
| `app_streamlit.py` | Vorlage für eine einfache Demo-Oberfläche; die Zielgruppe nutzt ein iPad, die finale UI folgt `app/` |
| `04` Pitch-Abschnitt | Gliederung als Ausgangspunkt; Vorgabe ist 5 Folien (PPTX), 5 Minuten |

## Schnellstart

Alle Befehle im Ordner `wissensbank/`. Die Skripte brauchen Python ≥ 3.11 und sind
unabhängig vom `uv`-Projekt der Wurzel (eigene Abhängigkeiten in `requirements.txt`).

```bash
python -m venv .venv
.venv/Scripts/Activate.ps1          # Windows PowerShell; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt     # oder: uv pip install -r requirements.txt
cd scripts
python selftest.py                  # ca. 20-30 s, alle Prüfungen müssen OK sein
```

Synthetische Testbilder erzeugen (nicht im Repo, da groß und reproduzierbar):

```bash
python make_synthetic_data.py --out ../data/synthetic --n-images 8 --seed 42
python make_synthetic_data.py --out ../data/mock --corn1000-mock --n-images 6   # A4-Szenen im Datensatzformat
streamlit run app_streamlit.py      # Häkchen "Synthetisches Beispielbild verwenden"
```

## Befehlsrezepte nach Datenlage

| Datenlage | Befehl (im Ordner `scripts/`) |
|---|---|
| **corn1000** (A4-Fotos, Download nach `data/corn1000`) | `python corn1000_data.py index --src ../../data/corn1000 --out ../../data/corn1000_index` danach `python evaluate_counting.py --meta ../../data/corn1000_index/metadata.csv --out ../outputs/count_baseline --jobs 4` (oder Team-Eval: `PYTHONPATH=wissensbank/scripts uv run python -m tausendkorn.eval classical_counter:count --split test --name classical`) |
| Bilder (Referenzmünze im Bild) | `python grain_segmentation.py --input ../data/raw --out ../outputs/seg --ref-diameter-mm 25.75` |
| Bilder (mm/px bekannt) | `python grain_segmentation.py --input ../data/raw --out ../outputs/seg --mm-per-px 0.1` |
| Bilder und Label-Tabelle | zusätzlich `python merge_labels.py --features ../outputs/seg/summary.csv --labels <labels.xlsx> --labels-key <Bildspalte> --out ../outputs/train_table.csv` |
| Regression auf TKG | `python train_model.py --csv ../outputs/train_table.csv --target <TKG-Spalte> --drop image` |
| Reine Tabelle | `python eda_tabular.py --csv <datei> --target <ziel>`, danach `train_model.py` |

Lokale Ordner `data/` und `outputs/` sind nicht im Repo (siehe `.gitignore`). Der Datensatz
gehört wie in der Haupt-README beschrieben nach `data/corn1000` im Repo-Stamm.

## Teststatus

- Selbsttest besteht in einer frischen Umgebung aus `requirements.txt` (Python 3.13).
- Validiert nur an **synthetischen** Bildern: Kornzahl-Fehler −2 bis +1 Korn je Bild, TKG nach
  Wiegen + Zählen im Mittel 0,5 % Fehler. Echte Fotos (Schatten, Spiegelungen, Staub) fallen
  schlechter aus; Parameter müssen dort neu justiert werden. Details in `02`, Abschnitt 6.
- Der Datensatz-Download (Hugging Face) war aus der Entwicklungsumgebung nicht erreichbar und ist **nicht getestet**; Export und Auswertung laufen an einer Attrappe im selben Format (`05`, Abschnitt 8).
- Nicht enthalten und ungetestet: Deep-Learning-Zählung (YOLO, Cellpose, SAM, Dichtekarten-Netze).
- Richtwerte stammen aus zwei gelesenen Quellen (siehe `01`, Quellen); alles Weitere ist als
  „vor Ort verifizieren“ markiert.
