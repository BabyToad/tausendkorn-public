"""Tausendkorn Feld-App: Foto hochladen, Körner zählen, prüfen, Saatmenge rechnen.

    uv run python -m app [--mock]

TK_MOCK=1 liefert sofort ein gespeichertes Ergebnis (app/mock/result.json) statt die
bezahlte Zählpipeline aufzurufen. Daten liegen in data/app/ (gitignored).
Datenmodell und Regeln: docs/app/DATA.md, Formeln: docs/app/SAATGUTRECHNER.md.

Absicherung im WLAN: Geräte koppeln sich einmal mit einem 6-stelligen Code (oder dem
QR-Code, den die App auf dem Laptop zeigt) und bekommen ein Cookie. Der Laptop selbst
(localhost) braucht keinen Code. Gezählt wird immer nur ein Foto gleichzeitig.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import queue
import re
import secrets
import shutil
import sqlite3
import threading
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from app.net import lan_ip

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("TK_DATA", ROOT / "data" / "app"))
PHOTOS = DATA / "photos"
DB = DATA / "tausendkorn.db"
MOCK = os.environ.get("TK_MOCK", "") not in ("", "0", "false")
MOCK_DELAY = float(os.environ.get("TK_MOCK_DELAY", "4"))
DISPLAY_MAX = 2000  # long side of the preview image the app shows
FORMEL_VERSION = 1
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
MAX_PIXELS = 60_000_000   # a 50 MP phone photo still fits
MIN_SIDE = 800            # smaller photos cannot be counted reliably
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
# Unsicherheit der Kornzahl, wenn nicht geprüft wurde: ± max(rel × Zahl, min) Körner.
# Gemessen: Pipeline v1.0.2, Holdout Within-Session, 30 Bilder, 170–800 Körner
# (docs/RESULTS.md "Finale Messung Pipeline v1.0.2"): relativer Fehler Median 1,7 %,
# p80 2,7 %, p90 3,1 %, max. 4,4 %; absolut Median 5,5, p90 10, max. 14 Körner.
# ±3 % ≈ p90, mindestens ±5 Körner. Auf dem Test-Satz (anderer Tag) gab es einen
# Ausreißer von −58 bei 1000 Körnern (Hartweizen), darum der zweite Satz im Hinweis.
ERROR_BAND = {
    "rel": 0.03, "min": 5, "gemessen": True,
    # nachgezählt in results/argon_v1.0.2: innerhalb ±3 % lagen 26/30 Holdout- und 5/6 Testfotos
    "hinweis": "Beobachtet, keine Garantie: Bei 26 von 30 Holdout-Fotos und 5 von 6 Testfotos "
               "lag die Zählung innerhalb von ±3 %; an anderen Tagen teils größer.",
}

JSON_COLS = ("points", "points_model", "check_here", "corrections", "attempts")
EXTRA_COLS = {  # added to older databases on start
    "points_model": "TEXT", "corrections": "TEXT", "attempts": "TEXT", "provenance": "TEXT",
    "modus": "TEXT", "saatstaerke": "REAL", "formel_version": "INTEGER", "koerner_m2": "REAL",
    "updated_at": "TEXT", "deleted_at": "TEXT", "client_id": "TEXT",
    "pruefung": "TEXT",
    "abdreh_m2": "REAL", "abdreh_kg": "REAL",
    "precheck": "TEXT",
    "partie_id": "TEXT",  # mehrere Handvoll derselben Partie (ROADMAP 2.2); vom ersten Foto vergeben
    # Empfehlung für die Partie (ab 2 gewogenen Handvoll), gespeichert pro Handvoll:
    "partie_tkg": "REAL",   # 1000 × Σ Gewicht / Σ Körner
    "drill_kg_ha": "REAL",  # worauf die Drillmaschine gestellt wird: Partie-Wert, sonst eigener  # Foto-Vorprüfung: {"metrics", "warnings", "override"}  # Abdrehprobe: Fläche laut Drillmaschine, Sollmenge  # NULL offen · 'uebersprungen' · 'geprueft' · 'keine' (nichts zu prüfen)
}

PHOTOS.mkdir(parents=True, exist_ok=True)
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
_db_lock = threading.Lock()
_queue: queue.Queue[int] = queue.Queue()
_queued: set[int] = set()     # waiting or counting; guards against double starts
_queued_lock = threading.Lock()


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def secret(name: str, make) -> str:
    """Pairing code and cookie token survive restarts, so paired iPads stay paired."""
    f = DATA / name
    if not f.exists():
        f.write_text(make(), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


PAIR_CODE = os.environ.get("TK_CODE") or secret("pair_code.txt", lambda: f"{secrets.randbelow(10**6):06d}")
TOKEN = secret("device_token.txt", lambda: secrets.token_hex(24))
_pair_failures: list[float] = []


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _db_lock, db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, kultur TEXT, sorte TEXT,
            haenger TEXT, status TEXT, error TEXT, photo TEXT, width INTEGER, height INTEGER,
            count INTEGER, count_model INTEGER, points TEXT, check_here TEXT, cost_usd REAL,
            seconds REAL, weight_g REAL, keimfaehigkeit REAL, feldaufgang REAL, plants_m2 REAL,
            tkg REAL, kg_ha REAL, notes TEXT)""")
        have = {r[1] for r in con.execute("PRAGMA table_info(samples)")}
        for col, typ in EXTRA_COLS.items():
            if col not in have:
                con.execute(f"ALTER TABLE samples ADD COLUMN {col} {typ}")
        # One sample per device-generated id, enforced by the database (idempotent send).
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS samples_client_id ON samples(client_id)")
        # Rows from before the correction log: their points may already be edited.
        con.execute("UPDATE samples SET points_model=points, provenance='legacy' "
                    "WHERE points_model IS NULL AND points IS NOT NULL")
        con.execute("UPDATE samples SET modus='pflanzen', formel_version=0 "
                    "WHERE modus IS NULL AND plants_m2 IS NOT NULL")
        # Older samples get their own Partie, so "weitere Handvoll" can join them.
        con.execute("UPDATE samples SET partie_id=lower(hex(randomblob(16))) WHERE partie_id IS NULL")
        # Work that was running when the server stopped will never finish:
        # an upload without photo holds nothing, so free its client_id for the resend;
        # a photo that was stored but not counted yet can be counted again.
        con.execute("DELETE FROM samples WHERE photo IS NULL")
        con.execute("UPDATE samples SET status='fehler', error='Zählung unterbrochen' "
                    "WHERE status IN ('zaehlt', 'neu')")


def get_row(sid: int, con: sqlite3.Connection | None = None) -> dict:
    if con is None:
        with _db_lock, db() as c:
            row = c.execute("SELECT * FROM samples WHERE id=? AND deleted_at IS NULL", (sid,)).fetchone()
    else:
        row = con.execute("SELECT * FROM samples WHERE id=? AND deleted_at IS NULL", (sid,)).fetchone()
    if not row:
        raise HTTPException(404, "Probe nicht gefunden")
    d = dict(row)
    for k in JSON_COLS:
        d[k] = json.loads(d[k] or "[]")
    d["precheck"] = json.loads(d["precheck"]) if d.get("precheck") else None
    return d


def write(con: sqlite3.Connection, sid: int, **fields) -> None:
    fields["updated_at"] = now()
    for k in (*JSON_COLS, "precheck"):
        if k in fields and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k])
    sets = ", ".join(f"{k}=?" for k in fields)
    con.execute(f"UPDATE samples SET {sets} WHERE id=?", (*fields.values(), sid))


def update(sid: int, **fields) -> None:
    with _db_lock, db() as con:
        write(con, sid, **fields)


def replay(points_model: list, corrections: list) -> list:
    """Current points [[id, x, y], …] = model points + every event not undone (DATA.md 3)."""
    undone = {ev["of"] for ev in corrections if ev.get("op") == "undo"}
    pts = {f"m{i}": (p[-2], p[-1]) for i, p in enumerate(points_model)}
    for ev in corrections:
        if ev.get("e") in undone:
            continue
        if ev.get("op") == "add":
            pts[ev["id"]] = (ev["x"], ev["y"])
        elif ev.get("op") == "remove":
            pts.pop(ev["id"], None)
    return [[k, x, y] for k, (x, y) in pts.items()]


def calc(d: dict) -> tuple[float | None, float | None, float | None]:
    """SAATGUTRECHNER.md 2, unrounded: TKG = m / n × 1000.
    keimfaehig: K = S / (KF/100), kg/ha = S × TKG / KF.
    pflanzen:   K = P / (KF/100) / (FA/100), kg/ha = P × TKG × 100 / (KF × FA);
                fehlender Feldaufgang zählt als 100 %, 0 % ist schon bei der Eingabe abgelehnt."""
    if not d["count"] or not d["weight_g"]:
        return None, None, None
    tkg = d["weight_g"] / d["count"] * 1000
    return (tkg, *rate(d, tkg))


def rate(d: dict, tkg: float) -> tuple[float | None, float | None]:
    """Körner/m² and kg/ha for this sample's targets and a given TKG."""
    kf = d["keimfaehigkeit"]
    if d["modus"] == "pflanzen":
        if not kf or not d["plants_m2"]:
            return None, None
        fa = 100 if d["feldaufgang"] is None else d["feldaufgang"]
        return d["plants_m2"] / (kf / 100) / (fa / 100), d["plants_m2"] * tkg * 100 / (kf * fa)
    if not kf or not d["saatstaerke"]:
        return None, None
    return d["saatstaerke"] / (kf / 100), d["saatstaerke"] * tkg / kf


def half_up(x: float) -> int:
    """Round halves up like Math.round in the app (not Python's round-half-even)."""
    return math.floor(x + 0.5)


def derive_partie(con: sqlite3.Connection, partie_id: str | None) -> None:
    """Store the Partie recommendation on every handful: pooled TKG over the weighed ones,
    the kg/ha the drill is set to (from each handful's own targets) and the Abdrehprobe."""
    if not partie_id:
        return
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM samples WHERE partie_id=? AND deleted_at IS NULL AND status='fertig'", (partie_id,))]
    weighed = [r for r in rows if r["count"] and r["weight_g"]]
    pooled = (1000 * sum(r["weight_g"] for r in weighed) / sum(r["count"] for r in weighed)
              if len(weighed) >= 2 else None)
    for r in rows:
        drill = rate(r, pooled)[1] if pooled else r["kg_ha"]
        # Sollmenge der Abdrehprobe [kg] = kg/ha × Fläche [m²] / 10 000 (SAATGUTRECHNER.md 2.4),
        # mit der ganzzahligen kg/ha, auf die die Drillmaschine eingestellt wird
        abdreh = half_up(drill) * r["abdreh_m2"] / 10_000 if drill is not None and r["abdreh_m2"] else None
        write(con, r["id"], partie_tkg=pooled, drill_kg_ha=drill, abdreh_kg=abdreh)


def derive(con: sqlite3.Connection, sid: int) -> None:
    """Recompute points, count, TKG and kg/ha inside the caller's transaction."""
    d = get_row(sid, con)
    if d["points_model"] or d["status"] == "fertig":
        d["points"] = replay(d["points_model"], d["corrections"])
        d["count"] = len(d["points"])
    tkg, kpm2, kg_ha = calc(d)
    write(con, sid, points=d["points"], count=d["count"], tkg=tkg, koerner_m2=kpm2, kg_ha=kg_ha,
          drill_kg_ha=kg_ha, abdreh_kg=None,
          formel_version=FORMEL_VERSION if kg_ha is not None else d["formel_version"])
    derive_partie(con, d["partie_id"])


def save_photo(src: Path, dest_stem: str) -> tuple[str, int, int]:
    """Store the upright full-size photo (pipeline input) plus a smaller preview."""
    im = Image.open(src)
    if im.width * im.height > MAX_PIXELS:
        raise ValueError("zu groß")
    im = ImageOps.exif_transpose(im).convert("RGB")
    if min(im.size) < MIN_SIDE:
        raise ValueError("zu klein")
    full = PHOTOS / f"{dest_stem}.jpg"
    im.save(full, quality=92)
    w, h = im.size
    im.thumbnail((DISPLAY_MAX, DISPLAY_MAX))
    im.save(PHOTOS / f"{dest_stem}_klein.jpg", quality=85)
    return full.name, w, h


def incomplete(res: dict) -> bool:
    tiles = res.get("first_pass", {}).get("tiles", [])
    return bool(res.get("failed_tiles")) or any(t.get("pred") is None for t in tiles) \
        or any(n.get("failed") for n in res.get("notes", []))


INCOMPLETE = "Zählung unvollständig, bitte erneut versuchen."


def run_count(sid: int) -> None:
    started = time.time()
    try:
        row = get_row(sid)
        if MOCK:
            res = json.loads((HERE / "mock" / "result.json").read_text(encoding="utf-8"))
            # the marks belong to this photo (app/mock/foto.jpg, in the repo); never draw
            # them on the uploaded photo
            mock_photo = ROOT / res["photo"]
            if not mock_photo.exists():
                update(sid, status="fehler", error=f"Demo-Foto fehlt ({res['photo']}). "
                                                   "Bitte das Repository vollständig auschecken.")
                return
            name, w, h = save_photo(mock_photo, Path(row["photo"]).stem)
            update(sid, width=w, height=h)
            time.sleep(MOCK_DELAY)
        else:
            from tausendkorn.pipeline import count_kernels
            res = count_kernels(PHOTOS / row["photo"])
        if incomplete(res):  # never show a partial number
            update(sid, status="fehler", error=INCOMPLETE, cost_usd=res.get("cost_usd"))
            return
        model = [[round(x, 1), round(y, 1)] for x, y in res["points"]]
        spots = [{**c, "done": False} for c in res.get("check_here", [])]
        with _db_lock, db() as con:
            write(con, sid, status="fertig", error=None, count_model=len(model), points_model=model,
                  corrections=[], provenance="model", check_here=spots,
                  pruefung=None if spots else "keine",
                  cost_usd=0 if MOCK else res.get("cost_usd"), seconds=round(time.time() - started, 1))
            derive(con, sid)
    except Exception as e:  # shown to the user, details in the server log
        traceback.print_exc()
        msg = INCOMPLETE if type(e).__name__ == "IncompleteCount" else \
            f"Das Zählen hat nicht geklappt ({type(e).__name__}). Bitte nochmal versuchen."
        update(sid, status="fehler", error=msg)


def worker() -> None:
    """One count at a time: protects the API budget and keeps the laptop responsive."""
    while True:
        sid = _queue.get()
        try:
            run_count(sid)
        finally:
            with _queued_lock:
                _queued.discard(sid)


def start_count(sid: int) -> bool:
    """Queue a count once; a second call while it waits or runs (double tap) is a no-op."""
    with _queued_lock:
        if sid in _queued:
            return False
        row = get_row(sid)
        if row["status"] in ("zaehlt", "fertig") or not row["photo"]:
            return False
        fields = {}
        if row["points_model"]:  # keep the earlier attempt (DATA.md 4)
            fields = dict(attempts=row["attempts"] + [{
                "at": row["updated_at"], "count_model": row["count_model"],
                "points_model": row["points_model"], "corrections": row["corrections"]}],
                points_model=[], corrections=[], points=[], count=None, count_model=None)
        update(sid, status="zaehlt", error=None, **fields)
        _queued.add(sid)
        _queue.put(sid)
    return True


init_db()
threading.Thread(target=worker, daemon=True).start()
app = FastAPI(title="Tausendkorn")


def is_local(request: Request) -> bool:
    return (request.client.host if request.client else "") in LOCAL_HOSTS


def paired_response(resp: Response) -> Response:
    resp.set_cookie("tk", TOKEN, max_age=400 * 24 * 3600, httponly=True, samesite="lax")
    return resp


def check_code(code: str) -> HTTPException | None:
    """Shared by the form and the QR link: at most 10 wrong codes per 10 minutes."""
    recent = [t for t in _pair_failures if t > time.time() - 600]
    _pair_failures[:] = recent
    if len(recent) >= 10:
        return HTTPException(429, "Zu viele Versuche. Bitte 10 Minuten warten.")
    if not secrets.compare_digest(code.strip().encode(), PAIR_CODE.encode()):
        _pair_failures.append(time.time())
        return HTTPException(403, "Code stimmt nicht. Er steht auf dem Laptop.")
    return None


@app.middleware("http")
async def guard(request: Request, call_next):
    path = request.url.path
    if path == "/" and "k" in request.query_params:  # QR code link
        ok = check_code(request.query_params["k"]) is None
        return paired_response(RedirectResponse("/")) if ok else RedirectResponse("/")
    # /api/v1 checks Bearer token or cookie itself, with no localhost exception (app/api_v1.py)
    if path.startswith("/api/") and not path.startswith("/api/v1/") and path != "/api/pair" \
            and not is_local(request) \
            and not secrets.compare_digest(request.cookies.get("tk", ""), TOKEN):
        return JSONResponse({"detail": "nicht gekoppelt"}, status_code=401)
    resp = await call_next(request)
    # iPads keep old app files otherwise; ETags still make reloads cheap.
    resp.headers.setdefault("Cache-Control", "no-cache")
    return resp


class Pair(BaseModel):
    code: str


@app.post("/api/pair")
def pair(p: Pair):
    err = check_code(p.code)
    if err:
        raise err
    return paired_response(JSONResponse({"ok": True}))


@app.get("/api/pairing")
def pairing(request: Request):
    """Only the laptop itself sees the code and the QR code for the iPad."""
    if not is_local(request):
        raise HTTPException(403, "nur am Laptop")
    port = request.url.port or 80
    url = f"http://{lan_ip()}:{port}/?k={PAIR_CODE}"
    svg = ""
    try:
        import qrcode
        import qrcode.image.svg
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12)
        svg = img.to_string(encoding="unicode")
    except Exception:
        traceback.print_exc()
    return {"code": PAIR_CODE, "url": url, "svg": svg}


@app.get("/api/config")
def config():
    with _db_lock, db() as con:
        rows = con.execute("SELECT kultur, sorte, haenger FROM samples WHERE deleted_at IS NULL "
                           "ORDER BY id DESC LIMIT 200").fetchall()
    uniq = lambda key: list(dict.fromkeys(r[key] for r in rows if r[key]))[:8]
    return {"mock": MOCK, "band": ERROR_BAND, "recent": {"kultur": uniq("kultur"),
            "sorte": uniq("sorte"), "haenger": uniq("haenger")}}


@app.post("/api/samples")
def create_sample(photo: UploadFile = File(...), kultur: str = Form(""), sorte: str = Form(""),
                  haenger: str = Form(""), token: str = Form(""), partie_id: str = Form("")):
    # token: generated on the device per photo; the UNIQUE index makes a resend a no-op.
    client_id = token if re.fullmatch(r"[A-Za-z0-9-]{8,64}", token or "") else uuid.uuid4().hex
    with _db_lock, db() as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO samples (client_id, created_at, updated_at, kultur, sorte, "
            "haenger, status, modus, partie_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (client_id, now(), now(), kultur.strip()[:80] or "Winterweizen", sorte.strip()[:80],
             haenger.strip()[:80], "neu", "keimfaehig",
             partie_id if re.fullmatch(r"[A-Za-z0-9-]{8,64}", partie_id or "") else uuid.uuid4().hex))
        if not cur.rowcount:  # already sent (retry or double tap): same sample
            return {"id": con.execute("SELECT id FROM samples WHERE client_id=?", (client_id,)).fetchone()["id"]}
        sid = cur.lastrowid
    stem = uuid.uuid4().hex  # own file names, never shared between requests
    tmp = PHOTOS / f"{stem}.upload"
    try:
        size = 0
        with tmp.open("wb") as f:
            while chunk := photo.file.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Das Foto ist zu groß (über 30 MB).")
                f.write(chunk)
        try:
            name, w, h = save_photo(tmp, stem)
        except Exception:
            raise HTTPException(400, "Das Bild konnte nicht gelesen werden oder ist zu klein. "
                                     "Bitte noch einmal fotografieren.")
    except BaseException:
        with _db_lock, db() as con:
            con.execute("DELETE FROM samples WHERE id=?", (sid,))  # the device may resend
        raise
    finally:
        tmp.unlink(missing_ok=True)
    update(sid, photo=name, width=w, height=h)
    # Check the photo before paying for a count; a warning waits for the farmer.
    pre = run_precheck(PHOTOS / name)
    if pre["warnings"]:
        update(sid, status="warnung", precheck=pre)
    else:
        update(sid, precheck=pre)
        start_count(sid)
    return {"id": sid}


def run_precheck(path: Path) -> dict:
    """If the check itself fails, the farmer decides as with any warning (never a silent paid count)."""
    try:
        from app.precheck import check, measure
        with Image.open(path) as im:
            m = measure(im.convert("RGB"))
        return {"metrics": m, "warnings": check(m), "override": False}
    except Exception as e:
        traceback.print_exc()
        return {"metrics": None, "error": f"{type(e).__name__}: {e}"[:300], "override": False,
                "warnings": [{"kind": "fehler", "text": "Das Foto konnte nicht geprüft werden. "
                              "Wenn Blatt und Körner gut zu sehen sind, trotzdem zählen."}]}


@app.post("/api/samples/{sid}/count")
def recount(sid: int):
    d = get_row(sid)
    if d["status"] == "warnung" and d["precheck"]:  # "Trotzdem zählen"
        update(sid, precheck={**d["precheck"], "override": True})
    return {"started": start_count(sid)}


@app.get("/api/samples")
def list_samples():
    with _db_lock, db() as con:
        rows = con.execute("SELECT id, created_at, kultur, sorte, haenger, status, count, weight_g, "
                           "tkg, kg_ha, drill_kg_ha, check_here, pruefung, partie_id FROM samples WHERE deleted_at IS NULL "
                           "AND photo IS NOT NULL ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        spots = json.loads(d.pop("check_here") or "[]")
        d["unchecked"] = sum(not c.get("done") for c in spots)
        d["pruefung"] = "keine" if not spots else "geprueft" if not d["unchecked"] else d["pruefung"]
        out.append(d)
    groups: dict[str, list[dict]] = {}
    for d in sorted(out, key=lambda d: d["id"]):
        groups.setdefault(d.pop("partie_id") or f"x{d['id']}", []).append(d)
    for g in groups.values():  # "Handvoll 2 von 3"
        for i, d in enumerate(g):
            d["partie_pos"], d["partie_size"] = i + 1, len(g)
    return out


def review_state(r: dict) -> str | None:
    """Same rule as reviewState() in the app."""
    spots = json.loads(r["check_here"] or "[]") if isinstance(r["check_here"], str) else r["check_here"]
    if not spots:
        return "keine"
    return "geprueft" if all(c.get("done") for c in spots) else r["pruefung"]


def partie(d: dict) -> dict:
    """All counted handfuls of this sample's Partie; TKG = 1000 × Σ Gewicht / Σ Körner
    over the weighed ones (not the mean of single TKGs)."""
    with _db_lock, db() as con:
        rows = [dict(r) for r in con.execute(
            "SELECT id, count, weight_g, tkg, check_here, pruefung FROM samples WHERE partie_id=? "
            "AND deleted_at IS NULL AND status='fertig' ORDER BY id", (d["partie_id"],))]
    weighed = [r for r in rows if r["count"] and r["weight_g"]]
    n, w = sum(r["count"] for r in weighed), sum(r["weight_g"] for r in weighed)
    # same rule as a single handful: only "geprueft" removes the uncertainty; an
    # automatic count without flagged spots ("keine") still has its count error
    unchecked = any(review_state(r) != "geprueft" for r in weighed)
    return {"size": len(rows), "pos": next((i + 1 for i, r in enumerate(rows) if r["id"] == d["id"]), None),
            "samples": [{"id": r["id"], "count": r["count"], "weight_g": r["weight_g"], "tkg": r["tkg"]} for r in rows],
            "weighed": len(weighed), "count": n, "weight_g": w,
            "tkg": 1000 * w / n if len(weighed) >= 2 else None, "unchecked": unchecked}


@app.get("/api/samples/{sid}")
def sample(sid: int):
    d = get_row(sid)
    if d["partie_id"]:
        d["partie"] = partie(d)
    if d["status"] == "zaehlt":
        waiting = list(_queue.queue)  # the sample being counted right now is not in here
        d["queue_ahead"] = waiting.index(sid) + 1 if sid in waiting else 0
        # elapsed on the server's clock, so a wrong device clock cannot skew the display
        d["elapsed_s"] = max(0.0, (datetime.now().astimezone() - datetime.fromisoformat(d["updated_at"])).total_seconds())
    return d


Pos = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Pct = Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)]
Target = Annotated[float, Field(gt=0, le=5000, allow_inf_nan=False)]
Area = Annotated[float, Field(ge=1, le=10_000, allow_inf_nan=False)]  # m², höchstens 1 ha


class Patch(BaseModel):
    """Missing field = unchanged, null = cleared; no silent replacement of bad values."""
    kultur: str | None = Field(None, max_length=80)
    sorte: str | None = Field(None, max_length=80)
    haenger: str | None = Field(None, max_length=80)
    weight_g: Pos | None = None
    keimfaehigkeit: Pct | None = None
    feldaufgang: Pct | None = None
    plants_m2: Target | None = None
    saatstaerke: Target | None = None
    abdreh_m2: Area | None = None
    modus: str | None = Field(None, pattern="^(keimfaehig|pflanzen)$")
    notes: str | None = Field(None, max_length=2000)
    spot_done: int | None = None  # index into check_here the farmer confirmed
    pruefung: str | None = Field(None, pattern="^uebersprungen$")  # "Ergebnis übernehmen"


@app.patch("/api/samples/{sid}")
def patch_sample(sid: int, p: Patch):
    fields = p.model_dump(exclude_unset=True)
    with _db_lock, db() as con:
        d = get_row(sid, con)
        spot = fields.pop("spot_done", None)
        if spot is not None and 0 <= spot < len(d["check_here"]):
            d["check_here"][spot]["done"] = True
            fields["check_here"] = d["check_here"]
            if all(c.get("done") for c in d["check_here"]):
                fields["pruefung"] = "geprueft"
        # All spots confirmed means checked, even if another device sent a stale "skip".
        if d["check_here"] and all(c.get("done") for c in d["check_here"]):
            fields["pruefung"] = "geprueft"
        if fields:
            write(con, sid, **fields)
        derive(con, sid)
    return sample(sid)


class Corrections(BaseModel):
    corrections: list[dict]


@app.put("/api/samples/{sid}/corrections")
def put_corrections(sid: int, body: Corrections):
    """The log only grows: the client sends the whole list, old events must be unchanged."""
    with _db_lock, db() as con:
        d = get_row(sid, con)
        old, new = d["corrections"], body.corrections
        if new[:len(old)] != old:
            raise HTTPException(409, "Korrekturen sind veraltet. Bitte Seite neu laden.")
        for ev in new[len(old):]:
            ok = ev.get("op") in ("add", "remove", "undo") and (
                ev["op"] != "add" or all(isinstance(ev.get(c), (int, float)) and math.isfinite(ev[c])
                                         for c in ("x", "y")))
            if not ok:
                raise HTTPException(400, "Ungültige Korrektur.")
        write(con, sid, corrections=new)
        derive(con, sid)
    return sample(sid)


@app.delete("/api/samples/{sid}")
def delete_sample(sid: int):
    get_row(sid)
    with _db_lock, db() as con:  # Papierkorb; Foto und Daten bleiben erhalten
        write(con, sid, deleted_at=now())
        derive_partie(con, con.execute("SELECT partie_id FROM samples WHERE id=?", (sid,)).fetchone()["partie_id"])
    return {"ok": True}


@app.get("/api/samples/{sid}/photo")
def photo(sid: int):
    d = get_row(sid)
    if not d["photo"]:
        raise HTTPException(404, "Foto fehlt")
    small = PHOTOS / f"{Path(d['photo']).stem}_klein.jpg"
    return FileResponse(small if small.exists() else PHOTOS / d["photo"],
                        headers={"Cache-Control": "no-cache"})


@app.get("/api/export.csv")
def export():
    cols = {"id": "Nr", "created_at": "Datum", "kultur": "Kultur", "sorte": "Sorte",
            "haenger": "Partie/Hänger", "count": "Körner", "count_model": "Körner (automatisch)",
            "weight_g": "Gewicht g", "tkg": "TKG Probe g (inkl. Besatz)", "keimfaehigkeit": "Keimfähigkeit %",
            "modus": "Modus", "saatstaerke": "Saatstärke keimf. Körner/m²",
            "plants_m2": "Pflanzen/m²", "feldaufgang": "Feldaufgang %",
            "koerner_m2": "Körner/m² ablegen", "kg_ha": "Aussaatmenge kg/ha",
            "partie_tkg": "TKG Partie g (inkl. Besatz)", "drill_kg_ha": "Drillmaschine kg/ha",
            "abdreh_m2": "Abdrehfläche m²", "abdreh_kg": "Abdrehprobe kg",
            "formel_version": "Formel", "pruefung": "Prüfung", "partie_id": "Partie-ID",
            "notes": "Notiz", "photo": "Foto"}
    digits = {"tkg": 2, "partie_tkg": 2, "koerner_m2": 0, "kg_ha": 1, "drill_kg_ha": 1, "abdreh_kg": 3}
    with _db_lock, db() as con:
        rows = con.execute(f"SELECT {', '.join(cols)} FROM samples WHERE deleted_at IS NULL "
                           "AND photo IS NOT NULL ORDER BY id").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")  # Excel (de) opens ; directly
    w.writerow(cols.values())
    for r in rows:
        w.writerow(["" if v is None else str(round(v, digits.get(k, 2))).replace(".", ",")
                    if isinstance(v, float) else v for k, v in zip(cols, r)])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=tausendkorn.csv"})


# Web-Pitch-Deck des Teams (pitch/web/, eigenständige Seite), falls vorhanden.
if (ROOT / "pitch" / "web").is_dir():
    app.add_api_route("/pitch", lambda: RedirectResponse("/pitch/"), include_in_schema=False)
    app.mount("/pitch", StaticFiles(directory=ROOT / "pitch" / "web", html=True), name="pitch")
from app.api_v1 import install  # noqa: E402  (/api/v1, /freigabe, llms.txt: before the static mount)
install(app)
app.mount("/", StaticFiles(directory=HERE / "static", html=True), name="static")
