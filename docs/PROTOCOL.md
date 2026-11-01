# Evaluationsprotokoll (gegen Benchmaxxing)

Festgelegt 27.10.2026, vor dem Vergleich der Methoden. Änderungen nur mit Eintrag
unten und Begründung.

## Splits

Erzeugt mit `uv run python -m tausendkorn.splits`, nur Bilder mit Punkt-Labels.
Aufeinanderfolgende Steps einer Session teilen die meisten Körner, deshalb Step-Blöcke
mit Puffer:

| Split | Steps | Bilder | Zweck |
|---|---|---|---|
| `dev` | 14–19 | 24 (1 Foto pro Arrangement) | Methoden ausprobieren, Prompts und Parameter wählen |
| `holdout` | 0–9 | 40 (1 Foto pro Arrangement) | **Einmal** am Ende, mit eingefrorener Pipeline |
| `train` | 21–30 | 49 (alle Fotos) | Nur für lernende Methoden |
| Test `count_1000` | – | 85 | Anderer Tag, enthält **Roggen** (sonst nirgends). Finale Prüfung. |

Steps 10–13 und 20 sind Puffer und werden nicht benutzt.

SHA-256 zum Festschreiben:

Die Hashes gelten für die Listen mit CRLF-Zeilenenden, wie sie beim Einfrieren auf Windows vorlagen; mit LF-Zeilenenden (Git-Blobs, Linux/macOS) ergeben sich andere Werte.

```
f2d3090fe4c8c718c8df061a4b03277fa355bdff5748b625b377bedb19a33683  splits/dev.txt
06e4757a6dc5c29314f7bb730d1101f3bdca54261a6c36c9916dc3d5a2e7aa84  splits/holdout.txt
9a67117c40abbe7da37cc33c41d50e1a6dc9c478f53c8766a7863d858e57c3b8  splits/train.txt
```

## Regeln

1. Entscheidungen (Methode, Prompt, Kachelgröße, Schwellen) nur auf `dev`.
2. `holdout` und `count_1000` laufen erst, wenn die Pipeline eingefroren ist, und
   werden in `docs/RESULTS.md` mit Commit-Hash eingetragen. Danach kein Nachjustieren
   mit diesen Bildern; neue Ideen gehen wieder über `dev`.
3. `count_1000` allein beweist nichts: Jedes Bild hat 1000 Körner, ein konstanter
   Zähler hätte Fehler 0. Immer zusammen mit `holdout` (170–800 Körner) berichten.
4. Metriken: Summenfehler und MAE, Bias, max. Fehler, Anteil exakt / ±1 / ±5; bei
   Punkt-Methoden zusätzlich Precision/Recall aus 1:1-Abgleich mit `kernel_points`.
5. Die Punkt-Labels können wenige Körner von `count` abweichen; `count` bleibt das
   Label für Summen, Punkte dienen der Fehleranalyse.
6. Der Pilot auf `S05-017` (Dev-Block) wurde vor diesem Protokoll gemacht und zählt
   als Dev-Erfahrung.

## Bekannte Abweichung: keine session-unabhängigen Splits

`docs/CHALLENGE.md` und die Datensatz-README verlangen eine Aufteilung nach `session`.
Unsere `dev`/`holdout`/`train`-Splits enthalten dagegen **alle vier Sessions S02–S05** und
trennen nur nach Step-Blöcken mit Puffer. Hintergrund, Kamera und Teile der Körner sind
dadurch zwischen den Splits geteilt (Astra-Review, 27.10.). Konsequenzen:

- Holdout-Zahlen sind **Within-Session-Ergebnisse**, keine Aussage über neue Sessions.
- Für Methoden ohne Training (unsere VLM-Pipeline) ist das Risiko geringer als bei
  trainierten Modellen, aber Prompt- und Schwellenwahl auf `dev` kann Session-spezifisch
  sein.
- Der Test-Split `count_1000` stammt von einem **anderen Tag** und enthält **Roggen**, der
  nirgends sonst vorkommt; er ist der unabhängigste Check, den wir haben.
- Bereits benutzte Daten werden nachträglich nicht als „unberührt“ umdeklariert. Echte
  Unabhängigkeit liefern erst neue, eigene Fotos (`data/staged/`).

## Änderungen

| Datum | Änderung | Grund |
|---|---|---|
| 27.10. | Holdout-Ergebnisse von Pipeline v1.0 (11 Bilder, Commit 80be2c4) verworfen, Neulauf mit v1.0.1 | Astra-Review: stille Unterzählung bei Ausfällen, Naht-Abgleich, Rasterabdeckung |
