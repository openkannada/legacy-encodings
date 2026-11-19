"""The canonical form of the Kannada text normalization profile, rules C1 to C8.

The profile is NORMALIZATION.md in kannadi (https://github.com/openkannada/kannadi), whose
test vectors are copied in conformance/normalization-vectors.json. The conformance runner
compares converter output with the expected text in this form as well as exactly, so
spellings that render the same are not counted as errors.
"""

import unicodedata

VIRAMA = "್"
NUKTA = "಼"
ZWNJ = "‌"
ZWJ = "‍"
RA = "ರ"
JOINERS = (ZWNJ, ZWJ)
VOWEL_PARTS = {("ಉ", "ಾ"): "ಊ", ("ಒ", "ೌ"): "ಔ", ("ಋ", "ಾ"): "ೠ"}


def is_kannada(c):
    return "ಀ" <= c <= "೿"


def is_consonant(c):
    return ("ಕ" <= c <= "ಹ" and c not in "಩಴") or c == "ೞ"


def is_vowel_sign(c):
    return ("ಾ" <= c <= "ೌ" and c not in "೅೉") or c in "ೕೖೢೣ"


def is_mark(c):
    return (
        is_vowel_sign(c)
        or c in (VIRAMA, NUKTA)
        or "ಀ" <= c <= "ಃ"
        or "ೱ" <= c <= "ೳ"
    )


def ends_with_consonant(out):
    if out and out[-1] == NUKTA:
        return len(out) > 1 and is_consonant(out[-2])
    return bool(out) and is_consonant(out[-1])


def starts_syllable(out, i):
    return i == 0 or out[i - 1] != VIRAMA


def joiners(out, run, nxt):
    prev = out[-1] if out else None
    if not (prev and is_kannada(prev)) and not (nxt and is_kannada(nxt)):
        out.extend(run)
        return
    if nxt == VIRAMA and ends_with_consonant(out):
        if prev == RA and starts_syllable(out, len(out) - 1):
            out.append(ZWJ)
        return
    if prev == VIRAMA:
        if not (nxt and is_consonant(nxt)):
            return
        n = len(out)
        ra = n >= 2 and out[n - 2] == RA and starts_syllable(out, n - 2)
        if ra and all(j == ZWJ for j in run):
            out.insert(n - 1, ZWJ)
        else:
            out.append(ZWNJ)
        return
    if ends_with_consonant(out) and nxt and is_mark(nxt):
        out.extend(run)


def place_nukta(out):
    at = len(out)
    while at > 0 and is_vowel_sign(out[at - 1]):
        at -= 1
    if at < len(out) and ends_with_consonant(out[:at]):
        if out[at - 1] != NUKTA:
            out.insert(at, NUKTA)
        return
    out.append(NUKTA)


def one_pass(chars):
    out = []
    i = 0
    while i < len(chars):
        c = chars[i]
        if c in JOINERS:
            start = i
            while i < len(chars) and chars[i] in JOINERS:
                i += 1
            joiners(out, chars[start:i], chars[i] if i < len(chars) else None)
            continue
        i += 1
        prev = out[-1] if out else None
        if (prev, c) in VOWEL_PARTS:
            out[-1] = VOWEL_PARTS[(prev, c)]
        elif prev == c and is_mark(c):
            pass
        elif c == NUKTA:
            place_nukta(out)
        else:
            out.append(c)
    return out


def canonical(text):
    """The canonical form of text (rules C1 to C8)."""
    chars = list(text)
    for _ in range(8):
        out = one_pass(list(unicodedata.normalize("NFC", "".join(chars))))
        if out == chars:
            break
        chars = out
    return "".join(chars)
