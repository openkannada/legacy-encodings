---
pretty_name: Kannada legacy-font lines from Karnataka government documents
language:
  - kn
license: other
license_name: excerpts-fair-dealing
license_link: https://github.com/openkannada/legacy-encodings/blob/main/LICENSES/LicenseRef-Excerpts.txt
size_categories:
  - 1K<n<10K
task_categories:
  - text2text-generation
tags:
  - kannada
  - legacy-fonts
  - nudi
  - baraha
  - akruti
  - shree-lipi
  - unicode-conversion
  - benchmark
configs:
  - config_name: nudi
    data_files: lines/nudi.tsv
  - config_name: akruti
    data_files: lines/akruti.tsv
  - config_name: shree-lipi
    data_files: lines/shree-lipi.tsv
  - config_name: nudi-b
    data_files: lines/nudi-b.tsv
  - config_name: kan-eng
    data_files: lines/kan-eng.tsv
---

# Kannada legacy-font lines from Karnataka government documents

5,098 lines of Kannada typed in legacy fonts (Nudi and Baraha, Nudi B-Akshara, Akruti, Shree-Lipi and Kan-Eng), each as the glyph codes stored in a public Karnataka government PDF and the Unicode text the line shows, chosen among converter outputs by OCR of the line. It measures how accurately a converter turns legacy-font text into Unicode, on real documents from 2001 to 2026.

## Why it exists

Karnataka's offices have typed in legacy fonts for 25 years, and many still do: 53 of the 123 Kannada-text PDFs sampled from state sites in November 2026 store their Kannada as legacy font codes. Search engines, screen readers and language models read that text as strings like `PÀ£ÁðlPÀ`. Converters exist, but their published accuracy figures come from round trips of isolated syllables or from their own output. This set tests them on real lines, with expected texts the page supports; Kannada readers have not checked them yet.

## What is in it

| Layout | Lines | Documents | Confirmed | Likely | Unresolved |
|---|---|---|---|---|---|
| Nudi and Baraha (`nudi`) | 2,210 | 223 | 1,711 | 213 | 286 |
| Akruti (`akruti`) | 953 | 25 | 853 | 66 | 34 |
| Shree-Lipi (`shree-lipi`) | 421 | 8 | 337 | 19 | 65 |
| Nudi B-Akshara (`nudi-b`) | 1,000 | 36 | 682 | 123 | 195 |
| Kan-Eng (`kan-eng`) | 514 | 17 | 447 | 24 | 43 |
| **All** | **5,098** | **275** | **4,030** | **445** | **623** |

Fields of each line: `id`, `status`, `codes` (hexadecimal Windows-1252 glyph codes in drawing order), `expected` (Unicode, NFC, canonical form of the Open Kannada normalization profile), `source` (URL and page), `options`, `document`, `page`, `box` (PDF points), `fonts`, `found_by`. `documents.tsv` describes each document: group, year, URL, archive copy, SHA-256 and license.

Statuses: `confirmed` and `likely` lines are the scored set; `unresolved` lines wait for a Kannada reader; `verified` lines have been checked by one. See the [README](README.md#status).

## How it was made

Source documents come from Internet Archive and Common Crawl copies of Karnataka government sites and from the district portals' CDN, drawn by a fixed plan across sites and folders. Lines are read from the PDFs with their glyph codes, font names and positions. Each line is drawn with the font embedded in its own PDF; 2 Tesseract models, neither trained on legacy fonts, read the drawing and Unicode renderings of each converter's output in 4 fonts. The output that the page supports, with OCR habits discounted, becomes the expected text. The full method is in the [README](README.md).

## Known limits

- The expected text is one of the converters' outputs. Where all are wrong in a way OCR cannot see, the error stays; the reader sample measures how often.
- kannadi is a candidate on every line and the only one for Nudi B-Akshara, so its figures are an upper bound until the reader check. Use the normalized figures.
- Shree-Lipi is rare in government PDFs, so its lines come from few documents.
- Latin words in bilingual lines are not checked; digits and punctuation are checked loosely.
- Lines cluster by document; score with intervals that resample documents.

## Use

Score a converter with `conformance/run.py --cases benchmark/lines` and `benchmark/tools/score.py`. Cite the commit of the set and the converter's version with any figure.

Do not train a converter on these lines and then report its score here.

## License and removal

The lines are short excerpts of works of the Government of Karnataka with no license statement, kept with their sources for research on and testing of converters, as fair dealing under the Indian Copyright Act, 1957. They are not offered under an open license. To ask for an excerpt to be removed, write to support@luminik.io or open an issue. The tools are under MIT OR Apache-2.0 and this card under CC BY 4.0.
