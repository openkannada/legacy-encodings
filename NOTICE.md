# Notice

Kannada Legacy Encodings (KLE)
Copyright 2026 The Open Kannada Authors

## Licenses by directory

| Path | License |
|---|---|
| `spec/`, `PROPOSAL.md`, `README.md` and the other prose documents (`*.md`) | CC BY 4.0 ([LICENSES/CC-BY-4.0.txt](LICENSES/CC-BY-4.0.txt)) |
| `tables/`, `schema/`, `tools/`, `tests/` | MIT OR Apache-2.0 ([LICENSE-MIT](LICENSE-MIT), [LICENSE-APACHE](LICENSE-APACHE)) |
| `reference/`, the Python reference reader | MIT OR Apache-2.0 |
| `conformance/` runner, differential tester, edge cases, `cases/SOURCE.json` and `cases/shree-lipi.tsv` | MIT OR Apache-2.0 |
| `conformance/cases/{nudi,akruti,nudi-b,kan-eng}.tsv` | Short excerpts of third-party documents, not covered by either license (see below) |
| `adapters/` | MIT OR Apache-2.0 |

Code examples in the prose documents may also be used under MIT OR Apache-2.0. [REUSE.toml](REUSE.toml) gives the license of every file. If you redistribute this work, keep this notice and the license files.

## Glyph tables

The tables in `tables/` are copied from [kannadi](https://github.com/openkannada/kannadi), which licenses them the same way. They record which glyph code each legacy font uses for which Kannada letter. Each table was derived by rendering the font, whether installed or embedded in a public document, and by reading public documents typed in it; the table's header says which fonts and documents, and how. The tables hold no font software: no font files, outlines or hints. The code assignments are facts that any converter needs for compatibility. Nudi, Baraha, Akruti, Shree-Lipi, Shree-Kan-0850, Nudi B-Akshara and Kan-Eng are names of their owners' fonts and products, used here only to name the layouts.

No code or table was copied from other converters. In particular, nothing from ascii2unicode (GPL-3.0) is included; it is named in `PROPOSAL.md` as prior art only.

## Third-party material

| Material | Where | License | Credit |
|---|---|---|---|
| Short excerpts of Karnataka government web pages (2002), Karnataka Acts (2001 to 2003), budget papers (2002 to 2014) and Legislative Assembly member pages | `conformance/cases/{nudi,akruti,nudi-b,kan-eng}.tsv` | No license stated; not covered by this repository's licenses ([LICENSES/LicenseRef-Excerpts.txt](LICENSES/LicenseRef-Excerpts.txt)) | Government of Karnataka; each line records its source URL |

The Shree-Lipi lines in `conformance/cases/shree-lipi.tsv` were written for kannadi and encoded with its table. No newspaper text is included.

Used, not included: the Rust crates in `adapters/kannadi/Cargo.lock`, fetched by Cargo under their own permissive licenses, and jsonschema, installed by the test command.

## Removal requests

To ask for an excerpt to be removed, write to support@luminik.io or open an issue.
