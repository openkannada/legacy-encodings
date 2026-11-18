# Conformance tests

These tests show how closely a converter follows the specification, as accuracy figures any converter can report.

## What is tested

| Set | File | What it checks |
|---|---|---|
| Lines | `cases/<layout>.tsv` | 782 lines, 642 from public documents and 140 written for the tests: the converter's text against the expected text |
| Edge cases | `edge-cases.tsv` | 64 short inputs that reach the 32 rules listed in `tools/edge_cases.py`, from sections 3.3, 5 and 7.2, including the error reports |
| Font names | `../tables/fonts.json` | 47 font names: layout, legacy flag and Kannada digit flag (section 7.1) |
| Detection | the lines | the layout found from each whole line, and from its first 8, 16 and 32 codes (section 7.2) |

### Lines

| Layout | Lines | Status | Documents | Sources |
|---|---|---|---|---|
| nudi | 12 read, 95 pending, 102 unchecked | see below | 31 | Karnataka government web pages of 2002 (Rural Development and Panchayat Raj; Finance) |
| akruti | 125 read | | 5 | Karnataka Acts and the 2002 budget highlights (PDF) |
| shree-lipi | 140 written | | | Written for kannadi and encoded with its Shree-Lipi table, with 22 words retyped in the typing habits of the Udayavani newspaper pages of 2003 and 2004 |
| nudi-b | 190 read | | 15 | 13th Karnataka Legislative Assembly member pages and budget papers (PDF) |
| kan-eng | 118 read | | 36 | Karnataka budget papers, 2002 to 2011 (PDF) |

Every line records the archived URL of its source. Each file has 5 tab-separated columns: id, status, codes (hexadecimal Windows-1252 codes in drawing order), the expected Unicode, and the source.

Status says how far the expected text can be trusted:

- **verified**: a Kannada reader checked the expected text against the line drawn in its font. No line is verified yet.
- **read**: the expected text was read against the same codes rendered in the font, glyph by glyph, and matches the line as typed, including the source's own typing errors. A Kannada reader's check is pending.
- **written**: the line was written for the tests and its codes were made with the layout's table, so the expected text is the text that was written. Some words were then retyped by hand in typing habits seen in real documents; the source column names them.
- **pending**: in kannadi's 100-line verification set, waiting for a Kannada reader; the expected text is kannadi's output until then.
- **unchecked**: the expected text is kannadi's output and nobody has reviewed it.

The headline figures count verified, read and written lines only.

### Edge cases

`tools/edge_cases.py` breaks each of 32 rules of the reference reader in turn and keeps 2 random inputs whose result changes, so each of those rules is tested by at least 2 cases. The expected result of each, including the unknown positions and malformed ranges, comes from kannadi. A test checks that breaking any listed rule still fails at least 1 edge case. The cases also exercise the 2 reading options. A rule that is not in the list is not guaranteed a case; adding one means adding its mutation to the list.

## The protocol

A converter takes part through a small program that reads 1 JSON request per line on standard input and writes 1 JSON response per line on standard output, in the same order, each with the request's `id`.

| Request | Response |
|---|---|
| `{"id": "nudi-001", "op": "read", "layout": "nudi", "codes": "50 C0 A3 C0", "options": {"zero_as_anusvara": true, "kannada_digits": false}}` | `{"id": "nudi-001", "text": "ಕನ", "unknown": [], "malformed": []}` |
| `{"id": "nudi-001", "op": "detect", "codes": "50 C0 A3 C0"}` | `{"id": "nudi-001", "layout": "nudi"}` |
| `{"id": "font-0", "op": "font", "name": "Nudi 01 e"}` | `{"id": "font-0", "layout": "nudi", "legacy": true, "kannada_digits": false}` |

- `codes` are hexadecimal Windows-1252 codes separated by spaces.
- `options` may be missing; the defaults are those of section 5.7.
- `unknown` lists the positions of unknown codes, counting codes from 0. `malformed` lists `[start, end)` ranges of the output text, counting code points from 0.
- A converter that does not support an operation answers `{"id": ..., "error": "..."}`, and the runner counts it as wrong.
- The runner compares only the fields above; a response may carry others.
- Input is always given as glyph codes. The rules for text given as a string, such as characters with no Windows-1252 code and Unicode Kannada passing through (sections 3.2, 5.1 and 5.6), are not tested yet, and the reference reader reads glyph codes only.

2 programs speak the protocol here:

- `reference/adapter.py`, the reference reader in Python (`reference/kle.py`), written from the specification;
- `adapters/kannadi`, the kannadi library at the commit the tables come from.

## Running it

```bash
python3 conformance/run.py --markdown -- python3 reference/adapter.py
cargo build --release --manifest-path adapters/kannadi/Cargo.toml
python3 conformance/run.py --markdown -- adapters/kannadi/target/release/kle-kannadi-adapter
```

The exit code is 0 when the converter conforms (section 8 of the specification) and 1 otherwise. A converter that does not detect layouts or read font names is run with `--no-detect` or `--no-fonts`, which leave those operations out of the run and of the verdict. `--timeout SECONDS` (default 30) bounds the wait for each response. `--out FILE` saves every response; `run.py --compare A B` lists the responses that differ between 2 saved runs. `differential.py` compares 2 converters on random code sequences built from each layout's entries:

```bash
python3 conformance/differential.py --count 2000 --seed 1 -- python3 reference/adapter.py -- adapters/kannadi/target/release/kle-kannadi-adapter
```

## Figures reported

- **Exact**: lines whose text equals the expected text.
- **Character accuracy**: 1 minus the Levenshtein distance between output and expected text, summed over the lines, divided by the expected length, in code points.
- **Clean**: lines with no unknown codes and no malformed ranges.
- **Layout found**: lines whose detected layout is the right one, from the whole line and from its first 8, 16 and 32 codes. A snippet figure counts only the lines longer than the snippet, and says how many.
- **Edge cases** and **font names**: responses equal to the expected ones.
- **Conforming**: yes when all 4 conditions of section 8 hold. Cite the specification version and the kannadi commit in `cases/SOURCE.json` with the figures.

[RESULTS.md](RESULTS.md) has the figures for the 2 programs here.

## License and use

The Nudi, Akruti, Nudi B-Akshara and Kan-Eng lines are short excerpts of works of the Government of Karnataka. Source credit: Government of Karnataka; each line records the archived URL of its source. They carry no license statement, and neither license of this repository covers them. They are kept, with their sources, for research on and testing of converters, as fair dealing under the Indian Copyright Act, 1957. No page is stored in full.

To ask for an excerpt to be removed, write to support@luminik.io or open an issue.

The Shree-Lipi lines were written for kannadi and are under MIT OR Apache-2.0, like the runner, the edge cases and the other files here. No newspaper text is included.

## Updating

The cases come from kannadi's test fixtures and its Nudi benchmark corpus:

```bash
python3 tools/cases.py ../kannadi <commit>
python3 tools/edge_cases.py -- adapters/kannadi/target/release/kle-kannadi-adapter
```
