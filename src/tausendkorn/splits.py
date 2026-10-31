"""Write the frozen evaluation splits to splits/*.txt (see docs/PROTOCOL.md).

Consecutive steps of a session share most kernels, so the splits are step blocks
with buffer zones between them. Deterministic: rerunning must reproduce the files.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from tausendkorn.eval import load_split

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = {
    "holdout": range(0, 10),   # touched once, at the end
    # 10-13 buffer
    "dev": range(14, 20),      # method exploration and tuning
    # 20 buffer
    "train": range(21, 31),    # only for methods that learn
}


def main() -> None:
    rows = [r for r in load_split("train") if r["kernel_points"]]
    by_step = defaultdict(list)
    for r in rows:
        by_step[(r["session"], r["step"])].append(r)

    out = ROOT / "splits"
    out.mkdir(exist_ok=True)
    for name, steps in BLOCKS.items():
        picked = []
        for (session, step), group in sorted(by_step.items()):
            if step not in steps:
                continue
            group.sort(key=lambda r: (r["camera"], r["file_name"]))
            # dev/holdout: one photo per arrangement, alternating cameras; train: all
            picked += group if name == "train" else [group[step % len(group)]]
        (out / f"{name}.txt").write_text("\n".join(r["file_name"] for r in picked) + "\n")
        print(name, len(picked))


if __name__ == "__main__":
    main()
