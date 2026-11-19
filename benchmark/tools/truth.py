"""Chooses each line's expected text from the converters' outputs by what OCR reads on the page.

Usage: truth.py LINES.jsonl CANDIDATES.jsonl OCR.jsonl OUT.jsonl

Texts are compared in canonical form (normalization profile) without white space or joiners.
For each candidate and OCR engine, the reading of the line image is aligned to the candidate.
An edit is explained when the same engine makes the same edit reading that candidate rendered
in a Unicode font: it is then an OCR habit, not a difference on the page. Not counted at all:
swaps between digits or punctuation, punctuation read as at most 2 other characters, and Latin
words of 2 letters or more, which the Kannada models do not read. A Latin letter written against
a Kannada letter, or a symbol outside ASCII in a Kannada word, always counts, once per engine. A candidate's evidence against it is its count
of unexplained edits over both engines.

Tiers (export.py names them):
  A  confirmed: an engine reads exactly 1 candidate, with no edit that counts; or the best
     candidate has no unexplained edit, and every other candidate has some
  B  likely: the best candidate has exactly 1 unexplained edit and every other candidate more; or
     it ties with no unexplained edit but is closer to the OCR reading, or the tied texts differ
     only in digit script and the font decides it (section 7.1)
  C  unresolved: anything else, or the agreeing outputs differ in a joiner the profile keeps;
     the expected text is a guess, for a Kannada reader
Zero against ಂ is not compared, since the 2 look alike; ties go to ಂ after a letter (section 5.6).
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


def ignorable(a, b):
    """Edits OCR makes on its own: digit script, punctuation, Latin words, and zero against ಂ."""
    if a and b and set(a + b) <= ZEROS | {ANUSVARA}:
        return True
    if a.isascii() and sum(c.isalpha() for c in a) >= 2:
        return True
    if all(is_digit(c) or is_punct(c) for c in a) and all(is_digit(c) or is_punct(c) for c in b):
        return True
    return bool(a) and all(is_punct(c) for c in a) and len(b) <= 2


def edits(cand, read):
    out = set()
    sm = difflib.SequenceMatcher(None, cand, read, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal" and not ignorable(cand[i1:i2], read[j1:j2]):
            out.add((op, i1, i2, read[j1:j2]))
    return out


TYPOGRAPHIC = set("\u2018\u2019\u201c\u201d\u2013\u2014\u2022\u2026\u00a0")


def stray(text):
    """Latin letters, and symbols outside ASCII, written against a Kannada letter: glyphs a
    converter left unconverted, such as ç or £ in a Nudi word."""
    n = 0
    for i, c in enumerate(text):
        odd = (c.isascii() and c.isalpha()) or (not c.isascii() and not "\u0c80" <= c <= "\u0cff" and c not in TYPOGRAPHIC)
        if odd:
            near = text[max(0, i - 1): i] + text[i + 1: i + 2]
            n += any(is_kannada_letter(x) for x in near)
    return n


def evidence(cand_text, crop, renders):
    c = key(cand_text)
    odd = stray(c)
    total, direct, detail = 0, {}, {}
    for e in ENGINES:
        if e not in crop:
            continue
        seen = edits(c, key(crop[e]))
        direct[e] = len(seen) + odd
        explained = set()
        for face in (renders or {}).values():
            if face and e in face:
                explained |= edits(c, key(face[e]))
        left = seen - explained
        # OCR skips a stray glyph on the page and on the rendering alike, so it is counted here.
        detail[e] = len(left) + odd
        total += len(left) + odd
    return total, direct, detail


def decide(line, cand, ocr):
    outs = {k: v for k, v in cand["outputs"].items() if v}
    if not outs:
        return {"tier": "C", "reason": "no converter output"}
    variants = {}
    for name, text in sorted(outs.items()):
        variants.setdefault(key(text), text)
    scored = []
    for k, text in variants.items():
        total, direct, detail = evidence(text, ocr["crop"], ocr["renders"].get(text))
        scored.append({"total": total, "direct": direct, "key": k, "text": text, "detail": detail})
    want_kn_digits = line.get("kannada_digits", False)

    def fit(text):
        """Section 7.1 and 5.6: the digit script the font draws, and ಂ, not a zero, after a letter."""
        kn = any("\u0ce6" <= c <= "\u0cef" for c in text)
        ascii_digits = any(c.isascii() and c.isdigit() for c in text)
        zeros = sum(1 for i, c in enumerate(text) if c in ZEROS and i and is_kannada_letter(text[i - 1]))
        return int(ascii_digits if want_kn_digits else kn) + zeros

    read_exactly = [s for s in scored if any(v == 0 for v in s["direct"].values())]
    for s in scored:
        s["rank"] = (s["total"], sum(s["direct"].values()) + 0.5 * fit(s["text"]))
    scored.sort(key=lambda s: s["rank"])
    as_anusvara = {"".join(ANUSVARA if c in ZEROS and i and is_kannada_letter(t[i - 1]) else c for i, c in enumerate(t))
                   for t in (s["key"] for s in read_exactly)}
    if read_exactly and len(as_anusvara) == 1:
        # Read exactly, alone or with texts that differ only in a zero after a letter (section 5.6).
        best, tier = min(read_exactly, key=lambda s: (fit(s["text"]), s["rank"])), "A"
    else:
        best = scored[0]
        unique = len(scored) == 1 or scored[1]["total"] > best["total"]
        closer = not unique and scored[1]["total"] == best["total"] and scored[1]["rank"][1] > best["rank"][1]
        if unique:
            tier = "A" if best["total"] == 0 else "B" if best["total"] == 1 else "C"
        else:
            tier = "B" if closer and best["total"] == 0 else "C"
    agree = sorted(n for n, v in outs.items() if key(v) == best["key"])
    forms = sorted({canonical(outs[n]) for n in agree})
    if len(forms) > 1:
        # The outputs differ only in a joiner the profile keeps, which changes the drawing but not the OCR key.
        tier = "C"
    clean = [outs[n] for n in agree if outs[n] == canonical(outs[n])]
    expected = clean[0] if clean else canonical(best["text"])
    return {"tier": tier, "expected": expected, "agree": agree, "variants": len(variants),
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
