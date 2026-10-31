# 01 – Domänenwissen: Tausendkornmasse und Getreidequalität

Stand: 27.10.2026 · Zweck: Fachlicher Hintergrund für Modellierung, Fragen an den Landwirt und Pitch.
Kennzeichnung: **[geprüft]** = aus gelesener Quelle (Links unten) · **[Fachwissen]** = gängiges Agrarwissen, vor Ort verifizieren · **[Annahme]** = Arbeitshypothese.

---

## 1. Definition und Bedeutung der TKM

- **Tausendkornmasse (TKM, engl. TGW/TKW):** Masse von 1000 Körnern in Gramm. Maß für Korngröße und Kornfüllung. [Fachwissen]
- **Einzelkornmasse** [mg] = TKM [g] (zahlenmäßig identisch: 45 g je 1000 Körner = 45 mg je Korn).
- **Körner pro Gramm** = 1000 / TKM (bei 45 g TKM ≈ 22 Körner/g).
- **Bezugsbasis beachten:** TKM wird je nach Labor/Betrieb auf Trockensubstanz (TS) oder bei tatsächlicher Kornfeuchte angegeben. In den gelesenen Quellen ist die Basis nicht angegeben. → **Beim Landwirt und im Datenset klären** (siehe Fragenkatalog in `04`).

### Wofür die TKM gebraucht wird

| Anwendung | Nutzen der TKM | Betroffene |
|---|---|---|
| Saatstärkenberechnung | Saatgutmenge (kg/ha) bei gewünschter Kornzahl pro m² | Landwirt, Lohnunternehmer |
| Ertragsprognose / Ertragskomponenten | Ertrag = Ähren/m² × Körner/Ähre × TKM | Landwirt, Berater, Versicherer |
| Sortenversuche / Züchtung | Phänotypisierung vieler Proben | Züchter, Landessortenversuche |
| Qualitätsbewertung | Indikator für Kornfüllung, Schmachtkorn, Stressjahre | Annahmestelle, Landhandel |
| Aufbereitung / Beizung / Pillierung | Dosierung, Maschineneinstellung (Siebweiten) | Saatgutaufbereiter |
| Mälzung / Vermahlung | Sortierung (Vollgerste), Ausmahlung | Mälzerei, Mühle |

---

## 2. Ertragsmodell und Rechenbeispiele

**Ertragskomponenten:** Bestandesdichte (Ähren/m²) × Kornzahl je Ähre × TKM.

| Größe | Beispiel |
|---|---|
| Ähren/m² | 600 |
| Körner/Ähre | 35 |
| TKM | 45 g |
| Ertrag | 600 × 35 × 45 / 1000 = 945 g/m² = **94,5 dt/ha** |

- Umrechnung: 1 g/m² = 10 kg/ha = 0,1 dt/ha.
- **Sensitivität:** +1 g TKM bei sonst gleichen Komponenten ≈ **+2,1 dt/ha** (≈ +2,2 %). Ein TKM-Messfehler von 5 % entspricht also ca. 4–5 dt/ha Fehler in der Ertragsprognose.
- **Kompensation:** Die Komponenten sind negativ korreliert. Wenige Körner je Ähre gehen oft mit höherer TKM einher. Die TKM allein erklärt den Ertrag nicht. [Fachwissen]

### Saatstärke

```
Körner/m²  = Zielpflanzen/m² / (Keimfähigkeit × Feldaufgang)
Saatstärke [kg/ha] = Körner/m² × TKM [g] / 100
```

Beispiel: 350 Pflanzen/m², TKM 45 g, Keimfähigkeit 95 %, Feldaufgang 100 % → **≈ 165,8 kg/ha**.
Wirkung der TKM-Streuung: 10 % TKM-Abweichung zwischen zwei Partien → 10 % Abweichung der Saatmenge (≈ 16 kg/ha bei 160 kg/ha). Wird die TKM der Partie nicht gemessen, drohen Über- oder Unterbestockung.

---

## 3. Einflussfaktoren auf die TKM [Fachwissen]

| Faktor | Wirkung | Bildanalyse-Bezug |
|---|---|---|
| **Sorte (genetisch)** | größter systematischer Anteil; Sortenunterschiede deutlich | Kornform/-größe als Sortenmerkmal |
| **Witterung in der Kornfüllung** (BBCH 71–89) | Hitze/Trockenheit → Notreife, Schmachtkorn, niedrige TKM; kühle, feuchte Füllungsphase → hohe TKM | Anteil kleiner/schmaler Körner |
| **Stickstoff / Nährstoffversorgung** | beeinflusst Kornzahl und Füllung | – |
| **Blattkrankheiten, Fusarium, Halmbasis** | verkürzen/stören Kornfüllung → Schmachtkörner | Verfärbung, Form, Größe |
| **Kornzahl je Ähre / Bestandesdichte** | Kompensation: weniger Körner → größere Körner | – |
| **Kornposition in der Ähre** | Basis- und Spitzenkörner leichter, Mittelkörner schwerer | Verteilungsform der Größen |
| **Standort, Boden, Wasserversorgung** | regionale Unterschiede | Metadaten (Feld, Region) |
| **Erntezeitpunkt / Kornfeuchte** | Feuchte verändert Masse und Größe | Feuchte erfassen oder korrigieren |
| **Aufbereitung** | Reinigung/Sortierung verschiebt Mittelwert nach oben | Siebfraktion |

---

## 4. Richtwerte

### 4.1 Typische TKM je Kultur [geprüft]

Quelle: Auswertung von Sortenprüfdaten des Bundessortenamts (2011–2018, Saatgutpartien), 5.–95. Perzentil. Saatgutpartien können leicht über Marktware liegen. Messbasis (Feuchte) nicht angegeben.

| Kultur | Mittelwert [g] | 5.–95. Perzentil [g] | Variationskoeffizient* |
|---|---|---|---|
| Winterweizen | 49,2 | 38,8 – 58,8 | ≈ 12 % |
| Sommerweizen | 47,0 | 38,0 – 55,0 | ≈ 10 % |
| Wintergerste | 55,5 | 44,5 – 67,0 | ≈ 12 % |
| Sommergerste | 56,4 | 47,0 – 65,0 | ≈ 10 % |
| Winterroggen | 37,3 | 28,3 – 47,7 | ≈ 16 % |
| Wintertriticale | 52,6 | 40,2 – 64,0 | ≈ 13 % |
| Hafer (Sommer) | 43,6 | 36,0 – 52,8 | ≈ 13 % |
| Winterraps | 5,58 | 4,00 – 7,84 | ≈ 20 % |
| Mais | 289,8 | 224,9 – 353,0 | ≈ 14 % |
| Futtererbse | 246,0 | 179,0 – 309,5 | ≈ 16 % |
| Soja | 202,3 | 154,0 – 240,0 | ≈ 14 % |

\*Variationskoeffizient zwischen Partien (eigene Berechnung aus Standardabweichung/Mittelwert der Quelle), nicht innerhalb einer Probe.
Diese Werte stecken als `TKM_REFERENCE_G` in `scripts/tkm_utils.py` (Plausibilitätsprüfung).

### 4.2 Beispiel regionale Qualitätswerte: Winterweizen Sachsen 2025 [geprüft]

Ortsmittel je Standort (Baruth, Christgrün, Forchheim, Nossen, Pommritz, Salbitz), Quelle: Qualitätsdaten Winterweizen 2025 auf landwirtschaft.sachsen.de:

| Merkmal | Einheit | Spanne der Ortsmittel |
|---|---|---|
| TKM (Stufe I) | g | 39,8 – 51,1 |
| TKM (Stufe II) | g | 42,8 – 54,6 |
| Hektolitergewicht | kg/hl | 77,2 – 79,5 |
| Rohprotein | % in TM | 10,9 – 13,3 |
| Fallzahl | s | 284 – 398 |
| Sedimentationswert | – | 37 – 53 |
| Stärke | % in TM | 67,5 – 69,0 |

Lesart: Zwischen Standorten im selben Jahr variiert die TKM um bis zu ca. 12 g. Wer nur eine Referenz-TKM annimmt, liegt bereits strukturell daneben.

### 4.3 Grobe Kornabmessungen [Fachwissen, grob]

| Kultur | Länge | Breite | Form |
|---|---|---|---|
| Weizen | 5–8 mm | 2,5–4 mm | länglich-oval, Furche |
| Gerste | 8–12 mm | 3–4,5 mm | spindelförmig, oft mit Spelzen |
| Roggen | 6–9 mm | 2–3 mm | schlank |
| Hafer | 10–14 mm | 2–3,5 mm | schlank, Spelzen |
| Raps | ca. 1,8–2,2 mm Ø | – | kugelig |
| Mais | 8–12 mm | 6–9 mm | flach-zahnförmig |

Bildanalyse-Konsequenz: Rundliche Körner (Raps, Erbsen, Soja) trennt man besser per Kreiserkennung; längliche (Weizen, Gerste, Roggen) per Ellipsenmodell und Watershed.

---

## 5. Messung der TKM in der Praxis

### 5.1 Verfahren

1. **Repräsentative Probe ziehen**, Besatz (Fremdbesatz, Bruchkorn, Spreu) entfernen bzw. getrennt erfassen.
2. **Körner zählen** (von Hand, Zählbrett, Kornzählgerät) und **wiegen**.
3. TKM = Masse / Anzahl × 1000.
4. **Wiederholungen:** gängige Praxis sind mehrere Teilproben (z. B. 8 × 100 Körner), Mittelwert und Streuung bilden. Die internationalen Saatgutprüfregeln (ISTA) beschreiben ein Wiederholungsverfahren mit Streuungsgrenze. [Fachwissen – konkrete Zahlen vor Ort verifizieren]
5. **Feuchte** messen und TKM auf Bezugsfeuchte umrechnen (Formel in Abschnitt 6).

### 5.2 Fehlerquellen

| Fehlerquelle | Wirkung | Gegenmaßnahme |
|---|---|---|
| Zu kleine Probe | hohe Streuung des Mittelwerts | Stichprobenumfang berechnen (Abschnitt 6) |
| Unrepräsentative Probe | Verzerrung durch Entmischung | Probenteiler, mehrere Einstiche |
| Zählfehler (manuell) | systematisch ± | Zählgerät oder Bildzählung |
| Feuchte nicht berücksichtigt | TKM ändert sich mit Feuchte | immer Feuchte mitführen |
| Besatz / Bruchkorn nicht entfernt | verfälscht Mittelwert | vorher reinigen oder separat zählen |
| Wiegefehler | gering bei Feinwaage (0,01 g) | Waage tarieren, Probe trocken |

---

## 6. Formelsammlung

| Größe | Formel | Funktion in `tkm_utils.py` |
|---|---|---|
| TKM aus Probe | `TKM = m[g] / n × 1000` | `tkm_from_sample` |
| Feuchtekorrektur | `TKM_ref = TKM × (1 − w/100) / (1 − w_ref/100)` | `tkm_to_reference_moisture` |
| Beispiel | 45 g bei 14 % → TS-Basis: 45 × 0,86 = **38,7 g** | – |
| Saatstärke | `kg/ha = Z / (KF × FA) × TKM / 100` | `seed_rate_kg_ha` |
| Ertrag | `dt/ha = Ähren/m² × Körner/Ähre × TKM / 10 000` | `yield_dt_ha` |
| Benötigte Kornzahl | `n = (z × CV / Fehler)²` mit z = 1,96 | `required_sample_size` |
| Beispiel | CV 12 %, gewünscht ±2 % → **n ≈ 139 Körner** | – |
| Siebfraktionen | Anteil je Breitenklasse (z. B. < 2,0 / 2,0–2,2 / 2,2–2,5 / 2,5–2,8 / ≥ 2,8 mm) | `sieve_fractions` |

Bedeutung für die Bildzählung: Schon ~140 vermessene Einzelkörner genügen statistisch für ±2 % Genauigkeit des Mittelwerts, sofern die Messung unverzerrt ist. Entscheidend ist also **Bias** (Skalierung, Segmentierung, Massebezug), nicht die Stichprobengröße.

---

## 7. Weitere Qualitätsmerkmale

| Merkmal | Bedeutung | Messung klassisch | Aus Bildern ableitbar? |
|---|---|---|---|
| **TKM** | Kornfüllung, Größe | Zählen + Wiegen | indirekt (Fläche → Masse), siehe `02` |
| **Hektolitergewicht (HLG)** | Schüttdichte, kg/hl; Hinweis auf Füllung und Besatz | Probenbehälter + Waage | nein (Schüttdichte), indirekt über Korngröße |
| **Rohprotein** | Backfähigkeit, Futterwert | NIR / Kjeldahl | nein direkt; schwacher Zusammenhang über Farbe/Härte |
| **Fallzahl** | Auswuchsindikator (niedrig = enzymaktiv) | Fallzahlgerät | nein; Auswuchs teils sichtbar (Keimling) |
| **Sedimentationswert** | Eiweißqualität (Backqualität) | Labortest | nein |
| **Besatz** (Fremdbesatz, Bruchkorn, Schmachtkorn, Auswuchs, Spelzen) | Abzüge bei Annahme | Siebanalyse, Handauslese | **ja**: Form, Größe, Farbe |
| **Kornverfärbungen / Fusarium** | Mykotoxinrisiko (DON), Abzüge | Labor (DON-Test) | **teilweise** (bleich-rosa Körner) |
| **Sortierung / Vollgerste** | Anteil > 2,5 mm bei Braugerste | Siebe | **ja**: Kornbreite |
| **Kornform / -einheitlichkeit** | Sorten-, Reinheitsmerkmal | Sichtprüfung | **ja** |

Typische Braugerste-Vorgaben (Vollgerste-Anteil hoch, Eiweiß niedrig) sind mälzereispezifisch; Zahlen vor Ort erfragen. [Fachwissen]
Für Brotweizen unterscheiden sich die Qualitätsgruppen (E/A/B/C) vor allem in Protein, Sedimentation und Fallzahl. Diese lassen sich nicht aus Bildern messen, nur indirekt vorhersagen.

---

## 8. Nutzenlogik für den Pitch [Annahme]

| Zielgruppe | Problem heute | Beitrag der Bildanalyse |
|---|---|---|
| Landwirt | TKM-Bestimmung manuell, langsam, nur stichprobenhaft | Smartphone-/Scannerfoto → Kornzahl, Größenverteilung, TKM-Schätzung in Sekunden |
| Landhandel / Annahmestelle | Eingangsprüfung zeitaufwendig, subjektiv | Standardisierte Sofortbewertung, dokumentierte Bilder |
| Saatgutaufbereitung | Saatstärke je Partie nötig | TKM je Partie → Saatmenge exakt |
| Züchtung / Versuchswesen | Tausende Proben | Hoher Durchsatz, reproduzierbar |

Quantifizierbare Argumente (mit eigenen Zahlen belegen, nicht mit Behauptungen):
- Zeit pro Probe: manuell (Zählen + Wiegen) vs. Bild + Wiegen.
- Genauigkeit: MAPE der TKM gegen Referenzmessung (aus unserer Evaluation).
- Ertragswirkung: 1 g TKM ≈ 2,1 dt/ha (Rechenbeispiel Abschnitt 2).

---

## 9. Glossar

| Begriff | Erklärung |
|---|---|
| TKM / TKG / TGW | Tausendkornmasse |
| BBCH | Entwicklungsskala (71–89: Fruchtentwicklung bis Vollreife) |
| Kornfüllungsphase | Zeit vom Ende der Blüte bis zur Reife; hier entsteht die Kornmasse |
| Notreife | vorzeitige Abreife durch Hitze/Trockenheit, führt zu Schmachtkorn |
| Schmachtkorn | unterentwickeltes, kleines, leichtes Korn |
| Bruchkorn | mechanisch beschädigtes Korn |
| Besatz | Fremdbestandteile (Unkrautsamen, Spreu, Steine, Bruch, Auswuchs) |
| Auswuchs | Keimung in der Ähre vor der Ernte |
| HLG | Hektolitergewicht in kg/hl |
| Fallzahl | Enzymaktivität-Indikator in Sekunden (Auswuchs) |
| Vollgerste | Siebfraktion > 2,5 mm bei Gerste |
| Keimfähigkeit | Anteil keimender Körner (%) |
| Feldaufgang | Anteil aufgelaufener Pflanzen je gesäte Körner |
| Z-Saatgut | zertifiziertes Saatgut |
| TS / TM | Trockensubstanz / Trockenmasse |
| DON | Deoxynivalenol, Fusarium-Mykotoxin |

---

## 10. Offene Annahmen, im Verlauf zu klären

- [ ] Auf welcher Feuchtebasis ist die TKM im Datenset angegeben?
- [ ] Welche Kultur(en) enthält das Datenset?
- [ ] Ist die TKM je Bild/Probe gemessen oder nur je Feld/Partie?
- [ ] Gibt es Referenzobjekt/Maßstab im Bild?
- [ ] Welche Genauigkeit gilt in der Praxis als „ausreichend“ (±1 g? ±3 %?)

---

## Quellen

- Variabilität der Tausendkornmassen von Saatgutpartien wichtiger Acker- und einiger Gartenbaukulturen (Kulturpflanzenjournal): <https://ojs.openagrar.de/index.php/Kulturpflanzenjournal/article/view/13333/13170>
- Sachsen (landwirtschaft.sachsen.de), Winterweizen 2025, Qualitätsdaten: <https://landwirtschaft.sachsen.de/download/Winterweizen_2025_SN_Quali_.pdf>
