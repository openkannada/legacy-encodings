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
| [conformance/](conformance/) | 772 lines from public documents, 52 edge cases, the runner and its protocol, and [measured results](conformance/RESULTS.md) |
| [reference/kle.py](reference/kle.py) | A reference reader in Python, written from the specification |
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

## License

The specification text is under [CC BY 4.0](LICENSE-CC-BY-4.0). The tables, schema and tools are under the [MIT license](LICENSE-MIT). See [NOTICE.md](NOTICE.md).
