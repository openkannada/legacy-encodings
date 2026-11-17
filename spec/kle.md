# Kannada Legacy Encodings (KLE)

Version 0.1.0, draft. Not for adoption yet: tables, names and section numbers may change before 1.0.

## 1. Introduction

Before Unicode, Kannada was typed in fonts that draw Kannada shapes at the code points of Latin letters. A document stores the codes the typist pressed, in the order the shapes are drawn, and only the font makes them readable. Copied out of that font, the word ಕನ್ನಡ typed in Nudi reads `PÀ£ÀßqÀ`.

Each family of fonts puts its shapes at different codes, and many families store a syllable's parts in a different order from Unicode. Converters for this text exist, but each keeps its own tables and its own rules, and none publishes a test set. This specification describes:

- what a layout table is, in a form any program can read (section 4);
- how legacy text is read into Unicode, step by step (section 5);
- how the result reports what could not be read (section 6);
- how the layout of a text is found from its font name or from the text itself (section 7);
- how a converter shows that it follows this specification (section 8).

Section 9 covers writing Unicode back into a legacy layout, which this version describes only in outline.

### 1.1 Conventions

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119 and RFC 8174 when they are in capitals.

Glyph codes are written as 2 hexadecimal digits, such as `C0`. Unicode characters are written as U+0CCD or as the character itself. Text in a code font is shown in `code` style.

### 1.2 Layouts covered

| Id | Name | Fonts |
|---|---|---|
| `nudi` | Nudi | Nudi 01 e to Nudi 05 and Nudi Akshara (the ANSI Nudi fonts up to version 5), and Baraha's BRH fonts for Kannada |
| `akruti` | Akruti | AkrutiKndPadma and its weights |
| `shree-lipi` | Shree-Lipi | Shree-Kan-0850 and its styles |
| `nudi-b` | Nudi B-Akshara | NudiB-Akshar, the bilingual Nudi font |
| `kan-eng` | Kan-Eng | Kan-EngPraja, Kan-EngDeepa, Kan-EngKarn, Kan-EngVani, Kan-EngUsha |

The id `baraha` is an alias of `nudi`: Baraha's ANSI fonts for Kannada share the Nudi layout. Baraha's phonetic typing scheme, which spells Kannada in Latin letters, is a transliteration scheme and is out of scope.

## 2. Terms

- **Glyph code**: a number from 00 to FF that selects a glyph in a legacy font.
- **Legacy text**: a sequence of glyph codes meant to be shown in a legacy font.
- **Layout**: the assignment of glyphs to codes shared by a family of fonts.
- **Layout table**: the list of entries that says what text each code, or sequence of codes, stands for in 1 layout.
- **Entry**: 1 row of a layout table: a code sequence, a kind, a value and an optional preference.
- **Drawing order**: the order in which a typist stored a syllable's glyphs, which follows how the shapes are drawn left to right.
- **Logical order**: the order of characters in Unicode text.
- **Syllable**: a consonant or vowel letter with the marks that belong to it. Unicode calls this an akshara.

## 3. Characters

### 3.1 Classes

The rules of section 5 sort Kannada characters into these classes.

| Class | Characters |
|---|---|
| vowel | U+0C85 to U+0C8C, U+0C8E to U+0C90, U+0C92 to U+0C94, U+0CE0, U+0CE1 |
| consonant | U+0C95 to U+0CA8, U+0CAA to U+0CB3, U+0CB5 to U+0CB9, U+0CDE |
| vowel sign | U+0CBE to U+0CC4, U+0CC6 to U+0CC8, U+0CCA to U+0CCC, U+0CD5, U+0CD6, U+0CE2, U+0CE3 |
| virama | U+0CCD |
| nukta | U+0CBC |
| modifier | U+0C81 to U+0C83, U+0CF1 to U+0CF3, U+0951 to U+0954, U+1CD0 to U+1CD2, U+1CD4 to U+1CE8, U+1CED, U+1CF4, U+1CF7 to U+1CF9 |
| digit | U+0CE6 to U+0CEF |
| other | every other character |

A **letter character** is a vowel, a consonant or a vowel sign.

The **mahaprana pairs** are ಪ and ಫ, ಬ and ಭ, ಡ and ಢ, ದ and ಧ. The first of each pair is the plain consonant and the second its aspirate.

### 3.2 Passing characters

These characters carry no Kannada and pass through a conversion unchanged without being reported: white space (the Unicode White_Space property), ASCII punctuation (U+0021 to U+002F, U+003A to U+0040, U+005B to U+0060, U+007B to U+007E), U+2010 to U+2027, and U+00A0.

### 3.3 Normalization

Converted text is in Unicode Normalization Form C (NFC), syllable by syllable (section 5.5). In Kannada this joins split vowel signs: U+0CC6 with U+0CD5 becomes ೇ U+0CC7, U+0CC6 with U+0CC2 becomes ೊ U+0CCA, and so on.

## 4. Layout tables

A layout table is published in 2 equivalent forms: a tab-separated file (`tables/<id>.tsv`), which is the form edited by hand, and a JSON file (`tables/json/<id>.json`) generated from it, which follows `schema/layout.schema.json`.

### 4.1 Tab-separated form

The file is UTF-8. A line that starts with `#` is a comment, and the comment lines before the first entry are the table's notes. Empty lines are skipped. Every other line is 1 entry with up to 4 columns separated by tabs:

1. **codes**: 1 or more glyph codes, as 2 uppercase hexadecimal digits each, separated by spaces;
2. **kind**: 1 of the kinds in section 4.3;
3. **value**: the Kannada text, which may be empty for some kinds;
4. **preference**: optional, as in section 4.4.

### 4.2 JSON form

The JSON form holds the same entries in the same order, with these fields:

- `codes`: the codes as an array of 2-digit strings;
- `kind`;
- `value`;
- `prefer`, when the entry has a preference: `{"type": "on", "chars": ["ಪ", "ಫ", "ವ"]}`, `{"type": "with", "chars": ["ಿ"]}`, `{"type": "after-ottu"}` or `{"type": "read"}`.

The file also carries the layout's `id`, `name`, `aliases`, `description`, example `fonts`, the `byte_encoding` (always `windows-1252` in this version), `draws_latin` (section 4.6), the `source` it was generated from, and the `notes`.

### 4.3 Kinds

| Kind | Meaning | Value |
|---|---|---|
| `letter` | Starts a syllable that is complete as drawn. | A vowel or consonant, optionally followed by a vowel sign, or a whole cluster such as ಶ್ರೀ. |
| `base` | Starts a syllable whose consonant shape needs a following sign: the head stroke for the inherent a, a vowel sign, or the virama. | A consonant, or a cluster of consonants joined by the virama. |
| `sign` | A vowel sign or part of one, added to the open syllable. | 1 vowel sign, the virama, or empty for the head stroke. |
| `ottu` | Subscript consonants added to the open syllable's cluster. | 1 or more consonants drawn as 1 glyph, optionally followed by 1 vowel sign drawn with them. |
| `arka` | The arkavattu: ರ್ written before the cluster. | Empty. |
| `mod` | Anusvara or visarga added to the open syllable. | 1 modifier. |
| `aspirate` | The mahaprana stroke: turns the open syllable's first consonant into its aspirate (section 3.1). | Empty. |
| `ignore` | A spacing glyph that carries no text. | Empty. |
| `literal` | Punctuation, digits, Latin letters or spaces drawn as themselves. | The text it stands for. |

### 4.4 Preferences

A preference tells a writer (section 9) which of several entries with the same meaning to use. Readers ignore preferences, apart from `read`, which writers also skip.

- `on X Y ...`: use this entry when the syllable's consonant is one of the listed characters.
- `with X Y ...`: use this entry when the syllable's vowel sign contains one of the listed characters.
- `after-ottu`: use this entry right after a subscript consonant.
- `read`: a way of typing that is read but never written, such as a sign typed after a space.

### 4.5 Rules

A table MUST follow these rules. `tools/tables.py check` tests every one of them.

1. No 2 entries have the same codes.
2. An entry whose codes start with 20 (space) and have more than 1 code is marked `read`.
3. A `base` value is a consonant, or consonants joined by the virama. A `base` that is not marked `read` has a value of exactly 1 consonant.
4. An `ottu` value is 1 or more consonants followed by at most 1 vowel sign.
5. A `sign` value is empty, 1 vowel sign, or the virama.
6. A `letter` value starts with a vowel or a consonant.
7. A `mod` value is 1 modifier.
8. `arka`, `aspirate` and `ignore` have an empty value; `literal` has a value.
9. Only `sign` (with a value), `ottu`, `arka` and `aspirate` entries have an `on`, `with` or `after-ottu` preference.

### 4.6 Bilingual layouts

A layout **draws Latin** when it has a `literal` entry whose value is 1 or more ASCII letters. Nudi B-Akshara and Kan-Eng draw Latin letters at the ASCII letter codes, so English in the same font converts to itself. Section 7.2 uses this property.

## 5. Reading legacy text

This section is normative. A conforming reader MUST give the same text as these steps for every input; it MAY be built any way it likes.

### 5.1 Input

The input is a sequence of glyph codes. Text taken from a word processor document or a web page is usually already a string: each of its characters stands for the code it has in Windows-1252, and the 5 codes Windows-1252 leaves undefined (81, 8D, 8F, 90, 9D) appear as U+0081, U+008D, U+008F, U+0090 and U+009D. A reader MUST map such a string back to codes through Windows-1252 before the steps below, or apply the steps to the characters directly, which gives the same result.

Text taken from a PDF needs the font's own encoding applied first. Getting codes out of a PDF is out of scope, but 1 pitfall is common enough to note: when Acrobat cannot keep a glyph at an undefined Windows-1252 code, it moves the glyph into a second copy of the font, which a text extractor reports as a separate run. Those runs belong back in the line at the original codes.

Below, a **position** is an index into the code sequence, starting at 0.

### 5.2 Matching

At each position, the reader finds the **longest entry**: the entry with the most codes whose codes equal the codes at that position. A match is refused when the code at the position is white space and no syllable is open (section 5.3); the reader then treats the position as if no entry matched.

- If an entry matches, the reader applies it (section 5.3) and moves past all its codes.
- If none matches, the code is a **plain code** (section 5.6), and the reader moves 1 position on.

### 5.3 Syllables

The reader keeps at most 1 **open syllable**, with these parts: its letter text, whether its shape needs a sign, whether it has a sign, its vowel signs in order, whether it has a virama, its subscript consonants in order, whether it has an arkavattu, its modifiers in order, and the codes it has rejected.

Entries are applied as follows.

- `letter`: close the open syllable (section 5.5) and open a new one with the value as its letter text and no need for a sign.
- `base`: the same, except that the new syllable needs a sign.
- `ignore`: nothing.
- `literal`: close the open syllable and write the value.
- Any other kind, when a syllable is open, is added to it:
  - `sign` with the virama as its value: mark the syllable as having a sign. If it already has a virama, reject the codes; otherwise give it a virama.
  - `sign` with any other value: mark the syllable as having a sign and append the value to its vowel signs. An empty value, the head stroke, appends nothing.
  - `ottu`: append the consonants to its subscripts. If the value ends in a vowel sign, mark the syllable as having a sign and append that sign to its vowel signs.
  - `arka`: if the syllable already has an arkavattu, reject the codes; otherwise give it one.
  - `mod`: append the value to its modifiers.
  - `aspirate`: if the first character of the letter text is a plain consonant of a mahaprana pair, replace it with its aspirate; otherwise reject the codes.
- Any other kind, when no syllable is open, is a **stray mark** (section 5.4).

Rejected codes are reported as unknown at their positions (section 6) and are kept, as their Windows-1252 characters, to be written after the syllable.

### 5.4 Stray marks

A mark with no syllable to join is written at once:

- a `sign` with a value: write the value;
- `mod`: write the value;
- `ottu`: for each consonant, write the virama and the consonant; then write the vowel sign, if any;

and the written range is reported as malformed (section 6). A `sign` with an empty value, an `arka` or an `aspirate` with no syllable is reported as unknown at its positions, and its codes are written as their Windows-1252 characters.

### 5.5 Closing a syllable

A syllable is closed when another starts, when a `literal` or plain code is written, and at the end of the input. Its text is built in this order:

1. ರ U+0CB0 and the virama, if it has an arkavattu;
2. the **cluster** of the letter text (below);
3. the virama and the consonant, for each subscript consonant in order;
4. the rest of the letter text after the cluster;
5. its vowel signs in order;
6. the virama, if it has one;
7. its modifiers in order.

The **cluster** is the letter text's first character, extended while it is followed by the virama and a consonant. If the cluster then has at least 3 characters and ends in the virama and ರ, that final virama and ರ are left out of the cluster. So subscripts typed after ಕ್ಷಿ join after ಕ್ಷ, while subscripts typed after a letter ending in ್ರ go before it, because Unicode keeps ್ರ last.

The text is normalized to NFC and written, followed by the rejected codes. The syllable is **malformed** when any of these hold:

- its shape needs a sign and it has none;
- the NFC text has more than 1 vowel sign;
- its letter text starts with a vowel, and it has an arkavattu, a sign or a subscript.

The range of the written syllable, without the rejected codes, is reported as malformed.

### 5.6 Plain codes

A code with no entry is written by these rules, after closing the open syllable:

1. An ASCII digit 0 to 9. If the digit is 0, the option **zero as anusvara** is on, the last character written so far is a letter character, and the longest entry at the next position is a `letter` or `base`, write the anusvara ಂ U+0C82. Otherwise, if the option **Kannada digits** is on, write the Kannada digit of the same value; otherwise write the ASCII digit.
2. A passing character (section 3.2): write it.
3. Anything else: write it as its Windows-1252 character and report it as unknown.

### 5.7 Options

| Option | Default | Use |
|---|---|---|
| zero as anusvara | on | Typists often typed the digit 0 for ಂ between letters: `ಪ್ರಾರ0ಭ` is ಪ್ರಾರಂಭ. |
| Kannada digits | off | The `k` variants of the numbered Nudi fonts, such as Nudi 04 k, draw Kannada digits at the ASCII digit codes (section 7.1). |

### 5.8 Worked examples

In the Nudi layout:

| Codes | Entries | Text |
|---|---|---|
| 50 C0 A3 C0 DF 71 C0 | base ಕ, head stroke; base ನ, head stroke, ottu ನ; base ಡ, head stroke | ಕನ್ನಡ |
| 50 C9 C6 C3 | base ಕ, sign ೆ, sign ೂ, sign ೕ | ಕೋ: ೆ ೂ ೕ in NFC is ೋ |
| 50 C0 F0 | base ಕ, head stroke, arka | ರ್ಕ: the arkavattu is drawn last but read first |
| A5 73 C0 | base ಪ, aspirate, head stroke | ಫ |

## 6. Reports

A conversion gives 3 results:

- **text**: the Unicode text, with unknown codes kept as their Windows-1252 characters;
- **unknown**: each code that could not be placed, with its position: codes with no entry and no passing meaning (section 5.6), rejected codes (section 5.3), and stray head strokes, arkavattus and mahaprana strokes (section 5.4);
- **malformed**: each range of the output text that is not a valid syllable: stray marks (section 5.4) and malformed syllables (section 5.5).

A conversion is **clean** when both lists are empty. A reader MUST NOT drop a code without a report, except for `ignore` entries, and MUST NOT change unknown codes into something else. Positions in the unknown list count codes from 0. Malformed ranges count Unicode code points of the output from 0; a reader MAY report them in other units, such as UTF-8 bytes, if it says so.

These reports are what make a conversion checkable: a reader that guesses silently gives text that looks right and is wrong.

## 7. Detecting the layout

### 7.1 From the font name

When the font is known, as in a word processor document, a PDF or styled HTML, the layout comes from its name. `tables/fonts.json` holds the rules:

1. Make the **key**: keep the ASCII letters and digits of the name, lowercased, and drop everything else. `"BRH Kannada"` becomes `brhkannada`, and `Shree-Kan-0850 Bold` becomes `shreekan0850bold`.
2. Try each rule in `layout_rules` in order. A rule whose regular expression is found in the key gives its layout, which is `null` for a font that is not a legacy Kannada font. The first rule that matches decides.
3. If no rule matches, the font has no layout in this version.

A font is a **legacy font** when it has a layout, or when, without matching the first rule, it matches a rule in `legacy_without_table`; text in such a font is legacy text in a layout this version has no table for, and a converter SHOULD say so instead of passing it through. A font **draws Kannada digits** when a rule in `kannada_digits` matches; the reader then turns the Kannada digits option on (section 5.7).

The regular expressions use only syntax shared by the regular expression engines of common languages: anchors, classes, groups, alternation and counted repeats.

### 7.2 From the text

When the font is not known, as in pasted text, the layout is chosen by reading the text in every layout:

1. Convert the text in each layout, with the default options.
2. Score each conversion with 3 numbers, compared in order: the number of unknown codes plus the number of malformed ranges; then the number of ASCII letters in the output; then the number of viramas in the output.
3. Choose the layout with the lowest score. On a full tie, choose the first in the order of section 1.2.

The second number prefers a layout that reads the text as Kannada, because a layout that draws Latin (section 4.6) reads text in any other layout cleanly as English. The third number prefers fewer clusters, because legacy text read in the wrong layout often comes out as a run of clusters: ದ್ಬ್ಟ for ಅಥವಾ.

Short text can read cleanly in more than 1 layout, so the choice grows surer with length. A converter SHOULD prefer the font name when it has one, and SHOULD let the user override the guess.

### 7.3 Measured accuracy

On the 772 lines of the conformance cases, the method finds the right layout for every whole line. From the first 32 codes of each line it is right for 99.0% of Nudi B-Akshara lines, 97.4% of Kan-Eng lines and every line of the other layouts; from the first 8 codes, about 2 or 3 syllables, for 81.5% of Nudi B-Akshara and 83.1% of Kan-Eng lines, and 93.5% or more for the others. Most mistakes on short text choose Akruti for a bilingual layout. `conformance/RESULTS.md` has the details.

## 8. Conformance

Conformance is measured and reported as figures, because the expected texts keep the source documents' own typing errors and some still wait for a Kannada reader's check.

A **conforming reader**:

1. gives the expected result for every edge case in `conformance/edge-cases.tsv`, including the unknown positions and malformed ranges;
2. gives the expected text for every line of `conformance/cases/` whose status is verified or read;
3. gives the expected answer for every font-name example in `tables/fonts.json`, if it reads font names.

A converter that does not conform SHOULD still publish its figures from `conformance/run.py`, with the version of this specification and of the cases it was measured against. The cases, the protocol a converter speaks to the runner, and the figures reported are described in `conformance/README.md`.

## 9. Writing legacy text

This section describes writing Unicode back into a layout, for documents that must still be printed in a legacy font. It is informative in this version; conformance cases for it are planned for 0.2.

A writer splits the text into syllables and writes each one in the order typists stored it: the consonant shape, the vowel sign, the subscript consonants, ೃ and the length marks ೕ ೖ, the arkavattu, and then ಂ or ಃ. Entries marked `read` are never written. Where a layout has more than 1 entry for the same sign, subscript, arkavattu or mahaprana stroke, the writer uses the first entry whose preference holds for the syllable, or else the first entry with no preference. Where a layout has no entry for a subscript consonant, the writer splits the syllable before it, ending the first part with a visible virama; both read back as the same Unicode. Characters a layout cannot write, such as the zero-width joiners and the nukta, are reported.

When a written result is clean, reading it back (section 5) gives the NFC form of the input.

## 10. Versions and changes

This specification follows semantic versioning. A change that makes a conforming reader give different text for some input is a minor version before 1.0 and a major version after it. Every change to a table is listed in `CHANGELOG.md` with the evidence for it.

A proposed change to a table MUST come with evidence: the font file or a rendering of its glyphs, and lines from public documents that use the codes, added as conformance cases with their sources.
