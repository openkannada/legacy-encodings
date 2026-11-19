"""Runs each converter over the selected lines through the conformance protocol.

The outputs are candidates for truth.py. They name third-party converters, so keep them
out of the repository.

Usage: candidates.py LINES.jsonl OUT.jsonl
Writes 1 row per line: line_id, outputs {converter: text or null}.
"""
import json
import os
import subprocess
import sys

from paths import ROOT

# Each converter's command, from the environment, and the layouts it reads (None: all).
# KANNADI_ADAPTER: adapters/kannadi built at the kannadi commit under test.
# KAGAPA_ADAPTER: e.g. "dotnet /path/KagapaAdapter.dll" (adapters/kagapa/README.md).
# SANKA_JS and SANCHAYA_JS: the files adapters/sanka and adapters/sanchaya load.
CONVERTERS = {
    "kannadi": (lambda: os.environ["KANNADI_ADAPTER"].split(), None),
    "kagapa": (lambda: os.environ["KAGAPA_ADAPTER"].split(), {"nudi"}),
    "sanka": (lambda: ["node", str(ROOT / "adapters/sanka/adapter.mjs")], {"nudi"}),
    "sanchaya": (lambda: ["node", str(ROOT / "adapters/sanchaya/adapter.mjs")], {"nudi", "akruti", "shree-lipi", "kan-eng"}),
}
NEEDS = {"kannadi": "KANNADI_ADAPTER", "kagapa": "KAGAPA_ADAPTER", "sanka": "SANKA_JS", "sanchaya": "SANCHAYA_JS"}


def run(command, reqs):
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reqs)
    p = subprocess.run(command, input=data, capture_output=True, text=True, timeout=3600)
    out = {}
    for line in p.stdout.splitlines():
        try:
            j = json.loads(line)
        except ValueError:
            continue
        out[j.get("id")] = j
    return out


def main():
    lines = [json.loads(l) for l in open(sys.argv[1])]
    results = {l["line_id"]: {} for l in lines}
    for name, (command, layouts) in CONVERTERS.items():
        if not os.environ.get(NEEDS[name]):
            print(name, "skipped:", NEEDS[name], "is not set", file=sys.stderr)
            continue
        reqs = [{"id": l["line_id"], "op": "read", "layout": l["layout"], "codes": l["codes"],
                 "options": {"zero_as_anusvara": True, "kannada_digits": l["kannada_digits"]}}
                for l in lines if layouts is None or l["layout"] in layouts]
        resp = run(command(), reqs)
        for r in reqs:
            j = resp.get(r["id"], {})
            results[r["id"]][name] = j.get("text") if "error" not in j else None
        print(name, len(reqs), sum(1 for r in reqs if resp.get(r["id"], {}).get("text") is not None), file=sys.stderr)
    with open(sys.argv[2], "w") as f:
        for lid, outs in results.items():
            f.write(json.dumps({"line_id": lid, "outputs": outs}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
