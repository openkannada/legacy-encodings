import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "conformance"))
sys.path.insert(0, str(ROOT / "tools"))

import edge_cases  # noqa: E402
import kle  # noqa: E402
import run  # noqa: E402

TABLES = kle.load_tables()
FONTS = json.loads((ROOT / "tables" / "fonts.json").read_text(encoding="utf-8"))


def codes(hexes):
    return [int(h, 16) for h in hexes.split()]


def respond(module, tables, req):
    if req["op"] == "detect":
        return {"layout": module.detect(codes(req["codes"]), tables)}
    r = module.read(codes(req["codes"]), tables[req["layout"]], **req["options"])
    return {"text": r.text, "unknown": r.unknown, "malformed": [list(m) for m in r.malformed]}


class WorkedExamples(unittest.TestCase):
    """Section 5.8 of the specification."""

    def test_nudi_examples(self):
        for hexes, text in [
            ("50 C0 A3 C0 DF 71 C0", "ಕನ್ನಡ"),
            ("50 C9 C6 C3", "ಕೋ"),
            ("50 C0 F0", "ರ್ಕ"),
            ("A5 73 C0", "ಫ"),
        ]:
            r = kle.read(codes(hexes), TABLES["nudi"])
            self.assertEqual(r.text, text, hexes)
            self.assertTrue(r.clean, hexes)


class Cases(unittest.TestCase):
    def test_every_case_reads_as_expected(self):
        for case in run.load_cases():
            r = kle.read(codes(case["codes"]), TABLES[case["layout"]])
            self.assertEqual(r.text, case["expected"], case["id"])

    def test_every_edge_case_matches(self):
        for e in run.load_edge_cases():
            self.assertEqual(respond(kle, TABLES, e["request"]), e["expected"], e["request"]["id"])

    def test_font_examples(self):
        for ex in FONTS["examples"]:
            layout, legacy, digits = kle.font_info(ex["font"], FONTS)
            self.assertEqual(layout, ex["layout"], ex["font"])
            self.assertEqual(legacy, ex.get("legacy", legacy), ex["font"])
            self.assertEqual(digits, ex.get("kannada_digits", digits), ex["font"])


class EdgeCasesCoverEveryRule(unittest.TestCase):
    """Breaking any rule of the reference reader fails at least 1 edge case."""

    def test_each_broken_rule_fails_an_edge_case(self):
        edges = run.load_edge_cases()
        for section, rule, old, new in edge_cases.RULES:
            broken = edge_cases.mutant(old, new)
            tables = broken.load_tables()
            caught = any(respond(broken, tables, e["request"]) != e["expected"] for e in edges)
            self.assertTrue(caught, f"section {section}: {rule}")


class Runner(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(run.distance("ಕನ್ನಡ", "ಕನ್ನಡ"), 0)
        self.assertEqual(run.distance("ಕನಡ", "ಕನ್ನಡ"), 2)
        self.assertEqual(run.distance("", "ಕ"), 1)


if __name__ == "__main__":
    unittest.main()
