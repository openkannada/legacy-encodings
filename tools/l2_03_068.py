#!/usr/bin/env python3
"""The Nudi glyph codes in the 2003 Unicode proposal L2/03-068, and how they compare with
tables/nudi.tsv.

L2/03-068 (https://www.unicode.org/L2/L2003/03068-kannada.pdf), from the Directorate of
Information Technology, Government of Karnataka, prints in its Appendix A every Kannada
code point next to its glyph, set in the font Nudi 01 k. The text layer of the PDF holds
those glyphs as their Nudi codes, read as Windows-1252.

    uv run --no-project --with pymupdf==1.26.5 python tools/l2_03_068.py extract PDF
        writes sources/l2-03-068.tsv: code point, name, Nudi codes, page
    python3 tools/l2_03_068.py check
        compares each row with the Nudi table through the reference reader
"""

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))

import kle  # noqa: E402

SHA256 = "7358bb569608f52751db1b1900993271c7cd665fdf02724632ab5782c28b5016"
SOURCE = ROOT / "sources" / "l2-03-068.tsv"
CODE = re.compile(r"^\s*[O0]C([0-9A-F]{2})\s*$")
NAME = re.compile(r"^(KANN?A?DA|RESERVED|Reserved)\b")
KA = [0x50, 0xC0]


def extract(pdf: Path) -> list[tuple[int, str, str, int]]:
    import fitz

    data = pdf.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit(f"{pdf} is not the expected file (sha256 {SHA256})")
    doc = fitz.open(stream=data, filetype="pdf")
    rows, started = [], False
    for number, page in enumerate(doc, 1):
        lines = page.get_text().splitlines()
        # Appendix B is a code chart grid, which the text layer does not keep in order.
        if any(line.strip().startswith("APPENDIX B") for line in lines):
            break
        if not started:
            if not any(line.strip() == "APPENDIX A" for line in lines):
                continue
            started = True
            lines = lines[[line.strip() for line in lines].index("APPENDIX A") + 3 :]
        i = 0
        while i < len(lines):
            m = CODE.match(lines[i])
            if not m or i + 2 >= len(lines):
                i += 1
                continue
            glyph, name = lines[i + 1].strip(" \t"), lines[i + 2].strip()
            if glyph and not CODE.match(lines[i + 1]) and not NAME.match(glyph):
                try:
                    codes = " ".join(f"{b:02X}" for b in glyph.encode("cp1252"))
                except UnicodeEncodeError as e:
                    raise SystemExit(f"page {number}, U+0C{m.group(1)}: {glyph!r} is not Windows-1252") from e
                cp = 0x0C00 + int(m.group(1), 16)
                earlier = [r for r in rows if r[0] == cp]
                if earlier and earlier[0][2] != codes:
                    raise SystemExit(f"U+{cp:04X} has 2 glyphs: {earlier[0][2]} and {codes}")
                if not earlier:
                    rows.append((cp, name, codes, number))
            i += 3
    return rows


def write_source(rows):
    lines = [
        "# Kannada code points and their glyphs in Nudi 01 k, from Appendix A of L2/03-068.",
        "# https://www.unicode.org/L2/L2003/03068-kannada.pdf, sha256 " + SHA256,
        "# Written by tools/l2_03_068.py extract: 1 row per code point. Names are as the",
        "# proposal prints them. Appendix B, a code chart grid, is not read.",
        "codepoint\tname\tcodes\tpage",
    ]
    lines += [f"U+{cp:04X}\t{name}\t{codes}\t{page}" for cp, name, codes, page in rows]
    SOURCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_source():
    rows = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or line.startswith("codepoint\t"):
            continue
        cp, name, codes, page = line.split("\t")
        rows.append((int(cp[2:], 16), name, [int(c, 16) for c in codes.split()], int(page)))
    return rows


def expected(cp: int) -> tuple[list[int], str] | None:
    """The codes to read and the text a correct reading gives, or None for a code point
    Unicode does not assign as the proposal does."""
    c = chr(cp)
    try:
        uname = unicodedata.name(c)
    except ValueError:
        return None
    if "DIGIT" in uname:
        return [], c
    cat = unicodedata.category(c)
    if cat == "Lo":
        return [], c
    if cat in ("Mn", "Mc"):
        return KA, "ಕ" + c
    return None


def check(rows, table):
    results = []
    for cp, name, codes, page in rows:
        want = expected(cp)
        if want is None:
            results.append((cp, name, codes, "not in Unicode as proposed", ""))
            continue
        prefix, text = want
        digits = "DIGIT" in unicodedata.name(chr(cp))
        got = kle.read(prefix + codes, table, kannada_digits=digits)
        got_text = unicodedata.normalize("NFC", got.text)
        status = "agrees" if got_text == unicodedata.normalize("NFC", text) and got.clean else "differs"
        results.append((cp, name, codes, status, got.text))
    return results


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("pdf", type=Path)
    sub.add_parser("check")
    args = p.parse_args(argv)
    if args.cmd == "extract":
        rows = extract(args.pdf)
        write_source(rows)
        print(f"{len(rows)} code points written to {SOURCE.relative_to(ROOT)}")
        return 0
    table = kle.load_tables()["nudi"]
    results = check(load_source(), table)
    for cp, name, codes, status, got in results:
        if status != "agrees":
            hexes = " ".join(f"{c:02X}" for c in codes)
            print(f"U+{cp:04X}\t{name}\t{hexes}\t{status}\t{got!r}")
    counts = {}
    for r in results:
        counts[r[3]] = counts.get(r[3], 0) + 1
    print(", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
    return 1 if counts.get("differs") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
