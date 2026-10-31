# Demo-Daten für `--mock`

`uv run python -m app --mock` zeigt dieses gespeicherte Ergebnis, statt die bezahlte
Zählung aufzurufen.

- `foto.jpg`: Foto `S03/S03-014_galaxy-tab-s6-lite_20260916_162825.jpg` aus dem Datensatz
  **corn1000, Smart Farming Lab Leipzig, CC BY-NC 4.0**
  (<https://huggingface.co/datasets/SmartFarmingLab/corn1000>), aufrecht gedreht
  (EXIF), volle Auflösung 2448 × 3264, als JPEG Qualität 85 neu gespeichert.
- `result.json`: Kornpunkte und Prüfstellen eines echten Pipeline-Laufs auf diesem Foto
  (411 Punkte, 6 Prüfstellen, englische Modellkommentare). Koordinaten in Pixeln von
  `foto.jpg`. `photo_original` nennt die Quelle im Datensatz.

Im Mock-Modus ersetzt die App jedes hochgeladene Foto durch `foto.jpg`, damit Marken und
Foto zusammenpassen. Fehlt die Datei, endet die Demo-Zählung mit einer Fehlermeldung.
