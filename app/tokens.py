"""Betriebs-Tokens für /api/v1 (API.md 1, Auth). Nur am Laptop per Kommandozeile:

    uv run python -m app.tokens erstellen --name claude-desktop --scopes lesen,eingaben,zaehlen
    uv run python -m app.tokens liste
    uv run python -m app.tokens widerrufen tok_…

--mock nimmt die Demo-Daten (data/app-demo) wie `python -m app --mock`. Bis es die
Admin-PIN gibt, ist Zugriff auf diesen Laptop die Admin-Berechtigung. Gespeichert wird nur
der SHA-256 des Tokens; das Token selbst wird einmal angezeigt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ("lesen", "eingaben", "zaehlen", "admin")
_lock = threading.Lock()


def data_dir() -> Path:
    return Path(os.environ.get("TK_DATA", ROOT / "data" / "app"))


def _file() -> Path:
    return data_dir() / "api_tokens.json"


def _load() -> list[dict]:
    f = _file()
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def _save(items: list[dict]) -> None:
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(name: str, scopes: list[str], tage: int = 90, autonomie_usd: float = 0.0) -> tuple[str, dict]:
    bad = [s for s in scopes if s not in SCOPES]
    if bad or not scopes:
        raise ValueError(f"Unbekannte Scopes {bad}; erlaubt: {', '.join(SCOPES)}")
    token = "tk_" + secrets.token_urlsafe(32)
    now = datetime.now().astimezone()
    item = {"id": "tok_" + secrets.token_hex(6), "name": name, "scopes": scopes, "sha256": _hash(token),
            "erstellt": now.isoformat(timespec="seconds"),
            "ablauf": (now + timedelta(days=tage)).isoformat(timespec="seconds"),
            "autonomie_usd": float(autonomie_usd), "widerrufen": False}
    with _lock:
        items = _load()
        items.append(item)
        _save(items)
    return token, item


def verify(token: str) -> dict | None:
    """The token record if valid, not expired and not revoked; compares hashes in constant time."""
    h = _hash(token)
    found = None
    for item in _load():
        if secrets.compare_digest(item["sha256"], h):
            found = item
    if not found or found["widerrufen"]:
        return None
    if datetime.fromisoformat(found["ablauf"]) < datetime.now().astimezone():
        return None
    return found


def revoke(tid: str) -> bool:
    with _lock:
        items = _load()
        hit = [i for i in items if i["id"] == tid]
        for i in hit:
            i["widerrufen"] = True
        _save(items)
    return bool(hit)


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m app.tokens", description="Betriebs-Tokens für /api/v1")
    ap.add_argument("--mock", action="store_true", help="Demo-Daten (data/app-demo) statt echter Daten")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("erstellen")
    c.add_argument("--name", required=True)
    c.add_argument("--scopes", default="lesen", help=f"kommagetrennt aus {','.join(SCOPES)}")
    c.add_argument("--tage", type=int, default=90)
    c.add_argument("--autonomie-usd", type=float, default=0.0,
                   help="Zählungen ohne Einzelfreigabe bis zu diesem Betrag pro Tag (Vorgabe 0)")
    sub.add_parser("liste")
    r = sub.add_parser("widerrufen")
    r.add_argument("id")
    a = ap.parse_args()
    if a.mock:
        os.environ.setdefault("TK_DATA", str(ROOT / "data" / "app-demo"))
    if a.cmd == "erstellen":
        token, item = create(a.name, [s.strip() for s in a.scopes.split(",") if s.strip()], a.tage, a.autonomie_usd)
        print(f"Token für {item['name']} ({item['id']}, Scopes {','.join(item['scopes'])}, "
              f"gültig bis {item['ablauf'][:10]}). Wird nur jetzt angezeigt:\n\n{token}\n")
    elif a.cmd == "liste":
        for i in _load():
            state = "widerrufen" if i["widerrufen"] else f"bis {i['ablauf'][:10]}"
            print(f"{i['id']}  {i['name']:<20} {','.join(i['scopes']):<28} {state}  autonomie {i['autonomie_usd']} USD")
    else:
        print("widerrufen" if revoke(a.id) else "nicht gefunden")


if __name__ == "__main__":
    main()
