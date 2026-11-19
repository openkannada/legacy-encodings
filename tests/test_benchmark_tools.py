"""The benchmark's scoring, error bars and line building, on small made-up inputs."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "benchmark" / "tools"))

import sample  # noqa: E402
import score  # noqa: E402
import tesseract  # noqa: E402
from unittest import mock  # noqa: E402

HEADER = "id\tstatus\tcodes\texpected\tsource\toptions\tdocument\tpage\tbox\tfonts\tfound_by\n"


def line(lid, status, expected, doc):
    return f"{lid}\t{status}\t50 C0\t{expected}\thttps://example.org/{doc}.pdf page 1\t\t{doc}\t1\t0 0 1 1\tNudi01e\tfont name\n"


class Score(unittest.TestCase):
    def run_score(self, responses, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "nudi.tsv").write_text(
                HEADER + line("nudi-0001", "confirmed", "ಕನ್ನಡ", "doc-1") + line("nudi-0002", "confirmed", "ನಾಡು", "doc-1")
                + line("nudi-0003", "likely", "ಕರ್ನಾಟಕ", "doc-2") + line("nudi-0004", "unresolved", "ಗೊತ್ತಿಲ್ಲ", "doc-2"),
                encoding="utf-8")
            Path(tmp, "r.json").write_text(json.dumps(responses), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = score.main([tmp, str(Path(tmp, "r.json")), *extra])
            return code, out.getvalue()

    def test_figures_skip_unresolved_lines(self):
        responses = {"read nudi-0001": {"text": "ಕನ್ನಡ"}, "read nudi-0002": {"text": "ನಾಡ"},
                     "read nudi-0003": {"text": "ಕರ್ನಾಟಕ"}, "read nudi-0004": {"text": "x"}}
        code, out = self.run_score(responses)
        self.assertEqual(code, 0)
        row = next(r for r in out.splitlines() if r.startswith("| nudi"))
        self.assertIn("| 3 (2)*", row)
        self.assertIn("66.7%", row)
        self.assertTrue(row.endswith("| 1 |"))

    def test_a_missing_response_fails(self):
        code, _ = self.run_score({"read nudi-0001": {"text": "ಕನ್ನಡ"}})
        self.assertEqual(code, 1)

    def test_label_error_widens_the_interval(self):
        responses = {f"read nudi-000{i}": {"text": t} for i, t in ((1, "ಕನ್ನಡ"), (2, "ನಾಡು"), (3, "ಕರ್ನಾಟಕ"))}
        _, plain = self.run_score(responses)
        _, wide = self.run_score(responses, "--label-error", "nudi=10")
        self.assertIn("100.0% (100.0 to 100.0)", plain)
        self.assertIn("100.0% (90.0 to 100.0)", wide)


class Bars(unittest.TestCase):
    def sample(self, n):
        return [{"id": f"nudi-{i:04d}", "layout": "nudi", "status": "confirmed", "stratum_lines": "1000", "stratum_sampled": str(n)}
                for i in range(n)]

    def test_only_answered_lines_count(self):
        out = sample.bars(self.sample(40), {"nudi-0000": "wrong", "nudi-0001": "right"})
        self.assertIn("| nudi | confirmed | 1000 | 40 | 2 | 1 | 50.0%", out)

    def upper(self, out):
        return float(out.splitlines()[-1].split("|")[4].strip().rstrip("%"))

    def test_no_answers_gives_the_best_case(self):
        out = sample.bars(self.sample(40))
        self.assertIn("0.0% (0.0% to 8.8%)", out)
        self.assertTrue(8.0 < self.upper(out) < 9.0)

    def test_an_answers_file_with_no_rows_bounds_nothing(self):
        self.assertEqual(self.upper(sample.bars(self.sample(40), {})), 100.0)

    def test_a_stratum_with_no_answer_counts_as_wrong(self):
        rows = self.sample(2) + [{"id": "nudi-9999", "layout": "nudi", "status": "likely", "stratum_lines": "1000", "stratum_sampled": "1"}]
        out = sample.bars(rows, {"nudi-0000": "right", "nudi-0001": "right"})
        self.assertGreaterEqual(self.upper(out), 50.0)


class Tesseract(unittest.TestCase):
    def read(self, stdout, code=0, n=3):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tesseract.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout=stdout, returncode=code)
            return tesseract.read_images([f"{i}.png" for i in range(n)], "kan", Path(tmp, "list.txt"), "tessdata")

    def test_1_reading_per_image(self):
        self.assertEqual(self.read("ಕ\n\fಖ\n\fಗ\n"), ["ಕ", "ಖ", "ಗ"])

    def test_a_missing_page_drops_the_line(self):
        self.assertIsNone(self.read("ಕ\n\fಖ\n"))
        self.assertIsNone(self.read("ಕ\n\fಖ\n\fಗ\n", code=1))

    def test_resume_drops_a_cut_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp, "ocr.jsonl")
            log.write_text('{"line_id": "a"}\n{"line_id": "b"}\n{"line_id": "c", "cr', encoding="utf-8")
            self.assertEqual(tesseract.resume(log), {"a", "b"})
            self.assertEqual(log.read_text().count("\n"), 2)
            self.assertEqual(tesseract.resume(Path(tmp, "none.jsonl")), set())


def pdf_with_2_fonts():
    """A 1-page PDF with 2 fonts of the same name and different Differences lists."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> >>",
            "<< /Type /Font /Subtype /TrueType /BaseFont /Nudi01e /Encoding << /Differences [65 /c80] >> >>",
            "<< /Type /Font /Subtype /TrueType /BaseFont /Nudi01e /Encoding << /Differences [65 /c90] >> >>"]
    out, offsets = b"%PDF-1.4\n", []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj {body} endobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


@unittest.skipUnless(importlib.util.find_spec("pdfminer") and importlib.util.find_spec("fontTools"), "needs pdfminer.six and fontTools")
class LineBuilding(unittest.TestCase):
    def setUp(self):
        import extract
        self.x = extract

    def glyph(self, code, x, y=100.0, font="ABCDEF+Nudi01e", adv=5.0):
        return {"code": code, "x": x, "y": y, "size": 10.0, "adv": adv, "font": font, "bbox": (x, y - 3, x + adv, y + 7)}

    def test_runs_split_at_a_new_baseline_and_a_wide_gap(self):
        gs = [self.glyph(0x50, 10), self.glyph(0xC0, 15), self.glyph(0x50, 10, y=80), self.glyph(0x50, 100, y=80)]
        self.assertEqual([len(r) for r in self.x.segments(gs)], [2, 1, 1])

    def test_runs_split_where_the_font_family_changes(self):
        gs = [self.glyph(0x50, 10), self.glyph(0x31, 15, font="Arial"), self.glyph(0x20, 20, font="Arial"),
              self.glyph(0x50, 25, font="Nudi01e,Bold")]
        parts = self.x.by_family(gs)
        self.assertEqual([len(p) for p in parts], [1, 2, 1])

    def test_a_bold_overprint_is_dropped(self):
        gs = [self.glyph(0x50, 10), self.glyph(0x50, 10.3), self.glyph(0xC0, 15)]
        self.assertEqual(len(self.x.dedupe(gs)), 2)
        self.assertTrue(self.x.overprint(self.glyph(0x50, 10.5), gs[:1]))

    def test_a_gap_becomes_1_space(self):
        gs = [self.glyph(0x50, 10), self.glyph(0xC0, 15), self.glyph(0x50, 30)]
        self.assertEqual(self.x.line_codes(gs), [0x50, 0xC0, 0x20, 0x50])

    def test_differences_are_kept_per_font_object(self):
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfparser import PDFParser
        doc = PDFDocument(PDFParser(io.BytesIO(pdf_with_2_fonts())))
        self.assertEqual(self.x.differences(doc), {4: {65: 80}, 5: {65: 90}})

    def test_content_detection_needs_a_hidden_or_kannada_font_name(self):
        for name, ok in (("CIDFont+F1", True), ("SHREE-KAN7-0850", True), ("SHREE-DEV-0706E", False),
                         ("KNB_TTNandiEN", False), ("BookAntiqua", False)):
            self.assertEqual(self.x.content_detection_allowed(name), ok, name)


if __name__ == "__main__":
    unittest.main()
