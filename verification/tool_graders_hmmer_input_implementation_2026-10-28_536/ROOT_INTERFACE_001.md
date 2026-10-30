# HMMER input implementation ports, first coding assignments

This records implementation boundaries under the original user goal. It does
not change that goal or declare a format, resource or episode path complete.
Packet 534's SHARED_INTERFACE.md, SOURCE_MAP.md and VERIFICATION_CASES.md define
the input meanings; the clarifications here freeze the first independent coding
assignments. Existing scoring, weights, MAP calculation and saved observations
remain owned by their existing implementations.

## Files and dependencies

- Alphabet owner: new `hmmer_alignment_input_alphabet.py` and
  `tests/test_hmmer_alignment_input_alphabet.py`. Implement exactly
  `classify_easel_alphabet_counts(counts: list[int]) -> dict` and
  `infer_hmmer_alignment_alphabet(content: bytes, *, declared_format: str) -> dict`
  with packet 534's AlphabetProbe, rule enum and source-byte scanners. No sheet,
  weighting, row-decoding, driver or projection edits.
- FASTA owner: new `hmmer_alignment_input_fasta.py`, shared primitive module
  `hmmer_alignment_input_types.py`, and
  `tests/test_hmmer_alignment_input_fasta.py`. Implement exactly
  `decode_native_fasta_alignment(content: bytes, *, declared_format: str,
  alphabet: str) -> dict` for `afa` and `a2m`, returning packet 534's DecoderBatch.
  Do not implement other format state machines or numerical calculations.
- Root owns the later source-to-existing-sheet adapter, saved-fact validation,
  shared-calculator consumption and native-driver integration. Neither coding
  owner changes existing production files. Other format readers get separate
  ownership after these same output ports, not separate scoring definitions.
- Both assignments can be authored independently. Their only shared code
  dependency is the primitive API below, implemented by the FASTA owner.
  Tests and native verification run only in root-selected bounded lifecycle
  jobs, never by importing application modules on the host.

## Frozen primitive API

`hmmer_alignment_input_types.py` has no imports from other application modules.
It provides:

```python
class NativeAlignmentLine(NamedTuple):
    number: int          # one-based
    byte_start: int      # zero-based inclusive
    content_end: int     # excludes LF or CRLF
    byte_end: int        # includes LF or CRLF, otherwise equals content_end
    data: bytes          # original content[byte_start:content_end]

iter_native_alignment_lines(content: bytes) -> Iterator[NativeAlignmentLine]

alignment_input_diagnostic(code: str, *, record_ordinal=None,
    row_ordinal=None, event_ordinal=None, byte_start=None, byte_end=None,
    expected=None, actual=None, token_hex=None) -> dict
```

The iterator recognizes LF and CRLF only. Bare CR, VT, FF and other bytes remain
data. It emits a final unterminated nonempty line, and emits no phantom line
after a final terminator. Empty content yields no lines. It does not decode
Unicode or use general splitlines. It validates `content` is bytes.

Event raw text and locator spans include original terminators. Segment spans
include only their actual source symbols/ignored data, never line terminators.
`raw` is reversible UTF-8 with surrogateescape. Source name bytes, physical
columns and byte counts are never replaced by decoded-text character counts.

Diagnostic has exactly packet 534's seven fields. `details` is a closed object
with exactly `expected`, `actual`, `token_hex`: expected/actual are null, integer
(not bool), or string; token_hex is null or a lower-case even-length byte hex
string. No prose findings, arbitrary object fields or runtime identities.
Code supplies the meaning. Initial closed diagnostic codes are:

```
invalid_header missing_name invalid_name_byte invalid_sequence_byte
row_count_mismatch row_order_mismatch column_count_mismatch
block_geometry_mismatch annotation_order_mismatch
annotation_cardinality_mismatch missing_consensus_line
a2m_consensus_count_mismatch psiblast_case_conflict
phylip_dimension_invalid native_source_semantics_unestablished
empty_alignment empty_sequence
```

Argument misuse raises ValueError with one of these exact strings:
`hmmer_alignment_content_invalid`, `hmmer_alignment_format_invalid`,
`hmmer_alignment_alphabet_invalid`, `hmmer_alignment_counts_invalid`, or
`hmmer_alignment_diagnostic_invalid`. Malformed scientific bytes return
structured diagnostics and partial/invalid records rather than argument errors.
Future diagnostic additions must be explicit shared-contract additions.

## Frozen record meanings

Use the exact packet 534 DecoderBatch and AlphabetProbe key sets. Sequence and
row ordinals start at zero. Each event is ordered within its record. Line
positions are one-based; byte, physical-column and aligned spans are zero-based
half-open. `next_byte_offset` includes any line already consumed, but excludes
an unread/lookahead line. Partial records never become complete alignments.

The inferred state is a source-derived decoding fact, not an observed native
execution or a scientific confidence score. No flag is inserted into selected
settings. The inference scans original bytes independently from row parsing;
in particular it can examine later Stockholm records or a PHYLIP continuation
region that a first-record parser does not interpret the same way.

All low-level readers require an explicit actual alphabet. A2M O/o behavior,
consensus counts, insert expansion and generated RF follow the inspected native
source. The unresolved lowercase-o source contradiction returns unavailable
geometry and an explicit source-semantics diagnostic; it is not silently fixed.
Format-defined insert expansion records generated gaps with null source spans;
it never pads a failed alignment. Duplicate names retain separate row ordinals.

The decoder's `native_status_equivalent` is 0, 3, 7 or null, supported by source
semantics. All eight readers translate digital sequence errors to status 7.
Alphabet-open 26, runtime allocation/I/O failures and actual process returncodes
remain separate. Native status 0 cannot override invalid geometry.

Neither first-wave module opens paths, acquires data, launches commands, calls a
model, reads a Store, supplies native provenance, awards credit, normalizes
weights, calculates MAP or mutates earlier sheets. No compiler/native oracle is
part of production. Root will verify the new pure paths against actual retained
native sources and artifacts before integration/closure claims.

## Verification handoff

Alphabet cases are packet 534 A01-A08, including per-format byte regions,
whole-line strict thresholds and EOF inference. FASTA cases are N02-N04/N13/N14
with authentic retained A2M emissions read unchanged; generated edge cases are
explicit test inputs, not measurements. Each owner supplies expected values,
failure reasons, source anchors, full owned diff and exact test selectors.
Tests are written but not run on the host. No source availability, standalone
test or parser handoff is counted as a complete scientific operation.

After each tool/substantial source examination, every owner rereads the original
attachment's objective and all ten operating principles verbatim, then the
current contract. Historical source and goal records remain unchanged.
