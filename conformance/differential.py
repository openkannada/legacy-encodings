#!/usr/bin/env python3
"""Compares 2 converters on random code sequences, to reach rules the cases rarely use.

  differential.py [--count N] [--seed S] -- COMMAND_A ... -- COMMAND_B ...

Sequences are built from each layout's own entries, random codes, spaces and digits,
so stray marks, rejected codes and plain codes all occur. Every response must match.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUTS = ["nudi", "akruti", "shree-lipi", "nudi-b", "kan-eng"]


def sequences(count, seed):
    rng = random.Random(seed)
    for layout in LAYOUTS:
        doc = json.loads((ROOT / "tables" / "json" / f"{layout}.json").read_text(encoding="utf-8"))
        keys = [e["codes"] for e in doc["entries"]]
        for n in range(count):
            codes = []
            for _ in range(rng.randint(1, 12)):
                pick = rng.random()
                if pick < 0.7:
                    codes += rng.choice(keys)
                elif pick < 0.85:
                    codes.append(f"{rng.randint(0, 255):02X}")
                elif pick < 0.93:
                    codes.append(rng.choice(["20", "20", "20", "09", "0A", "A0"]))
                else:
                    codes.append(rng.choice(["30", "31", "39"]))
            options = {"zero_as_anusvara": rng.random() > 0.1, "kannada_digits": rng.random() < 0.1}
            yield {"id": f"{layout}-{n}", "op": "read", "layout": layout, "codes": " ".join(codes), "options": options}
            if n % 10 == 0:
                yield {"id": f"{layout}-{n}", "op": "detect", "codes": " ".join(codes)}


def run(command, reqs):
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    out = []
    for req in reqs:
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise SystemExit(f"{command[0]} stopped at {req['id']}")
        out.append(json.loads(line))
    proc.stdin.close()
    proc.wait()
    return out


def main(argv):
    count, seed = 2000, 1
    if "--count" in argv:
        count = int(argv[argv.index("--count") + 1])
    if "--seed" in argv:
        seed = int(argv[argv.index("--seed") + 1])
    first = argv.index("--")
    second = argv.index("--", first + 1)
    reqs = list(sequences(count, seed))
    a = run(argv[first + 1 : second], reqs)
    b = run(argv[second + 1 :], reqs)
    diffs = [(r, x, y) for r, x, y in zip(reqs, a, b) if x != y]
    for r, x, y in diffs[:10]:
        print(f"{r['op']} {r.get('layout', '')} {r['codes']}\n  A: {x}\n  B: {y}")
    print(f"{len(diffs)} of {len(reqs)} responses differ")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
