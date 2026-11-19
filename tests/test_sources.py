"""The Nudi table against L2/03-068 and the reference normalization against its vectors."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "tools"))

import kle  # noqa: E402
import l2_03_068  # noqa: E402
from normalize import canonical  # noqa: E402


class ProposalChart(unittest.TestCase):
    def test_known_differences_only(self):
        results = l2_03_068.check(l2_03_068.load_source(), kle.load_tables()["nudi"])
        differs = sorted({(cp, " ".join(f"{c:02X}" for c in codes)) for cp, _, codes, status, _ in results if status == "differs"})
        self.assertEqual(differs, [(0x0CBC, "F3"), (0x0CBD, "73"), (0x0CC4, "F1")])
        agrees = sum(1 for r in results if r[3] == "agrees")
        self.assertEqual(agrees, 76)
        self.assertEqual(len(results), 82)


class Normalization(unittest.TestCase):
    def test_canonical_vectors(self):
        vectors = json.loads((ROOT / "conformance" / "normalization-vectors.json").read_text(encoding="utf-8"))
        canonical_vectors = [v for v in vectors if v["form"] == "canonical"]
        self.assertGreater(len(canonical_vectors), 40)
        for v in canonical_vectors:
            with self.subTest(v["id"]):
                self.assertEqual(canonical(v["input"]), v["expected"])
                self.assertEqual(canonical(v["expected"]), v["expected"])

    def test_classes_match_kannadi(self):
        # U+0C80 is not a mark. A joiner before a Vedic mark stays, but only Kannada
        # marks collapse when repeated.
        self.assertEqual(canonical("ಕ\u0c80\u0c80"), "ಕ\u0c80\u0c80")
        self.assertEqual(canonical("ಯ\u200d\u0c80"), "ಯ\u0c80")
        self.assertEqual(canonical("ಕ\u200c\u0951"), "ಕ\u200c\u0951")
        self.assertEqual(canonical("क\u0951\u0951"), "क\u0951\u0951")


if __name__ == "__main__":
    unittest.main()
