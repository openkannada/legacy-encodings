# Sources for the layout tables

The Nudi table (`tables/nudi.tsv`) comes from kannadi, which identified each glyph code by rendering the Nudi 01 e font and checked the readings against Karnataka government pages of 2002. This folder holds 2 checks of that table against sources that are independent of kannadi and of KaGaPa's code.

## The 2003 Unicode proposal, L2/03-068

[L2/03-068](https://www.unicode.org/L2/L2003/03068-kannada.pdf), "UNICODE for Kannada", was issued by the Directorate of Information Technology, Government of Karnataka, in February 2003. It names the Government's 8-bit coding, KSCLP (Kannada Script Code for Language Processing), and its Appendix A prints every Kannada code point with its glyph set in Nudi 01 k, a Nudi font embedded in the PDF. The PDF's text layer holds those glyphs as their Nudi codes.

`tools/l2_03_068.py extract` reads Appendix A into [l2-03-068.tsv](l2-03-068.tsv): 82 code points, each with its Nudi codes. It stops at Appendix B, a code chart grid whose text layer is not kept in reading order. `tools/l2_03_068.py check` reads each row's codes with the reference reader (after ಕ for a sign) and compares the result with the code point.

| Result | Rows |
|---|---|
| Agrees with the Nudi table | 76 |
| Differs | 3 |
| Not assigned in Unicode as the proposal asked | 3 |

The 3 differences:

- **U+0CBC nukta, code F3.** The table has no entry for F3. In the Nudi 01 k fonts embedded in the PDF and in Nudi 19 e, F3 is 2 small dots below the baseline with no advance: a nukta. The table should read F3 as the nukta. kannadi's reader does not yet accept a nukta from a legacy glyph, and section 4.3 has no kind for it, so this needs a specification change.
- **U+0CC4 vowel sign ೄ, code F1.** The table has no entry for F1. F1 draws the ೃ shape (code C8) with a longer tail, the way ೄ is drawn. The table should read F1 as ೄ, as a `sign`.
- **U+0CBD avagraha, code 73.** The proposal draws the avagraha with 73, which the table reads as the mahaprana stroke. 73 has no advance and sits on the glyph before it, so it is the mahaprana stroke, and the proposal borrowed its shape. The table is right; a standalone 73 stays unknown.

The 3 rows not in Unicode are the proposal's stem glyph at U+0CBB (code C0, which the table reads as the head stroke), and diacritics it asked for at U+0CD4 and U+0CF9.

## The KGP keyboard

Nudi text was typed on the KGP (Kannada Ganaka Parishat) phonetic layout. jquery.ime's rules for it, `rules/kn/kn-kgp.js` in [wikimedia/jquery.ime](https://github.com/wikimedia/jquery.ime) (checked at commit 4853ee466fd06b072f0743c36324a45d62156263), list what each key sequence types. `tools/kgp_repertoire.py` collects every Kannada character those rules can produce and checks that the reference reader writes it from some Nudi glyph, a pair or triple of vowel sign glyphs, or a digit:

    KGP types 78 Kannada characters; the Nudi table reads 76.
      not read: U+0CBC KANNADA SIGN NUKTA
      not read: U+0CC4 KANNADA VOWEL SIGN VOCALIC RR

These are the same 2 gaps the proposal shows.

## Kannada University's Kuvempu fonts

The Kuvempu Tantramsha legacy fonts from Kannada University, Hampi, published in [sanchaya/kuvempu-fonts](https://github.com/sanchaya/kuvempu-fonts) (checked at commit 29f8e6055d77233facde25e9a7a8dbdef3d650a6; no license, so nothing of them is kept here), do not need a new layout:

- The 30 Kuvempu_Kan and Kuvempu_Eng fonts are in the Nudi layout. For every single-code entry of each table, a glyph is checked for the shape its kind needs: a subscript below the baseline, the arkavattu high with no advance, a letter on the baseline with an advance. 93% to 99% of the Nudi entries fit in each Kuvempu font, as 92% to 97% fit in Nudi 19 e and Nudi KVK e, against at most 76% for any other layout.
- The 20 Heamavathi_Brd fonts map only A to Z and a to z: border ornaments, with no Kannada.

## What is not used

KaGaPa's own mapping files are not a source for these tables: `kagapa-blr/kannada-nudi-core` is under the AGPL, and its mapping reference was not read for this work. KaGaPa's MIT-licensed KannadaAsciiUnicodeSDK is used only as a converter under test, through `adapters/kagapa`, never as a source of table entries.
