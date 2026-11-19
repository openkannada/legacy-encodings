"""Selects the benchmark lines from the extracted pool, spread over documents.

Usage: select_lines.py OUT.jsonl
Keeps clean lines of 12 to 160 codes, drops repeated code sequences, then takes
lines round-robin over documents in random order, up to a target per layout and a cap per
document. Adds source metadata from BENCH_WORK/plan.tsv, fetch-*.jsonl and live-archive.json
(Internet Archive copies of PDFs fetched live).
"""
import glob
import hashlib
import json
import random
import re
import sys
from collections import defaultdict

from paths import WORK

TARGET = {"nudi": 2400, "nudi-b": 1000, "akruti": 1000, "kan-eng": 1000, "shree-lipi": 600}
CAP = 100
# Tab and line-break codes cannot be kept in a TSV cell; such lines are left out.
CONTROL = {"09", "0A", "0D"}
CAP_FEW_DOCS = 300


def year(url, fetched):
    m = re.search(r"/uploads/(20\d\d)/", url) or re.search(r"(?<![0-9])(19[89]\d|20[0-2]\d)(?![0-9])", url)
    return int(m.group(1)) if m else None


def main():
    rng = random.Random(20261119)
    docs = {}
    for l in open(WORK / "plan.tsv"):
        d, group, url, arch, src = l.rstrip("\n").split("\t")
        docs[d] = {"group": group, "url": url}
    for f in glob.glob(str(WORK / "fetch-*.jsonl")):
        for l in open(f):
            j = json.loads(l)
            if j.get("status") == "ok":
                docs[j["doc"]].update(sha256=j["sha256"], archive=j.get("archive"), source=j["source"])
    live = json.load(open(WORK / "live-archive.json")) if (WORK / "live-archive.json").exists() else {}
    for d, url in live.items():
        if url and not docs[d].get("archive"):
            docs[d]["archive"] = url.replace("http://web.archive.org/", "https://web.archive.org/", 1)
    pool = defaultdict(lambda: defaultdict(list))
    seen = set()
    files = sorted(glob.glob(str(WORK / "lines" / "*.jsonl")))
    for f in files:
        for l in open(f):
            r = json.loads(l)
            if not r["clean"] or r["codes"] in seen or CONTROL & set(r["codes"].split()):
                continue
            seen.add(r["codes"])
            pool[r["layout"]][r["doc"]].append(r)
    out = []
    for layout, by_doc in sorted(pool.items()):
        cap = CAP if len(by_doc) >= 15 else CAP_FEW_DOCS
        order = sorted(by_doc)
        rng.shuffle(order)
        for d in order:
            rng.shuffle(by_doc[d])
        picked, k = [], 0
        while len(picked) < TARGET.get(layout, 0) and k < cap:
            took = False
            for d in order:
                if k < len(by_doc[d]) and len(picked) < TARGET.get(layout, 0):
                    picked.append(by_doc[d][k])
                    took = True
            if not took:
                break
            k += 1
        for n, r in enumerate(sorted(picked, key=lambda r: (r["doc"], r["page"], -r["bbox"][1])), 1):
            meta = docs[r["doc"]]
            h = hashlib.sha1(r["codes"].encode()).hexdigest()[:10]
            r.update(line_id=f"{r['doc']}-p{r['page']}-{h}", url=meta["url"], archive=meta.get("archive"), sha256=meta.get("sha256"),
                     group=meta["group"], fetched_from=meta.get("source"), year=year(meta["url"], None))
            out.append(r)
        print(layout, len(picked), "of", sum(len(v) for v in by_doc.values()), "from", len({r["doc"] for r in picked}), "documents", file=sys.stderr)
    with open(sys.argv[1], "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
