# Additive review correction 002: B1 precision and unqualified witness links

This correction supersedes only the specific statements identified below in
`CONTRACT_PROPOSAL_001.md`. Proposal001, its schema, filled examples, 43-check
receipt and hashes remain unchanged historical design artifacts. This remains
design work; no production code is installed. Root owns B0; a later fresh worker
can implement the five B1 functions independently after root freezes this
correction. No B2 or producer work is required to implement B1.

## Missing execution-witness interface

Root correctly identified a gap: proposal001 says B2 compares decoded
execution/occurrence witnesses, but `ExecutionInputLink` and
`NativeProteinLink` carry only source locators and `build_native_joins` has no
parameter for the decoded witness values. The locator is insufficient.

**Resolved boundary for this revision: those links remain unqualified.** This
correction does not invent a producer wire format or accept caller statements
as execution evidence. No declared witness parameter/reader exists yet.

Until a separately reviewed decoded-witness interface exists:

1. Preserve a requested `ExecutionInputLink.relation=exact_executed_fasta` in
   `NativeJoins.execution_links`, but do not admit it as a qualified execution
   relationship. Its `TrackInputBinding.execution_relation` is `unknown`,
   membership is `unknown`, and input_record_count is missing, with
   `execution_witness_interface_unavailable`. Matching SHA/byte count and
   nonempty witness locators do not change this result.
2. Preserve a requested `NativeProteinLink.basis=producer_occurrence_mapping`
   or `ProteinMetadataLink.basis=producer_occurrence_mapping`, but do not admit
   it on that basis. The applicable join remains `ambiguous` when multiple
   candidates exist, otherwise `not_supplied`/`unmatched` for native joins or
   `unmatched` for metadata joins, with
   `occurrence_witness_interface_unavailable`. It cannot contribute a joined
   protein occurrence merely because a source field is present.
3. A unique exact ID can establish a structurally consistent link to the
   explicitly supplied inventory/metadata occurrence under the existing B2
   checks. It is still qualified by that input's actual relation
   (`original_supplied_fasta`, `later_snapshot`, or `unknown`); it is not proof
   of the executed input. Exact-execution denominators stay unavailable.
4. Missing witness capability does not block native record counts, preserved
   finite native fractions, postfilters over those recorded fractions, or B1
   extraction. It blocks only claims requiring the absent execution/occurrence
   proof. Numeric examples in proposal001 with known exact denominators are
   **conditional arithmetic examples for the future qualified interface**,
   not cases the currently proposed B2 signature can establish.

The future interface must accept decoded, source-bound facts for the exact
original input slot/value, executed FASTA binding and membership, plus the actual
emitted-row-to-executed-occurrence relationship where duplicates were involved.
Its source-specific reader and API custody must be defined separately. That
is an exact remaining contract dependency, not a new acquisition or permission
request. No new placeholder `validated=true` field is introduced here.

`DATA_SHAPES_PROPOSAL_002.json` adds the two diagnostic/requirement codes above.
It otherwise preserves the B2 link input shapes so claims remain inspectable;
their admissibility follows this corrected boundary. Do not use proposal001's
more permissive prose to infer proof from those old fields.

## B0 validation responsibility

Root owns B0 and its production files. `validate_proteome_data` checks saved
shape and structural/cross-record relationships: finite types, presence/value
consistency, unique identities/ordinals, source-field references, canonical
keys, exact copied-cell equality, array bounds, matching saved identifiers and
content bindings, and consistency of admitted versus unresolved references.
Counts describing stored arrays may be checked against those arrays. Checking
the digest/length of a saved normalized string is data-integrity validation,
not a claim that it reproduces source bytes.

The validator **does not read or reparse source artifacts, rerun parsers or
calculators, repopulate a sheet, create or select scientific joins, acquire data,
execute scientific software, or decide whether a biological interpretation is
true**. In particular, replace proposal001's phrase “recomputed sheet-derived
state” with “consistency of saved state and its declared structural
dependencies.” Numerical formula correctness belongs to the calculator and its
independent arithmetic verification. A saved B2 claim requiring the unavailable
witness interface cannot be admitted by B0 because its pointers look plausible.

## B1 signatures remain unchanged

```python
def read_protein_fasta(content: bytes, *, source: dict,
    declared_format: str, inventory_key: str) -> dict: ...

def read_feature_metadata(content: bytes, *, source: dict,
    declared_format: str, snapshot_key: str, population: dict,
    coordinate_convention: dict) -> dict: ...

def read_genome_metadata(content: bytes, *, source: dict,
    declared_format: str, snapshot_key: str, population: dict) -> dict: ...

def read_feature_sequences(content: bytes, *, source: dict,
    declared_format: str, snapshot_key: str, population: dict) -> dict: ...

def index_original_inputs(original_task: dict, *, parameter_source: dict,
    source_contract: dict) -> dict: ...
```

Return names, fields, consumer handoffs and declared format names remain as in
proposal001. The following precision applies to their new implementation.

## Metadata identity and validity

Each record keeps its original ordinal and all declared cells, including when
invalid. No row or field is dropped to make an identity unique. Identifiers are
case-sensitive, unmodified source strings. A usable identity is a string with
at least one non-whitespace character. Do not trim whitespace to create a
different identity, infer an identifier from a display name, impose a biological
ID regex, or require both names when the source supplies only one.

| Record | Identity required for `valid=true` | Other required data |
|---|---|---|
| `FeatureRecord` | At least one usable `feature_id` **or** `patric_id`. If both are present, retain both; neither supersedes the other. | No genome, annotation, product, coordinate, family, length or sequence field is required merely to retain a valid identifiable feature record. |
| `GenomeRecord` | A usable `genome_id`. | `genome_name` and `taxon_id` are optional; missing taxon is not taxon zero. |
| `FeatureSequenceRecord` | A present `md5` string containing exactly 32 hexadecimal characters. | A present, complete, nonempty amino-acid `sequence` with the accepted symbols. The caller's selected profile declares aa; no inference from composition. |

`valid=true` additionally requires the record to be an object and every present
recognized field to meet its declared type/range. Omitted, explicit-null and
blank optional fields are missing states, not fabricated values. A missing
required identity or invalid recognized field sets `valid=false`; valid other
cells survive. Unrecognized fields remain in the original bytes and the exact
unsupported-path list; they do not provide identity or numerical values to this
profile. Unknown fields alone do not invalidate a record's known cells.

`md5` and `aa_sequence_md5` values preserve original case/spelling in NativeString.
Hexadecimal comparison is case-insensitive; computed digests are lowercase.
`aa_sequence_md5` is optional on a feature; a nonblank supplied value must have
the same 32-hex form. A feature record need not have sequence bytes to remain
valid. A valid format MD5 differing from the digest of its supplied complete
feature-sequence text is a `sequence_digest_conflict`, not a reason to overwrite
the source identifier. The record is invalid for that sequence identity, with
all values and computed digests retained. A matching MD5 alone is not evidence
that two features are the same feature.

Strings remain strings; JSON numbers/bools are not coerced to string IDs.
Numerical JSON tokens and strictly numeric decimal strings may populate numeric
cells with their exact native lexeme, as in A. Booleans, NaN/Infinity,
unit-bearing strings, unsupported overflow and nonzero underflow are invalid.
The original scalar remains recoverable in the retained bytes.

| Numeric metadata field | Rule; missing behavior |
|---|---|
| Feature `aa_length` | Finite integer >=0. Zero remains an explicit native zero; do not require a biologically plausible minimum or infer it from coordinates. Missing stays missing. |
| Genome `taxon_id` | Finite integer >0 when supplied. Zero, negative and fractional values are invalid native taxon identifiers, not inferred alternate taxa. Omitted/null/blank remain missing. |
| Feature `start`, `end` with unknown convention | Finite integers; preserve signed/zero values without converting them. Add `coordinate_convention_unknown`. Do not infer a coordinate system from values. |
| `start`, `end` with documented `one_based_closed` | Finite integers >=1. Retain ascending or descending endpoint order; do not assume strand or swap endpoints. |
| `start`, `end` with documented `zero_based_half_open` | Finite integers >=0; when both are present require end>=start. Empty intervals are not rejected merely by this extractor. Retain strand separately. |

A known coordinate convention needs its existing supporting source fields.
An unsupported convention invalidates that supplied convention argument; it
does not authorize choosing another one. Coordinate disagreements remain local
invalid fields/record diagnostics. No unconditional end/start ordering,
triplet-multiple, known taxonomic lineage, CDS-only feature filter, minimum
protein length, contig match or function assignment is added.

For optional native strings, blank/null/omitted retain their separate A presence
states. For a JSON record that is not an object, keep its original row ordinal
with invalid fields and a scoped record diagnostic; a scalar neighbor does not
delete usable records. Duplicate JSON members are still a fatal document error;
there is no first/last-member selection.

## FASTA header and byte interval definition

The declared profile uses LF or CRLF physical line endings. `>` at the first
byte of a physical line starts a record. `byte_start` is the zero-based physical
byte offset of that **leading `>`**, and `byte_end_exclusive` is the byte offset
of the next record's leading `>`, or the received object's end for the last
record. Header and sequence line terminators inside that interval belong to
that record. Offsets are byte offsets, not Unicode character offsets.

`header` is exactly the decoded text **after the leading `>`**, excluding its
one LF or CRLF terminator. Preserve all whitespace in that text. For tokenizing
the header, whitespace is ASCII space, tab, vertical tab, form feed and carriage
return; the excluded LF is never a token character. Find the first nonempty run
of non-whitespace characters after any leading whitespace. That run is the
identifier. `description` is the complete remainder of `header` immediately
after that token, **including its separating and trailing whitespace**. Do not
strip it. With no remainder, description is `""`; with no identifier, identifier
and description are null. Keep the header even when it contains no usable ID.

Example: the bytes `>  dup  first description\t\r\n` yield:

```json
{"header":"  dup  first description\t", "identifier":"dup",
 "description":"  first description\t", "byte_start":0}
```

A complete but empty/whitespace-only header is invalid as an identifier. It is
retained, not replaced by `untitled`. Duplicate identifiers remain separate
record occurrences.

For an incomplete final header, or a header that cannot be decoded from its
retained complete bytes, `header` may be null rather than an invented empty or
partially completed header. `DATA_SHAPES_PROPOSAL_002.json` makes this field
nullable. A complete empty header still uses the actual empty string. Identifier
and description must be null whenever header is null. Complete malformed UTF-8
document handling remains explicit invalid input; the null possibility also
permits retained incomplete-record information without inventing text.

## Complete invalid sequence retention

This is a precision of proposal001, not a new biological scoring rule.
Sequence normalization removes only ASCII whitespace (space, tab, LF, CR,
vertical tab, form feed) and uppercases **ASCII a–z only**. It performs no Unicode
case folding, residue substitution, stop/gap removal, translation or inference.
The accepted nonempty sequence alphabet remains
`ACDEFGHIKLMNPQRSTVWYBXZJUO*`.

For **every complete decodable record**, including an empty or illegal sequence:

- retain the entire normalized `sequence` string;
- set `sequence_symbol_count=len(sequence)` in decoded Unicode codepoints;
- retain SHA256 and MD5 over `sequence.encode('utf-8')`;
- set `valid_sequence` from nonempty accepted-alphabet validity;
- retain a specific empty/invalid sequence diagnostic where needed.

For valid aa records this is exactly the former ASCII-byte digest/count
definition. For complete invalid records this explicitly preserves illegal
characters rather than disguising them as missing data. An illegal non-ASCII
symbol has no asserted amino-acid coordinate meaning. No count/digest from an
invalid record supplies a valid protein length or sequence-equivalence group.
Raw bytes remain bound separately, so normalized text is not the only retained
input. MD5 is used only for exact source-key comparison; SHA256 and actual full
sequence equality underpin demonstrated sequence grouping.

Examples:

| Complete sequence input | Retained normalized sequence | Count | valid_sequence |
|---|---|---:|---|
| `acde` | `ACDE` | 4 | true |
| `AA-?1` | `AA-?1` | 5 | false |
| no sequence text | `""` | 0 | false |

The latter two still have the actual hashes of those strings. Do not replace
their values with null. By contrast, an **incomplete record** has null sequence,
symbol count and both digests, because a visible prefix is not a complete
sequence. Its raw byte interval remains retained. A next complete header can
close the preceding record; the final record requires complete body and
`object_complete=yes` to be complete. No EOF/newline heuristic upgrades unknown
object completeness.

`observed_header_count` counts recognizable record-start markers, including
invalid/partial header records. `complete_record_count` counts closed record
intervals, including complete invalid records. `valid_complete_record_count`
counts complete records with a usable identifier and `valid_sequence=true`.
Only those valid complete records enter `sequence_groups`. Duplicate-ID groups
include each record with that known identifier, even if its sequence is invalid.
These are supplied-input inspection counts, never an executed-proteome
denominator. Header lines inside a sequence start another record; do not join
them back into an earlier sequence to repair malformed input.

## Numerical and verification additions

`B1_PRECISION_EXAMPLES_002.json` gives complete byte-bound synthetic input
examples and expected retained fields, explicitly **not outputs of an
implemented B1 reader**. It includes a complete illegal sequence with its full
digest/count, an empty sequence, exact whitespace-preserving header fields and
byte intervals. These are constructed input examples, not fabricated native
GenomeComparison/BLAST reports.

`VERIFICATION_002.json` records schema closure, retention arithmetic, validation
cases, and unchanged proposal001 hashes. Validation remains contract-shape and
literal arithmetic checking. No B1 parser, B2 join, B3 sheet builder, production
calculator, native scientific program or episode integration ran here.
