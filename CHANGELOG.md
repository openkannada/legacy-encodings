# Changelog

## Unreleased

- `benchmark/`: 5,098 lines in the 5 layouts from 275 public Karnataka government PDFs of 2001 to 2026, from Internet Archive and Common Crawl copies and the district portals. Each line keeps its glyph codes, page, box and fonts; its expected text is the converter output that 2 OCR models, neither trained on legacy fonts, support when they read the line drawn with the PDF's own font. 4,358 lines are confirmed, 65 likely and 675 unresolved. A stratified sample of 400 lines and an offline review page wait for Kannada readers. The tools that made it are in `benchmark/tools`, with `score.py` for intervals that resample documents.
- `run.py --cases DIR` runs another folder of line files, such as `benchmark/lines`, with an optional 6th column of reading options; `confirmed` and `likely` count as checked statuses.

- The runner also compares text in the canonical form of kannadi's Kannada text normalization profile (`reference/normalize.py`, tested against the profile's vectors), and reports exact and normalized figures side by side. Section 8 says the normalized figure does not count towards conformance. `--layouts` limits a run to the layouts a converter reads.
- Adapters for KaGaPa's KannadaAsciiUnicodeSDK (`adapters/kagapa`), Sanka (`adapters/sanka`) and Sanchaya's kannada-font-converter (`adapters/sanchaya`), all run locally from a checkout.
- The Kuvempu Tantramsha fonts of Kannada University (sanchaya/kuvempu-fonts) are in the Nudi layout or have no Kannada, so they need no new layout (sources/README.md).
- `--layouts` with an unknown id is an error, and a run limited by it is not assessed for conformance.
- `sources/`: the Nudi table checked against Appendix A of the 2003 Unicode proposal L2/03-068 (76 of the 79 code points Unicode assigned as proposed agree; F3 nukta and F1 ೄ are missing from the table, and 73, which the proposal uses for the avagraha, is the mahaprana stroke) and against the characters the KGP keyboard types in jquery.ime (76 of 78 read; the same 2 gaps).
- Unicode Kannada passes through a conversion unreported (section 3.2): the Kannada block, the dandas, ZWNJ and ZWJ, which no layout uses as glyph codes. Section 5.1 no longer gives ಕ as an unknown character, and a zero before a Unicode Kannada letter becomes ಂ (section 5.6). This matches kannadi from fded282. Input given as glyph codes is unaffected, so the conformance results do not change.
- Licenses: tables, schema, tools, tests, the reference reader, the conformance runner and the adapters are under MIT OR Apache-2.0, and the prose under CC BY 4.0, with "The Open Kannada Authors" as copyright holder. `NOTICE.md` names the license of every directory, `REUSE.toml` that of every file, and `TRADEMARKS.md` says how the names may be used.
- The Shree-Lipi conformance lines are 140 lines written for kannadi and encoded with its table, in place of 130 lines of Udayavani newspaper pages. A new status, `written`, marks them, and the headline figures count it with `verified` and `read`. Cases copied from kannadi e350d5d.
- Contributions are signed off under the Developer Certificate of Origin. CI checks the `Signed-off-by` line of each commit in a pull request, and runs `reuse lint`.

## 0.1.0, draft

- Specification draft: layout tables, reading rules, reports, layout detection from font names and from text, and an outline of writing back.
- Tables for 5 layouts (nudi, akruti, shree-lipi, nudi-b, kan-eng), copied from kannadi at commit c786820, as TSV and JSON, with a JSON Schema.
- Font-name rules with 47 examples.
- Conformance: 772 lines from public documents in 5 layouts, 64 edge cases that reach 32 rules of the reading and detection steps, a runner with a line-based JSON protocol, a differential tester, a Python reference reader written from the specification, and an adapter for kannadi. The reference reader and kannadi give the same response to every request.
- Detection accuracy measured from whole lines and from 8, 16 and 32 codes (section 7.3).
