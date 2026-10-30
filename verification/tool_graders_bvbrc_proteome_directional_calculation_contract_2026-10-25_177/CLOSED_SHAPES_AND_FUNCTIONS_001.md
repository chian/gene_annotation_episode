# Proposed closed numerical interfaces — 177/001

**Current interface revision:** read the additive
[INTERFACE_CORRECTIONS_002.md](INTERFACE_CORRECTIONS_002.md) for required explicit
rendering parameters, the explicit subject key, and semantic-validation context.
It supersedes the affected001 signatures and Issue shape below.

This is a schema specification for review, not executable production code. All
objects below are **closed** (`additionalProperties:false`), all listed fields
are required, and nullable fields are written explicitly. Array order is native
order except merged intervals/unique pairs, which use the specified coordinate
order. Arbitrary formula expressions, arbitrary measurement names, freeform
model judgments and arbitrary metadata maps are not accepted.

The mathematical definitions and qualification rules in
[DIRECTIONAL_NUMERICAL_CONTRACT_001.md](DIRECTIONAL_NUMERICAL_CONTRACT_001.md)
are part of each field's semantic validation. Implement ordinary deterministic
functions for those definitions; this document is not a second runtime scoring
language.

## 1. Public signatures and responsibilities

```python
# New bvbrc_proteome_directional_sheet.py: extraction/copying, no scoring.
def build_directional_sheet(directional_results: list[dict]) -> dict:
    """Return DirectionalSheetResult; retain every valid reader result in order."""

# New bvbrc_proteome_directional_calculators.py: pure numerical functions.
def calculate_directional_components(sheet: dict, *, parameters: dict) -> dict:
    """Return DirectionalComponentsResult from a DirectionalSheet."""

# New bvbrc_proteome_directional_geometry.py: reusable BLASTP-only primitives.
def calculate_protein_block(
    block: dict, *, key: dict,
    query_length: dict, subject_length: dict,
    amino_acid_alphabet: str,
) -> dict:
    """Native TraceBlock + native length cells -> BlockComponents."""

def union_position_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """Valid zero-based half-open intervals -> sorted merged intervals."""

def inspect_protein_correspondence(hsp_components: list[dict]) -> dict:
    """One subject occurrence's HspComponents -> CorrespondenceGraph."""

# New bvbrc_proteome_directional_numerical_contracts.py.
def directional_numerical_schema(name: str) -> dict:
    """Fresh copy of the named closed JSON Schema."""

def validate_directional_numerical(
    name: str, value: dict, *, sheet: dict | None = None,
) -> dict:
    """Validate structural and field relationships; return an independent copy.
    DirectionalComponents[Result] require their observed sheet for validation.
    Invalid arguments raise a dedicated contract error carrying code+pointer.
    """
```

The only legal schema names are `DirectionalSheet`, `DirectionalSheetResult`,
`DirectionalCalculationParameters`, `BlockComponents`, `HspComponents`,
`CorrespondenceGraph`, `DirectionalComponents`, `DirectionalComponentsResult`
and `DirectionalScoringSheet`. Primitive schemas are private `$defs`.

The builder and top calculator convert input-contract errors to structured
failure results. Native scientific partial/failure reader results that satisfy
the reader's schema are valid inputs and are retained, with usable neighbors
processed. Structural corruption is not silently normalized. The provider
must retain independent documents/results if one selected document is invalid;
it can invoke the builder per document to isolate such a failure. Failure does
not destroy or revise already saved native input.

No function above accepts a URL, file path to acquire, API client, execution
launcher, LLM, resource selector or witness assertion. Actual bytes are the
existing reader's responsibility. A caller obtains bytes through the authorized
existing custody path before invoking the reader. These functions perform no
network or process execution.

## 2. Primitive shapes

`N` is a nonnegative JSON integer excluding booleans. `P` is a positive such
integer. All decimal values use the existing native reader's decimal-string
contract; computed ratios never require a binary float. `Sha` is64 lowercase
hex digits. An `Interval` is exactly `[N,P]` with second > first and means
zero-based, half-open displayed protein positions. Interval arrays are sorted,
nonoverlapping and maximally merged, including adjacent intervals.

```text
QueryKey   = {report_ordinal:N, query_ordinal:N}
SubjectKey = {report_ordinal:N, query_ordinal:N, subject_ordinal:N}
HspKey     = {report_ordinal:N, query_ordinal:N, subject_ordinal:N, hsp_ordinal:N}
BlockKey   = {report_ordinal:N, query_ordinal:N, subject_ordinal:N,
              hsp_ordinal:N, block_ordinal:N}
ColumnKey  = {report_ordinal:N, query_ordinal:N, subject_ordinal:N,
              hsp_ordinal:N, block_ordinal:N, column_ordinal:N}
FieldRef   = {report_ordinal:N, pointer:string}
```

FieldRef pointers must resolve into that report in `sheet.reader_results` and
refer to the actual operands for the named formula. A structurally valid pointer
to a different query/HSP is invalid. Keys are contiguous original array ordinals;
the calculator never renumbers a partial subset. Report key/source identity is
retained in the native reader result, outside the episode's prose.

Native aliases are **exact existing schemas**, not open objects:
`NativeIntCell`, `NativeDecimalCell`, `NativeTextCell`, `ReaderTraceBlock`,
`ReaderDescription`, `ReaderDatabaseHeader`, `ReaderStatistic` and
`ReaderResult` denote their corresponding existing closed reader shapes under
the inspected `bvbrc_proteome_directional_schemas.json`. Their exact field sets,
numeric lexical rules, source bindings and missing/invalid semantics are retained.
For example a native cell is `{state,value,native_text,locations}`; location is
`{source_ref,sha256,span:{byte_start,byte_end}}`. Do not coerce these aliases to
older B3 `RetainedHSP` proposal rows.

```text
Issue = {
  code:IssueCode,
  fields:FieldRef[],
  columns:ColumnKey[],
  hsps:HspKey[]
}

Support = {
  included_blocks:BlockKey[],
  excluded_blocks:BlockKey[],
  hsps_without_traceback:HspKey[],
  complete_for_displayed_blocks:bool
}

ExactFraction = {numerator:N, denominator:P, decimal:string}

CountCell = {
  state:"value"|"missing"|"invalid"|"conflict"|"undefined",
  value:N|null,
  unit:"alignment_column"|"paired_column"|"displayed_position"|
       "coordinate_pair"|"gap_run"|"query_occurrence"|
       "description_occurrence"|"subject_occurrence"|"hsp_occurrence"|
       "block_occurrence"|"pair_representation",
  inputs:FieldRef[], reasons:IssueCode[], uncertainty:null
}

RatioCell = {
  state:"value"|"missing"|"invalid"|"conflict"|"undefined",
  value:ExactFraction|null, unit:"fraction",
  inputs:FieldRef[], reasons:IssueCode[], uncertainty:null
}
```

`state=value` iff value is non-null. `undefined` is reserved for mathematically
undefined empty/zero-denominator ratios, not unknown scientific inputs. Native
zero length/denominator is invalid; a calculated empty pair denominator is
undefined. Missing, invalid and conflicting causes have their distinct states
and all applicable reason codes; when several apply, `conflict` takes precedence
over `invalid`, then `missing`, then `undefined`. Valid native and valid trace
cells can each remain value while a separate Issue records their disagreement.
`uncertainty:null` means not reported or modeled; no biological precision claim.

The semantic validator enforces the unit appropriate to each field below.
`ExactFraction` retains the semantic numerator/denominator without reduction;
decimal must equal HALF_EVEN rounding of their exact quotient to the explicit
requested number of places. Ratio field definitions here are bounded0..1;
violation invalidates the derived cell rather than clamps it. Decimal rendering
must not feed calculations.

Support sets partition the actual displayed block membership of that scope;
HSPs with no traceback must be explicitly listed. Completeness is exactly no
excluded blocks and no HSPs without traceback. This is **not** completeness of
all algorithmic HSPs, input occurrences or execution. A scope with no HSPs may
produce zero display coverage only under the native no-hit case specified in
the numerical contract. Otherwise it does not manufacture zero geometry.

Closed IssueCode enum for this formula version:

```text
invalid_input_contract, invalid_parameters, no_report_supplied,
native_reader_partial, native_reader_failure, source_body_incomplete,
source_object_completeness_unknown, source_object_incomplete,
missing_native_count, invalid_native_count, zero_native_denominator,
count_exceeds_denominator, incompatible_native_denominators,
identity_exceeds_paired_count, positive_below_identity,
positive_exceeds_paired_count, reported_count_traceback_conflict,
missing_traceback, missing_traceback_symbols, invalid_traceback_symbols,
traceback_width_conflict, double_gap_column, missing_coordinate,
invalid_coordinate, reverse_protein_coordinates, coordinate_span_conflict,
coordinate_outside_reported_length, missing_reported_length,
invalid_reported_length, block_continuity_conflict,
incomplete_displayed_geometry, incomplete_displayed_strings,
native_denominator_extent_unknown, native_denominator_extent_conflict,
alternative_query_mapping, alternative_subject_mapping,
query_symbol_conflict, subject_symbol_conflict,
query_gap_versus_pair_conflict, subject_gap_versus_pair_conflict,
noncollinear_pair_order, overlapping_hsp_occupied_positions,
zero_paired_population, zero_resolved_population,
native_no_hit_with_displayed_population, empty_without_native_no_hit,
descriptions_without_subject_blocks, missing_native_score,
invalid_native_score, printed_zero_expectation,
statistic_occurrences_disagree, no_execution_or_occurrence_evidence
```

Existing reader Issues are retained verbatim inside ReaderResult; they are not
force-converted to this new enum. The new fixed enum is for new arithmetic and
relationship diagnostics. A future change requiring a new code is a versioned
contract revision, not freeform prose in a child return.

## 3. Populated observed sheet

```text
DirectionalSheet = {
  version:"bvbrc_proteome_directional_sheet_v1",
  reader_results:ReaderResult[],
  reports:ReportObservation[],
  diagnostics:Issue[]
}

ReportObservation = {
  report_ordinal:N,
  report_key:string,
  query_rows:QueryObservation[]
}

QueryObservation = {
  key:QueryKey,
  reported_length:NativeIntCell,
  header_text:NativeTextCell,
  identifier_token:NativeTextCell,
  no_hits_marker:NativeTextCell,
  boundary:"next_banner"|"next_query"|"eof_complete"|"eof_unconfirmed",
  database_headers:ReaderDatabaseHeader[],
  descriptions:ReaderDescription[],
  statistics:ReaderStatistic[],
  subjects:SubjectObservation[]
}

SubjectObservation = {
  key:SubjectKey,
  reported_length:NativeIntCell,
  defline_text:NativeTextCell,
  identifier_token:NativeTextCell,
  hsps:HspObservation[]
}

HspObservation = {
  key:HspKey,
  identity_count:NativeIntCell,
  identity_denominator:NativeIntCell,
  identity_printed_percent:NativeDecimalCell,
  positive_count:NativeIntCell,
  positive_denominator:NativeIntCell,
  positive_printed_percent:NativeDecimalCell,
  gap_count:NativeIntCell,
  gap_denominator:NativeIntCell,
  gap_printed_percent:NativeDecimalCell,
  bit_score:NativeDecimalCell,
  raw_score:NativeIntCell,
  expect:NativeDecimalCell,
  expect_group_count:NativeIntCell,
  method_text:NativeTextCell,
  traceback_blocks:ReaderTraceBlock[]
}

DirectionalSheetResult = {
  state:"available"|"partial"|"failure",
  sheet:DirectionalSheet|null,
  diagnostics:Issue[]
}
```

`reports` and its complete nested membership must exactly cover ReaderResult
arrays; every copied native cell/block/row must equal the original. Extra,
missing, swapped and re-keyed rows fail semantic validation. All original spans,
native raw records, parser Issues, banners and source-custody facts remain in
`reader_results`, even if not copied into this numerical view. Diagnostics do
not authorize dropping scientific data.

`available` describes construction of this input sheet, not scientific success.
`partial` retains usable native partial/failure records and qualifications.
Only structural impossibility of constructing a conforming sheet returns
`failure` with sheet null; valid neighboring native records remain caller-owned
and independently usable. No report supplied yields an empty partial sheet and
`no_report_supplied`, not a zero-hit result.

## 4. Explicit parameters

```text
DirectionalCalculationParameters = {
  version:"bvbrc_proteome_directional_parameters_v1",
  formula_version:"displayed_blastp_correspondence_v1",
  amino_acid_alphabet:"standard20"|"standard20_plus_uo",
  ratio_decimal_places:N constrained0..30,
  rounding:"half_even"
}
```

No defaults are silently inserted into a saved calculation. The filled example
uses standard20 and18 places. Overlap handling is the formula's set/graph
definition, not a parameter allowing naive residue summation. E-value cutoffs,
resource settings, report caps and scientific acceptance thresholds are not
correspondence parameters. Actual search settings remain native/witness facts.

## 5. Block and HSP components

```text
AxisPosition = {state:"position"|"gap"|"unavailable_coordinate", value:N|null}
# value is non-null iff state=position; gap is permitted only for native '-'.

Column = {
  key:ColumnKey,
  query_symbol:one ASCII native symbol,
  subject_symbol:one ASCII native symbol,
  query_position:AxisPosition,
  subject_position:AxisPosition,
  kind:"query_gap"|"subject_gap"|"resolved_identical"|
       "resolved_substituted"|"unresolved_pair"|"stop_containing_pair",
  displayed_symbol_equal:bool
}

TraceCounts = {
  alignment_columns:CountCell,
  paired_columns:CountCell,
  displayed_symbol_identical_pairs:CountCell,
  displayed_symbol_nonidentical_pairs:CountCell,
  resolved_amino_acid_pairs:CountCell,
  resolved_amino_acid_identical_pairs:CountCell,
  resolved_amino_acid_substituted_pairs:CountCell,
  unresolved_symbol_pairs:CountCell,
  stop_containing_pairs:CountCell,
  query_gap_columns:CountCell,
  subject_gap_columns:CountCell,
  query_gap_runs:CountCell,
  subject_gap_runs:CountCell,
  query_non_gap_symbols:CountCell,
  subject_non_gap_symbols:CountCell
}

TraceFractions = {
  trace_symbol_identity_over_columns:RatioCell,
  trace_symbol_identity_over_pairs:RatioCell,
  trace_resolved_amino_acid_identity:RatioCell,
  trace_resolved_pair_fraction:RatioCell,
  trace_unresolved_pair_fraction:RatioCell,
  trace_gap_fraction:RatioCell
}

PositionUnion = {
  intervals:Interval[],
  count:CountCell,
  reported_length:NativeIntCell,
  coverage:RatioCell,
  support:Support
}

CoverageComponents = {
  query_reported_interval_union:PositionUnion,
  subject_reported_interval_union:PositionUnion,
  query_trace_occupied_union:PositionUnion,
  subject_trace_occupied_union:PositionUnion,
  query_trace_paired_union:PositionUnion,
  subject_trace_paired_union:PositionUnion
}

BlockComponents = {
  key:BlockKey,
  counts:TraceCounts,
  fractions:TraceFractions,
  columns:Column[],
  coverage:CoverageComponents,
  diagnostics:Issue[]
}

ReportedFractions = {
  reported_identity_fraction:RatioCell,
  reported_positive_fraction:RatioCell,
  reported_gap_fraction:RatioCell,
  reported_paired_column_count:CountCell,
  reported_nonidentical_paired_count:CountCell,
  reported_identity_among_paired_fraction:RatioCell
}

NativeScores = {
  bit_score:NativeDecimalCell,
  raw_score:NativeIntCell,
  expect:NativeDecimalCell,
  expect_group_count:NativeIntCell,
  expectation_display:"positive_reported_decimal"|"printed_zero_precision_unknown"|
                      "missing"|"invalid"
}

HspComponents = {
  key:HspKey,
  reported:ReportedFractions,
  native_scores:NativeScores,
  blocks:BlockComponents[],
  trace_counts:TraceCounts,
  trace_fractions:TraceFractions,
  strings_support:Support,
  coverage:CoverageComponents,
  pair_geometry_support:Support,
  contiguous_blocks:"yes"|"no"|"unknown",
  native_denominator_extent:"agrees"|"disagrees"|"unknown",
  diagnostics:Issue[]
}
```

Counts of paired classes have unit `paired_column`; query/subject non-gap symbol
counts use `displayed_position`; C and gap columns use `alignment_column`; runs
use `gap_run`. Individual block gap runs are calculable from its valid symbols
even if coordinates are missing. HSP total runs require the continuity rule.
HSP trace counts/fractions describe the included valid string blocks, with
`strings_support` always exposed. If no block is usable, they are missing or
invalid, not0. For partial strings, they are exact **valid subset** quantities;
the complete retained membership stays in `blocks` and `excluded_blocks`.

Only columns with usable paired strings are expanded. Invalid strings retain
native data and unavailable column-derived fields; no fabricated columns.
Each valid column can have an independently unavailable coordinate on either
axis. Paired coverage on the valid axis remains possible; an exact coordinate
pair requires both. For gap kinds `displayed_symbol_equal=false` (double gaps
are invalid); for pairs it is the uppercase equality comparison, independent
of whether the symbols are resolved amino acids.

All intervals/counts/cell sources are verified against the saved blocks and
their scope. Empty interval arrays do not by themselves mean measured zero.
`native_denominator_extent=agrees` requires complete usable strings and agreement
with every present usable denominator; no denominator yields unknown, a
disagreement yields disagrees. It does not prove the absence of undisplayed HSPs.

## 6. Subject graph and aggregates

```text
PairEdge = {
  query_position:N,
  subject_position:N,
  supports:ColumnKey[],
  symbol_state:"consistent"|"conflicting"
}

MappingConflict = {
  code:"alternative_query_mapping"|"alternative_subject_mapping"|
       "query_symbol_conflict"|"subject_symbol_conflict"|
       "query_gap_versus_pair_conflict"|"subject_gap_versus_pair_conflict"|
       "noncollinear_pair_order"|"block_continuity_conflict",
  columns:ColumnKey[],
  query_intervals:Interval[],
  subject_intervals:Interval[]
}

CorrespondenceGraph = {
  key:SubjectKey,
  edges:PairEdge[],
  distinct_pair_count:CountCell,
  repeated_pair_occurrence_count:CountCell,
  pair_geometry_support:Support,
  conflicts:MappingConflict[],
  mapping_state:"compatible_displayed_partial_map"|"observed_conflict"|
                "incomplete_geometry"
}

CompatiblePairCounts = {
  identical_symbol_pairs:CountCell,
  resolved_pairs:CountCell,
  resolved_identical_pairs:CountCell,
  resolved_substituted_pairs:CountCell,
  unresolved_pairs:CountCell,
  stop_containing_pairs:CountCell
}

Extremum = {
  state:"value"|"missing"|"invalid",
  selected_field:FieldRef|null,
  tied_hsps:HspKey[],
  excluded_hsps:HspKey[],
  reason_codes:IssueCode[]
}
# selected_field references the actual unmodified native cell. If several tie,
# select its first native-order reference for storage and retain all ties;
# this is representation of an extremum, never a selected scientific HSP.

SubjectComponents = {
  key:SubjectKey,
  displayed_hsp_count:CountCell,
  displayed_block_count:CountCell,
  hsps:HspComponents[],
  coverage:CoverageComponents,
  correspondence:CorrespondenceGraph,
  compatible_pair_counts:CompatiblePairCounts,
  compatible_unique_pair_symbol_identity:RatioCell,
  compatible_unique_pair_resolved_identity:RatioCell,
  compatible_unique_pair_resolved_fraction:RatioCell,
  nonoverlapping_hsp_reported_identity_count:CountCell,
  nonoverlapping_hsp_reported_alignment_columns:CountCell,
  nonoverlapping_hsp_reported_identity_over_columns:RatioCell,
  maximum_reported_hsp_bit_score:Extremum,
  maximum_reported_hsp_raw_score:Extremum,
  minimum_reported_hsp_expectation:Extremum,
  diagnostics:Issue[]
}
```

Edges sort by `(query_position,subject_position)`; support keys sort by native
HSP/block/column order, are unique, and all correspond to that exact pair.
Edges never cross a subject occurrence. Mapping conflicts enumerate the actual
participating columns; they cannot refer only to endpoint span intersection.
If one edge has agreeing identity booleans but different actual symbols, the
symbol conflict is still required. Coordinate sets, distinct edge count and
repeated representations remain available for their valid subset even when
the graph conflicts; compatible pair counts and identity ratios do not.

`CompatiblePairCounts` uses unit `coordinate_pair`. Incomplete geometry makes
its cells missing; observed contradictions make them conflict. In the compatible
case every unique edge contributes exactly once to its class and equality count.
Resolved fraction uses resolved edge count / total distinct edge count.

Nonoverlapping native identity/column sums are ordinary integer sums with the
strict disjointness/count-agreement conditions in the numerical contract.
Native integer counts are not used to assign identities to unspecified positions.
Extrema compare decimal/integer cells directly, without binary floats. `Expect`
group notation remains on the HSP and is never interpreted as independent P.

## 7. Query/report components and saved sheet

```text
QueryComponents = {
  key:QueryKey,
  display_state:"native_no_hit_claim"|"alignments_displayed"|
                "descriptions_only"|"empty_without_native_no_hit_claim"|
                "contradictory_native_no_hit_claim",
  displayed_description_count:CountCell,
  displayed_subject_count:CountCell,
  displayed_hsp_count:CountCell,
  displayed_block_count:CountCell,
  subjects:SubjectComponents[],
  any_displayed_subject_query_paired_union:PositionUnion,
  diagnostics:Issue[]
}

ReportComponents = {
  report_ordinal:N,
  displayed_query_count:CountCell,
  displayed_description_count:CountCell,
  displayed_subject_count:CountCell,
  displayed_hsp_count:CountCell,
  displayed_block_count:CountCell,
  queries:QueryComponents[],
  diagnostics:Issue[]
}

DirectionalComponents = {
  version:"bvbrc_proteome_directional_components_v1",
  formula_version:"displayed_blastp_correspondence_v1",
  sheet_sha256:Sha,
  parameters:DirectionalCalculationParameters,
  reports:ReportComponents[],
  diagnostics:Issue[],
  correspondence_used_inputs:["native_counts","traceback_symbols",
      "traceback_coordinates","reported_lengths","amino_acid_alphabet"],
  correspondence_unused_retained_inputs:["database_expectations",
      "native_alignment_scores","native_positives","native_midlines",
      "description_scores","database_statistics","method_text"]
}

DirectionalComponentsResult = {
  state:"available"|"partial"|"failure",
  components:DirectionalComponents|null,
  diagnostics:Issue[]
}

DirectionalScoringSheet = {
  version:"bvbrc_proteome_directional_scoring_sheet_v1",
  observed:DirectionalSheet,
  calculated:DirectionalComponents
}
```

The two fixed lists describe correspondence calculations only: raw/bit scores
and expectations are retained and used by their separate descriptive extrema;
native positives have their own reported fraction. No claim is made that the
correspondence formula uses those families. No overall scalar score is present.

Sheet hash is SHA256 of the complete observed sheet encoded UTF-8 with sorted
object keys, compact separators, `ensure_ascii=False`, no NaN or infinity.
The implementation must specify this exact encoding in one shared helper.
The saved `calculated.sheet_sha256` must match `observed`; parameters, formula
version and native values remain immutable for that publication. A new formula
or parameter set makes a new calculation/publication referencing the same
observed sheet, never an in-place rewrite of closed history.

Top result states classify availability of this calculation, not the tool's
scientific completion or runtime continuation. Any incomplete strings/geometry,
native reader degradation or conflicting calculation produces `partial` with
usable neighboring cells intact; absence of execution witnesses alone does not
turn a successfully calculated report sheet into a failed calculation. Valid
no-hit input is available, with undefined pair identity as specified.

All query/subject/HSP/block memberships and their keys must exactly match the
observed sheet. Numerical validators check source references, allowed unit,
ratio numerator/denominator/rounding, set cardinalities, pair-support membership,
class partitions, required conflict relationships and copied native score cells.
They must not validate only JSON shape or accept tampered derived values because
the parent source hash is correct. These are deterministic data validations,
not reviewers, model calls, acceptance gates or action decisions.

## 8. Precise BLAST reuse boundary

The full existing `blast_pairwise_grader.py` and `blast_database_grader.py` were
read, including their count, geometry, union, conflict and database-statistics
consumers. The exact reusable math is:

| Existing function | Reusable portion / required restriction |
|---|---|
| `alignment_components(hsp, program="blastp", query_length=Lq, reference_length=Ls)` | Valid-string column counts, uppercase symbol equality, native-count/trace diagnostics and mapped nongap pairs. Adapt one contiguous HSP or one valid native block; pass actual integer fields only. Its `identical_pairs` is displayed-symbol equality, not resolved-AA identity. Preserve native cells elsewhere. |
| `_axis_positions(...)` | Positive inclusive endpoints → zero-based per-column positions, nongap span check and reported-length bounds. Invoke independently for each protein axis; `coordinate_unit="aa"`, `alignment_unit="aa"`, no inferred strand/frame. |
| `_union_size(intervals)` | Exact unique interval cardinality; current formula sorts/deduplicates and advances the maximal boundary. The new wrapper also retains the merged intervals and source support. |
| `_mapping_conflicts(pairs, axis)` | Alternative paired mapping detection on one axis; duplicate exact edges are harmless. It is insufficient for symbols, paired-vs-gap labels, noncollinearity and block continuity. Add those explicitly. |
| Database `_union_length` | Same mathematical interval union; do not create a conflicting definition. |

Recommended implementation: the new geometry module is the only adapter to
these existing primitives. It may call the existing public `alignment_components`
for usable block counts/pairs and the existing private `_axis_positions`,
`_union_size`, `_mapping_conflicts` behind tested local wrappers. This requires
no edit to the preserved BLAST graders. If root prefers public exports later,
assign that refactor to a single shared-math owner and retain the same regression
behavior; do not duplicate competing coverage/coordinate formulas across workers.

The adapter does not round-trip native score cells through the old normalized
HSP. `alignment_components` accepts number fields and returns float/int score
cells, whereas this reader has exact decimal strings, lexical text and explicit
states. Scores are copied directly from the new sheet instead. The adapter
does not pass HSP-wide I/L into each individual block as if the count belonged
to that block. Unknown optional normalized numeric fields are omitted, not0.

Do not call `build_pairwise_sheet` on the whole GenomeComparison database result:
it enforces one pairwise reference/mode. Its union structure is informative but
does not preserve these native field states or all required symbol/gap/order
relationships. Do not call database `_hit_measurements` to stand in for this
graph: its unique key includes identity boolean and can represent contradictory
identity labels as separate entries; its score handling does not retain lexical
decimals. Existing `calculate_database_probabilities` is a separate statistical
consumer requiring explicit function/sequence/population bindings and is not
automatically invoked by this correspondence contract.

## 9. Required small filled sheet

[FILLED_NUMERICAL_SHEET_EXCERPT_001.json](FILLED_NUMERICAL_SHEET_EXCERPT_001.json)
is explicitly an **excerpt**, not a fake complete conforming report with dropped
queries. It records concrete observed native cells and calculated cell values
for the two2.2.21 q1 HSPs and both2.2.2 overlapping-subject examples, including
source pointers, exact fractions and states. Full independent arithmetic for
all29 displayed HSPs is in `NUMERICAL_NATIVE_EXAMPLES_001.json`. Full native
reader outputs remain in worker172 and are byte-bound by the source manifest.
An implementation must generate the complete shapes above for the actual full
reports; it must not treat the excerpt as a complete membership test.
