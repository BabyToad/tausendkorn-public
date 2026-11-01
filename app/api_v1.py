"""Öffentliche API /api/v1 für Hofsoftware, Skripte und Agenten (docs/app/API.md, openapi.yaml).

Stand heute: Lesen, Rechner, Saatmenge je Hänger und Zählung nur nach Freigabe durch
einen Menschen. Die Web-App nutzt weiter /api/samples; beide teilen dieselbe Datenbank
und dieselbe Logik in app/server.py (hier nur abgebildet, nicht dupliziert).

Auth: Betriebs-Token (Bearer, app/tokens.py) oder die gekoppelte App-Sitzung (Cookie).
Keine localhost-Ausnahme: ein Agent auf dem Laptop ist auch localhost.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import secrets
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from app import tokens
from app.kulturen import KULTUREN, SAATV, finde

router = APIRouter()

KOSTEN_SCHAETZUNG_USD = (0.30, 0.55)
OBERGRENZE_USD = 1.00          # reserved per count until its real cost is known; NOT a hard stop yet
AUTONOMIE_AKTIV = False        # counting without approval only once the pipeline enforces a cost limit
BUDGET_USD_TAG = 10.00         # whole farm, API counts only
MAX_ZAEHLUNGEN_TAG = 30        # per token
FREIGABE_MINUTEN = 15
WARN_KINDS = {"blatt": "blatt_abgeschnitten", "unscharf": "unscharf", "haufen": "haeufchen",
              "wenig": "wenige_koerner"}
SPERRT = {"blatt", "haufen"}   # missing kernels cannot be bounded (API.md 1)


def srv():
    """app.server includes this router, so import it only when a request runs."""
    from app import server
    return server


# ---------------------------------------------------------------- Fehler (RFC 9457)

class Problem(Exception):
    def __init__(self, status: int, code: str, detail: str, title: str = "", headers: dict | None = None, **extra):
        self.status, self.code, self.detail, self.title = status, code, detail, title or code
        self.headers, self.extra = headers or {}, extra


def _problem_response(p: Problem) -> JSONResponse:
    body = {"type": f"https://tausendkorn.local/fehler/{p.code}", "title": p.title, "status": p.status,
            "code": p.code, "detail": p.detail, **p.extra}
    return JSONResponse(body, status_code=p.status, headers=p.headers, media_type="application/problem+json")


async def _validation(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/v1/"):
        return await request_validation_exception_handler(request, exc)
    err = exc.errors()[0] if exc.errors() else {}
    feld = ".".join(str(x) for x in err.get("loc", [])[1:]) or None
    return _problem_response(Problem(422, "validierung", f"Ungültige Eingabe bei {feld or 'Anfrage'}: "
                                     f"{err.get('msg', 'unbekannt')}. Bitte den Wert prüfen.",
                                     "Ungültige Eingabe", feld=feld))


def install(app: FastAPI) -> None:
    """Called once from app/server.py, before the static mount."""
    async def _problem(request: Request, exc: Problem):
        return _problem_response(exc)
    init_jobs()
    S = srv()
    if not getattr(S.run_count, "_kassenbuch", False):
        S.run_count = _with_ledger(S.run_count)  # the worker looks run_count up on every call
    app.add_exception_handler(Problem, _problem)
    app.add_exception_handler(RequestValidationError, _validation)
    app.include_router(router)


# ---------------------------------------------------------------- Auth

class Caller(BaseModel):
    art: Literal["token", "app", "anonym"]
    token: dict | None = None
    scopes: set[str] = set()


APP_SCOPES = {"lesen", "eingaben"}  # the paired app approves counts; it counts via /api/samples


def caller(request: Request) -> Caller:
    auth = request.headers.get("authorization", "")
    if auth[:7].lower() == "bearer ":
        tok = tokens.verify(auth[7:].strip())
        if not tok:
            raise Problem(401, "nicht_angemeldet", "Das Token ist ungültig, abgelaufen oder widerrufen. "
                          "Bitte am Laptop ein neues erzeugen: uv run python -m app.tokens erstellen …",
                          headers={"WWW-Authenticate": 'Bearer realm="tausendkorn"'})
        return Caller(art="token", token=tok, scopes=set(tok["scopes"]))
    if secrets.compare_digest(request.cookies.get("tk", ""), srv().TOKEN):
        return Caller(art="app", scopes=APP_SCOPES)
    return Caller(art="anonym")


def need(request: Request, scope: str) -> Caller:
    c = caller(request)
    if c.art == "anonym":
        raise Problem(401, "nicht_angemeldet", "Anmeldung nötig: Header 'Authorization: Bearer <Token>' "
                      "mitschicken. Ein Token erzeugt die Betriebsleitung am Laptop.",
                      headers={"WWW-Authenticate": 'Bearer realm="tausendkorn"'})
    if scope not in c.scopes:
        raise Problem(403, "scope_fehlt", f"Diesem Zugang fehlt die Berechtigung '{scope}'. "
                      "Die Betriebsleitung kann ein Token mit diesem Scope erzeugen.", fehlender_scope=scope)
    return c


# ---------------------------------------------------------------- Abbildung Probe

def de(x: float | None, d: int = 1) -> str:
    return "–" if x is None else f"{x:,.{d}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def rev_of(d: dict) -> int:
    """Opaque revision: changes whenever the stored sample changes (any route, any device)."""
    raw = json.dumps(d, sort_keys=True, default=str, ensure_ascii=False)
    return int(hashlib.sha256(raw.encode()).hexdigest()[:12], 16)


def pid(sid: int) -> str:
    return f"prb_{sid}"


def parse_pid(probe_id: str) -> int:
    m = re.fullmatch(r"prb_(\d{1,12})", probe_id or "")
    if not m:
        raise Problem(404, "nicht_gefunden", f"'{probe_id}' ist keine Proben-ID (Form prb_<Zahl>).")
    return int(m.group(1))


def load(sid: int) -> dict:
    from fastapi import HTTPException
    try:
        return srv().get_row(sid)
    except HTTPException:
        raise Problem(404, "nicht_gefunden", f"Probe {pid(sid)} gibt es nicht oder sie liegt im Papierkorb.")


def groesse(wert, einheit, unten=None, oben=None, basis="annahme") -> dict:
    return {"wert": wert, "einheit": einheit, "unten": unten, "oben": oben, "basis": basis}


def band(n: int) -> int:
    b = srv().ERROR_BAND
    return max(round(b["rel"] * n), b["min"])


def status_of(d: dict) -> str:
    s = d["status"]
    if s in ("neu", "warnung"):
        return "wartet"
    if s == "fertig" and any(not c.get("done") for c in d["check_here"]) \
            and d.get("pruefung") not in ("uebersprungen", "geprueft"):
        return "pruefen"
    return s if s in ("zaehlt", "fertig", "fehler") else "wartet"


def warnings_of(d: dict) -> list[dict]:
    return (d.get("precheck") or {}).get("warnings") or []


def gesperrt(d: dict) -> bool:
    """Counted although the photo showed piles or a cut-off sheet: kg/ha is not given."""
    pre = d.get("precheck") or {}
    return bool(pre.get("override")) and any(w.get("kind") in SPERRT for w in warnings_of(d))


def quelle(d: dict) -> str:
    undone = {ev["of"] for ev in d["corrections"] if ev.get("op") == "undo"}
    if any(ev.get("op") in ("add", "remove") and ev.get("e") not in undone for ev in d["corrections"]):
        return "korrigiert"
    return "pruefstellen_bestaetigt" if d.get("pruefung") == "geprueft" else "automatisch"


def rechenweg(kultur: str | None, tkg, n, gewicht, modus, kf, ss, pflanzen, fa, kg_ha) -> str:
    teile = []
    if tkg is not None and n:
        teile.append(f"TKG = {de(gewicht, 2)} g ÷ {n} Körner × 1000 = {de(tkg, 2)} g")
    if kg_ha is not None:
        if modus == "pflanzen":
            teile.append(f"Aussaatmenge = {de(pflanzen, 0)} Pflanzen/m² × {de(tkg, 2)} g × 100 ÷ "
                         f"({de(kf, 0)} % × {de(100 if fa is None else fa, 0)} % Feldaufgang) = {de(kg_ha)} kg/ha")
        else:
            teile.append(f"Aussaatmenge = {de(ss, 0)} keimf. Körner/m² × {de(tkg, 2)} g ÷ {de(kf, 0)} % "
                         f"= {de(kg_ha)} kg/ha")
    s = "; ".join(teile)
    return f"{kultur}: {s}." if kultur and s else (s + "." if s else "Noch kein Ergebnis.")


def fehlt(d: dict) -> list[str]:
    out = []
    if not d["count"]:
        out.append("zaehlung")
    if not d["weight_g"]:
        out.append("gewicht_g")
    if not d["keimfaehigkeit"]:
        out.append("keimfaehigkeit_pct")
    if d["modus"] == "pflanzen":
        if not d["plants_m2"]:
            out.append("pflanzen_m2")
    elif not d["saatstaerke"]:
        out.append("saatstaerke_koerner_m2")
    return out


def scaled(v, n, lo_n, hi_n):
    """Values ∝ 1/count: count in [lo_n, hi_n] → value in [v·n/hi_n, v·n/lo_n]."""
    if v is None or not n or lo_n <= 0:
        return None, None
    return v * n / hi_n, v * n / lo_n


def partie_gesperrt(d: dict) -> bool:
    """The app pools every weighed handful; if one of them is blocked, its Partie values are not usable."""
    if not d.get("partie_id"):
        return False
    S = srv()
    with S._db_lock, S.db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM samples WHERE partie_id=? AND deleted_at IS NULL "
                                         "AND status='fertig'", (d["partie_id"],))]
        return any(gesperrt(S.get_row(i, con)) for i in ids)


def probe_out(d: dict, base: str, punkte: bool = False) -> dict:
    sid, n = d["id"], d["count"]
    basis = "gemessen" if srv().ERROR_BAND.get("gemessen") else "annahme"
    lock = gesperrt(d)
    pm = band(n) if n else None
    lo_n, hi_n = (n - pm, n + pm) if n else (None, None)
    anzahl = groesse(n, "Körner", None, None, "keine") if lock or not n else groesse(n, "Körner", lo_n, hi_n, basis)
    t_lo, t_hi = scaled(d["tkg"], n, lo_n, hi_n) if n else (None, None)
    a_lo, a_hi = scaled(d["kg_ha"], n, lo_n, hi_n) if n else (None, None)
    kultur = finde(d["kultur"])
    out = {
        "id": pid(sid), "rev": rev_of(d), "status": status_of(d), "fehler": d["error"],
        "erstellt": d["created_at"], "geaendert": d["updated_at"],
        "kultur": kultur["key"] if kultur else None, "kultur_name": d["kultur"],
        "sorte": d["sorte"] or None, "haenger": d["haenger"] or None, "partie_id": par_id(d.get("partie_id")),
        "eingaben": {
            "gewicht_g": d["weight_g"], "keimfaehigkeit_pct": d["keimfaehigkeit"], "modus": d["modus"],
            "saatstaerke_koerner_m2": d["saatstaerke"], "pflanzen_m2": d["plants_m2"],
            "feldaufgang_pct": d["feldaufgang"], "abdreh_flaeche_m2": d["abdreh_m2"], "notiz": d["notes"],
        },
        "zaehlung": {
            "anzahl": anzahl, "anzahl_modell": d["count_model"], "quelle": quelle(d) if n else None,
            "pruefstellen_offen": sum(not c.get("done") for c in d["check_here"]),
            "foto_warnungen": [WARN_KINDS.get(w.get("kind"), w.get("kind")) for w in warnings_of(d)],
            "foto_warnungen_text": [w.get("text") for w in warnings_of(d)],
            "aussaatmenge_gesperrt": lock,
            "kosten_usd": d["cost_usd"], "dauer_s": d["seconds"],
            "pruefstellen": [{"index": i, "bereich": c.get("region"), "konfidenz": c.get("confidence"),
                              "kommentar": c.get("comment"), "erledigt": bool(c.get("done"))}
                             for i, c in enumerate(d["check_here"])],
        },
        "ergebnis": {
            "tkg": groesse(d["tkg"], "g", None, None, "keine") if lock else groesse(d["tkg"], "g", t_lo, t_hi, basis),
            "koerner_m2": groesse(d["koerner_m2"], "Körner/m²", d["koerner_m2"], d["koerner_m2"], "als_fest"),
            "aussaatmenge": groesse(None, "kg/ha", basis="keine") if lock
            else groesse(d["kg_ha"], "kg/ha", a_lo, a_hi, basis),
            # from the app's (possibly pooled, rounded) drill value: its range is not derived here
            "abdreh_sollmenge": groesse(None, "kg", basis="keine") if lock or partie_gesperrt(d)
            else groesse(d["abdreh_kg"], "kg", basis="annahme" if d["abdreh_kg"] is not None else "keine"),
            "rechenweg": "Aussaatmenge gesperrt: Das Foto zeigte Häufchen oder ein abgeschnittenes Blatt, "
                         "fehlende Körner lassen sich nicht abschätzen. Bitte neu fotografieren." if lock
            else rechenweg(d["kultur"], d["tkg"], n, d["weight_g"], d["modus"], d["keimfaehigkeit"],
                           d["saatstaerke"], d["plants_m2"], d["feldaufgang"], d["kg_ha"]),
            "formel_version": d["formel_version"], "fehlt": fehlt(d),
        },
        "links": {"self": f"{base}api/v1/proben/{pid(sid)}", "foto": f"{base}api/samples/{sid}/photo",
                  "app": f"{base}#/probe/{sid}"},
    }
    if punkte:
        out["zaehlung"]["punkte"] = [{"id": p[0], "x": p[1], "y": p[2]} for p in d["points"]] \
            if d["points"] and len(d["points"][0]) == 3 else \
            [{"id": f"m{i}", "x": p[-2], "y": p[-1]} for i, p in enumerate(d["points"])]
    return out


# ---------------------------------------------------------------- öffentlich

@router.get("/api/v1/kulturen", tags=["Rechner"])
def kulturen():
    """Saatstärke-Vorgaben je Kultur mit Spannen und Quellen (öffentlich, kostet nichts)."""
    return {"kulturen": KULTUREN, "einheit_saatstaerke": "keimfähige Körner/m²",
            "hinweis": "Vorschläge zum Ändern, keine Vorschriften; Sortenempfehlung des Züchters geht vor.",
            "quelle_mindestkeimfaehigkeit": SAATV}


class RechnerEingabe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modus: Literal["keimfaehig", "pflanzen"] = "keimfaehig"
    tkg_g: float = Field(gt=0, le=200, allow_inf_nan=False)
    keimfaehigkeit_pct: float = Field(gt=0, le=100, allow_inf_nan=False)
    saatstaerke_koerner_m2: float | None = Field(None, gt=0, le=5000, allow_inf_nan=False)
    pflanzen_m2: float | None = Field(None, gt=0, le=5000, allow_inf_nan=False)
    feldaufgang_pct: float | None = Field(None, gt=0, le=100, allow_inf_nan=False)
    kultur: str | None = None


def hinweise_fuer(kultur: dict | None, tkg=None, kf=None, ss=None) -> list[str]:
    out = []
    if kultur and ss is not None:
        lo, hi = kultur["saatstaerke_spanne_koerner_m2"]
        if not lo <= ss <= hi:
            out.append(f"Saatstärke {de(ss, 0)} liegt außerhalb der üblichen Spanne {lo}–{hi} für {kultur['name']}.")
    if kultur and tkg is not None and kultur["tkg_plausibel_g"]:
        lo, hi = kultur["tkg_plausibel_g"]
        if not lo <= tkg <= hi:
            out.append(f"TKG {de(tkg)} g ist ungewöhnlich für {kultur['name']} (üblich {de(lo)}–{de(hi)} g). "
                       "Bitte Gewicht und Kornzahl prüfen.")
    if kf is not None and kf < 85:
        out.append("Niedrige Keimfähigkeit. Bitte Wert prüfen.")
    return out


@router.post("/api/v1/rechner/aussaatmenge", tags=["Rechner"])
def rechner(e: RechnerEingabe):
    """Reiner Rechner, speichert nichts, kostet nichts. Dieselbe Formel wie die App (SAATGUTRECHNER.md 2)."""
    kultur = finde(e.kultur) if e.kultur else None
    if e.kultur and not kultur:
        raise Problem(422, "validierung", f"Kultur '{e.kultur}' ist unbekannt. Liste: GET /api/v1/kulturen.",
                      feld="kultur", erlaubt=[k["key"] for k in KULTUREN])
    if e.modus == "keimfaehig" and e.saatstaerke_koerner_m2 is None:
        raise Problem(422, "validierung", "Für den Modus keimfaehig fehlt saatstaerke_koerner_m2 "
                      "(keimfähige Körner/m², z. B. Vorgabe der Kultur).", feld="saatstaerke_koerner_m2")
    if e.modus == "pflanzen" and e.pflanzen_m2 is None:
        raise Problem(422, "validierung", "Für den Modus pflanzen fehlt pflanzen_m2.", feld="pflanzen_m2")
    # calc() takes a sample row; 1000 kernels weighing tkg_g gram give exactly this TKG.
    row = {"count": 1000, "weight_g": e.tkg_g, "keimfaehigkeit": e.keimfaehigkeit_pct, "modus": e.modus,
           "saatstaerke": e.saatstaerke_koerner_m2, "plants_m2": e.pflanzen_m2, "feldaufgang": e.feldaufgang_pct}
    tkg, kpm2, kg_ha = srv().calc(row)
    return {
        "aussaatmenge": groesse(kg_ha, "kg/ha", kg_ha, kg_ha, "als_fest"),
        "koerner_m2": groesse(kpm2, "Körner/m²", kpm2, kpm2, "als_fest"),
        "rechenweg": rechenweg(kultur["name"] if kultur else None, e.tkg_g, None, None, e.modus,
                               e.keimfaehigkeit_pct, e.saatstaerke_koerner_m2, e.pflanzen_m2, e.feldaufgang_pct,
                               kg_ha),
        "formel_version": srv().FORMEL_VERSION,
        "hinweise": hinweise_fuer(kultur, e.tkg_g, e.keimfaehigkeit_pct, e.saatstaerke_koerner_m2)
        + ["Eingaben gelten als fest; die Unsicherheit des TKG ist hier nicht enthalten. "
           "Die Aussaatmenge ersetzt nicht das Abdrehen."],
    }


# ---------------------------------------------------------------- Proben lesen

def all_rows() -> list[dict]:
    S = srv()
    with S._db_lock, S.db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM samples WHERE deleted_at IS NULL AND photo IS NOT NULL "
                                         "ORDER BY id DESC")]
        return [S.get_row(i, con) for i in ids]


def norm(s: str | None) -> str:
    return re.sub(r"\s+", "", (s or "").casefold())


@router.get("/api/v1/proben", tags=["Proben"])
def proben(request: Request, kultur: str | None = None, sorte: str | None = None, haenger: str | None = None,
           status: str | None = None, seit: str | None = None, limit: int = 20, cursor: str | None = None,
           partie_id: str | None = None):
    """Proben suchen, neueste zuerst. Filter sind exakt (Groß-/Kleinschreibung und Leerzeichen egal)."""
    need(request, "lesen")
    if not 1 <= limit <= 50:
        raise Problem(422, "validierung", "limit muss zwischen 1 und 50 liegen.", feld="limit", erlaubt=[1, 50])
    before = parse_pid(cursor) if cursor else None
    par = parse_par(partie_id) if partie_id else None
    k = finde(kultur) if kultur else None
    out = []
    for d in all_rows():
        if before is not None and d["id"] >= before:
            continue
        if par and d.get("partie_id") != par:
            continue
        if kultur and norm(d["kultur"]) not in {norm(kultur), norm(k["name"]) if k else None}:
            continue
        if sorte and norm(d["sorte"]) != norm(sorte):
            continue
        if haenger and norm(d["haenger"]) != norm(haenger):
            continue
        if seit and (d["created_at"] or "") < seit:
            continue
        p = probe_out(d, str(request.base_url))
        if status and p["status"] != status:
            continue
        p["zaehlung"].pop("pruefstellen")
        out.append(p)
        if len(out) == limit + 1:
            break
    more = len(out) > limit
    out = out[:limit]
    return {"proben": out, "naechster_cursor": out[-1]["id"] if more else None}


@router.get("/api/v1/proben/{probe_id}", tags=["Proben"])
def probe(probe_id: str, request: Request, punkte: bool = False):
    need(request, "lesen")
    d = load(parse_pid(probe_id))
    p = probe_out(d, str(request.base_url), punkte)
    return JSONResponse(p, headers={"ETag": f'"{p["rev"]}"'})


def par_id(raw: str | None) -> str | None:
    return f"par_{raw}" if raw else None


def parse_par(partie_id: str) -> str:
    m = re.fullmatch(r"par_([A-Za-z0-9-]{8,64})", partie_id or "")
    if not m:
        raise Problem(404, "nicht_gefunden", f"'{partie_id}' ist keine Partie-ID (Form par_…). "
                      "Partien findet GET /api/v1/partien?suche=….")
    return m.group(1)


def partien_rows() -> dict[str, list[dict]]:
    """Counted handfuls grouped by the app's Partie (partie_id), oldest first."""
    groups: dict[str, list[dict]] = {}
    for d in reversed(all_rows()):
        if d["status"] == "fertig" and d["count"] and d.get("partie_id"):
            groups.setdefault(d["partie_id"], []).append(d)
    return groups


def partie_kurz(rows: list[dict]) -> dict:
    last = rows[-1]
    return {"partie_id": par_id(last["partie_id"]), "bezeichnung": last["haenger"] or last["sorte"] or last["kultur"],
            "haenger": last["haenger"] or None, "sorte": last["sorte"] or None, "kultur_name": last["kultur"],
            "kultur": (finde(last["kultur"]) or {}).get("key"), "erstellt": rows[0]["created_at"],
            "anzahl_proben": len(rows), "proben": [pid(d["id"]) for d in rows]}


@router.get("/api/v1/partien", tags=["Partien"])
def partien(request: Request, suche: str | None = None, kultur: str | None = None, sorte: str | None = None):
    """Partien (Handvoll-Gruppen der App) mit gezählten Proben suchen. `suche` ist Freitext wie
    „Hänger 3“ und trifft Hänger, Sorte oder Kultur. Mehrere Treffer: nachfragen, nicht raten."""
    need(request, "lesen")
    k = finde(kultur) if kultur else None
    out = []
    for rows in partien_rows().values():
        last = rows[-1]
        if suche and not any(norm(suche) in norm(last[f]) for f in ("haenger", "sorte", "kultur")):
            continue
        if kultur and norm(last["kultur"]) not in {norm(kultur), norm(k["name"]) if k else None}:
            continue
        if sorte and norm(last["sorte"]) != norm(sorte):
            continue
        out.append(partie_kurz(rows))
    out.sort(key=lambda p: p["erstellt"] or "", reverse=True)
    return {"partien": out[:50], "eindeutig": len(out) == 1,
            "hinweis": None if len(out) == 1 else "Keine Partie gefunden. Andere Suche versuchen." if not out
            else "Mehrere Partien passen. Bitte nachfragen, welche gemeint ist."}


@router.get("/api/v1/partien/{partie_id}", tags=["Partien"])
def partie(partie_id: str, request: Request):
    """Gepooltes TKG (1000 × Σ Gewicht ÷ Σ Körner) und Aussaatmenge der Partie mit Spanne und Rechenweg.
    Wie die App: ab zwei gewogenen Handvoll der Partie-Wert, sonst der Wert der einen Handvoll."""
    need(request, "lesen")
    S = srv()
    raw = parse_par(partie_id)
    rows = partien_rows().get(raw)
    if not rows:
        raise Problem(404, "nicht_gefunden", f"Partie {partie_id} hat keine gezählte Probe.")
    usable = [d for d in rows if d["weight_g"] and not gesperrt(d)]
    out = {**partie_kurz(rows), "proben_verwendet": [pid(d["id"]) for d in usable],
           "gesperrt": [pid(d["id"]) for d in rows if gesperrt(d)],
           "hinweise": ["Die Aussaatmenge ersetzt nicht das Abdrehen der Drillmaschine."]}
    if not usable:
        return {**out, "tkg_gepoolt": groesse(None, "g", basis="keine"),
                "aussaatmenge": groesse(None, "kg/ha", basis="keine"), "koerner_m2": groesse(None, "Körner/m²", basis="keine"),
                "eingaben_quelle": None, "tkg_einzeln": [],
                "rechenweg": "Keine gewogene Probe. Bitte das Gewicht der ganzen Probe eingeben, mit Bruch, Spreu und Fremdbesatz.",
                "fehlt": ["gewicht_g"]}
    w = sum(d["weight_g"] for d in usable)
    n = sum(d["count"] for d in usable)
    lo_n = sum(d["count"] - band(d["count"]) for d in usable)
    hi_n = sum(d["count"] + band(d["count"]) for d in usable)
    tkg = 1000 * w / n
    basis = "gemessen" if S.ERROR_BAND.get("gemessen") else "annahme"
    # targets of the newest handful that has them, as the drill value in the app
    src = next((d for d in reversed(usable) if d["keimfaehigkeit"] and (d["saatstaerke"] or d["plants_m2"])), None)
    kpm2, kg_ha = S.rate(src, tkg) if src else (None, None)
    a_lo, a_hi = scaled(kg_ha, n, lo_n, hi_n)
    weg = f"TKG = {de(w, 2)} g ÷ {n} Körner × 1000 = {de(tkg, 2)} g aus {len(usable)} Handvoll"
    if src:
        weg += "; " + rechenweg(None, tkg, None, None, src["modus"], src["keimfaehigkeit"], src["saatstaerke"],
                                src["plants_m2"], src["feldaufgang"], kg_ha).rstrip(".")
        weg += f" (Keimfähigkeit und Saatstärke aus {pid(src['id'])})"
    offen = sum(sum(not c.get("done") for c in d["check_here"]) for d in usable
                if d.get("pruefung") not in ("uebersprungen", "geprueft"))
    if offen:
        out["hinweise"].append(f"{offen} Prüfstelle(n) noch offen; die Zahl kann sich nach dem Prüfen ändern.")
    if len(usable) == 1:
        out["hinweise"].append("Nur eine gewogene Handvoll. Eine zweite Handvoll macht das TKG der Partie sicherer.")
    return {**out, "tkg_gepoolt": groesse(tkg, "g", 1000 * w / hi_n, 1000 * w / lo_n if lo_n > 0 else None, basis),
            "tkg_einzeln": [d["tkg"] for d in usable],
            "aussaatmenge": groesse(kg_ha, "kg/ha", a_lo, a_hi, basis),
            "koerner_m2": groesse(kpm2, "Körner/m²", kpm2, kpm2, "als_fest"),
            "eingaben_quelle": pid(src["id"]) if src else None, "rechenweg": weg + ".",
            "fehlt": [] if src else ["keimfaehigkeit_pct", "saatstaerke_koerner_m2"]}


# ---------------------------------------------------------------- Zählaufträge

def init_jobs() -> None:
    S = srv()
    with S._db_lock, S.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS api_jobs (
            id TEXT PRIMARY KEY, sample_id INTEGER, token_id TEXT, token_name TEXT, idem_key TEXT,
            status TEXT, photo TEXT, rev INTEGER, obergrenze_usd REAL, autonom INTEGER DEFAULT 0,
            created_at TEXT, expires_at TEXT, decided_at TEXT, decided_by TEXT, kosten_usd REAL,
            kosten_unbekannt INTEGER DEFAULT 0)""")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS api_jobs_idem ON api_jobs(token_id, idem_key)")
        if "kosten_unbekannt" not in {r[1] for r in con.execute("PRAGMA table_info(api_jobs)")}:
            con.execute("ALTER TABLE api_jobs ADD COLUMN kosten_unbekannt INTEGER DEFAULT 0")
        # Server stopped while a job was claimed or counting: the model may already have been paid.
        # Book the full reservation as the unknown cost (never assume zero).
        # A count that did finish (sample fertig with a cost) keeps its real result.
        for r in con.execute("SELECT * FROM api_jobs WHERE status IN ('startet', 'gestartet')").fetchall():
            d = _sample_or_none(r["sample_id"], con)
            if d and d["status"] == "fertig" and d["photo"] == r["photo"] and d.get("cost_usd") is not None:
                con.execute("UPDATE api_jobs SET status='fertig', kosten_usd=? WHERE id=?", (d["cost_usd"], r["id"]))
        con.execute("UPDATE api_jobs SET status='fehler', kosten_usd=obergrenze_usd, kosten_unbekannt=1 "
                    "WHERE status IN ('startet', 'gestartet')")


def _now() -> datetime:
    return datetime.now().astimezone()


def _today() -> str:
    return _now().date().isoformat()


# Stored job states: freigabe_noetig → abgelehnt | abgelaufen | startet (claimed) → gestartet (queued)
# → fertig | fehler | abgebrochen. Final states keep their own cost (ledger); a later recount of the
# same sample never rewrites an earlier job.
FINAL = ("abgelehnt", "abgelaufen", "fertig", "fehler", "abgebrochen")


def job_status(j: dict, d: dict | None) -> str:
    if j["status"] == "freigabe_noetig" and datetime.fromisoformat(j["expires_at"]) < _now():
        return "abgelaufen"
    if j["status"] == "startet":
        return "wartet"
    if j["status"] != "gestartet":
        return j["status"]
    if d is None:
        return "abgebrochen"
    if d["status"] == "zaehlt":
        return "laeuft" if d["id"] not in list(srv()._queue.queue) else "wartet"
    return {"fertig": "fertig", "fehler": "fehler"}.get(d["status"], "abgebrochen")


def settle(con, j: dict, d: dict | None) -> dict:
    """Write the outcome of a finished job once. Unknown cost of a failed count = full reservation."""
    st = job_status(j, d)
    # Only approval expiry is settled here; a started attempt is settled by the worker alone (_with_ledger),
    # otherwise a poll between "fehler" and the worker's bookkeeping would book a stale cost (Astra round 3).
    if j["status"] == "freigabe_noetig" and st in FINAL:
        cost = 0.0 if st in ("abgelehnt", "abgelaufen") else \
            j["obergrenze_usd"] if st == "abgebrochen" else \
            float(d["cost_usd"]) if d and d.get("cost_usd") is not None else \
            (0.0 if srv().MOCK else j["obergrenze_usd"])
        con.execute("UPDATE api_jobs SET status=?, kosten_usd=? WHERE id=?", (st, cost, j["id"]))
        j = {**j, "status": st, "kosten_usd": cost}
    return j


def job_cost(j: dict, st: str) -> float:
    """Booked jobs: their own recorded cost. Everything else, including a finished attempt the worker has
    not booked yet, keeps the full reservation (Astra round 4)."""
    if st in ("abgelehnt", "abgelaufen"):
        return 0.0
    if j["status"] in FINAL and j["kosten_usd"] is not None:
        return float(j["kosten_usd"])
    return j["obergrenze_usd"]


def _sample_or_none(sid: int, con) -> dict | None:
    from fastapi import HTTPException
    try:
        return srv().get_row(sid, con)
    except HTTPException:
        return None


def jobs_today(con, token_id: str | None = None) -> list[tuple[dict, str, dict | None]]:
    q = "SELECT * FROM api_jobs WHERE substr(created_at, 1, 10) = ?"
    args: list = [_today()]
    if token_id:
        q += " AND token_id = ?"
        args.append(token_id)
    out = []
    for r in con.execute(q, args).fetchall():
        j = dict(r)
        d = _sample_or_none(j["sample_id"], con)
        j = settle(con, j, d)
        out.append((j, job_status(j, d), d))
    return out


def job_out(j: dict, request: Request, d: dict | None = None) -> dict:
    st = job_status(j, d)
    waiting = list(srv()._queue.queue)
    base = str(request.base_url)
    return {
        "id": j["id"], "probe_id": pid(j["sample_id"]), "status": st,
        "freigabe_bis": j["expires_at"] if st == "freigabe_noetig" else None,
        "freigabe_url": f"{base}freigabe/{j['id']}" if st == "freigabe_noetig" else None,
        "beantragt_von": j["token_name"], "autonom": bool(j["autonom"]),
        "reserviert_usd": j["obergrenze_usd"], "obergrenze_erzwungen": False,
        "geschaetzte_kosten_usd": list(KOSTEN_SCHAETZUNG_USD),
        "kosten_usd": j["kosten_usd"] if st in FINAL else None,
        "kosten_unbekannt": bool(j.get("kosten_unbekannt")),
        "position": waiting.index(j["sample_id"]) + 1 if st == "wartet" and j["sample_id"] in waiting else 0,
        "hinweis": {
            "freigabe_noetig": "Ein Mensch muss die Zählung in der Tausendkorn-App freigeben. "
                               "Bitte den Freigabe-Link auf dem gekoppelten iPad öffnen.",
            "abgelehnt": "Die Zählung wurde abgelehnt. Es entstehen keine Kosten.",
            "abgelaufen": "Die Freigabe ist abgelaufen (15 Minuten). Bei Bedarf neu beantragen.",
            "wartet": "Freigegeben, wartet auf das Zählen.", "laeuft": "Wird gerade gezählt (einige Minuten).",
            "fertig": "Fertig gezählt. Ergebnis mit tk_probe_lesen bzw. GET /api/v1/proben/{id} abrufen.",
            "fehler": "Die Zählung ist fehlgeschlagen. Bitte in der App nachsehen.",
            "abgebrochen": "Die Probe gibt es nicht mehr oder sie wurde anderweitig geändert.",
        }[st],
        "links": {"self": f"{base}api/v1/auftraege/{j['id']}", "probe": f"{base}api/v1/proben/{pid(j['sample_id'])}"},
    }


class ZaehlungAntrag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_kosten_usd: float | None = Field(None, description="Noch nicht unterstützt: nur null")


@router.post("/api/v1/proben/{probe_id}/zaehlungen", status_code=202, tags=["Zählung"])
def zaehlung_beantragen(probe_id: str, request: Request, antrag: ZaehlungAntrag | None = None):
    """Zählung **beantragen** (kostet nach Freigabe meist 0,30–0,55 USD; eine harte Obergrenze gibt es
    noch nicht). Läuft erst, wenn ein Mensch sie in der App freigibt.
    Verlangt die Header `Idempotency-Key` und `If-Match` (Revision der Probe)."""
    c = need(request, "zaehlen")
    if c.art != "token":
        raise Problem(403, "scope_fehlt", "Die App zählt über ihren eigenen Knopf; diese Schnittstelle ist für Tokens.")
    key = request.headers.get("idempotency-key", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}", key):
        raise Problem(428, "idempotenz_key_fehlt", "Header 'Idempotency-Key' fehlt oder ist ungültig "
                      "(8–128 Zeichen, z. B. eine UUID). Bei Wiederholung denselben Schlüssel schicken.")
    if antrag and antrag.max_kosten_usd is not None:
        # the pipeline cannot stop at a given amount yet; refuse instead of pretending (Astra #2)
        raise Problem(422, "validierung", "Eine Kostengrenze je Zählung kann die Zählung heute noch nicht "
                      "einhalten (meist 0,30–0,55 USD, Ausreißer möglich). max_kosten_usd weglassen oder null schicken.",
                      feld="max_kosten_usd", erlaubt=[None])
    match = request.headers.get("if-match", "").strip().strip('"').removeprefix("W/").strip('"')
    sid = parse_pid(probe_id)
    tok = c.token
    S = srv()
    started = False
    with S._db_lock, S.db() as con:
        prev = con.execute("SELECT * FROM api_jobs WHERE token_id=? AND idem_key=?", (tok["id"], key)).fetchone()
        if prev:
            prev = dict(prev)
            if prev["sample_id"] != sid:
                raise Problem(422, "idempotenz_konflikt", "Dieser Idempotency-Key wurde schon für eine andere "
                              "Probe benutzt. Für eine neue Absicht einen neuen Schlüssel erzeugen.")
            dprev = _sample_or_none(sid, con)
            return JSONResponse(job_out(settle(con, prev, dprev), request, dprev), status_code=202)
        d = _sample_or_none(sid, con)
        if d is None:
            raise Problem(404, "nicht_gefunden", f"Probe {pid(sid)} gibt es nicht oder sie liegt im Papierkorb.")
        if not match:
            raise Problem(428, "if_match_fehlt", "Header 'If-Match' mit der Revision der Probe fehlt "
                          "(Feld rev bzw. ETag aus GET /api/v1/proben/{id}).")
        if match != str(rev_of(d)):
            raise Problem(412, "revision_veraltet", "Die Probe hat sich geändert. Bitte neu lesen und dann "
                          "entscheiden; nicht automatisch wiederholen.", aktuelle_rev=rev_of(d))
        if d["status"] in ("fertig", "zaehlt") or not d["photo"]:
            raise Problem(409, "schon_gezaehlt", "Diese Probe ist schon gezählt oder wird gerade gezählt. "
                          "Neu zählen geht nur nach einem Fehler.", status_probe=status_of(d))
        today = jobs_today(con)
        for j, st, _ in today:
            if j["sample_id"] == sid and st in ("freigabe_noetig", "wartet", "laeuft"):
                raise Problem(409, "schon_beantragt", "Für diese Probe läuft schon ein Antrag.",
                              auftrag=job_out(j, request, d))
        mine = [(j, st, dd) for j, st, dd in today if j["token_id"] == tok["id"]]
        if len(mine) >= MAX_ZAEHLUNGEN_TAG:
            raise Problem(429, "zu_viele_anfragen", f"Höchstens {MAX_ZAEHLUNGEN_TAG} Zählungen je Token und Tag.",
                          headers={"Retry-After": str(_seconds_to_midnight())})
        spent = sum(job_cost(j, st) for j, st, _ in today)
        if spent + OBERGRENZE_USD > BUDGET_USD_TAG:
            raise Problem(402, "budget_erschoepft", f"Tagesbudget von {de(BUDGET_USD_TAG, 2)} USD erreicht "
                          f"(verbraucht oder reserviert: {de(spent, 2)} USD). Morgen wieder möglich.",
                          verbraucht_usd=spent, budget_usd=BUDGET_USD_TAG)
        mine_spent = sum(job_cost(j, st) for j, st, _ in mine)
        autonom = AUTONOMIE_AKTIV and (tok.get("autonomie_usd") or 0) > 0 \
            and mine_spent + OBERGRENZE_USD <= tok["autonomie_usd"] \
            and d["status"] != "warnung"  # a photo warning always needs a human
        now = _now()
        j = {"id": "job_" + uuid.uuid4().hex[:16], "sample_id": sid, "token_id": tok["id"],
             "token_name": tok["name"], "idem_key": key, "status": "startet" if autonom else "freigabe_noetig",
             "photo": d["photo"], "rev": rev_of(d), "obergrenze_usd": OBERGRENZE_USD, "autonom": int(autonom),
             "created_at": now.isoformat(timespec="seconds"),
             "expires_at": (now + timedelta(minutes=FREIGABE_MINUTEN)).isoformat(timespec="seconds"),
             "decided_at": now.isoformat(timespec="seconds") if autonom else None,
             "decided_by": "autonomie-budget" if autonom else None, "kosten_usd": None}
        con.execute(f"INSERT INTO api_jobs ({', '.join(j)}) VALUES ({', '.join('?' * len(j))})", tuple(j.values()))
    if autonom:
        _start(j["id"], sid)
    with S._db_lock, S.db() as con:
        j = _job(j["id"], con)
        d = _sample_or_none(sid, con)
    return JSONResponse(job_out(j, request, d), status_code=202)


def _start(jid: str, sid: int) -> None:
    """The job is already claimed ('startet', reservation held). Queue the count; the worker settles
    the job when this attempt ends (_with_ledger), possibly before this function returns."""
    ok = srv().start_count(sid)
    S = srv()
    with S._db_lock, S.db() as con:
        if ok:
            con.execute("UPDATE api_jobs SET status='gestartet' WHERE id=? AND status='startet'", (jid,))
        else:
            con.execute("UPDATE api_jobs SET status='abgebrochen', kosten_usd=0 WHERE id=? AND status='startet'", (jid,))


def _with_ledger(run_count):
    """Settle the API job of exactly this worker attempt when it ends, so a later recount (from the app
    or the API) can never rewrite it. A failure without a newly written cost books the full
    reservation as unknown cost: start_count() keeps the previous attempt's cost_usd on the row."""
    def run(sid: int) -> None:
        S = srv()
        before = _sample_or_none(sid, None)
        try:
            run_count(sid)
        finally:
            with S._db_lock, S.db() as con:
                r = con.execute("SELECT * FROM api_jobs WHERE sample_id=? AND status IN ('startet', 'gestartet') "
                                "ORDER BY created_at DESC LIMIT 1", (sid,)).fetchone()
                if r:
                    j, d = dict(r), _sample_or_none(sid, con)
                    st = d["status"] if d and d["status"] in ("fertig", "fehler") else "fehler"
                    fresh = d is not None and d.get("cost_usd") is not None and \
                        (before is None or d.get("cost_usd") != before.get("cost_usd") or st == "fertig")
                    cost = float(d["cost_usd"]) if fresh else (0.0 if S.MOCK else j["obergrenze_usd"])
                    con.execute("UPDATE api_jobs SET status=?, kosten_usd=?, kosten_unbekannt=? WHERE id=?",
                                (st, cost, 0 if fresh or S.MOCK else 1, j["id"]))
    run._kassenbuch = True
    return run


def _seconds_to_midnight() -> int:
    n = _now()
    return int((n.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) - n).total_seconds())


def _set_job(jid: str, **fields) -> None:
    S = srv()
    with S._db_lock, S.db() as con:
        con.execute(f"UPDATE api_jobs SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), jid))


def _job(jid: str, con) -> dict:
    r = con.execute("SELECT * FROM api_jobs WHERE id=?", (jid,)).fetchone()
    if not r:
        raise Problem(404, "nicht_gefunden", f"Auftrag {jid} gibt es nicht.")
    return dict(r)


@router.get("/api/v1/auftraege/{job_id}", tags=["Zählung"])
def auftrag(job_id: str, request: Request):
    c = need(request, "lesen")
    S = srv()
    with S._db_lock, S.db() as con:
        j = _job(job_id, con)
        d = _sample_or_none(j["sample_id"], con)
        j = settle(con, j, d)
    if c.art == "token" and j["token_id"] != c.token["id"] and "admin" not in c.scopes:
        raise Problem(404, "nicht_gefunden", f"Auftrag {job_id} gibt es nicht.")
    return job_out(j, request, d)


class Freigabe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entscheidung: Literal["freigeben", "ablehnen"]


def same_origin(request: Request) -> bool:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin") or ""
    if not origin:
        ref = request.headers.get("referer") or ""
        origin = "/".join(ref.split("/")[:3]) if ref else ""
    return bool(host) and origin in (f"http://{host}", f"https://{host}")


@router.post("/api/v1/auftraege/{job_id}/freigabe", tags=["Zählung"])
def freigabe(job_id: str, body: Freigabe, request: Request):
    """Nur ein Mensch in der gekoppelten App gibt frei (Cookie + gleicher Ursprung), nie ein Token."""
    c = caller(request)
    if c.art != "app":
        raise Problem(403, "nur_app", "Freigeben kann nur ein Mensch in der gekoppelten Tausendkorn-App, "
                      "nicht ein Token oder Agent. Bitte den Freigabe-Link auf dem iPad öffnen.")
    if not same_origin(request):
        raise Problem(403, "ursprung_falsch", "Freigabe nur von der Tausendkorn-Seite selbst.")
    S = srv()
    with S._db_lock, S.db() as con:
        j = _job(job_id, con)
        d = _sample_or_none(j["sample_id"], con)
        j = settle(con, j, d)
        st = job_status(j, d)
        if st != "freigabe_noetig":
            raise Problem(409, "nicht_offen", f"Dieser Antrag ist nicht mehr offen (Stand: {st}).", stand=st)
        if d is None or d["photo"] != j["photo"] or d["status"] in ("fertig", "zaehlt"):
            con.execute("UPDATE api_jobs SET status='abgebrochen', kosten_usd=0, decided_at=? WHERE id=?",
                        (_now().isoformat(timespec="seconds"), job_id))
            raise Problem(409, "probe_geaendert", "Die Probe wurde inzwischen gezählt, gelöscht oder hat ein "
                          "anderes Foto. Der Antrag ist damit erledigt.")
        decided = "abgelehnt" if body.entscheidung == "ablehnen" else "startet"
        con.execute("UPDATE api_jobs SET status=?, decided_at=?, decided_by='app', kosten_usd=? WHERE id=?",
                    (decided, _now().isoformat(timespec="seconds"), 0.0 if decided == "abgelehnt" else None, job_id))
        if decided == "startet" and d["status"] == "warnung" and d["precheck"]:  # like "Trotzdem zählen"
            S.write(con, d["id"], precheck={**d["precheck"], "override": True})
    if decided == "startet":
        _start(job_id, j["sample_id"])
    with S._db_lock, S.db() as con:
        j = _job(job_id, con)
        d = _sample_or_none(j["sample_id"], con)
    return job_out(j, request, d)


@router.get("/api/v1/konto", tags=["Konto"])
def konto(request: Request):
    c = need(request, "lesen")
    S = srv()
    with S._db_lock, S.db() as con:
        today = jobs_today(con)
    mine = [t for t in today if c.token and t[0]["token_id"] == c.token["id"]]
    return {"betrieb": "Tausendkorn (diese Installation)",
            "token_name": c.token["name"] if c.token else "App-Sitzung",
            "scopes": sorted(c.scopes), "autonomie_budget_usd_tag": (c.token or {}).get("autonomie_usd", 0.0),
            "autonomie_aktiv": AUTONOMIE_AKTIV,
            "budget_usd_tag": BUDGET_USD_TAG,
            "verbraucht_oder_reserviert_usd_heute": round(sum(job_cost(j, st) for j, st, _ in today), 4),
            "zaehlungen_heute": len(mine), "max_zaehlungen_tag": MAX_ZAEHLUNGEN_TAG,
            "ablauf": (c.token or {}).get("ablauf")}


# ---------------------------------------------------------------- Freigabe-Seite

PAGE = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Zählung freigeben</title>
<style>
body{{font:18px/1.45 system-ui,sans-serif;margin:0;background:#f6f3ea;color:#1f2a1c}}
main{{max-width:560px;margin:0 auto;padding:24px 16px}}
h1{{font-size:26px;margin:0 0 12px}} .card{{background:#fff;border-radius:16px;padding:16px;margin:12px 0}}
img{{width:100%;max-height:35vh;object-fit:contain;border-radius:12px;margin-top:8px}} .warn{{background:#fff4d6;border-left:6px solid #d39b00}}
button{{font:inherit;font-weight:700;width:100%;padding:18px;border:0;border-radius:14px;margin-top:12px}}
.ok{{background:#2f6b2a;color:#fff}} .no{{background:#e7e2d4;color:#1f2a1c}} .muted{{color:#5d6657}}
</style></head><body><main>{body}</main>
<script>
async function go(e){{
  document.querySelectorAll("button").forEach(b=>b.disabled=true);
  const r=await fetch("/api/v1/auftraege/{jid}/freigabe",{{method:"POST",headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{entscheidung:e}})}});
  const j=await r.json();
  document.querySelector("#out").textContent=r.ok?(e==="freigeben"?"Freigegeben. Die Zählung startet.":"Abgelehnt. Es entstehen keine Kosten."):(j.detail||"Fehler");
}}
</script></body></html>"""


@router.get("/freigabe/{job_id}", response_class=HTMLResponse, include_in_schema=False)
def freigabe_seite(job_id: str, request: Request):
    esc = html.escape
    S = srv()
    with S._db_lock, S.db() as con:
        r = con.execute("SELECT * FROM api_jobs WHERE id=?", (job_id,)).fetchone()
        j = dict(r) if r else None
        d = _sample_or_none(j["sample_id"], con) if j else None
    jid = esc(job_id) if j else ""
    if caller(request).art != "app":
        body = ("<h1>Zählung freigeben</h1><div class='card'>Diese Seite funktioniert nur auf dem gekoppelten "
                "iPad oder Gerät. Bitte dort öffnen oder zuerst <a href='/'>koppeln</a>.</div>")
        return HTMLResponse(PAGE.format(body=body, jid=jid), status_code=403)
    if not j:
        return HTMLResponse(PAGE.format(body="<h1>Antrag nicht gefunden</h1>", jid=""), status_code=404)
    st = job_status(j, d)
    title = " · ".join(x for x in (d and d["sorte"], d and d["haenger"]) if x) or (d["kultur"] if d else "")
    lo, hi = KOSTEN_SCHAETZUNG_USD
    warn = "".join(f"<div class='card warn'>{esc(w.get('text', ''))}<br><b>Freigeben heißt hier: trotzdem "
                   "zählen.</b></div>" for w in (warnings_of(d) if d else []))
    if st != "freigabe_noetig":
        body = f"<h1>{esc(title)}</h1><div class='card'>Dieser Antrag ist nicht mehr offen (Stand: {esc(st)}).</div>"
    else:
        body = (f"<h1>Zählung freigeben?</h1><div class='card'><b>{esc(title)}</b><br>"
                f"<span class='muted'>{esc(d['kultur'] or '')} · Probe {pid(d['id'])}</span>"
                f"<img src='/api/samples/{d['id']}/photo' alt='Foto der Probe'></div>"
                f"<div class='card'>Beantragt von <b>{esc(j['token_name'])}</b>.<br>Kostet ca. "
                f"{de(lo, 2)}–{de(hi, 2)} USD (Ausreißer möglich).<br>"
                f"<span class='muted'>Gültig bis {esc(j['expires_at'][11:16])} Uhr.</span></div>{warn}"
                "<button class='ok' onclick=\"go('freigeben')\">Freigeben</button>"
                "<button class='no' onclick=\"go('ablehnen')\">Ablehnen</button><p id='out'></p>")
    return HTMLResponse(PAGE.format(body=body, jid=jid))


# ---------------------------------------------------------------- llms.txt, robots.txt

def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              timeout=2, cwd=srv().ROOT).stdout.strip() or "unbekannt"
    except Exception:
        return "unbekannt"


_COMMIT: str | None = None
REPO = "https://github.com/BabyToad/tausendkorn-public"


@router.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
def llms_txt(request: Request):
    global _COMMIT
    _COMMIT = _COMMIT or _commit()
    b = str(request.base_url).rstrip("/")
    kult = ", ".join(f"{k['name']} {k['saatstaerke_vorgabe_koerner_m2']}" for k in KULTUREN)
    return f"""# Tausendkorn

> Feld-App für Ackerbaubetriebe: Foto einer zufälligen Handvoll Getreidekörner auf A4 → jedes Korn markiert → Tausendkorngewicht (TKG) → Aussaatmenge in kg/ha je Partie (Hänger) und Sorte. Läuft im Hof-WLAN auf einem Laptop; das iPad ist die Bedienung.

Stand: {_now().date().isoformat()} · Commit {_COMMIT}. Diese Datei beschreibt die Installation unter {b}.

Wichtig für Agenten: Eine Zählung kostet Geld (meist 0,30–0,55 USD, eine harte Obergrenze gibt es noch nicht). Ein Agent kann sie nur beantragen; ausgeführt wird sie erst nach Freigabe durch einen Menschen in der App. Lesen und Rechnen kosten nichts. Prozentwerte sind Zahlen von 0 bis 100. Jede Zahl hat eine Einheit und eine Herkunft der Unsicherheit (`basis`: als_fest, annahme, gemessen, keine); `annahme` ist eine Faustregel, kein gemessenes Intervall. Die Aussaatmenge ersetzt nicht das Abdrehen der Drillmaschine.

## API (/api/v1)

- [OpenAPI-Beschreibung]({b}/openapi.json): Endpunkte dieser Installation mit Schemas
- [Kulturen und Vorgaben]({b}/api/v1/kulturen): Saatstärke-Vorgaben je Kultur mit Spannen und Quellen, ohne Anmeldung
- [Aussaatmenge rechnen]({b}/api/v1/rechner/aussaatmenge): POST, reiner Rechner, speichert nichts, ohne Anmeldung
- [Proben]({b}/api/v1/proben): suchen und lesen (Token mit Scope lesen)
- [Partien]({b}/api/v1/partien?suche=H%C3%A4nger%203): Partien suchen; /api/v1/partien/{{id}} gibt gepooltes TKG und kg/ha mit Spanne und Rechenweg (lesen)
- Zählung beantragen: POST {b}/api/v1/proben/{{id}}/zaehlungen mit Idempotency-Key und If-Match (Scope zaehlen); Stand unter /api/v1/auftraege/{{id}}
- Anmeldung: Header `Authorization: Bearer <Token>`. Tokens erzeugt die Betriebsleitung am Laptop (`uv run python -m app.tokens erstellen`). Keine Ausnahme für localhost.
- Fehler: application/problem+json mit `code` und deutschem `detail`, das sagt, was zu tun ist.

## MCP

- [MCP-Server (stdio)]({REPO}/blob/main/docs/app/MCP.md): `uv run python -m app.mcp_server`, Tools tk_kulturen_auflisten, tk_partien_suchen, tk_saatmenge_fuer_partie, tk_proben_suchen, tk_probe_lesen, tk_aussaatmenge_berechnen, tk_aussaatmenge_pflanzen_berechnen, tk_zaehlung_beantragen, tk_auftrag_lesen, tk_konto_lesen

## Fachliches

- Vorgaben (keimfähige Körner/m²): {kult}
- [Saatgutrechner]({REPO}/blob/main/docs/app/SAATGUTRECHNER.md): kg/ha = keimfähige Körner/m² × TKG [g] / Keimfähigkeit [%]
- [API und Integration]({REPO}/blob/main/docs/app/API.md)

## Geplant (noch nicht verfügbar)

- Proben per API anlegen und ändern, Korrekturen, Partien als eigene Ressource, Webhooks, Admin-PIN, ISO-XML-Export für die Drillmaschine, MCP über HTTP, llms-full.txt
"""


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots_txt():
    return "# Für Sprachmodelle: /llms.txt\nUser-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /freigabe/\n"
