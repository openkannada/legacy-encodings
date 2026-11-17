#!/usr/bin/env python3
"""Builds and checks the machine-readable layout tables.

  tables.py sync KANNADI_CHECKOUT REV   copy the TSV tables from kannadi at REV
  tables.py build                       write tables/json/*.json from tables/*.tsv
  tables.py check                       validate the tables and fail if the JSON is stale
"""

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tables"
SPEC_VERSION = "0.1.0-draft"
KANNADI_URL = "https://github.com/openkannada/kannadi"
KANNADI_DATA = "crates/kannadi/data"

KINDS = {"letter", "base", "sign", "ottu", "arka", "mod", "aspirate", "ignore", "literal"}
WHITE_SPACE_CODES = {"09", "0A", "0B", "0C", "0D", "20", "A0"}
VIRAMA = "್"


def char_class(c):
    """The character classes the specification defines (section 3)."""
    o = ord(c)
    if 0x0C85 <= o <= 0x0C8C or 0x0C8E <= o <= 0x0C90 or 0x0C92 <= o <= 0x0C94 or o in (0x0CE0, 0x0CE1):
        return "vowel"
    if 0x0C95 <= o <= 0x0CA8 or 0x0CAA <= o <= 0x0CB3 or 0x0CB5 <= o <= 0x0CB9 or o == 0x0CDE:
        return "consonant"
    if 0x0CBE <= o <= 0x0CC4 or 0x0CC6 <= o <= 0x0CC8 or 0x0CCA <= o <= 0x0CCC or o in (0x0CD5, 0x0CD6, 0x0CE2, 0x0CE3):
        return "vowel-sign"
    if o == 0x0CCD:
        return "virama"
    if o == 0x0CBC:
        return "nukta"
    if 0x0C81 <= o <= 0x0C83 or 0x0CF1 <= o <= 0x0CF3:
        return "modifier"
    if 0x0951 <= o <= 0x0954 or 0x1CD0 <= o <= 0x1CD2 or 0x1CD4 <= o <= 0x1CE8 or o in (0x1CED, 0x1CF4) or 0x1CF7 <= o <= 0x1CF9:
        return "modifier"
    if 0x0CE6 <= o <= 0x0CEF:
        return "digit"
    if o == 0x200D:
        return "zwj"
    if o == 0x200C:
        return "zwnj"
    if 0x0C80 <= o <= 0x0CFF:
        return "other-kannada"
    return "other"


def layouts():
    return json.loads((TABLES / "layouts.json").read_text(encoding="utf-8"))["layouts"]


def source():
    return json.loads((TABLES / "SOURCE.json").read_text(encoding="utf-8"))


def parse_prefer(column, where):
    if column == "":
        return None
    if column in ("read", "after-ottu"):
        return {"type": column}
    kind, _, chars = column.partition(" ")
    if kind in ("on", "with") and chars.strip():
        if any(len(c) != 1 for c in chars.split()):
            raise ValueError(f"{where}: preference characters must be separated by spaces")
        return {"type": kind, "chars": chars.split()}
    raise ValueError(f"{where}: unknown preference {column!r}")


def parse_table(text, name):
    """Rows of a TSV table, checked against the rules of section 4."""
    notes, entries, seen = [], [], {}
    in_header = True
    for n, line in enumerate(text.splitlines(), 1):
        where = f"{name}:{n}"
        if line.startswith("#"):
            if in_header:
                notes.append(line[1:].strip())
            continue
        if not line.strip():
            continue
        in_header = False
        cols = line.split("\t")
        if len(cols) > 4:
            raise ValueError(f"{where}: more than 4 columns")
        codes_col, kind, value, prefer_col = (cols + ["", "", ""])[:4]
        codes = codes_col.split()
        if not codes or not all(re.fullmatch(r"[0-9A-F]{2}", c) for c in codes):
            raise ValueError(f"{where}: codes must be 2-digit uppercase hex, found {codes_col!r}")
        key = " ".join(codes)
        if key in seen:
            raise ValueError(f"{where}: codes {key} repeat line {seen[key]}")
        seen[key] = n
        if kind not in KINDS:
            raise ValueError(f"{where}: unknown kind {kind!r}")
        prefer = parse_prefer(prefer_col, where)
        check_value(kind, value, prefer, where)
        if len(codes) > 1 and codes[0] in WHITE_SPACE_CODES and (prefer or {}).get("type") != "read":
            raise ValueError(f"{where}: a sequence that starts with white space must be marked read")
        entry = {"codes": codes, "kind": kind, "value": value}
        if prefer:
            entry["prefer"] = prefer
        entries.append(entry)
    return notes, entries


def check_value(kind, value, prefer, where):
    classes = [char_class(c) for c in value]
    if value != unicodedata.normalize("NFC", value) and kind not in ("letter", "sign"):
        raise ValueError(f"{where}: value {value!r} is not NFC")
    if kind == "ottu":
        n = 0
        while n < len(classes) and classes[n] == "consonant":
            n += 1
        rest = classes[n:]
        if n == 0 or len(rest) > 1 or (rest and rest[0] != "vowel-sign"):
            raise ValueError(f"{where}: ottu value {value!r} must be consonants and at most 1 vowel sign")
    elif kind == "mod":
        if len(value) != 1 or classes[0] != "modifier":
            raise ValueError(f"{where}: mod value {value!r} must be 1 modifier")
    elif kind == "base":
        cluster = all(
            k == ("consonant" if i % 2 == 0 else "virama") for i, k in enumerate(classes)
        ) and len(value) % 2 == 1
        if not cluster:
            raise ValueError(f"{where}: base value {value!r} must be a consonant or a cluster")
        if len(value) > 1 and (prefer or {}).get("type") != "read":
            raise ValueError(f"{where}: a base written back must be 1 consonant, or else marked read")
    elif kind == "sign":
        if len(value) > 1 or (value and classes[0] not in ("vowel-sign", "virama")):
            raise ValueError(f"{where}: sign value {value!r} must be empty, 1 vowel sign or the virama")
    elif kind == "letter":
        if not value or classes[0] not in ("vowel", "consonant"):
            raise ValueError(f"{where}: letter value {value!r} must start with a vowel or consonant")
    elif kind in ("arka", "aspirate", "ignore"):
        if value:
            raise ValueError(f"{where}: {kind} takes no value, found {value!r}")
    elif kind == "literal":
        if not value:
            raise ValueError(f"{where}: literal needs a value")
        if len(value) > 1 and (prefer or {}).get("type") != "read":
            raise ValueError(f"{where}: a literal written back must be 1 character, or else marked read")
    if prefer and prefer["type"] != "read" and kind not in ("sign", "ottu", "arka", "aspirate"):
        raise ValueError(f"{where}: a {prefer['type']} preference has no effect on {kind}")
    if prefer and prefer["type"] != "read" and kind == "sign" and value == "":
        raise ValueError(f"{where}: a {prefer['type']} preference has no effect on the head stroke")


def draws_latin(entries):
    return any(
        e["kind"] == "literal" and e["value"].isascii() and e["value"].isalpha() for e in entries
    )


def build_layout(meta, src):
    tsv = TABLES / f"{meta['id']}.tsv"
    notes, entries = parse_table(tsv.read_text(encoding="utf-8"), tsv.name)
    return {
        "$schema": "../../schema/layout.schema.json",
        "spec_version": SPEC_VERSION,
        "id": meta["id"],
        "name": meta["name"],
        "aliases": meta["aliases"],
        "description": meta["description"],
        "fonts": meta["fonts"],
        "byte_encoding": "windows-1252",
        "draws_latin": draws_latin(entries),
        "source": {
            "repository": src["repository"],
            "commit": src["commit"],
            "path": f"{KANNADI_DATA}/{meta['id']}.tsv",
        },
        "notes": notes,
        "entries": entries,
    }


def rendered():
    src = source()
    out = {}
    for meta in layouts():
        doc = build_layout(meta, src)
        out[TABLES / "json" / f"{meta['id']}.json"] = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"
    return out


def check_fonts():
    fonts = json.loads((TABLES / "fonts.json").read_text(encoding="utf-8"))
    ids = {m["id"] for m in layouts()}
    for rule in fonts["not_legacy"] + fonts["layout_rules"] + fonts["legacy_without_table"] + fonts["kannada_digits"]:
        re.compile(rule["match"])
    for rule in fonts["layout_rules"]:
        if rule["layout"] is not None and rule["layout"] not in ids:
            raise ValueError(f"fonts.json: unknown layout {rule['layout']!r}")
    for ex in fonts["examples"]:
        got = font_layout(fonts, ex["font"])
        if got != ex["layout"]:
            raise ValueError(f"fonts.json: {ex['font']!r} gives {got!r}, expected {ex['layout']!r}")
        if "legacy" in ex and is_legacy(fonts, ex["font"]) != ex["legacy"]:
            raise ValueError(f"fonts.json: {ex['font']!r} legacy is wrong")
        if "kannada_digits" in ex and kannada_digits(fonts, ex["font"]) != ex["kannada_digits"]:
            raise ValueError(f"fonts.json: {ex['font']!r} kannada_digits is wrong")


def font_key(name):
    return "".join(c for c in name if c.isascii() and c.isalnum()).lower()


def font_layout(fonts, name):
    key = font_key(name)
    if any(re.search(r["match"], key) for r in fonts["not_legacy"]):
        return None
    for rule in fonts["layout_rules"]:
        if re.search(rule["match"], key):
            return rule["layout"]
    return None


def is_legacy(fonts, name):
    if font_layout(fonts, name) is not None:
        return True
    key = font_key(name)
    if any(re.search(r["match"], key) for r in fonts["not_legacy"]):
        return False
    return any(re.search(r["match"], key) for r in fonts["legacy_without_table"])


def kannada_digits(fonts, name):
    return any(re.search(r["match"], font_key(name)) for r in fonts["kannada_digits"])


def sync(checkout, rev):
    commit = subprocess.run(
        ["git", "-C", checkout, "rev-parse", rev], check=True, capture_output=True, text=True
    ).stdout.strip()
    for meta in layouts():
        path = f"{KANNADI_DATA}/{meta['id']}.tsv"
        data = subprocess.run(
            ["git", "-C", checkout, "show", f"{commit}:{path}"], check=True, capture_output=True
        ).stdout
        (TABLES / f"{meta['id']}.tsv").write_bytes(data)
    doc = {"repository": KANNADI_URL, "commit": commit}
    (TABLES / "SOURCE.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"copied {len(layouts())} tables from kannadi {commit[:7]}")


def main(argv):
    if len(argv) == 3 and argv[0] == "sync":
        sync(argv[1], argv[2])
        argv = ["build"]
    if argv == ["build"]:
        (TABLES / "json").mkdir(exist_ok=True)
        for path, text in rendered().items():
            path.write_text(text, encoding="utf-8")
        check_fonts()
        print(f"wrote {len(layouts())} JSON tables")
        return 0
    if argv == ["check"]:
        stale = [p.name for p, t in rendered().items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        check_fonts()
        if stale:
            print("stale, run tools/tables.py build: " + ", ".join(stale), file=sys.stderr)
            return 1
        print(f"{len(layouts())} tables and the font rules check out")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
