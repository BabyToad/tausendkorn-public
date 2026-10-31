# Audit Kornzähler (Fable, 27.10.2026)

Geprüft: Metadaten beider Splits, alle 85 Vorhersage-JSONs von `final-yolo11s-count1000`,
holdout- und dev-JSONs, Overlays und Vollauflösungs-Ausschnitte mehrerer Testbilder, plus ein
**Störungstest nur auf dev** mit dem eingefrorenen Modell (Inferenz, ~3 min GPU, keine
Trainingsläufe). Skripte und Bilder: `runs/audit/fable_scratch/`. Gekennzeichnet:
[geprüft] = an Daten gemessen, [Vermutung] = plausibel, nicht gemessen.

## Die drei wichtigsten Erkenntnisse

**1. Die Diagnose „Farbe/Perspektive/Dichte“ hält der Prüfung nicht stand; der Treiber ist
Unschärfe.** [geprüft] Das schlechteste Bild (`…122805`, Gerste S23, −108) und ein Bild
derselben Anordnung 5 s früher (`…122800`, +1) haben dieselbe Farbe, dieselbe Dichte, dieselbe
Kamera. Unterschied: 122805 ist schräg aufgenommen, und sein hinterer Bereich liegt außerhalb
der Schärfentiefe (Ausschnitt `crop_122805.jpg`: weich, unmarkierte Körner klar sichtbar).
Hafer und Roggen des Testtags sind gar nicht gebeizt/rosa. Im Störungstest auf dev (24 Bilder,
Labels mittransformiert) reproduziert **nur** Gauß-Unschärfe den Testtag:

| dev, eingefrorenes YOLO11s conf 0,4 | Summe | MAE | Bias | max | R |
|---|---|---|---|---|---|
| unverändert | +19 | 3,0 | +0,8 | 14 | 0,995 |
| Keystone-Warp, Oberkante 0,6 / 0,45 der Breite | −17 / −28 | 3,9 / 5,4 | −0,7 / −1,2 | 11 / 20 | 0,993 / 0,987 |
| Skalierung 0,55 / 0,7 / 1,4 | −30 / −21 / +32 | 3,6 / 2,9 / 2,8 | | 10 / 9 / 8 | ≥0,989 |
| Gauß σ=2 / **σ=3** / σ=4 px | −205 / **−502** / −1120 | 10,4 / **22,4** / 48,1 | −8,5 / **−20,9** / −46,7 | 66 / **101** / 243 | 0,981 / 0,957 / 0,908 |

σ=3 px (bei 4000 px Bildbreite eine milde Weichheit) ergibt exakt das count_1000-Bild (MAE 25,
Bias −20, max 108). Perspektivgeometrie und Kornmaßstab allein kosten fast nichts; der Kachel-
Maßstab ist also nicht der Hebel. Perspektive wirkt nur indirekt: schräg + nah = hinten
unscharf. Ein kantenbasiertes Schärfemaß an den Kornrändern (schwächstes Fünftel des Blatts)
korreliert auf count_1000 mit dem Fehler (Spearman 0,46): Bilder mit Mindestschärfe ≥0,17 haben
im Mittel −2 (n=22), <0,12 im Mittel −41 (n=21). Alle Trainings-/dev-Bilder liegen bei 0,11–0,26
(Median 0,19), die S23-Testbilder fast alle am unteren Rand. [Vermutung] Die S23-Testbilder
sind zusätzlich durch das Kamera-Rauschfilter weicher als die iPhone-8-Bilder; das erklärt,
warum fast nur S23 einbricht, obwohl S23 im holdout unauffällig war (Bias −2,4).

**2. count_1000 hat effektiv n = 5, nicht 85.** [geprüft] Der Testsplit besteht aus fünf
Anordnungen (`count_1000-000`…`004`), je Art genau eine, mit 13–21 Aufnahmen (Takes). Die
Tabelle „pro Art und Kamera“ in RESULTS.md vergleicht also fünf Haufen, nicht fünf Arten:
„Hartweizen −64“ ist eine einzelne, überbelichtete, sehr schräge Anordnung, die auf beiden
Kameras einbricht (iPhone −24…−52). Art, Anordnung, Lichtsituation und Aufnahmewinkel sind
vollständig konfundiert. Aussagen wie „Roggen generalisiert schlecht“ sind daraus nicht
ableitbar (Roggen iPhone: 12 Bilder, Bias −7, 8 davon innerhalb ±3).

**3. Die Splits sind nach Dichte sortiert, und dev ist für YOLO nicht sauber.** [geprüft]
Schrittblöcke korrelieren mit der Kornzahl: holdout 170–482, dev 410–670, train 585–800 Körner.
Holdout misst also den leichtesten Fall (dünn besetzt) und ist zusätzlich within-session mit
denselben Anordnungen (plus Körner) im Training. Dev ist gleichzeitig YOLOs `val`-Split
(`data.yaml`), auf dem `best.pt`, `last.pt` und conf gewählt wurden; dev-MAE 3,0 ist daher leicht
optimistisch. Richtung ist trotzdem richtig: holdout 4,2 bestätigt grob. Erst neue, eigene
Fotos (andere Session, 1000 Körner, beide Winkel) messen wirklich.

## Weitere Audit-Befunde

- **Schwelle ist der eigentliche Sensor für Unschärfe.** [geprüft] Unter σ=3 fallen die
  Detektionen nicht weg, sie verlieren Konfidenz: conf 0,25 statt 0,4 bringt R von 0,957 auf
  0,989, dreht aber den Bias auf +8,7 (Duplikate, P 0,969); conf 0,15 explodiert (+1813).
  Unsharp-Mask (MAE 15,9) und Hochskalieren ×1,4 (13,8) helfen nur wenig. Eine feste conf ist
  also für wechselnde Schärfe zu starr; der Fix gehört ins Training, nicht in die Schwelle.
- **Label→Box-Ableitung:** Cluster-Körner bekommen die Median-Box des Bildes achsparallel,
  Orientierung ignoriert; bei diagonalen, langen Körnern (Hafer) sind Boxen zu klein/groß. Für
  Zählen akzeptabel, aber die NMS-Interaktion bei parallel liegenden Körnern ist ungeprüft.
  Ohne Albumentations-Installation hat Ultralytics **keine** Blur-Augmentierung (sonst Blur/
  MedianBlur nur p=0,01); `degrees=90, flipud/fliplr` decken Geometrie ab, nicht Optik.
- **Kachel-Ownership** (Mittellinien zwischen Nachbarkacheln) ist korrekt; Randkörner, die
  in beiden Kacheln nur halb sichtbar sind, werden einmal gezählt. Kein Kachelfehler sichtbar.
- **GeCo2-Befund stimmt** (R 0,64 bei Berührung); die Dichtekarte trennt aneinanderliegende
  Körner nicht. Nicht weiter verfolgen.
- **Protokoll:** PROTOCOL Regel 3 ist wichtig und wurde eingehalten; aber RESULTS.md sollte
  die Take-Struktur und n = 5 Anordnungen nennen, sonst liest die Jury 85 unabhängige Bilder.

## Literatur, soweit sie trägt

- Robustheit gegen Bildstörungen ist bei Detektoren ein bekanntes, gemessenes Problem; Blur
  ist eine der Hauptklassen in Benchmarks und synthetische Störungen im Training verbessern
  die Robustheit gegen natürliche (Premakumara et al. 2023, [arXiv 2304.10622](https://arxiv.org/pdf/2304.10622);
  Benchmark mit globaler/lokaler Defokus-Unschärfe: [arXiv 2210.15999](https://arxiv.org/pdf/2210.15999)).
  Begründet Idee 1.
- Test-Time Adaptation für Detektoren auf **einem** Bild ohne Quelldaten, mit IoU-Filter gegen
  unzuverlässige Pseudo-Labels (Ruan & Tang, CVPRW 2024, [Code](https://github.com/XiaoqianRuan1/IoU-filter));
  Mean-Teacher-TTA mit Foundation-Detektor (Gao et al., NeurIPS 2025, [Code](https://github.com/gaoyingjay/ttaod_foundation)).
  Für die Deadline zu schwer; nachher als Option, wenn neue Fotos zeigen, dass Augmentierung
  nicht reicht.
- Punktbasierte Zähler: APGCC (ECCV 2024, [arXiv 2405.10589](https://arxiv.org/pdf/2405.10589),
  Code AaronCIH/APGCC) stabilisiert P2PNets Punkt-Matching mit Hilfspunkten. Relevant, weil
  eure Labels Punkte sind und die Box-Ableitung entfällt; aber ein Punktzähler löst das
  Unschärfeproblem nicht von selbst. Erst nach Idee 1.
- Class-agnostic Counting: DAVE (CVPR 2024, [Paper](https://openaccess.thecvf.com/content/CVPR2024/html/Pelhan_DAVE_-_A_Detect-and-Verify_Paradigm_for_Low-Shot_Counting_CVPR_2024_paper.html)),
  GeCo (NeurIPS 2024, [Code](https://github.com/jerpelhan/geco)), CountGD++ (CVPR 2026,
  [arXiv 2512.23351](https://arxiv.org/pdf/2512.23351)). Eine Nachfolgearbeit zeigt, dass bei
  >300 Objekten pro Bild alle Methoden große Fehler machen und synthetisch dichte Daten kaum
  helfen ([arXiv 2602.12774](https://arxiv.org/pdf/2602.12774)). Deckt sich mit eurem GeCo2-
  Befund: dichte, berührende Objekte sind für Exemplar-Zähler kein gelöstes Problem.
- SAM 3 (ICLR 2026, [arXiv 2511.16719](https://arxiv.org/pdf/2511.16719)) zählt mit Konzept-
  Prompts, Benchmarks aber nur auf dünn besetzten Szenen (CountBench); keine Evidenz für
  1000 berührende Körner. Übersprungen lassen.
- Saatgut-Zählung: Domain Randomization mit ausgeschnittenen echten Körnern auf Hintergründen,
  YOLOv8 (Margapuri et al., [arXiv 2308.05846](https://arxiv.org/pdf/2308.05846)); Mobile-App
  mit klassischer und YOLOv5-Zählung, deren DL-Variante bei dichten Clustern inkonsistent war
  (Zu et al., Front. Plant Sci. 2025, [DOI](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1659781/full));
  SeedCounter nutzt das A4-Blatt als Maßstab und verlangt vom Nutzer parallele Blattkanten
  statt Perspektive zu korrigieren (Komyshev et al. 2016). Lehre: die Aufnahmeanleitung war
  immer Teil der Lösung.
- Global Wheat Head Detection 2021 ([Rothamsted](https://repository.rothamsted.ac.uk/id/eprint/31705)):
  einziger Multi-Domain-Detektionsbenchmark in WILDS; Domänenshift kommt aus Kamera, Ort,
  Dichte, und aggregierte mAP verdeckt Domänen-Ausreißer. Begründet Leave-one-session-out.

## Ideen, priorisiert (Nutzen/Aufwand)

1. **Blur-/Defokus-Augmentierung nachtrainieren** (heute machbar: Training dauerte 20 min).
   Hypothese: Modell lernt unscharfe Körner mit gleicher Konfidenz; count_1000-S23-Einbruch
   verschwindet weitgehend. Umsetzung: Albumentations `GaussianBlur(sigma 0,5–4)`,
   `Defocus`, `MotionBlur` mit p≈0,5, zusätzlich `ImageCompression`, leichte `GaussNoise`;
   optional pro Kachel vertikaler Schärfeverlauf (oben unscharf, unten scharf) als eigener
   Transform, das entspricht dem Testtag. Validierung nur auf dev: Tabelle oben erneut mit
   dem neuen Modell (`perturb.py`), Ziel σ=3 → MAE < 6 bei unverändertem Basis-MAE. Risiko:
   leichter Verlust auf scharfen Bildern (Bias +), Überzählen in Clustern; daher conf-Plateau
   auf dev neu prüfen. Dann **nicht** auf count_1000 nachjustieren, sondern eigene Fotos.
2. **Schärfe-Ampel in der App** (1 h, ohne Modell). Kantenschärfe pro Blattfünftel wie in
   `fable_scratch/a4`-Nachfolger messen; unter Schwelle (auf dev kalibriert, dort liegt das
   5-%-Quantil bei 0,11): „Hinterer Bereich unscharf, Foto von oben wiederholen“. Hypothese:
   fängt die −40…−108-Fälle vor dem Zählen ab. Validierung: auf dev künstlich geblurrte
   Bilder müssen rot werden, scharfe grün; auf neuen Fotos Precision der Warnung. Risiko:
   Maß ist kamera- und artabhängig (Hafer kontrastreicher); Schwelle konservativ wählen.
3. **Aufnahmeanleitung statt Perspektivkorrektur.** Die Marker-Homographie würde Geometrie
   korrigieren, die das Modell ohnehin verkraftet (Warp 0,45: MAE 5,4); die Unschärfe bleibt.
   Besser: Live-Hinweis „Blatt füllt den Rahmen, Kamera parallel“ über die Marker-/Blatt-Form
   (Trapezverhältnis aus 4 Ecken), plus Tipp auf Fokus auf die hintere Hälfte. 1–2 h im
   Kamera-UI. Risiko: Nutzer ignorieren; dann greift Idee 2.
4. **Schärfe-adaptive Konfidenzschwelle als Notnagel** (30 min): conf 0,4 bei scharf,
   0,3 bei weich; auf dev mit σ=2/3 Fehler-Minimum suchen. Bringt bei σ=3 MAE 22 → ~11,
   kippt aber in Überzählung. Nur als Zwischenlösung, wenn Idee 1 heute nicht durchläuft.
5. **Leave-one-session-out-Evaluation** (1 h CPU-Skripting, Training 4×20 min später). Vier
   Modelle, je eine Session S02–S05 ausgelassen; erst das zeigt, was ein neuer Tag kostet,
   und macht holdout als „leicht“ sichtbar. Für die Jury ehrlicher als within-session 4,2.
6. **Neue unverbrauchte Prüfung:** 10–20 eigene Fotos (1000 Körner abgezählt, beide Winkel,
   beide Kameras, eine Art nicht im Training) nach Abgabe; count_1000 nach Anordnung getrennt
   berichten (n = 5), nicht nach Art.
7. **Später:** Punktzähler (APGCC) auf denselben Kacheln mit Blur-Augmentierung; Mehrfach-
   Aufnahme in der App (2 Fotos, Abweichung > 2 % → warnen, ersetzt den „Prüfer“ aus
   ZWEITMEINUNG mit demselben Modell und ist ohne Zusatztraining messbar); TTA mit IoU-Filter
   nur, wenn neue Fotos trotz Augmentierung einbrechen.

Was ich **nicht** empfehle: Kacheln nach Kornmaßstab (Maßstab kostet nichts), GeCo2/SAM 3
weiterverfolgen, Farbaugmentierung als Hauptmaßnahme (HSV ist schon aktiv, Farbe war nicht
der Treiber).

## Quellen

- Premakumara et al., Enhancing object detection robustness: synthetic and natural perturbation, 2023, https://arxiv.org/pdf/2304.10622
- Beghdadi et al., Benchmarking object detection under image distortions, 2022, https://arxiv.org/pdf/2210.15999
- Ruan & Tang, Fully Test-time Adaptation for Object Detection, CVPRW 2024, https://openaccess.thecvf.com/content/CVPR2024W/MAT/html/Ruan_Fully_Test-time_Adaptation_for_Object_Detection_CVPRW_2024_paper.html
- Gao et al., Test-Time Adaptive Object Detection with Foundation Model, NeurIPS 2025, https://github.com/gaoyingjay/ttaod_foundation
- Chen et al., APGCC, ECCV 2024, https://arxiv.org/pdf/2405.10589
- Pelhan et al., DAVE, CVPR 2024; GeCo, NeurIPS 2024, https://github.com/jerpelhan/geco ; GeCo2 https://github.com/jerpelhan/GECO2
- Amini-Naieni et al., CountGD++, CVPR 2026, https://arxiv.org/pdf/2512.23351
- Bootstrapping MLLM for weakly-supervised class-agnostic counting (dichte Szenen >300), 2026, https://arxiv.org/pdf/2602.12774
- Carion et al., SAM 3, ICLR 2026, https://arxiv.org/pdf/2511.16719
- Margapuri et al., Seed kernel counting with domain randomization, 2023, https://arxiv.org/pdf/2308.05846
- Zu et al., Automated seed counting, Front. Plant Sci. 2025, https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2025.1659781/full
- Komyshev et al., SeedCounter, Front. Plant Sci. 2016, https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2016.01990/pdf
- David et al., Global Wheat Head Detection 2021, https://repository.rothamsted.ac.uk/id/eprint/31705
- Ultralytics Albumentations-Integration (Blur p=0,01), https://docs.ultralytics.com/integrations/albumentations
