# Gestaltungsrichtungen der Feld-App

Drei klickbare Mockups mit denselben vier Bildschirmen (Verlauf, Foto-Anleitung,
Zählen/Prüfen, Ergebnis mit Saatgutrechner), echte corn1000-Probe (S03-014,
411 Punkte aus `app/mock/result.json`). Studie: `docs/design/STUDY.md`.

| Ordner | Richtung |
|---|---|
| `feldgeraet/` | A · Feldgerät: robustes Bedienterminal |
| `labor/` | B · Labor: ruhiges Präzisionsinstrument |
| `ackerblatt/` | C · Ackerblatt: Feldbuch und Saatgutkatalog |
| `system/` | **gewähltes UI-System (B · Labor)**: Tokens, Komponenten, Bewegung, Referenzseite. Doku: `docs/design/UI_SYSTEM.md` |
| `shared/` | gemeinsamer Kern der Mockups (`tk.js`), Foto und Punkte |

## Ansehen

Ein statischer Server reicht (das Foto wird relativ geladen):

```bash
uv run python -m http.server 8020 --directory design
```

Dann `http://localhost:8020/feldgeraet/` usw. Sprungmarken: `#start`, `#foto`,
`#pruefen`, `#ergebnis`. `?rm=1` zeigt die Fassung für reduzierte Bewegung.


Foto: `SmartFarmingLab/corn1000`, train-Bild S03-014 (Galaxy Tab S6 Lite),
CC BY-NC 4.0, zugeschnitten und verkleinert. Punkte: Zählung Gemini Argon (411, wahr 410).

Redundante Screenshot-Exporte sind nicht enthalten (Telefon 375 px, Tablet 768 px). Neu erzeugen bei laufendem Server mit
`uv run --no-project --with playwright python design/shared/screens.py`
(nutzt das installierte Chrome). `?check=2` springt direkt in Prüfstelle 2.
