# Proposal: an open specification for legacy Kannada encodings

Status: draft for Prasad's review. Nothing here is public yet.

## The problem

Years of Kannada documents were typed before Unicode: government orders, budget papers, Acts, newspapers, school textbooks. They were typed in fonts that draw Kannada shapes at the codes of Latin letters. At least 5 families of such fonts are in public documents, and each family stores text in its own way:

| Layout | Where it is found | How it differs |
|---|---|---|
| Nudi, and Baraha's ANSI fonts | Karnataka government web pages and documents | The state's own standard. Vowel signs split into 2 or 3 glyphs. |
| Akruti | Karnataka Acts and budget highlights | Other codes; some signs typed after a space. |
| Shree-Lipi | The Udayavani newspaper's web pages, 2003 and 2004; the test lines are now written by us | Other codes, and cluster glyphs such as ಕ್ಷ and ಜ್ಞ. |
| Nudi B-Akshara | Legislative Assembly and budget PDFs | Bilingual: Latin at the ASCII codes, Kannada above 80. |
| Kan-Eng | Budget papers, 2002 to 2014 | Bilingual, with yet another Kannada layout. |

Text in these fonts cannot be searched, indexed, read aloud by a screen reader, used to train a language model, or copied into a modern document. Converters exist (aravindavk/ascii2unicode, KAGAPA's KannadaAsciiUnicodeSDK, a Python package, Baraha's own tool, Google Docs add-ons), but each keeps its own tables and rules, and none publishes a verified test set or an accuracy figure. A user cannot tell which converter is right, and a converter author has to rediscover every layout from scratch.

kannadi, the Rust library under openkannada, has now derived tables for all 5 layouts from the font files and public documents, with 445 test lines read against the rendered glyphs, 140 Shree-Lipi lines written for the tests, and a 207-line Nudi benchmark corpus. This proposal turns that work into a shared, open reference.

## What we propose

A small open specification, **Kannada Legacy Encodings (KLE)**, with 4 parts, in the repository `openkannada/legacy-encodings`:

1. **Specification** (`spec/kle.md`): what a layout table is; the exact steps that turn drawing-order glyph codes into Unicode syllables; how unknown and malformed output is reported; how the layout is found from a font name or from the text alone; how writing back works.
2. **Tables** (`tables/`): 1 table per layout, as hand-edited TSV and generated JSON with a JSON Schema. They are generated from kannadi's data tables at a pinned commit, so there is 1 source of truth, and every change is listed with its evidence.
3. **Conformance tests** (`conformance/`, next pull request): the test lines from public documents with their sources, a runner that drives any converter through a line-based JSON protocol and reports accuracy, a reference reader in Python written only from the specification, and an adapter for kannadi.
4. **Detection** (section 7 of the specification): the font-name rules as data, and a documented scoring method for unknown text, with its accuracy measured on the test lines, including short snippets.

### Who it is for

- **Converter authors**, in any language: read the JSON tables, follow section 5, run the conformance tests, publish the figure.
- **Archives and digitization projects**: know which converter to trust for which layout, and what the remaining errors are.
- **Font and standards bodies** (KAGAPA, the Kannada Development Authority): a neutral reference to point to, and a place to add layouts they hold the fonts for.

### Why a specification and tables as well as a library

A library helps people who can use that language. Tables and a test set help every converter, including ones built into word processors, OCR pipelines and web tools. The reading rules are small (section 5 is about 2 pages), so a faithful reader in another language is a few hundred lines; the Python reference reader in the next pull request will show how small.

## Design choices

- **Drawing order lives in the tables.** Each layout's quirks (split vowel signs, multi-glyph letters, signs typed after a space, subscripts that carry a vowel sign) are expressed as table entries of a few kinds, and 1 set of reading rules serves every layout. A new layout should need only a new table.
- **Every problem is reported.** A conforming reader reports every code it cannot place and every syllable that is not valid. A clean result can be trusted; an unclean one says where to look.
- **Evidence for every entry.** A table change needs the font's glyph and lines from public documents, added as test cases with sources.
- **Windows-1252 as the code space.** Documents and web pages give legacy text as Windows-1252 characters, so tables key on those codes, including the 5 codes Windows-1252 leaves undefined.
- **Portable detection rules.** Font-name rules are regular expressions limited to syntax every common engine shares.

## Naming

Recommended: **Kannada Legacy Encodings (KLE)**, repository `openkannada/legacy-encodings`. It says what it covers, in the words people search for, and leaves room for related scripts later.

Alternatives considered:

- `kannada-legacy-fonts`: names the fonts, though the subject is the encodings.
- `lipi-tables`: short, but says little to someone who does not know the project.
- A Kannada name, such as `lipi-setu` (bridge between scripts): memorable, but harder to find.

## License

- Specification text: **CC BY 4.0**, so others can quote and adapt it with credit.
- Tables, schema, tools, reference reader, runner and adapters: **MIT OR Apache-2.0**, the same license kannadi has, so the tables are copied with no relicensing. Decided on 17 November 2026, in place of CC0.
- Test lines: short excerpts of Karnataka government documents, kept with their sources for testing, as kannadi already does; neither license covers them. The Shree-Lipi lines were written for kannadi, encoded with its table, and are under the code license; no newspaper text is kept.
- Contributions: signed off under the Developer Certificate of Origin, with no contributor license agreement.

## Versions and governance

- Semantic versions. A change that gives different output for some input is a minor version before 1.0 and a major version after it.
- 1.0 needs: a Kannada reader's check of the test lines; 1 independent reader in another language passing the tests; writing-back cases (section 9).
- Changes come as pull requests with evidence. Prasad decides until there are other maintainers.

## Plan

| Step | Content | State |
|---|---|---|
| 1 | Proposal, specification draft, schema, generated tables, font rules | Pull request 1 |
| 2 | Conformance cases, runner, Python reference reader, kannadi adapter, detection accuracy | Pull request 2 |
| 3 | Kannada reader's check of the test lines; writing-back cases | After Prasad's review |
| 4 | Make the repository public; tell converter authors and KAGAPA | Prasad's call |

## Decisions for Prasad

1. **Name and home**: KLE in `openkannada/legacy-encodings`, or another name.
2. **Table license**: decided on 17 November 2026: MIT OR Apache-2.0, like kannadi.
3. **Source of truth**: for now kannadi's tables are the source and this repository copies them at a pinned commit. Once the specification is public, the source could move here, with kannadi reading the tables from this repository.
4. **When to go public**, and whether to invite KAGAPA and the authors of other converters to review the draft first.
5. **Names in the drafts**: the proposal and its decisions name Prasad; they should be reworded before the repository is public.
