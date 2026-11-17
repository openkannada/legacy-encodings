#!/usr/bin/env python3
"""Runs the conformance cases against a converter and reports its accuracy.

  run.py [--out FILE] [--markdown] -- COMMAND [ARGS...]

COMMAND speaks the line protocol in conformance/README.md on stdin and stdout.
--out saves every response, so 2 converters can be compared with --compare.
The exit code is 0 when the converter conforms (section 8 of the specification), else 1.

  run.py --compare A.json B.json
"""

import json
import selectors
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LAYOUTS = ["nudi", "akruti", "shree-lipi", "nudi-b", "kan-eng"]
SNIPPETS = [8, 16, 32]
CHECKED = ("verified", "read")
KEYS = {"read": ("text", "unknown", "malformed"), "detect": ("layout",), "font": ("layout", "legacy", "kannada_digits")}


def load_cases():
    cases = []
    for layout in LAYOUTS:
        text = (HERE / "cases" / f"{layout}.tsv").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip() and not line.startswith("#"):
                cid, status, codes, expected, source = line.split("\t")
                cases.append({"id": cid, "layout": layout, "status": status, "codes": codes, "expected": expected, "source": source})
    return cases


def load_edge_cases():
    edges = []
    for line in (HERE / "edge-cases.tsv").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            eid, op, layout, opts, codes, expected, section, rule = line.split("\t")
            req = {"id": eid, "op": op, "codes": codes}
            if op == "read":
                req["layout"] = layout
                req["options"] = {
                    "zero_as_anusvara": "zero_as_anusvara" in opts.split(","),
                    "kannada_digits": "kannada_digits" in opts.split(","),
                }
            edges.append({"request": req, "expected": json.loads(expected), "section": section, "rule": rule})
    return edges


def requests(cases, fonts, edges):
    for e in edges:
        yield e["request"]
    for c in cases:
        yield {"id": c["id"], "op": "read", "layout": c["layout"], "codes": c["codes"]}
        yield {"id": c["id"], "op": "detect", "codes": c["codes"]}
        codes = c["codes"].split()
        for n in SNIPPETS:
            if len(codes) > n:
                yield {"id": f"{c['id']}@{n}", "op": "detect", "codes": " ".join(codes[:n])}
    for n, ex in enumerate(fonts["examples"]):
        yield {"id": f"font-{n}", "op": "font", "name": ex["font"]}


def run(command, reqs, timeout=30):
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    ready = selectors.DefaultSelector()
    ready.register(proc.stdout, selectors.EVENT_READ)
    responses = {}
    for req in reqs:
        proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        proc.stdin.flush()
        if not ready.select(timeout):
            proc.kill()
            raise SystemExit(f"no response to {req['id']} within {timeout} seconds")
        line = proc.stdout.readline()
        if not line:
            raise SystemExit(f"the converter stopped at {req['id']} (exit code {proc.wait()})")
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            raise SystemExit(f"the response to {req['id']} is not JSON: {line[:200]!r}")
        if not isinstance(resp, dict) or resp.get("id") != req["id"]:
            raise SystemExit(f"expected a response to {req['id']}, got {line[:200]!r}")
        responses[(req["op"], req["id"])] = resp
    proc.stdin.close()
    proc.wait()
    return responses


def answer(responses, op, rid):
    """The fields the protocol defines for `op`; a missing field, as in an error response, is None."""
    resp = responses[(op, rid)]
    return {k: resp.get(k) for k in KEYS[op]}


def distance(a, b):
    """Levenshtein distance in code points."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def edge_failures(edges, responses):
    failed = []
    for e in edges:
        req = e["request"]
        if answer(responses, req["op"], req["id"]) != e["expected"]:
            failed.append(f"{req['id']} (section {e['section']}, {e['rule']})")
    return failed


def summarize(cases, responses, fonts):
    rows = []
    for layout in LAYOUTS:
        for group, statuses in (("checked", CHECKED), ("all", None)):
            sel = [c for c in cases if c["layout"] == layout and (statuses is None or c["status"] in statuses)]
            if not sel:
                continue
            exact = errors = chars = clean = detected = 0
            snip = {n: [0, 0] for n in SNIPPETS}
            for c in sel:
                r = answer(responses, "read", c["id"])
                text = r["text"] if isinstance(r["text"], str) else ""
                exact += r["text"] == c["expected"]
                errors += distance(text, c["expected"])
                chars += len(c["expected"])
                clean += r["unknown"] == [] and r["malformed"] == []
                detected += answer(responses, "detect", c["id"])["layout"] == layout
                for n in SNIPPETS:
                    if ("detect", f"{c['id']}@{n}") in responses:
                        snip[n][0] += answer(responses, "detect", f"{c['id']}@{n}")["layout"] == layout
                        snip[n][1] += 1
            rows.append({
                "layout": layout,
                "group": group,
                "lines": len(sel),
                "exact": exact,
                "char_accuracy": max(0.0, 1 - errors / chars),
                "clean": clean,
                "detected": detected,
                "snippets": {n: tuple(v) for n, v in snip.items()},
            })
    fonts_right = sum(
        answer(responses, "font", f"font-{n}") == {k: ex[k] for k in KEYS["font"]}
        for n, ex in enumerate(fonts["examples"])
    )
    return rows, (fonts_right, len(fonts["examples"]))


def conforming(rows, fonts_score, edges, failed):
    """Section 8: every edge case, every checked line, every font example and every whole line's layout."""
    checked = [r for r in rows if r["group"] == "checked"]
    return (
        not failed
        and all(r["exact"] == r["lines"] and r["detected"] == r["lines"] for r in checked)
        and fonts_score[0] == fonts_score[1]
    )


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def snippet(score):
    return f"{pct(*score)} of {score[1]}"


def markdown(rows, fonts_score, edges, failed):
    lines = [
        "| Layout | Lines | Exact | Character accuracy | Clean | Layout found, whole line | First 8 codes | First 16 codes | First 32 codes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    checked = {r["layout"]: r["lines"] for r in rows if r["group"] == "checked"}
    for r in rows:
        if r["group"] == "all" and checked.get(r["layout"]) == r["lines"]:
            continue
        name = r["layout"] + (", all statuses" if r["group"] == "all" else "")
        s = r["snippets"]
        lines.append(
            f"| {name} | {r['lines']} | {r['exact']} ({pct(r['exact'], r['lines'])}) | {100 * r['char_accuracy']:.2f}% "
            f"| {r['clean']} | {pct(r['detected'], r['lines'])} | {snippet(s[8])} | {snippet(s[16])} | {snippet(s[32])} |"
        )
    lines.append("")
    lines.append(f"Font names: {fonts_score[0]} of {fonts_score[1]} examples right.")
    lines.append(f"Edge cases: {len(edges) - len(failed)} of {len(edges)} exact.")
    lines.extend(f"- failed: {f}" for f in failed)
    lines.append(f"Conforming (section 8): {'yes' if conforming(rows, fonts_score, edges, failed) else 'no'}.")
    return "\n".join(lines)


def compare(a_path, b_path):
    a = json.loads(Path(a_path).read_text(encoding="utf-8"))
    b = json.loads(Path(b_path).read_text(encoding="utf-8"))
    diffs = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    for k in diffs[:20]:
        print(f"{k}\n  A: {a.get(k)}\n  B: {b.get(k)}")
    print(f"{len(diffs)} of {len(set(a) | set(b))} responses differ")
    return 1 if diffs else 0


def main(argv):
    if argv[:1] == ["--compare"] and len(argv) == 3:
        return compare(argv[1], argv[2])
    if "--" not in argv:
        print(__doc__, file=sys.stderr)
        return 2
    split = argv.index("--")
    opts, command = argv[:split], argv[split + 1 :]
    out = opts[opts.index("--out") + 1] if "--out" in opts else None
    fonts = json.loads((ROOT / "tables" / "fonts.json").read_text(encoding="utf-8"))
    cases = load_cases()
    edges = load_edge_cases()
    responses = run(command, requests(cases, fonts, edges))
    if out:
        saved = {f"{op} {rid}": {k: v for k, v in r.items() if k != "id"} for (op, rid), r in responses.items()}
        Path(out).write_text(json.dumps(saved, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    rows, fonts_score = summarize(cases, responses, fonts)
    failed = edge_failures(edges, responses)
    if "--markdown" in opts:
        print(markdown(rows, fonts_score, edges, failed))
    else:
        print(json.dumps({"rows": rows, "fonts": fonts_score, "edge_cases": [len(edges) - len(failed), len(edges)], "conforming": conforming(rows, fonts_score, edges, failed)}, indent=1))
    return 0 if conforming(rows, fonts_score, edges, failed) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
