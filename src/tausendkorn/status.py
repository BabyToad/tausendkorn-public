"""Observability for VLM runs: live call stats and a results table.

    uv run python -m tausendkorn.status            # last 30 minutes of calls + all results
    uv run python -m tausendkorn.status --minutes 5
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

RUNS = Path(__file__).resolve().parents[2] / "runs" / "vlm"


def calls(minutes: float) -> None:
    path = RUNS / "calls.jsonl"
    if not path.exists():
        print("no calls logged yet")
        return
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - minutes * 60))
    by = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["ts"] >= cutoff:
            by[(r["model"], r["mode"])].append(r)
    print(f"calls in the last {minutes:g} min")
    print(f"{'model':12s} {'mode':6s} {'calls':>5s} {'ok':>4s} {'fail':>4s} {'p50 s':>6s} {'max s':>6s}  last")
    for (model, mode), rs in sorted(by.items()):
        ok = [r for r in rs if r["status"] == "ok"]
        secs = [r["seconds"] for r in rs]
        bad = [r for r in rs if r["status"] != "ok"]
        last = rs[-1]
        print(f"{model:12s} {mode:6s} {len(rs):5d} {len(ok):4d} {len(bad):4d} "
              f"{statistics.median(secs):6.1f} {max(secs):6.1f}  {last['ts'][11:]} {last['image'][:28]}")
        for r in bad[-2:]:
            print(f"    {r['status']}: {(r.get('detail') or '')[:110]!r}")


def results() -> None:
    rows = []
    for f in sorted(RUNS.glob("*/*/*.json")):
        r = json.loads(f.read_text())
        rows.append(r)
    if not rows:
        return
    print(f"\n{'run':16s} {'model':11s} {'image':34s} {'pred':>5s} {'true':>5s} {'err':>5s} "
          f"{'P':>6s} {'R':>6s} {'fail':>4s} {'min':>5s}")
    for r in rows:
        p = f"{r['precision']:.3f}" if "precision" in r else "-"
        rc = f"{r['recall']:.3f}" if "recall" in r else "-"
        print(f"{r['mode']}-g{r['grid']:<9d} {r['model']:11s} {r['file_name'][:34]:34s} {r['pred']:5d} "
              f"{r['count']:5d} {r['pred'] - r['count']:+5d} {p:>6s} {rc:>6s} {r['failed_tiles']:4d} "
              f"{r['seconds'] / 60:5.1f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=30)
    args = ap.parse_args()
    calls(args.minutes)
    results()


if __name__ == "__main__":
    main()
