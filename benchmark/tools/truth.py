"""Chooses each line's expected text from the converters' outputs by what OCR reads on the page.

Usage: truth.py LINES.jsonl CANDIDATES.jsonl OCR.jsonl OUT.jsonl

Texts are compared in canonical form (normalization profile) without white space or joiners.
For each candidate and OCR engine, the reading of the line image is aligned to the candidate.
An edit is explained when the same engine makes the same edit reading that candidate rendered
in a Unicode font: it is then an OCR habit, not a difference on the page. Not counted at all:
swaps between digits or punctuation, zero against ಂ, punctuation read as at most 2 other
characters, and, in
Nudi B-Akshara and Kan-Eng, Latin words of 2 letters or more, which the Kannada models do not
read. A Latin letter or a symbol outside ASCII written against a Kannada letter always counts,
once per engine, and so does any such character in the other layouts, where every ASCII code is
a Kannada glyph. A candidate's evidence against it is its count of unexplained edits over both
engines.

Outputs that differ only in a zero after a letter count as 1 candidate, written with ಂ (section
5.6). The expected text is the winner in canonical form.

Tiers (export.py names them):
  A  confirmed: the best candidate has no unexplained edit, and every other candidate has some
  B  likely: the best candidate has exactly 1 unexplained edit and every other candidate more; or it
     ties with no unexplained edit but wins on an exact reading by an engine, then on closeness to
     the readings, then on the digit script the font draws (section 7.1)
  C  unresolved: anything else, or the agreeing outputs differ in a joiner the profile keeps;
     the expected text is a guess, for a Kannada reader
"""
import difflib
import json
import sys

import paths  # noqa: F401  (puts the reference reader on the path)
from normalize import canonical  # noqa: E402

JOINERS = {"\u200c", "\u200d"}
ENGINES = ["kan_ft_ofl3", "kan"]


def key(t):
    return "".join(c for c in canonical(t) if not c.isspace() and c not in JOINERS)


def is_kannada_letter(c):
    """Kannada letters, signs and marks: anything in the block but its digits."""
    return "\u0c80" <= c <= "\u0cff" and not "\u0ce6" <= c <= "\u0cef"


def is_digit(c):
    return c.isdigit()


def is_punct(c):
    return not c.isalnum() and not is_kannada_letter(c)


ZEROS = set("0\u0ce6oO")
ANUSVARA = "\u0c82"


# Layouts with Latin letters at the ASCII letter codes; in the others every ASCII code is a Kannada glyph.
BILINGUAL = {"nudi-b", "kan-eng"}


def ignorable(a, b, bilingual=True):
    """Edits OCR makes on its own: digit script, punctuation, Latin words, and zero against ಂ."""
    if a and b and set(a + b) <= ZEROS | {ANUSVARA}:
        return True
    if bilingual and a.isascii() and sum(c.isalpha() for c in a) >= 2:
        return True
    if all(is_digit(c) or is_punct(c) for c in a) and all(is_digit(c) or is_punct(c) for c in b):
        return True
    return bool(a) and all(is_punct(c) for c in a) and len(b) <= 2


def edits(cand, read, bilingual=True):
    out = set()
    sm = difflib.SequenceMatcher(None, cand, read, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal" and not ignorable(cand[i1:i2], read[j1:j2], bilingual):
            out.add((op, i1, i2, read[j1:j2]))
    return out


TYPOGRAPHIC = set("\u2018\u2019\u201c\u201d\u2013\u2014\u2022\u2026\u00a0")


def stray(text, bilingual=True):
    """Glyphs a converter left unconverted, such as ç or £ in a Nudi word: Latin letters and
    symbols outside ASCII written against a Kannada letter, and, in a layout whose ASCII codes
    are all Kannada glyphs, every such character."""
    n = 0
    for i, c in enumerate(text):
        if (c.isascii() and c.isalpha()) or (not c.isascii() and not "\u0c80" <= c <= "\u0cff" and c not in TYPOGRAPHIC):
            near = text[max(0, i - 1): i] + text[i + 1: i + 2]
            n += not bilingual or any(is_kannada_letter(x) for x in near)
    return n


def as_anusvara(text):
    """The text with each zero after a Kannada letter read as ಂ (section 5.6)."""
    return "".join(ANUSVARA if c in ZEROS and i and is_kannada_letter(text[i - 1]) else c for i, c in enumerate(text))


def evidence(cand_text, crop, renders, bilingual=True):
    c = key(cand_text)
    odd = stray(canonical(cand_text), bilingual)
    total, direct, detail = 0, {}, {}
    for e in ENGINES:
        if e not in crop:
            continue
        seen = edits(c, key(crop[e]), bilingual)
        direct[e] = len(seen) + odd
        explained = set()
        for face in (renders or {}).values():
            if face and e in face:
                explained |= edits(c, key(face[e]), bilingual)
        left = seen - explained
        # OCR skips a stray glyph on the page and on the rendering alike, so it is counted here.
        detail[e] = len(left) + odd
        total += len(left) + odd
    return total, direct, detail


def decide(line, cand, ocr):
    outs = {k: v for k, v in cand["outputs"].items() if v}
    if not outs:
        return {"tier": "C", "reason": "no converter output"}
    bilingual = line.get("layout") in BILINGUAL
    want_kn_digits = line.get("kannada_digits", False)

    def misfit(text):
        """Section 7.1 and 5.6: digits in the other script than the font draws, and zeros after a letter."""
        kn = any("\u0ce6" <= c <= "\u0cef" for c in text)
        ascii_digits = any(c.isascii() and c.isdigit() for c in text)
        return int(ascii_digits if want_kn_digits else kn) + sum(1 for a, b in zip(text, as_anusvara(text)) if a != b)

    # Texts that differ only in a zero after a letter look alike and count as 1 candidate.
    groups = {}
    for name, text in sorted(outs.items()):
        groups.setdefault(as_anusvara(key(text)), []).append(text)
    scored = []
    for texts in groups.values():
        text = min(texts, key=misfit)
        total, direct, detail = evidence(text, ocr["crop"], ocr["renders"].get(text), bilingual)
        read = any(v == 0 for v in direct.values())
        scored.append({"total": total, "order": (total, not read, sum(direct.values()), misfit(text)),
                       "text": text, "texts": texts, "detail": detail})
    scored.sort(key=lambda s: s["order"])
    best, rivals = scored[0], scored[1:]
    if all(r["total"] > best["total"] for r in rivals):
        tier = "A" if best["total"] == 0 else "B" if best["total"] == 1 else "C"
    else:
        # A tie on unexplained differences: an exact reading, closeness to the readings, then the
        # font's digits break it, and never into confirmed.
        tied = [r for r in rivals if r["total"] == best["total"]]
        tier = "B" if best["total"] == 0 and all(r["order"] > best["order"] for r in tied) else "C"
    if len({as_anusvara(canonical(t)) for t in best["texts"]}) > 1:
        # The outputs differ only in a joiner the profile keeps, which changes the drawing but not the OCR key.
        tier = "C"
    agree = sorted(n for n, v in outs.items() if v in best["texts"])
    return {"tier": tier, "expected": canonical(best["text"]), "agree": agree, "variants": len(scored),
            "unexplained": {s["text"]: s["total"] for s in scored}, "best_detail": best["detail"],
            "ocr": ocr["crop"]}


def main():
    lines = {json.loads(l)["line_id"]: json.loads(l) for l in open(sys.argv[1])}
    cands = {json.loads(l)["line_id"]: json.loads(l) for l in open(sys.argv[2])}
    with open(sys.argv[4], "w") as f:
        for l in open(sys.argv[3]):
            o = json.loads(l)
            if o["line_id"] not in lines or o["line_id"] not in cands:
                continue
            d = decide(lines[o["line_id"]], cands[o["line_id"]], o)
            d["line_id"] = o["line_id"]
            f.write(json.dumps(d, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
