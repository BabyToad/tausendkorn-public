"""One-time evaluation of the frozen pipeline (docs/PROTOCOL.md, rule 2).

    uv run python -m tausendkorn.final --split holdout --budget 10
    uv run python -m tausendkorn.final --split test --per-species 2 --budget 5

The image selection is written to runs/final/<split>/<version>/manifest.json before
any paid call; a later run must match it. Results are reused only if they carry the
same pipeline version and are complete. The budget is checked before every image with
a conservative per-image estimate (prior until real costs exist). Exit code 0 only if
every planned image was counted; 2 on an incomplete count, 3 on a budget stop.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from tausendkorn.eval import load_split
from tausendkorn.match import match
from tausendkorn.pipeline import PIPELINE_VERSION, IncompleteCount, count_kernels, fingerprint

ROOT = Path(__file__).resolve().parents[2]
PRIOR_USD = {"holdout": 0.45, "test": 0.9}  # per image before real costs are known


def pick(split: str, per_species: int | None) -> list[dict]:
    if split == "holdout":
        rows = {r["file_name"]: r for r in load_split("train")}
        return [rows[n] for n in (ROOT / "splits" / "holdout.txt").read_text().split()]
    by = defaultdict(list)
    for r in sorted(load_split("test"), key=lambda r: r["file_name"]):
        by[r["species"]].append(r)
    chosen = {}
    for sp, rs in by.items():  # spread picks over each species' photos
        n = per_species or len(rs)
        step = max(1, len(rs) // n)
        chosen[sp] = rs[::step][:n]
    # Round-robin over species so a budget stop never drops a whole species (e.g. rye).
    out = []
    for i in range(max(len(v) for v in chosen.values())):
        out += [chosen[sp][i] for sp in sorted(chosen) if i < len(chosen[sp])]
    return out


def complete(res: dict, fp: str) -> bool:
    return res.get("version") == PIPELINE_VERSION and res.get("fingerprint") == fp and \
        all(t["pred"] is not None for t in res["first_pass"]["tiles"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["holdout", "test"], required=True)
    ap.add_argument("--per-species", type=int)
    ap.add_argument("--budget", type=float, required=True, help="USD for this run")
    args = ap.parse_args()

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    outdir = ROOT / "runs" / "final" / args.split / PIPELINE_VERSION
    outdir.mkdir(parents=True, exist_ok=True)
    rows = pick(args.split, args.per_species)
    manifest = outdir / "manifest.json"
    names = [r["file_name"] for r in rows]
    fp = fingerprint()
    if manifest.exists():
        frozen = json.loads(manifest.read_text())
        if frozen["images"] != names or frozen.get("fingerprint") != fp:
            print("selection or pipeline code differs from the frozen manifest; refusing to mix")
            return 1
    else:
        manifest.write_text(json.dumps({"split": args.split, "version": PIPELINE_VERSION,
                                        "fingerprint": fp, "commit": commit, "images": names},
                                       indent=1))
    failures = outdir / "failed_attempts.jsonl"
    failed_cost = sum(json.loads(line)["cost_usd"] for line in failures.read_text().splitlines()) \
        if failures.exists() else 0.0

    spent, done, status = 0.0, [], 0
    for i, row in enumerate(rows, 1):
        out = outdir / (row["file_name"].replace("/", "__") + ".json")
        res = json.loads(out.read_text()) if out.exists() else None
        if res is None or not complete(res, fp):
            costs = [r["cost_usd"] for r in done if not r.get("_cached")]
            est = max(PRIOR_USD[args.split], 1.5 * max(costs)) if costs else PRIOR_USD[args.split]
            if spent + est > args.budget:
                print(f"budget stop before {row['file_name']} (spent ${spent:.2f}, next ~${est:.2f})")
                status = 3
                break
            try:
                res = count_kernels(row["path"], row["file_name"])
            except IncompleteCount as e:  # never store a partial count as a result
                spent += e.cost_usd  # paid for, even though unusable
                failed_cost += e.cost_usd
                with open(failures, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"file_name": row["file_name"], "cost_usd": e.cost_usd,
                                         "error": str(e)}) + "\n")
                print(f"stop: {row['file_name']}: {e}")
                status = 2
                break
            res.update(file_name=row["file_name"], species=row["species"], camera=row["camera"],
                       true=row["count"], commit=commit)
            if row.get("kernel_points"):
                m = match(res["points"], row["kernel_points"])
                res.update({k: m[k] for k in ("tp", "fp", "fn", "precision", "recall")})
            out.write_text(json.dumps(res, indent=1))
            spent += res["cost_usd"]
        else:
            res["_cached"] = True
        done.append(res)
        print(f"[{i}/{len(rows)}] {row['file_name']}: {res['count']} vs {res['true']} "
              f"({res['count'] - res['true']:+d})  ${res['cost_usd']:.3f}  run ${spent:.2f}",
              flush=True)

    print(f"\n{args.split} {PIPELINE_VERSION} @ {commit}: {len(done)}/{len(rows)} images done")
    if not done:
        return status or 1
    errs = [r["count"] - r["true"] for r in done]
    rel = [abs(e) / r["true"] * 100 for e, r in zip(errs, done)]
    print(f"MAE {statistics.mean(map(abs, errs)):.2f}  MAPE {statistics.mean(rel):.2f}%  "
          f"bias {statistics.mean(errs):+.2f}  max|err| {max(map(abs, errs))}  "
          f"exact {sum(e == 0 for e in errs)}  within±5 {sum(abs(e) <= 5 for e in errs)}  "
          f"cost all ${sum(r['cost_usd'] for r in done) + failed_cost:.2f} "
          f"(incl. ${failed_cost:.2f} earlier failed attempts)")
    by = defaultdict(list)
    for e, r in zip(errs, done):
        by[r["species"]].append(e)
    for sp, es in sorted(by.items()):
        print(f"  {sp:10s} n={len(es)}  errors {es}")
    if status:
        print("INCOMPLETE: not all planned images were counted")
    return status


if __name__ == "__main__":
    sys.exit(main())
