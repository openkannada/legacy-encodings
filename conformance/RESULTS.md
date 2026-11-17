# Results

Measured on 17 November 2026 with the cases copied from kannadi c786820.

## Reference reader and kannadi

The Python reference reader (`reference/kle.py`), written from the specification, and kannadi give the same response to every request: 3,709 of 3,709, counting text, unknown positions, malformed ranges, detected layouts and font answers. On random code sequences with random options (`differential.py`, 5 seeds of 3,000 sequences per layout), 82,500 of 82,500 responses are the same. Both conform to section 8.

| Layout | Lines | Exact | Character accuracy | Clean | Layout found, whole line | First 8 codes | First 16 codes | First 32 codes |
|---|---|---|---|---|---|---|---|---|
| nudi | 12 | 12 (100.0%) | 100.00% | 12 | 100.0% | 100.0% of 12 | 100.0% of 12 | 100.0% of 12 |
| nudi, all statuses | 209 | 209 (100.0%) | 100.00% | 208 | 100.0% | 99.0% of 209 | 100.0% of 209 | 100.0% of 209 |
| akruti | 125 | 125 (100.0%) | 100.00% | 125 | 100.0% | 93.5% of 124 | 99.2% of 119 | 100.0% of 105 |
| shree-lipi | 130 | 130 (100.0%) | 100.00% | 130 | 100.0% | 98.5% of 130 | 100.0% of 130 | 100.0% of 107 |
| nudi-b | 190 | 190 (100.0%) | 100.00% | 190 | 100.0% | 81.5% of 189 | 95.4% of 173 | 99.0% of 96 |
| kan-eng | 118 | 118 (100.0%) | 100.00% | 118 | 100.0% | 83.1% of 118 | 95.9% of 97 | 97.4% of 39 |

A snippet column counts the lines longer than the snippet.

Font names: 47 of 47. Edge cases: 64 of 64.

### Reading these figures

- The text figures cannot measure kannadi's accuracy: its tables were corrected until it read these lines as they were read against the glyphs, and the pending and unchecked Nudi lines are its own output. With the edge cases and the random sequences, they show that the specification describes kannadi completely for input given as glyph codes, and they set the bar for other converters. Accuracy in the usual sense waits for a Kannada reader's check.
- The 1 Nudi line that is not clean has a glyph, F5, whose meaning is an open question in kannadi's corpus.
- Detection is measured fairly: the method does not use the expected text.

### Detection from short text

From a whole line, the layout is right for all 772 lines. From the first 8 codes, about 2 or 3 syllables, these are the mistakes, as the right layout and the one chosen:

| Right layout | Chosen | Snippets |
|---|---|---|
| nudi-b | akruti | 27 |
| nudi-b | nudi | 6 |
| kan-eng | akruti | 8 |
| kan-eng | shree-lipi | 5 |
| kan-eng | nudi-b | 4 |
| kan-eng | nudi | 3 |
| akruti | nudi | 5 |
| others | | 9 |

At 16 codes, 13 snippets are wrong, 11 of them read as Akruti; at 32 codes, 2 are. The bilingual layouts are the hard ones: a few of their syllables often also read cleanly as Akruti.

## Other converters

Not measured yet. Any converter can be measured by writing a small program for the protocol in [README.md](README.md).
