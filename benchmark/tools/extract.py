"""Extracts legacy-font text lines from a PDF as glyph codes with their page boxes.

Usage: extract.py DOC_ID PDF OUT.jsonl
Each output row: doc, page, rotation, cropbox, bbox (PDF points, page as displayed), fonts,
layout, layout_by, kannada_digits, codes (hex, drawing order), n, clean (no glyph of another run
in the box), and glyphs (code, font object, x, y, em) for draw.py.
"""
import json
import re
import sys

from fontTools.agl import toUnicode
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import resolve1

from paths import ROOT  # also puts the reference reader on the path

import kle  # noqa: E402  (reference reader)

TABLES = kle.load_tables()
FONTS = json.loads((ROOT / "tables/fonts.json").read_text())


def cp1252_byte(ch):
    try:
        b = ch.encode("cp1252")
    except (UnicodeEncodeError, AttributeError):
        return None
    return b[0] if len(b) == 1 else None


class Resources(PDFResourceManager):
    """Remembers each font's object id, so a line can be drawn later with the font program."""

    def get_font(self, objid, spec):
        font = super().get_font(objid, spec)
        if objid is not None:
            font._objid = objid
        return font


class Recorder(PDFPageAggregator):
    def __init__(self, rm):
        super().__init__(rm, laparams=LAParams())
        self.glyphs = []

    def render_char(self, matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate):
        adv = super().render_char(matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate)
        item = self.cur_item._objs[-1] if self.cur_item._objs else None
        bbox = item.bbox if isinstance(item, LTChar) else None
        code = cid
        tu = None
        if not font.is_multibyte():
            try:
                u = font.to_unichr(cid)
                tu = cp1252_byte(u) if u and len(u) == 1 else None
            except Exception:
                tu = None
        if font.is_multibyte():
            try:
                u = font.to_unichr(cid)
            except Exception:
                u = None
            if u == "−":
                u = "\xad"
            code = cp1252_byte(u) if u and len(u) == 1 else None
        size = (bbox[3] - bbox[1]) if bbox and bbox[3] > bbox[1] else fontsize
        em = fontsize * (matrix[3] if abs(matrix[3]) > 1e-6 else (matrix[0] ** 2 + matrix[1] ** 2) ** 0.5)
        self.glyphs.append({"x": matrix[4], "y": matrix[5], "size": size, "em": em, "cid": cid, "fid": getattr(font, "_objid", None),
                            "font": font.fontname,
                            "code": code, "tu": tu, "adv": adv * matrix[0], "bbox": bbox, "upright": abs(matrix[1]) < 1e-6 and abs(matrix[2]) < 1e-6})
        return adv


def differences(doc):
    """Font object id -> {code: original code} from glyph names in /Differences."""
    tables = {}
    for xref in doc.xrefs:
        for oid in xref.get_objids():
            try:
                o = resolve1(doc.getobj(oid))
            except Exception:
                continue
            if not (isinstance(o, dict) and getattr(o.get("Type"), "name", "") == "Font"):
                continue
            enc = resolve1(o.get("Encoding"))
            if not isinstance(enc, dict):
                continue
            m, code = {}, None
            for x in resolve1(enc.get("Differences") or []):
                if isinstance(x, int):
                    code = x
                    continue
                if code is None:
                    continue
                n = getattr(x, "name", str(x))
                if re.fullmatch(r"[cg]\d+", n):
                    m[code] = int(n[1:]) if n[0] == "c" and int(n[1:]) < 256 else None
                else:
                    u = toUnicode(n)
                    m[code] = cp1252_byte(u) if len(u) == 1 else None
                code += 1
            tables[oid] = m
    return tables


def short_font(name):
    return name.split("+", 1)[1] if re.match(r"^[A-Z]{6}\+", name) else name


def font_layout(name):
    layout, legacy, digits = kle.font_info(short_font(name), FONTS)
    return layout if legacy else None, digits


# The layout comes from the codes only for fonts whose names a PDF hid, or Kannada legacy families
# without a name rule (other Shree-Lipi and Akruti fonts); other names, such as Book Antiqua,
# Shree-Lipi's Devanagari fonts or KN-Nandi, never qualify.
HIDDEN = re.compile(r"^(CIDFont\+F\d+|F\d+|T\d+_\d+|TT[0-9A-F]+t00|C\d+_\d+)$")
KANNADA_FAMILY = re.compile(r"^(shree-?kan|shree8[0-9]{2}|akruti|aklite|langscape|skpadmini|nudi|brh|baraha|kan-?eng)", re.I)


def content_detection_allowed(font):
    return bool(HIDDEN.match(font) or KANNADA_FAMILY.match(font))


def segments(glyphs):
    """Splits glyphs, in drawing order, into runs on one baseline that move rightward."""
    runs, cur = [], []
    for g in glyphs:
        if cur:
            p = cur[-1]
            em = max(p["size"], 1)
            same = abs(g["y"] - p["y"]) < 0.35 * em and g["x"] > p["x"] - 0.6 * em and g["x"] - (p["x"] + p["adv"]) < 1.5 * em
            if not same:
                runs.append(cur)
                cur = []
        cur.append(g)
    if cur:
        runs.append(cur)
    return runs


def family(name):
    return re.sub(r"[,-]?(bold|italic|oblique)+$", "", short_font(name), flags=re.I).lower()


def by_family(run):
    """Splits a run where the font family changes; a space joins the run it sits in."""
    parts, cur, fam = [], [], None
    for g in run:
        f = family(g["font"])
        if g["code"] == 0x20 and cur:
            cur.append(g)
            continue
        if cur and f != fam:
            parts.append(cur)
            cur = []
        cur.append(g)
        fam = f
    if cur:
        parts.append(cur)
    return parts


def dedupe(run):
    kept = []
    for g in run:
        if any(k["code"] == g["code"] and abs(k["x"] - g["x"]) < 0.6 and abs(k["y"] - g["y"]) < 0.6 for k in kept[-6:]):
            continue
        kept.append(g)
    return kept


def line_codes(run):
    codes, prev_end = [], None
    for g in run:
        if prev_end is not None and g["x"] - prev_end > 0.2 * max(g["size"], 1) and codes and codes[-1] != 0x20 and g["code"] != 0x20:
            codes.append(0x20)
        codes.append(g["code"])
        prev_end = g["x"] + g["adv"]
    while codes and codes[-1] == 0x20:
        codes.pop()
    while codes and codes[0] == 0x20:
        codes.pop(0)
    return codes


def overprint(g, run):
    """A copy of a run glyph drawn again nearby, as PDFs do to fake bold."""
    return any(r["code"] == g["code"] and abs(r["x"] - g["x"]) < 1.5 and abs(r["y"] - g["y"]) < 1.5 for r in run)


def union(boxes):
    boxes = [b for b in boxes if b]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None


def overlaps(a, b, pad=0.5):
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad


def main():
    doc_id, path, out = sys.argv[1:4]
    fh = open(path, "rb")
    doc = PDFDocument(PDFParser(fh))
    diffs = differences(doc)
    rm = Resources()
    dev = Recorder(rm)
    interp = PDFPageInterpreter(rm, dev)
    rows = []
    for pno, page in enumerate(PDFPage.create_pages(doc), 1):
        dev.glyphs = []
        try:
            interp.process_page(page)
        except Exception:
            continue
        low = {}
        for g in dev.glyphs:
            if g["code"] is not None:
                t = low.setdefault(g["font"], [0, 0])
                t[0] += g["code"] < 0x20
                t[1] += 1
        renumbered = {f for f, (a, n) in low.items() if a > 0.2 * n}
        for g in dev.glyphs:
            if g["font"] in renumbered:
                g["code"] = g["tu"]
                continue
            m = diffs.get(g["fid"])
            if m and g["code"] is not None and g["code"] in m:
                g["code"] = m[g["code"]]
        glyphs = [g for g in dev.glyphs if g["upright"]]
        for run in (p for s in segments(glyphs) for p in by_family(dedupe(s))):
            fonts = sorted({short_font(g["font"]) for g in run if g["code"] not in (None, 0x20)})
            if not fonts or any(g["code"] is None for g in run):
                continue
            named = {font_layout(f) for f in fonts}
            codes = line_codes(run)
            if not 12 <= len(codes) <= 160:
                continue
            layouts = {l for l, _ in named}
            if len(layouts) == 1 and None not in layouts:
                layout, how = layouts.pop(), "font name"
            else:
                if not all(content_detection_allowed(f) for f in fonts):
                    continue
                layout, how = kle.detect(codes, TABLES), "content"
            r = kle.read(codes, TABLES[layout], kannada_digits=any(d for _, d in named))
            letters = [c for c in r.text if not c.isspace()]
            kn = sum("\u0c80" <= c <= "\u0cff" for c in letters)
            if kn < 6 or kn < 0.5 * len(letters) or (how == "content" and (r.unknown or r.malformed)):
                continue
            digits = any(d for _, d in named)
            bbox = union([g["bbox"] for g in run])
            ids = {id(g) for g in run}
            clean = bbox is not None and not any(id(g) not in ids and g["bbox"] and g["code"] != 0x20 and overlaps(bbox, g["bbox"])
                                                 and not overprint(g, run) for g in dev.glyphs)
            cb = [float(v) for v in page.cropbox]
            rows.append({"doc": doc_id, "page": pno, "rotation": int(page.rotate or 0) % 360, "cropbox": cb, "bbox": bbox,
                         "fonts": fonts, "layout": layout, "layout_by": how, "kannada_digits": digits,
                         "codes": " ".join(f"{c:02X}" for c in codes), "n": len(codes), "clean": clean,
                         "glyphs": [[g["cid"], g["fid"], round(g["x"], 2), round(g["y"], 2), round(g["em"], 2)] for g in run if g["code"] != 0x20]})
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(doc_id, len(rows))


if __name__ == "__main__":
    main()
