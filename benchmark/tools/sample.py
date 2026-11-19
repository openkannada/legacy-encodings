"""Draws the stratified reader sample and works out the error bars it gives.

Usage:
  sample.py draw LINES_DIR OUT.tsv [--per-layout 80] [--seed 20261119]
  sample.py bars LINES_DIR SAMPLE.tsv [ANSWERS.tsv]

Strata are layout x status. Each layout gets --per-layout lines: half from `confirmed`, a
quarter each from `likely` and `unresolved`, moving any shortfall to the other statuses.
`bars` prints, per stratum and per layout, the share of wrong expected texts the sample can
rule out: with ANSWERS (id, verdict right|wrong) it uses the readers' verdicts; without, it
assumes they find no error, which gives the best error bars the sample can reach.
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


def bars(rows, sample, answers):
    sizes = Counter((r["layout"], r["status"]) for r in rows)
    drawn = defaultdict(list)
    for r in sample:
        drawn[(r["layout"], r["status"])].append(r["id"])
    out = ["| Layout | Status | Lines | Sampled | Wrong | Error rate (95% CI) |", "|---|---|---|---|---|---|"]
    per_layout = defaultdict(lambda: [0.0, 0.0, 0])
    for (layout, status), n_h in sorted(sizes.items()):
        ids = drawn.get((layout, status), [])
        n = len(ids)
        wrong = sum(answers.get(i) == "wrong" for i in ids) if answers else 0
        lo, hi = wilson(wrong, n)
        out.append(f"| {layout} | {status} | {n_h} | {n} | {wrong if answers else '0 (assumed)'} | "
                   f"{100 * wrong / n if n else 0:.1f}% ({100 * lo:.1f}% to {100 * hi:.1f}%) |")
        if status in ("confirmed", "likely") and n:
            p = wrong / n
            # Stratified estimate over the scored statuses; the variance term uses the Wilson upper bound
            # so a stratum with no observed error still widens the interval.
            per_layout[layout][0] += n_h * p
            per_layout[layout][1] += n_h * n_h * hi * (1 - hi) / n
            per_layout[layout][2] += n_h
    out.append("")
    out.append("| Layout | Scored lines (confirmed + likely) | Estimated wrong expected texts | 95% upper bound |")
    out.append("|---|---|---|---|")
    for layout, (num, var, total) in sorted(per_layout.items()):
        p = num / total
        upper = min(1.0, p + Z * math.sqrt(var) / total)
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
        sample = list(csv.DictReader(open(argv[2], encoding="utf-8"), delimiter="\t"))
        answers = {}
        if len(argv) > 3:
            answers = {r["id"]: r["verdict"] for r in csv.DictReader(open(argv[3], encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE)}
        print(bars(load(argv[1]), sample, answers))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
