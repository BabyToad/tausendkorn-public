# Abgabe Team Goldpfanne: Tausendkorn

Tausendkorn-Hackathon, Smart Farming Lab, Universität Leipzig, 27.10.2026.
Team **Goldpfanne**: Leon Böhlau, Jonas Heinke.
Code: vollständig im ZIP `goldpfanne_tausendkorn.zip` (Stand `main` zur Abgabe); das
GitHub-Repo bleibt privat. Live ansehen (Demo, Ergebnisse, Pitch):
<https://goldpfanne-tausendkorn.pages.dev/>.

## Was die Lösung macht

Ein Foto einer zufällig gegriffenen Handvoll Körner auf A4 (iPad oder Handy) →
**jedes Korn wird markiert** → die App zeigt die Zahl mit Fehlerband und die Stellen,
an denen das Modell unsicher war. Wer will, prüft diese Stellen und korrigiert per
Tippen, wer nicht will, überspringt mit Fehlerband. Mit dem gewogenen Probengewicht
und der Keimfähigkeit rechnet die App **TKG** und die **Aussaatmenge in kg/ha** für die
Drillmaschine, zeigt die Prüfung der Einstellung per **Abdrehprobe** und speichert
alles im Verlauf (CSV-Export). Bedienung deutsch, wenige Schritte.
So sieht die App aus: `docs/app/screens/` (9 Screenshots mit Erklärung).

## Aufbau in einfachen Worten

1. **Adaptive Kacheln** (`src/tausendkorn/adaptive.py`): Das Blatt wird nach
   Korndichte so zerschnitten, dass jeder Ausschnitt höchstens ~15 Körner enthält,
   mit einer Kornlänge Rand. Leere Bereiche fallen weg.
2. **Punkte setzen mit Gemini 4 Argon** (`pipeline.py`): Das Vision-Modell setzt auf
   jedem Ausschnitt einen Punkt pro Korn und meldet seine Konfidenz. Gezählt wird nach
   ISO 520 (nur ganze Körner; Bruch, Spreu, Fremdbesatz nicht). Gewogen wird dagegen die
   ganze Probe mit Besatz: Das ergibt das Gewicht der Partie pro 1000 ganze Körner, also das,
   was die Drillmaschine ausbringt (bewusst kein reines Labor-TKG, das etwas niedriger liegt).
3. **Abgleich**: Punkte aus überlappenden Rändern werden zusammengeführt, doppelte
   Koordinaten (< 0,05 Kornlängen) entfernt.
4. **Prüfdurchgang**: Ausschnitte mit Konfidenz < 0,9 sieht das Modell mit seinen
   nummerierten Markierungen noch einmal, ergänzt/entfernt und schreibt einen Hinweis.
5. **Zweiter Zähler YOLO11s** (`src/tausendkorn/gpu/`), auf dem `train`-Split trainiert. YOLO11s wurde separat offline verglichen und ist nicht in die App integriert. Auf denselben 30 Holdout-/6 Testbildern: MAE 3,2/12,5; auf allen 85 Testbildern: MAE 25,4. Laufzeit auf einer RTX 3070 typischerweise 0,4 s pro Bild. Die Gewichte werden wegen offener Lizenzfragen nicht verteilt (siehe models/README.md). Hashes und Messwerte bleiben in docs/RESULTS.md. Das nach der Abgabe trainierte Blur-Modell wurde nur auf dev gemessen; diese Ergebnisse gehören nicht zum eingefrorenen Benchmark. (`docs/ZWEITMEINUNG.md`)
6. **Feld-App** (`app/`): läuft auf dem Laptop, iPad im selben WLAN koppelt per QR-Code.
   Vorab-Prüfung des Fotos (Blatt, Schärfe, Häufchen) vor dem bezahlten Zählen.
   **Mock-Modus** zeigt ein gespeichertes Ergebnis ohne Kosten.

## Messergebnisse (ehrlich eingeordnet)

Alle Bilder mit Overlays (grün Treffer, rot Fehlalarm, gelb übersehen) zum Durchklicken:
`results/index.html` im Browser öffnen, Dateien erklärt in `results/README.md`.
Messregeln: `docs/PROTOCOL.md`, alle Zahlen: `docs/RESULTS.md`. Methoden und Schwellen
wurden nur auf `dev` gewählt. Die finale Pipeline v1.0.2 wurde einmal auf 30 Holdout- und 6 Testbildern gemessen. Ein früherer Holdout-Lauf mit 11 Bildern wurde nach Fehlerkorrekturen verworfen; der Holdout ist daher nicht vollständig unberührt. Die Splits teilen Sessions und liefern Within-Session-Ergebnisse. Holdout-Commit `d2ced75`, Test-Commit `44a553a`, gleicher Pipeline-Fingerprint `422967946cbd`. YOLO: Commit `d70b248`.

| Satz | Bilder | Argon-Pipeline | YOLO11s auf denselben Bildern |
|---|---|---|---|
| Holdout, gleiche Aufnahmetage wie Training (170–482 Körner) | 30 von 40 (Hafer, Gerste, Weizen) | **MAE 5,9** (1,85 %), Bias +2,5, max. 14 | MAE 3,2 |
| Test `count_1000`, anderer Tag, Roggen neu (1000 Körner) | 6 von 85, alle 5 Arten | **MAE 15,8** (1,58 %), Bias −5,2, max. 58 | MAE 12,5 |

- Hartweizen fehlt im Holdout (Budget-Stopp nach 30 Bildern), der Test ist eine
  Stichprobe von 6 Bildern. Die Argon-Läufe kosteten real 9,43 $ bzw. 3,94 $.
- YOLO über alle Bilder: Holdout (40) MAE 4,2, Test (85) **MAE 25,4, Bias −20**: innerhalb
  der bekannten Aufnahmetage besser, am neuen Tag (gebeiztes Saatgut, schräge Fotos,
  dichter) deutlich schlechter. Die YOLO-Werte auf denselben 30 bzw. 6 Bildern sind aus
  den Lauf-Dateien nachgerechnet.
- Fehler sind je Art gerichtet (Gerste zu hoch, Weizen zu niedrig).
- **Hartweizen-Testserie (`count_1000-001`):** Die Hartweizen-Abweichung ist ungeklärt: Argon zählt 942, YOLO auf demselben Foto 948; über 17 Fotos zählt YOLO 911–976. Gemeinsame Unterzählung verdeckter Körner und eine Abweichung der Probe vom Label sind nicht ausgeschlossen. Ein fehlender 50er-Becher ist nur eine Hypothese. Gewertet wird unverändert gegen 1000; Test-MAE 15,8 bei n=6. Wir bitten die Veranstalter um Prüfung (`docs/befund/DURUM_COUNT_1000.md`).
- **Abweichung vom Protokoll:** Unsere Splits trennen nach Aufnahme-Schritten, nicht
  nach `session` wie gefordert. Holdout ist daher ein Within-Session-Ergebnis; der Test
  vom anderen Tag ist unser unabhängigster Check.
- **Live-Tests aus der App:** Zwei erfolgreiche Einzeltests, keine Messreihe: PC-Upload 488 statt 493 Körner, 47 s, 0,39 US-Dollar; eigenes iPad-Foto über Hotspot 233 Marken, 54 s, 0,36 US-Dollar; dabei per Sichtprüfung zwei Doppelmarkierungen, eine unabhängige Sollzählung fehlt. PC-Foto: Dev-Bild S04-014. Screenshots: `docs/app/screens/echt/`.
- **Kosten und Zeit:** Gemessene API-Kosten pro Foto: Holdout 0,12–0,56 US-Dollar, Test 0,61–0,79 US-Dollar; Mittelwerte 0,31 bzw. 0,66 US-Dollar. Dauer 1–2 Minuten pro Probe (Argon-Einführungspreis
  bis 30.11.2026).

## Starten

Voraussetzung: [uv](https://docs.astral.sh/uv/), Python 3.12 wird automatisch geholt.

```bash
uv sync
uv run python -m app --mock
```

Dann `http://localhost:8000` öffnen (iPad: QR-Code auf der Laptop-Seite). Der Mock-Modus
kostet nichts und braucht keinen Schlüssel; ohne Datensatz liegen die gespeicherten
Markierungen auf dem selbst hochgeladenen Foto, mit Datensatz auf dem passenden.

Für echte Zählungen:

```bash
uvx --from huggingface_hub hf download SmartFarmingLab/corn1000 --repo-type dataset --local-dir data/corn1000
uvx keyring set tokenkit GEMINI_API_KEY
uv run python -m tausendkorn.pipeline foto.jpg
uv run python -m app
```

Der Gemini-Schlüssel (Projekt mit Billing) liegt im Schlüsselbund des Betriebssystems,
nie in Dateien.

## Grenzen und nächste Schritte

- Übersehene Körner in dichten Gruppen meldet das Modell oft nicht als unsicher; die
  Prüfschleife greift dort nicht. Fotoanleitung und Häufchen-Warnung mildern das. Die
  Hartweizen-Abweichung im Test ist ungeklärt (siehe oben).
- Bruchkorn und Fremdbesatz als eigene Klassen, Größenverteilung in mm, Offline-Zähler
  (YOLO) als Rückfall, Batch-API für günstigere Auswertung.
- Ideen: [`docs/IDEEN.md`](docs/IDEEN.md) · App-Fahrplan:
  [`docs/app/ROADMAP.md`](docs/app/ROADMAP.md) · Schnittstelle:
  [`docs/app/API.md`](docs/app/API.md).

**Lizenz Daten:** Fotos und Labels aus
[`SmartFarmingLab/corn1000`](https://huggingface.co/datasets/SmartFarmingLab/corn1000),
CC BY-NC 4.0 (nicht kommerziell, Namensnennung). Der Datensatz ist nicht im ZIP.

## Checkliste Abgabe (Jonas, bis 22:00)

- [ ] `dist/goldpfanne_tausendkorn.zip` in den Drive-Ordner
  <https://drive.google.com/drive/folders/1Kl2eHm6Jg6zKYrfFAJ2SEF7P4nUPdxXn> hochladen
- [ ] `ABGABE.md` dazulegen (oder als PDF `dist/ABGABE.pdf`)
- [ ] Teamnamen **Goldpfanne** den Veranstaltern mitteilen
- [ ] Optional: Nachfrage zur Hartweizen-Serie aus `docs/befund/DURUM_COUNT_1000.md`
  schicken
