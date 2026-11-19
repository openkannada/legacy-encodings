"""Reads each line image, and each distinct converter output rendered in Unicode fonts, with Tesseract.

Usage: ocr.py CANDIDATES.jsonl IMAGEDIR OUT.jsonl
IMAGEDIR holds the line images draw.py made.
Engines: kan_ft_ofl3 (Open Kannada, trained without legacy fonts) and Tesseract's stock kan.
Writes per line: line_id, crop {engine: text}, renders {candidate text: {face: {engine: text}}}.
Resumable: lines already in OUT are skipped.
"""
import hashlib
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from paths import WORK, kannada_ocr  # noqa: E402
from tesseract import read_images, resume
from PIL import Image

OCR = kannada_ocr()
sys.path.insert(0, str(OCR / "src"))
from kannada_ocr.render import FontFace, render  # noqa: E402

TESSDATA = str(OCR / "data/tessdata")
ENGINES = ["kan_ft_ofl3", "kan"]
FONTS = OCR / "data/fonts"
# 2 OFL fonts, plus the Unicode release of the Nudi design that most legacy documents use, so
# that an OCR habit on Nudi letter shapes shows up on the rendering too. NUDI UNI comes from
# KaGaPa's Nudi package; set NUDI_UNI to the folder holding it, or leave it out.
FACES = {
    "noto-sans": FontFace(FONTS / "google/NotoSansKannada[wdth,wght].ttf", "Noto Sans Kannada", 400),
    "noto-serif": FontFace(FONTS / "google/NotoSerifKannada[wght].ttf", "Noto Serif Kannada", 400),
}
if os.environ.get("NUDI_UNI"):
    FACES["nudi-uni"] = FontFace(Path(os.environ["NUDI_UNI"]) / "NUDI UNI 01E.ttf", "NUDI UNI 01E")
    FACES["nudi-uni-bold"] = FontFace(Path(os.environ["NUDI_UNI"]) / "NUDI UNI 01E BOLD.ttf", "NUDI UNI 01E BOLD")
RENDERS = WORK / "renders"


def render_png(text, face, tag):
    h = tag + "-" + hashlib.sha1((face + text).encode()).hexdigest()[:16]
    path = RENDERS / f"{h}.png"
    if not path.exists():
        ink = render(FACES[face], text, 64, pad=12)
        if ink is None:
            return None
        Image.fromarray((255 - ink * 255).astype(np.uint8)).save(path)
    return path


def work(args):
    row, imagedir = args
    image = Path(imagedir) / f"{row['line_id']}.png"
    if not image.exists():
        return None
    texts = sorted({t for t in row["outputs"].values() if t})
    jobs = [("page", None, image)]
    for text in texts:
        for face in FACES:
            png = render_png(text, face, row["line_id"])
            if png:
                jobs.append(("render", (text, face), png))
    listing = RENDERS / f"{row['line_id']}.txt"
    reads = {e: read_images([j[2] for j in jobs], e, listing, TESSDATA) for e in ENGINES}
    listing.unlink()
    for _, _, png in jobs[1:]:
        png.unlink()
    if any(r is None for r in reads.values()):
        print("Tesseract could not read every image of", row["line_id"], "; line left out", file=sys.stderr, flush=True)
        return None
    out = {"line_id": row["line_id"], "crop": {e: reads[e][0] for e in ENGINES}, "renders": {t: {f: None for f in FACES} for t in texts}}
    for n, (kind, key, png) in enumerate(jobs):
        if kind == "render":
            out["renders"][key[0]][key[1]] = {e: reads[e][n] for e in ENGINES}
    return out


def main():
    cands, imagedir, dest = sys.argv[1:4]
    RENDERS.mkdir(parents=True, exist_ok=True)
    done = resume(dest)
    rows = [json.loads(l) for l in open(cands)]
    todo = [(r, imagedir) for r in rows if r["line_id"] not in done]
    with open(dest, "a") as f, Pool(int(os.environ.get("OCR_JOBS", "6"))) as pool:
        for n, res in enumerate(pool.imap_unordered(work, todo, chunksize=4), 1):
            if res:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            if n % 200 == 0:
                f.flush()
                print(n, len(todo), file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
