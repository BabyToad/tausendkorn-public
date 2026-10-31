# Zweitmeinung: Gegenprüfung der Kornzahl mit Ampel

Konzept vom 27.10.2026 (Hackathon, Team 1). **Status: Konzept plus Referenzcode, noch auf
keinem echten Foto gemessen.** Alle Zahlenwerte unten sind Platzhalter, bis sie nach
[`PROTOCOL.md`](PROTOCOL.md) kalibriert sind.

Zugehörig: [`PROBLEMFAELLE.md`](PROBLEMFAELLE.md) (bekannte Schwächen und offene Fälle),
[`../src/tausendkorn/agreement.py`](../src/tausendkorn/agreement.py) (Referenzcode),
GitHub-Issues mit Label `zweitmeinung` (Sammel-Issue [#1](https://github.com/BabyToad/tausendkorn/issues/1)).

> **Abgleich mit `docs/STATUS.md` (18:10):** Der Kurs des Teams ist eine VLM-Pipeline
> (Gemini auf adaptiven Ausschnitten, `pipeline.py`), die klassische Pipeline dient dort
> nur noch als Schneidehilfe. Die Rolle des Prüfers (Abschnitt 2) ist damit **offen**:
> (a) klassische Pipeline als Prüfer behalten, abhängig von der Messung in
> [#2](https://github.com/BabyToad/tausendkorn/issues/2); (b) die eigene Prüfschleife
> des VLM (Konfidenz je Ausschnitt, Prüfstellen) liefert die Signale S02–S04; (c) ein
> zweiter, anderer Zähler (GeCo2/YOLO laut `GPU_BRIEF.md` (nicht im öffentlichen Snapshot enthalten)). Die Idee der
> Ampel aus mehreren Signalen bleibt gültig, der Text unten nennt „Detektor“ und
> „klassisch“ als Beispiele, nicht als Festlegung.

## 1. Worum es geht

Die Kornzahl ist das Hauptkriterium der Challenge ([`CHALLENGE.md`](CHALLENGE.md)). Ein
Zähler liefert aber immer eine Zahl, auch wenn das Foto schlecht ist oder das Modell
daneben liegt. Der Landwirt sieht der Zahl nicht an, ob sie stimmt.

Idee: **Zwei Zähler, die auf verschiedenen Prinzipien beruhen, zählen dasselbe Foto.**
Stimmen sie überein, ist es unwahrscheinlich, dass beide gleichzeitig falsch liegen.
Weichen sie ab, zeigt die App eine Warnung mit einem konkreten Hinweis, was zu tun ist.

Nutzen:

- **Landwirt:** weiß, wann er der Zahl trauen kann und wann er das Foto wiederholen soll.
- **Technikjury:** Unsicherheit wird gemessen und ausgewiesen statt verschwiegen.
- **Pitch:** "Wir sagen dir, wann wir uns unsicher sind" ist ehrlicher und
  überzeugender als "immer exakt".

## 2. Rollen

| Rolle | Wer | Aufgabe |
|---|---|---|
| Hauptzähler (A) | gekachelter Detektor (siehe [`RESEARCH_ASTRA.md`](RESEARCH_ASTRA.md)) | liefert die **angezeigte** Zahl und die Punkte fürs Overlay |
| Prüfer (B) | klassische Pipeline, [`../wissensbank/scripts/classical_counter.py`](../wissensbank/scripts/classical_counter.py) | liefert nur eine **Vergleichszahl**, wird nie angezeigt |
| Zusatzsignale | A, B und das Foto selbst | Kachelraster, Konfidenzen, Blobgrößen, Blatt, Schärfe, Licht |
| Bewertung | `agreement.assess(...)` | macht daraus Ampel plus Hinweistexte |

B muss **nicht genau** sein, nur **anders falsch** als A. Ein klassischer Zähler macht
andere Fehler als ein trainiertes Netz (Tabelle in Abschnitt 3).

## 3. Warum die Fehler verschieden sind (Hypothesen)

Nur die Zeile zum Datensatz ist belegt, der Rest sind plausible Erwartungen, die zu
messen sind (siehe PF-02, PF-04 in [`PROBLEMFAELLE.md`](PROBLEMFAELLE.md)).

| Situation | Detektor A | Klassisch B |
|---|---|---|
| Körner berühren sich | meist ok (Einzelkorn-Erkennung) | unterschätzt: ein Blob = ein Objekt, Korrektur über Fläche ist grob |
| ungewöhnliche Art, Farbe, Licht | kann schwächeln (Trainingslücke, z. B. Roggen) | robust, da Schwelle adaptiv |
| Spreu, Grannen, Steine | kann sie als Bruch oder Fremd klassifizieren | zählt sie oft mit |
| Schatten, Spiegelungen | kann Fehltreffer erzeugen | kann Körner verlieren |
| **Datensatz** | Test hat 1000 Körner je Bild, Training höchstens 800 | gleiche Dichte im Test: B nur an Attrappen getestet |

## 4. Ablauf und Signale

```python
a      = detector_count(img)       # Hauptzähler, wird angezeigt
b      = classical_count(img)      # Prüfzahl, kann None sein
a_shift = detector_count(img, grid_offset=0.5)   # gleiches Modell, halbe Kachel versetzt

verdict = agreement.assess(
    a, b,
    count_main_shifted=a_shift,
    low_conf_share=..., big_blob_share=..., sheet_found=...,
    sharpness=agreement.sharpness(gray), brightness_cv=agreement.brightness_cv(gray),
)
verdict.name      # "gruen" | "gelb" | "rot"
verdict.reasons   # Liste mit Code und deutschem Hinweistext
```

**Regel:** Die relative Abweichung `|a-b| / ((a+b)/2)` setzt die Basisstufe (grün, gelb
oder rot). Jedes **weitere** verletzte Signal senkt die Ampel um eine Stufe, höchstens
bis rot. Fehlt der Prüfer, ist das Ergebnis **nie grün**.

| Code | Signal | Quelle | Gelb/Rot ab (Platzhalter) | Hinweistext an den Landwirt |
|---|---|---|---|---|
| S00 | Prüfer liefert nichts | B | – | Ergebnis konnte nicht gegengeprüft werden |
| S01 | Abweichung A zu B | A, B | 3 % / 8 % | Zählungen weichen ab, Foto wiederholen |
| S02 | A mit sich selbst bei halb versetztem Kachelraster | A | 1,5 % | Ergebnis schwankt, Foto näher und gerade |
| S03 | Anteil unsicherer Treffer (Konfidenz 0,25–0,5) | A | 15 % | Licht prüfen, keine Schatten |
| S04 | Anteil großer Blobs (>1,5 × Mediankorn) | B | 20 % | Körner weiter auseinanderlegen |
| S05 | A4-Blatt nicht gefunden | B (`rectify_a4`) | – | Ganzes Blatt gerade von oben fotografieren |
| S06 | Schärfe (Varianz des Laplace) | Foto | < 60 | Foto unscharf |
| S07 | Helligkeits-Ungleichmäßigkeit (Variationskoeffizient der Blockmittel) | Foto | > 0,35 | Schatten und Spiegelungen vermeiden |
| S08 | Kornzahl außerhalb des geprüften Bereichs | A | <150 oder >1100 | Ergebnis mit Vorsicht nutzen |

Hinweistexte stehen im Code (`agreement.py`) und sind absichtlich **konkret und
handlungsleitend**, nicht nur "gelb".

## 5. Kalibrierung und Auswertung (verbindlich nach PROTOCOL.md)

1. **Schwellen nur auf `dev`** (`splits/dev.txt`, 24 Bilder) festlegen. Für jedes Bild
   den echten Fehler `|A - count|` gegen die Abweichung `|A - B|` und die Signale
   auftragen. Grün-Schwelle so wählen, dass im grünen Bereich der echte Fehler
   akzeptabel klein bleibt (Zielwert vorher im Team festlegen und hier eintragen).
2. Lernende Teile (z. B. Detektor) trainieren auf `train`, nie auf `dev`/`holdout`.
3. **Einmal** auf `holdout` und `count_1000` rechnen, wenn die Pipeline eingefroren ist,
   Ergebnis mit Commit-Hash in [`RESULTS.md`](RESULTS.md).
4. Berichten **je Ampelstufe**: Anteil der Fotos, MAE, max. Fehler, und je Art.
   Vorlage:

   | Stufe | Anteil Fotos | MAE Körner | max. Fehler | Fotos gesamt |
   |---|---|---|---|---|
   | grün | | | | |
   | gelb | | | | |
   | rot | | | | |

5. `count_1000` allein beweist nichts (jedes Bild hat 1000 Körner, ein konstanter
   Zähler hätte Fehler 0). Immer zusammen mit `holdout` berichten.
6. **Nicht** die Vorgabe "genau 1000 Körner im Test" als Signal benutzen. Das wäre auf
   neue Fotos nicht übertragbar.

Abgrenzung zu einer früheren Skizze im Chat: Dort war "eine ganze Session als
Hold-out" genannt. Verbindlich ist das Protokoll mit `dev`/`holdout`/`train`.

## 6. Grenzen (ehrlich benennen)

- Machen **beide** Zähler denselben Fehler (z. B. Spreu mitgezählt, dunkle Körner auf
  dunklem Grund übersehen), schlägt die Ampel nicht an (PF-01). Sie ist ein Indikator,
  keine Garantie.
- Ist B systematisch weit daneben, ist die Ampel dauernd rot und wertlos (PF-02). Dann
  die Signale S02–S08 stärker gewichten und B abschwächen.
- Schwellen gelten für die gemessenen Arten und Kameras. Neue Arten oder Geräte brauchen
  neue Kalibrierung (PF-03, PF-09).
- Mit 24 Dev-Bildern ist die Kalibrierung grob (PF-04). Lieber konservativ einstellen.

## 7. Einbindung ins Team-Interface

Schnittstelle laut [`../README.md`](../README.md):
`count_kernels(image) -> {count, points, broken, foreign}`. Vorschlag: zusätzlich ein
Feld `check` mit `verdict.as_dict()`:

```python
{"count": 1000, "points": [...], "broken": [...], "foreign": [...],
 "check": {"level": "gelb", "gap": 0.041,
           "reasons": [{"code": "S01_abweichung_gelb", "hint": "..."}]}}
```

UI (iPad, deutsch): große Zahl, Overlay, Ampel mit **einem** Satz Hinweis, Details
ausklappbar. Kein Fachjargon.

## 8. Stand und nächste Schritte

| Schritt | Stand |
|---|---|
| Konzept dokumentiert | erledigt (diese Datei) |
| Referenzcode `agreement.py` mit Selbsttest | erledigt, nur Logik getestet, nicht auf echten Fotos |
| Baseline B auf `dev` und `test` messen | offen, siehe [#2](https://github.com/BabyToad/tausendkorn/issues/2) |
| Signale S02–S04 aus Hauptzähler/Prüfer ausgeben | offen |
| Schwellen auf `dev` kalibrieren | offen, erst nach erstem Hauptzähler-Lauf |
| Ampel in die App einbauen | offen |
| Auswertung je Ampelstufe in `RESULTS.md` | offen |

Offene Fragen an die Fachjury / den Landwirt: Welche Abweichung ist für die Aussaat
praktisch egal (z. B. 1 %, 2 %)? Das legt die Grün-Schwelle fest, weil 1 % Zählfehler
1 % TKG-Fehler bedeuten (Dataset-Card).
