# BV-BRC feature-to-sequence supplied-sheet verification

This directory verifies D3's pure `extract_feature_sequence_join` and its
interface to the independently owned D2 reader and count calculator. It does
not establish a live v2 acquisition, host custody admission, a selectable
child-owned production binding, or episode delivery. No network request, job,
LLM call, service/runtime/prompt edit, or accounting change was made by D3.

The original contract is
`docs/TOOL_GRADER_BVBRC_DATA_CONTRACT_2026-10-24_001.md` and its frozen
`CONTRACT_SHAPES.json`. Additive correction002 removes `supplied` from native
`CellLocation.source_level`; it does not change feature-to-sequence semantics.
The original contract artifacts remain unchanged. Production imports static
schema/field constants; it never reads this directory or the contract documents.

`NATIVE_DECODER_SHEETS.json` contains complete sheets from the production D2
native payload decoder, using the retained historical array responses. The
explicit prepared field/population descriptors are test inputs: their historical
request does not match a v2 request, so `request_matches=false` and the diagnostic
remain intact. These sheets are native-decoder evidence, not qualified host
results. `SUPPLIED_SHEET_FIXTURES.json` separately records the original test-only
sheet construction, with synthetic custody/population/prepared metadata labeled
inside its envelope. It is not evidence that that builder is a production parser.

`FILLED_EXAMPLES.json` contains the real native-derived join, its separately
calculated components, explicit expected counts, the lowercase/uppercase MD5
comparison, and labeled synthetic missing/conflict/repetition cases.
`REPORT.json` records the actual checks, commands, file hashes, and remaining
integration work. Exact SHA-256s refer to the bytes present at verification time.

Numerical meanings remain separate:

| Quantity | Meaning and missing behavior |
| --- | --- |
| `sequence_length` | Character count of the exact supplied string; null when candidate strings are missing or candidate lengths disagree. No trimming, case conversion, translation, or coordinate-derived substitute. |
| `feature_length` | The corresponding native nonnegative integer `aa_length` or `na_length`; null for absent, unselected, null, invalid, or unrepresentable values. Units follow the requested AA/NA kind. NA does not establish DNA versus RNA. |
| `raw_md5_match` | Exact ASCII bytes hashed by MD5 and compared to the exact recorded key; nullable when unavailable or candidate checks disagree. This is a byte check, not biological identity confidence. |
| `length_match` | Equality of the two unambiguous available lengths; null if either length is unavailable or conflicting. Per-candidate mismatch issues survive conflicts. |
| `input_page_counts` | Retained/valid row counts for each distinct `(native_sha256, collection)`, including unjoined sequence rows. Repeated delivery does not add rows. |
| Separate D2 components | Selected features, selected feature occurrences, all supplied sequence rows, distinct joined AA/NA hashes, joined/repeated relations, missing-key/record relations, conflicts/type mismatches, and joined length agreements. These describe the supplied pages, without a population denominator or confidence score. |

Every selected feature occurrence owns one edge for each requested kind. Exact
PATRIC and RefSeq endpoints remain distinct when their hash agrees. Repeated
identical sequence rows retain separate row/cell locators. Conflicting values
remain candidates with no first-row choice. Source strings and all selected
feature metadata remain in the supplied sheets; a later explicit projection
owns which cells reach the receiver. Coordinate/strand/segment metadata is
preserved without assuming genomic span equals sequence length.

Missing features, missing keys, missing pages, missing referenced records,
unavailable sequence text, incompatible types, and invalid/conflicting values
retain separate statuses/reasons. Acquisition requirements describe exact IDs
and kinds as data. The extractor never executes those requirements. Malformed
sheet structures and forged locators raise `ValueError`; meaningful partial
native data remains usable. Host source/custody verification is a separate,
unimplemented boundary for this isolated workload.
