"""Draws each selected line's glyphs with the font program embedded in its own PDF.

Usage: draw.py LINES.jsonl OUTDIR
Each glyph is placed at its recorded origin, scaled so 1 em is 64 pixels, so the image holds
exactly the line's codes as the document's font draws them, and nothing from nearby lines.
Lines whose font is not embedded, or whose glyphs cannot be found in it, are skipped.
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import freetype
import numpy as np
from paths import DOWNLOADS
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import resolve1
from PIL import Image

EM = 64


class Font:
    def __init__(self, doc, objid):
        spec = resolve1(doc.getobj(objid))
        self.cid_font = getattr(spec.get("Subtype"), "name", "") == "Type0"
        self.cid_to_gid = None
        if self.cid_font:
            spec = resolve1(resolve1(spec["DescendantFonts"])[0])
            m = resolve1(spec.get("CIDToGIDMap"))
            if m is not None and not hasattr(m, "name"):
                data = m.get_data()
                self.cid_to_gid = [int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data), 2)]
        desc = resolve1(spec.get("FontDescriptor")) or {}
        data = None
        for k in ("FontFile2", "FontFile3", "FontFile"):
            if k in desc:
                data = resolve1(desc[k]).get_data()
                break
        if data is None:
            raise ValueError("font not embedded")
        self.face = freetype.Face(io.BytesIO(data))
        self.maps = {(cm.platform_id, cm.encoding_id): cm for cm in self.face.charmaps}

    def gid(self, cid):
        if self.cid_font:
            return self.cid_to_gid[cid] if self.cid_to_gid and cid < len(self.cid_to_gid) else cid
        for key, code in (((3, 0), 0xF000 + cid), ((3, 0), cid), ((1, 0), cid), ((3, 1), cid)):
            cm = self.maps.get(key)
            if cm is None:
                continue
            self.face.select_charmap(cm.encoding)
            g = self.face.get_char_index(code)
            if g:
                return g
        if not self.maps:
            return cid
        return 0


def draw(line, fonts):
    glyphs = line["glyphs"]
    em = max(g[4] for g in glyphs)
    if em <= 0:
        return None
    s = EM / em
    x0 = min(g[2] for g in glyphs)
    base = max(g[3] for g in glyphs)
    width = int((max(g[2] for g in glyphs) - x0) * s) + 4 * EM
    height = 3 * EM
    canvas = np.zeros((height, width), dtype=np.uint8)
    origin_y = int(1.8 * EM)
    for cid, fid, x, y, gem in glyphs:
        font = fonts[fid]
        gid = font.gid(cid)
        if not gid:
            return None
        size = max(1, int(round(gem * s * 64)))
        font.face.set_char_size(size)
        font.face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        slot = font.face.glyph
        bm = slot.bitmap
        if bm.width and bm.rows:
            arr = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, : bm.width]
            px = int(round((x - x0) * s)) + EM + slot.bitmap_left
            py = origin_y - int(round((y - base) * s)) - slot.bitmap_top
            if px < 0 or py < 0 or px + bm.width > width or py + bm.rows > height:
                return None
            region = canvas[py: py + bm.rows, px: px + bm.width]
            np.maximum(region, arr, out=region)
    rows = np.flatnonzero(canvas.max(axis=1) > 12)
    cols = np.flatnonzero(canvas.max(axis=0) > 12)
    if not len(rows):
        return None
    ink = np.pad(canvas[rows[0]: rows[-1] + 1, cols[0]: cols[-1] + 1], 12)
    return Image.fromarray(255 - ink)


def main():
    lines = [json.loads(l) for l in open(sys.argv[1])]
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    by_doc = defaultdict(list)
    for l in lines:
        if not (out / f"{l['line_id']}.png").exists():
            by_doc[l["doc"]].append(l)
    skipped = 0
    for doc_id, items in by_doc.items():
        fh = open(DOWNLOADS / f"{doc_id}.pdf", "rb")
        doc = PDFDocument(PDFParser(fh))
        fonts = {}
        for l in items:
            try:
                for fid in {g[1] for g in l["glyphs"]}:
                    if fid not in fonts:
                        fonts[fid] = Font(doc, fid)
                img = draw(l, fonts)
            except Exception:
                img = None
            if img is None:
                skipped += 1
                continue
            img.save(out / f"{l['line_id']}.png")
        fh.close()
    print("skipped", skipped, "of", sum(len(v) for v in by_doc.values()), file=sys.stderr)


if __name__ == "__main__":
    main()
