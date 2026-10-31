# Saatgutrechner

Stand 27.10.2026, 19:20. Formeln, Vorgaben je Kultur, Einheiten, Rundung und ein
durchgerechnetes Beispiel. Quellen: Abschnitt 7. Stand der Prüfung durch Astra: Abschnitt 8.

## 1. Eingaben und Ergebnis

| Größe | Symbol | Einheit | Herkunft |
|---|---|---|---|
| gezählte Körner | n | Stück | Zählung (+ Korrekturen) |
| Gewicht dieser Körner | m | g | Waage, Eingabe |
| Tausendkorngewicht | TKG | g | berechnet |
| Saatstärke | S | keimfähige Körner/m² | Vorgabe je Kultur, änderbar (±10-Knöpfe) |
| Keimfähigkeit | KF | % | Sacketikett oder eigene Keimprobe, Eingabe |
| Feldaufgang | FA | % | nur Pflanzen-Modus, Vorgabe 90 % (siehe 2.3) |
| Aussaatmenge | A | kg/ha | **Ergebnis** |
| abzulegende Körner | K | Körner/m² | Nebenergebnis |

## 2. Formeln

### 2.1 TKG

```
TKG [g] = m [g] / n × 1000
```

Gewogen wird **die ganze Probe, wie sie auf dem Blatt liegt**, inklusive Bruch, Spreu und
Fremdbesatz; gezählt werden nur ganze Körner (`n`). Das ergibt **Gramm Partie pro 1000
ganze Körner**, genau die Größe für die Aussaatmenge: Die Drillmaschine bringt die Partie
mit Besatz aus, und der Besatz ist in Probe und Tonne gleich verteilt. Bewusst **kein**
Labor-TKG nach ISO; das liegt ohne Besatz etwas niedriger. Voraussetzung: Die Probe ist
repräsentativ und wird vollständig gewogen.

### 2.2 Aussaatmenge

Die Empfehlungen von Züchtern und Landesanstalten nennen die Saatstärke als
**keimfähige Körner/m²**. Damit:

```
K [Körner/m²]  = S / (KF/100)          (abzulegende Körner)
A [kg/ha]      = K × TKG [g] / 100     = S × TKG / KF
```

Herleitung der 100: K Körner/m² × TKG g/1000 Körner = K × TKG / 1000 g/m²;
× 10 000 m²/ha / 1000 g/kg = K × TKG / 100 kg/ha.

Das ist die Formel aus `docs/CHALLENGE.md` (dort „Körner/m²“ = keimfähige Körner/m²),
z. B. 200 × 45 / 95 = 94,7 kg/ha. Kein Feldaufgang im Standardmodus (2.3).

### 2.3 Feldaufgang: nur im Pflanzen-Modus

Empfehlungen in keimfähigen Körnern/m² enthalten die üblichen Auflaufverluste schon.
Wer zusätzlich Feldaufgang abzieht, sät zu dick. Darum:

- **Standard:** Feld „Saatstärke (keimfähige Körner/m²)“, kein Feldaufgang.
  `A = S × TKG / KF` (KF in %).
- **Pflanzen-Modus** (unter „Mehr“): Feld „Ziel-Pflanzen/m²“ und „Feldaufgang %“.
  Feldaufgang heißt hier: Anteil der **keimfähigen** Körner, die auflaufen
  (bedingter Feldaufgang). Auswahl „gut 95 % · normal 90 % · schwierig 85 %“, Vorgabe
  90 %, frei änderbar. `A = P × TKG × 100 / (KF × FA)`.
- Wer einen Feldaufgang bezogen auf **alle** gesäten Körner kennt (F), rechnet
  `A = P × TKG / F` ohne Keimfähigkeit. Das bietet die App nicht an; nur in der Hilfe
  erwähnen, damit niemand doppelt korrigiert.
- Der Modus wird pro Gerät gemerkt.

Varianten im Überblick (T = TKG in g, KF und FA in %):

| Eingegebenes Ziel | kg/ha |
|---|---|
| abgelegte Körner/m², K | K × T / 100 |
| keimfähige Körner/m², S | S × T / KF |
| Pflanzen/m², P, bedingter Feldaufgang FA | P × T × 100 / (KF × FA) |
| Pflanzen/m², P, Gesamt-Feldaufgang F | P × T / F |

### 2.4 Abdrehprobe (Ausblick, nicht im MVP)

```
Sollgewicht Abdrehprobe [kg] = A [kg/ha] × abgedrehte Fläche [ha]
```

Die Fläche nennt der Drillmaschinen-Hersteller (z. B. 1/10 ha, 1/40 ha).

## 3. Vorgaben je Kultur

Alle Werte in **keimfähigen Körnern/m²** bei normaler Saatzeit und ordentlichem
Saatbett. Das sind **Vorschläge zum Ändern**, keine Vorschriften: Sortenempfehlung des
Züchters geht vor. Die App zeigt die Spanne unter dem Feld und die Quelle in der Hilfe.
Kein pauschaler Zuschlag pro Woche Spätsaat; der Mensch wählt innerhalb der Spanne.

| Schlüssel | Anzeige | Vorgabe | Spanne | früh → spät | Quelle |
|---|---|---|---|---|---|
| `winterweizen` | Winterweizen | **320** | 250–400 | früh 250–300 · normal 310–350 · spät 360–400 | [LG Getreidefibel][lg] |
| `sommerweizen` | Sommerweizen | **390** | 350–450 | unteres Ende früh/gut, oberes spät | [Saaten-Union][su-sw], [Saatbau][sb-sw] |
| `winterdurum` | Winterdurum | **350** | 320–400 | früh 320–350 · spät 360–400 | [Saaten-Union Durum][su-d] |
| `sommerdurum` | Sommerdurum | **400** | 360–450 | früh 360–400 · spät 400–450 | [Saaten-Union Durum][su-d] |
| `wintergerste_mz` | Wintergerste mehrzeilig | **300** | 220–350 | früh 220–270 · normal 270–320 · spät 320–350 | [KWS Gerste][kws-g] |
| `wintergerste_zz` | Wintergerste zweizeilig | **310** | 230–380 | früh 230–280 · normal 280–340 · spät 340–380 | [KWS Gerste][kws-g] |
| `wintergerste_hyb` | Wintergerste Hybrid | **180** | 130–260 | normal 150–190 · spät 190–260, stark sortenabhängig | [Ströttmann 2026][str], [SY-Prospekt][sy] |
| `sommergerste` | Sommergerste | **300** | 275–375 | März 275–300 · April 300–350 · Ende April 350–375 | [KWS Gerste][kws-g] |
| `winterroggen_pop` | Winterroggen Population | **230** | 180–300 | niedrig früh/gut, hoch spät/schlecht | [KWS Roggen][kws-r] |
| `winterroggen_hyb` | Winterroggen Hybrid | **200** | 150–250 | Optimum meist 170–200 | [KWS Roggen][kws-r] |
| `hafer` | Hafer | **330** | 300–360 | früh säen; unteres Ende bei gutem Saatbett | [AELF Niederbayern 2025][aelf] |

TKG-Plausibilität (nur Hinweis, nie Grenze; Quelle ungeprüft, siehe 8):
Winterweizen 38,8–58,8 g, Sommerweizen 38,0–55,0, Wintergerste 44,5–67,0,
Sommergerste 47,0–65,0, Winterroggen 28,3–47,7, Hafer 36,0–52,8
(`wissensbank/01_Domain_Wissen.md` 4.1). Durum: keine Daten, keine Prüfung.

**Keimfähigkeit:** keine Vorgabe, Pflichtfeld für kg/ha. Hinweis „Steht auf dem
Sacketikett. Bei Nachbau: 100 Körner keimen lassen.“ Die gesetzlichen Mindestwerte
sind Zertifizierungsgrenzen, nicht die Keimfähigkeit der eigenen Partie; die App nutzt
sie nur für einen Hinweis bei niedrigen Werten:

| Kultur | Mindestkeimfähigkeit Z-Saatgut (SaatV Anl. 3) |
|---|---|
| Weichweizen, Gerste (inkl. Hybride) | 92 % (Z1), 85 % (Z2) |
| Durum, Hafer, Roggen | 85 % |
| Nackthafer, Nacktgerste | 75 % |

Hinweis bei KF < 85 %: „Niedrige Keimfähigkeit. Bitte Wert prüfen.“

Für die Nachvollziehbarkeit wird pro Probe gespeichert: Modus, Zielwert mit Einheit,
KF, ggf. FA und `formel_version` (`DATA.md` 2). Ein Gerätewechsel des Modus deutet
alte Proben nicht um.

## 4. Einheiten, Rundung, Anzeige

| Wert | Speichern | Anzeigen |
|---|---|---|
| Gewicht | wie eingegeben (0,1 g oder 0,01 g) | wie eingegeben |
| TKG | 0,1 g | 1 Nachkommastelle („46,3 g“) |
| Körner/m² (K) | ungerundet | ganze Zahl |
| Aussaatmenge | ungerundet rechnen, ganze kg/ha speichern | **ganze kg/ha** („172 kg/ha“) |
| Keimfähigkeit, Feldaufgang | ganze % (Kommastellen erlaubt) | ganze % |

Immer mit dem ungerundeten TKG weiterrechnen, erst die Anzeige runden.
Eingabegrenzen (sonst Hinweis, keine Sperre): KF 50–100 %, FA 50–100 %,
Saatstärke 100–600, Gewicht > 0.

## 5. Durchgerechnetes Beispiel

Winterweizen, Hänger 3. Zählung 982 Körner, Gewicht 45,5 g, Keimfähigkeit 95 %.

1. TKG = 45,5 / 982 × 1000 = **46,33 g** → Anzeige „46,3 g“.
2. Standardmodus, Saatstärke 320 keimfähige Körner/m², FA 100 %:
   K = 320 / 0,95 = 336,8 Körner/m²;
   A = 336,8 × 46,33 / 100 = **156,1 → 156 kg/ha**.
3. Pflanzen-Modus, 300 Pflanzen/m², FA 90 %:
   K = 300 / 0,95 / 0,90 = 350,9 Körner/m²;
   A = 350,9 × 46,33 / 100 = **162,6 → 163 kg/ha**.
4. Warum zählen sich lohnt: Mit dem Sorten-Durchschnitt 49,2 g statt 46,3 g wären es
   im Standardmodus 166 kg/ha, also 10 kg/ha (6 %) zu viel Saatgut.

Prüfwerte für Tests (Standardmodus):

| n | m [g] | KF [%] | S | TKG | A [kg/ha] |
|---|---|---|---|---|---|
| 1000 | 45,0 | 95 | 200 | 45,0 | 94,7 → 95 |
| 982 | 45,5 | 95 | 320 | 46,33 | 156 |
| 750 | 27,9 | 90 | 250 | 37,2 | 103 |

## 6. Code-Skizze

```python
def tkg(weight_g: float, count: int) -> float:
    return weight_g / count * 1000

def kerne_m2(saatstaerke: float, kf_pct: float, fa_pct: float = 100) -> float:
    return saatstaerke / (kf_pct / 100) / (fa_pct / 100)

def kg_ha(saatstaerke: float, tkg_g: float, kf_pct: float, fa_pct: float = 100) -> float:
    return kerne_m2(saatstaerke, kf_pct, fa_pct) * tkg_g / 100
```

## 7. Quellen

- Formel und „keimfähige Körner/m²“ als übliche Einheit: [LG Getreidefibel][lg]
- Feldaufgangsverluste 5–15 %, getrennt von Keimfähigkeit und Auswinterung:
  [LWK NRW Saatstärken][lwk], [LWK NRW Wintergerste][lwk-g]
- Mindestkeimfähigkeit: [Saatgutverordnung Anlage 3][saatv]
- Abdrehen statt Vertrauen in die Rechnung: [AMAZONE Downloads][amaz]

[lg]: https://www.lgseeds.de/fileadmin/user_upload/_Mediathek/LG_Getreidefibel.pdf
[su-sw]: https://www.saaten-union.de/downloadcenter?download=637&filepos=1
[sb-sw]: https://www.saatbau.at/uploads/files/Kulturfuehrung-Sommerweizen-11.pdf
[su-d]: https://www.saaten-union.de/downloadcenter?download=494&filepos=1
[kws-g]: https://www.kws.com/de/de/beratung/aussaat/gerste/
[kws-r]: https://www.kws.com/de/de/beratung/aussaat/roggen/
[str]: https://stroetmann-saat.de/fileadmin/user_upload/pdf/Agrarkatalog/Agrarkatalog_2026_2027_182S_Internet.pdf
[sy]: https://landwirtschaft.rw.net/medias/Sortenprospekt-2026.pdf
[aelf]: https://www.aelf-ds.bayern.de/mam/cms10/aelf-ds/landwirtschaft/dateien/versuchsberichtsheft_niederbayern__2025.pdf
[lwk]: https://www.landwirtschaftskammer.de/landwirtschaft/ackerbau/getreide/getreide-saatstaerken-pdf.pdf
[lwk-g]: https://www.landwirtschaftskammer.de/landwirtschaft/ackerbau/getreide/wintergerste/sortenwahl-wintergerste-pdf.pdf
[saatv]: https://www.gesetze-im-internet.de/saatv/anlage_3.html
[amaz]: https://amazone.de/de-de/service-support/fuer-landwirte-lohnunternehmer-und-kommunen/kundenservice/downloads/

Die Quellen hat Astra (GPT-6 Astra, Websuche) am 27.10. herausgesucht. Selbst geöffnet und
bestätigt (27.10., 19:30): **KWS Gerste** (Spannen wörtlich, ausdrücklich „keimf.
Körner/m²“; Hybridgerste steht dort nicht, kommt aus den Sortenprospekten) und
**SaatV Anlage 3** (Weichweizen/Gerste 92 % B und Z1, 85 % Z2; Durum, Hafer, Roggen
85 %; Fußnote 6: Nackthafer/Nacktgerste 75 %). Übrige Links ungeprüft.

## 8. Prüfung durch Astra (Runde 1)

- **Bestätigt:** Formel `S × TKG / KF` für keimfähige Körner/m², Herleitung, Rundung
  (ganze kg/ha, TKG 0,1 g, ganze Körner/m² sind sinnvolle Anzeige, keine Norm).
- **Korrigiert:** Mindestkeimfähigkeit ist für Weizen/Gerste Z1 92 %, nicht 85 %.
  Unser erster Entwurf rechnete Feldaufgang optional auf keimfähige Körner/m²; jetzt
  nur im Pflanzen-Modus. Vorgaben je Kultur aus Astras Quellen übernommen
  (Sommerweizen 390 statt 400, Winterdurum 350, Wintergerste mz 300, Hybrid 180,
  Sommergerste 300, Roggen Population 230). Feldaufgang-Vorgabe 90 % statt 85 %.
- **Hinweise an die Wissensbank** (nicht unser Bereich, an Leon weitergeben):
  `01_Domain_Wissen.md` 2/6 teilt durch Keimfähigkeit **und** einen Feldaufgang, der in
  §9 auf alle gesäten Körner bezogen ist (doppelte Korrektur); die
  ~140-Körner-Rechnung nutzt den Variationskoeffizienten zwischen Partien statt
  zwischen Einzelkörnern; Feuchte-Normierung ist für die Aussaat falsch (gesät wird mit
  aktueller Feuchte); „1 g TKG ≈ 2,1 dt/ha“ ist eine Rechenempfindlichkeit, kein Nutzen
  der App; die TKG-Perzentile (4.1) konnte Astra nicht öffnen (HTTP 403).
- **Begriff:** Die Handvoll ist keine „Abdrehprobe“. Abdrehprobe = Drillmaschine
  auslitern. In App und Pitch sauber trennen.
