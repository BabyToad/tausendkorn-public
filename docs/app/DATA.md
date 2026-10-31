# Daten: Verlauf der Proben

Stand 27.10.2026, 20:00 (nach Astras Runde 2). Baut auf der Tabelle `samples` in `app/server.py` auf (eine flache
Tabelle, SQLite unter `data/app/tausendkorn.db`). Ziel: **so wenig Schema wie möglich**,
aber die Zahl muss nachvollziehbar bleiben (was hat die Zählung gesagt, was hat der
Mensch geändert).

## 1. Grundsatz

- **Eine Zeile = eine Probe** (ein Foto einer Handvoll aus einer Partie).
- **Rohdaten bleiben unverändert:** Foto, Punkte der Zählung (`points_model`), Zahl der
  Zählung (`count_model`). Alles, was der Mensch ändert, liegt daneben.
- **Abgeleitete Werte (TKG, kg/ha) werden gespeichert**, damit der Verlauf auch dann
  stimmt, wenn sich Vorgaben im Rechner später ändern. Sie werden bei jeder Änderung
  der Eingaben neu berechnet (eine Funktion, eine Stelle im Code).

## 2. Schema (Soll)

Fett = gegenüber `app/server.py` (Stand 18:30) neu oder umbenannt. Alles andere ist
schon da und bleibt.

| Spalte | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `id` | INTEGER PK | ja | |
| **`client_id`** | TEXT UNIQUE (UUID) | ja | vom Gerät erzeugt; Server nimmt dieselbe ID nur einmal an (idempotentes Senden ohne Netz) |
| `created_at` | TEXT (ISO 8601, lokale Zeit mit Offset) | ja | Zeitpunkt des Fotos |
| **`updated_at`** | TEXT | ja | letzte Änderung |
| **`betrieb`** | TEXT | nein | Betrieb/Schlag, Freitext. Im MVP nicht anzeigen, nur für Export. |
| `kultur` | TEXT | ja | Schlüssel aus `SAATGUTRECHNER.md` (z. B. `winterweizen`), nicht der Anzeigetext |
| `sorte` | TEXT | nein | Freitext, z. B. „RGT Reform“ |
| `haenger` | TEXT | nein | Partie/Hänger, Freitext („Hänger 3“). Anzeigename „Partie“. |
| `status` | TEXT | ja | `wartet` · `zaehlt` · `pruefen` · `fertig` · `fehler` |
| `error` | TEXT | nein | Fehlertext für den Menschen |
| `photo` | TEXT | ja | Dateiname unter `data/app/photos/` (Original, EXIF-gedreht) |
| `width`, `height` | INTEGER | ja | Pixelmaße des gedrehten Fotos (Bezug für Punkte) |
| `count_model` | INTEGER | nach Zählung | Zahl der Zählung, **nie überschreiben** |
| **`points_model`** | TEXT (JSON `[[x,y],…]`) | nach Zählung | Punkte der Zählung, **nie überschreiben** |
| **`photo_sha256`** | TEXT | ja | Hash des Bildes, das gezählt wurde (Bezug der Koordinaten) |
| `points` | TEXT (JSON) | nach Zählung | aktuelle Punkte = Modell + Korrekturen, **mit stabiler ID**: `[[id,x,y],…]`, Modellpunkte `m0…`, ergänzte `c0…` |
| **`attempts`** | TEXT (JSON-Liste) | nein | frühere Zählversuche (`count_model`, `points_model`, Zeit), falls „Nochmal zählen“ |
| **`provenance`** | TEXT | ja | `model` (Punkte stammen sicher vom Modell) oder `legacy` (alte Zeilen, Herkunft unklar) |
| `count` | INTEGER | nach Zählung | `len(points)`, die Zahl, mit der gerechnet wird |
| **`corrections`** | TEXT (JSON-Liste) | nein | Protokoll der Taps, siehe 3 |
| `check_here` | TEXT (JSON) | nach Zählung | Prüfstellen aus `count_kernels`, je Eintrag + **`done: bool`** |
| `cost_usd`, `seconds` | REAL | nach Zählung | Kosten und Dauer der Zählung (intern, nicht anzeigen) |
| `weight_g` | REAL | nein | Gewicht der gezählten Körner in g |
| `tkg` | REAL | abgeleitet | `weight_g / count × 1000`, **ungerundet** speichern, nur Anzeige rundet |
| `keimfaehigkeit` | REAL | nein | % (z. B. 95), nicht Anteil |
| `feldaufgang` | REAL | nein | % |
| **`modus`** | TEXT | nein | `keimfaehig` (Standard) oder `pflanzen` (`SAATGUTRECHNER.md` 2.3), **pro Probe** |
| **`saatstaerke`** | REAL | nein | Zielwert im Standardmodus, keimfähige Körner/m² |
| `plants_m2` | REAL | nein | Zielwert im Pflanzen-Modus, Pflanzen/m² |
| **`formel_version`** | INTEGER | nein | Version der Rechenformel (heute 1) |
| **`koerner_m2`** | REAL | abgeleitet | abzulegende Körner/m² |
| `kg_ha` | REAL | abgeleitet | Aussaatmenge, ungerundet speichern, Anzeige ganzzahlig |
| **`rev`** | INTEGER | ja | Revisionszähler; jede Änderung schickt den erwarteten `rev` mit, Server lehnt veraltete Speicherungen ab |
| `notes` | TEXT | nein | Freitext („Sack von Händler X“, „Bruch auffällig“) |
| **`deleted_at`** | TEXT | nein | Papierkorb statt Löschen, siehe 4 |

Migration aus dem jetzigen Stand: `ALTER TABLE samples ADD COLUMN …` für die neuen
Spalten; `points_model` einmalig mit `points` füllen, wo es leer ist, und dann
`provenance='legacy'` setzen (die Punkte könnten schon korrigiert sein).
Bestehende Zeilen mit `plants_m2` bekommen `modus='pflanzen'`, `formel_version=0`.

**Reproduzierbarkeit:** Aus `weight_g`, `count`, `modus`, Zielwert, `keimfaehigkeit`,
`feldaufgang` und `formel_version` muss sich `kg_ha` jederzeit exakt neu rechnen lassen.
Ein späterer Gerätewechsel des Modus ändert alte Proben nicht.

### Warum keine zweite Tabelle für Partien/Sorten

Für den MVP reicht Freitext mit Vorschlägen (`SELECT DISTINCT sorte FROM samples
WHERE kultur=? ORDER BY max(created_at) DESC`). Eine eigene Tabelle `partien` lohnt erst,
wenn mehrere Proben pro Partie gemittelt werden sollen (`ROADMAP.md`).

## 3. Korrekturen

Jeder Tap in Prüfen erzeugt einen Eintrag:

```json
{"e": 1, "t": "2026-10-27T18:42:10+01:00", "op": "add", "id": "c0", "x": 1234.5, "y": 876.0, "spot": 2}
{"e": 2, "t": "...", "op": "remove", "id": "m412", "spot": 2}
{"e": 3, "t": "...", "op": "undo", "of": 2}
```

- `e` = laufende Ereignisnummer, `id` = stabile Punkt-ID (`m<i>` = i-ter Modellpunkt,
  `c<n>` = n-ter ergänzter Punkt). Entfernen über die ID, nicht über Koordinaten
  (zwei Punkte können fast gleich liegen).
- `x, y` in Pixeln des gedrehten Fotos (wie `points`).
- `spot` = Index in `check_here` oder `null` (Korrektur in „Alle Markierungen“).
- **Rückgängig ist selbst ein Ereignis** (`undo`), nichts wird gelöscht. `points` =
  `points_model` + alle nicht rückgängig gemachten Ereignisse, neu abgespielt.
- Korrektur, neues `count`, neues `tkg`/`kg_ha` und `rev` werden in **einer**
  Transaktion gespeichert.

Nutzen über die App hinaus: Korrekturen sind gelabelte Fehlerstellen der Zählung, also
Trainings- und Messdaten (Wie oft korrigieren Menschen? Wo? Welche Kultur?). Exportierbar.

## 4. Regeln fürs Bearbeiten

| Was | Darf geändert werden? | Folge |
|---|---|---|
| Kultur, Sorte, Partie, Betrieb, Notiz | jederzeit | Kultur ändern setzt Rechner-Vorgaben **nicht** zurück, zeigt aber Hinweis, wenn Werte von den neuen Vorgaben abweichen |
| Gewicht, Keimfähigkeit, Feldaufgang, Pflanzen/m² | jederzeit | TKG, Körner/m², kg/ha sofort neu berechnen und speichern |
| Punkte (Korrekturen) | jederzeit, auch nach „fertig“ | `count` neu, damit TKG und kg/ha neu |
| Foto | nein | Neues Foto = neue Probe. Die alte bleibt (oder wird gelöscht). |
| `count_model`, `points_model` | nie | |
| Probe löschen | ja, mit Bestätigung | setzt `deleted_at`; Liste blendet aus; „Rückgängig“-Leiste 10 s; endgültig nach 30 Tagen oder per „Papierkorb leeren“ |
| Nochmal zählen | nur bei `fehler` oder unvollständiger Zählung | alter Versuch wandert nach `attempts`, Korrekturen bleiben dort erhalten; neuer Versuch startet ohne Korrekturen (Hinweis vorher) |

`updated_at` und `rev` bei jeder Änderung setzen. Kein vollständiger
Versionsverlauf im MVP; das Korrekturprotokoll reicht für die Nachvollziehbarkeit der
Zahl. Später (ROADMAP): Ergebnis-Schnappschuss je „Speichern“, damit eine spätere
Gewichtsänderung nicht verdeckt, mit welchem kg/ha-Wert gedrillt wurde.

Bekannte Grenze: Partie ist Freitext. „Hänger 3“ aus zwei Jahren ist nicht dieselbe
Partie. Für das Mitteln mehrerer Proben braucht es eine Partie-ID (ROADMAP 2.2).

Status-Logik:

- `wartet` → Foto gespeichert, Zählung noch nicht gestartet (kein Netz).
- `zaehlt` → läuft. Beim Serverstart: `zaehlt` → `fehler` („Zählung unterbrochen“), so
  wie jetzt schon.
- nach Zählung: `pruefen`, wenn ein `check_here`-Eintrag `done=false` hat, sonst `fertig`.
- Zählung unvollständig (Ausschnitte `failed`): `fehler` mit Text „Zählung unvollständig“,
  nie `fertig`.
- `fertig` heißt „Zahl steht“, nicht „Gewicht eingetragen“. „Gewicht fehlt“ ist eine
  Anzeige (weight_g IS NULL), kein Status.

## 5. Export

- CSV mit allen Spalten außer `points*`, `corrections`, `check_here` (die sind JSON und
  für die Tabellenkalkulation nutzlos). Semikolon als Trenner, Dezimalkomma, UTF-8 mit
  BOM, damit Excel auf deutschen Geräten es richtig öffnet.
- Foto + Punkte als JSON pro Probe auf Wunsch (Rohdaten-Export für uns).

## 6. Datenschutz und Speicherort

- Fotos zeigen nur Körner auf Papier. Betrieb/Sorte sind betriebliche Daten, keine
  personenbezogenen; trotzdem: nichts davon geht an die Zählung außer dem Foto.
- Die Zählung (Gemini) bekommt nur Bildausschnitte. Das in der App einmal sagen
  („Zum Zählen wird das Foto an einen Rechendienst gesendet.“).
