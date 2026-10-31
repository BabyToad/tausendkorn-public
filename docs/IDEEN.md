# Ideen-Backlog: womit wir uns abheben

Gesammelt am 27.10.2026 (17:57), Team 1. Dient als Fundgrube für spätere
Verbesserungen und für den Pitch. **Alle Ideen haben Status `Idee`, bis hier etwas
anderes steht.** Nichts davon ist gebaut oder gemessen.

Verwandt: [`ZWEITMEINUNG.md`](ZWEITMEINUNG.md) (Ampel), [`PROBLEMFAELLE.md`](PROBLEMFAELLE.md),
[`CHALLENGE.md`](CHALLENGE.md) (Bewertung und Ask-the-Farmer-Notizen).

## 0. Abgleich mit `docs/STATUS.md` (Stand 18:10)

`STATUS.md` ist maßgeblich für Kurs und Aufteilung. Dieser Backlog wurde vorher
geschrieben, drei Punkte sind deshalb überholt oder überschneiden sich:

- Der Kurs ist eine **VLM-Pipeline** (Gemini auf adaptiven Ausschnitten, `pipeline.py`).
  Die klassische Pipeline ist dort nur noch Schneidehilfe, nicht Zähler.
- Es gibt schon eine **Feld-App** (`app/`, Commit 30865fa: Foto, Zählen, Prüfen,
  Saatgutrechner, Verlauf). ID-01 bis ID-04 und ID-07 müssen **gegen die App abgeglichen**
  werden, bevor jemand etwas doppelt baut. `STATUS.md` nennt die Fotoanleitung (ID-07)
  und die Historie je Hänger/Sorte (ID-04) auch selbst als Ziele.
- Die **Pfanne** (ID-11) ist laut `STATUS.md` verworfen. Stattdessen läuft eine
  Foto-/Streustation in `hardware/station/`.

## 1. Leitplanken

- **Zählgenauigkeit ist Priorität 1** (Hauptkriterium der Technikjury). Keine Idee darf
  Zählzeit kosten. Zähler spätestens um **20:00 einfrieren** ([`PROTOCOL.md`](PROTOCOL.md)).
- Abheben können wir uns bei **Vertrauen, Nutzen am Feld und Ehrlichkeit**, nicht mit
  mehr Funktionen als alle anderen. Zielgruppe: Landwirt:innen mit iPad, deutsch, wenige Schritte.
- Wir behaupten keine Neuheit: Zähl-Apps gibt es schon
  ([`EXISTING_SOLUTIONS.md`](EXISTING_SOLUTIONS.md)). Unser Angebot: **messbarer,
  prüfbarer Weg vom Foto zur Aussaatentscheidung**, mit Warnung bei Unsicherheit.
  Nicht als „ISO-zertifiziert“ bewerben (ISO 520 schließt Saatgut zum Säen aus).

## 2. Übersicht

| ID | Idee | Kategorie | Aufwand | Wirkung | Status |
|---|---|---|---|---|---|
| ID-01 | Abdrehprobe-Sollwert | App | 20–30 Min. | hoch | gebaut (PR #15, ca0d2a5) |
| ID-02 | Spanne statt Einzelzahl (± Körner, kg/ha-Bereich) | App | 20–30 Min. | hoch | gebaut (PR #14, afb6065; Band vorläufig ±1 %) |
| ID-03 | Mehrfachfoto mit Mittelwert und Streuung | App | 30–40 Min. | hoch | gebaut (PR #17, f89c9f5; Partie-TKG = 1000·ΣGewicht/ΣKörner, keine Streuungsschwelle) |
| ID-04 | Verlauf und Protokoll je Hänger und Sorte (Export) | App | 30–40 Min. | mittel–hoch | gebaut (30865fa, b9a2d5f; CSV-Export, kein PDF) |
| ID-05 | Qualitätskennzahlen (Bruch, Fremd, Uniformität) | Modell+App | 40–60 Min. | mittel | Idee, nach Zählerfreeze |
| ID-06 | Korrekturmodus im Overlay | App | 60+ Min. | hoch | gebaut (b9a2d5f; Tippen, Rückgängig, Protokoll) |
| ID-07 | Aufnahme-Assistent (Checkliste, Schablone, Sofort-Hinweis) | App | 30–45 Min. | mittel | gebaut ohne Schablone (Checkliste 30865fa, Sofort-Hinweis PR #16, 949f2c7) |
| ID-08 | Stichprobengröße: reichen weniger Körner? | Statistik | offen | mittel | Hypothese, erst prüfen |
| ID-09 | Folie „Wo wir scheitern“ (ehrliche Fehleranalyse) | Pitch | 0 Min. Entwicklung | hoch | Idee |
| ID-10 | Stoppuhr-Demo live (Handzählung gegen App) | Pitch | 0 Min. Entwicklung | hoch | Idee |
| ID-11 | Requisite `hardware/pfanne` | Pitch | offen | niedrig | verworfen laut `STATUS.md` |
| ID-12 | API, Hof-Integration und Agenten-Zugang (MCP, llms.txt) | App | Folie 15 Min., MCP-Demo 45–60 Min. | mittel (Pitch), hoch (später) | Entwurf (`docs/app/API.md`) |

Empfohlenes Paket bis 22:00: **ID-01 bis ID-04** (ca. 1,5 Std., braucht keine Modellarbeit,
passt zur Ampel). Danach ID-06, falls Zeit bleibt.

## 3. Details

### ID-01 Abdrehprobe-Sollwert

- **Was:** Neben der Aussaatmenge (kg/ha) zeigt die App die Sollmenge für die
  Abdrehprobe: `Sollmenge [kg] = kg/ha × Fläche der Abdrehprobe [m²] / 10 000`.
- **Warum:** Die Abdrehprobe kam im „Ask the Farmer“ vor ([`CHALLENGE.md`](CHALLENGE.md)).
  Das ist der nächste Handgriff nach der Zählung.
- **Eingabe:** Fläche der Abdrehprobe in m². Wird sie je nach Drillmaschine anders
  definiert, ist die Definition anhand der jeweiligen Maschinenanleitung zu prüfen.
- **Abhängigkeit:** `seed_rate_kg_ha` aus `wissensbank/scripts/tkm_utils.py`.
- **Stand Feld-App (18:10):** `app/static/app.js` rechnet kg/ha und Körner/m² (inkl. Keimfähigkeit,
  Feldaufgang), eine Sollmenge für die Abdrehprobe habe ich dort nicht gefunden.
- **Abnahme:** Rechenbeispiel stimmt von Hand nach; eine Plausibilitätsprüfung bei
  unsinnigen Eingaben (z. B. Keimfähigkeit > 100 %).

### ID-02 Spanne statt Einzelzahl

- **Was:** „1 000 ± 4 Körner → 94,7 kg/ha (94,0–95,4)“. Der Zählfehler wirkt linear auf
  TKG und Aussaatmenge (1 % Zählfehler = 1 % TKG-Fehler, Dataset-Card).
- **Quelle der Unsicherheit:** Zunächst die relative Abweichung zwischen Hauptzähler
  und Prüfer ([`ZWEITMEINUNG.md`](ZWEITMEINUNG.md)), später die gemessene Streuung auf
  `dev`. Bis es gemessen ist, nur als „Spanne aus Zweitmeinung“ kennzeichnen.
- **Abnahme:** Bei Ampel grün enge, bei rot weite oder keine Spanne.

### ID-03 Mehrfachfoto mit Mittelwert und Streuung

- **Was:** Dieselbe Probe nach dem Neulegen ein zweites (und drittes) Mal fotografieren.
  Mittelwert wird angezeigt, die Streuung der Zählungen als Maß der Messunsicherheit.
- **Warum:** Die Probe hat immer dieselbe Kornzahl, jede Abweichung ist Zählfehler. Das
  braucht kein neues Modell.
- **Hinweis:** Wirkt nur, wenn der Landwirt die Körner wirklich neu auslegt. Im Text
  klar sagen.
- **Abnahme:** Mit drei Fotos derselben Karte aus dem Datensatz (mehrere Aufnahmen je
  Arrangement existieren) prüfen, dass die Streuung plausibel ist.

### ID-04 Verlauf und Protokoll je Hänger und Sorte

- **Was:** Liste der Messungen mit Datum, Sorte, Hänger, Kornzahl, TKG, kg/ha, Ampel.
  Export als CSV oder PDF.
- **Warum:** Laut „Ask the Farmer“ wird für jeden Hänger und jede Sorte neu gezählt
  (Saatzeitraum ca. 2 Wochen). Ein Protokoll ersetzt Zettel.
- **Speicherort:** Lokal im Gerät. Internet auf dem Hof ist laut Notizen offen, aber
  Daten sollen nicht ohne Grund wandern. Datenschutz im Pitch erwähnen.

### ID-05 Qualitätskennzahlen

- **Was:** Anteil Bruch und Fremdbesatz in Prozent, Verteilung der Kornflächen
  (Uniformität), optional Schrumpfkörner. Aus dem Handout: Vollkornanteil > 90 %,
  Fremdbesatz, Schrumpfkörner.
- **Voraussetzung:** Detektor mit getrennten Klassen Korn/Bruch/Fremd, Punkt-Labels
  `broken_points` und `invalid_points` im Datensatz.
- **Achtung:** Bruch und Fremd werden laut ISO 520 nie gezählt. Anzeige getrennt von der
  Kornzahl, keine Händler-Aussagen („geeignet für …“) ohne Rücksprache mit der Fachjury.
- **Status:** Erst nach Zählerfreeze (nachrangig gegenüber der Zählgenauigkeit).

### ID-06 Korrekturmodus im Overlay

- **Was:** Landwirt tippt auf ein falsch erkanntes oder fehlendes Korn, die Zahl passt
  sich an. Er behält die Kontrolle, das schafft Vertrauen.
- **Umsetzung:** In Streamlit mit einem Klick-Canvas oder vereinfacht als „Bereich
  markieren“. Nur angehen, wenn Zähler und Ampel fertig sind.
- **Folge:** Korrekturen sollten als Evaluationsdaten loggbar sein (Fehlerfälle für
  [`PROBLEMFAELLE.md`](PROBLEMFAELLE.md)).

### ID-07 Aufnahme-Assistent

- **Was:** Vor dem Foto Checkliste oder Schablone („ganzes Blatt, gerade von oben,
  Körner nicht berühren, keine Schatten“). Nach dem Foto sofort die Hinweise der Ampel.
- **Warum:** Verhindert die häufigsten schlechten Fotos (Signale S05–S07 in
  `agreement.py`), spart dem Zähler Fehler.
- **Hinweis:** Live-Vorschau mit Echtzeit-Erkennung ist in Streamlit schwer, deshalb nur
  Checkliste und Rückmeldung nach der Aufnahme.

### ID-08 Stichprobengröße: reichen weniger Körner?

- **Hypothese (nicht geprüft):** Aus der Streuung der Kornflächen im Foto lässt sich die
  Streuung der Kornmasse grob abschätzen, damit eine kleinere Probe als 1000 Körner
  genügt. Wäre ein Zeitgewinn für den Landwirt.
- **Risiko:** Fläche ist nur ein Proxy für Masse. Nicht versprechen, bevor es an echten
  Daten (falls Gewichte vorliegen) geprüft ist. Verwandt: Stichprobenrechnung in
  `wissensbank/scripts/tkm_utils.py`.
- **Status:** Erst prüfen, dann entscheiden. Nicht in den Pitch ohne Messung.

### ID-09 Folie „Wo wir scheitern“

- **Was:** Ehrliche Fehleranalyse: Fehler je Art und je Ampelstufe, ein echtes Fehlerbild,
  bekannte Grenzen (PF-01, PF-03).
- **Warum:** Technik- und Fachjury schätzen Ehrlichkeit. Viele Teams zeigen nur den besten Wert.
- **Quelle:** Tabelle je Ampelstufe aus [`ZWEITMEINUNG.md`](ZWEITMEINUNG.md), Abschnitt 5, und
  [`RESULTS.md`](RESULTS.md). Zahlen nur nach Protokoll eintragen.

### ID-10 Stoppuhr-Demo live

- **Was:** Landwirt oder Freiwilliger zählt eine Probe von Hand, parallel läuft die App.
  Die Uhr ist sichtbar.
- **Warum:** Das Publikum hat eher niedrigen Wissensstand. Ein sichtbarer Zeitvergleich
  wirkt sofort. Fallback: aufgenommenes Video, falls die Demo ausfällt.

### ID-12 API, Hof-Integration und Agenten-Zugang

- **Was:** Eine REST-API (`docs/app/openapi.yaml`) für App, Hofsoftware und Agenten;
  ein dünner MCP-Server darüber; `llms.txt`/`llms-full.txt` nach Exocortex-Konvention.
  Export Richtung Drillmaschine: heute CSV + Ergebniskarte zum Eintippen, als Nächstes
  ISO-XML (DDI 6, mg/m²) für eine echte Terminal/Drillen-Kombination, später agrirouter.
- **Warum:** Fortgeschrittene Betriebe arbeiten mit NEXT Farming, HELM, Deere/CLAAS und
  Terminals; eine Insel-App wird dort nicht benutzt. Agenten können „Wie viel kg/ha für
  Hänger 3?“ beantworten, wenn jede Zahl Einheit, Unsicherheit und Rechenweg hat.
- **Leitplanke:** Zählen kostet Geld → eigener Scope, Tagesbudget, Zwei-Schritt-Bestätigung.
  „Integration“ erst sagen, wenn Schreiben **und** Ausführen auf der Maschine gezeigt sind.
- **Abhängigkeit:** tk-app nach PR #13–#15; Leons Terminal/Drille für den ISO-XML-Test.
- **Abnahme Pitch:** Folie „Passt in Ihren Betrieb“ mit ehrlichem Status; optional
  MCP-Demo, die nur liest (keine Zählung live).

### ID-11 Requisite `hardware/pfanne` (verworfen)

- **Was war gedacht:** STL-Dateien der Pfanne als Hand-Requisite im Pitch.
- **Warum verworfen:** `STATUS.md` führt die Tausendkorn-Pfanne (genau 1000 Körner
  auswählen) als verworfen, weil sie die Zufallsstichprobe verletzt. Im Pitch nicht zeigen.
- **Stattdessen:** Foto-/Streustation, Stand in `hardware/station/` und `STATUS.md`.

## 4. Offene Fragen an die Fachjury / den Landwirt

- Wie ist die Abdrehprobe bei seiner Drillmaschine definiert (Fläche, Umdrehungen)? (ID-01)
- Welche Abweichung der Aussaatmenge ist praktisch egal (z. B. 1 %, 2 %)? (ID-02, Grün-Schwelle)
- Welche Begriffe versteht er sofort („Bruch“, „Fremdbesatz“, „Ampel“)? (ID-05, PF-08)
- Welche Daten dürfen das Gerät verlassen? (ID-04)

## 5. Ideen verworfen oder zurückgestellt

| Idee | Grund |
|---|---|
| Vorgabe „genau 1000 im Test“ als Signal nutzen | nicht übertragbar, siehe PF-04 |
| Neuheit gegenüber vorhandenen Zähl-Apps behaupten | stimmt nicht, siehe `EXISTING_SOLUTIONS.md` |
| Live-Erkennung in der Kamera-Vorschau | in Streamlit zu aufwendig, ID-07 als Checkliste |
| Pfanne als Requisite (ID-11) | `STATUS.md`: verletzt die Zufallsstichprobe |

## 6. Neue Idee eintragen

1. Nächste freie ID vergeben (`ID-12`, …) und Zeile in Abschnitt 2 ergänzen.
2. Abschnitt 3 mit **Was / Warum / Abhängigkeit / Abnahme** (und Risiko, wenn bekannt).
3. Status ehrlich pflegen: `Idee` → `in Arbeit (Wer)` → `gebaut (Commit)` → `gemessen`.
   Hypothesen als solche kennzeichnen, nichts ohne Messung im Pitch behaupten.
4. Bei größeren Ideen zusätzlich ein GitHub-Issue anlegen und hier verlinken.
