# FolE2 handoff and verification

The completed one-paper research conversion is `FOLE2_NUMERICAL_CASE_001.md`.
`fole2_numerical_cells_001.json` contains reported operands, derived numerical
cells, explicit unknowns and their meanings. `source_and_reset_provenance_001.json`
records the source identities and all 15 authority documents reread in full.
`primary_figure3.jpg` is the inspected primary figure. No other primary paper or
previous paper-summary packet was opened.

The case provides two bounded numerical response calculations: a measured
metal-condition ratio and a substrate-condition ratio evaluated from the
reported kinetic parameters. It identifies each numerator and denominator,
keeps those two protocols separate, and records which uncertainty and isolation
operands are absent. No new transfer model was fitted or adopted.

The check executed was:

```
python3 research/experimental_scoring_review_2026-10-23/a105_fole_case_006/check_fole2_arithmetic_001.py
```

Result: **PASS: 7 arithmetic and missing-data groups**. These cover relative-unit
conversion, response reconstruction, common-reference cancellation, kinetic
units and model evaluation, shared-parameter derivatives, nondetection and
replication meanings, and correspondence/occupancy limitations. The finite
difference step in the checker is only a numerical-analysis step; it is not an
experimental uncertainty. These checks validate calculations and retained
unknowns, not the completeness or scientific validity of a general scoring
policy.

## Additive source-location correction

The “Kinetic values, metal-content qualification” row in
`FOLE2_NUMERICAL_CASE_001.md` names retained-text lines **394–395**. The precise
locations are **395–396**: line 394 is the Fig. 3 caption, line 395 is the kinetic
result, and line 396 is the metal-content paragraph. The named section and all
numerical operands remain unchanged. This correction preserves the original
record.

Mechanical source-location verification also confirmed the Table 2 heading at
line 347, Fig. 3 at line 392, the structural-search paragraph at line 649, and
the comparison-subsection heading at line 650. The primary HTML contains both
the `t2` and `f3` anchors used by the report's links. This verification retrieved
locator numbers and anchor-presence flags only; it did not introduce another
paper or new experimental observations after the authority reset.

## Inspection and authority scope

The retained primary text was inspected at lines 310–460 and 600–677, including
the complete relevant activity Methods, Table 2, Fig. 3 caption, kinetic/metal
results and relevant structural comparisons. The Fig. 3 image was separately
downloaded and visually inspected. The paper's webpage was opened for source
verification. The full supplement, all crystallographic statistics, referenced
earlier assay/purification paper and raw assay records were not inspected.

The initial authority read contained one truncated combined output; the affected
episode-structure and time-estimation portions were then read in complete
sequential portions. The **post-paper** reset had no truncated output and covered
all 15 full documents from 00:48:12 to 00:48:32 UTC on 2026-10-24 (local task date
2026-10-23). The latest human goal attachment was read last. Hashes identify the
actual files. The source-free mapping/correspondence proposals supplied existing
unadopted interfaces; they were not treated as adopted score policy.

Only new files within `a105_fole_case_006/` were written. No production code,
reader/grader implementation, prompt, library publication, scientific run,
previous record or permanent record was changed. No scoring sheet was marked
complete. Essential missing source-reliability, target-correspondence and
uncertainty inputs remain visible for the parent's A105 sheet integration.
