"""Draws the stratified sample of archived PDFs to fetch, and lists the archive queries it uses.

Usage:
  plan.py queries                      prints the Internet Archive CDX queries to save as BENCH_WORK/cdx-<name>.txt
  plan.py draw [AUDIT.csv ...]         writes BENCH_WORK/plan.tsv

Each CDX file holds lines of "timestamp url length digest". The draw takes a fixed number of
PDFs from each folder of each site, so no single series fills the set. AUDIT files are CSVs
of the 2026 audit of Karnataka government sites (url, kind, class, source, fetched_at,
organization); their legacy and mixed PDFs are added as they are, fetched live or from Common Crawl.
"""
import csv
import random
import re
import sys
from collections import defaultdict

from paths import WORK

SEED = 20261119
SITES = {
    "kla": "kla.kar.nic.in/",
    "gazette": "gazette.kar.nic.in/",
    "dpal": "dpal.kar.nic.in/",
    "finance": "kar.nic.in/finance/",
    "ktbs": "ktbs.kar.nic.in/",
    "kpsc": "kpsc.kar.nic.in/",
    "kseeb": "kseeb.kar.nic.in/",
}

# PDFs per folder. Legislature folders are named by their first 2 path parts; others by the first.
KLA = {"council/replies": 30, "council/newsclips": 6, "council/house": 12, "council/research": 6,
       "council/committemeeting": 6, "council/bulletin": 10, "council/lob": 6, "council/houseproceedings": 10,
       "council/secretariatinfo": 4, "assembly/member": 45, "assembly/elib": 6, "assembly/lob": 6,
       "assembly/bills": 10, "assembly/debates": 21, "assembly/questions": 6, "assembly/research": 5,
       "assembly/bulletin": 5, "council/gazette": 6, "council/members": 6}
# A second draw, for Shree-Lipi: PDFs of 20 kB to 4 MB from the education and recruitment sites.
PROBE = {"ktbs": 20, "kpsc": 15, "kseeb": 20}


def queries():
    for name, prefix in SITES.items():
        print(f"cdx-{name}.txt\thttps://web.archive.org/cdx/search/cdx?url={prefix}&matchType=prefix"
              "&filter=mimetype:application/pdf&filter=statuscode:200&collapse=urlkey&fl=timestamp,original,length,digest")


def cdx(site):
    path = WORK / f"cdx-{site}.txt"
    out = []
    for line in open(path) if path.exists() else []:
        p = line.split()
        if len(p) >= 3 and p[2].isdigit() and int(p[2]) > 2000:
            out.append(p)
    return out


def first_draw(rng):
    rows = []

    def add(group, items, n):
        items = list(items)
        rng.shuffle(items)
        rows.extend((group, url, f"https://web.archive.org/web/{ts}id_/{url}", "wayback") for ts, url, *_ in items[:n])

    by = defaultdict(list)
    for r in cdx("kla"):
        by["/".join(re.sub(r"https?://(www\.)?kla\.kar\.nic\.in(:80)?/", "", r[1]).split("/")[:2]).lower()].append(r)
    for g, n in KLA.items():
        add("kla:" + g, by.get(g, []), n)
    add("gazette", [r for r in cdx("gazette") if "Contents" not in r[1]], 35)
    by, other = defaultdict(list), []
    for r in cdx("dpal"):
        by[re.sub(r"https?://(www\.)?dpal\.kar\.nic\.in(:80)?/", "", r[1]).split("/")[0]].append(r)
    for g, items in by.items():
        n = 8 if g == "pdf_files" else 5 if "padakosha" in g.lower() else 4 if g.startswith("ao") else 3 if "Central" in g else 0
        if n:
            add("dpal:" + g, items, n)
        else:
            other.extend(items)
    add("dpal:other", other, 15)
    by = defaultdict(list)
    for r in cdx("finance"):
        rest = re.sub(r"https?://(www\.)?kar\.nic\.in(:80)?/finance/", "", r[1])
        by[rest.split("/")[0] if "/" in rest else "top"].append(r)
    for g, items in by.items():
        add("finance:" + g, items, 8 if g.startswith("bud") or g == "2008july" else 6 if g in ("gos", "mtfp", "top") else 3)
    return rows


def audit_rows(paths):
    rows = []
    for path in paths:
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r["kind"] == "pdf" and r["class"] in ("legacy", "mixed"):
                if r["source"].startswith("commoncrawl"):
                    rows.append(("audit-cc:" + r["organization"][:30], r["url"], f"{r['source']}@{r['fetched_at']}", "commoncrawl"))
                else:
                    rows.append(("audit-live:" + r["organization"][:30], r["url"], r["url"], "live"))
    return rows


def probe_draw():
    rng = random.Random(7)
    rows = []
    for site, n in PROBE.items():
        items = [p for p in cdx(site) if 20_000 < int(p[2]) < 4_000_000]
        rng.shuffle(items)
        rows.extend((f"probe:{site}", url, f"https://web.archive.org/web/{ts}id_/{url}", "wayback") for ts, url, *_ in items[:n])
    return rows


def draw(audits):
    seen, out = set(), []
    for group, url, location, source in first_draw(random.Random(SEED)) + audit_rows(audits) + probe_draw():
        if url not in seen:
            seen.add(url)
            out.append((f"d{len(out) + 1:04d}", group, url, location, source))
    with open(WORK / "plan.tsv", "w", encoding="utf-8") as f:
        for r in out:
            f.write("\t".join(r) + "\n")
    print(len(out), "documents planned", file=sys.stderr)


def main(argv):
    if argv[:1] == ["queries"]:
        queries()
    elif argv[:1] == ["draw"]:
        draw(argv[1:])
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
