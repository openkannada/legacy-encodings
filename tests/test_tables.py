import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import tables  # noqa: E402


def parse(*rows):
    return tables.parse_table("\n".join(rows), "t")[1]


class TableRules(unittest.TestCase):
    def rejects(self, *rows):
        with self.assertRaises(ValueError):
            parse(*rows)

    def test_a_valid_table_parses(self):
        entries = parse(
            "# notes",
            "50\tbase\tಕ",
            "C0\tsign\t",
            "DF\tottu\tನ",
            "F0\tarka\t",
            "73\taspirate\t",
            "41\tmod\tಂ",
            "C9\tsign\tೆ\twith ೈ",
            "20 BD\tsign\tೃ\tread",
            "FB\tbase\tಕ್ಷ\tread",
            "86\tliteral\t।",
        )
        self.assertEqual(len(entries), 10)
        self.assertEqual(entries[6]["prefer"], {"type": "with", "chars": ["ೈ"]})

    def test_codes_are_unique(self):
        self.rejects("50\tbase\tಕ", "50\tbase\tಖ")

    def test_codes_are_uppercase_hex_pairs(self):
        self.rejects("5\tbase\tಕ")
        self.rejects("c0\tsign\t")

    def test_a_sequence_after_a_space_is_read_only(self):
        for code in ["09", "0A", "0B", "0C", "0D", "20", "A0"]:
            self.rejects(f"{code} BD\tsign\tೃ")
        self.assertEqual(len(parse("A0 58\tottu\tಯ\tread")), 1)

    def test_a_written_literal_is_1_character(self):
        self.rejects("F5\tliteral\t--")
        self.assertEqual(len(parse("F5\tliteral\t--\tread")), 1)

    def test_preference_characters_are_single(self):
        self.rejects("DF\tottu\tನ\ton ಪಫ")

    def test_a_base_is_a_consonant_or_cluster(self):
        self.rejects("50\tbase\tಅ")
        self.rejects("50\tbase\tಕ್")

    def test_a_written_base_is_1_consonant(self):
        self.rejects("FB\tbase\tಕ್ಷ")

    def test_an_ottu_is_consonants_and_1_sign(self):
        self.rejects("DF\tottu\tೃ")
        self.rejects("DF\tottu\tಕೃೃ")

    def test_a_sign_is_1_vowel_sign_or_virama(self):
        self.rejects("C1\tsign\tಾಾ")
        self.rejects("C1\tsign\tಕ")

    def test_a_letter_starts_with_a_letter(self):
        self.rejects("51\tletter\tಿ")

    def test_a_mod_is_1_modifier(self):
        self.rejects("41\tmod\tಕ")

    def test_marks_without_value_take_none(self):
        self.rejects("F0\tarka\tರ")

    def test_a_literal_needs_a_value(self):
        self.rejects("86\tliteral\t")

    def test_values_other_than_letters_and_signs_are_nfc(self):
        self.rejects("86\tliteral\tಕ\u0cc6\u0cc2\tread")

    def test_preferences_only_on_choosable_kinds(self):
        self.rejects("50\tbase\tಕ\ton ಕ")
        self.rejects("C0\tsign\t\tafter-ottu")
        self.rejects("C9\tsign\tೆ\tsoon")


class Fonts(unittest.TestCase):
    def setUp(self):
        self.fonts = json.loads((ROOT / "tables" / "fonts.json").read_text(encoding="utf-8"))

    def test_examples_hold(self):
        tables.check_fonts()

    def test_the_key_keeps_ascii_letters_and_digits(self):
        self.assertEqual(tables.font_key('"Shree-Kan-0850 Bold"'), "shreekan0850bold")

    def test_unicode_fonts_are_not_legacy(self):
        self.assertIsNone(tables.font_layout(self.fonts, "Nudi Unicode 01"))
        self.assertIsNone(tables.font_layout(self.fonts, "BRH Kannada Unicode"))
        self.assertFalse(tables.is_legacy(self.fonts, "Shree-Kan-0851 Unicode"))

    def test_other_shree_kan_fonts_are_legacy_with_no_table(self):
        self.assertIsNone(tables.font_layout(self.fonts, "Shree-Kan-0851"))
        self.assertTrue(tables.is_legacy(self.fonts, "Shree-Kan-0851"))


class Generated(unittest.TestCase):
    def test_json_tables_are_current(self):
        self.assertEqual(tables.main(["check"]), 0)

    def test_draws_latin(self):
        latin = {
            p.stem: json.loads(p.read_text(encoding="utf-8"))["draws_latin"]
            for p in (ROOT / "tables" / "json").glob("*.json")
        }
        self.assertEqual(
            latin,
            {"nudi": False, "akruti": False, "shree-lipi": False, "nudi-b": True, "kan-eng": True},
        )

    def test_json_tables_follow_the_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        schema = json.loads((ROOT / "schema" / "layout.schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for path in (ROOT / "tables" / "json").glob("*.json"):
            errors = list(validator.iter_errors(json.loads(path.read_text(encoding="utf-8"))))
            self.assertEqual(errors, [], path.name)

    def test_the_schema_rejects_entries_that_break_the_rules(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        schema = json.loads((ROOT / "schema" / "layout.schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        doc = json.loads((ROOT / "tables" / "json" / "nudi.json").read_text(encoding="utf-8"))

        def valid(entry):
            return validator.is_valid(dict(doc, entries=[entry]))

        read = {"type": "read"}
        for code in ["09", "0A", "0B", "0C", "0D", "20", "A0"]:
            self.assertFalse(valid({"codes": [code, "BD"], "kind": "sign", "value": "ೃ"}), code)
        self.assertTrue(valid({"codes": ["20", "BD"], "kind": "sign", "value": "ೃ", "prefer": read}))
        self.assertFalse(valid({"codes": ["C0"], "kind": "sign", "value": "", "prefer": {"type": "on", "chars": ["ಕ"]}}))
        self.assertFalse(valid({"codes": ["C0"], "kind": "sign", "value": "ಾಾ"}))
        self.assertFalse(valid({"codes": ["FB"], "kind": "base", "value": "ಕ್ಷ"}))
        self.assertTrue(valid({"codes": ["FB"], "kind": "base", "value": "ಕ್ಷ", "prefer": read}))
        self.assertFalse(valid({"codes": ["50"], "kind": "base", "value": "ಕ", "prefer": {"type": "after-ottu"}}))
        self.assertFalse(valid({"codes": ["F0"], "kind": "arka", "value": "ರ"}))
        self.assertFalse(valid({"codes": ["DF"], "kind": "ottu", "value": "ನ", "prefer": {"type": "on", "chars": ["ಪಫ"]}}))
        self.assertFalse(valid({"codes": ["df"], "kind": "ottu", "value": "ನ"}))
        self.assertFalse(valid({"codes": ["50"], "kind": "base", "value": ""}))
        self.assertFalse(valid({"codes": ["C9"], "kind": "sign", "value": "ೆ", "prefer": {"type": "on"}}))
        self.assertFalse(valid({"codes": ["C9"], "kind": "sign", "value": "ೆ", "prefer": {"type": "read", "chars": ["ಕ"]}}))


if __name__ == "__main__":
    unittest.main()
