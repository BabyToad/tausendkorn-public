1. **Die Diagnose „neue rosa Farbe/Markierung“ trägt nicht; Aufnahmequalität ist der stärkere erste Hebel.** Rosa Gerste, Marker und dichte Cluster existieren bereits im Training. Im schlechtesten Testfoto fällt besonders die starke Unschärfe hinten auf. Perspektive, Maßstab und Dichte bleiben plausible Mitursachen, sind aber nicht getrennt nachgewiesen.
2. **Die Genauigkeitszahlen stimmen, ihre Generalisierbarkeit ist sehr begrenzt.** 85 Testfotos entsprechen nur fünf `arrangement_id`, einer je Art; alle vier Trainingssessions kommen auch in Dev/Holdout vor. Zusätzlich liegen Trainings-Punktzahlen systematisch unter `count`. Kleine Summenfehler können Auslassungen und zusätzliche Treffer verdecken.
3. **Heute Aufnahmeführung, überprüfbare Fehlersignale und höchstens eine Dev-Ablation; danach bessere Daten/Labels vor neuer Architektur.** Weder eine pauschale Zählkorrektur noch selbstlernende Anpassung auf dem verbrauchten Test ist gerechtfertigt.

**Astra-Audit, 27.10.2026.** Selbst geprüft: verlangte Projektdokumente, YOLO-/GeCo2-Code und lokale GeCo2-Hilfsfunktionen, Trainingskonfiguration, Metadaten, 173 gespeicherte Ergebnis-JSONs; 49 Trainingsbilder zur Boxanalyse; visuell vier Train-, vier Dev- und zehn ausgewählte Testbilder sowie Originalauflösungs-Ausschnitte. Bilder über `load_image` mit EXIF-Korrektur. Keine neue Modellinferenz, kein Training, keine Commits. Ausgangs-HEAD: `4e60e67`; finale YOLO-JSONs nennen `d70b248`.

**Was die Daten tatsächlich zeigen**

Die nachgerechneten YOLO-MAE sind **3,04 / 4,20 / 25,39** für Dev/Holdout/Test. Test: Bias −20,12, Maximum |Fehler| 108. S23-MAE 36,48, iPhone 12,31. „iPhone nahe Holdout“ ist zu großzügig: Hartweizen-MAE 37,57; ein Roggenfoto liegt bei −60. Weizen überzählt auf beiden Geräten im Mittel. Die untrainierte Art Roggen ist somit nicht das größte Problem.

Die 49 Trainingsfotos stammen aus nur 38 Arrangements und vier Sessions; jede Session repräsentiert genau eine Art. Bild- oder Kachelzahl überschätzt damit die unabhängige Vielfalt. Im Test ist jede Sollzahl 1000: Ein konstanter Zähler wäre scheinbar perfekt. Variable neue Probenzahlen und Objektabgleich bleiben zwingend; Holdout-MAE ist ausschließlich ein Within-Session-Ergebnis.

**Visueller Gegenbeleg:** Trainingsfoto `S03-024_galaxy-s23_IMG_20260921_141843.jpg` enthält rosa Gerste und Marker; auch Trainings-Durum ist schräg fotografiert. Beim Test-Gerstenfoto `…122805.jpg` (−108) sind hintere Körner kleiner **und deutlich unschärfer**, vordere wesentlich schärfer. Gespeicherte Punkte lassen hinten sichtbare Körner aus. Derselbe Test-Arrangement-/Kamerablock reicht von −108 bis +5. Das stützt einen Aufnahmeeffekt, beweist aber weder einen reinen Geräteeffekt noch dessen genaue Ursache. Beizung selbst ist aus RGB nicht sicher bestimmbar. Mehr Körner pro Blatt bedeuten außerdem nicht automatisch höhere **lokale** Packungsdichte: Trainingshafer liegt bereits eng zusammen.

Eine Homographie kann Maßstab vereinheitlichen, aber verlorene Bildinformation nicht wiederherstellen. Dass „kein Kachelfehler“ vorliege, ist zu stark: CPU-Prüfung bestätigt lückenlose Kernfelder für alle sieben Dev-/Test-Bildformate. Unterschiedliche vorhergesagte Mittelpunkte desselben Korns können trotzdem beidseits einer Naht landen. Ohne Test-Punktlabels lässt sich die räumliche Auslassungsrate nicht vollständig messen.

**Labels, Pipeline und Messung**

- **Referenzkonflikt:** `len(kernel_points) − count` summiert sich auf Train zu −341 (Ø −6,96; Minimum −24), Dev −66, Holdout −65. Ursache – Punktannotation, Referenzzählung oder Sichtbarkeit – ist ungeklärt. Dev-YOLO hat gegen Punkte 147 FP und 62 FN, obwohl der Summenfehler gegen `count` nur +19 beträgt. FP können teilweise unannotierte echte Körner sein; keine automatische Bias-Korrektur daraus ableiten.
- **Grobe Boxaufsicht:** `point_boxes` verwendet trotz Otsu-Dokumentation tatsächlich `75%-Perzentil − 35`. Cluster erhalten eine bildweite Medianbox, auch Bruch/Fremdmaterial. Bei 32.526/35.000 Kornboxen entspricht die Größe der jeweils häufigsten Größe des Fotos; 13.948 Boxen enthalten mehrere annotierte Kornmittelpunkte. Überlappung ist nicht automatisch falsch, aber diese Ersatzgeometrie rechtfertigt keine präzisen Box-/NMS-Schlüsse. Nur 33 Bruch- und 180 Fremdpunkte stehen 35.000 Kornpunkten gegenüber; Ausschlusskompetenz ist damit schwach abgesichert.
- **Augmentierung existiert schon:** `args.yaml` enthält HSV, Rotation, `scale=0.5`, Mosaic; `perspective=0`, `shear=0`. Gezielt Schärfe-/Maßstabsrobustheit prüfen, statt unspezifisch „Farbe augmentieren“. `best.pt` nach Boxmetrik muss bei künstlichen Boxen nicht der beste Zähler sein; Auswahl von `last.pt` auf Dev ist zulässig.
- **GeCo2 ist exemplarunterstützt, nicht bedienungsfreies Zero-shot:** Exemplare werden anhand sämtlicher Wahrheits-Punkte als besonders isoliert ausgewählt. Das ist eine günstige Orakelhilfe, keine nachgewiesene Drei-Tipp-UX. Exemplarstreifen verändern zudem Bildkontext und Resize. Lokale Peak-Selektion plus nachgeschaltetes NMS können Kandidaten verlieren; R≈0,64 belegt die Schwäche dieses Versuchs, nicht aller exemplar- oder dichtebasierten Zähler.
- **Unsicherheit:** Greedy-Punktmatching mit globalem Radius ist kein maximaler bipartiter Abgleich. VLM-Selbstkonfidenz und Übereinstimmung zweier Zähler sind keine kalibrierte Fehlerwahrscheinlichkeit; beide können dieselben Körner übersehen. Gewichts-, Daten-, Paket- und Fremdcode-Hashes gehören gemeinsam ins Laufmanifest, nicht nur der `src`-Commit.

**Was aus der Literatur trägt**

**Direkte Punkte statt erfundener Boxen:** APGCC (ECCV 2024), eine Weiterentwicklung des P2PNet-Prinzips, stabilisiert Punktzuordnung und verbessert Zählung/Lokalisierung auf Crowd-Benchmarks. Das passt zur vorhandenen Aufsicht und zum editierbaren Overlay. Es ist kein Beleg für Korn-Generalisation; fehlende Labels bleiben fehlende Trainingsziele. Dichtesummen vermeiden Box-NMS, liefern aber nicht automatisch einzeln prüfbare Körner oder Bruchausschluss. [APGCC][apgcc]

**Generalisierung braucht mehr als Farbwechsel:** MPCount (CVPR 2024) kombiniert konsistente Merkmale unter photometrischer Augmentierung mit Speicher und zusätzlicher Patch-Klassifikation. URM (CVPR 2025) destilliert CLIP-Merkmale in Zählprototypen; im Few-shot-Transfer FSC-147→FSCD-LVIS erreicht es MAE 21,87 gegenüber 25,11 für die angepasste MPCount-Baseline. Das begründet einen späteren Merkmals-Lehrer, keine Übertragung dieser Zahlen auf Körner. [MPCount][mpcount], [URM][urm]

**Foundation-Zähler als kontrollierte Lehrer:** CountGD++ (CVPR 2026) unterstützt positive/negative Exemplare, passend zu Korn versus Bruch. Seine dichten Benchmarks enthalten adaptive Ausschnitte und externe 4×-Superauflösung; die 900-Query-Grenze bleibt relevant. Kein fairer „Modell allein“-Vergleich und kein Anlass, erzeugte Details als Wahrheit zu übernehmen. Erst menschlich geprüfte Trainings-Pseudolabels verwenden. [CountGD++][countgd]

**Test-Time Adaptation zurückstellen:** IoU-Filter (CVPR-Workshop 2024) untersucht Selbsttraining auf einzelnen Testbildern. Die Autoren beobachten Verschlechterung bei zu vielen Updates und Verlust richtiger Pseudolabels durch Filterung. Hier würden ausgerechnet fehlende Kornkandidaten keine zuverlässige Aufsicht liefern. Unveränderliche Mehrskalen-Inferenz ist davon zu unterscheiden. [IoU-Filter][tta]

**Agrarbelege kritisch lesen:** GrainNet (Plant Methods 2025) berichtet MAE 5,97, beschreibt aber die 8:2-Aufteilung **nach** Augmentierung; Trennung nach Ursprungsbild ist dort nicht belegt. Das ist ein Leakage-Risiko, kein Nachweis tatsächlicher Leakage. GrainSet (Scientific Data 2023) liefert >350.000 Einzelkornbilder für Qualitätsmerkmale, aber keine Validierung dichter Handyaufnahmen. Nutzen: Zusatzmaterial für Ausschlussklassen, mit expliziter Domänenprüfung. [GrainNet][grainnet], [GrainSet][grainset]

**Priorisierte Verbesserungen – Aufwand geschätzt, Nutzen ungemessen**

| Rang / Aufwand | Hypothese und Maßnahme | Saubere Prüfung / Risiko |
|---|---|---|
| **1 · 30–60 min** | Gerade von oben, Blatt bildfüllend, diffuse Beleuchtung, Schärfe vorne/hinten prüfen; Probe vollständig ausbreiten. Optional zwei getrennte Teilproben fotografieren und summieren. | Neue, vorab gezählte Proben mit unterschiedlichen Mengen, gepaart gute/schräge Aufnahme. Keine Auswahl nach Testergebnis. Risiko: Mehrarbeit; gleiche Gesamtprobe vollständig zählen und wiegen. |
| **2 · 60–120 min** | Maßstabstest: Baseline gegen genau eine vorab festgelegte kleinere Quellkachel, auf 1024 skaliert; alternativ Markierungs-/A4-Homographie, separat. | Nur 24 Dev-Bilder plus feste, zählerhaltende Blur-/Perspektivvarianten; MAE, Bias, FN/FP, schlechteste Art, Laufzeit. Randkörner korrekt transformieren. Risiko: vergrößerte Unschärfe, Interpolation, zusätzliche Nähte; keine Verbesserung garantiert. |
| **3 · 1–2 h Prototyp** | Schärfe je Blattregion und Raster-/Skalenabweichung markieren; Benutzer prüft Ausschnitte. VLM nur für ausgewählte Streitstellen. | Auf Dev Fehlererkennung und Anteil gewarnter Bilder messen; Warnschwellen danach einfrieren. Risiko: gemeinsame Blindstellen; „unauffällig“ bedeutet nicht „exakt“. |
| **4 · halber bis zwei Tage** | Train-Labels stratifiziert nachprüfen; saubere Clusterboxen/Masken, Nachbarpunkte als negative SAM-Prompts, Bruch/Fremdmaterial nachannotieren. Danach gezieltes Blur-/Perspektivtraining und maßstabserhaltendes Copy-Paste. | Lernaufsicht ausschließlich aus Train/neuem Trainingspool; Dev nur Auswahl. Kontrollierte Ablationen. Risiko: SAM verschmilzt Körner; Copy-Paste erzeugt unrealistische Schatten/Verdeckung. Keine ungeprüften Lehrerlabels als Hintergrundwahrheit. |
| **5 · mehrere Tage** | APGCC-artigen Punktkopf gegen verbesserten YOLO testen; Dichtekopf nur als zusätzliche Gegenprüfung. Anschließend Merkmalsdistillation nach URM-Prinzip. | Gleiche Trainingsdaten, identisches Auswahlbudget, neue Sessions. Risiko: 8-GB-/Windows-Portierung und erneut Überanpassung; kein Deadline-Wechsel. |

**Neue Evidenz planen:** Leave-one-session-out ist Entwicklungs-Stresstest und lässt hier zugleich eine Art aus; es isoliert keinen Sessioneffekt. Bereits betrachtete Testtag-Teilmengen bleiben verbraucht. Neue Tage, Partien und Arrangements vorab in Entwicklung/Abnahme trennen; Geräte, Winkel und Dichte innerhalb einer Partie gezielt variieren. Bei eingefrorener Pipeline neben MAE/Bias/±1/±5 das schlechteste Bild, Fehler je Arrangement und korrigierte versus automatische Ergebnisse getrennt berichten. 85 Fotos nicht als 85 unabhängige Proben behandeln. Bei −108/1000 steigt TKG bei gleicher Masse um **12,1 %**, nicht nur 10,8 %.

**Lokale Belege:** [Kennzahlen](../runs/audit/astra_evidence/summary.json), [Boxanalyse](../runs/audit/astra_evidence/box_stats.json), [Kachelabdeckung](../runs/audit/astra_evidence/coverage.json). Kontaktbögen und Bildausschnitte verbleiben im privaten Archiv. Test-Auswahl: größter absoluter Fehler je Art/Gerät, diagnostisch, nicht repräsentativ.

**Quellenliste – Primärquellen, recherchiert am 27.10.2026**

- Chen et al., **APGCC**, ECCV 2024: [Paper][apgcc], [Code und Checkpoint](https://github.com/AaronCIH/APGCC).
- Peng & Chan, **Single Domain Generalization for Crowd Counting / MPCount**, CVPR 2024: [Paper][mpcount], [Code](https://github.com/Shimmer93/MPCount).
- Chen et al., **Universal Representation Matching**, CVPR 2025: [Paper][urm], [Code](https://github.com/jbr97/URM).
- Amini-Naieni & Zisserman, **CountGD++**, CVPR 2026, Fassung vom 30.05.2026: [Paper, insbesondere Anhang C.3][countgd], [Code](https://github.com/niki-amini-naieni/CountGDPlusPlus).
- Ruan & Tang, **Fully Test-time Adaptation for Object Detection**, CVPR Workshops 2024: [Paper][tta], [Code](https://github.com/XiaoqianRuan1/IoU-filter).
- Wang et al., **GrainNet**, Plant Methods 21:44, 2025: [Paper][grainnet], [Code](https://github.com/1371530728/grainnet).
- Fan et al., **An annotated grain kernel image database for visual quality inspection**, Scientific Data 10:778, 2023: [Paper/Datenzugang][grainset].
- Pelhan et al., **GeCo2**, AAAI 2026: [Autorenrepository mit Paper und Gewichten](https://github.com/jerpelhan/GECO2); ergänzend zur lokalen Codeprüfung.

[apgcc]: https://arxiv.org/html/2405.10589v1
[mpcount]: https://openaccess.thecvf.com/content/CVPR2024/papers/Peng_Single_Domain_Generalization_for_Crowd_Counting_CVPR_2024_paper.pdf
[urm]: https://arxiv.org/html/2505.16778v1
[countgd]: https://arxiv.org/html/2512.23351v2
[tta]: https://openaccess.thecvf.com/content/CVPR2024W/MAT/papers/Ruan_Fully_Test-time_Adaptation_for_Object_Detection_CVPRW_2024_paper.pdf
[grainnet]: https://link.springer.com/article/10.1186/s13007-025-01363-y
[grainset]: https://www.nature.com/articles/s41597-023-02660-8
