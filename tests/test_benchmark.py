"""The benchmark lines, their documents and the reader sample are well formed."""

import contextlib
import csv
import io
import json
import re
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmark"
sys.path.insert(0, str(ROOT / "conformance"))
sys.path.insert(0, str(BENCH / "tools"))

import run  # noqa: E402
import sample  # noqa: E402

COLUMNS = ["id", "status", "codes", "expected", "source", "options", "document", "page", "box", "fonts", "found_by"]
STATUSES = {"verified", "confirmed", "likely", "unresolved"}
HEX = re.compile(r"^[0-9A-F]{2}( [0-9A-F]{2})*$")


def rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return [r for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if r and not r[0].startswith("#")]


class Lines(unittest.TestCase):
    def setUp(self):
        self.documents = {r["document"]: r for r in csv.DictReader(open(BENCH / "documents.tsv", encoding="utf-8"), delimiter="\t")}

    def test_columns_and_values(self):
        seen = set()
        for layout in run.LAYOUTS:
            path = BENCH / "lines" / f"{layout}.tsv"
            table = rows(path)
            self.assertEqual(table[0], COLUMNS, path)
            for r in table[1:]:
                with self.subTest(r[0]):
                    self.assertEqual(len(r), len(COLUMNS))
                    line = dict(zip(COLUMNS, r))
                    self.assertTrue(line["id"].startswith(layout + "-"))
                    self.assertNotIn(line["id"], seen)
                    seen.add(line["id"])
                    self.assertIn(line["status"], STATUSES)
                    self.assertRegex(line["codes"], HEX)
                    self.assertTrue(line["expected"].strip())
                    self.assertEqual(unicodedata.normalize("NFC", line["expected"]), line["expected"])
                    self.assertIn(line["options"], ("", "kannada_digits"))
                    self.assertIn(line["document"], self.documents)
                    self.assertIn(self.documents[line["document"]]["url"], line["source"])
                    self.assertGreaterEqual(int(line["page"]), 1)
                    self.assertEqual(len(line["box"].split()), 4)
                    self.assertIn(line["found_by"], ("font name", "content"))
        self.assertGreaterEqual(len(seen), 5000)

    def test_runner_reads_the_lines(self):
        cases = run.load_cases(BENCH / "lines")
        self.assertEqual(len(cases), sum(len(rows(BENCH / "lines" / f"{layout}.tsv")) - 1 for layout in run.LAYOUTS))
        digits = [c for c in cases if c["options"]]
        self.assertGreater(len(digits), 0)
        self.assertTrue(all(c["options"] == ["kannada_digits"] for c in digits))
        reqs = list(run.requests(digits[:1], {"examples": []}, [], ("read",)))
        self.assertTrue(reqs[0]["options"]["kannada_digits"])

    def test_runner_takes_a_cases_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = rows(BENCH / "lines" / "nudi.tsv")
            Path(tmp, "nudi.tsv").write_text("\n".join("\t".join(r) for r in table[:3]) + "\n", encoding="utf-8")
            out = Path(tmp, "out.json")
            args = ["--cases", tmp, "--layouts", "nudi", "--no-detect", "--no-fonts", "--out", str(out),
                    "--", sys.executable, str(ROOT / "reference" / "adapter.py")]
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(args)
            ids = {k.split(" ", 1)[1] for k in json.loads(out.read_text(encoding="utf-8")) if k.startswith("read nudi-")}
            self.assertEqual(ids, {r[0] for r in table[1:3]})

    def test_an_empty_cases_folder_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit):
            run.load_cases(tmp)

    def test_documents(self):
        for d, r in self.documents.items():
            with self.subTest(d):
                self.assertRegex(r["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(r["url"].startswith("http"))
                self.assertTrue(r["archive"].startswith("https://") or r["archive"] == "none")
                self.assertEqual(r["license"], "LicenseRef-Excerpts")


class Sample(unittest.TestCase):
    def test_sample_ids_and_strata(self):
        lines = sample.load(BENCH / "lines")
        status = {r["id"]: (r["layout"], r["status"]) for r in lines}
        drawn = list(csv.DictReader(open(BENCH / "review" / "sample.tsv", encoding="utf-8"), delimiter="\t"))
        self.assertGreaterEqual(len(drawn), 350)
        for r in drawn:
            self.assertEqual(status[r["id"]], (r["layout"], r["status"]))

    def test_draw_is_repeatable(self):
        lines = sample.load(BENCH / "lines")
        self.assertEqual(sample.draw(lines, 80, 1), sample.draw(lines, 80, 1))

    def test_wilson(self):
        lo, hi = sample.wilson(0, 80)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0458, places=3)
        lo, hi = sample.wilson(40, 80)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)


if __name__ == "__main__":
    unittest.main()
