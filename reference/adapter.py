#!/usr/bin/env python3
"""The reference reader behind the conformance protocol (conformance/README.md)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kle  # noqa: E402


def main():
    tables = kle.load_tables()
    fonts = json.loads((kle.ROOT / "tables" / "fonts.json").read_text(encoding="utf-8"))
    for line in sys.stdin:
        req = json.loads(line)
        rid, op = req["id"], req["op"]
        if op == "read":
            codes = [int(c, 16) for c in req["codes"].split()]
            options = req.get("options", {})
            r = kle.read(
                codes,
                tables[req["layout"]],
                zero_as_anusvara=options.get("zero_as_anusvara", True),
                kannada_digits=options.get("kannada_digits", False),
            )
            resp = {"id": rid, "text": r.text, "unknown": r.unknown, "malformed": [list(m) for m in r.malformed]}
        elif op == "detect":
            resp = {"id": rid, "layout": kle.detect([int(c, 16) for c in req["codes"].split()], tables)}
        elif op == "font":
            layout, legacy, digits = kle.font_info(req["name"], fonts)
            resp = {"id": rid, "layout": layout, "legacy": legacy, "kannada_digits": digits}
        else:
            resp = {"id": rid, "error": f"unknown op {op}"}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
