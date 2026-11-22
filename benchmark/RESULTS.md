# Benchmark results: kannadi

Measured on 22 November 2026 with the benchmark at `5affedc` and the kannadi adapter in `adapters/kannadi`, which pins kannadi `fded282`:

```bash
cargo build --manifest-path adapters/kannadi/Cargo.toml
python3 conformance/run.py --markdown --cases benchmark/lines --out kannadi.json -- adapters/kannadi/target/debug/kle-kannadi-adapter
```

"Scored" lines are the confirmed and likely ones; "all" adds the unresolved lines, whose expected text is a best guess. Text is compared in the canonical form of the normalization profile.

| Layout | Scored lines | Exact, normalized | All lines | Exact, normalized | Character accuracy, normalized (all) |
|---|---:|---:|---:|---:|---:|
| Nudi and Baraha | 1,924 | 1,922 (99.9%) | 2,210 | 2,141 (96.9%) | 99.90% |
| Akruti | 919 | 918 (99.9%) | 953 | 952 (99.9%) | 99.99% |
| Shree-Lipi | 356 | 356 (100.0%) | 421 | 421 (100.0%) | 100.00% |
| Nudi B-Akshara | 805 | 805 (100.0%) | 1,000 | 1,000 (100.0%) | 100.00% |
| Kan-Eng | 471 | 471 (100.0%) | 514 | 514 (100.0%) | 100.00% |

Layout detection from whole lines was right on 99.0% of Nudi B-Akshara lines and 100.0% of the others. Font names: 47 of 47. Edge cases: 64 of 64.

These figures are an upper bound for kannadi: its output is a candidate for the expected text on every line, and the only candidate for Nudi B-Akshara (see [Limitations](README.md#limitations)). The reader check in [README.md](README.md#reader-check) will bound how far that matters.
