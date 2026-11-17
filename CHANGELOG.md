# Changelog

## 0.1.0, draft

- Specification draft: layout tables, reading rules, reports, layout detection from font names and from text, and an outline of writing back.
- Tables for 5 layouts (nudi, akruti, shree-lipi, nudi-b, kan-eng), copied from kannadi at commit c786820, as TSV and JSON, with a JSON Schema.
- Font-name rules with 47 examples.
- Conformance: 772 lines from public documents in 5 layouts, 52 edge cases that reach every reading rule, a runner with a line-based JSON protocol, a differential tester, a Python reference reader written from the specification, and an adapter for kannadi. The reference reader and kannadi give the same response to every request.
- Detection accuracy measured from whole lines and from 8, 16 and 32 codes (section 7.3).
