"""Galerie results/index.html aus den Ergebnis-JSONs bauen (ohne Abhängigkeiten).

    uv run python results/build_index.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARGON = HERE / "argon_v1.0.2"
YOLO = HERE / "yolo11s"
ART = {"oats-s": "Hafer", "barley-w": "Gerste", "wheat-w": "Weizen", "durum-w": "Hartweizen", "rye-w": "Roggen"}

CSS = """
:root{--bg:#F4F5F3;--surface:#FFF;--sunken:#E9ECEB;--ink:#14181B;--ink-2:#434A50;--rule:#B9C0C4;
--mark:#005FB8;--unsure:#E08A00;--unsure-ink:#8A4B00;--unsure-soft:#FFF5E6;--bad:#A3261B;--photo-bg:#2A2F33;
--f-sans:"IBM Plex Sans",-apple-system,"Segoe UI",Roboto,system-ui,sans-serif;
--f-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--f-sans)}
main{max-width:1100px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:34px;margin:0 0 4px}h2{font-size:22px;margin:40px 0 8px;border-bottom:1.5px solid var(--rule);padding-bottom:4px}
.lead{color:var(--ink-2);font-size:18px;max-width:760px}
.label{font:600 12px var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2)}
.num{font-family:var(--f-mono);font-weight:600}
table{border-collapse:collapse;width:100%;background:var(--surface);font-size:15px}
th,td{border-bottom:1px solid var(--sunken);padding:6px 8px;text-align:left}th{font:600 12px var(--f-mono);text-transform:uppercase;color:var(--ink-2)}
td.n{font-family:var(--f-mono);text-align:right}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--surface);border-radius:12px;overflow:hidden;border:1.5px solid var(--sunken)}
.card a.img{display:block;background:var(--photo-bg)}.card img{width:100%;height:240px;object-fit:cover;display:block}
.card .body{padding:12px 14px}.card h3{margin:0 0 4px;font-size:18px}
.note{background:var(--unsure-soft);border-left:4px solid var(--unsure);padding:10px 14px;border-radius:8px;color:var(--unsure-ink)}
.legend span{display:inline-block;margin-right:16px}.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:-1px}
a{color:var(--mark)}footer{margin-top:48px;color:var(--ink-2);font-size:14px}
@media (max-width:600px){.card img{height:200px}table{font-size:13px}}
"""


def load(split: str) -> list[dict]:
    out = []
    for f in sorted((ARGON / split).glob("*.jpg.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        y = YOLO / split / f.name
        r["yolo"] = json.loads(y.read_text(encoding="utf-8"))["pred"] if y.exists() else None
        r["json"] = f.relative_to(HERE).as_posix()
        r["overlay"] = f"overlays/{split}__{f.name.removesuffix('.json')}"
        out.append(r)
    return out


def de(x: float, n: int = 1) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def mae(rows, key):
    e = [abs(r[key] - r["true"]) for r in rows if r.get(key) is not None]
    return sum(e) / len(e) if e else float("nan")


def card(r: dict, text: str = "") -> str:
    err = r["count"] - r["true"]
    pr = f" · P {de(r["precision"], 3)} / R {de(r["recall"], 3)}" if r.get("precision") is not None else ""
    return (f'<div class="card"><a class="img" href="{r["overlay"]}"><img loading="lazy" src="{r["overlay"]}" '
            f'alt="Overlay {html.escape(r["file_name"])}"></a><div class="body"><div class="label">'
            f'{ART.get(r["species"], r["species"])} · {html.escape(r["camera"])}</div><h3><span class="num">{r["count"]}</span> '
            f'gezählt, Label <span class="num">{r["true"]}</span> ({err:+d})</h3><div class="label">{pr.strip(" ·")}</div>'
            f'{text}<div><a href="{r["json"]}">Punkte (JSON)</a></div></div></div>')


def table(rows: list[dict]) -> str:
    head = "<tr><th>Bild</th><th>Art</th><th>Label</th><th>Argon</th><th>Fehler</th><th>YOLO</th><th>Fehler</th><th>Kosten $</th></tr>"
    body = ""
    for r in rows:
        y = r["yolo"]
        body += (f'<tr><td><a href="{r["overlay"]}">{html.escape(r["file_name"].split("/")[-1])}</a></td>'
                 f'<td>{ART.get(r["species"], r["species"])}</td><td class="n">{r["true"]}</td><td class="n">{r["count"]}</td>'
                 f'<td class="n">{r["count"] - r["true"]:+d}</td><td class="n">{y if y is not None else "–"}</td>'
                 f'<td class="n">{(y - r["true"]) if y is not None else 0:+d}</td><td class="n">{de(r.get("cost_usd") or 0, 2)}</td></tr>')
    return f"<table>{head}{body}</table>"


def main() -> None:
    hold, test = load("holdout"), load("test")
    picks = []
    for sp in ("oats-s", "barley-w", "wheat-w"):  # je Art das Bild mit dem Median-Fehler
        rs = sorted((r for r in hold if r["species"] == sp), key=lambda r: abs(r["count"] - r["true"]))
        if rs:
            picks.append(rs[len(rs) // 2])
    durum = next(r for r in test if r["species"] == "durum-w")
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Tausendkorn Ergebnisse</title>
<style>{CSS}</style></head><body><main>
<div class="label">Team Goldpfanne · Tausendkorn-Hackathon 2026</div>
<h1>Ergebnisse der Kornzählung</h1>
<p class="lead">Eingefrorene Pipeline v1.0.2 (Gemini 4 Argon, adaptive Kacheln, Prüfdurchgang), einmal gelaufen
auf Holdout und Test. Klick auf ein Bild öffnet das Overlay in voller Größe.</p>
<p class="legend"><span><i class="dot" style="background:#00C83C"></i>Treffer</span>
<span><i class="dot" style="background:#E61414"></i>Fehlalarm (Kreuz)</span>
<span><i class="dot" style="background:#FFD200"></i>übersehen (Ring)</span>
<span><i class="dot" style="background:#005FB8"></i>Marke ohne Punkt-Label (Test)</span></p>

<h2>Auf einen Blick</h2>
<table><tr><th>Satz</th><th>Bilder</th><th>Argon MAE</th><th>YOLO11s MAE, dieselben Bilder</th></tr>
<tr><td>Holdout, gleiche Aufnahmetage wie Training</td><td class="n">{len(hold)} / 40</td><td class="n">{de(mae(hold, "count"))}</td><td class="n">{de(mae(hold, "yolo"))}</td></tr>
<tr><td>Test count_1000, anderer Tag, Roggen neu</td><td class="n">{len(test)} / 85</td><td class="n">{de(mae(test, "count"))}</td><td class="n">{de(mae(test, "yolo"))}</td></tr></table>
<p>Hartweizen fehlt im Holdout (Budget-Stopp). Holdout teilt Sessions mit dem Training (Abweichung vom Protokoll,
siehe <code>docs/PROTOCOL.md</code>). Alle Zahlen: <code>docs/RESULTS.md</code>.</p>

<h2>Je Art ein Holdout-Bild (mittlerer Fehler)</h2>
<div class="grid">{"".join(card(r) for r in picks)}</div>

<h2>Hartweizen-Testserie: ungeklärte Abweichung</h2>
<p class="note">Ungeklärt: Argon zählt 942, YOLO auf demselben Foto 948; über 17 Fotos zählt YOLO 911–976.
Gemeinsame Unterzählung verdeckter Körner und eine Abweichung der Probe vom Label sind nicht ausgeschlossen; ein fehlender
50er-Becher ist nur eine Hypothese. Gewertet wird unverändert gegen 1000. Details: <code>docs/befund/DURUM_COUNT_1000.md</code>.</p>
<div class="grid">{card(durum)}
<div class="card"><a class="img" href="befund/durum_crop.jpg"><img loading="lazy" src="befund/durum_crop.jpg" alt="Ausschnitt Hartweizen"></a><div class="body"><h3>Ausschnitt</h3>Jedes sichtbare Korn trägt einen Argon- und einen YOLO-Punkt.</div></div>
<div class="card"><a class="img" href="befund/durum_timeline.jpg"><img loading="lazy" src="befund/durum_timeline.jpg" alt="Zwei Auslagen"></a><div class="body"><h3>Zwei Auslagen</h3>16:57 und ab 18:51, beide Auslagen ergeben ähnliche Zahlen.</div></div></div>

<h2>Alle Testbilder</h2>{table(test)}
<h2>Alle Holdout-Bilder</h2>{table(hold)}

<footer>Fotos und Punkt-Labels: <a href="https://huggingface.co/datasets/SmartFarmingLab/corn1000">SmartFarmingLab/corn1000</a>,
CC BY-NC 4.0. Overlays neu erzeugen: <code>uv run python results/make_overlays.py</code>. Erklärung der Dateien: <code>results/README.md</code>.</footer>
</main></body></html>"""
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print("index.html", len(hold), len(test))


if __name__ == "__main__":
    main()
