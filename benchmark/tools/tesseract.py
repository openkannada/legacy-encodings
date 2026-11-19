"""Tesseract runs and the resumable OCR log, kept apart from the rendering so they can be tested alone."""
import json
import os
import subprocess
from pathlib import Path


def read_images(pngs, engine, listing, tessdata):
    """Reads each image with 1 Tesseract run, so the model loads once; None if a reading is missing."""
    listing.write_text("\n".join(str(Path(p).resolve()) for p in pngs) + "\n")
    p = subprocess.run(["tesseract", str(listing), "-", "--tessdata-dir", tessdata, "-l", engine, "--psm", "7"],
                       capture_output=True, text=True, timeout=600, env=dict(os.environ, OMP_THREAD_LIMIT="1"))
    pages = p.stdout.split("\f")
    # Tesseract stops at an image it cannot read; then the readings no longer line up with the images.
    if p.returncode != 0 or len(pages) != len(pngs):
        return None
    return [t.strip() for t in pages]


def resume(dest):
    """Line ids already in the log; drops a last line cut short when an earlier run was stopped."""
    path = Path(dest)
    if not path.exists():
        return set()
    done, good = set(), []
    for line in path.read_text().splitlines():
        try:
            done.add(json.loads(line)["line_id"])
            good.append(line + "\n")
        except ValueError:
            continue
    path.write_text("".join(good))
    return done
