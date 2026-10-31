"""Screenshots aller Richtungen (Telefon 375×812, Tablet 768×1024).

Server muss laufen: uv run python -m http.server 8020 --directory design
Aufruf: uv run --no-project --with playwright python design/shared/screens.py
Nutzt das installierte Chrome (channel="chrome"), lädt keinen Browser herunter.
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

BASE = "http://localhost:8020"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DIRS = sys.argv[1:] or ["feldgeraet", "labor", "ackerblatt"]
PHONE = dict(viewport={"width": 375, "height": 812}, device_scale_factor=2, is_mobile=True, has_touch=True)
TABLET = dict(viewport={"width": 768, "height": 1024}, device_scale_factor=2, is_mobile=True, has_touch=True)

# (Name, Gerät, Sprungmarke, Wartezeit ms, ganze Seite)
SHOTS = [
    ("1_start", PHONE, "#start", 800, False),
    ("2_foto", PHONE, "#foto", 800, False),
    ("3_pruefen", PHONE, "#pruefen", 6500, False),
    ("4_pruefen_stelle", PHONE, "?check=2#pruefen", 8000, False),
    ("5_ergebnis", PHONE, "#ergebnis", 2500, True),
    ("6_tablet_pruefen", TABLET, "#pruefen", 6500, False),
    ("7_tablet_ergebnis", TABLET, "#ergebnis", 2500, True),
]


SEM = asyncio.Semaphore(3)


async def one(browser, d, name, dev, frag, wait, full):
    async with SEM:
        await _one(browser, d, name, dev, frag, wait, full)


async def _one(browser, d, name, dev, frag, wait, full):
    ctx = await browser.new_context(**dev)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/{d}/{frag}", wait_until="networkidle")
    # Foto im SVG muss geladen sein, sonst zeigt der Screenshot ein Platzhalterbild.
    await page.evaluate("() => new Promise((r) => { const i = new Image(); i.onload = r; i.onerror = r; i.src = '../shared/probe.jpg'; })")
    await page.wait_for_timeout(wait)
    out = ROOT / d / "screens" / f"{name}.jpg"
    out.parent.mkdir(exist_ok=True)
    await page.screenshot(path=str(out), full_page=full, type="jpeg", quality=85)
    await ctx.close()
    print(out.relative_to(ROOT))


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        await asyncio.gather(*(one(browser, d, *s) for d in DIRS for s in SHOTS))
        await browser.close()


asyncio.run(main())
