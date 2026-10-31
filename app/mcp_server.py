"""MCP-Server `tausendkorn` (stdio) für Claude Desktop, Claude Code und andere MCP-Clients.

    TK_API_URL=http://localhost:8000 TK_API_TOKEN=tk_… uv run python -m app.mcp_server

Dünne Hülle über /api/v1 (docs/app/API.md 3, docs/app/MCP.md): jedes Tool ruft die REST-API,
keine eigene Logik, kein Datenbankzugriff. Zählen kann ein Agent nur beantragen; ausgeführt
wird erst nach Freigabe durch einen Menschen in der App (im Server erzwungen).

Schemas nach API.md 3 „Regeln für Namen und Schemas“: Präfix tk_, alle Parameter Pflicht
(Optionales als null), additionalProperties false, keine Zahlengrenzen im Schema (prüft der
Server). stdout ist der Protokollkanal: Logs nur nach stderr.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from typing import Annotated, Any, Literal

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

log = logging.getLogger("tausendkorn.mcp")

LESEN = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
ANWEISUNGEN = """Tausendkorn zählt Getreidekörner auf einem A4-Foto und rechnet daraus TKG und Aussaatmenge (kg/ha).
Lesen und Rechnen kosten nichts. Eine Zählung kostet Geld und läuft erst, wenn ein Mensch sie in der App freigibt:
tk_zaehlung_beantragen gibt einen Freigabe-Link zurück, den du dem Menschen zeigst. Jede Zahl hat eine Einheit und
eine Spanne mit `basis` (annahme = Faustregel, nicht gemessen); nenne die Spanne mit. Die Aussaatmenge ersetzt
nicht das Abdrehen der Drillmaschine. Punkte korrigieren, löschen und freigeben kann nur der Mensch in der App."""


def D(text: str) -> Any:
    return Field(description=text)


ID_FORM = {"prb": r"prb_\d{1,12}", "par": r"par_[A-Za-z0-9-]{8,64}", "job": r"job_[0-9a-f]{16}"}


def ident(value: str, kind: str) -> str:
    """IDs go into URL paths: anything but the exact form could reach other routes (Astra #1)."""
    if not isinstance(value, str) or not re.fullmatch(ID_FORM[kind], value):
        raise ToolError(f"ungueltige_id: '{value}' ist keine gültige ID (Form {kind}_…). "
                        "IDs aus den Antworten der anderen Tools übernehmen.")
    return value


def make_server(client: httpx.AsyncClient) -> MCPServer:
    mcp = MCPServer("tausendkorn", title="Tausendkorn", instructions=ANWEISUNGEN, version="0.1.0")

    async def call(method: str, path: str, **kw) -> dict:
        try:
            if not re.fullmatch(r"/[A-Za-z0-9_/-]*", path):
                raise ToolError("ungueltige_id: unzulässige Zeichen im Pfad.")
            r = await client.request(method, f"/api/v1{path}", **kw)
        except httpx.HTTPError as e:
            raise ToolError(f"Tausendkorn-Server nicht erreichbar ({type(e).__name__}). Läuft die App "
                            f"(uv run python -m app) und stimmt TK_API_URL?") from None
        if r.status_code >= 400:
            try:
                p = r.json()
            except ValueError:
                raise ToolError(f"HTTP {r.status_code}: {r.text[:300]}") from None
            raise ToolError(f"{p.get('code', r.status_code)}: {p.get('detail', '')}")
        return r.json()

    def clean(d: dict) -> dict:
        return {k: v for k, v in d.items() if v is not None}

    @mcp.tool(title="Kulturen und Saatstärke-Vorgaben", annotations=LESEN)
    async def tk_kulturen_auflisten() -> dict[str, Any]:
        """Listet alle Kulturen mit Saatstärke-Vorgabe und üblicher Spanne in keimfähigen Körnern/m², plausiblem
        TKG in Gramm, Mindestkeimfähigkeit und Quellen. Nutze das, bevor du eine Saatstärke vorschlägst.
        Kostet nichts, ändert nichts."""
        return await call("GET", "/kulturen")

    @mcp.tool(title="Partien suchen", annotations=LESEN)
    async def tk_partien_suchen(
        suche: Annotated[str | None, D("Freitext wie 'Hänger 3'; trifft Hänger, Sorte oder Kultur. null = alle")],
        kultur: Annotated[str | None, D("Kultur-Schlüssel oder Name, z. B. winterweizen; null = egal")],
        sorte: Annotated[str | None, D("Sorte, z. B. 'RGT Reform'; null = egal")],
    ) -> dict[str, Any]:
        """Sucht Partien (eine oder mehrere gezählte Handvoll derselben Ware) und gibt partie_id, Bezeichnung,
        Sorte und Proben zurück. „Hänger 3“ ist ein Wort, keine ID: Bei mehreren Treffern (eindeutig = false)
        den Menschen fragen, welche Partie gemeint ist, nicht raten. Kostet nichts."""
        return await call("GET", "/partien", params=clean(dict(suche=suche, kultur=kultur, sorte=sorte)))

    @mcp.tool(title="Saatmenge für eine Partie", annotations=LESEN)
    async def tk_saatmenge_fuer_partie(
        partie_id: Annotated[str, D("ID wie par_… aus tk_partien_suchen")],
    ) -> dict[str, Any]:
        """Gepooltes TKG (1000 × Σ Gewicht ÷ Σ Körner) und Aussaatmenge in kg/ha einer Partie, jeweils mit Spanne
        und `basis`, Rechenweg, verwendeten und gesperrten Proben und was fehlt (`fehlt`). Nenne kg/ha als ganze
        Zahl mit Spanne und erinnere ans Abdrehen. Kostet nichts."""
        return await call("GET", f"/partien/{ident(partie_id, 'par')}")

    @mcp.tool(title="Proben suchen", annotations=LESEN)
    async def tk_proben_suchen(
        partie_id: Annotated[str | None, D("nur Proben dieser Partie (par_…); null = alle")],
        kultur: Annotated[str | None, D("Kultur-Schlüssel oder Name; null = egal")],
        sorte: Annotated[str | None, D("Sorte; null = egal")],
        haenger: Annotated[str | None, D("Hänger genau wie in der App; null = egal")],
        status: Annotated[Literal["wartet", "zaehlt", "pruefen", "fertig", "fehler"] | None,
                          D("nur Proben mit diesem Status; null = alle")],
        seit: Annotated[str | None, D("nur Proben ab diesem Datum, YYYY-MM-DD; null = alle")],
        limit: Annotated[int, D("höchstens so viele, 1 bis 50")],
        cursor: Annotated[str | None, D("naechster_cursor der vorigen Antwort; null = von vorn")],
    ) -> dict[str, Any]:
        """Sucht Proben, neueste zuerst: ID, Status, Kornzahl, TKG und kg/ha je mit Einheit und Spanne, ohne
        Kornkoordinaten. Filter sind exakt (Groß-/Kleinschreibung egal). Für die Saatmenge einer Partie besser
        tk_saatmenge_fuer_partie. Kostet nichts."""
        return await call("GET", "/proben", params=clean(dict(partie_id=partie_id, kultur=kultur, sorte=sorte,
                                                               haenger=haenger, status=status, seit=seit,
                                                               limit=limit, cursor=cursor)))

    @mcp.tool(title="Probe lesen", annotations=LESEN)
    async def tk_probe_lesen(
        probe_id: Annotated[str, D("ID wie prb_12")],
        mit_punkten: Annotated[bool, D("Koordinaten aller Körner mitliefern (groß, meist false)")],
    ) -> dict[str, Any]:
        """Eine Probe komplett: Eingaben, Zählung mit Prüfstellen, Ergebnis mit Spannen, Rechenweg, was fehlt
        (`ergebnis.fehlt`), Revision `rev` (für tk_zaehlung_beantragen) und Link in die App. Kostet nichts."""
        return await call("GET", f"/proben/{ident(probe_id, 'prb')}", params={"punkte": str(mit_punkten).lower()})

    @mcp.tool(title="Aussaatmenge berechnen (keimfähige Körner/m²)", annotations=LESEN)
    async def tk_aussaatmenge_berechnen(
        tkg_g: Annotated[float, D("Tausendkorngewicht in Gramm, größer 0")],
        keimfaehigkeit_pct: Annotated[float, D("Keimfähigkeit in Prozent, 0 bis 100 (95 = 95 %)")],
        saatstaerke_koerner_m2: Annotated[float, D("Ziel in keimfähigen Körnern/m², z. B. 320")],
        kultur: Annotated[str | None, D("Kultur-Schlüssel für Hinweise zur üblichen Spanne; null = ohne")],
    ) -> dict[str, Any]:
        """Reiner Rechner (Standard): kg/ha = Saatstärke × TKG ÷ Keimfähigkeit. Gibt kg/ha, Körner/m², Rechenweg
        und Hinweise (z. B. außerhalb der üblichen Spanne) zurück. Speichert nichts, kostet nichts."""
        return await call("POST", "/rechner/aussaatmenge", json=clean(dict(
            modus="keimfaehig", tkg_g=tkg_g, keimfaehigkeit_pct=keimfaehigkeit_pct,
            saatstaerke_koerner_m2=saatstaerke_koerner_m2, kultur=kultur)))

    @mcp.tool(title="Aussaatmenge berechnen (Pflanzen/m²)", annotations=LESEN)
    async def tk_aussaatmenge_pflanzen_berechnen(
        tkg_g: Annotated[float, D("Tausendkorngewicht in Gramm, größer 0")],
        keimfaehigkeit_pct: Annotated[float, D("Keimfähigkeit in Prozent, 0 bis 100")],
        pflanzen_m2: Annotated[float, D("Ziel in Pflanzen/m²")],
        feldaufgang_pct: Annotated[float, D("erwarteter Feldaufgang in Prozent, 0 bis 100")],
        kultur: Annotated[str | None, D("Kultur-Schlüssel für Hinweise; null = ohne")],
    ) -> dict[str, Any]:
        """Reiner Rechner für ein Ziel in Pflanzen/m²: kg/ha = Pflanzen × TKG × 100 ÷ (Keimfähigkeit ×
        Feldaufgang). Speichert nichts, kostet nichts."""
        return await call("POST", "/rechner/aussaatmenge", json=clean(dict(
            modus="pflanzen", tkg_g=tkg_g, keimfaehigkeit_pct=keimfaehigkeit_pct, pflanzen_m2=pflanzen_m2,
            feldaufgang_pct=feldaufgang_pct, kultur=kultur)))

    @mcp.tool(title="Zählung beantragen (kostet nach Freigabe Geld)",
              annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True,
                                          openWorldHint=True))
    async def tk_zaehlung_beantragen(
        probe_id: Annotated[str, D("ID wie prb_12; die Probe hat ein Foto und ist noch nicht gezählt")],
        erwartete_rev: Annotated[int, D("Feld rev aus tk_probe_lesen; schützt vor veralteten Daten")],
        vorgang_id: Annotated[str, D("einmal pro Absicht erzeugen (z. B. UUID); bei Wiederholung dieselbe")],
        max_kosten_usd: Annotated[float | None, D("noch nicht unterstützt: immer null schicken")],
    ) -> dict[str, Any]:
        """Beantragt die Zählung einer Probe. Kostet NICHTS sofort: Die Zählung läuft erst, wenn ein Mensch sie in
        der Tausendkorn-App freigibt; danach kostet sie meist 0,30–0,55 USD (eine harte Obergrenze gibt es noch
        nicht, Ausreißer sind möglich). Dieses Tool zählt nie selbst; Zählen ohne Freigabe ist abgeschaltet.
        Hinweis: Auf dem Laptop selbst ist die Freigabe für lokale Prozesse noch nicht erzwungen (kommt mit
        der Admin-PIN); umgehe sie nie über andere Wege. Gib dem Menschen
        den Link aus freigabe_url und frage später mit tk_auftrag_lesen nach. Nur auf ausdrücklichen Wunsch des
        Menschen. Für Wiederholungen dieselbe vorgang_id, sonst entsteht ein zweiter Antrag. Bei
        revision_veraltet die Probe neu lesen und den Menschen fragen, nicht automatisch wiederholen."""
        return await call("POST", f"/proben/{ident(probe_id, 'prb')}/zaehlungen", json={"max_kosten_usd": max_kosten_usd},
                          headers={"Idempotency-Key": vorgang_id, "If-Match": f'"{erwartete_rev}"'})

    @mcp.tool(title="Zählauftrag lesen", annotations=LESEN)
    async def tk_auftrag_lesen(
        job_id: Annotated[str, D("ID wie job_… aus tk_zaehlung_beantragen")],
    ) -> dict[str, Any]:
        """Stand eines Zählauftrags: freigabe_noetig (Mensch hat noch nicht freigegeben), abgelehnt, abgelaufen,
        wartet, laeuft, fertig oder fehler, mit Kosten. Zählen dauert einige Minuten; nicht öfter als alle
        30 Sekunden fragen. Kostet nichts."""
        return await call("GET", f"/auftraege/{ident(job_id, 'job')}")

    @mcp.tool(title="Konto und Budget", annotations=LESEN)
    async def tk_konto_lesen() -> dict[str, Any]:
        """Name und Berechtigungen dieses Zugangs, Tagesbudget, heute verbraucht oder reserviert und
        Autonomie-Budget (Zählungen ohne Einzelfreigabe). Kostet nichts."""
        return await call("GET", "/konto")

    @mcp.resource("tausendkorn://kulturen", name="kulturen", title="Kulturen und Vorgaben",
                  mime_type="application/json")
    async def kulturen_resource() -> dict[str, Any]:
        """Saatstärke-Vorgaben je Kultur (wie tk_kulturen_auflisten)."""
        return await call("GET", "/kulturen")

    @mcp.prompt(title="Saatmenge besprechen")
    def saatmenge_besprechen(partie: str) -> str:
        """Saatmenge für eine Partie holen und verständlich erklären."""
        return (f"Finde mit tk_partien_suchen die Partie '{partie}' (bei mehreren Treffern nachfragen) und hole mit "
                "tk_saatmenge_fuer_partie die Saatmenge. Nenne kg/ha als ganze Zahl mit Spanne und sage, ob die "
                "Spanne gemessen oder nur angenommen ist. Erkläre den Rechenweg in einem Satz. Wenn etwas fehlt "
                "(fehlt), frage danach. Erinnere daran, die Drillmaschine abzudrehen.")

    for tool in mcp._tool_manager._tools.values():  # strict-mode friendly (OpenAI, Anthropic, MCP)
        tool.parameters["additionalProperties"] = False
        tool.parameters["required"] = list(tool.parameters.get("properties", {}))
    return mcp


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    url = os.environ.get("TK_API_URL", "http://localhost:8000").rstrip("/")
    token = os.environ.get("TK_API_TOKEN", "")
    if not token:
        log.warning("TK_API_TOKEN fehlt: nur Kulturen und Rechner funktionieren.")
    headers = {"User-Agent": "tausendkorn-mcp/0.1", **({"Authorization": f"Bearer {token}"} if token else {})}
    make_server(httpx.AsyncClient(base_url=url, headers=headers, timeout=30)).run("stdio")


if __name__ == "__main__":
    main()
