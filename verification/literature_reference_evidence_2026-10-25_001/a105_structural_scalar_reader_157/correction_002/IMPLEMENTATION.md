# Additive correction 002: soft numeric breaks

This continues workload 157 under the root's explicit correction. The earlier
157 notes, original diff, hashes, probes and test results remain historical
records. Root pin001 and its invocation were preserved. Final acceptance and
joined verification use the later pin002 bytes.

## Observed regression and correction

The first structural-space repair accepted `7` selected from `-<br>7` and
`-3` selected from `1e<br>-3`. These are clipped scalar fragments across a soft
visual break. The root required their rejection while retaining independent
numbers and signs across definite table cells, `Label<br>7`, and `7<br>9`.

`_soft_break_numeric_token` adds a separate guard over the exact original
source contexts. It runs candidate checks only when an adjacent tag run
contains an actual `br` or `break` tag. Within this guard, inline formatting
and soft break tags contribute no text; definite structural tags contribute
spaces; every actual source whitespace character is preserved. Entity decoding
follows recognition of actual tags. The normalized guard text is not a new
source representation or a scientific operand.

The guard rejects an exposed clipped sign/decimal marker, a selected decimal
fraction clipped from a preceding mantissa, and genuine numeric exponent
fragments. It does not join independent digits across breaks. An ending `e`
in a label is not an exponent without a numerical mantissa. The existing
plus/minus exception for the explicitly selected spread role is retained.
Definite cell boundaries and actual source whitespace remain separators.

The root's second review found that inline formatting inside exponent text
could obstruct the initial guard. Both actual probes accepted fragments before
the final refinement: `1<em>e</em><br>-3` selected as `-3`, and
`1<br><em>e</em>-3` selected as `1`. The final candidate normalizes inline
formatting throughout this guard's context, retaining structural spaces and
actual whitespace. Both probes now reject with
`partial_source_numeric_token`. A formatted `Rat<em>e</em><br>7` label remains
supported. No arbitrary mathematical expression parser was added.

`read_source_number` invokes this guard before accepting the existing lexical
edges. Its output schema, exact witnesses, byte offsets, numerical values,
unit conversions, qualifier meanings and caller-owned scientific meanings are
unchanged. The same direct consumers inspected in the earlier 157 record use
this unchanged reader interface. No new production file or changed consumer
was needed.

## Final evidence

- `source_fields_from_001_final.diff` contains the exact incremental production
  correction from the previously recorded 157 implementation.
- `file_hashes_final.json` binds production SHA256
  `5158e9ec97a7fa592ed4d03b81cba3e9c94a7331e35d4249df166899da0a925a`
  and targeted-test SHA256
  `02c3fc12eb862030dd195bd28b3c4d6c4cb3b25cc38a0bc3a29a66ae3ab76f9a`.
- `synthetic_before_after_final.json` contains thirteen executed synthetic
  before/after probes, including the reported failures and preserved valid
  boundaries. Earlier correction002 candidate artifacts remain alongside them.
- The final focused soft-break checks passed: 58 passed, 77 deselected in
  0.57 seconds.
- The final affected group passed: 429 passed in 43.50 seconds across the
  structural suite, existing partner scalar tests and numeric-range scope tests.
  This includes the actual selected partner operation, ordinary typed parent
  receipt and reopened Store with scientific sources/parsers/calculators
  disabled before binding reconstruction. No cached catalog substitutes that
  reconstruction.

The intermediate correction002 group passed 416 tests before review found the
inline exponent hole; that pass is retained as intermediate evidence rather
than final acceptance. The earlier six-file 476-test group applies to the first
157 implementation. These groups overlap; their counts must not be summed or
counted as assays. Root joined final verification is a separate record.

All added sources and probes are synthetic. No original paper, retained
paper-specific packet or private model/provider data was inspected. No live
scientific investigation was restarted, source number rewritten, scientific
credit invented, controller changed, or frozen binding fingerprint bypassed.
