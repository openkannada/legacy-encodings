#!/usr/bin/env python3
"""The reference reader behind the conformance protocol (conformance/README.md)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kle  # noqa: E402


def layout_ids():
    """Layout ids and aliases, such as baraha for nudi."""
    doc = json.loads((kle.ROOT / "tables" / "layouts.json").read_text(encoding="utf-8"))
    ids = {}
    for meta in doc["layouts"]:
        ids[meta["id"]] = meta["id"]
        ids.update({alias: meta["id"] for alias in meta["aliases"]})
    return ids


def parse_codes(text):
    codes = [int(c, 16) for c in text.split()]
    if any(not 0 <= c <= 0xFF for c in codes):
        raise ValueError("codes must be 00 to FF")
    return codes


def respond(req, tables, fonts, ids):
    op = req.get("op")
    if op == "read":
        layout = ids.get(str(req.get("layout", "")).lower())
        if layout is None:
            raise ValueError(f"unknown layout {req.get('layout')!r}")
        options = req.get("options") or {}
        r = kle.read(
            parse_codes(req["codes"]),
            tables[layout],
            zero_as_anusvara=options.get("zero_as_anusvara", True),
            kannada_digits=options.get("kannada_digits", False),
        )
        return {"text": r.text, "unknown": r.unknown, "malformed": [list(m) for m in r.malformed]}
    if op == "detect":
        return {"layout": kle.detect(parse_codes(req["codes"]), tables)}
    if op == "font":
        layout, legacy, digits = kle.font_info(req["name"], fonts)
        return {"layout": layout, "legacy": legacy, "kannada_digits": digits}
    raise ValueError(f"unknown op {op!r}")


def main():
    tables = kle.load_tables()
    fonts = json.loads((kle.ROOT / "tables" / "fonts.json").read_text(encoding="utf-8"))
    ids = layout_ids()
    for line in sys.stdin:
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            resp = {"id": rid, **respond(req, tables, fonts, ids)}
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            resp = {"id": rid, "error": str(e)}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
