"""uv run python -m app [--mock] [--port 8000]: serve the field app on the LAN."""

import argparse
import os
from pathlib import Path

import uvicorn

from app.net import lan_ip

ap = argparse.ArgumentParser()
ap.add_argument("--mock", action="store_true", help="gespeichertes Ergebnis statt bezahlter Zählung")
ap.add_argument("--port", type=int, default=8000)
args = ap.parse_args()
if args.mock:
    os.environ["TK_MOCK"] = "1"
    # demo samples must not end up in the real history
    os.environ.setdefault("TK_DATA", str(Path(__file__).resolve().parent.parent / "data" / "app-demo"))
print(f"\n  Tausendkorn läuft. Am Laptop http://localhost:{args.port} öffnen:\n"
      f"  dort stehen Code und QR-Code, mit dem sich das iPad koppelt\n"
      f"  (iPad im selben WLAN, Adresse http://{lan_ip()}:{args.port}).\n")
uvicorn.run("app.server:app", host="0.0.0.0", port=args.port)
