"""A reference reader for Kannada Legacy Encodings, written from spec/kle.md.

It follows the specification's steps literally and favors clarity over speed.
Section numbers in the comments are the specification's.
"""

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIRAMA = "್"
ANUSVARA = "ಂ"
RA = "ರ"
ASPIRATES = {"ಪ": "ಫ", "ಬ": "ಭ", "ಡ": "ಢ", "ದ": "ಧ"}
ORDER = ["nudi", "akruti", "shree-lipi", "nudi-b", "kan-eng"]

# Windows-1252 at 80 to 9F, with the 5 undefined codes as C1 controls (5.1).
_HIGH = "€\x81‚ƒ„…†‡ˆ‰Š‹Œ\x8dŽ\x8f\x90‘’“”•–—˜™š›œ\x9džŸ"


def code_char(code):
    return _HIGH[code - 0x80] if 0x80 <= code <= 0x9F else chr(code)


def char_class(c):
    o = ord(c)
    if 0x0C85 <= o <= 0x0C8C or 0x0C8E <= o <= 0x0C90 or 0x0C92 <= o <= 0x0C94 or o in (0x0CE0, 0x0CE1):
        return "vowel"
    if 0x0C95 <= o <= 0x0CA8 or 0x0CAA <= o <= 0x0CB3 or 0x0CB5 <= o <= 0x0CB9 or o == 0x0CDE:
        return "consonant"
    if 0x0CBE <= o <= 0x0CC4 or 0x0CC6 <= o <= 0x0CC8 or 0x0CCA <= o <= 0x0CCC or o in (0x0CD5, 0x0CD6, 0x0CE2, 0x0CE3):
        return "vowel-sign"
    if o == 0x0CCD:
        return "virama"
    if o == 0x0CBC:
        return "nukta"
    if 0x0C81 <= o <= 0x0C83 or 0x0CF1 <= o <= 0x0CF3:
        return "modifier"
    if 0x0951 <= o <= 0x0954 or 0x1CD0 <= o <= 0x1CD2 or 0x1CD4 <= o <= 0x1CE8 or o in (0x1CED, 0x1CF4) or 0x1CF7 <= o <= 0x1CF9:
        return "modifier"
    if 0x0CE6 <= o <= 0x0CEF:
        return "digit"
    return "other"


def is_letter_char(c):
    return char_class(c) in ("vowel", "consonant", "vowel-sign")


# The Unicode White_Space property (3.2).
_WHITE_SPACE = set(
    "\t\n\x0b\x0c\r \x85\xa0            "
    "    　"
)


def is_white_space(c):
    return c in _WHITE_SPACE


def is_passing(c):
    o = ord(c)
    return (
        is_white_space(c)
        or 0x21 <= o <= 0x2F
        or 0x3A <= o <= 0x40
        or 0x5B <= o <= 0x60
        or 0x7B <= o <= 0x7E
        or 0x2010 <= o <= 0x2027
        or o == 0xA0
    )


class Table:
    def __init__(self, doc):
        self.id = doc["id"]
        self.entries = {}
        for e in doc["entries"]:
            self.entries[tuple(int(c, 16) for c in e["codes"])] = e
        self.longest = max(len(k) for k in self.entries)

    def longest_entry(self, codes, i):
        """The entry with the most codes that equal the codes at i (5.2)."""
        best = None
        for n in range(1, min(self.longest, len(codes) - i) + 1):
            e = self.entries.get(tuple(codes[i : i + n]))
            if e is not None:
                best = (e, n)
        return best


def load_tables(directory=ROOT / "tables" / "json"):
    return {lid: Table(json.loads((directory / f"{lid}.json").read_text(encoding="utf-8"))) for lid in ORDER}


@dataclass
class Syllable:
    letter: str
    needs_sign: bool
    signed: bool = False
    signs: str = ""
    virama: bool = False
    ottus: list = field(default_factory=list)
    arka: bool = False
    mods: str = ""
    rejected: str = ""

    def add(self, e):
        """Adds an entry (5.3); False if its codes are rejected."""
        kind, value = e["kind"], e["value"]
        if kind == "sign" and value == VIRAMA:
            self.signed = True
            if self.virama:
                return False
            self.virama = True
            return True
        if kind == "sign":
            self.signed = True
            self.signs += value
            return True
        if kind == "ottu":
            consonants = [c for c in value if char_class(c) == "consonant"]
            self.ottus.extend(consonants)
            sign = value[len(consonants) :]
            if sign:
                self.signed = True
                self.signs += sign
            return True
        if kind == "arka":
            if self.arka:
                return False
            self.arka = True
            return True
        if kind == "mod":
            self.mods += value
            return True
        if kind == "aspirate":
            first = self.letter[:1]
            if first not in ASPIRATES:
                return False
            self.letter = ASPIRATES[first] + self.letter[1:]
            return True
        return False

    def text(self):
        """The syllable's text and whether it is well formed (5.5)."""
        letter = self.letter
        end = 1 if letter else 0
        while end + 1 < len(letter) and letter[end] == VIRAMA and char_class(letter[end + 1]) == "consonant":
            end += 2
        if end >= 3 and letter[end - 2] == VIRAMA and letter[end - 1] == RA:
            end -= 2
        s = (RA + VIRAMA if self.arka else "") + letter[:end]
        s += "".join(VIRAMA + o for o in self.ottus)
        s += letter[end:] + self.signs + (VIRAMA if self.virama else "") + self.mods
        s = unicodedata.normalize("NFC", s)
        vowel_signs = sum(char_class(c) == "vowel-sign" for c in s)
        on_vowel = bool(letter) and char_class(letter[0]) == "vowel"
        valid = not (self.needs_sign and not self.signed)
        valid = valid and vowel_signs <= 1
        valid = valid and not (on_vowel and (self.arka or self.signed or self.ottus))
        return s, valid


@dataclass
class Result:
    text: str
    unknown: list
    malformed: list

    @property
    def clean(self):
        return not self.unknown and not self.malformed


def read(codes, table, zero_as_anusvara=True, kannada_digits=False):
    """Reads a list of glyph codes in a layout (section 5)."""
    out = []
    unknown, malformed = [], []
    syllable = None

    def length():
        return sum(len(s) for s in out)

    def close():
        nonlocal syllable
        if syllable is None:
            return
        s, valid = syllable.text()
        start = length()
        out.append(s + syllable.rejected)
        if not valid:
            malformed.append((start, length()))
        syllable = None

    def last_char():
        for s in reversed(out):
            if s:
                return s[-1]
        return None

    i = 0
    while i < len(codes):
        match = table.longest_entry(codes, i)
        if match and is_white_space(code_char(codes[i])) and syllable is None:
            match = None
        if match is None:
            c = code_char(codes[i])
            nxt = table.longest_entry(codes, i + 1)
            starts = nxt is not None and nxt[0]["kind"] in ("letter", "base")
            close()
            if "0" <= c <= "9":
                prev = last_char()
                if zero_as_anusvara and c == "0" and starts and prev is not None and is_letter_char(prev):
                    out.append(ANUSVARA)
                elif kannada_digits:
                    out.append(chr(0x0CE6 + int(c)))
                else:
                    out.append(c)
            else:
                if not is_passing(c):
                    unknown.append(i)
                out.append(c)
            i += 1
            continue
        e, n = match
        glyphs = "".join(code_char(c) for c in codes[i : i + n])
        kind, value = e["kind"], e["value"]
        if kind in ("letter", "base"):
            close()
            syllable = Syllable(value, kind == "base")
        elif kind == "ignore":
            pass
        elif kind == "literal":
            close()
            out.append(value)
        elif syllable is not None:
            if not syllable.add(e):
                syllable.rejected += glyphs
                unknown.extend(range(i, i + n))
        else:
            stray = None
            if kind in ("sign", "mod") and value:
                stray = value
            elif kind == "ottu":
                consonants = [c for c in value if char_class(c) == "consonant"]
                stray = "".join(VIRAMA + c for c in consonants) + value[len(consonants) :]
            if stray is None:
                unknown.extend(range(i, i + n))
                out.append(glyphs)
            else:
                start = length()
                out.append(stray)
                malformed.append((start, start + len(stray)))
        i += n
    close()
    return Result("".join(out), unknown, malformed)


def detect(codes, tables):
    """The layout whose reading scores lowest (7.2)."""

    def score(lid):
        r = read(codes, tables[lid])
        latin = sum(c.isascii() and c.isalpha() for c in r.text)
        return (len(r.unknown) + len(r.malformed), latin, r.text.count(VIRAMA))

    return min(ORDER, key=lambda lid: (score(lid), ORDER.index(lid)))


def font_key(name):
    return "".join(c for c in name if c.isascii() and c.isalnum()).lower()


def font_info(name, fonts):
    """Layout, legacy flag and Kannada digit flag of a font name (7.1)."""
    key = font_key(name)
    layout, matched_first = None, False
    for n, rule in enumerate(fonts["layout_rules"]):
        if re.search(rule["match"], key):
            layout = rule["layout"]
            matched_first = n == 0
            break
    legacy = layout is not None or (
        not matched_first and any(re.search(r["match"], key) for r in fonts["legacy_without_table"])
    )
    digits = any(re.search(r["match"], key) for r in fonts["kannada_digits"])
    return layout, legacy, digits
