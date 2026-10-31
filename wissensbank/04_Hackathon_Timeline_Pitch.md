# 04 – Hackathon: Fahrplan, Aufgabenverteilung, Fragenkatalog, Pitch

**Ort:** Smart Farming Lab, Universität Leipzig, WiWi-Fakultät, Raum IZ03 (Zwischengeschoss, rechts am Kickertisch vorbei), Grimmaische Straße 12, 04109 Leipzig.
**Heute:** Di 27.10.2026 · **Abgabe:** 22:00 Uhr · **Pitch & Siegerehrung:** Mi 28.10.2026, Albertina, Kernzeit 13:30–14:45 Uhr.

---

## 1. Vorbereitung vor 14:00 Uhr

| ✔ | Aufgabe | Details |
|---|---|---|
| ☐ | Python-Umgebung steht | `py -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt` (siehe `03`) |
| ☐ | Selbsttests laufen | `python scripts/tkm_utils.py`, `python scripts/make_synthetic_data.py`, `python scripts/grain_segmentation.py --input data/synthetic/images --out outputs/seg --ref-diameter-mm 25.75` |
| ☐ | Streamlit startet | `streamlit run scripts/app_streamlit.py` (Beispielbild-Häkchen) |
| ☐ | Git initialisiert | `git init`, erster Commit mit Struktur |
| ☐ | Hardware | Ladegerät, Mehrfachsteckdose, Maus, ggf. Hotspot/Tethering als Netz-Backup |
| ☐ | Kaggle | Konto angelegt, **Telefonnummer verifiziert** (sonst keine GPU, kein Internet), Notebook mit GPU T4 ×2 und Internet „On“, Mitglieder unter Share → Collaborators |
| ☐ | Datensatz | `pip install -r requirements.txt` (enthält `datasets`); Datensatz noch nicht nötig, siehe `05` |
| ☐ | Optional: eigene Messmittel | Lineal, Münze (2 €), Feinwaage (0,01 g), Smartphone-Stativ, einfarbiger Karton als Hintergrund |
| ☐ | Notizen vorbereitet | Fragen an den Landwirt (Abschnitt 5) ausgedruckt oder offen |
| ☐ | Team-Rollen festgelegt | Abschnitt 4 |

---

## 2. Fahrplan Dienstag, 27.10.2026

Offizieller Ablauf laut Handout (Team 1, PC Pool 3): 14:00 Start · 14:30 Challenge und Teambekanntgabe · 14:45 „Ask the Farmer“ · 15:00 Technikinput (Raum- und Materialorga, Technikübergabe, Modelle) · 15:45–18:00 Arbeitszeit I · ab 18:00 Pizzapause · 19:00–22:00 Arbeitszeit II · **22:00 Abgabe** (Google Drive). Getränke und Snacks gibt es den ganzen Tag.

| Uhrzeit | Block | Ziel / Ergebnis | Wer |
|---|---|---|---|
| **14:00–14:30** | Start, Vorstellung Smart Farming Lab, Vorstellungsrunde | Rollen im Team klären (Abschnitt 4), Umgebung steht | alle |
| **14:30–14:45** | Challenge-Vorstellung und Teambekanntgabe | Aufgabenstellung, Bewertung, Datensatz mitschreiben (bekannt: siehe `../docs/CHALLENGE.md`, Abweichungen in `05`, Abschnitt 1) | alle zuhören, eine Person protokolliert in `notes/` |
| **14:45–15:00** | „Ask the Farmer“ | Offene Fragen (Abschnitt 5, P1 zuerst), Antworten in `notes/` | R4 fragt, R1 protokolliert |
| **15:00–15:45** | Technikinput und Technikübergabe | Hinweise zu Modellen/Hardware; **Daten laden und exportieren** (`05`, Abschnitt 3), Erstblick-Prüfung | R1/R2 |
| **15:45–16:30** | **M1: End-to-End-Baseline** | Export steht, `evaluate_counting.py` auf einer Session, Overlays angesehen, erste Zahl in `docs/RESULTS.md` | R1, R2 |
| **16:30–17:45** | **M2: Validierung und Modell** | Leave-one-session-out-Zahlen, Fehlerbilder; Entscheidung, ob Kaggle-Training (Stufe 3 in `05`) startet | R1, R2, R3 (App-Gerüst) |
| **17:45–18:00** | **M3: Entscheidungspunkt** | Go/No-Go DL (max. 45 min Zeitbox je Option), Eintrag im Entscheidungslog | alle, 10 min |
| **18:00–19:00** | **Pizzapause** | 20–30 min essen, danach 30 min Zwischenstand und Pitch-Skizze (5 Folien, Abschnitt 8) | alle |
| **19:00–20:30** | **M4: Finale Modellversion** | Parameter eingefroren, vollständige Evaluation (Abschnitt 3.1), Demo stabil | R1, R2, R3 |
| **20:30** | **Feature-Freeze** | nur noch Fehlerbehebung und Dokumentation | alle |
| **20:30–21:30** | Dokumentation und Pitch-Material | README, Ergebnisgrafiken, Pitch-Entwurf (PPTX), Demo-Video als Fallback, **Teamname festlegen** | R3, R4 |
| **21:30–21:50** | **Abgabe-Trockenlauf** | Frische Umgebung, Setup nach README, ein Befehl reproduziert Ergebnisse | R3 prüft, R1 gegen |
| **21:50** | Hochladen in den Team-Drive-Ordner | Bestätigung sichern (Screenshot); Teamnamen mitteilen | R3 |
| **22:00** | **Abgabefrist** (technische Lösung) | 10 Minuten Puffer eingeplant | – |

Zeitregeln:
- Jeder Meilenstein hat ein **Ausstiegskriterium** (Abschnitt 3). Ist es um 15 min überschritten, wird der Umfang gekürzt, nicht die Qualität der Basis.
- Ab 20:30 wird nur noch stabilisiert. Neue Ideen landen in „Ausblick“ der Pitch-Folien.
- Commit-Rhythmus: mindestens alle 30–45 min; stündliches ZIP-Backup auf zweites Medium.

---

## 3. Meilensteine mit Abnahmekriterien

| Meilenstein | Abnahmekriterium (messbar) | Fallback, falls verfehlt |
|---|---|---|
| **M1 Baseline** | Kornzahl je Bild per Skript ausgegeben; Overlay für 5 Bilder visuell plausibel | Parameter pro Aufbau fixieren; Hintergrund-/Kanalwahl manuell |
| **M2 Validierung** | Zählabweichung gegen manuelle Zählung/Label auf ≥ 5 Bildern bekannt; TKM-Fehler (MAE, MAPE) einer Methode bekannt | Methode A (Wiegen + Zählen) als Kernlösung; Methode C nur falls Labels vorhanden |
| **M3 Entscheidung** | Dokumentiert: gewählter Ansatz, Begründung, geschätzter Restaufwand | klassisch bleibt Standard |
| **M4 Finale** | Alle Kennzahlen in `outputs/`; Streamlit-Demo fehlerfrei mit 3 echten Bildern; README geschrieben | Demo auf Beispielbilder beschränken, Video als Ersatz |
| **Abgabe** | Trockenlauf aus frischer Umgebung erfolgreich | zuletzt funktionierenden Commit abgeben |

### 3.1 Pflichtkennzahlen für Abgabe und Pitch

- Zählgenauigkeit: mittlerer absoluter Fehler (Körner) und in %.
- TKM-Genauigkeit: MAE [g], MAPE [%], R², Bland-Altman.
- Verteilungsgrafik der Korngrößen (Länge/Breite) und Siebfraktionen.
- 2–3 Fehlerbeispiele mit Erklärung.
- Laufzeit je Bild.

---

## 4. Rollen und Aufgabenverteilung

Teamgröße und Namen eintragen. Bei kleinerem Team werden Rollen kombiniert (siehe unten).

| Rolle | Name | Verantwortung | Hauptdateien |
|---|---|---|---|
| **R1 Daten und CV** | ________ | Datenimport, Erstblick, Segmentierung, Parameter, Zählvalidierung | `grain_segmentation.py`, `notes/01_…` |
| **R2 Modellierung und Evaluation** | ________ | Feature-Tabelle, TKM-Modelle, Gruppen-CV, Metriken, Fehleranalyse | `train_model.py`, `eda_tabular.py` |
| **R3 App, Reproduzierbarkeit, Abgabe** | ________ | Streamlit-Demo, README, Requirements, Trockenlauf, Upload | `app_streamlit.py`, `README.md`, Abgabeordner (Drive) |
| **R4 Domäne und Pitch** | ________ | Fragen an Landwirt, Storyline, Folien, Business Case, Q&A-Vorbereitung | `01`, `04`, `../pitch/` |

| Teamgröße | Zuordnung |
|---|---|
| 2 | Person A = R1 + R3, Person B = R2 + R4 |
| 3 | R1 · R2 + R3 (App ab M3) · R4 (Folien ab M2; hilft R1 beim Labeln) |
| 4 | je eine Rolle |
| 5+ | R1 teilt sich in Segmentierung und Datenaufbereitung; zusätzlich Tester/„Red Team“ für Fehlerfälle |

Arbeitsregeln:
1. Schnittstelle zwischen R1 und R2 ist die CSV (`grains.csv`, `image_features.csv`): Spaltennamen nicht ohne Absprache ändern.
2. Jede Entscheidung mit Zahl in `notes/02_Entscheidungslog.md`.
3. Ein Verantwortlicher für `main` (R3), andere arbeiten in Kopien/Branches und mergen zu festen Zeiten (16:15, 17:30, 19:00, 20:30).
4. Daten nie ins Remote-Repository, falls Weitergabe untersagt ist (Abschnitt 6).

---

## 5. „Ask the Farmer“ – Fragenkatalog

Zeitfenster 14:45–15:00 (ca. 15 min, vermutlich mit mehreren Teams). **Priorität P1 zuerst stellen**, Rest informell in der Pause.

Stand: Notizen aus einer früheren Fragerunde stehen in `../docs/CHALLENGE.md` (Abschnitt „Aus Ask the Farmer“). Dort bereits beantwortet: Zielgrößen (Gewicht je 1000 Korn, Keimrate, ca. 200 Körner/m²), Sorten Gerste und Weizen, Abdrehprobe mit ca. 1000 Körnern, vorsortierte Körner, Nutzen von Bruchkorn- und Fremdbesatzerkennung, iPad als Gerät, Internet auf dem Hof offen. **Offen bleiben**: geforderte Genauigkeit (Frage 3), Zeit je Probe heute (2), Preis-/Abzugsmerkmale an der Annahme (5), No-Gos und Zahlungsbereitschaft (8), UI-Wünsche. Diese zuerst stellen.

### P1 – Entscheidend für unsere Technik

| # | Frage | Warum wir fragen / Wirkung auf unsere Lösung |
|---|---|---|
| 1 | Welche Kultur(en) und Sorten, welches Erntejahr? | Kornform bestimmt Methode (länglich: Ellipse/Watershed; rund: Kreiserkennung); Referenzwerte |
| 2 | Wie wird die TKM heute bestimmt (Verfahren, Zeit je Probe, Genauigkeit)? Auf welche Feuchte bezogen? | Vergleichsbasis für unseren Nutzenvergleich; Feuchtekorrektur |
| 3 | Welche Genauigkeit reicht für Ihre Entscheidungen (± g oder ± %)? | Zielgröße für unsere Evaluation; „gut genug“-Schwelle |
| 4 | Wann und wofür messen Sie (Saatgutkauf, Saatstärke, Ernte, Verkauf)? Wie viele Proben je Saison? | Anwendungsfall, Durchsatz, Priorität von Geschwindigkeit |
| 5 | Welche Merkmale beeinflussen Preis oder Abzüge an der Annahme (Besatz, Bruch, HLG, Protein, Fallzahl)? Welche sieht man mit bloßem Auge? | Welche Qualitätsmerkmale wir zusätzlich per Bild bedienen können |
| 6 | Welche Kornfehler erkennen Sie visuell (Schmachtkorn, Bruch, Fusarium, Auswuchs, Verfärbung)? Können Sie Beispiele beschreiben/zeigen? | Zusatzfunktionen, Farb-/Formmerkmale |
| 7 | Wo und womit würden Sie ein solches Werkzeug nutzen (Smartphone, Halle, Feld, Mähdrescher)? Netz verfügbar? | Offline-Fähigkeit, Bedienkonzept, Bildqualität |
| 8 | Was würde die Lösung für Sie unbrauchbar machen (zu langsam, zu teuer, zu kompliziert)? Welche Größenordnung wäre zahlbar? | Abgrenzung, Pitch-Argumentation |

### P2 – Datenverständnis (falls Antworten nicht aus Dokumentation hervorgehen)

| # | Frage |
|---|---|
| 9 | Wie wurden die Bilder aufgenommen (Kamera, Hintergrund, Beleuchtung, Abstand, Maßstab)? |
| 10 | Wurde die TKM je Bild gewogen oder nur je Feld/Partie? Wie viele Körner liegen je Bild? |
| 11 | Auf Trockensubstanz oder bei Erntefeuchte? Ist die Feuchte je Probe bekannt? |
| 12 | Wurden Besatz, Spelzen, Bruchkörner vor dem Foto entfernt? |
| 13 | Gibt es bekannte Messausreißer oder fehlerhafte Proben im Datensatz? |
| 14 | Sind Sorte, Standort, Datum, Schlag je Probe verfügbar (für Gruppen-Validierung)? |
| 15 | Wie stark schwankt die TKM innerhalb eines Schlages bzw. zwischen Teilflächen? |

### P3 – Kontext und Nutzen

| # | Frage |
|---|---|
| 16 | Wie berechnen Sie die Saatstärke konkret, und welche Rolle spielt die gemessene TKM darin? |
| 17 | Wer misst sonst die TKM (Lohnunternehmer, Handel, Mühle)? Was kostet eine externe Messung? |
| 18 | Welche Wetter-/Jahreseffekte (Hitze, Trockenheit) haben Sie zuletzt in der TKM gesehen? |
| 19 | Ist ein amtlich anerkanntes Verfahren nötig, oder genügt ein Orientierungswert? |
| 20 | Wie wichtig sind Nachvollziehbarkeit und Dokumentation (Bild + Zahl) gegenüber reiner Geschwindigkeit? |
| 21 | Wären Sie bereit, Fotos mit Standort/Sorte zu teilen (Datenschutz, Betriebsdaten)? |

### Fragen an Veranstalter und im Technikinput (Stand nach Handout)

| # | Frage | Stand |
|---|---|---|
| V1 | Bewertungskriterien | **geklärt:** je 1/3 Technikjury (Genauigkeit und weitere Kriterien; KI erlaubt, erhöht die Anforderungen), Fachjury Landwirtschaft (UI und Nutzbarkeit; keine individuelle Produktfreigabe dokumentiert), Live-Voting des Publikums |
| V2 | Abgabeformat und -ort | **geklärt:** technische Lösung bis 27.10., 22:00 Uhr auf Google Drive (Team-Ordner, QR-Code im Handout); Präsentation bis 28.10., 12:00 Uhr ebenfalls dort. Offen: ob Code/Modell/Demo-Form vorgegeben ist (Format frei, „App etc.“) |
| V3 | Pitch-Dauer, Format | **geklärt:** 5 Minuten auf der Bühne, max. 5 Folien als PPTX, 1–3 Personen, Handmikrofone. Offen: Reihenfolge, Beamer/Adapter, ob Live-Demo praktikabel ist |
| V4 | Datenzugang | **geklärt:** Hugging Face `SmartFarmingLab/corn1000`, kein Token nötig, mehrere GB; Lizenz CC BY-NC 4.0 |
| V5 | Labels, Test-Teil, Metrik | **teilweise:** Label `count`, Punkt-Labels für ca. 158 Bilder; Test-Split `count_1000` (85 Bilder à 1000 Körner) steht auf der Dataset-Card (`05`, Abschnitt 1). Offizielle Metrik nicht genannt |
| V6 | Hardware | **geklärt:** Kaggle (T4 ×2, ca. 30 h/Woche/Person, Telefonverifizierung nötig); eigene Hardware nicht beschrieben |
| V7 | Erlaubte Hilfsmittel | **teilweise:** „KI ist erlaubt, allerdings steigen dadurch die Anforderungen“; zu externen Modellen/APIs nichts gesagt |
| V8 | Lizenz für unseren Code | offen |
| V9 | Teamregeln | Team 1 „PC Pool 3“ (vorläufiger Name); eigener Teamname bis zur Abgabe um 22:00 Uhr mitteilen |
| V10 | Wird auf dem öffentlichen `test`-Split (85 Bilder, je 1000 Körner) bewertet oder zusätzlich auf einem versteckten Hold-out? | **offen, einmal fragen** (Test-Split selbst ist bekannt) |

Antworten sofort in `notes/00_Antworten_Landwirt_Veranstalter.md` ablegen.

---

## 6. Datenschutz und Regeln (beim Start klären)

- Daten dürfen nur im Rahmen der Veranstaltung genutzt werden, sofern nicht anders erlaubt. Rohdaten **nicht** in öffentliche Repositories oder Cloud-Dienste laden.
- Externe Modell-APIs nur nach Freigabe (Datenabfluss).
- Quellenangaben für Referenzwerte (Abschnitt 4 in `01`) in den Folien nennen.

---

## 7. Plan B: Risiken und Gegenmaßnahmen

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|---|---|---|
| Datenset kommt spät oder ist anders als erwartet (z. B. nur Tabellen) | mittel | `eda_tabular.py` + `train_model.py` sind bereit; synthetische Bilder für Demo-Gerüst |
| Segmentierung auf echten Bildern schlecht (Schatten, Spiegelungen, Berührung) | hoch | Kanalwechsel, Flatfield, adaptiver Schwellwert; Overlays als Diagnose; bei Überlappung Cellpose-Zeitbox |
| Keine TKM-Labels je Bild | mittel | Methode A nur mit Probenmasse; sonst Fokus auf Zählung, Größenverteilung, Qualitätsmerkmale |
| Labels nur je Feld/Partie (weniger Datenpunkte) | mittel | Aggregation auf Partieebene, Ridge, Gruppen-CV, ehrlich als Machbarkeitsstudie darstellen |
| Hugging-Face-Download langsam oder blockiert (mehrere GB) | mittel | Download früh starten (Technikinput 15:00–15:45), zuerst `--limit 3`, nur Sessions S03/S04 (Gerste/Weizen); Kaggle als zweiter Weg |
| Kaggle ohne GPU/Internet (Telefon nicht verifiziert) | mittel | vorab verifizieren (Abschnitt 1); sonst klassische Baseline als Abgabe |
| Test (1000 Körner, Roggen) ist dichter als Training (max. 800) und hat nur 5 unabhängige Layouts | hoch | früh auf `test` messen, Dichte-Extrapolation prüfen, Fehler je Art berichten |
| Netz/Installation fällt aus | mittel | Umgebung vorab installieren; Hotspot; keine Abhängigkeit von Downloads im Kernpfad |
| Live-Demo scheitert beim Pitch | mittel | 60–90-s-Video und Screenshots als Fallback, Beispielbilder lokal |
| Teammitglied fällt aus/Burnout | niedrig | Rollen dokumentieren, Pausen einhalten (Pizzapause wirklich nutzen) |
| Überlauf kurz vor 22:00 | mittel | Feature-Freeze 20:30, Trockenlauf 21:30, Abgabe 21:50 |

---

## 8. Pitch: Struktur und Material

Vorgaben (Handout): **5 Minuten** auf der Bühne, **max. 5 Folien**, Abgabe als **PPTX** (Formatierungen prüfen), 1–3 Vortragende, Handmikrofone, weitere kreative Elemente sind erlaubt, Material und Umsetzung organisiert das Team selbst. Auf der Folie: Idee hinter dem Konzept und kurze Erklärung der Funktionsweise **für Publikum ohne technischen Hintergrund** (überwiegend Landwirt:innen, Berater:innen, Wissenschaft und Politik, tendenziell niedriger Wissensstand; die Challenge wird dort nur in einem 5-Minuten-Intro vorgestellt). Das Live-Voting des Publikums zählt ein Drittel; die Technikjury prüft Genauigkeit.

Folien und Überschriften sachlich und benennend halten. Zahlen mit Quelle und Testbedingung nennen; Ergebnisse auf synthetischen Daten als solche kennzeichnen.

| Folie | Benennung der Überschrift | Inhalt | Zeit |
|---|---|---|---|
| 1 | Ausgangslage: Körner zählen vor der Aussaat | Ablauf heute (1000 Körner von Hand zählen), Bedeutung für Saatstärke (200 Körner/m², kg/ha), Kosten eines Fehlers (1 % Zählfehler = 1 % Saatmenge) | 45 s |
| 2 | Lösung: Foto auf dem A4-Blatt | Bild der App/Foto, drei Schritte (Foto, Probe wiegen, Ergebnis), Ausgabe: Kornzahl, Tausendkorngewicht, Aussaatstärke, Qualitätshinweise | 60 s |
| 3 | Funktionsweise und Daten | verständliches Schaubild: Blatt erkennen → Körner finden → zählen; Datensatz (Sessions, Arten, Kameras), Besonderheit Bruchkorn/Zwillinge | 60 s |
| 4 | Ergebnisse | Zählfehler auf unbekannter Session (MAE, MAPE, Trefferquote ±2 %), 1–2 Beispielbilder mit Overlay, ehrliche Grenzen | 75 s |
| 5 | Nutzen und nächste Schritte | Zeitersparnis je Probe, Einsatz auf dem iPad, Erweiterungen (Keimrate als Eingabe, Bruchkorn, Fremdbesatz), Team und Name | 45 s |
| – | Demo/Video | wenn Live-Demo, dann in Folie 2 oder 4 einbetten (max. 30 s), Video als Fallback | – |

Zeitplan morgen: Folien bis **28.10., 12:00 Uhr** in den Drive-Ordner. Rollen: höchstens drei Vortragende, einer führt die Demo.

### Dramaturgie für ein fachfremdes Publikum

- Mit dem Bild des Landwirts beginnen, der Körner zählt, nicht mit der Technik.
- Fachbegriffe vermeiden („Kornzahl“, „Foto“, „Gewicht“), keine Modellnamen auf Folie 1–2.
- Eine Kennzahl im Fokus („nur x Körner Abweichung bei 1000“), alle weiteren im Backup.
- Handlungsaufforderung: Was soll das Publikum behalten? („Foto statt Zählen“).

### Demo-Drehbuch (30–90 s, je nach Folie)

1. App öffnen (vorab gestartet, Beispielbild geladen).
2. Bild hochladen → Overlay erscheint (Farbcodes erklären: grün/orange/rot).
3. Kornzahl und Probenmasse eingeben → TKM mit Plausibilitätsprüfung.
4. Siebfraktionen/Größenverteilung zeigen.
5. Ein Fehlerbeispiel offen ansprechen und erklären.

### Vorbereitete Antworten auf wahrscheinliche Jury-Fragen

| Frage | Antwortgerüst |
|---|---|
| Wie genau ist das Verfahren? | Kennzahl nennen (MAE/MAPE), Testbedingungen und Datenumfang, Grenzen offen sagen |
| Überträgt sich das auf andere Sorten/Kulturen? | Kalibrierung je Sorte/Partie nötig; Methode A ist sortenunabhängig; Ausblick: mehr Daten |
| Warum nicht Deep Learning? | Wenig Daten, Erklärbarkeit, Geschwindigkeit, Offline-Fähigkeit; DL als Erweiterung bei Überlappung |
| Was ist der Geschäftswert? | Zeitersparnis je Probe, Dokumentation, Fehlervermeidung bei Saatstärke (Beispielrechnung) |
| Wie geht ihr mit Feuchte um? | Feuchtekorrektur auf Bezugsfeuchte, Feuchte als Eingabe/Messgröße |
| Was passiert bei überlappenden Körnern? | Watershed, Cluster-Korrektur über Flächenanteil, ungelöste Fälle markiert; Empfehlung: Körner vereinzeln |
| Datenschutz? | Lokale Verarbeitung, keine Cloud-Pflicht |
| Wie skaliert das? | Batch-CLI, Streamlit lokal, Containerisierung als Ausblick |

---

## 9. Mittwoch, 28.10.2026

Veranstaltung: SMUL-Werkstatt „KI im Pflanzenbau: Vision oder Realität?“, Vortragssaal der Universitätsbibliothek Albertina. Preisverleihung 14:10–14:40 Uhr. Mindestens eine Person pro Team muss in der **Kernzeit 13:30–14:45 Uhr** vor Ort sein (spätestens zur Kaffeepause 13:30 Uhr).

| Uhrzeit | Block | To-do |
|---|---|---|
| bis **12:00** | **Abgabe Pitch-Deck (PPTX)** | Datei im Drive-Ordner, Formatierung in PowerPoint (nicht nur Vorschau) prüfen |
| ab 11:30 | Mittagsbuffet, Albertina | Ankommen, Technik prüfen (Adapter, Laptop-Akku, Beamer-Auflösung) |
| 12:00–13:15 | Puffer | Pitch zweimal laut durchsprechen, Zeit stoppen (5 min!); Demo offline testen; PPTX und Video auf USB-Stick und lokal |
| **13:30–14:45** | **Pitches (je 5 min) und Siegerehrung** | Reihenfolge erfragen; Demo vorab bereit; Fallback-Video |
| 14:10–14:40 | Preisverleihung | – |
| danach | Feedback, Kontakte | Fragen an die Jury notieren; Code und Ergebnisse sichern |

Packliste Pitch: Laptop und Netzteil, HDMI/USB-C-Adapter, PPTX (lokal und USB), Demo-Video (lokal), Beispielbilder, Visitenkarten oder QR-Code zum Repository, Wasser.
