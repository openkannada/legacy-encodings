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


class Clarifications(unittest.TestCase):
    """Inputs where a looser reading of the specification would differ from kannadi."""

    def check(self, layout, hexes, text, unknown, malformed):
        r = kle.read(codes(hexes), TABLES[layout])
        self.assertEqual((r.text, r.unknown, [list(m) for m in r.malformed]), (text, unknown, malformed))

    def test_no_break_space_starts_no_match_outside_a_syllable(self):
        self.check("akruti", "A0 58", "\u00a0\u0ccd\u0caf", [], [[1, 3]])

    def test_the_zero_lookahead_skips_the_white_space_refusal(self):
        self.check("nudi-b", "83 30 20 A6 D0 D4", "ಅಂ ಯ", [], [])

    def test_stray_marks_are_not_normalized(self):
        self.check("nudi", "C9 C3", "\u0cc6\u0cd5", [], [[0, 1], [1, 2]])

    def test_unknown_positions_count_codes(self):
        self.check("nudi", "50 C0 68", "ಕh", [2], [])


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
