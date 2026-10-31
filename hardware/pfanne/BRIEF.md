# Tausendkorn-Pfanne: Konzept v0

Ziel: Landwirt schöpft eine Probe direkt aus dem Saatgutsack, schüttelt kurz, kippt den
Überschuss über die Schöpflippe zurück, macht ein Foto (App prüft die Belegung) und
stellt die Pfanne auf eine Waage (Tara eingraviert) → Tausendkorngewicht ohne Zählen.

- Wechseleinsatz mit 40 × 25 = 1000 Mulden, Weizen-Einsatz: Mulde 4,0 × 7,5 mm,
  3,0 mm tief, Stege 1,2 mm. Korn Weizen ca. 6–7 × 3–3,5 × 2,5–3 mm.
  Feld 209 × 219 mm, Einsatz 237 × 247 mm. Gerste/Hafer: eigene Einsätze, längere Mulden.
- Pfanne: mattschwarz (Kontrast), Rand 22 mm auf drei Seiten, vorne 45 mm Schöpflippe
  mit abfallenden Seitenwänden, Griff hinten 130 mm, 15° steigend.
- Vier helle Markerflächen (14 mm) in den Einsatzecken für Perspektive und Maßstab.
- Fertigung Prototyp: FDM-Druck (PLA/PETG), Einsatz separat.

Erzeugt mit `build_pfanne.py` (Blender 5.0, headless). Ausgaben in `out/`.

## v1 (nach Astra-Review, `ASTRA_REVIEW_v0.md`)

`build_pfanne_v1.py` → `out_v1/`. Alle STL geprüft: geschlossen (0 nicht-manifolde Kanten).

| Teil | Datei | Maße (mm) |
|---|---|---|
| Kassette Weizen, 500 Mulden (25 × 20), zweimal befüllen | `kassette_weizen_500.stl` | 161,2 × 209,2 × 3,0 |
| Träger mit offener Schürze (25 mm, Lippe 0,8 mm), Seitenrastung | `traeger.stl` | 165,8 × 236,8 × 16,6 |
| Griff (separat, 12° steigend) | `griff.stl` | 34 × 117 × 40 |
| 6 Testcoupons 5 × 4 Mulden: Breite 4,0/4,4/4,8 × Tiefe 1,6/2,0 | `coupon_w*_d*.stl` | je ca. 37 × 47 × 3 |

Mulde Weizen: gerundetes Rechteck 4,4 × 8,2 mm, Ecken r 1,0, Tiefe 1,8 mm, Stege 1,2 mm
mit 0,4 mm Fase je Seite (45°) → 0,4 mm Grat. Marker: 4 unterscheidbare 4×4-Muster
(Platzhalter für ArUco-Aufkleber ID 0–3, 8 mm).

**Reihenfolge heute:** zuerst Coupons drucken (PLA, 0,2 mm, ohne Stützen, ~30–60 min)
und mit echtem Weizen testen: Füllzeit, Leerstellen, Doppelbelegung, Körner auf Stegen,
Verluste beim Abkippen. Gate: ≥ 98 % Einfachbelegung nach kurzem Füllen. Erst dann
Kassette (2–4 h) und Träger drucken.

**Offene Risiken:** Größenselektion beim Füllen (TKG-Bias) gegen handgezählte Proben
prüfen; verdeckte Doppelbelegung ist im Foto nicht sicher erkennbar; Bruchkorn vor dem
Wiegen physisch entfernen. Waage: 0,01 g Ablesbarkeit.
