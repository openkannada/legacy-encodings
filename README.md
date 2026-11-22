# Kannada Legacy Encodings

An open specification for the legacy fonts Kannada documents were typed in, such as Nudi and Baraha, which draw Kannada shapes at the codes of Latin letters: copy the text out of such a PDF and you get `PÀ£ÁðlPÀ` instead of ಕರ್ನಾಟಕ, which search engines, screen readers and language models cannot read as Kannada.

It gives 1 glyph table per layout for 5 layouts, the exact steps that turn glyph codes back into Unicode, and tests that measure any converter on the same lines, including a benchmark of 5,098 lines from 275 Karnataka government PDFs. [kannadi](https://github.com/openkannada/kannadi), the converter the tables come from, reads 96.9% of the benchmark's 2,210 Nudi and Baraha lines exactly, counting lines whose expected text is still unresolved.

Draft 0.1.0. [PROPOSAL.md](PROPOSAL.md) explains why it exists and what is still to decide. To convert documents, use [kannadi](https://github.com/openkannada/kannadi) or [openkannada.org/nudi-to-unicode](https://openkannada.org/nudi-to-unicode/).

## Quick start

The reference reader needs only Python 3.12 or later. The last line runs the conformance suite against it; swap in your own converter's adapter.

```bash
git clone https://github.com/openkannada/legacy-encodings && cd legacy-encodings
python3 -c 'import sys; sys.path.insert(0, "reference"); import kle; t = kle.load_tables(); c = list("PÀ£ÁðlPÀ gÁdå¥ÀvÀæ".encode("cp1252")); l = kle.detect(c, t); print(l, kle.read(c, t[l]).text)'
echo '{"id": 1, "op": "read", "layout": "nudi", "codes": "50 C0 A3 C1 F0 6C 50 C0"}' | python3 reference/adapter.py
python3 conformance/run.py --markdown -- python3 reference/adapter.py
```

The second line prints `nudi ಕರ್ನಾಟಕ ರಾಜ್ಯಪತ್ರ`. A converter speaks the JSON-lines protocol in [conformance/README.md](conformance/README.md).

## Results

kannadi on the [benchmark](benchmark/README.md), text compared in the canonical form of the normalization profile ([benchmark/RESULTS.md](benchmark/RESULTS.md)):

| Layout | Lines | Documents | Exact, all lines | Exact, confirmed and likely lines |
|---|---:|---:|---:|---:|
| Nudi and Baraha | 2,210 | 223 | 96.9% | 99.9% of 1,924 |
| Akruti | 953 | 25 | 99.9% | 99.9% of 919 |
| Shree-Lipi | 421 | 8 | 100.0% | 100.0% of 356 |
| Nudi B-Akshara | 1,000 | 36 | 100.0% | 100.0% of 805 |
| Kan-Eng | 514 | 17 | 100.0% | 100.0% of 471 |
| **All** | **5,098** | **275** | | |

The expected text of each line is the converter output that OCR of the line, drawn with the PDF's own font, supports: 4,030 lines are confirmed, 445 likely and 623 unresolved. kannadi is a candidate on every line and the only one for Nudi B-Akshara, so its figures are an upper bound until Kannada readers check the 400-line sample ([Limitations](benchmark/README.md#limitations)).

On the conformance suite, the reference reader and kannadi give the same response to all 3,767 requests and to 82,500 random code sequences, and both conform to section 8 of the specification: 782 test lines (642 from public documents, 140 written for the tests), 64 edge cases and 47 font names ([conformance/RESULTS.md](conformance/RESULTS.md)).

## Contents

| Path | What it is |
|---|---|
| [spec/kle.md](spec/kle.md) | The specification: layout tables, reading rules, reports, layout detection |
| [tables/](tables/) | 1 table per layout, as TSV (`tables/<id>.tsv`) and generated JSON (`tables/json/<id>.json`) |
| [tables/fonts.json](tables/fonts.json) | Font-name rules for finding a layout, with examples |
| [schema/layout.schema.json](schema/layout.schema.json) | JSON Schema for the JSON tables |
| [tools/tables.py](tools/tables.py) | Copies the tables from kannadi, builds the JSON and checks every table rule |
| [conformance/](conformance/) | 782 test lines (642 from public documents, 140 written for the tests), 64 edge cases, the runner and its protocol, and [measured results](conformance/RESULTS.md) |
| [reference/kle.py](reference/kle.py) | A reference reader in Python, written from the specification |
| [benchmark/](benchmark/) | 5,098 lines from 275 Karnataka government PDFs, with expected texts chosen by OCR of each line as its own font draws it, a reader review page, a data card and [kannadi's results](benchmark/RESULTS.md) |
| [adapters/kannadi](adapters/kannadi) | kannadi behind the conformance protocol |

## Using the tables

Read `tables/json/<id>.json` and follow section 5 of the specification. Each file records the kannadi commit it was generated from.

## Changing a table

The tables are generated from [kannadi](https://github.com/openkannada/kannadi)'s data tables, so a change starts there, with its evidence. Then:

```bash
python3 tools/tables.py sync ../kannadi <commit>
python3 tools/tables.py check
python3 -m unittest discover -s tests
```

and list the change in [CHANGELOG.md](CHANGELOG.md).

## Proposing changes

Open a GitHub issue for a change to the specification, a table entry, a new layout or a new test line. A table change needs evidence: the font file or a rendering of its glyphs, and lines from public documents that use the codes, with their sources (section 10 of the specification). Bugs and sample documents go in issues too; send documents that cannot be public to support@luminik.io. Report security problems as [SECURITY.md](SECURITY.md) says.

Every commit needs a `Signed-off-by` line (`git commit -s`) under the [Developer Certificate of Origin](https://developercertificate.org/); see [CONTRIBUTING.md](CONTRIBUTING.md).

Organizations that want to take part in the specification, such as KAGAPA or a government office, can write to founders@luminik.io.

## Related

- [kannadi](https://github.com/openkannada/kannadi): the converter, library and CLI the tables come from.
- [kannada-test-corpus](https://github.com/openkannada/kannada-test-corpus): indexes the conformance cases and the benchmark lines.
- [kannada-ocr](https://github.com/openkannada/kannada-ocr): trained 1 of the 2 OCR models that chose the benchmark's expected texts.
- [openkannada.org/nudi-to-unicode](https://openkannada.org/nudi-to-unicode/): convert Nudi and Baraha text in the browser.

## License

The specification and other prose are under [CC BY 4.0](LICENSES/CC-BY-4.0.txt); the tables, schema, tools, tests, reference reader, runner and adapters under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your choice. The test lines from government documents are short excerpts that neither license covers; [NOTICE.md](NOTICE.md) and [REUSE.toml](REUSE.toml) give the license of every file, and [TRADEMARKS.md](TRADEMARKS.md) covers the names Open Kannada and kannadi.

Part of [Open Kannada](https://github.com/openkannada), free and open-source tools that make Kannada work properly on computers.
