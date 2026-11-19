# Kannada Legacy Encodings

An open specification, glyph tables and conformance tests for converting text typed in legacy Kannada fonts (Nudi, Baraha's ANSI fonts, Akruti, Shree-Lipi, Nudi B-Akshara, Kan-Eng) to Unicode.

Draft 0.1.0. The repository is private while the draft is reviewed. [PROPOSAL.md](PROPOSAL.md) explains why it exists and what is still to decide.

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
| [benchmark/](benchmark/) | 5,098 lines from 275 Karnataka government PDFs, with expected texts chosen by OCR of each line as its own font draws it, a reader review page and a data card |
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

Open a GitHub issue for a change to the specification, a table entry, a new layout or a new test line. A table change needs evidence: the font file or a rendering of its glyphs, and lines from public documents that use the codes, with their sources (section 10 of the specification). Bugs and sample documents go in issues too; send documents that cannot be public to support@luminik.io.

Every commit needs a `Signed-off-by` line (`git commit -s`) under the [Developer Certificate of Origin](https://developercertificate.org/); see [CONTRIBUTING.md](CONTRIBUTING.md).

Organizations that want to take part in the specification, such as KAGAPA or a government office, can write to founders@luminik.io.

## License

The specification and the other prose documents are under [CC BY 4.0](LICENSES/CC-BY-4.0.txt). The tables, schema, tools, tests, reference reader, conformance runner and adapters are under the MIT license or the Apache License 2.0, at your choice: see [LICENSE-MIT](LICENSE-MIT) and [LICENSE-APACHE](LICENSE-APACHE). The test lines from government documents are short excerpts that neither license covers. [NOTICE.md](NOTICE.md) gives the license of each directory and credits the sources, and [REUSE.toml](REUSE.toml) gives the license of every file. The names Open Kannada and kannadi are covered by [TRADEMARKS.md](TRADEMARKS.md).

Part of [Open Kannada](https://github.com/openkannada), free and open-source tools that make Kannada work properly on computers.
