# Feld-App: Durchklick in Bildern

Stand 27.10.2026, App auf `main` (UI-System B „Labor“), Mock-Modus
(`uv run python -m app --mock`: gespeichertes Ergebnis statt bezahlter Zählung, Foto aus
`corn1000`). Handy-Ansicht 390 px breit, 2-fach aufgelöst, aufgenommen mit Chrome
(DevTools-Geräteemulation). Kornpunkte und Prüfstellen stammen aus einem echten
Pipeline-Lauf auf diesem Foto (`app/mock/result.json`, 411 Punkte, 6 Prüfstellen).

| # | Bild | Was man sieht |
|---|---|---|
| 1 | [01_neue_probe.png](01_neue_probe.png) | Kultur wählen (bei Wintergerste die Art), Sorte und Partie optional, Vorschläge aus dem Verlauf. |
| 2 | [02_foto.png](02_foto.png) | Drei Sätze Fotoanleitung, dann Kamera oder Galerie. |
| 3 | [03_zaehlen.png](03_zaehlen.png) | Zählung läuft auf dem Laptop: nur ein unbestimmter Balken und die echte Sekundenzahl, kein erfundener Fortschritt. |
| 4 | [04_gezaehlt.png](04_gezaehlt.png) | Ergebnis mit allen Kornmarken; eine Entscheidung: übernehmen oder die 6 unsicheren Stellen prüfen. ± ist als Annahme gekennzeichnet. |
| 5 | [05_pruefkarte.png](05_pruefkarte.png) | Prüfkarte: Ausschnitt groß, Kommentar der Zählung, Tippen setzt oder entfernt ein Korn, Zähler im Kasten. |
| 6 | [06_alle_markierungen.png](06_alle_markierungen.png) | Alle Marken und Prüfstellen auf dem ganzen Foto, Zoom und Korrektur möglich. |
| 7 | [07_ergebnis.png](07_ergebnis.png) | Ergebnis und Saatgutrechner: TKG mit Spanne, Saatstärke (keimf. Körner/m²) und Keimfähigkeit, Aussaatmenge mit Rechenweg, TKG der Partie aus zwei Handvoll (1000 × Σ Gewicht / Σ Körner), Abdrehprobe. |
| 8 | [08_foto_warnung.png](08_foto_warnung.png) | Foto-Vorprüfung vor der bezahlten Zählung: Häufchen markiert, „Neu aufnehmen“ oder „Trotzdem zählen“. |

Hinweis: Im Mock-Modus ersetzt die App das hochgeladene Foto durch das gespeicherte
Beispielfoto, damit Marken und Foto zusammenpassen. Gewichte und Keimfähigkeit sind
Beispielwerte.

## Echter Lauf (kein Mock), 27.10.2026, 20:45

`uv run python -m app` mit Gemini 4 Argon, Pipeline v1.0.2, Dev-Foto
`S04/S04-014_galaxy-tab-s6-lite_IMG_20261015_140950.jpg` (Weizen, Soll **493** Körner).
Hochgeladen über dieselbe Schnittstelle wie der Browser.

| Messgröße | Wert |
|---|---|
| Angezeigte Kornzahl | **488** (−5, −1,0 %) |
| Prüfstellen | 0 → direkt zum Ergebnis, „automatisch gezählt“, ± 5 (Annahme) |
| Zählzeit (Server) | 44,9 s; Upload + Vorprüfung ca. 1 s; 47 s vom Senden bis zum Ergebnis |
| Kosten | 0,386 $ |
| Vorprüfung | ohne Befund (Schärfe 291) |

Gewicht (22,6 g) und Keimfähigkeit (95 %) sind Beispielwerte. Bilder in [`echt/`](echt/):
Handy (390 px) `01_…05_`, PC (1280 px) `pc_…`. Die Fotoseite am PC (`pc_02_foto.png`,
„Foto wählen“ statt Kamera) zeigt den Stand von PR #23.

Die beiden Verlaufsbilder wurden wegen sichtbarer Kopplungsdaten aus dem öffentlichen Snapshot entfernt.

Fotos: corn1000 — Smart Farming Lab, Universität Leipzig, [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Details: [DATA_LICENSE.md](../../../DATA_LICENSE.md). Eigene iPad-Fotos sind Team-Aufnahmen.
