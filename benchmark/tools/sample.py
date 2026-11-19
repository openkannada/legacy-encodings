"""Draws the stratified reader sample and works out the error bars it gives.

Usage:
  sample.py draw LINES_DIR OUT.tsv [--per-layout 80] [--seed 20261119]
  sample.py bars SAMPLE.tsv [ANSWERS.tsv]

Strata are layout x status. Each layout gets --per-layout lines: half from `confirmed`, a
quarter each from `likely` and `unresolved`, moving any shortfall to the other statuses.
`bars` prints, per stratum, the share of wrong expected texts with a Wilson interval, and per
layout a stratified estimate with an approximate, conservative upper bound (normal approximation,
no finite-population correction, p(1-p) taken at its largest over each stratum's interval). With
ANSWERS (id, verdict right|wrong) it counts answered lines only; without, it assumes readers find
no error, which gives the best error bars the sample can reach.
"""
import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

STATUSES = ("confirmed", "likely", "unresolved")
SHARE = {"confirmed": 0.5, "likely": 0.25, "unresolved": 0.25}
Z = 1.959964


def load(lines_dir):
    rows = []
    for path in sorted(Path(lines_dir).glob("*.tsv")):
        for r in csv.reader(open(path, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            if r and not r[0].startswith("#") and r[0] != "id":
                rows.append({"id": r[0], "status": r[1], "layout": path.stem})
    return rows


def draw(rows, per_layout, seed):
    rng = random.Random(seed)
    strata = defaultdict(list)
    for r in rows:
        strata[(r["layout"], r["status"])].append(r["id"])
    picked = []
    for layout in sorted({r["layout"] for r in rows}):
        want = {s: round(per_layout * SHARE[s]) for s in STATUSES}
        have = {s: len(strata[(layout, s)]) for s in STATUSES}
        spare = sum(max(0, want[s] - have[s]) for s in STATUSES)
        take = {s: min(want[s], have[s]) for s in STATUSES}
        while spare:
            room = [s for s in STATUSES if have[s] > take[s]]
            if not room:
                break
            for s in room:
                if spare:
                    take[s] += 1
                    spare -= 1
        for s in STATUSES:
            ids = sorted(strata[(layout, s)])
            rng.shuffle(ids)
            picked += [(i, layout, s, len(ids), take[s]) for i in ids[: take[s]]]
    rng.shuffle(picked)
    return picked


def wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def bars(sample, answers=None):
    """Error-rate table per stratum and an approximate, conservative upper bound per layout.

    Stratum sizes come from the sample file, as drawn, so later status changes do not shift them.
    With answers, only answered lines count; without, every sampled line counts as right.
    """
    strata = {}
    for r in sample:
        s = strata.setdefault((r["layout"], r["status"]), {"N": int(r["stratum_lines"]), "ids": []})
        s["ids"].append(r["id"])
    out = ["| Layout | Status | Lines | Sampled | Answered | Wrong | Error rate (95% CI) |", "|---|---|---|---|---|---|---|"]
    per_layout = defaultdict(lambda: [0.0, 0.0, 0, 0])
    for (layout, status), s in sorted(strata.items()):
        ids = [i for i in s["ids"] if i in answers] if answers is not None else s["ids"]
        n = len(ids)
        wrong = sum(answers[i] == "wrong" for i in ids) if answers is not None else 0
        lo, hi = wilson(wrong, n)
        out.append(f"| {layout} | {status} | {s['N']} | {len(s['ids'])} | {n if answers is not None else '0 (none yet)'} | "
                   f"{wrong if answers is not None else '0 (assumed)'} | {100 * wrong / n if n else 0:.1f}% ({100 * lo:.1f}% to {100 * hi:.1f}%) |")
        if status in ("confirmed", "likely"):
            agg = per_layout[layout]
            agg[2] += s["N"]
            if not n:
                agg[3] += s["N"]
                continue
            # p(1-p) at its largest over the Wilson interval, so a stratum with no error seen still widens the bound.
            spread = 0.25 if lo <= 0.5 <= hi else max(lo * (1 - lo), hi * (1 - hi))
            agg[0] += s["N"] * wrong / n
            agg[1] += s["N"] * s["N"] * spread / n
    out.append("")
    out.append("| Layout | Scored lines (confirmed + likely) | Estimated wrong expected texts | Approximate 95% upper bound |")
    out.append("|---|---|---|---|")
    for layout, (num, var, total, unseen) in sorted(per_layout.items()):
        p = num / total
        # Lines in strata with no answered line are counted as wrong.
        upper = min(1.0, p + Z * math.sqrt(var) / total + unseen / total)
        out.append(f"| {layout} | {total} | {100 * p:.1f}% | {100 * upper:.1f}% |")
    return "\n".join(out)


def main(argv):
    if argv[0] == "draw":
        per = int(argv[argv.index("--per-layout") + 1]) if "--per-layout" in argv else 80
        seed = int(argv[argv.index("--seed") + 1]) if "--seed" in argv else 20261119
        picked = draw(load(argv[1]), per, seed)
        with open(argv[2], "w", encoding="utf-8") as f:
            f.write("id\tlayout\tstatus\tstratum_lines\tstratum_sampled\n")
            for row in picked:
                f.write("\t".join(map(str, row)) + "\n")
        print(len(picked), "lines drawn", file=sys.stderr)
    elif argv[0] == "bars":
        sample = list(csv.DictReader(open(argv[1], encoding="utf-8"), delimiter="\t"))
        answers = None
        if len(argv) > 2:
            answers = {r["id"]: r["verdict"] for r in csv.DictReader(open(argv[2], encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE)}
        print(bars(sample, answers))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
