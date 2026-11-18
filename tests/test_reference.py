import json
import subprocess
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

    def test_unicode_kannada_passes_through(self):
        for c in "ಕಂ್\u0964\u0965\u200c\u200d":
            self.assertTrue(kle.is_passing(c), hex(ord(c)))
        for c in "\u00c0\u0bae":
            self.assertFalse(kle.is_passing(c), hex(ord(c)))

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
            got = kle.font_info(ex["font"], FONTS)
            self.assertEqual(got, (ex["layout"], ex["legacy"], ex["kannada_digits"]), ex["font"])


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
    def run_with(self, script):
        return subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--markdown", "--", sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_error_answers_count_as_wrong(self):
        script = (
            "import json,sys\n"
            "for line in sys.stdin:\n"
            "    print(json.dumps({'id': json.loads(line)['id'], 'error': 'not supported'}), flush=True)\n"
        )
        r = self.run_with(script)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("Edge cases: 0 of", r.stdout)
        self.assertIn("Font names: 0 of", r.stdout)
        self.assertIn("Conforming (section 8): no.", r.stdout)

    def test_the_reference_reader_conforms(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--markdown", "--", sys.executable, str(ROOT / "reference" / "adapter.py")],
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Conforming (section 8): yes.", r.stdout)

    def test_wrong_detection_does_not_conform(self):
        script = (
            "import json,subprocess,sys\n"
            f"ref = subprocess.Popen([sys.executable, {str(ROOT / 'reference' / 'adapter.py')!r}], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)\n"
            "for line in sys.stdin:\n"
            "    ref.stdin.write(line); ref.stdin.flush()\n"
            "    resp = json.loads(ref.stdout.readline())\n"
            "    req = json.loads(line)\n"
            "    if req['op'] == 'detect' and not req['id'].startswith('edge-'):\n"
            "        resp['layout'] = 'nudi'\n"
            "    print(json.dumps(resp), flush=True)\n"
        )
        r = self.run_with(script)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("Edge cases: 64 of 64", r.stdout)
        self.assertIn("Conforming (section 8): no.", r.stdout)

    def test_a_silent_converter_times_out(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--timeout", "1", "--", sys.executable, "-c", "import time; time.sleep(30)"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("within 1", r.stderr)

    def test_the_reference_adapter_answers_bad_requests_with_errors(self):
        lines = [
            '{"id": "1", "op": "read", "layout": "baraha", "codes": "50 C0"}',
            '{"id": "2", "op": "read", "layout": "nope", "codes": "50"}',
            '{"id": "3", "op": "read", "layout": "nudi", "codes": "ZZ"}',
            '{"id": "4", "op": "read", "layout": "nudi", "codes": "1FF"}',
            "not json",
        ]
        r = subprocess.run(
            [sys.executable, str(ROOT / "reference" / "adapter.py")],
            input="\n".join(lines) + "\n",
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = [json.loads(line) for line in r.stdout.splitlines()]
        self.assertEqual(out[0]["text"], "ಕ")
        self.assertEqual([("error" in o) for o in out], [False, True, True, True, True])

    def test_each_condition_of_section_8_is_needed(self):
        row = {"group": "checked", "lines": 10, "exact": 10, "detected": 10}
        self.assertTrue(run.conforming([row], (5, 5), [], []))
        self.assertFalse(run.conforming([row], (4, 5), [], []))
        self.assertFalse(run.conforming([row], (5, 5), [{}], ["edge-000"]))
        self.assertFalse(run.conforming([dict(row, exact=9)], (5, 5), [], []))
        self.assertFalse(run.conforming([dict(row, detected=9)], (5, 5), [], []))
        self.assertTrue(run.conforming([dict(row, group="all", exact=9)], (5, 5), [], []))

    def test_a_partial_line_times_out(self):
        script = "import sys,time; sys.stdout.write('{\"id\": \"x'); sys.stdout.flush(); time.sleep(30)"
        r = subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--timeout", "1", "--", sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("within 1", r.stderr)

    def test_a_missing_command_is_reported(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--", str(ROOT / "no-such-converter")],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cannot start", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_a_reader_without_detection_or_fonts_can_conform(self):
        script = (
            "import json,subprocess,sys\n"
            f"ref = subprocess.Popen([sys.executable, {str(ROOT / 'reference' / 'adapter.py')!r}], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)\n"
            "for line in sys.stdin:\n"
            "    req = json.loads(line)\n"
            "    if req['op'] != 'read':\n"
            "        sys.exit(3)\n"
            "    ref.stdin.write(line); ref.stdin.flush()\n"
            "    print(ref.stdout.readline().strip(), flush=True)\n"
        )
        self.assertIn("stopped", self.run_with(script).stderr)
        r = subprocess.run(
            [sys.executable, str(ROOT / "conformance" / "run.py"), "--markdown", "--no-detect", "--no-fonts", "--", sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Detection: not tested.", r.stdout)

    def test_extra_fields_are_ignored(self):
        responses = {("detect", "x"): {"id": "x", "layout": "nudi", "clean": True}}
        self.assertEqual(run.answer(responses, "detect", "x"), {"layout": "nudi"})

    def test_written_lines_count_as_checked(self):
        cases = [
            {"id": f"x-{status}", "layout": "nudi", "status": status, "codes": "50 C0", "expected": "ಕ"}
            for status in ("verified", "read", "written", "pending", "unchecked")
        ]
        responses = {("read", c["id"]): {"text": "ಕ", "unknown": [], "malformed": []} for c in cases}
        rows, _ = run.summarize(cases, responses, {"examples": []})
        checked = [r for r in rows if r["group"] == "checked"]
        self.assertEqual([r["lines"] for r in checked], [3])

    def test_distance(self):
        self.assertEqual(run.distance("ಕನ್ನಡ", "ಕನ್ನಡ"), 0)
        self.assertEqual(run.distance("ಕನಡ", "ಕನ್ನಡ"), 2)
        self.assertEqual(run.distance("", "ಕ"), 1)


if __name__ == "__main__":
    unittest.main()
