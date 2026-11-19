# Legacy converter benchmark: Karnataka government lines

A test set of 5,098 lines of Kannada typed in legacy fonts, taken from 275 public Karnataka government PDFs, each with the Unicode text it should convert to. The expected text was chosen by what an OCR reader sees in the line as the document's own font draws it, not by any one converter. Any converter that speaks the [conformance protocol](../conformance/README.md#the-protocol) can be scored on it.

| Layout | Lines | Documents | Confirmed | Likely | Unresolved |
|---|---|---|---|---|---|
| Nudi and Baraha (`nudi`) | 2,210 | 223 | 1,937 | 16 | 257 |
| Akruti (`akruti`) | 953 | 25 | 883 | 29 | 41 |
| Shree-Lipi (`shree-lipi`) | 421 | 8 | 355 | 3 | 63 |
| Nudi B-Akshara (`nudi-b`) | 1,000 | 36 | 709 | 14 | 277 |
| Kan-Eng (`kan-eng`) | 514 | 17 | 474 | 3 | 37 |
| **All** | **5,098** | **275** | **4,358** | **65** | **675** |

## Files

| Path | What it holds |
|---|---|
| `lines/<layout>.tsv` | 1 line per row: id, status, codes, expected, source, options, document, page, box, fonts, found_by |
| `documents.tsv` | Each source document: group, year, layouts, lines, URL, archive copy, how it was fetched, SHA-256 of the copy read, license |
| `plan.tsv` | The 641 PDFs drawn for the collection, before any was read |
| `review/sample.tsv` | The stratified sample for Kannada readers |
| `review/index.html` | The reader review page for that sample, with the line images inside; it works offline |
| `tools/` | The scripts that made all of the above, and `score.py` for intervals |

Columns of `lines/<layout>.tsv`:

- **codes**: the glyph codes in drawing order, as hexadecimal Windows-1252 codes, like `conformance/cases`.
- **expected**: the Unicode text, in the canonical form of the [normalization profile](https://github.com/openkannada/kannadi/blob/main/NORMALIZATION.md) where a converter gave that form.
- **source**: the document URL and page. **document** points into `documents.tsv`, which gives the archive copy.
- **options**: `kannada_digits` for lines in fonts that draw Kannada digits at the ASCII digit codes (the `k` Nudi fonts, section 7.1); the runner passes it on.
- **box**: the line's box on the page as displayed, in PDF points from the bottom left: x0 y0 x1 y1.
- **fonts** and **found_by**: the font names the codes came from, and whether the layout was known from those names (section 7.1) or found from the codes (section 7.2), for fonts whose names were stripped from the PDF.

## Status

- **verified**: a Kannada reader checked the expected text against the line image. None yet; see [Reader check](#reader-check).
- **confirmed**: OCR evidence supports exactly 1 converter output and no other.
- **likely**: the OCR evidence leans to 1 output, with 1 difference left unexplained, or a tie broken by closeness to the OCR reading or by the digits the font draws.
- **unresolved**: no output is supported over the others, or none matches the page. The expected text is the best guess and waits for a reader.

On 96% to 99% of the confirmed and likely lines of each layout, at least 1 of the 2 OCR models reads the expected text exactly, apart from the differences listed under step 5 below.

`conformance/run.py` counts verified, confirmed and likely lines as checked, and reports unresolved lines under "all statuses".

## How the lines were collected

1. **Documents.** Most Karnataka government hosts do not answer from outside India, so the PDFs come from archive copies: the Internet Archive's captures of the Legislature (kla.kar.nic.in), the Karnataka Gazette (gazette.kar.nic.in), the Department of Parliamentary Affairs and Legislation's Acts (dpal.kar.nic.in), the Finance Department's budget papers (kar.nic.in/finance, 2002 to 2014) and a few textbook, examination and recruitment PDFs (ktbs, kseeb, kpsc); and, from the 2026 audit of Karnataka government sites, the legacy and mixed PDFs of the 31 district portals and other state bodies, fetched live from their CDN, and of the Legislature, from Common Crawl. `tools/plan.py` draws a fixed number of PDFs from each folder of each site, so no single series fills the set. Scanned PDFs, English PDFs and Unicode PDFs drop out at the next step.
2. **Lines.** `tools/extract.py` reads each page with pdfminer and records every glyph's code, font, position and size. A glyph's code is its code in the font, through the font's `Differences` list or, for subsets Word renumbered from 1, through the font's ToUnicode map. Glyphs on 1 baseline that move rightward form a run, split where the font family changes; a second copy drawn on top for a bold effect is dropped. A run becomes a line when it has 12 to 160 codes, its layout is known, at least half of its readable characters and at least 6 are Kannada, and no glyph of another run overlaps its box.
3. **Layout.** The font name decides the layout (section 7.1). Where the PDF hides the name (`CIDFont+F1`), the layout comes from the codes (section 7.2), and the line is kept only if the reference reader finds no unknown or malformed code in it. Lines in standard fonts such as Arial or Times never qualify, so the OCR text layers of scanned pages stay out.
4. **Selection.** `tools/select_lines.py` drops any code sequence seen before, then takes lines round-robin over the documents of each layout in random order, at most 100 lines a document (300 for a layout found in fewer than 15 documents), up to a target per layout.

## How the expected text was chosen

No line's expected text comes from a single converter. `tools/truth.py` treats the outputs of 4 converters as candidates and lets the page decide between them:

1. **The page.** `tools/draw.py` draws the line's glyphs with the font program embedded in that same PDF, each at its recorded position, at 64 pixels to the em. The image shows exactly the line's codes as the document's font draws them, with nothing from the lines above or below. Lines whose font is not embedded are left out.
2. **The candidates.** kannadi, KaGaPa's KannadaAsciiUnicodeSDK, Sanka and Sanchaya's kannada-font-converter each convert the codes (`tools/candidates.py`), for the layouts each one reads. Their outputs are compared in canonical form, without white space or joiners.
3. **OCR.** 2 Tesseract models read the line image: `kan_ft_ofl3` from [kannada-ocr](https://github.com/openkannada/kannada-ocr), trained on Wikisource lines and OFL fonts and never on legacy fonts, and Tesseract's own `kan`. Neither knows any legacy table.
4. **Explained differences.** The same 2 models also read each candidate rendered in 4 Unicode fonts: Noto Sans Kannada, Noto Serif Kannada, and the regular and bold Unicode releases of the Nudi design most of these documents use (`tools/ocr.py`). A difference between a candidate and the OCR reading of the page counts against the candidate only when the model does not make the same difference reading that candidate's own rendering. That separates OCR habits, such as reading ದ್ದಿ as ದ್ಧಿ, from real differences on the page.
5. **What does not count.** Swaps between digits or punctuation marks, punctuation read as up to 2 stray characters, and Latin words of 2 letters or more, which the Kannada models cannot read. A Latin letter written against a Kannada letter always counts, once per model: it is a glyph a converter left unconverted, which OCR skips on the page and on the rendering alike.
6. **Status.** The candidate with the fewest unexplained differences wins. It is confirmed if it has none and every other candidate has some; likely if it has exactly 1 and the others more, or if it ties with no unexplained difference but is closer to the OCR reading, or if the tied texts differ only in digit script and the font decides it; unresolved otherwise.

## Parallel text

The first plan was to align documents published both in a legacy font and in Unicode. None could be used. The 2026 bills set their title pages in Nudi and their bodies in Nirmala UI, but the Unicode bodies have damaged text layers that drop conjuncts on extraction, as 62 of the 70 Unicode PDFs in the audit did. Kannada Wikisource has no Karnataka Acts, budget speeches or bills. Any Unicode editions of these Acts and budget papers would be on karnataka.gov.in hosts, which do not answer from outside India. Every expected text here comes from the OCR evidence above.

## Reader check

`review/sample.tsv` is a stratified random sample of 400 lines: for each layout, about half from confirmed lines and a quarter each from likely and unresolved lines, so that the error of each status can be measured. `review/index.html` shows each line image with its expected text; a reader marks it Same or Different, types a correction, and downloads the answers.

```bash
python3 benchmark/tools/sample.py bars benchmark/lines benchmark/review/sample.tsv answers.tsv
```

prints, for each layout and status, the share of wrong expected texts with a 95% Wilson interval, and for each layout the stratified estimate over confirmed and likely lines with its upper bound. Without answers it assumes the readers find no error, which gives the narrowest error bars the sample can reach. A line a reader checks becomes `verified`, with the reader's text where it differed.

## Scoring a converter

```bash
python3 conformance/run.py --markdown --cases benchmark/lines --out kannadi.json -- adapters/kannadi/target/release/kle-kannadi-adapter
python3 benchmark/tools/score.py benchmark/lines kannadi.json --label-error nudi=1.5,akruti=1.5
```

`run.py` gives exact and normalized line and character figures, as for the conformance cases. `score.py` adds 95% intervals from a bootstrap that resamples whole documents, since lines from 1 document share a typist and habits, and `--label-error` widens each interval by the upper bound on wrong expected texts from the reader check. Report both with the commit of this file and the converter's version.

## Limitations

- **The candidates bound the truth.** A line where every converter is wrong in the same way can still be confirmed if OCR cannot see the difference, and a line where none is right is unresolved. The reader check measures the first; the unresolved count shows the second.
- **OCR reads Kannada, not typing errors.** Where the source has a typing error that looks like the correct spelling, both OCR models tend to read the correct spelling; the explained-difference step catches most of these, and the rest end up likely or unresolved.
- **Digits and punctuation are checked loosely**, and Latin words not at all.
- **Shree-Lipi is thin.** Government PDFs rarely use it; its 421 lines come from 8 documents, 300 of them from 1 Karnataka Public Service Commission PDF.
- **Documents are not equal.** A few large documents supply many lines; `score.py` resamples documents for that reason.
- **Archive copies.** For PDFs fetched live, the archive link is the Internet Archive's closest capture, which may be a different version than the copy read; `documents.tsv` gives the SHA-256 of the copy read.

## Reproducing it

The tools need Python 3.12 with pdfminer.six, fontTools, Pillow, freetype-py, uharfbuzz and numpy; poppler; Tesseract 5 with the `kan` model; a checkout of [kannada-ocr](https://github.com/openkannada/kannada-ocr) with `kan_ft_ofl3` in `data/tessdata` (`KANNADA_OCR`); and the converters' adapters (`KANNADI_ADAPTER`, `KAGAPA_ADAPTER`, `SANKA_JS`, `SANCHAYA_JS`). Run them from a scratch folder:

```bash
T=path/to/legacy-encodings/benchmark/tools
python3 $T/plan.py queries          # save each query's result as work/cdx-<site>.txt
python3 $T/plan.py draw audit.csv legislature-census.csv
python3 $T/fetch.py work/plan.tsv
for f in dl/*.pdf; do d=$(basename $f .pdf); python3 $T/extract.py $d $f work/lines/$d.jsonl; done
python3 $T/select_lines.py work/selected.jsonl
python3 $T/draw.py work/selected.jsonl work/images
python3 $T/candidates.py work/selected.jsonl work/candidates.jsonl
python3 $T/ocr.py work/candidates.jsonl work/images work/ocr.jsonl
python3 $T/truth.py work/selected.jsonl work/candidates.jsonl work/ocr.jsonl work/truth.jsonl
python3 $T/export.py work/selected.jsonl work/truth.jsonl out
```

Converter outputs, the intermediate files and the PDFs stay in the scratch folder. Nothing here records which converter gave which text.

## License

The lines are short excerpts of works of the Government of Karnataka, kept with their sources for research on and testing of converters, as fair dealing under the Indian Copyright Act, 1957 (`LicenseRef-Excerpts`). No page is stored in full; the line images in `review/index.html` are drawn from the excerpts alone. To ask for an excerpt to be removed, write to support@luminik.io or open an issue. The tools are under MIT OR Apache-2.0, and this file and the data card under CC BY 4.0.
