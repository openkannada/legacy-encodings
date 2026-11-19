"""Writes the benchmark files from the selected lines and their decided expected texts.

Usage: export.py SELECTED.jsonl TRUTH.jsonl OUT_DIR
Writes OUT_DIR/lines/<layout>.tsv, OUT_DIR/documents.tsv and OUT_DIR/ids.tsv (internal id to
public id, for the images). Converter outputs and per-converter agreement are not written.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

STATUS = {"A": "confirmed", "B": "likely", "C": "unresolved"}
LAYOUTS = ["nudi", "akruti", "shree-lipi", "nudi-b", "kan-eng"]
COLUMNS = ["id", "status", "codes", "expected", "source", "options", "document", "page", "box", "fonts", "found_by"]


def clean(text):
    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def main():
    sel = [json.loads(l) for l in open(sys.argv[1])]
    truth = {json.loads(l)["line_id"]: json.loads(l) for l in open(sys.argv[2])}
    out = Path(sys.argv[3])
    (out / "lines").mkdir(parents=True, exist_ok=True)
    kept = [r for r in sel if r["line_id"] in truth and truth[r["line_id"]].get("expected")]
    docs = sorted({r["doc"] for r in kept}, key=lambda d: next(r["url"] for r in kept if r["doc"] == d))
    doc_id = {d: f"doc-{n:03d}" for n, d in enumerate(docs, 1)}
    meta, layouts_of, count = {}, defaultdict(set), defaultdict(int)
    by_layout = defaultdict(list)
    for r in kept:
        by_layout[r["layout"]].append(r)
        meta[r["doc"]] = r
        layouts_of[r["doc"]].add(r["layout"])
        count[r["doc"]] += 1
    ids = []
    for layout in LAYOUTS:
        rows = sorted(by_layout[layout], key=lambda r: (doc_id[r["doc"]], r["page"], -r["bbox"][3], r["bbox"][0]))
        with open(out / "lines" / f"{layout}.tsv", "w", encoding="utf-8", newline="") as f:
            f.write("\t".join(COLUMNS) + "\n")
            for n, r in enumerate(rows, 1):
                pid = f"{layout}-{n:04d}"
                ids.append((r["line_id"], pid))
                t = truth[r["line_id"]]
                cells = [pid, STATUS[t["tier"]], r["codes"], t["expected"], f"{r['url']} page {r['page']}",
                         "kannada_digits" if r["kannada_digits"] else "", doc_id[r["doc"]], r["page"],
                         " ".join(f"{v:.2f}" for v in r["bbox"]), "|".join(r["fonts"]), r["layout_by"]]
                f.write("\t".join(clean(str(c)) for c in cells) + "\n")
    with open(out / "documents.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE)
        w.writerow(["document", "group", "year", "layouts", "lines", "url", "archive", "fetched_from", "sha256", "license"])
        for d in docs:
            r = meta[d]
            w.writerow([doc_id[d], r["group"], r["year"] or "", ",".join(sorted(layouts_of[d])), count[d], r["url"],
                        r.get("archive") or "none", r.get("fetched_from") or "", r["sha256"], "LicenseRef-Excerpts"])
    with open(out / "ids.tsv", "w") as f:
        for a, b in ids:
            f.write(f"{a}\t{b}\n")
    print(len(ids), "lines,", len(docs), "documents", file=sys.stderr)


if __name__ == "__main__":
    main()
