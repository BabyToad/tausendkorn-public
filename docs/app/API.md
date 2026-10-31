# API, Betriebs-Integration und Agenten-Zugang

Stand 27.10.2026, abends (MCP-Teil gegen Primärquellen geprüft). Entwurf, **nicht implementiert**. Maschinenlesbar:
[`openapi.yaml`](openapi.yaml) (OpenAPI 3.1, validiert). Baut auf dem Stand von PR #13–#15
auf (Kopplung, `client_id`, Korrekturprotokoll, Unsicherheitsband, Abdrehprobe).
Recherche zu Betriebssystemen: Astra (GPT-6 Astra mit Websuche), Quellen in Abschnitt 3.
Kritik von Astra: Abschnitt 7.

## 0. Entscheidungen auf einen Blick

1. **Eine API für alle:** Web-App, Skripte, Hofsoftware und Agenten nutzen dieselbe REST-API
   unter `/api/v1`. Der MCP-Server ist eine dünne Hülle darüber, keine zweite Logik.
2. **Geld braucht die Freigabe eines Menschen, im Server erzwungen.** Ein Agent kann
   eine Zählung nur **beantragen**; ausgeführt wird sie erst, wenn ein Mensch sie in
   der App (gekoppeltes iPad oder Laptop mit Admin-PIN) freigibt. Ausnahme nur mit
   ausdrücklich vergebenem Autonomie-Budget pro Token. Budget wird beim Antrag
   reserviert, eine laufende Zählung pro Probe.
3. **Jede Zahl trägt Einheit und Herkunft der Unsicherheit** (`annahme` / `gemessen` /
   `keine`). Die API behauptet nie mehr Genauigkeit, als gemessen ist.
4. **Erster Integrationsschritt ist Datei, nicht Cloud:** CSV-Export (gibt es) und eine
   klare Ergebniskarte zum Eintippen am Terminal; danach ISO-XML für **eine** echte
   Drillmaschine prüfen. agrirouter und FMIS-Partnerschaften erst, wenn ein Betrieb sie will.
5. **Für den Pitch:** eine Folie „passt in Ihren Betrieb“ und, wenn tk-app Zeit hat, eine
   Live-Frage an einen Agenten: „Wie viel kg/ha für Hänger 3?“ (Abschnitt 6).

## 1. Ressourcen-Modell und REST-API

```
Betrieb (eine Installation = ein Betrieb)
 ├─ Partie  par_…   „Hänger 3“, Kultur, Sorte, Saison    ── gepooltes TKG, kg/ha
 │    └─ Probe  prb_…   Foto + Zählung + Eingaben + Ergebnis
 │         ├─ Zählversuche (unveränderlich)  ── Auftrag job_… (Warteschlange, Kosten)
 │         ├─ Prüfstellen (aus der Zählung)
 │         └─ Korrekturereignisse e=1,2,…  (wachsen nur)
 ├─ Sorte   (Freitext, Liste aus dem Verlauf, keine eigene Ressource)
 ├─ Kultur  (feste Liste mit Vorgaben und Quellen, SAATGUTRECHNER.md 3)
 ├─ Token   (Betriebs-Token mit Scopes)
 └─ Webhook whk_…
```

**Hänger** bleibt Freitext an der Probe (`haenger`), so wie Landwirte es sagen. Eine
**Partie** ist die stabile Klammer darüber, sobald mehrere Proben gemittelt werden
(ROADMAP 2.2). Der Server legt beim ersten Foto zu „Hänger 3 · RGT Reform · 2026/27“
automatisch eine Partie an und schlägt sie beim nächsten Foto vor; zusammenführen und
trennen geht später von Hand.

### Endpunkte (Kurzfassung, Details in `openapi.yaml`)

| Methode und Pfad | Zweck | Kostet Geld | Scope |
|---|---|---|---|
| `GET /proben` | suchen (Partie, Kultur, Sorte, Hänger, Status, seit), Cursor | nein | lesen |
| `POST /proben` | Foto + Kultur anlegen, **zählt nicht** | nein | eingaben |
| `GET /proben/{id}?punkte=true` | Probe mit Zählung, Prüfstellen, Ergebnis, ETag | nein | lesen |
| `PATCH /proben/{id}` | Gewicht, Keimfähigkeit, Saatstärke … ändern, `If-Match` | nein | eingaben |
| `DELETE /proben/{id}` | Papierkorb | nein | admin oder App-Sitzung |
| `POST /proben/{id}/zaehlungen` | Zählung beantragen → `202` Auftrag mit Status `freigabe_noetig` (oder direkt `wartet` bei Web-App/Autonomie-Budget) | **ja** | zaehlen |
| `POST /auftraege/{id}/freigabe` | Mensch gibt frei oder lehnt ab | – | nur App-Sitzung / Admin |
| `GET /auftraege/{id}` | Position, Fortschritt, Kosten | nein | lesen |
| `GET/POST /proben/{id}/korrekturen` | Ereignisprotokoll lesen, ein Ereignis anhängen | nein | lesen / korrigieren |
| `GET/POST /partien`, `GET /partien/{id}` | Partien, gepooltes TKG | nein | lesen / eingaben |
| `GET /partien/{id}/isoxml` | TaskData-ZIP für USB (später, heute `501`) | nein | lesen |
| `POST /rechner/aussaatmenge` | reiner Rechner, speichert nichts | nein | lesen |
| `GET /kulturen` | Vorgaben, Spannen, Quellen | nein | öffentlich |
| `GET /sorten` | bisher verwendete Sorten | nein | lesen |
| `GET /export/proben.csv` | CSV (Semikolon, Dezimalkomma, BOM) | nein | lesen |
| `GET/POST/DELETE /webhooks` | Ereignisse abonnieren, nur an freigegebene Ziele | nein | admin |
| `GET /konto` | Token, Scopes, Budget heute | nein | lesen |

Die heutigen Pfade `/api/samples…` aus PR #13 bleiben für die Web-App bestehen;
`/api/v1` ist die öffentliche, stabile Fläche. Umbau erst nach den laufenden PRs.

### Zählung und Ergebnis mit Unsicherheit

Jede Größe ist ein Objekt `Groesse`:

```json
"aussaatmenge": {"wert": 156.1, "einheit": "kg/ha", "unten": 154.5, "oben": 157.7, "basis": "annahme"}
```

| `basis` | Bedeutung | Wann |
|---|---|---|
| `als_fest` | als fest behandelt (eingegeben, nicht fehlerfrei) | Gewicht, Keimfähigkeit |
| `annahme` | feste Faustregel, **nicht gemessen** (heute ±1 %, mind. 3 Körner, PR #14) | Prüfstellen offen oder automatisch gezählt |
| `gemessen` | aus Validierung auf Holdout kalibriert | erst nach Messung |
| `keine` | nicht angebbar, `wert` kann trotzdem da sein | Foto mit Häufchen / Blatt abgeschnitten: `aussaatmenge.wert = null`, `zaehlung.aussaatmenge_gesperrt = true` |

Die Spanne der Kornzahl wirkt umgekehrt auf TKG und kg/ha: bei Kornzahl in [L, U] und
Gewicht m ist TKG ∈ [1000·m/U, 1000·m/L], kg/ha entsprechend. `basis` ist Pflicht;
`annahme` ist ein Faustregel-Szenario, kein Konfidenzintervall, `gemessen` trägt
zusätzlich `methode` und `abdeckung` (z. B. „95 % auf Holdout v1“).
„Prüfstellen bestätigt“ heißt nicht „alles geprüft“. `aussaatmenge_gesperrt` und
`basis: keine` gelten auch in Partie-Mittelwerten, CSV und Agenten-Antworten: eine
gesperrte Probe geht nicht in das gepoolte TKG ein.
`zaehlung.quelle` sagt, ob die Zahl `automatisch`, `pruefstellen_bestaetigt` oder
`korrigiert` ist, und `ergebnis.rechenweg` enthält den Rechenweg als deutschen Satz.
`ergebnis.fehlt` listet, was für das nächste Ergebnis fehlt (z. B. `keimfaehigkeit_pct`).
Ein Agent kann daraus selbst die nächste Frage an den Menschen ableiten.

### Auth

| Weg | Für wen | Wie |
|---|---|---|
| Kopplungs-Cookie | iPad/Browser im Hof-WLAN | wie PR #13: 6-stelliger Code oder QR, Cookie 400 Tage; darf Zählungen freigeben. Dazu später: Origin/Host-Prüfung, CSRF-Token, ablaufende Codes, widerrufbare Sitzungen |
| Admin-PIN | Betriebsleitung am Laptop | beim ersten Start gesetzt. Nötig für: Token erzeugen, Budget ändern, Webhook-Ziele freigeben. **Nicht** an eine IP gebunden. |
| Betriebs-Token (Bearer) | Skripte, Hofsoftware, MCP-Server, Agenten | mit Admin-PIN erzeugt: Name, Scopes, Ablaufdatum, optional Autonomie-Budget. Einmal angezeigt, als Hash gespeichert, widerrufbar. |

**Keine localhost-Ausnahme mehr für Schreiben, Zählen oder Verwaltung** (heute in PR
#13 vorhanden): Ein Agent auf dem Laptop ist auch „localhost“. Wer keine passende
Berechtigung mitschickt, bekommt 401/403, nie stillschweigend mehr Rechte. Gilt gleich
für alte `/api/samples…`-Pfade, Fotos, Markdown und MCP-Ressourcen.

Scopes: `lesen` · `eingaben` (Gewicht, Keimfähigkeit, Saatstärke, Notiz, Partie) ·
`korrigieren` (Punkte; nur Menschen in der App) · `zaehlen` (beantragen; kostet nach
Freigabe Geld) · `admin` (Token, Budget, Webhooks, Löschen). Empfehlung für Agenten:
`lesen` + `eingaben`, `zaehlen` nur auf Wunsch.

### Idempotenz, Nebenläufigkeit

- `POST /proben` und `POST /proben/{id}/zaehlungen` verlangen `Idempotency-Key`
  (UUID). Gültig je Betrieb + Token + Operation + Probe; aufbewahrt, bis der Auftrag
  abgeschlossen ist, mindestens 24 h. Gleicher Key → gleiche Antwort. Gleicher Key mit
  anderem Inhalt → `422 idempotenz_konflikt`. Die Web-App nutzt ihre `client_id`.
- **Eine aktive Zählung pro Probe**; ein zweiter Antrag → `409 schon_gezaehlt` bzw.
  der laufende Auftrag. Neu zählen nur bei Status `fehler` (wie `DATA.md` 4).
- Idempotenz-Eintrag, Auftrag und Budget-Reservierung werden **in einer Transaktion**
  gespeichert. Nach einem Absturz laufen offene Aufträge mit ihrer Reservierung weiter
  oder werden mit Abrechnung der Ist-Kosten beendet.
- **Alle** Änderungen (PATCH, Korrektur, Löschen, Neuzählen) verlangen
  `If-Match: "<rev>"` mit derselben Proben-Revision; veraltet → `412
  revision_veraltet`. Clients wiederholen einen 412 nicht automatisch.
- Korrekturen gehören zu einem `versuch_id`. Ein spät fertig werdender Zählversuch
  überschreibt keine geprüfte Probe.
- Änderungen an Eingaben werden mit Akteur (Token-Name/App), vorher und nachher
  protokolliert.

### Kosten und Limits

Jede Zählung kostet ≈ 0,30–0,55 USD (STATUS.md, Argon-Einführungspreis bis 30.11.).

| Grenze | Vorgabe | Antwort bei Überschreitung |
|---|---|---|
| Tagesbudget je Betrieb | 10 USD (Admin-PIN) | `402 budget_erschoepft`, `detail` nennt Stand und Rücksetzzeit |
| Reservierung | beim Antrag wird die **Obergrenze** des Auftrags reserviert, nicht die Schätzung; Fehlversuche und Wiederholungen zählen mit | `402`, wenn Reservierung nicht passt |
| Obergrenze je Auftrag | Server-Vorgabe 1,00 USD; Pipeline begrenzt jeden Modellaufruf | Auftrag bricht ab, Ist-Kosten werden gebucht |
| Autonomie-Budget je Token | 0 USD (Vorgabe) | über 0: Antrag ohne Freigabe bis zu diesem Betrag pro Tag |
| Zählungen je Token und Tag | 30 | `429 zu_viele_anfragen`, `Retry-After` |
| Warteschlange | ein Worker (PR #13) | `202` mit `position` |
| Upload | ≤ 30 MB, 800 px bis 60 MP | `413` / `400 foto_ungeeignet` |

Jede Antwort einer Zählung enthält Schätzung vorher und Ist-Kosten danach;
`GET /konto` zeigt Verbrauch heute. Batch-API (−50 %) als späterer Modus
`prioritaet: guenstig` (Ergebnis in Stunden statt Minuten).

### Webhooks

Ereignisse `probe.gezaehlt`, `probe.korrigiert`, `probe.fehlgeschlagen`.
Body enthält `id` (`evt_…`, zum Entdoppeln), `typ`, `zeit`, `probe_id`, `rev` und die
Probe ohne Punkte. Signatur `Tk-Signatur: t=<unix>,v1=<HMAC-SHA256("t." + gesendete Bytes)>`,
bei jeder Wiederholung mit neuem Zeitstempel; Empfänger prüft ±5 min.
Zustellung mindestens einmal, Wiederholung 1 min / 10 min / 1 h / 6 h, danach
deaktiviert und in `GET /webhooks` sichtbar. Reihenfolge nicht garantiert → Empfänger
entdoppelt per `id` und nimmt **je Probe** die höchste `rev`.

Webhooks schicken Betriebsdaten ins Netz, darum: nur Scope `admin`; Ziele (Host + Port)
vorher mit Admin-PIN freigeben; die aufgelöste IP bei jeder Verbindung gegen die
Freigabe prüfen; keine Weiterleitungen; Loopback, Metadaten- und Verwaltungsadressen
gesperrt; Zeit- und Größenlimits pro Zustellung.
Realistischer Nutzer heute: ein Skript, das in eine Tabelle schreibt, oder n8n/Home
Assistant auf dem Hof. Im LAN ohne öffentliche Adresse kommen Webhooks nur bei
Empfängern im selben Netz an.

### Fehler

`application/problem+json` (RFC 9457) mit stabilem `code`, deutschem `detail`, das sagt,
**was zu tun ist**, und bei Eingabefehlern `feld` und `erlaubt`:

```json
{"type": "https://tausendkorn.local/fehler/validierung", "title": "Ungültige Eingabe",
 "status": 422, "code": "validierung", "feld": "keimfaehigkeit_pct", "erlaubt": [0, 100],
 "detail": "Keimfähigkeit 150 % ist nicht möglich. Bitte einen Wert zwischen 1 und 100 angeben (steht auf dem Sacketikett)."}
```

## 2. Betriebs-Integration

### Was ein Ackerbaubetrieb real nutzt (Astra, geprüft 27.10.2026)

Marktanteile sind Herstellerangaben mit verschiedenen Bezugsgrößen, keine Erhebung.

| System | Bedeutung in DE | Zugang für eine kleine Dritt-App | Hürde |
|---|---|---|---|
| **NEXT Farming** (FarmFacts) | groß; BayWa nannte 2023 „30 % der Fläche“ (alt). Software jetzt bei AGCO | ISO-XML/Shapefile-Export auf USB, Aufträge über agrirouter. **Keine öffentliche Schreib-API gefunden** | Module kosten extra |
| **HELM Software** | „15.000+ Betriebe, ≈ ⅓ der Ackerfläche dokumentiert“ (Herstellerangabe) | ISODESK nimmt externe TaskData an (USB, Deere, Fendt). Öffentliche API/CSV-Import ungeprüft | unklar |
| **John Deere Operations Center** | verbreitet bei Deere-Flotten, Anteil ungeprüft | REST + OAuth2, Datei-Upload, Funkübertragung; Terminals nehmen Shapefile-Vorgaben, **nicht jedes nimmt ISO-XML** | Freigabe + Vertrag |
| **CLAAS connect** | CLAAS-Flotten | Online-File-Transfer-API: REST/OAuth2, ISO-XML-Aufträge an Maschinen | Partnerschaft |
| **365FarmNet** | ≈ 100.000 Registrierungen (mehrere Länder) | **wird am 30.11.2026 eingestellt** → nicht anbinden | – |
| **agrirouter** (DKE) | herstellerübergreifender Datentransport | REST + OAuth2; Implementierungsprüfung statt Zertifizierung; Testen gratis | Vertrag; als Vereinsmitglied 1.000 €/Jahr bei < 10 Mio. € **Agrar-Umsatz** (Mitgliedsbeitrag, gestaffelt nach Umsatz) |
| **xarvio** (BASF) | Anteil ungeprüft | REST/OAuth2, Saatkarten; `seedWeight` ist TKG **in kg** als Kultur/Saison-Angabe, keine geprüfte Steuerung je Partie | Zugang ungeprüft |
| **PTx Trimble / ADAPT** | Trimble-Flotten | Partner-APIs; ADAPT ist ein Software-Framework, kein Dienst | lizenzabhängig |

### Wie die Saatmenge heute an die Drillmaschine kommt

1. **Von Hand am Terminal** (kg/ha oder Körner/m²): dokumentierte Möglichkeit
   (wie verbreitet, ist ungeprüft; Leon fragen).
2. **USB-Stick** mit `TASKDATA/TASKDATA.XML` (ISO 11783-10) aus der Hofsoftware.
3. **Auftrag aus FMIS/Cloud** (agrirouter, Deere, CLAAS), am Terminal auswählen.

Danach wird nach Vorgabe des Drillmaschinen-Herstellers abgedreht. Keine Integration
ersetzt die Abdrehprobe.

### ISO-XML: was wir schreiben würden

Für einen festen Sollwert: Task (`TSK`) → Behandlungszone (`TZN`, als Standardzone
referenziert) → `ProcessDataVariable` (`PDV`) mit DDI und Rohwert, Produkt- und
Gerätezuordnung und `ValuePresentation`. Ob ein Terminal das annimmt, ist
terminalabhängig. ProductAllocation allein steuert noch nichts.
TC-BAS dokumentiert; ortsabhängige Vorgaben brauchen TC-GEO. Terminal und Gerät müssen
die Funktion und Lizenz haben.

| DDI (dez / hex) | Sollwert | Einheit | Auflösung | Beispiel |
|---|---|---|---|---|
| 6 / `0006` | Masse pro Fläche | mg/m² | 1 | 156 kg/ha → **15.600** |
| 11 / `000B` | Anzahl pro Fläche | Stück/m² | 0,001 | 337 Körner/m² → **337.000** |
| 1 / `0001` | Volumen pro Fläche | mm³/m² | 0,01 | nicht genutzt |

(1 kg/ha = 100 mg/m². DDIs direkt bei isobus.net geprüft, siehe Quellen.)

Welche DDI? Drillmaschinen für Getreide dosieren nach Masse (kg/ha), Einzelkorn nach
Anzahl. Wir schreiben **DDI 6** und legen TKG in die Produktbeschreibung. Ob das Terminal
das annimmt, ist **ungeprüft**: erst mit einer echten Kombination testen (z. B. Leons
Drille + Terminal).

### Reihenfolge

| Wann | Schritt | Status |
|---|---|---|
| **Pitch** | CSV-Export (gebaut; Import in FMIS ungeprüft) + Ergebniskarte zum Eintippen: Partie, Sorte, TKG, Keimfähigkeit, Saatstärke, **kg/ha**, Abdreh-Sollmenge, Zeit | da / Karte = Ergebnis-Screen |
| Wochen | ISO-XML-Export (DDI 6) für **eine** Terminal/Drillen-Kombination mit einem Betrieb testen: Anzeige, Produkt, Abdrehen, Ausführung | Idee |
| Monate | agrirouter-Endpunkt (deckt gemischte Flotten), dann Deere/CLAAS je nach Pilotbetrieb; FMIS (NEXT/HELM) oder xarvio als Partner für Dokumentation | Idee |
| nie | 365FarmNet (eingestellt) | – |

„Integration“ sagen wir erst, wenn Schreiben **und** Ausführen auf der Maschine gezeigt
sind. Bis dahin: „Export für …“.

## 3. Agenten- und LLM-Zugang

### Grundsätze

- **Stabile IDs** mit Präfix (`prb_`, `par_`, ULID), nie wiederverwendet. Agenten dürfen
  sie sich merken.
- **Einheit im Feldnamen** (`gewicht_g`, `keimfaehigkeit_pct`, `aussaatmenge_kg_ha` bzw.
  `Groesse.einheit`), Prozent immer 0–100.
- **Unsicherheit als Daten**, nicht als Fließtext (`basis`, `unten`, `oben`).
- **Fehler sagen, was zu tun ist**, in Deutsch, mit stabilem `code`.
- **Rechenweg mitliefern**, damit ein Agent seine Antwort begründen kann.
- **Nichts Teures ohne Zustimmung des Menschen**, erzwungen im Server (Freigabe in der
  App), nicht nur im Agenten. Kosten stehen in Tool-Beschreibung und Rückgabe; MCP
  hat dafür keine Standard-Annotation.
- **Ein Werkzeugsatz für alle Ökosysteme:** dieselben Tool-Namen und Schemas für MCP
  (Claude, ChatGPT), Anthropic-Tool-Use und OpenAI-Function-Calling, ohne Umbau.

### MCP-Server `tausendkorn` (Entwurf, gegen Primärquellen geprüft am 27.10.2026)

Python mit dem offiziellen MCP-SDK, Version fest pinnen. Neueste MCP-Revision ist
**2026-07-28** (zustandsloser Kern, `_meta` pro Anfrage, Rückfragen über
`input_required`/Elicitation). Welche Revision Claude- und OpenAI-Clients heute sprechen,
steht in deren Doku nicht als Tabelle → **vor dem Bau mit dem echten Client testen**,
nicht nach Datum wählen. Der MCP-Server hat keine eigene Logik, jedes Tool ruft die
REST-API auf.

#### Wo der Server laufen kann

| Client | Transport | Anmeldung | Freigabe-Mechanismus des Clients | Für uns |
|---|---|---|---|---|
| **Claude Desktop / Claude Code** auf dem Hof-Laptop | stdio (lokal) | Betriebs-Token aus Umgebungsvariable (MCP-Spec: stdio holt Zugangsdaten aus der Umgebung, nicht per OAuth) | Nutzer stellt je Tool „immer erlauben / fragen / blockieren“ ein | **jetzt**: einziger Weg ohne öffentliche Adresse |
| **Claude-Apps, eigener Connector** (claude.ai, Desktop, Cowork) | Remote-HTTP über das Internet | OAuth (oder feste Header) | Freigabe-Abfrage pro Tool-Aufruf, „immer erlauben“ möglich; im Research-Modus ruft Claude Tools ohne Rückfrage auf → Schreib-Tools dort abschalten | später |
| **Anthropic Messages API, MCP-Connector** (Beta `mcp-client-2025-11-20`) | Streamable HTTP oder SSE, **öffentlich erreichbar**, kein stdio | `authorization_token` (OAuth-Token, besorgt der Aufrufer) | **keine** Freigabe pro Aufruf; nur Tools ein-/ausschalten (`mcp_toolset`, Allow-/Denylist). Nur Tools, keine Ressourcen/Prompts | später, für Berater-/Hofsoftware-Integrationen |
| **OpenAI Responses API, Remote-MCP** | Streamable HTTP oder HTTP/SSE; privater Server über Secure MCP Tunnel (`tunnel_id`) | `authorization` (OAuth-Token, jede Anfrage neu), optional `headers` | `require_approval`: Standard ist Freigabe; `{"never": {"tool_names": [...]}}` für Lese-Tools; Ablauf `mcp_approval_request` → `mcp_approval_response` (`approve: true/false`) | später |
| **ChatGPT / OpenAI Apps SDK** | Remote-HTTP | OAuth | Host-Richtlinie; nutzt `structuredContent` sichtbar | später |

Folgen:

1. **Der Hof-Laptop ist für Cloud-Clients nicht erreichbar.** Remote-Nutzung braucht eine
   öffentliche HTTPS-Adresse oder einen Tunnel (OpenAI Secure MCP Tunnel, sonst ein
   eigener Tunnel), **und** dann MCP-konforme Autorisierung: Protected-Resource-Metadata
   (RFC 9728), Token nur mit unserem Server als Audience (RFC 8707), `WWW-Authenticate`
   mit `scope` bei 401/403, Origin-Prüfung. Ein festes Bearer-Token funktioniert
   technisch mit beiden Anbietern (`authorization_token` / `authorization`), erfüllt aber
   das MCP-OAuth-Profil nicht. Darum: erst stdio, Remote erst mit OAuth.
2. **Alles Wichtige muss über Tools gehen.** Der Anthropic-Connector kennt nur Tools.
   Ressourcen und Prompt-Vorlagen sind Zugaben für volle MCP-Clients wie Claude Desktop.
3. **Keine Client-Freigabe ist ein Beweis für die Zustimmung des Landwirts.** OpenAIs
   `mcp_approval_response` kann ein Programm schicken; der Anthropic-Connector fragt gar
   nicht; App-Einstellungen wie „immer erlauben“ sind Nutzerkomfort. Annotations sind
   laut Spec nur Hinweise, denen Clients bei fremden Servern nicht trauen sollen.
   → Die Freigabe in der Tausendkorn-App bleibt **die** Instanz (Abschnitt unten).

#### Regeln für Namen und Schemas (passen in alle drei Welten)

| Regel | Grund (Quelle) |
|---|---|
| Namen nur `a-z`, `0-9`, `_`, Präfix `tk_`, ≤ 64 Zeichen, keine Umlaute, kein Punkt | Anthropic verlangt `^[a-zA-Z0-9_-]{1,128}$`; MCP empfiehlt ASCII 1–128; OpenAI Chat Completions max. 64. Präfix gegen Namenskollisionen mehrerer Server (MCP-Spec, Anthropic-Empfehlung) |
| `title` und `description` deutsch, ausführlich (3–5 Sätze: was, wann, wann nicht, Einheiten, Kosten, Freigabe) | Anthropic: Beschreibung ist der wichtigste Faktor; MCP: UTF-8 |
| `inputSchema`: Wurzel `type: object`, `additionalProperties: false`, **alle** Felder in `required`, Optionales als `["typ", "null"]` | OpenAI Strict Mode verlangt das; MCP und Anthropic akzeptieren es |
| Kein `oneOf`/`allOf`/`if` und keine Varianten auf Wurzelebene; Varianten als **eigene Tools** | OpenAI Strict: Wurzel ohne `anyOf`, `allOf`/`if` nicht unterstützt, `oneOf` nicht in der Liste |
| Nur einfache Typen, `enum`, `format` höchstens `date-time`/`uuid`; Zahlengrenzen in die Beschreibung, **geprüft wird im Server** | Anthropic Strict unterstützt keine Zahlen-/Längengrenzen; Fehlerprüfung gehört ohnehin auf den Server |
| Ergebnis als `structuredContent` **und** gleiches JSON als Text; `outputSchema` angeben | MCP-Spec (Rückwärtskompatibilität); Apps SDK nutzt `structuredContent`; ob die API-Connectoren es auswerten, ist nicht dokumentiert |
| Fachliche Fehler als Tool-Ergebnis mit `isError: true` und deutschem Satz, was zu tun ist | MCP-Spec: Ausführungsfehler gehen ans Modell zur Selbstkorrektur |
| Annotations **immer alle vier** setzen | Spec-Vorgaben sind `destructiveHint: true`, `openWorldHint: true`; ohne Angabe sähe jedes Lese-Tool gefährlich aus |

Beispiel (gilt unverändert als MCP-`inputSchema`, Anthropic-`input_schema` und
OpenAI-`parameters`; `strict: true` setzt der jeweilige Client):

```json
{"name": "tk_zaehlung_beantragen",
 "title": "Zählung beantragen",
 "description": "Beantragt die Zählung einer Probe. Kostet NICHTS sofort: Die Zählung läuft erst, wenn ein Mensch sie in der Tausendkorn-App freigibt; danach kostet sie etwa 0,30–0,55 USD, höchstens die Obergrenze. Gib dem Menschen den Link aus freigabe_url und frage nach. Nutze für Wiederholungen dieselbe vorgang_id, sonst entsteht ein zweiter Antrag. Nicht für Proben mit fertiger Zählung.",
 "inputSchema": {"type": "object", "additionalProperties": false,
   "required": ["probe_id", "erwartete_rev", "vorgang_id", "max_kosten_usd"],
   "properties": {
     "probe_id": {"type": "string", "description": "z. B. prb_01JB8Z…"},
     "erwartete_rev": {"type": "integer", "description": "rev aus tk_probe_lesen"},
     "vorgang_id": {"type": "string", "format": "uuid", "description": "einmal pro Absicht erzeugen"},
     "max_kosten_usd": {"type": ["number", "null"], "description": "Obergrenze in USD, höchstens 1; null = Server-Vorgabe"}}},
 "annotations": {"readOnlyHint": false, "destructiveHint": false, "idempotentHint": true, "openWorldHint": true}}
```

#### Tools

Alle Parameter sind Pflicht; „| null“ heißt: `null` schicken, wenn egal.
Annotations: R = `readOnlyHint: true, openWorldHint: false`; sonst angegeben.

| Tool | Parameter | Rückgabe (`structuredContent`) | Seiteneffekt / Kosten | Annotations |
|---|---|---|---|---|
| `tk_kulturen_auflisten` | – | Kulturen mit Vorgaben, Spannen, Quellen | keine | R |
| `tk_partien_suchen` | `suche` (z. B. „Hänger 3“) \| null, `kultur` \| null, `sorte` \| null | Kandidaten mit `partie_id`, Bezeichnung, Sorte, Saison, Zahl der Proben | keine | R |
| `tk_saatmenge_fuer_partie` | `partie_id` | gepooltes TKG und kg/ha als `Groesse`, Rechenweg, Proben-IDs, `fehlt`, gesperrte Proben | keine | R |
| `tk_proben_suchen` | `partie_id`, `kultur`, `sorte`, `haenger`, `status`, `seit` (je \| null), `limit` (1–50), `cursor` \| null | Liste ohne Punkte + `naechster_cursor` | keine | R |
| `tk_probe_lesen` | `probe_id`, `mit_punkten` (bool) | Probe inkl. `rev`, Prüfstellen, `fehlt`, Rechenweg, App-Link | keine | R |
| `tk_aussaatmenge_berechnen` | `tkg_g`, `keimfaehigkeit_pct`, `saatstaerke_koerner_m2`, `kultur` \| null | kg/ha, Körner/m², Rechenweg, Hinweise | keine, speichert nichts | R |
| `tk_aussaatmenge_pflanzen_berechnen` | `tkg_g`, `keimfaehigkeit_pct`, `pflanzen_m2`, `feldaufgang_pct`, `kultur` \| null | wie oben | keine | R |
| `tk_eingaben_setzen` | `probe_id`, `erwartete_rev`, `aenderungen`: Liste von `{feld, aktion, wert}` mit `feld` ∈ {gewicht_g, keimfaehigkeit_pct, modus, saatstaerke_koerner_m2, pflanzen_m2, feldaufgang_pct, abdreh_flaeche_m2, sorte, haenger, notiz}, `aktion` ∈ {setzen, loeschen}, `wert` Zahl/Text \| null | Probe neu berechnet; bei veralteter `rev` Fehler mit aktueller `rev`, **kein** Neuversuch | überschreibt (protokolliert, wer) | `readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: false` |
| `tk_probe_anlegen` | `anhang_id` \| null, `import_datei` \| null (genau eins), `kultur`, `sorte` \| null, `haenger` \| null, `vorgang_id` | `probe_id`, Status `wartet` | legt an, **zählt nicht** | `readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false` |
| `tk_zaehlung_beantragen` | `probe_id`, `erwartete_rev`, `vorgang_id`, `max_kosten_usd` \| null | Auftrag: `status` (`freigabe_noetig` oder bei Autonomie-Budget `wartet`), `freigabe_url`, `freigabe_bis`, Schätzung, Obergrenze | **kostet nach Freigabe ≈ 0,30–0,55 USD** | `readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true` |
| `tk_auftrag_lesen` | `job_id` | Status, Position, Fortschritt, Kosten; bei `fertig` die Probe | keine | R |
| `tk_konto_lesen` | – | Token-Name, Scopes, Budget heute, Autonomie-Budget | keine | R |

Warum so:

- **`tk_eingaben_setzen` mit Änderungsliste:** REST unterscheidet „Feld fehlt = bleibt“
  und „`null` = löschen“. Mit OpenAI-Strict (alle Felder Pflicht) ginge der Unterschied
  verloren; die Liste macht ihn ausdrücklich.
- **Zwei Rechner-Tools statt `oneOf`:** strict-tauglich, und das Modell wählt den Modus
  über den Tool-Namen, nicht über ein verstecktes Feld.
- **`tk_partien_suchen` vor `tk_saatmenge_fuer_partie`:** „Hänger 3“ ist ein Wort, keine
  ID. Bei mehreren Treffern fragt der Agent nach, statt zu raten.
- **`tk_auftrag_lesen` statt Warten im Tool:** Zeitlimits der Hosts sind nicht dokumentiert;
  kurzes Abfragen ist sicher.
- **Fotos:** remote nur als `anhang_id` (vorher über `POST /anhaenge` hochgeladen),
  lokal als `import_datei` aus einem freigegebenen Ordner. Kein beliebiger Pfad.
- **Nicht als Tool:** Punkte korrigieren, Löschen, Zählung freigeben, Token, Webhooks.

`vorgang_id`: einmal pro Absicht erzeugen, bei Wiederholung gleich lassen; der
MCP-Server reicht sie als `Idempotency-Key` durch.

#### Freigabe kostenpflichtiger Zählungen in beiden Welten

Zwei Schichten, die sich ergänzen; **nur die zweite ist verbindlich**:

1. **Client-Schicht (Komfort, kein Beweis):** Lese-Tools ohne Rückfrage, alles andere
   mit Rückfrage. Konkret: OpenAI `require_approval: {"never": {"tool_names":
   ["tk_kulturen_auflisten", "tk_partien_suchen", "tk_saatmenge_fuer_partie",
   "tk_proben_suchen", "tk_probe_lesen", "tk_aussaatmenge_berechnen",
   "tk_aussaatmenge_pflanzen_berechnen", "tk_auftrag_lesen", "tk_konto_lesen"]}}`;
   Anthropic Messages API: Allowlist der Lese-Tools, Schreib-Tools nur einschalten, wenn
   die eigene Anwendung vorher fragt; Claude-Apps: Lese-Tools „immer erlauben“, Rest
   „fragen“, im Research-Modus Schreib-Tools aus.
2. **Server-Schicht (verbindlich):** `tk_zaehlung_beantragen` legt nur einen Antrag an.
   Stand PR #22: **Heute nicht erzwungen auf dem Laptop selbst (localhost):** Ein lokaler Prozess, auch ein lokal laufender Agent mit eigenem HTTP- oder Dateizugriff, kann über die alten Routen ohne Kopplung zählen lassen (`POST /api/samples/{id}/count`) und den Kopplungscode lesen (`GET /api/pairing`). Erzwungen ist die Freigabe für Geräte im LAN und für Agenten, die nur das Token bzw. die MCP-Tools haben: Der MCP-Server ruft ausschließlich `/api/v1` auf, prüft jede ID streng, und `tk_zaehlung_beantragen` zählt nie selbst. Die Admin-PIN, die das schließt, kommt nach dem Pitch (tk-app).
   Ausgeführt wird erst, wenn ein Mensch in der Tausendkorn-App freigibt (gekoppelte
   Sitzung oder Admin-PIN). Der Antrag ist gebunden an Token, Probe, Foto-Hash,
   Revision und Obergrenze, gilt 15 Minuten, ist einmal verwendbar. Freigeben kann kein
   Betriebs-Token und kein Tool. Die Rückgabe enthält `freigabe_url`; der Agent zeigt den
   Link und fragt später mit `tk_auftrag_lesen` nach.
3. **Elicitation nur als Zusatz:** Wo der Client MCP-Rückfragen kann
   (`input_required` mit URL-Modus), schickt der Server den Freigabe-Link als Rückfrage.
   Ein „accept“ des Clients setzt den Antrag **nicht** auf freigegeben; Abbruch oder
   fehlende Unterstützung führen nie zur Ausführung.
4. **Autonomie** gibt es nur als Budget am Token (Vorgabe 0), sichtbar in
   `tk_konto_lesen`. Das ist eine bewusste Entscheidung des Betriebs, keine
   Einzelfreigabe.

Ressourcen (nur für volle MCP-Clients): `tausendkorn://kulturen`,
`tausendkorn://probe/{id}`, `tausendkorn://partie/{id}`, `tausendkorn://doku`
(= `llms-full.txt`). Prompt-Vorlage `saatmenge_besprechen(partie_id)`.

### llms.txt und llms-full.txt (Exocortex-Konvention `LLM_FRIENDLY_WEB.md`)

- `/llms.txt`: wird vom Server als `text/plain` mit echtem 200 ausgeliefert (kein
  SPA-Fallback), deutsch, mit Datum/Commit im Kopf. **Aus den tatsächlich laufenden
  Fähigkeiten erzeugt**: Was nicht läuft (MCP, `/api/v1`, Markdown), steht dort nicht
  oder nur unter „Geplant“. Vorlage: [`llms.txt`](llms.txt).
- `/llms-full.txt`: **generiert, nicht von Hand** gepflegt. Ein Skript setzt beim Start
  zusammen: diese Datei (Abschnitte 1 und 3), `SAATGUTRECHNER.md` (Formeln, Vorgaben,
  Quellen), Kulturentabelle aus derselben Python-Konstante wie `/kulturen`, Fehlercodes
  aus `openapi.yaml`. Jede Sektion mit Quell-URL. So kann nichts auseinanderlaufen.
- `/openapi.json` (FastAPI erzeugt es), in `llms.txt` verlinkt.
- `robots.txt`: `Allow: /`, Kommentar auf `/llms.txt`, `Disallow: /api/` (kein Crawlen
  von Betriebsdaten). Die App läuft im Hof-WLAN; öffentlich wäre nur eine spätere
  Projektseite, die dieselben Dateien bekommt.
- Markdown-Geschwister: `GET /proben/{id}.md` (Ergebniskarte als Markdown) ist billig
  und für Agenten und zum Kopieren in Notizen nützlich.

## 4. Was der Pitch davon braucht

| Teil | Pitch 28.10. 12:00 | Aufwand | Wer |
|---|---|---|---|
| Folie „Passt in Ihren Betrieb“: Ergebnis → Terminal (heute von Hand), CSV, später ISO-XML/agrirouter, mit ehrlichem Status | ✅ | 15 min | Pitch |
| `llms.txt` + `robots.txt` im Server ausliefern | ✅ wenn tk-app 15 min hat | klein | tk-app |
| `GET /kulturen` + `POST /rechner/aussaatmenge` (keine Kosten, keine DB) | ✅ optional | 30 min | tk-app |
| MCP-Server, nur lesend: `tk_partien_suchen`, `tk_saatmenge_fuer_partie`, `tk_proben_suchen`, `tk_aussaatmenge_berechnen`, stdio, in Claude Desktop | **nicht im 5-Minuten-Pitch**, nur als Reserve für Rückfragen der Technikjury („Wie viel kg/ha für Hänger 3?“ mit Rechenweg und Spanne) | 45–60 min | tk-app nach seinen PRs, sonst gar nicht |
| Betriebs-Token, Scopes, Budget, Idempotency-Key, Webhooks, `/api/v1`-Umbau | später | mittel | – |
| ISO-XML-Export | später, braucht echte Drille zum Testen | mittel | – |
| agrirouter / FMIS | später | groß + Verträge | – |

Ehrlich im Pitch: „Die Zahl gehört heute von Hand ans Terminal. Export-Datei für die
Hofsoftware gibt es, ISO-XML für Ihre Drille testen wir als Nächstes.“

Der Pitch für Landwirt:innen bleibt: Problem → Foto mit markierten Körnern → eine
Korrektur → Gewicht/Keimfähigkeit → kg/ha → Verlauf, dann ein Satz zu Genauigkeit und
Grenzen und eine Zeile Integrations-Fahrplan. Eine Agenten-Demo liest nur vorhandene
Proben, zählt nichts; Claude Desktop selbst braucht trotzdem Internet.

## 5. Offene Fragen

- Welche Hofsoftware und welches Terminal nutzt Leon? (bestimmt den ISO-XML-Test)
- Stellt Leon die Saatmenge in kg/ha oder Körner/m² am Terminal ein?
- Dürfen Proben-Daten den Hof verlassen (Webhooks/Cloud)? Bisher geht nur das Foto an
  den Zähldienst.

## 6. Quellen

### Agenten-Ökosysteme (selbst geöffnet am 27.10.2026)

- MCP-Spezifikation, Revision 2026-07-28: [Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) (Namensregeln, `inputSchema`/`outputSchema`, `structuredContent`, `isError`, Mensch in der Schleife), [Schema/ToolAnnotations](https://modelcontextprotocol.io/specification/2026-07-28/schema#toolannotations) (Standardwerte, „nur Hinweise“; Elicitation-Formulare nur flache Felder), [Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) (OAuth 2.1, RFC 9728/8707, stdio: Zugangsdaten aus der Umgebung)
- Anthropic: [MCP-Connector der Messages API](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector) (Beta `mcp-client-2025-11-20`, nur Tools, Streamable HTTP/SSE, öffentlich, `authorization_token`, `mcp_toolset` mit Allow-/Denylist), [Tools definieren](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) (Name `^[a-zA-Z0-9_-]{1,128}$`, ausführliche Beschreibungen, Namensräume), [Custom Connectors in Claude](https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp) (Freigabe pro Tool, „immer erlauben“, Research-Modus ohne Rückfrage)
- OpenAI: [Remote-MCP in der Responses API](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) (`require_approval`, `mcp_approval_request`/`-response`, Streamable HTTP/SSE, `authorization`, Secure MCP Tunnel), [Structured Outputs, unterstützte Schemas](https://developers.openai.com/api/docs/guides/structured-outputs) (alle Felder `required`, `additionalProperties: false`, Wurzel Objekt ohne `anyOf`, kein `allOf`/`if`), [Function Calling, Strict Mode](https://developers.openai.com/api/docs/guides/function-calling)
- Zusätzlich von Astra mit Datum genannt (nicht selbst geöffnet): [Claude-Connector-Rechte](https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities), [Anthropic Strict Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use), [OpenAI Chat Completions, Namen ≤ 64](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [Apps SDK/Plugins-Referenz](https://developers.openai.com/plugins/reference), [MCP-Release 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/)

Nicht belegt: welche MCP-Revision die Anthropic- und OpenAI-Clients heute sprechen; ob die
API-Connectoren `structuredContent`/`outputSchema` auswerten; ob OpenAI-Remote-MCP
Nicht-ASCII-Namen annimmt. Darum ASCII-Namen und ein Test mit dem echten Client.

### Integration

- CLAAS/365FarmNet: [Pressemitteilung](https://www.claas.com/de-ch/presse/pressemitteilungen/2025-12-01-claas-skaliert-farm-management), [Einstellung](https://www.365farmnet.com/en/), [CLAAS OFT API](https://www.claas.com/en-eg/about-claas/partners/claas-api-partner-portal/online-file-transfer)
- NEXT Farming: [BayWa 2023](https://www.baywa.com/en/pressinformation/05223en_baywa_farmfacts), [Applikationskarten-Export](https://www.nextfarming.de/hilfe/applikationskarten-leitspuren-und-lenksysteme/next-applikationskartencenter-live/akc/), [Daten senden](https://www.nextfarming.de/hilfe/next-machine-management/verwendung-next-machine-management/daten-senden/), [CCI-Import](https://www.nextfarming.de/hilfe/terminal/cci-1200/)
- HELM: [Unternehmen](https://helm-software.de/about), [ISODESK](https://helm-software.de/produkte/isodesk)
- John Deere: [Operations Center](https://www.deere.de/de-de/produkte-loesungen/technologieloesungen/technologie-fuer-praezisionslandwirtschaft/operations-center), [Files API](https://developer.deere.com/dev-docs/files), [Freigabe](https://developer.deere.com/precision/get-started)
- agrirouter: [Überblick](https://agrirouter.com/en/docs), [API](https://agrirouter.com/en/docs/api), [Implementierungsprüfung](https://agrirouter.com/en/docs/integration/implementation-review), [Konditionen](https://agrirouter.com/en/docs/getting-started/business-and-legal)
- xarvio: [API](https://developer.xarvio.com/api.html) · PTx/ADAPT: [Entwickler](https://www.ptxag.com/us/en/partners/developers/), [Plugins](https://adaptframework.org/companies-supporting-adapt/)
- ISO-XML: [AMAZONE-Anleitung](https://downloadcenter.amazone.de/file/view/infoid/48887), [PDV-Schema (isoxml-js)](https://raw.githubusercontent.com/dev4Agriculture/isoxml-js/master/src/baseEntities/ProcessDataVariable.ts), [AEF](https://www.aef-online.org/aef-tour/), DDI [1](https://www.isobus.net/isobus/dDEntity/14) · [6](https://www.isobus.net/isobus/dDEntity/21) · [11](https://www.isobus.net/isobus/dDEntity/24)

Von uns selbst geöffnet: siehe Abschnitt 7.

## 7. Kritik von Astra

**Runde 1 (Recherche):** Abschnitt 2 und 6. Von uns selbst geöffnet und bestätigt:
DDI 6 bei isobus.net (mg/m², Auflösung 1) und die agrirouter-Konditionen
(Testen gratis, Implementierungsprüfung, Beitrag 1.000/2.000/3.000 € nach Agrar-Umsatz).

**Runde 2 (Gegenprüfung), alle übernommen außer wo unten vermerkt.** Die drei wichtigsten:

1. **Ein Bestätigungscode, den der Agent selbst bekommt, ist keine Zustimmung.** Der
   Agent könnte ihn sofort einsetzen oder REST direkt aufrufen. → Freigabe im Server
   durch eine App-Sitzung oder Admin-PIN; Autonomie nur als ausdrückliches Budget.
2. **localhost hebelt die Rechte aus**: Ein lokaler Agent hätte Tokens mit `zaehlen`
   erzeugen können. → Admin-PIN statt IP, keine localhost-Ausnahme fürs Schreiben.
3. **Budget und Idempotenz brauchen ein echtes Ausgabenmodell**: Reservierung der
   Obergrenze in derselben Transaktion wie Auftrag und Idempotenz-Eintrag, eine aktive
   Zählung pro Probe, Server-Obergrenze je Auftrag.

Außerdem übernommen: Webhooks nur `admin` mit freigegebenen Zielen und Signatur über
die gesendeten Bytes; einheitliche Revision für alle Änderungen, kein automatischer
Neuversuch bei 412, Korrekturen an `versuch_id` gebunden; `exakt` → `als_fest`,
`basis` Pflicht, Sperre auch in Partie/CSV/Agenten; Fotos im MCP nur als Anhang oder
aus freigegebenem Ordner (kein beliebiger Pfad); MCP-Annotationen mit Standardnamen,
HTTP-Transport erst mit MCP-Autorisierung; Integrationstabelle vorsichtiger formuliert
(„dokumentierte Möglichkeit“, TSK → TZN → PDV, agrirouter-Beitrag nach Agrar-Umsatz,
xarvio-`seedWeight` keine Partiesteuerung); MCP raus aus dem 5-Minuten-Pitch;
`llms.txt` nur mit laufenden Fähigkeiten.

**Runde 3 (Ökosysteme, Primärquellen 27.10.2026):** Astra und eigene Prüfung stimmen
überein: ASCII-Namen mit Präfix; strict-taugliche flache Schemas mit `null` statt
optionaler Felder; Varianten als eigene Tools; Annotationen vollständig setzen, aber
nicht darauf verlassen; Client-Freigaben (OpenAI `require_approval`, Claude-Rechte)
sind Komfort, die Freigabe in der App bleibt verbindlich. Neu von Astra:
`tk_eingaben_setzen` braucht eine Änderungsliste, weil Strict Mode „fehlt“ und
„löschen“ nicht mehr unterscheidet; Warten im Tool durch kurzes Abfragen ersetzen;
festes Bearer-Token funktioniert bei beiden Anbietern technisch, erfüllt aber das
MCP-OAuth-Profil nicht.

**Wo wir (noch) anderer Meinung sind:**

| Astra | Wir | Warum |
|---|---|---|
| HTTPS, CSRF, Origin-Prüfung, ablaufende Codes für das LAN | richtig, aber **nach** dem Pitch | Das iPad lädt Kamerafotos heute über http hoch (PR #13); ein selbstsigniertes Zertifikat auf dem iPad kostet die Demo. Bis dahin läuft die App nur im eigenen Hof-WLAN und zählt nur nach Freigabe. |
| Autonomes Zählen gar nicht oder nur mit voller Kostenbegrenzung | Autonomie-Budget pro Token, Vorgabe 0 | Ein Lohnunternehmer mit 40 Hängern will nicht 40-mal freigeben; die Entscheidung liegt beim Betrieb und ist sichtbar. |
| Korrekturen nur mit eigener Berechtigung | ja, und **nur Menschen in der App** | Ein Agent sieht das Foto nicht so, dass er Punkte sinnvoll setzen könnte; darum gibt es kein MCP-Tool dafür. |
