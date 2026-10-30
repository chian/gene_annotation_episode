# GenomeAlignment closed interface proposal 002

Additive follow-up to `BOUNDARY_PROPOSAL_001.md` and `CONTRACT_BOUNDARIES_001.json`. Those records are preserved. This document supersedes their underspecified A/B/C handoff shapes and their suggestion to omit optional missing requirements from adapter output. It remains a proposal: no production implementation, tests, registry or fixed ledger row was changed.

Two source clarifications are also additive. ProgressiveMauve's `applyBackbone` first uses the homology HMM to refine/unalign regions, then runs `BigGapsDetector(island_gap_size)` on the resulting intervals before writing final BBCols/sequence regions. The final sidecars therefore do not contain direct HMM posterior values. The retained default `island_gap_size` is 20. Its sequence-region file is subsequently merged and augmented with singleton segments. `weight` is documented as minimum pairwise LCB score and passed to `setBreakpointPenalty`; it remains an input parameter, not an emitted measured score.

## Contract notation and shared definitions

Every record below is **closed**: every listed key is required, nullable fields remain present as `null`, and undeclared keys are rejected. Union alternatives are selected only by their explicit literal discriminator. `T[]` means an ordered JSON array of T. Python call boundaries requiring `tuple` are listed explicitly; serialization uses arrays. No arbitrary metadata dictionary or unbounded findings string is accepted by the new contracts. Native raw strings are retained scientific input, not episode instructions.

Types: `Text` is a nonempty string; `RawText` permits empty native text; `UInt` is a nonnegative integer excluding Boolean; `Positive` is an integer >=1; `Interval` is exactly `[UInt,UInt]`, ordered half-open, with end >= start; `Strand` is `"+"|"-"`; `SHA256` is 64 lowercase hex digits. Unique IDs below are deterministic content/ordinal record identities, never claimed native accessions. Array order follows retained file order unless an explicit selection says otherwise.

The following are **aliases of existing complete contracts**, not new generic numerical or evidence abstractions:

| Alias | Exact existing contract/validator |
|---|---|
| `Artifact` | `{raw_artifact_ref:Text,source_ref:Text,sha256:SHA256}` validated by `xmfa_format_contracts._artifact` / existing document validators |
| `Location` | `{artifact:Artifact,byte_start_0based:UInt|null,byte_end_0based_exclusive:UInt|null,line_start_1based:Positive|null,line_end_1based_inclusive:Positive|null,xml_path:Text|null}`; existing `phylogeny_calculation_contracts.location` paired-bound rules. These new text readers always provide byte and line bounds and use null XML path |
| `NativeNumber` | existing `bvbrc_alignment_values.native_number` and `validate_native_number`: `{raw_token,value,state,token_kind,source_location}` with their existing enums, finite-number/range rules and token semantics |
| `NumericCell` | existing `bvbrc_alignment_values.numeric_cell` / `validate_numeric_cell` **unchanged**, including units, origin, numerator/denominator, population/method, evidence, uncertainty and requirement IDs |
| `Evidence` | exact `bvbrc_appservice_schemas.json/$defs/SourceEvidence` |
| `Content` | exact existing `ContentBinding` schema |
| `Requirement` | exact existing `AcquisitionRequirement` schema; `kind`, `role`, source refs and reason code remain present |
| `Diagnostic` | exact existing `Diagnostic` schema; code belongs to the finite family list below, phase and source refs remain constrained |
| `OriginalTask`, `ArtifactMember`, `DeclaredFormat` | corresponding complete existing AppService schemas; no native-field reinterpretation |
| `Occurrence` | exact `xmfa_calculation_contracts.occurrence`: `{input_binding_id:Text,member_id:Text,occurrence_index:UInt}` |
| `XMFAInputs`, `XMFADocument`, `XMFABindings` | unchanged `mauve_xmfa_source_inputs_v1`, `mauve_xmfa_document_v1`, source-binding output validators in `xmfa_source_contracts.py` |
| `XMFAAlignmentComponents`, `XMFACoverageComponents`, `XMFACoordinates`, `XMFAInverseCoordinates` | exact complete outputs validated by `validate_xmfa_alignment_components`, `validate_xmfa_coverage_components`, `validate_xmfa_coordinates`, `validate_xmfa_inverse_coordinates` in `xmfa_calculation_contracts.py` |
| `FastaRecord` | exact neutral XMFA file record: `{record_id:Text,entry_1based:Positive,header:RawText|null,sequence:RawText,source_location:Location}`; sequence obeys the existing neutral DNA alphabet validator |
| `OriginalMap` | exact neutral source-input original-map row (`file_id`, `record_id`, staged interval, `Occurrence`, original length/interval, strand, transformation id, evidence) |

New local primitives:

```text
NativeMember = {
  namespace: "mauve1_member_1based" | "mauve_v4_member_0based" | "mauve_sidecar_member_0based",
  index: UInt
}
RawLine = {raw_line: RawText, source_location: Location}
ParseCompleteness = "complete" | "partial" | "unknown"
MemberState = "present" | "absent_zero" | "missing" | "incompatible"
AssociationState = "bound" | "missing" | "unverified" | "conflicting"
RecordRef = {document_id:Text, interval_index:UInt, segment_index:UInt}
Pair = {member_a:NativeMember, member_b:NativeMember}
```

`mauve1_member_1based` requires positive index; other namespaces allow zero. Pair order is canonical by `(namespace,index)`; no self-pair or duplicate selected pair. `Location.artifact` must equal the owning document artifact; byte and line bounds must be ordered. NativeNumber fields retain invalid tokens instead of coercing them into valid member IDs. No absence/strand/association enum becomes a numeric confidence value.

## A: v4 reader and explicit-segment calculator

Exact signatures:

```python
parse_mauve_v4(data: bytes, *, artifact: dict,
    encoding: Literal['ascii', 'utf-8']) -> dict  # V4ParseResult
validate_mauve_v4_document(document: dict) -> dict
validate_mauve_v4_selection(selection: dict) -> dict
calculate_mauve_v4_segments(document: dict, *, selection: dict,
    inputs: dict | None) -> dict  # V4SegmentComponents
```

`inputs` is the closed `GenomeAlignmentInputs` below, supplied by C. It is not a generic mapping of names to sequences. The calculator calls no C acquisition operation; it reads already validated values.

```text
V4ParseResult = {
  status:"ok"|"partial"|"invalid",
  value:MauveV4Document|null,
  diagnostics:Diagnostic[]
}
V4Metadata = {
  metadata_index:UInt, raw_line:RawText,
  kind:"format_version"|"sequence_count"|"sequence_file"|"sequence_length"|"interval_count"|"unknown",
  member_index_token:NativeNumber|null,
  value_token:RawText,
  number:NativeNumber|null,
  source_location:Location
}
V4SequenceRow = {
  member_index_0based:UInt,
  sequence:RawText,
  sequence_parts:RawLine[],
  source_location:Location
}
V4Ungapped = {
  kind:"ungapped_coordinates", segment_index:UInt,
  raw_header:RawText, header_location:Location,
  native_length:NativeNumber, native_starts:NativeNumber[],
  source_location:Location,
  completeness:ParseCompleteness
}
V4Gapped = {
  kind:"gapped_rows", segment_index:UInt,
  marker:RawLine, raw_header:RawText|null, header_location:Location|null,
  native_width:NativeNumber|null, native_starts:NativeNumber[],
  expected_member_count:UInt|null,
  sequence_rows:V4SequenceRow[],
  source_location:Location,
  completeness:ParseCompleteness
}
V4Interval = {
  interval_index:UInt,
  raw_header:RawText,
  native_interval_ordinal:NativeNumber,
  header_location:Location,
  segments:(V4Ungapped|V4Gapped)[],
  unparsed:RawLine[],
  source_location:Location,
  completeness:ParseCompleteness
}
MauveV4Document = {
  schema_version:"mauve_v4_document_v1",
  document_id:Text, artifact:Artifact, encoding:"ascii"|"utf-8",
  metadata:V4Metadata[], intervals:V4Interval[], unparsed:RawLine[],
  completeness:ParseCompleteness
}
```

No declaration wins by position: repeated version/count/file/length declarations all remain in `metadata`. Resolve an effective scalar only when every applicable usable declaration agrees and none contradicts it; record conflict otherwise. A member file/length join uses its explicit native index token, not metadata row position. Original paths with whitespace remain whole `value_token` strings. `interval_index` is observed record order, while `native_interval_ordinal` preserves the file's potentially duplicated/malformed declaration. Segment index is observed order within that interval. Unknown lines are retained in the nearest applicable `unparsed` array and never silently discarded or treated as sequence.

The recognized header must say v4; another format is invalid/null. A missing/conflicting member count prevents treating an arbitrary number of lines as complete N-row gapped data. Preserve the marker and available row material as partial; do not infer N from a different interval or pad missing members. Every actual sequence row retains its original member line ordinal; an omitted row does not shift later rows into new membership. Parsing stops the affected gapped segment at a recognized structural header; missing rows remain missing. `native_length`/`native_width` and signed starts accept integer native-number parsing only; negative length, nonfinite numeric values, invalid starts and inconsistent counts are diagnosed with their raw tokens retained.

`completeness` is syntactic completeness of the retained bytes against native declarations, never proof of successful native execution, full transport or complete biological population. A legacy interval has no per-interval segment-count/trailer, so an apparently valid final interval can still be from an interrupted writer. C/D preserve that independent execution qualification.

```text
V4SegmentSelection = {
  interval_index:UInt, segment_index:UInt,
  column_ranges_0based_half_open:Interval[]
}
V4Selection = {
  schema_version:"mauve_v4_selection_v1",
  population_id:Text, document_id:Text,
  members:NativeMember[], segments:V4SegmentSelection[], pairs:Pair[],
  case_policy:"preserve"|"uppercase",
  denominator:"none"|"native_declared_length"|"validated_staged_length",
  population_scope:"selected_segments"|"all_observed_document_segments",
  evidence:Evidence[]
}
```

Members must use the v4 namespace. Ranges are nonempty, ascending, disjoint, within the segment's **valid** native width; caller does not assert completeness. If scope is all observed, the selection must enumerate every recognized segment and all its columns; a malformed/unresolved segment prevents an all-observed-complete interpretation. Explicit subset selections can still calculate unaffected segments. `native_declared_length` and `validated_staged_length` are separate calculation choices and must remain separate in stored output. `none` still computes native counts/unions with fraction state `not_measured`.

```text
V4MemberSegment = {
  segment:RecordRef, member:NativeMember,
  state:MemberState,
  native_start:NativeNumber|null,
  strand:Strand|null,
  native_interval_0based_half_open:Interval|null,
  symbols_origin:"native_rows"|"source_extracted"|"unavailable",
  aligned_sequence:RawText|null,
  alignment_columns:NumericCell,
  selected_column_count:NumericCell,
  selected_nongap_count:NumericCell,
  selected_gap_count:NumericCell,
  selected_canonical_count:NumericCell,
  selected_ambiguity_count:NumericCell,
  selected_other_count:NumericCell,
  source_comparison:"match"|"mismatch"|"not_checked"|"not_applicable",
  evidence:Evidence[], requirement_ids:Text[]
}
PairCounts = {
  identical_canonical:NumericCell, substitutions:NumericCell,
  a_only_gap:NumericCell, b_only_gap:NumericCell, both_gap:NumericCell,
  ambiguous_or_other:NumericCell, comparable_canonical:NumericCell,
  identity_fraction:NumericCell
}
V4PairSegment = {
  segment:RecordRef, pair:Pair,
  state:"available"|"not_coobserved"|"missing_symbols"|"incomplete"|"incompatible",
  counts:PairCounts,
  evidence:Evidence[], requirement_ids:Text[]
}
Placement = {
  record:RecordRef, member:NativeMember,
  interval_0based_half_open:Interval, strand:Strand,
  evidence:Evidence[]
}
MemberCoverage = {
  member:NativeMember,
  placements:Placement[], known_union_intervals:Interval[],
  known_union_bases:NumericCell, placement_bases:NumericCell,
  multiply_represented_bases:NumericCell, excess_placement_bases:NumericCell,
  denominator_kind:"none"|"native_declared_length"|"validated_staged_length",
  denominator_bases:NumericCell, coverage_fraction:NumericCell,
  complement_intervals:Interval[]|null, complement_bases:NumericCell,
  population_state:"complete_selected"|"partial_selected"|"unknown",
  evidence:Evidence[], requirement_ids:Text[]
}
V4SegmentComponents = {
  schema_version:"mauve_v4_segment_components_v1",
  document_id:Text, status:"ok"|"partial"|"invalid",
  selection:V4Selection,
  member_segments:V4MemberSegment[], pair_segments:V4PairSegment[],
  coverage:MemberCoverage[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
```

The existing NumericCell meaning is reused; field-specific formulas are in proposal 001. In particular ungapped native coordinates establish a span, not nucleotide identity. Without sources, `selected_nongap_count` for a valid ungapped present member is the selected column count, `selected_gap_count=0`, but canonical/ambiguity/other counts and pair identities are `missing`. A complete source extraction supplies sequence symbols while preserving `source_extracted` origin. Absence is never a zero identity. A gapped row's native span length is full-row nongaps; selected-column coverage counts only selected nongap positions. Native-declared denominator values are `native_observation`; extracted staged lengths and interval/count arithmetic are `calculated`. Source mismatches invalidate dependent source fractions but do not erase raw/native coordinate counts.

## B: sidecar readers, selections and components

Exact signatures:

```python
parse_mauve_backbone(data: bytes, *, artifact: dict,
    dialect: Literal['libmems_signed_coordinate_pairs_v1'],
    encoding: Literal['ascii','utf-8']) -> dict  # BackboneParseResult
parse_mauve_bbcols(data: bytes, *, artifact: dict,
    dialect: Literal['libmems_interval_columns_members_v1'],
    encoding: Literal['ascii','utf-8']) -> dict  # BBColsParseResult
validate_mauve_backbone_document(document: dict) -> dict
validate_mauve_bbcols_document(document: dict) -> dict
calculate_mauve_backbone_components(document: dict, *,
    selection: dict, inputs: dict | None) -> dict  # BackboneComponents
calculate_mauve_bbcols_components(document: dict, *,
    selection: dict, xmfa_document: dict | None,
    associations: dict | None) -> dict  # BBColsComponents
```

```text
BackboneHeaderColumn = {
  column_index:UInt, raw_token:RawText,
  member_index_token:NativeNumber|null,
  endpoint:"left"|"right"|"unrecognized",
  source_location:Location
}
BackboneCoordinatePair = {
  pair_index:UInt, member_index_0based:UInt|null,
  native_left:NativeNumber|null, native_right:NativeNumber|null,
  state:MemberState,
  strand:Strand|null, interval_0based_half_open:Interval|null,
  source_location:Location
}
BackboneRow = {
  row_index:UInt, raw_line:RawText, pairs:BackboneCoordinatePair[],
  extra_tokens:RawLine[], source_location:Location,
  completeness:ParseCompleteness
}
BackboneDocument = {
  schema_version:"mauve_backbone_document_v1",
  document_id:Text, artifact:Artifact,
  dialect:"libmems_signed_coordinate_pairs_v1", encoding:"ascii"|"utf-8",
  header:RawLine|null, columns:BackboneHeaderColumn[],
  rows:BackboneRow[], unparsed:RawLine[], completeness:ParseCompleteness
}
BackboneParseResult = {
  status:"ok"|"partial"|"invalid", value:BackboneDocument|null,
  diagnostics:Diagnostic[]
}
BBColsRow = {
  row_index:UInt, raw_line:RawText,
  native_interval_index_0based:NativeNumber|null,
  native_left_column_1based:NativeNumber|null,
  native_column_count:NativeNumber|null,
  native_member_indices_0based:NativeNumber[],
  columns_0based_half_open:Interval|null,
  state:"parsed"|"incompatible"|"incomplete",
  source_location:Location
}
BBColsDocument = {
  schema_version:"mauve_bbcols_document_v1",
  document_id:Text, artifact:Artifact,
  dialect:"libmems_interval_columns_members_v1", encoding:"ascii"|"utf-8",
  rows:BBColsRow[], unparsed:RawLine[], completeness:ParseCompleteness
}
BBColsParseResult = {
  status:"ok"|"partial"|"invalid", value:BBColsDocument|null,
  diagnostics:Diagnostic[]
}
```

`BackboneHeaderColumn` preserves both the final `seq0_leftend` spelling and the intermediate native `seq_0_leftend` spelling, with an explicit diagnostic if the selected final-producer evidence does not match the actual header. Duplicate/missing member endpoints are conflicts, not permission to pair adjacent arbitrary columns. `pair_index` preserves observed pair order; unresolved member index is null. A one-token row remains incomplete with its available native number, not converted into absence. Negative endpoints must have equal sign and increasing absolute endpoint; `0,0` alone is explicit absence.

BBCols is headerless: first three native tokens and all subsequent member tokens are preserved. Duplicate member tokens, invalid ordinals, nonpositive left/length or missing operands are diagnosed. Empty BBCols bytes are a recognizable **possible empty record list only because an explicit dialect was selected**: return document with unknown scientific completeness and no claimed zero backbone coverage; associated task/producer evidence must resolve empty-result meaning. Empty backbone without a header cannot establish member cardinality. Do not invent member rows. Per-row native syntax validity is separate from external block/member join validity.

```text
BackboneSelection = {
  schema_version:"mauve_backbone_selection_v1",
  document_id:Text, population_id:Text,
  members:NativeMember[], row_indices:UInt[],
  minimum_selected_multiplicity:Positive,
  denominator:"none"|"validated_staged_length",
  population_scope:"selected_rows"|"all_observed_document_rows",
  evidence:Evidence[]
}
BBColsSelection = {
  schema_version:"mauve_bbcols_selection_v1",
  document_id:Text, population_id:Text,
  members:NativeMember[], row_indices:UInt[],
  minimum_selected_multiplicity:Positive,
  calculate_bound_block_fraction:boolean,
  population_scope:"selected_rows"|"all_observed_document_rows",
  evidence:Evidence[]
}
BackboneRowComponents = {
  row_index:UInt, selected_present_members:NativeMember[],
  selected_absent_members:NativeMember[], unresolved_members:NativeMember[],
  selected_member_count:NumericCell,
  selected_by_multiplicity:boolean|null,
  member_spans:{member:NativeMember, state:MemberState,
    interval_0based_half_open:Interval|null, strand:Strand|null,
    span_bases:NumericCell, evidence:Evidence[], requirement_ids:Text[]}[]
}
SidecarPlacement = {
  document_id:Text, row_index:UInt, member:NativeMember,
  interval_0based_half_open:Interval, strand:Strand,
  evidence:Evidence[]
}
BackboneMemberCoverage = {
  member:NativeMember, placements:SidecarPlacement[],
  known_union_intervals:Interval[], known_union_bases:NumericCell,
  placement_bases:NumericCell, multiply_represented_bases:NumericCell,
  excess_placement_bases:NumericCell,
  denominator_kind:"none"|"validated_staged_length",
  denominator_bases:NumericCell, coverage_fraction:NumericCell,
  complement_intervals:Interval[]|null, complement_bases:NumericCell,
  population_state:"complete_selected"|"partial_selected"|"unknown",
  evidence:Evidence[], requirement_ids:Text[]
}
BackboneComponents = {
  schema_version:"mauve_backbone_components_v1",
  document_id:Text, status:"ok"|"partial"|"invalid",
  selection:BackboneSelection, rows:BackboneRowComponents[],
  coverage:BackboneMemberCoverage[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
BBColsRowComponents = {
  row_index:UInt, native_interval_index_0based:UInt|null,
  selected_present_members:NativeMember[], unresolved_member_tokens:NativeNumber[],
  selected_member_count:NumericCell, selected_by_multiplicity:boolean|null,
  column_count:NumericCell,
  xmfa_document_id:Text|null, xmfa_block_index:UInt|null,
  join_state:AssociationState,
  evidence:Evidence[], requirement_ids:Text[]
}
BBColsIntervalComponents = {
  native_interval_index_0based:UInt,
  contributing_row_indices:UInt[], known_union_intervals:Interval[],
  union_columns:NumericCell, column_placements:NumericCell,
  multiply_represented_columns:NumericCell, excess_column_placements:NumericCell,
  xmfa_document_id:Text|null, xmfa_block_index:UInt|null,
  bound_block_width:NumericCell, selected_block_fraction:NumericCell,
  population_state:"complete_selected"|"partial_selected"|"unknown",
  evidence:Evidence[], requirement_ids:Text[]
}
BBColsComponents = {
  schema_version:"mauve_bbcols_components_v1",
  document_id:Text, status:"ok"|"partial"|"invalid",
  selection:BBColsSelection,
  rows:BBColsRowComponents[], intervals:BBColsIntervalComponents[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
```

All B selected members use the sidecar namespace. Selected multiplicity counts only the declared subset; threshold must not exceed its size. Row eligibility is a selection predicate, not a confidence score. Unknown member correspondence gives null eligibility, not false. Per-member coverage uses only eligible valid selected rows, retaining unresolved-row qualifications. BBCols union counts on their native interval axis do not need an XMFA join; a block-width denominator does. Nothing in B joins backbone rows to BBCols rows.

## C: actual input and artifact association boundary

Exact signatures, superseding C's broader sketch in proposal 001:

```python
extract_genome_alignment_inputs(original_task: dict, *,
    supplied_values: tuple[dict, ...],
    supplied_bytes: dict[str, bytes]) -> dict  # InputExtraction
bind_genome_alignment_artifacts(original_task: dict, *,
    artifacts: tuple[dict, ...], parsed_artifacts: tuple[dict, ...],
    supplied_values: tuple[dict, ...],
    inputs: dict | None) -> dict  # AssociationResult
validate_genome_alignment_inputs(inputs: dict) -> dict
validate_genome_alignment_associations(associations: dict) -> dict
```

`supplied_values` retains the host's exact `{evidence:Evidence,value:MetadataValue}` wrapper. Here `MetadataValue` is a closed discriminated union below; any other supplied value is retained by host custody but not interpreted as provider metadata. The exact format decision is no longer inferred by C from artifact names: `parsed_artifacts` supplies the actual reader result and document artifact binding. The parser owner cannot certify remote task custody; C cannot claim an observed format without actual parsed bytes.

```text
GenomeOccurrence = {
  occurrence_index:UInt, genome_id:Text,
  parameter_pointer:Text, input_binding_id:Text|null,
  evidence:Evidence[]
}
RetrievalPopulation = {
  query:RawText|null, requested_record_limit:UInt|null,
  reported_total_records:UInt|null, returned_records:UInt,
  state:"complete"|"partial"|"unknown"|"conflicting",
  evidence:Evidence[]
}
InputFile = {
  file_id:Text, native_path_token:Text|null,
  path_state:AssociationState,
  artifact:Artifact|null, content:Content|null,
  format:"FastA", genome_occurrence_indices:UInt[],
  same_run_state:AssociationState,
  record_completeness:"complete"|"partial"|"unknown",
  records:FastaRecord[], retrieval:RetrievalPopulation,
  path_evidence:Evidence[], same_run_evidence:Evidence[],
  requirement_ids:Text[]
}
MemberComponent = {
  file_id:Text, record_id:Text,
  member_interval_0based_half_open:Interval,
  record_interval_0based_half_open:Interval
}
MemberBinding = {
  member:NativeMember, state:AssociationState,
  genome_occurrence_indices:UInt[],
  components:MemberComponent[], source_length:UInt|null,
  evidence:Evidence[], requirement_ids:Text[]
}
ContigBinding = {
  file_id:Text, record_id:Text,
  sequence_id:Text|null, accession:Text|null, accession_version:Text|null,
  genome_occurrence_indices:UInt[],
  state:AssociationState, evidence:Evidence[], requirement_ids:Text[]
}
FeatureSegment = {
  segment_id:Text, file_id:Text, record_id:Text,
  feature_interval_0based_half_open:Interval,
  record_interval_0based_half_open:Interval,
  strand:Strand, transformation_id:Text, evidence:Evidence[]
}
FeatureBinding = {
  feature:Occurrence, original_length:UInt|null,
  genome_occurrence_index:UInt,
  segments:FeatureSegment[], state:AssociationState,
  evidence:Evidence[], requirement_ids:Text[]
}
Invocation = {
  requested_recipe:"progressiveMauve"|"mauveAligner"|null,
  effective_recipe:"progressiveMauve"|"mauveAligner"|null,
  recipe_basis:"observed_argv"|"retained_source_default"|"unknown"|"conflicting",
  observed_argv:RawText[]|null, observed_program_version:Text|null,
  mode:"multiple_files_concatenated"|"single_file_entries"|"unknown",
  mode_basis:"observed_invocation"|"source_and_submitted_parameters"|"unknown"|"conflicting",
  ordered_file_ids:Text[], evidence:Evidence[]
}
GenomeAlignmentInputs = {
  schema_version:"bvbrc_genome_alignment_inputs_v1",
  original_task:OriginalTask,
  genome_occurrences:GenomeOccurrence[], invocation:Invocation,
  files:InputFile[], member_bindings:MemberBinding[],
  contig_bindings:ContigBinding[], feature_bindings:FeatureBinding[],
  original_maps:OriginalMap[],
  xmfa_source_inputs:XMFAInputs|null,
  genome_census_state:"complete"|"partial"|"unknown"|"conflicting",
  requirements:Requirement[], diagnostics:Diagnostic[]
}
InputExtraction = {
  status:"ok"|"partial"|"invalid",
  value:GenomeAlignmentInputs|null,
  requirements:Requirement[], diagnostics:Diagnostic[]
}
```

The C output includes one requested genome occurrence for every original list entry, including duplicates. `input_binding_id` is null when no actual parent input binding exists; never fabricate an original input identity for convenience. Missing files may be represented by an identified file expectation with null artifact/content and empty records; that does not assert a measured zero sequence length. Components preserve ordered concatenation offsets, and intervals have equal lengths. Bound complete multi-file native members cover the concatenated entire ordered records; one-file progressive members each correspond to their actual entry. A native file token must match the exact observed path, or be connected by explicit transformation evidence. Basename stripping is insufficient.

Feature segment intervals must have equal lengths and be bounded by known source/feature lengths. Overlap/duplication is retained and diagnosed; it does not manufacture multiple original bases. Only validated explicit mappings populate neutral `OriginalMap` rows. Entire-feature denominators require a known original feature length; partial mappings do not become complete through inferred gaps.

`xmfa_source_inputs` is produced only when its fields are supported by validated C records; otherwise it is null or contains only the allowed explicit partial source records under the existing neutral contract. Do not set complete neutral record populations when metadata lists only a subset. The downstream neutral source comparison remains mandatory for actual XMFA rows. A source-predicted invocation alone does not make staged bytes same-run bound.

Closed supplied metadata types:

```text
InvocationMetadata = {
  kind:"genome_alignment_invocation", original_task_id:Text,
  argv:RawText[], program_version:Text|null,
  ordered_file_ids:Text[], mode:"multiple_files_concatenated"|"single_file_entries"
}
InputFileMetadata = {
  kind:"genome_alignment_staged_file", original_task_id:Text,
  file_id:Text, native_path_token:Text, content:Content,
  genome_occurrence_indices:UInt[], retrieval:RetrievalPopulation
}
ContigMetadata = {
  kind:"genome_alignment_contig_identity", original_task_id:Text,
  file_id:Text, record_id:Text, sequence_id:Text|null,
  accession:Text|null, accession_version:Text|null,
  genome_occurrence_indices:UInt[]
}
FeatureMetadata = {
  kind:"genome_alignment_feature_mapping", original_task_id:Text,
  feature:Occurrence, original_length:UInt,
  genome_occurrence_index:UInt, segments:FeatureSegment[]
}
IntervalMapMetadata = {
  kind:"genome_alignment_interval_mapping", original_task_id:Text,
  bbcols_artifact:Artifact, xmfa_artifact:Artifact,
  mappings:{native_interval_index_0based:UInt,xmfa_block_index:UInt}[],
  omitted_native_interval_indices:UInt[]
}
ProducerMetadata = {
  kind:"genome_alignment_producer", original_task_id:Text,
  application_id:"GenomeAlignment",
  recipe:"progressiveMauve"|"mauveAligner",
  producer_source:Content, native_version:Text|null,
  output_artifacts:Artifact[]
}
MetadataValue = InvocationMetadata|InputFileMetadata|ContigMetadata|
                FeatureMetadata|IntervalMapMetadata|ProducerMetadata
SuppliedValue = {evidence:Evidence, value:MetadataValue}
```

These metadata records are **typed extraction results from retained actual records**, not new claims that a model can certify by writing JSON. A new extractor must bind each field to the actual recorded source pointer/bytes and validate its relationships. The host authenticates possession and raw evidence; C checks task equality, source format, actual record content, content hashes and producer-specific meaning. If no retained native/verified staging record establishes same-run file identity or internal interval mapping, keep `unverified`/`missing` and emit the requirement. The existing service does not emit these witnesses, so many live results will initially lack them. Fabricating an `InputFileMetadata` or `IntervalMapMetadata` document does not resolve the gap.

```text
ParsedArtifact = {
  artifact:Artifact,
  format:"mauve1_xmfa"|"mauve_v4"|"mauve_backbone"|"mauve_bbcols",
  parse_status:"ok"|"partial"|"invalid",
  document:XMFADocument|MauveV4Document|BackboneDocument|BBColsDocument|null,
  diagnostics:Diagnostic[]
}
AssociatedArtifact = {
  artifact:ArtifactMember,
  role:"genome_alignment_primary"|"genome_alignment_backbone"|"genome_alignment_bbcols"|"genome_alignment_visualization",
  observed_format:"mauve1_xmfa"|"mauve_v4"|"mauve_backbone"|"mauve_bbcols"|"p3_mauve_visualization_json"|null,
  document_id:Text|null,
  state:AssociationState,
  evidence:Evidence[], requirement_ids:Text[]
}
NativeMemberJoin = {
  artifact:Artifact, member:NativeMember,
  input_member:NativeMember|null,
  state:AssociationState,
  evidence:Evidence[], requirement_ids:Text[]
}
BBColsIntervalJoin = {
  bbcols_document_id:Text, native_interval_index_0based:UInt,
  xmfa_document_id:Text|null, xmfa_block_index:UInt|null,
  state:AssociationState,
  evidence:Evidence[], requirement_ids:Text[]
}
DuplicateRepresentation = {
  sha256:SHA256, raw_artifact_refs:Text[],
  source_refs:Text[], scientific_identity:"same_bytes_only"|"same_original_task_bytes"
}
ArtifactAssociations = {
  schema_version:"bvbrc_genome_alignment_associations_v1",
  original_task:OriginalTask,
  artifacts:AssociatedArtifact[],
  native_member_joins:NativeMemberJoin[],
  bbcols_interval_joins:BBColsIntervalJoin[],
  duplicate_representations:DuplicateRepresentation[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
AssociationResult = {
  status:"ok"|"partial"|"invalid",
  value:ArtifactAssociations|null,
  requirements:Requirement[], diagnostics:Diagnostic[]
}
```

`ParsedArtifact.format` must agree with the actual schema discriminator, parser parameters and raw artifact hash. Visualization JSON has no A/B parser and cannot acquire an observed scientific document through this interface; C may retain an associated visualization artifact with `document_id=null`, but must not claim byte-observed JSON structure without a separately selected reader. Its unknown observed format remains null unless actual typed evidence supplies it. The role must match the original selected output requirement and native producer rule. Declared format conflicts remain conflicts, even when a different reader could parse the bytes. Do not silently select that alternative.

The sidecar member mapping uses index0 to corresponding invocation member, then index0+1 only for an actually bound XMFA member. BBCols internal interval -> exported XMFA block needs explicit retained mapping or a validated producer proof that no internal interval was skipped. Matching array length or a plausible column width alone is insufficient. Native BBCols measurements survive a missing block join.

## Failure and missing-input contract shared by A/B/C

Improper **function arguments** (wrong Python types, unsupported explicit dialect/encoding, malformed closed contract or invalid caller selection) raise `ValueError` with a stable prefix and code. They are programmer/contract errors, not biological zero. Data-dependent native malformation returns typed results and diagnostic records. Every independently recoverable row is retained; no blanket exception discards valid partial work.

Parser code set, prefixed `mauve_v4_`, `mauve_backbone_` or `mauve_bbcols_` as appropriate. Unchanged neutral XMFA outputs retain their existing finite `xmfa_` diagnostic sets; the provider does not rename or broaden those codes:

```text
bytes_required, artifact_invalid, encoding_unsupported, dialect_unsupported,
digest_mismatch, encoding_invalid, empty_input, format_unrecognized,
version_unsupported, header_missing, header_malformed, metadata_duplicate,
metadata_conflict, count_invalid, count_conflict, member_invalid,
member_duplicate, interval_ordinal_invalid, interval_ordinal_duplicate,
segment_header_malformed, missing_sequence_row, extra_sequence_row,
width_conflict, sequence_symbol_invalid, coordinate_invalid,
zero_member_has_residues, header_member_conflict, row_incomplete,
unparsed_line
```

`digest_mismatch`, undecodable bytes or a different/unrecognizable required primary format => `invalid`, `value=null`. Recognizable native content with local malformed/missing rows => `partial` and a retained document. Valid retained syntax => `ok`; the document may still have unknown scientific completion. Empty primary v4/XMFA is not a measured zero result. Explicitly declared empty BBCols uses the qualified behavior above.

Extractor/association code set, prefixed `bvbrc_genome_alignment_`:

```text
argument_invalid, original_task_invalid, application_mismatch,
genome_input_missing, genome_occurrence_conflict, duplicate_genome_occurrence,
recipe_conflict, explicit_zero_not_forwarded, source_option_unsupported,
invocation_missing, invocation_conflict, metadata_type_unsupported,
metadata_record_unverified, metadata_task_conflict, content_missing,
content_digest_conflict, staged_file_missing, staged_file_run_unverified,
native_path_missing, native_path_conflict, source_records_partial,
source_sequence_mismatch, source_span_outside_input, genome_census_unknown,
contig_identity_missing, contig_identity_conflict, feature_map_missing,
feature_map_conflict, artifact_task_conflict, artifact_version_unverified,
artifact_role_conflict, artifact_format_conflict, primary_output_missing,
duplicate_representation, member_join_missing, member_join_conflict,
interval_join_missing, interval_join_conflict, native_execution_unverified
```

Requirements retain the existing shape and use corresponding exact reason codes, e.g. `kind=input_bytes, role=genome_alignment_staged_input, reason_code=bvbrc_genome_alignment_staged_file_missing`; missing same-run identity is separate from missing bytes. No requested selected file is replaced with another one. Invalid original-task/application shape returns invalid/null if data-dependent; invalid explicit typed caller arguments raise before analysis. Local conflicts retain unrelated useful records and produce partial. Full absent optional inputs still produce a partial extraction object containing requested occurrences, native expectations and all requirements.

Calculator code sets reuse the relevant parser/association causes and add only `selection_invalid`, `selection_document_conflict`, `selection_member_unknown`, `selection_record_unknown`, `selection_column_outside_record`, `selection_population_incomplete`, `pair_not_coobserved`, `source_symbols_missing`, `source_denominator_missing`, `zero_denominator`, `overlapping_placement`, `bbcols_block_unbound`, `bbcols_column_outside_block`. Diagnostic code selection is finite; evidence/source pointers supply specifics without unbounded prose findings.

NumericCell rules remain unchanged. A known finite count may remain available for an explicitly known partial subset, with `population_state=partial_selected`; a whole-population fraction dependent on missing records is null/truncated. Missing inputs are not failed computations; malformed dependent native values are incompatible; transport failure is retained from acquisition rather than invented by a pure reader. Uncertainty is not synthesized.

## D/E handoff and retained missing requirements

A/B/C are assignable from the closed records above. Their output sets for D are fixed: `GenomeAlignmentInputs|null`, `ArtifactAssociations`, every parsed native document, the explicit selection and their complete requirements/diagnostics. D must not invent alternate parser/member/selection shapes. The published sheet must contain actual numerical measurements, including unavailable cells where prerequisites are missing. A source-document inventory by itself is not the completed sheet. Exact provider sheet and numerical component envelopes:

```text
MeasurementSet =
  {kind:"mauve_v4_segments", value:V4SegmentComponents} |
  {kind:"mauve_backbone", value:BackboneComponents} |
  {kind:"mauve_bbcols", value:BBColsComponents} |
  {kind:"xmfa_alignment", value:XMFAAlignmentComponents} |
  {kind:"xmfa_coverage", value:XMFACoverageComponents} |
  {kind:"xmfa_coordinates", value:XMFACoordinates} |
  {kind:"xmfa_inverse_coordinates", value:XMFAInverseCoordinates}
GenomeAlignmentComponents = {
  schema_version:"bvbrc_genome_alignment_components_v1",
  analysis_id:Text, measurements:MeasurementSet[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
GenomeAlignmentSheet = {
  schema_version:"bvbrc_genome_alignment_sheet_v1",
  analysis_id:Text, original_task:OriginalTask,
  inputs:GenomeAlignmentInputs|null, associations:ArtifactAssociations,
  parsed_artifacts:ParsedArtifact[], measurements:MeasurementSet[],
  requirements:Requirement[], diagnostics:Diagnostic[]
}
```

Native numbers remain in parsed documents; the sheet's `measurements` also contains the populated A/B outputs or unchanged XMFA outputs with actual NumericCells. If the adapter publishes a separate component artifact, its `analysis_id` and entire `measurements` array must equal those in the sheet; no second calculation or inconsistent duplicate is allowed. Use a final sheet constructor that receives already calculated components, superseding the earlier circular sketch:

```python
build_genome_alignment_sheet(*, original_task: dict, associations: dict,
    inputs: dict | None, parsed_artifacts: tuple[dict, ...],
    components: dict) -> dict  # GenomeAlignmentSheet
```

D calculates from the immutable parsed artifacts, C bindings and explicit typed selections using A/B or public XMFA functions, then populates the sheet. The builder validates document/selection identities and every copied numeric relationship. Optional additional aggregate or feature-specific component variants require their own closed record before implementation; existing XMFA original-coordinate and original-coverage records already support explicitly mapped features. Do not invent an open miscellaneous-score slot. The episode-facing projection remains selected and small.

**Correction to proposal 001:** do not drop optional missing requirements from `AdapterResult.missing_requirements` to work around publication completion. Retain the union of all sheet/component requirements and diagnostics in the adapter output. Use explicit versioned requested-projection semantics for `(bvbrc_genome_alignment,"1")` in `AppServicePublications._requested_status`, analogous in mechanism to the existing specifically enumerated versioned providers, without changing their historical values. The new adapter's `status` is `ok` only when every dependency of the exact original requested projection is satisfied; unrelated missing retained inputs remain in `missing_requirements` and remain visible. Bundle required-artifact failure still blocks original requested completion. Integration tests must cover both a requested native pair count with missing optional FASTAs and a requested source fraction with missing required FASTAs. The full missing facts must survive both cases and immutable replay.

The sole shared integration owner makes that provider-version addition after E's status semantics and F's typed return validations are complete. There is no runtime reviewer, approval step, controller change or extra observation.

## Independent ownership check

A owns the exact V4 document, selection and component records and corresponding new functions/files. B owns the exact backbone/BBCols records and functions. C owns the exact input/association records, typed metadata extraction, source validation and provider tool information. They may import existing numerical/evidence helpers but cannot edit them without a new explicit owner. A/B consume C's frozen input shape; they do not implement their own acquisition/provenance vocabulary. E/F/G still follow the nonoverlapping file ownership in proposal 001. This document resolves handoff ambiguity; it does not assert that the contracts or a live service path are already implemented.
