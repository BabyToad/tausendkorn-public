# Astra-Abschlussreview A: Ehrlichkeit und Konsistenz der Zahlen

GPT-6 Astra (Codex, nur lesend), 27.10.2026 21:33, Stand 52ca19c. Pflichtpunkte vor dem Upload wurden an die Lanes verteilt; „after submission“ ist die offene Liste.

**Verdict: Textkorrekturen vor Upload nötig; die zentralen Messwerte sind korrekt.** Aus JSONs nachgerechnet: Holdout MAE **5,93**, MAPE **1,845 %**, **26/30** innerhalb ±3 %, p90 **3,136 %**; Test **n=6, MAE 15,83**. YOLO auf denselben Bildern: **3,23 / 12,5**. Prüfung des lokalen Stands `52ca19c`; nichts geändert.

**must fix before upload (text only, ≤5 items, file:line + exact replacement wording)**

| # | Fundstelle / Problem | Exakte Ersatzformulierung |
|---|---|---|
| 1 | `pitch/SCRIPT.md:48–51`; `pitch/web/index.html:105,135–147`; `ABGABE.md:45–47`; `README.md:19`: „nie angesehen“ / „jedes Prüffoto einmal“ verschweigt den verworfenen Holdout-Lauf. Test-Commit ist außerdem **44a553a**, nicht d2ced75. | „Die finale Pipeline v1.0.2 wurde einmal auf 30 Holdout- und 6 Testbildern gemessen. Ein früherer Holdout-Lauf mit 11 Bildern wurde nach Fehlerkorrekturen verworfen; der Holdout ist daher nicht vollständig unberührt. Die Splits teilen Sessions und liefern Within-Session-Ergebnisse. Holdout-Commit: d2ced75; Test-Commit: 44a553a; identischer Pipeline-Fingerprint 422967946cbd.“ |
| 2 | `pitch/SCRIPT.md:35,145–146`; `pitch/web/index.html:52`: „alles zählt“ widerspricht der korrekten Regel in App, README und ABGABE. | „Gewogen wird die ganze Probe einschließlich Bruch und Fremdbesatz. Gezählt werden nur ganze Körner. Nichts vor dem Wiegen aussortieren.“ |
| 3 | `docs/RESULTS.md:211–214`; `ABGABE.md:101–103`: Hartweizen-Auslassungen werden als geklärte Ursache dargestellt. Umgekehrt behauptet `docs/befund/DURUM_COUNT_1000.md:9–12,20–28` physisch etwa 950 Körner und einen unwahrscheinlichen Modellfehler. Beides ist unbewiesen. | „Die Hartweizen-Abweichung ist ungeklärt: Argon zählt 942, YOLO auf demselben Foto 948; über 17 Fotos zählt YOLO 911–976. Gemeinsame Unterzählung verdeckter Körner und eine Abweichung der Probe vom Label sind nicht ausgeschlossen. Ein fehlender 50er-Becher ist nur eine Hypothese. Gewertet wird unverändert gegen 1000; Test-MAE 15,8 bei n=6.“ |
| 4 | `README.md:80–81`; `ABGABE.md:34–36`: YOLO erscheint als integrierter Pipeline-Schritt. `pitch/web/index.html:108`: „auf den Testfotos deutlich ungenauer“ suggeriert einen Vergleich auf denselben Bildern – dort ist YOLO besser. | „YOLO11s wurde separat offline verglichen und ist nicht in die App integriert. Auf denselben 30 Holdout-/6 Testbildern: MAE 3,2/12,5; auf allen 85 Testbildern: MAE 25,4. Die Laufzeit lag auf der RTX 3070 typischerweise bei 0,4 Sekunden pro Bild.“ |
| 5 | `README.md:91–93,111`: nur ein Live-Test / kein echtes iPad ist seit `docs/RESULTS.md:287–288` veraltet. Kosten in `README.md:33`, `ABGABE.md:71`, `pitch/SCRIPT.md:127`, `pitch/web/index.html:165` sind keine vollständige gemessene Spanne; „Cent“ lässt die Währung offen. | **Live:** „Zwei erfolgreiche Einzeltests, keine Messreihe: PC-Upload 488 statt 493 Körner, 47 s, 0,39 US-Dollar; eigenes iPad-Foto über Hotspot 233 Marken, 54 s, 0,36 US-Dollar. Beim iPad-Foto wurden per Sichtprüfung zwei Doppelmarkierungen festgestellt; eine unabhängige Sollzählung fehlt.“ **Kosten:** „Gemessene API-Kosten pro Foto: Holdout 0,12–0,56 US-Dollar, Test 0,61–0,79 US-Dollar; Mittelwerte 0,31 bzw. 0,66 US-Dollar.“ |

**after submission**

| Fundstelle | Nacharbeit |
|---|---|
| `README.md:24`; `ABGABE.md:51`; `docs/RESULTS.md:204`; `docs/STATUS.md:49` | Gemessener Holdout umfasst **170–482**, nicht 170–800 Körner. STATUS nennt die bereits abgeschlossene Messung noch als nächsten Schritt. |
| `README.md:10`; `ABGABE.md:12`; `site/index.html:43,60`; Pitch mehrfach | „Jedes Korn markiert“ → „Jedes als Korn erkannte Objekt wird markiert.“ „Roggen kannte keines unserer Modelle“ auf eigene Entwicklungs-/Trainingsdaten beschränken; Gemini-Vortraining ist unbekannt. |
| `app/static/app.js:695,865` | Bestätigte Prüfstellen entfernen das Fehlerband; Verlauf sagt pauschal „geprüft“. Das belegt keine fehlerfreie Gesamtzählung. Band beibehalten und „Prüfstellen bestätigt“ verwenden. |
| `site/index.html:120`; `site/llms-full.txt:30` | Gleiche Besatzverteilung ist eine **Voraussetzung**, kein bewiesener Sachverhalt. Entsprechend bedingt formulieren. |
| `README.md:29–30`; `pitch/SCRIPT.md:136–138`; `ABGABE.md:120` | „Veranstalter bereits gefragt“ ist im geprüften Material nicht belegt; Abgabe-Checkliste nennt Versand noch optional. Versandstatus vereinheitlichen. |