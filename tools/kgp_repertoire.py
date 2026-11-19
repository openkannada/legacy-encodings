#!/usr/bin/env python3
"""Compares the Kannada characters the KGP keyboard can type with those the Nudi table reads.

The KGP (Kannada Ganaka Parishat, or Nudi) phonetic layout is how Nudi text was typed.
jquery.ime's rules for it (rules/kn/kn-kgp.js in https://github.com/wikimedia/jquery.ime)
list what each key sequence types. Every Kannada character a KGP typist can produce should
be readable from a Nudi glyph, or be named here as a gap.

    python3 tools/kgp_repertoire.py path/to/kn-kgp.js
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))

import kle  # noqa: E402

KA = [0x50, 0xC0]
KANNADA = re.compile(r"[ಀ-೿]")
# A rule is a JS array of 2 or 3 single-quoted strings; the output is the last one.
RULE = re.compile(r"\[\s*'((?:[^'\\]|\\.)*)'\s*(?:,\s*'((?:[^'\\]|\\.)*)'\s*)?,\s*'((?:[^'\\]|\\.)*)'\s*\]")


def typed_chars(js: str) -> set[str]:
    chars = set()
    for m in RULE.finditer(js):
        chars |= set(KANNADA.findall(m.group(3)))
    return chars


def readable_chars(doc: dict) -> set[str]:
    """Characters the reference reader writes for any entry, alone or after ಕ, for any 2 or
    3 signs after ಕ (vowel signs drawn in parts), and for the digits with Kannada digits on."""
    table = kle.Table(doc)
    entries = [[int(c, 16) for c in e["codes"]] for e in doc["entries"]]
    signs = [codes for codes, e in zip(entries, doc["entries"], strict=True) if e["kind"] == "sign"]
    inputs = [codes for codes in entries] + [KA + codes for codes in entries]
    inputs += [KA + a + b for a in signs for b in signs]
    inputs += [KA + a + b + c for a in signs for b in signs for c in signs]
    chars = set()
    for codes in inputs:
        result = kle.read(codes, table)
        if result.clean:
            chars |= set(KANNADA.findall(result.text))
    digits = kle.read([ord(d) for d in "0123456789"], table, kannada_digits=True).text
    return chars | set(KANNADA.findall(digits))


def main(argv):
    js = Path(argv[0]).read_text(encoding="utf-8")
    doc = json.loads((ROOT / "tables" / "json" / "nudi.json").read_text(encoding="utf-8"))
    typed, read = typed_chars(js), readable_chars(doc)
    missing = sorted(typed - read)
    print(f"KGP types {len(typed)} Kannada characters; the Nudi table reads {len(typed & read)}.")
    for c in missing:
        print(f"  not read: U+{ord(c):04X} {unicodedata.name(c, '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
