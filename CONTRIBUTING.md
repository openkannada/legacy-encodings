# Contributing

Changes to the specification, a table entry, a new layout or a new test line start as a GitHub issue; see [Proposing changes](README.md#proposing-changes). A table change starts in [kannadi](https://github.com/openkannada/kannadi), with its evidence, and is copied here with `tools/tables.py sync`.

Before asking for review, run:

```bash
python3 tools/tables.py check
python3 -m unittest discover -s tests
```

## Test lines

Lines from public documents are short excerpts with their source URLs. Do not add newspaper or other commercial text. For a layout with no public document that can be kept, write the lines yourself and encode them with the layout's table, as kannadi's Shree-Lipi lines are made.

## Sign off your commits

Every commit needs a `Signed-off-by` line with your name and email. It says that you wrote the change, or have the right to submit it, under the [Developer Certificate of Origin](https://developercertificate.org/). Git adds it for you:

```bash
git commit -s
```

There is no contributor license agreement. You keep the copyright in your contribution, and it is licensed like the files it changes: MIT OR Apache-2.0 for tables, schema, tools, tests, the reference reader, the conformance runner and the adapters, and CC BY 4.0 for the specification and other prose. A check on each pull request fails if a commit has no `Signed-off-by` line. To add the line to commits already on your branch, run `git rebase --signoff origin/main`.
