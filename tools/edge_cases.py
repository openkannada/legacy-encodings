#!/usr/bin/env python3
"""Builds conformance/edge-cases.tsv: inputs that reach every reading rule.

  edge_cases.py -- COMMAND ...

Each rule of the reference reader is broken in turn, and random inputs are read
with the broken reader until 2 are found whose result changes. COMMAND, a
converter behind the conformance protocol, gives the expected result for each.
"""

import json
import random
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))

import kle  # noqa: E402

SEED = 7
TRIES = 20000
PER_RULE = 2

# (section of the specification, the rule, the code that implements it, how to break it)
RULES = [
    ("5.2", "longest entry", "                best = (e, n)", "                best = best or (e, n)"),
    ("5.2", "white space starts no match outside a syllable", "if match and is_white_space(code_char(codes[i])) and syllable is None:", "if False:"),
    ("5.3", "a second virama is rejected", "            if self.virama:\n                return False", "            if False:\n                return False"),
    ("5.3", "a second arkavattu is rejected", "            if self.arka:\n                return False", "            if False:\n                return False"),
    ("5.3", "a mahaprana stroke on another letter is rejected", "            if first not in ASPIRATES:\n                return False", "            if first not in ASPIRATES:\n                return True"),
    ("5.3", "a subscript that carries a vowel sign signs the syllable", "            if sign:\n                self.signed = True", "            if sign:\n                self.signed = False"),
    ("5.3", "ignore entries write nothing", '        elif kind == "ignore":', "        elif False:"),
    ("5.3", "a literal closes the syllable", '        elif kind == "literal":\n            close()\n', '        elif kind == "literal":\n'),
    ("5.3", "rejected codes are kept", "                syllable.rejected += glyphs", "                pass"),
    ("5.4", "a stray sign is written", '            if kind in ("sign", "mod") and value:', '            if kind == "mod" and value:'),
    ("5.4", "a stray subscript is written with viramas", '            elif kind == "ottu":', "            elif False:"),
    ("5.5", "the cluster takes consonants joined by the virama", "        while end + 1 < len(letter) and", "        while False and end + 1 < len(letter) and"),
    ("5.5", "a final ra stays after the subscripts", "        if end >= 3 and letter[end - 2] == VIRAMA and letter[end - 1] == RA:", "        if False:"),
    ("5.5", "the arkavattu is written first", '        s = (RA + VIRAMA if self.arka else "") + letter[:end]', '        s = letter[:end] + (RA + VIRAMA if self.arka else "")'),
    ("5.5", "the syllable is normalized to NFC", '        s = unicodedata.normalize("NFC", s)', "        pass"),
    ("5.5", "a shape that needs a sign is malformed without one", "        valid = not (self.needs_sign and not self.signed)", "        valid = True"),
    ("5.5", "2 vowel signs are malformed", "        valid = valid and vowel_signs <= 1", "        valid = valid"),
    ("5.5", "marks on a vowel letter are malformed", "        valid = valid and not (on_vowel and (self.arka or self.signed or self.ottus))", "        valid = valid"),
    ("5.5", "the malformed range includes the rejected codes", "        out.append(s + syllable.rejected)\n        if not valid:\n            malformed.append((start, length()))", "        out.append(s)\n        if not valid:\n            malformed.append((start, length()))\n        out.append(syllable.rejected)"),
    ("5.6", "zero as anusvara", '                if zero_as_anusvara and c == "0" and starts', '                if False and c == "0" and starts'),
    ("5.6", "zero as anusvara needs a letter or base next", '                if zero_as_anusvara and c == "0" and starts and', '                if zero_as_anusvara and c == "0" and'),
    ("5.6", "zero as anusvara needs a letter character before", "prev is not None and is_letter_char(prev)", "True"),
    ("5.6", "Kannada digits", "                    out.append(chr(0x0CE6 + int(c)))", "                    out.append(c)"),
    ("5.6", "passing characters are not reported", "                if not is_passing(c):", "                if True:"),
    ("3.3", "only syllables are normalized", '    return Result("".join(out), unknown, malformed)', '    return Result(unicodedata.normalize("NFC", "".join(out)), unknown, malformed)'),
    ("5.2", "every white-space code starts no match outside a syllable", "if match and is_white_space(code_char(codes[i])) and syllable is None:", "if match and codes[i] == 0x20 and syllable is None:"),
    ("5.5", "modifiers come after the virama", '        s += letter[end:] + self.signs + (VIRAMA if self.virama else "") + self.mods', '        s += letter[end:] + self.signs + self.mods + (VIRAMA if self.virama else "")'),
    ("5.6", "the zero lookahead skips the white-space refusal", "            nxt = table.longest_entry(codes, i + 1)", "            nxt = None if i + 1 < len(codes) and is_white_space(code_char(codes[i + 1])) else table.longest_entry(codes, i + 1)"),
    ("5.6", "a vowel sign counts as a letter character", '    return char_class(c) in ("vowel", "consonant", "vowel-sign")', '    return char_class(c) in ("vowel", "consonant")'),
    ("7.2", "malformed syllables count against a layout", "        return (len(r.unknown) + len(r.malformed), latin, r.text.count(VIRAMA))", "        return (len(r.unknown), latin, r.text.count(VIRAMA))"),
    ("7.2", "fewer Latin letters wins a tie", "        latin = sum(c.isascii() and c.isalpha() for c in r.text)", "        latin = 0"),
    ("7.2", "fewer viramas wins a tie", "        return (len(r.unknown) + len(r.malformed), latin, r.text.count(VIRAMA))", "        return (len(r.unknown) + len(r.malformed), latin, 0)"),
]

SOURCE = (ROOT / "reference" / "kle.py").read_text(encoding="utf-8")


def mutant(old, new):
    if SOURCE.count(old) != 1:
        raise SystemExit(f"rule code not found exactly once: {old!r}")
    module = types.ModuleType("kle_mutant")
    module.__dict__["__file__"] = str(ROOT / "reference" / "kle.py")
    exec(compile(SOURCE.replace(old, new), "kle_mutant", "exec"), module.__dict__)
    return module


def random_inputs(tables):
    rng = random.Random(SEED)
    keys = {lid: [list(k) for k in t.entries] for lid, t in tables.items()}
    for _ in range(TRIES):
        layout = rng.choice(kle.ORDER)
        codes, last = [], []
        for _ in range(rng.randint(1, 10)):
            pick = rng.random()
            if pick < 0.1 and last:
                codes += last
            elif pick < 0.7:
                last = rng.choice(keys[layout])
                codes += last
            elif pick < 0.82:
                codes.append(rng.randint(0, 255))
            elif pick < 0.9:
                codes.append(rng.choice([0x20, 0x20, 0x20, 0x09, 0x0A, 0xA0]))
            else:
                codes.append(rng.choice([0x30, 0x31, 0x39]))
        options = {"zero_as_anusvara": rng.random() > 0.1, "kannada_digits": rng.random() < 0.1}
        yield layout, codes, options


def outcome(module, tables, layout, codes, options, detect):
    """The result of reading with `module`, whose own Table class reads `tables`."""
    if detect:
        return module.detect(codes, tables)
    r = module.read(codes, tables[layout], **options)
    return (r.text, r.unknown, r.malformed)


def query(command, reqs):
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    out = []
    for req in reqs:
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise SystemExit(f"the converter stopped at {req['id']}")
        out.append(json.loads(line))
    proc.stdin.close()
    proc.wait()
    return out


def main(argv):
    if argv[:1] != ["--"] or len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    tables = kle.load_tables()
    inputs = list(random_inputs(tables))
    picked = []
    for section, rule, old, new in RULES:
        broken = mutant(old, new)
        broken_tables = broken.load_tables()
        detect = section == "7.2"
        found = 0
        for layout, codes, options in inputs:
            if detect and len(codes) > 6:
                continue
            if outcome(kle, tables, layout, codes, options, detect) != outcome(broken, broken_tables, layout, codes, options, detect):
                picked.append((section, rule, layout, codes, options, detect))
                found += 1
                if found == PER_RULE:
                    break
        if found < PER_RULE:
            raise SystemExit(f"no input reaches rule {rule!r}")
    reqs = []
    for n, (section, rule, layout, codes, options, detect) in enumerate(picked):
        hexes = " ".join(f"{c:02X}" for c in codes)
        if detect:
            reqs.append({"id": f"edge-{n:03}", "op": "detect", "codes": hexes})
        else:
            reqs.append({"id": f"edge-{n:03}", "op": "read", "layout": layout, "codes": hexes, "options": options})
    answers = query(argv[1:], reqs)
    lines = [
        "# Edge cases: inputs that reach every reading rule of sections 5 and 7.2, chosen by",
        "# tools/edge_cases.py, with the expected result from kannadi.",
        "# Columns: id, op, layout, options, codes, expected (JSON), section, rule.",
    ]
    for (section, rule, layout, codes, options, detect), req, ans in zip(picked, reqs, answers):
        expected = {k: v for k, v in ans.items() if k != "id"}
        opts = "" if detect else ",".join(k for k, v in sorted(options.items()) if v)
        lines.append("\t".join([
            req["id"], req["op"], "" if detect else layout, opts, req["codes"],
            json.dumps(expected, ensure_ascii=False, sort_keys=True), section, rule,
        ]))
    (ROOT / "conformance" / "edge-cases.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(picked)} edge cases for {len(RULES)} rules")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
