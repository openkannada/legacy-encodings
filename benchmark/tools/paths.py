"""Where the benchmark tools find this repository, their working folders and other programs.

BENCH_WORK (default ./work) holds intermediate files, BENCH_DOWNLOADS (default ./dl) the
fetched PDFs, and KANNADA_OCR a checkout of openkannada/kannada-ocr with its fonts and models
under data/. Run the tools from a scratch folder, not from inside the repository.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("BENCH_WORK", "work"))
DOWNLOADS = Path(os.environ.get("BENCH_DOWNLOADS", "dl"))

sys.path.insert(0, str(ROOT / "reference"))


def kannada_ocr():
    """The kannada-ocr checkout named by KANNADA_OCR."""
    path = os.environ.get("KANNADA_OCR")
    if not path:
        raise SystemExit("set KANNADA_OCR to a checkout of openkannada/kannada-ocr")
    return Path(path)
