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

    def test_a_stray_glyph_counts_against_its_output(self):
        # OCR skips the unconverted ç; the output without it must still win.
        outs = {"a": "ಪ್ರಿಯ", "b": "ಪಿçಯ"}
        d = truth.decide({}, {"outputs": outs}, ocr("ಪಿಯ", {**rendered("ಪ್ರಿಯ", "ಪ್ರಿಯ"), **rendered("ಪಿçಯ", "ಪಿಯ")}))
        self.assertNotEqual(d["expected"], "ಪಿçಯ")
        self.assertEqual(truth.stray("ಪು£ರಾ"), 1)
        self.assertEqual(truth.stray("ರೂ.500 ‘ಕನ್ನಡ’"), 0)

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

    def test_latin_words_and_punctuation_are_not_compared(self):
        self.assertTrue(truth.ignorable("Papers", "೩೮118"))
        self.assertTrue(truth.ignorable(":-", "ು"))
        self.assertTrue(truth.ignorable("40", "4೦"))
        self.assertFalse(truth.ignorable("ಧ", "ದ"))


if __name__ == "__main__":
    unittest.main()
