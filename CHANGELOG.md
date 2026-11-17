# Changelog

## Unreleased

- Licenses: tables, schema, tools, tests, the reference reader, the conformance runner and the adapters are under MIT OR Apache-2.0, and the prose under CC BY 4.0, with "The Open Kannada Authors" as copyright holder. `NOTICE.md` names the license of every directory, `REUSE.toml` that of every file, and `TRADEMARKS.md` says how the names may be used.
- The Shree-Lipi conformance lines are 140 lines written for kannadi and encoded with its table, in place of 130 lines of Udayavani newspaper pages. A new status, `written`, marks them, and the headline figures count it with `verified` and `read`. Cases copied from kannadi 3148ffb.
- Contributions are signed off under the Developer Certificate of Origin. CI checks the `Signed-off-by` line of each commit in a pull request, and runs `reuse lint`.

## 0.1.0, draft

- Specification draft: layout tables, reading rules, reports, layout detection from font names and from text, and an outline of writing back.
- Tables for 5 layouts (nudi, akruti, shree-lipi, nudi-b, kan-eng), copied from kannadi at commit c786820, as TSV and JSON, with a JSON Schema.
- Font-name rules with 47 examples.
- Conformance: 772 lines from public documents in 5 layouts, 64 edge cases that reach 32 rules of the reading and detection steps, a runner with a line-based JSON protocol, a differential tester, a Python reference reader written from the specification, and an adapter for kannadi. The reference reader and kannadi give the same response to every request.
- Detection accuracy measured from whole lines and from 8, 16 and 32 codes (section 7.3).
