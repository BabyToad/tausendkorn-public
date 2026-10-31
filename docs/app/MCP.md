# API /api/v1 und MCP-Server: Bedienung

Stand 27.10.2026. Plan und Begründungen: [`API.md`](API.md), Schemas: [`openapi.yaml`](openapi.yaml).
Code: `app/api_v1.py` (REST), `app/mcp_server.py` (MCP, stdio), `app/tokens.py` (Tokens),
`app/kulturen.py` (Vorgaben je Kultur, eine Quelle für API, llms.txt und MCP).

## Was läuft

| Pfad | Zweck | Kostet Geld | Anmeldung |
|---|---|---|---|
| `GET /api/v1/kulturen` | Vorgaben, Spannen, Quellen | nein | keine |
| `POST /api/v1/rechner/aussaatmenge` | reiner Rechner, gleiche Formel wie die App | nein | keine |
| `GET /api/v1/proben`, `GET /api/v1/proben/{id}` | Proben mit Einheit, Spanne (`basis`), Rechenweg, `fehlt`, ETag | nein | `lesen` |
| `GET /api/v1/partien?suche=…`, `GET /api/v1/partien/{id}` | Partien der App (`partie_id`) finden; gepooltes TKG und kg/ha mit Spanne, Rechenweg | nein | `lesen` |
| `POST /api/v1/proben/{id}/zaehlungen` | Zählung **beantragen** (`Idempotency-Key`, `If-Match`) | nach Freigabe | `zaehlen` |
| `GET /api/v1/auftraege/{id}` | Stand des Auftrags | nein | `lesen` |
| `POST /api/v1/auftraege/{id}/freigabe` | freigeben/ablehnen | – | **nur gekoppelte App** |
| `GET /freigabe/{job_id}` | Freigabe-Seite fürs iPad | – | gekoppelte App |
| `GET /api/v1/konto` | Token, Scopes, Budget heute | nein | `lesen` |
| `/llms.txt`, `/robots.txt`, `/openapi.json` | für Agenten und Crawler | nein | keine |

Proben-IDs sind vorläufig `prb_<Zahl>` (die Zeilennummer), `rev` ist eine undurchsichtige
Zahl, die sich bei jeder Änderung der Probe ändert (nicht aufsteigend).

## Token erzeugen (am Laptop)

```bash
uv run python -m app.tokens erstellen --name claude-desktop --scopes lesen,zaehlen
```

`--mock` für die Demo-Daten, `liste`, `widerrufen tok_…`. Das Token wird einmal angezeigt
und nur als SHA-256 gespeichert (`data/app/api_tokens.json`). `--autonomie-usd` wird
gespeichert, ist aber **abgeschaltet** (`AUTONOMIE_AKTIV = False`), bis die Zählpipeline
eine Kostengrenze je Zählung wirklich einhält; bis dahin braucht jede Zählung eine Freigabe.

## MCP-Server in Claude Desktop / Claude Code

```json
{"mcpServers": {"tausendkorn": {
  "command": "uv",
  "args": ["run", "--directory", ".", "python", "-m", "app.mcp_server"],
  "env": {"TK_API_URL": "http://localhost:8000", "TK_API_TOKEN": "tk_…"}}}}
```

Die App muss laufen (`uv run python -m app`). Ohne Token gehen nur Kulturen und Rechner.

Tools nach API.md 3 (Präfix `tk_`, alle Parameter Pflicht, Optionales als `null`,
`additionalProperties: false`, Zahlengrenzen nur in der Beschreibung, alle vier Annotations):

| Tool | Kosten / Seiteneffekt | Annotations |
|---|---|---|
| `tk_kulturen_auflisten`, `tk_partien_suchen`, `tk_saatmenge_fuer_partie`, `tk_proben_suchen`, `tk_probe_lesen`, `tk_aussaatmenge_berechnen`, `tk_aussaatmenge_pflanzen_berechnen`, `tk_auftrag_lesen`, `tk_konto_lesen` | keine | `readOnlyHint: true`, `openWorldHint: false` |
| `tk_zaehlung_beantragen` | legt einen Antrag an; **kostet nach Freigabe meist 0,30–0,55 USD, harte Obergrenze fehlt noch** | `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: true` (mit `vorgang_id`), `openWorldHint: true` |

Noch nicht gebaut aus API.md 3: `tk_eingaben_setzen`, `tk_probe_anlegen`, Ressourcen
`tausendkorn://probe/{id}`, `…/partie/{id}`, `…/doku`, Elicitation mit Freigabe-Link.

Ressource `tausendkorn://kulturen`, Prompt `saatmenge_besprechen(partie)`.
Bewusst kein Tool: Punkte korrigieren, löschen, freigeben, Tokens.

## Freigabe einer Zählung

> **Heute nicht erzwungen auf dem Laptop selbst (localhost):** Ein lokaler Prozess, auch ein lokal laufender Agent mit eigenem HTTP- oder Dateizugriff, kann über die alten Routen ohne Kopplung zählen lassen (`POST /api/samples/{id}/count`) und den Kopplungscode lesen (`GET /api/pairing`). Erzwungen ist die Freigabe für Geräte im LAN und für Agenten, die nur das Token bzw. die MCP-Tools haben: Der MCP-Server ruft ausschließlich `/api/v1` auf, prüft jede ID streng, und `tk_zaehlung_beantragen` zählt nie selbst. Die Admin-PIN, die das schließt, kommt nach dem Pitch (tk-app).

1. Agent ruft `tk_zaehlung_beantragen` (bzw. `POST …/zaehlungen`) → Auftrag `freigabe_noetig`
   mit `freigabe_url`, 15 Minuten gültig, gebunden an Token, Probe und Foto.
2. Ein Mensch öffnet den Link auf dem **gekoppelten** iPad und tippt Freigeben oder Ablehnen.
   Der Server nimmt die Freigabe nur mit dem Kopplungs-Cookie und vom eigenen Ursprung an
   (`Origin`); ein Bearer-Token oder localhost ohne Cookie bekommt 403.
3. Erst dann startet die Zählung (eine gleichzeitig, wie in der App). Hat das Foto eine
   Warnung, steht sie auf der Seite; Freigeben heißt dann „trotzdem zählen“.

Grenzen: je Auftrag werden 1 USD reserviert, bis sein Ergebnis feststeht; das ist eine
Buchung, **keine** harte Grenze (die Pipeline bricht bei 1 USD nicht ab). 10 USD am Tag für
alle API-Zählungen, 30 Anträge je Token und Tag. Jeder Auftrag schreibt sein Ergebnis und
seine Kosten einmal fest (Kassenbuch in `api_jobs`); unbekannte Kosten eines Fehlschlags
zählen mit der vollen Reservierung (`kosten_unbekannt: true`). Abgerechnet wird, wenn der Zählversuch im Worker endet, nicht erst beim Abfragen; nach einem Neustart behält ein fertig gezählter Auftrag sein Ergebnis, ein unterbrochener wird mit voller Reservierung gebucht. Zählungen, die die App selbst startet, sind nicht enthalten.

## Bekannte Lücken (ehrlich)

- **Alte Routen vertrauen localhost** (PR #13): `POST /api/samples/{id}/count` startet von
  localhost aus ohne Anmeldung eine bezahlte Zählung, und `GET /api/pairing` zeigt localhost
  den Kopplungscode. Der MCP-Server prüft darum jede ID streng (nur `prb_<Zahl>`, `par_…`,
  `job_…`) und ruft nur Pfade unter `/api/v1` auf (Astra-Fund: `probe_id="../../samples/1/count?"`).
  Ein Agent mit **freiem** HTTP- oder Dateizugriff auf dem Laptop kann die alten Routen aber
  direkt nutzen. Wer also nicht nur das
  MCP-Token, sondern freien HTTP- oder Dateizugriff auf dem Laptop hat, kann sich selbst
  ein App-Cookie holen und freigeben. Gegen einen Agenten, der nur die MCP-Tools hat, hält
  die Freigabe. Abhilfe: Admin-PIN statt localhost für `/api/pairing` (API.md 1).
- `rev` deckt die ganze Probe ab: Ändert jemand in der App ein Gewicht, muss der Agent
  vor dem Antrag neu lesen (412). Die Freigabe prüft danach nur noch Foto und Status.
- Spanne bei `pruefstellen_bestaetigt`: die API nennt weiter die Faustregel (±1 %, mind.
  3 Körner) mit `basis: annahme`; die App zeigt nach dem Prüfen kein ± mehr.
- `aussaatmenge_gesperrt` gilt nur, wenn trotz Warnung „Häufchen“ oder „Blatt“ gezählt
  wurde. Die App selbst sperrt (noch) nicht.
- `max_kosten_usd` wird abgelehnt, sobald er nicht `null` ist (422): Die Pipeline kann heute
  nicht bei einem Betrag abbrechen, also tun wir nicht so.
- Eine Probe aus einer Partie, in der eine gesperrte Handvoll steckt, gibt keine
  Abdreh-Sollmenge aus (die App poolt alle gewogenen Handvoll); die Partie-Werte ohne die
  gesperrte Probe liefert `/api/v1/partien/{id}`.
- Mit einem echten Claude-Desktop- oder OpenAI-Client noch nicht getestet; getestet sind der
  In-Process-Client des SDK und ein echter stdio-Start gegen die laufende App (Mock).

## Nächste Schritte

Proben per API anlegen (die heutige Upload-Route startet sofort eine Zählung, darf also
nicht wiederverwendet werden), `PATCH` mit `If-Match`, Korrekturen, Partien als Ressource,
Admin-PIN (und damit Tokens/Budget in der App statt Kommandozeile), Webhooks, ISO-XML,
MCP über Streamable HTTP mit OAuth, `llms-full.txt` generiert.

## Quellen

- MCP Python SDK 2.3.0 (installiert, `mcp.server.mcpserver.MCPServer`, `ToolAnnotations`,
  `ToolError`, In-Memory-`Client` für Tests); Migrationshinweis
  <https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver>
- MCP-Spezifikation, Tools und Annotations: <https://modelcontextprotocol.io/specification>
