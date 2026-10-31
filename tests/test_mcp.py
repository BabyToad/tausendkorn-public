"""MCP server in-process, talking to the real ASGI app over httpx (no network, mock mode)."""

import asyncio
import json
import uuid

import httpx
from mcp import Client

from app import server as S
from app.mcp_server import make_server
from tests.conftest import bearer, counted_sample, make_sample

TOOLS = {"tk_kulturen_auflisten", "tk_partien_suchen", "tk_saatmenge_fuer_partie", "tk_proben_suchen",
         "tk_probe_lesen", "tk_aussaatmenge_berechnen", "tk_aussaatmenge_pflanzen_berechnen",
         "tk_zaehlung_beantragen", "tk_auftrag_lesen", "tk_konto_lesen"}


def api(headers=None) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=S.app), base_url="http://testserver",
                             headers=headers or {})


async def _session():
    h = bearer("lesen,zaehlen", name="claude-test")
    sid = make_sample()
    par = uuid.uuid4().hex
    counted_sample(haenger="Hänger 11", sorte="Asory", partie_id=par)
    out = {"sid": sid, "par": par}
    async with api(h) as http, Client(make_server(http)) as c:
        out["tools"] = {t.name: t for t in (await c.list_tools()).tools}
        out["k"] = await c.call_tool("tk_kulturen_auflisten", {})
        out["calc"] = await c.call_tool("tk_aussaatmenge_berechnen", {
            "tkg_g": 46.33, "keimfaehigkeit_pct": 95, "saatstaerke_koerner_m2": 320, "kultur": None})
        out["such"] = await c.call_tool("tk_partien_suchen", {"suche": "hänger 11", "kultur": None, "sorte": None})
        out["part"] = await c.call_tool("tk_saatmenge_fuer_partie", {"partie_id": f"par_{par}"})
        probe = await c.call_tool("tk_probe_lesen", {"probe_id": f"prb_{sid}", "mit_punkten": False})
        rev = probe.structured_content["rev"]
        out["job"] = await c.call_tool("tk_zaehlung_beantragen", {
            "probe_id": f"prb_{sid}", "erwartete_rev": rev, "vorgang_id": str(uuid.uuid4()), "max_kosten_usd": None})
        out["stale"] = await c.call_tool("tk_zaehlung_beantragen", {
            "probe_id": f"prb_{sid}", "erwartete_rev": 1, "vorgang_id": str(uuid.uuid4()), "max_kosten_usd": None})
        out["lesen"] = await c.call_tool("tk_auftrag_lesen", {"job_id": out["job"].structured_content["id"]})
        out["konto"] = await c.call_tool("tk_konto_lesen", {})
    return out


def test_mcp_tools():
    o = asyncio.run(_session())
    tools = o["tools"]
    assert set(tools) == TOOLS
    for name, t in tools.items():
        paid = name == "tk_zaehlung_beantragen"
        a = t.annotations
        assert (a.read_only_hint, a.destructive_hint, a.idempotent_hint, a.open_world_hint) == \
            ((False, False, True, True) if paid else (True, False, True, False)), name
        s = t.input_schema
        assert s["additionalProperties"] is False and set(s["required"]) == set(s.get("properties", {})), name
        assert "exclusiveMinimum" not in json.dumps(s) and "maximum" not in json.dumps(s), name
    assert "Kostet NICHTS sofort" in tools["tk_zaehlung_beantragen"].description
    assert not o["k"].is_error and o["k"].structured_content["kulturen"]
    assert round(o["calc"].structured_content["aussaatmenge"]["wert"]) == 156
    assert o["such"].structured_content["eindeutig"]
    assert o["part"].structured_content["partie_id"] == f"par_{o['par']}"
    assert o["job"].structured_content["status"] == "freigabe_noetig"
    assert o["stale"].is_error and "revision_veraltet" in o["stale"].content[0].text
    assert o["lesen"].structured_content["status"] == "freigabe_noetig"
    assert o["konto"].structured_content["token_name"] == "claude-test"
    assert S.get_row(o["sid"])["status"] == "fehler"  # the agent alone started nothing


async def _no_token():
    async with api() as http, Client(make_server(http)) as c:
        ok = await c.call_tool("tk_kulturen_auflisten", {})
        denied = await c.call_tool("tk_konto_lesen", {})
    return ok, denied


def test_mcp_without_token_reads_only_public():
    ok, denied = asyncio.run(_no_token())
    assert not ok.is_error
    assert denied.is_error and "nicht_angemeldet" in denied.content[0].text


async def _malformed():
    seen = []
    transport = httpx.MockTransport(lambda req: seen.append(str(req.url)) or httpx.Response(200, json={}))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http, \
            Client(make_server(http)) as c:
        bad = [await c.call_tool("tk_zaehlung_beantragen", {"probe_id": "../../samples/1/count?", "erwartete_rev": 1,
                                                             "vorgang_id": str(uuid.uuid4()), "max_kosten_usd": None}),
               await c.call_tool("tk_probe_lesen", {"probe_id": "prb_1/../../x", "mit_punkten": False}),
               await c.call_tool("tk_saatmenge_fuer_partie", {"partie_id": "par_abc?x=1"}),
               await c.call_tool("tk_auftrag_lesen", {"job_id": "job_%2e%2e"})]
    return bad, seen


def test_malformed_ids_never_reach_http():
    bad, seen = asyncio.run(_malformed())
    assert all(r.is_error and "ungueltige_id" in r.content[0].text for r in bad)
    assert seen == []
