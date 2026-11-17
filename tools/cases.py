#!/usr/bin/env python3
"""Copies the conformance cases from a kannadi checkout at a commit.

  cases.py KANNADI_CHECKOUT REV

Writes conformance/cases/<layout>.tsv from kannadi's legacy test fixtures and its
Nudi benchmark corpus, with columns: id, status, codes, expected, source.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "conformance" / "cases"
LAYOUTS = ["nudi", "akruti", "shree-lipi", "nudi-b", "kan-eng"]

HEADER = """\
# Conformance cases for the {layout} layout, copied from kannadi {commit}.
# Columns: id, status, codes (hex, Windows-1252), expected Unicode, source.
# status: verified (a Kannada reader checked the expected text), read (the expected
# text was read against the codes rendered in the font, pending a Kannada reader),
# pending or unchecked (the expected text is a converter's output, not yet read).
# The expected text keeps the source's own typing, errors included.
# Short excerpts of the sources, kept for testing; see conformance/README.md.
"""


def git_show(checkout, commit, path):
    return subprocess.run(
        ["git", "-C", checkout, "show", f"{commit}:{path}"], check=True, capture_output=True
    ).stdout.decode("utf-8")


def rows(text):
    for line in text.splitlines():
        if line.strip() and not line.startswith("#"):
            yield line.split("\t")


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    checkout, rev = argv
    commit = subprocess.run(
        ["git", "-C", checkout, "rev-parse", rev], check=True, capture_output=True, text=True
    ).stdout.strip()
    CASES.mkdir(parents=True, exist_ok=True)
    counts = {}
    for layout in LAYOUTS:
        out, seen = [], set()
        fixture = git_show(checkout, commit, f"crates/kannadi/tests/fixtures/{layout}.tsv")
        for n, (codes, expected, source) in enumerate(rows(fixture), 1):
            seen.add(codes)
            out.append((f"{layout}-{n:03}", "read", codes, expected, source))
        if layout == "nudi":
            corpus = git_show(checkout, commit, "corpus/nudi-2002.tsv")
            for cid, status, source, codes, expected, _note in rows(corpus):
                if codes not in seen:
                    seen.add(codes)
                    out.append((f"nudi-2002-{cid}", status, codes, expected, source))
        body = HEADER.format(layout=layout, commit=commit[:7]) + "".join(
            "\t".join(r) + "\n" for r in out
        )
        (CASES / f"{layout}.tsv").write_text(body, encoding="utf-8")
        counts[layout] = len(out)
    doc = {"repository": "https://github.com/openkannada/kannadi", "commit": commit, "cases": counts}
    (CASES / "SOURCE.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
