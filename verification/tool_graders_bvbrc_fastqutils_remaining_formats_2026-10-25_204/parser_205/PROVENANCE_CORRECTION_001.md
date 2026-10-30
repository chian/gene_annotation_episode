# Additive helper-fixture provenance correction

The first direct-helper tests and `evidence_001` passed bare, genuine Cutadapt
stdout to the embedded helper through a synthetic outer `_Report` context
labelled Trim Galore 0.6.10. Those numerical bytes were actually produced by
Cutadapt 4.9; they were not standalone Trim Galore report artifacts. The genuine
Trim Galore fixture was correctly identified and used the full outer parser.

The corrected tests and new `evidence_002` identify bare helper input as
`native_text`, producer `Cutadapt`, version `4.9`. The helper accepts an already
constructed `_Report`; this direct port test does not add or claim a supported
standalone format in production dispatch. The genuine enclosing report remains
`trim_galore_report_0_6_10`, producer `Trim Galore`, version `0.6.10`, and its
embedded version label is `4.9`.

The scoped-version purity test now uses the complete genuine enclosing Trim
Galore bytes and their original embedded byte interval. Handcrafted
concatenation and multibyte-prefix fixtures are explicitly handcrafted.

`evidence_001` and its generator remain unchanged as history. Use
`evidence_002/manifest.json` and its bound examples for the corrected handoff.
The parser implementation did not change for this correction. The final
focused run passed 77 tests in 7.38 seconds.
