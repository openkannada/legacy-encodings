"""Scores saved converter responses on the benchmark lines, with 95% intervals by document.

Usage: score.py LINES_DIR RESPONSES.json [--layouts nudi,akruti] [--label-error LAYOUT=PCT,...]

RESPONSES is a file written by `conformance/run.py --out`. Lines whose status is confirmed or
likely are scored; unresolved lines are counted apart. Intervals come from a bootstrap that
resamples whole documents (2,000 draws), since lines from 1 document are not independent.
--label-error widens each interval by the upper bound on wrong expected texts for that layout.
A percentile bootstrap over few documents is too narrow; layouts with fewer than 20 documents
are marked, and their intervals should be read as a lower limit on the uncertainty.
Exits 1 if a scored line has no response.
"""
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))
from normalize import canonical  # noqa: E402

SCORED = ("verified", "confirmed", "likely")
DRAWS = 2000
FEW_DOCUMENTS = 20


def distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def line_scores(expected, text):
    want, got = canonical(expected), canonical(text)
    return (text == expected, got == want, distance(text, expected), len(expected), distance(got, want), len(want))


def summarize(items):
    n = len(items)
    if not n:
        return None
    exact = sum(i[0] for i in items) / n
    norm = sum(i[1] for i in items) / n
    char = 1 - sum(i[2] for i in items) / max(1, sum(i[3] for i in items))
    nchar = 1 - sum(i[4] for i in items) / max(1, sum(i[5] for i in items))
    return [exact, norm, max(0.0, char), max(0.0, nchar)]


def bootstrap(by_doc, rng):
    docs = sorted(by_doc)
    draws = []
    for _ in range(DRAWS):
        items = [i for d in (rng.choice(docs) for _ in docs) for i in by_doc[d]]
        draws.append(summarize(items))
    out = []
    for k in range(4):
        vals = sorted(d[k] for d in draws)
        out.append((vals[int(0.025 * DRAWS)], vals[int(0.975 * DRAWS) - 1]))
    return out


def main(argv):
    lines_dir, responses = argv[0], json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    keep = set(argv[argv.index("--layouts") + 1].split(",")) if "--layouts" in argv else None
    label = {}
    if "--label-error" in argv:
        for pair in argv[argv.index("--label-error") + 1].split(","):
            k, v = pair.split("=")
            label[k] = float(v) / 100
    rng = random.Random(1)
    exit_code = 0
    few = []
    print("| Layout | Lines (documents) | Exact | Exact, normalized | Character accuracy | Normalized | Unresolved lines not scored |")
    print("|---|---|---|---|---|---|---|")
    for path in sorted(Path(lines_dir).glob("*.tsv")):
        layout = path.stem
        if keep and layout not in keep:
            continue
        by_doc, unresolved, missing = defaultdict(list), 0, 0
        for r in csv.reader(open(path, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            if not r or r[0].startswith("#") or r[0] == "id":
                continue
            lid, status, _codes, expected, _source, _options, doc = r[:7]
            if status not in SCORED:
                unresolved += 1
                continue
            if f"read {lid}" not in responses:
                missing += 1
            resp = responses.get(f"read {lid}", {})
            text = resp.get("text") if isinstance(resp.get("text"), str) else ""
            by_doc[doc].append(line_scores(expected, text))
        items = [i for v in by_doc.values() for i in v]
        if not items:
            continue
        point = summarize(items)
        ci = bootstrap(by_doc, rng)
        e = label.get(layout, 0.0)
        cells = [f"{100 * p:.1f}% ({100 * max(0, lo - e):.1f} to {100 * min(1, hi + e):.1f})" for p, (lo, hi) in zip(point, ci)]
        mark = "*" if len(by_doc) < FEW_DOCUMENTS else ""
        if mark:
            few.append(layout)
        print(f"| {layout} | {len(items)} ({len(by_doc)}){mark} | " + " | ".join(cells) + f" | {unresolved} |")
        if missing:
            print(f"{layout}: {missing} scored lines have no response", file=sys.stderr)
            exit_code = 1
    if few:
        print(f"\n*Fewer than {FEW_DOCUMENTS} documents: the interval understates the uncertainty.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
