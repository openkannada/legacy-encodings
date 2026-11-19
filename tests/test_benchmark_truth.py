"""The rules that choose a benchmark line's expected text from converter outputs and OCR readings."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmark" / "tools"))

import truth  # noqa: E402


def ocr(page, renders=None):
    """OCR readings: the page by both engines, and each candidate's renderings."""
    return {"crop": {"kan_ft_ofl3": page, "kan": page}, "renders": renders or {}}


def rendered(text, reading):
    return {text: {"noto-sans": {"kan_ft_ofl3": reading, "kan": reading}}}


class Decide(unittest.TestCase):
    def test_unanimous_and_read_exactly(self):
        d = truth.decide({}, {"outputs": {"a": "ಕನ್ನಡ ನಾಡು", "b": "ಕನ್ನಡ ನಾಡು"}}, ocr("ಕನ್ನಡ ನಾಡು"))
        self.assertEqual((d["tier"], d["expected"]), ("A", "ಕನ್ನಡ ನಾಡು"))

    def test_the_output_read_exactly_wins(self):
        outs = {"a": "ವಿದ್ಯಾರ್ಥಿ", "b": "ವಿದಾಥ್ಯಿರ"}
        d = truth.decide({}, {"outputs": outs}, ocr("ವಿದ್ಯಾರ್ಥಿ"))
        self.assertEqual((d["tier"], d["expected"]), ("A", "ವಿದ್ಯಾರ್ಥಿ"))

    def test_an_ocr_habit_is_explained_by_the_rendering(self):
        # The page has the typed ದ್ದಿ; OCR reads ದ್ಧಿ on the page and on the rendering alike.
        d = truth.decide({}, {"outputs": {"a": "ಅಭಿವೃದ್ದಿ"}}, ocr("ಅಭಿವೃದ್ಧಿ", rendered("ಅಭಿವೃದ್ದಿ", "ಅಭಿವೃದ್ಧಿ")))
        self.assertEqual((d["tier"], d["expected"]), ("A", "ಅಭಿವೃದ್ದಿ"))

    def test_an_unexplained_difference_leaves_the_line_unresolved(self):
        d = truth.decide({}, {"outputs": {"a": "ಅಭಿವೃದ್ದಿ"}}, ocr("ಅಭಿವೃದ್ಧಿ", rendered("ಅಭಿವೃದ್ದಿ", "ಅಭಿವೃದ್ದಿ")))
        self.assertNotEqual(d["tier"], "A")

    def test_zero_after_a_letter_is_the_anusvara(self):
        outs = {"a": "ಕುಟು0ಬ", "b": "ಕುಟುಂಬ"}
        d = truth.decide({}, {"outputs": outs}, ocr("ಕುಟು೦ಬ"))
        self.assertEqual((d["tier"], d["expected"]), ("A", "ಕುಟುಂಬ"))

    def test_a_tie_of_explained_candidates_is_never_confirmed(self):
        # The page has the typed ದ್ದಿ; OCR reads ದ್ಧಿ everywhere, so both outputs explain the page.
        outs = {"a": "ಅಭಿವೃದ್ದಿ", "b": "ಅಭಿವೃದ್ಧಿ"}
        renders = {**rendered("ಅಭಿವೃದ್ದಿ", "ಅಭಿವೃದ್ಧಿ"), **rendered("ಅಭಿವೃದ್ಧಿ", "ಅಭಿವೃದ್ಧಿ")}
        d = truth.decide({"layout": "nudi"}, {"outputs": outs}, ocr("ಅಭಿವೃದ್ಧಿ", renders))
        self.assertNotEqual(d["tier"], "A")

    def test_an_exact_reading_breaks_a_tie_into_likely(self):
        page = {"kan_ft_ofl3": "ಅಬಕಡಎ", "kan": "ಅಗಕತಎ"}
        renders = {
            "ಅಬಕಡಎ": {"noto-sans": {"kan_ft_ofl3": "ಅಬಕಡಎ", "kan": "ಅಗಕತಎ"}},
            "ಅಗಕಡಎ": {"noto-sans": {"kan_ft_ofl3": "ಅಬಕಡಎ", "kan": "ಅಗಕತಎ"}},
        }
        d = truth.decide({"layout": "nudi"}, {"outputs": {"a": "ಅಗಕಡಎ", "b": "ಅಬಕಡಎ"}}, {"crop": page, "renders": renders})
        self.assertEqual((d["tier"], d["expected"]), ("B", "ಅಬಕಡಎ"))

    def test_one_engine_reading_exactly_does_not_override_the_other(self):
        page = {"kan_ft_ofl3": "ಕರಾವಳಿ ಪ್ರದೇಶ", "kan": "ಕರಾವಳಿ ಪದೇಶ"}
        d = truth.decide({"layout": "nudi"}, {"outputs": {"a": "ಕರಾವಳಿ ಪದೇಶ"}}, {"crop": page, "renders": {}})
        self.assertNotEqual(d["tier"], "A")

    def test_a_single_candidate_is_confirmed_only_without_unexplained_edits(self):
        d = truth.decide({"layout": "nudi-b"}, {"outputs": {"a": "ಸಮಾಜ ಕಲ್ಯಾಣ"}}, ocr("ಸಮಾಜ ಕಲ್ಯಾಣ"))
        self.assertEqual(d["tier"], "A")
        page = {"kan_ft_ofl3": "ಸಮಾಜ ಕಲ್ಯಾಣ", "kan": "ಸಮಾಜ ಕಲ್ಯಣ"}
        d = truth.decide({"layout": "nudi-b"}, {"outputs": {"a": "ಸಮಾಜ ಕಲ್ಯಾಣ"}}, {"crop": page, "renders": {}})
        self.assertEqual(d["tier"], "B")
        d = truth.decide({"layout": "nudi-b"}, {"outputs": {"a": "ಸಮಾಜ ಕಲ್ಯಾಣ"}}, ocr("ಸಮಾಜ ಕಲ್ಯಣ"))
        self.assertEqual(d["tier"], "C")

    def test_a_stray_glyph_counts_against_its_output(self):
        # OCR skips the unconverted ç; the output without it must still win.
        outs = {"a": "ಪ್ರಿಯ", "b": "ಪಿçಯ"}
        d = truth.decide({}, {"outputs": outs}, ocr("ಪಿಯ", {**rendered("ಪ್ರಿಯ", "ಪ್ರಿಯ"), **rendered("ಪಿçಯ", "ಪಿಯ")}))
        self.assertNotEqual(d["expected"], "ಪಿçಯ")
        self.assertNotEqual(d["tier"], "A")
        self.assertEqual(truth.stray("ಪು£ರಾ"), 1)
        self.assertEqual(truth.stray("ರೂ.500 ‘ಕನ್ನಡ’"), 0)
        self.assertEqual(truth.stray("ಕನ್ನಡ ನಾಡು Š", bilingual=False), 1)

    def test_a_kept_joiner_leaves_the_line_unresolved(self):
        outs = {"a": "ಪೂರ್ಯಾ", "b": "ಪೂರ‍್ಯಾ"}
        d = truth.decide({}, {"outputs": outs}, ocr("ಪೂರ್ಯಾ"))
        self.assertEqual(d["tier"], "C")

    def test_digit_script_follows_the_font(self):
        outs = {"a": "ಸಂಖ್ಯೆ 12", "b": "ಸಂಖ್ಯೆ ೧೨"}
        d = truth.decide({"kannada_digits": True}, {"outputs": outs}, ocr("ಸಂಖ್ಯೆ 12"))
        self.assertEqual(d["expected"], "ಸಂಖ್ಯೆ ೧೨")
        d = truth.decide({"kannada_digits": False}, {"outputs": outs}, ocr("ಸಂಖ್ಯೆ ೧೨"))
        self.assertEqual(d["expected"], "ಸಂಖ್ಯೆ 12")

    def test_latin_is_left_unconverted_outside_bilingual_layouts(self):
        # In Nudi every ASCII code is a Kannada glyph, so a Latin word is a reading failure.
        outs = {"a": "vi) ಸಮಾಜ", "b": "ತು) ಸಮಾಜ"}
        d = truth.decide({"layout": "nudi"}, {"outputs": outs}, ocr("ತು) ಸಮಾಜ"))
        self.assertEqual((d["tier"], d["expected"]), ("A", "ತು) ಸಮಾಜ"))
        d = truth.decide({"layout": "nudi"}, {"outputs": {"a": "vi) ಸಮಾಜ"}}, ocr("ತು) ಸಮಾಜ"))
        self.assertNotEqual(d["tier"], "A")
        self.assertFalse(truth.ignorable("vi", "ತು", bilingual=False))
        self.assertEqual(truth.stray("vi) ಸಮಾಜ", bilingual=False), 2)
        self.assertEqual(truth.stray("vi) ಸಮಾಜ", bilingual=True), 0)
        # In Nudi B-Akshara the Latin word is real, and the Kannada models cannot read it.
        d = truth.decide({"layout": "nudi-b"}, {"outputs": {"a": "ಈಗ Papers ತೆಗೆದುಕೊಳ್ಳೋಣ"}}, ocr("ಈಗ ೩೮118 ತೆಗೆದುಕೊಳ್ಳೋಣ"))
        self.assertEqual(d["tier"], "A")
        d = truth.decide({"layout": "kan-eng"}, {"outputs": {"a": "ಕರ್ನಾಟಕ Act ಕಾಯ್ದೆ"}}, ocr("ಕರ್ನಾಟಕ ಆಕ್ಟ್ ಕಾಯ್ದೆ"))
        self.assertEqual(d["tier"], "A")

    def test_latin_words_and_punctuation_are_not_compared(self):
        self.assertTrue(truth.ignorable("Papers", "೩೮118"))
        self.assertTrue(truth.ignorable(":-", "ು"))
        self.assertTrue(truth.ignorable("40", "4೦"))
        self.assertFalse(truth.ignorable("ಧ", "ದ"))


if __name__ == "__main__":
    unittest.main()
