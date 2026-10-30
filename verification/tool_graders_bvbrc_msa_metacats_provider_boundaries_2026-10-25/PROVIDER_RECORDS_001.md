# Proposed production records — C-L204-MSA and C-L205-MetaCATS

Status: contract proposal for root acceptance, 2026-10-25. This task changes no production code. The accepted pure contracts in `../tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/ACCEPTED_PURE_INTERFACES_001.md` and `INTERFACE_CLARIFICATIONS_002.md` remain authoritative for existing functions. The types below specify the missing provider layer. `CALCULATIONS_001.md`, `BUNDLE_AND_RETURN_001.md`, and `WORKLOADS_001.md` complete this proposal.

All records are closed: every listed key is required, including nullable keys; extra keys fail validation. JSON arrays preserve order. An `int` excludes `bool`; a `number` is finite and excludes `bool`; `id` is a nonempty string; `text` permits empty strings; `index` is an integer >= 0; `positive` is an integer >= 1. Lists of identities and selected indices are unique unless native duplicates are explicitly retained. All coordinates are zero based, half open except a field expressly named `1based`. `Completeness = complete|partial|truncated|unknown`; `State = available|missing|not_measured|failed|truncated|incompatible`. Missing values never become measured zero.

## Existing value contracts reused without alteration

These are exact aliases to the installed validators, not copies to evolve independently:

```text
Content = {source_ref:id, artifact_field:artifact_ref|text_ref|stdout_ref|stderr_ref,
           artifact_ref:id, sha256:64-lowercase-hex, byte_count:index}
Evidence = {content:Content, pointer:valid JSON pointer}
Artifact = {raw_artifact_ref:id, source_ref:id, sha256:64-lowercase-hex}
Location = {artifact:Artifact, byte_start_0based:index|null,
  byte_end_0based_exclusive:index|null, line_start_1based:positive|null,
  line_end_1based_inclusive:positive|null, xml_path:text|null}
Diagnostic = {code:id, phase:custody|prepare|transport|native_decode|association|
  publication|recovery|return, path:JSON-pointer, severity:error|qualification,
  evidence_refs:[id]}
Requirement = {requirement_id:id, kind:definition|input_metadata|input_bytes|
  original_task|task_manifest|output_metadata|output_bytes|byte_version_evidence|
  scientific_metadata|parser_binding, role:id|null, source_refs:[id], reason_code:id}
NativeNumber = {raw_token:text, value:number|null, state:State,
  token_kind:finite|blank|native_na|underflow|overflow|nonfinite|malformed,
  source_location:Location}
NumericCell = {value:number|null, state:State, unit:id,
  origin:native_observation|calculated|fitted, numerator:number|null,
  denominator:number|null, population_id:id, method_id:id, evidence:[Evidence],
  uncertainty:null|{kind:confidence_interval|standard_error|standard_deviation|
    native_unknown, lower:number|null, upper:number|null, value:number|null,
    method_id:id}, requirement_ids:[id]}
SharedQuantity = {value:number|null, state:State, unit:id,
  origin:derived|native_observed|native_fitted, numerator:number|null,
  denominator:number|null, population_ref:id, method:id, evidence:[Evidence],
  requirement_ids:[id]}
ParseResult[T] = {status:ok|partial|invalid, value:T|null, diagnostics:[Diagnostic]}
```

Locations retain byte and/or line/XML evidence; range pairs must agree. `bvbrc_alignment_values.py` owns `NativeNumber`/`NumericCell`; `phylogeny_calculation_contracts.py` owns `SharedQuantity`. Do not coerce one cell schema into the other in saved components. An incompatible native numeric token may retain its finite value; an outward scalar is available only when its state is `available`. Exact decimal token bounds precede binary64 conversion.

```text
AlignmentRow = {row_index:index, raw_header:text, member_label:text,
                sequence:text, source_location:Location}
AlignmentDocument = {alignment_id:id, artifact:Artifact,
  format:aligned_fasta|relaxed_phylip, layout:fasta|sequential|interleaved,
  id_rule:id, encoding:ascii|utf-8, declared_row_count:index|null,
  declared_column_count:index|null, observed_row_count:index,
  observed_column_count:index|null, completeness:Completeness, rows:[AlignmentRow]}
AlignmentPopulation = {population_id:id, alignment_id:id, row_indices:[index],
  columns_0based:[index], completeness:Completeness, evidence:[Evidence]}
MemberRef = {input_binding_id:id, member_id:id}
Correspondence = {alignment_id:id, row_index:index, column_0based:index,
  staged_ungapped_position_0based:index|null, original_member:MemberRef|null,
  original_interval_0based_half_open:[index,index]|null,
  strand:+|-|unknown, translation_table:positive|null,
  transformation_id:id|null, evidence:[Evidence]}
Subject = {kind:input_member|feature|genome, id:id, source_record_id:id}
CompositionPopulation = {population_id:id, unit:sequence_member|feature,
  member_subjects:[Subject], assignment_completeness:Completeness,
  membership_completeness:Completeness, evidence:[Evidence]}
TaxonPopulation = CompositionPopulation with unit:sequence_member|feature|genome
FunctionAssignment = {assignment_id:id, subject:Subject, function_key:id,
  function_label:text, source_record_id:id, evidence:[Evidence]}
FunctionEquivalence = {equivalence_id:id, function_keys:[id],
  canonical_function_key:id, evidence:[Evidence]}
TaxonAssignment = {subject:Subject, taxon_id:id, rank:id|null,
  lineage:[{taxon_id:id,rank:id|null}], source_record_id:id, evidence:[Evidence]}
```

`AlignmentDocument` validates with `phylogeny_format_contracts.validate_alignment_document`; its ID remains `artifact.raw_artifact_ref + '#alignment'`. Row indices are physical parsed-row indices, not FASTA labels. Existing pure format documents below are retained **whole**, including rows, exact headers, original row ordinals, malformed numeric tokens, source locations, completeness and diagnostics:

| Stored type | Installed validator and complete definition |
|---|---|
| MSAFrequencyTable | `bvbrc_msa_format_contracts.validate_msa_frequency_table` |
| MetaCATSChiSquareTable | `bvbrc_metacats_format_contracts.validate_metacats_chisq_table` |
| MetaCATSPairTable | `...validate_metacats_pair_table` |
| MetaCATSRawRTable | `...validate_metacats_raw_r_table` |
| MetadataDocument | `...validate_metacats_metadata` |
| AdjustedMatrix | `...validate_metacats_adjusted_matrix` |
| TreeDocument/TreeRecord | exact `parse_newick` document envelope; each tree uses `phylogeny_format_contracts.validate_tree_record` |

The accepted pure-contract document and those complete implementation definitions are normative dependencies; providers add no alternate shape for them. `NATIVE_DOCUMENT_RECORDS_001.md` enumerates every nested record for readers implementing this new provider boundary. There is no installed `validate_tree_document` function; the provider validates the declared Newick envelope and every contained tree with the existing tree-record validator. In particular protein detail is a list, pair-group text is unsplit, raw R indices remain 1 based numeric tokens, and R/export group labels remain exact strings. A wrapper `ParsedDocument` is exactly `{kind, value}`, with kind one of `alignment|msa_frequency|metacats_chisq|metacats_pair|metacats_raw_r|metadata|adjusted_matrix|tree` and the corresponding value type above.

## Original input and transformation associations

Host `InputBinding` and `MemberFact` are copied unchanged from the original request. The host permits unique `member_id` per binding; a FASTA may nevertheless contain repeated labels. The provider therefore has a separate occurrence identity:

```text
MemberKey = {input_binding_id:id, member_id:id, occurrence_index:index}
OriginalMember = {key:MemberKey, host_member_id:id|null, original_input_pointer:JSON-pointer,
  source_document_id:id|null, source_row_index:index|null, raw_header:text|null,
  member_label:text|null, sequence_sha256:64-lowercase-hex|null,
  original_length:index|null, molecule:dna|rna|protein|mixed|unknown,
  feature_ids:[id], genome_ids:[id], source_record_ids:[id], evidence:[Evidence]}
InlineSequenceInput = {input_binding_id:id,parameter_pointer:JSON-pointer,
  id_rule:'first_whitespace_token',encoding:ascii|utf-8,completeness:Completeness,
  rows:[InlineSequenceRow],members:[OriginalMember],requirements:[Requirement],
  diagnostics:[Diagnostic]}
InlineSequenceRow = {row_index:index,raw_header:text,member_label:text,sequence:text,
  character_start_0based:index,character_end_0based_exclusive:index,
  line_start_1based:positive,line_end_1based_inclusive:positive}
RowMemberAssociation = {association_id:id, alignment_id:id, row_index:index,
  member_keys:[MemberKey], transformation_ids:[id],
  state:resolved|missing|conflicting|native_duplicate_merge,
  basis:explicit_map|exact_unique_header|exact_unique_sequence|transformation_record|unresolved,
  evidence:[Evidence]}
FeatureGenomeAssociation = {feature_id:id, genome_id:id, source_record_id:id,
  evidence:[Evidence]}
SourceRecord = {source_record_id:id, kind:original_input|feature|genome|sequence|
  function_assignment|taxonomy|metadata|native_run|parent_declaration,
  evidence:Evidence}
```

`occurrence_index` counts physical occurrences of the exact `member_id` within the binding. It is not a row index in an unrelated output. A retained input row supplies a known occurrence even when a host member fact is unavailable (`host_member_id=null`). An exact unique header join is permitted only under an explicitly selected header rule and actual uniqueness on both sides. Sequence equality is a selected fallback only if exactly one eligible original occurrence matches with the declared transformation; equal duplicate sequences remain ambiguous. No zip of sorted lists, taxon-only join, substring match or arbitrary first hit. Resolved associations can have multiple member keys only for a documented concatenation; they cannot be lowered to shared `MemberRef` as if one original sequence existed. Lowering to existing coverage/reference calculators requires a one-member association and unique original `MemberRef`; otherwise retain the occurrence and return `original_member_occurrence_ambiguous` for that calculation.

Inline FASTA is the actual authenticated `InputBinding(kind='inline_parameter').inline_value`, such as MSA `fasta_keyboard_input`. Its `parameter_pointer` remains tied to original submitted parameters by host validation. `InlineSequenceRow` ranges refer to Unicode character offsets and physical lines within that exact supplied string, not a fabricated byte artifact. It preserves duplicate rows, raw headers, case and all non-layout symbols. Formatting spaces/tabs may be removed from parsed sequence only with explicit diagnostics while the complete original string remains in InputBinding. Member sequence hashes use the declared encoding; unencodable strings retain content with null hash and an encoding diagnostic. `source_document_id=null`, `source_row_index=physical inline row index`; never fabricate Artifact or AlignmentDocument. Duplicate labels cannot inherit a unique host member identity simply because a host member fact of that name exists.

```text
TransformBase = {transformation_id:id, kind:<tag>, input_members:[MemberKey],
  input_rows:[{alignment_id:id,row_index:index}],
  output_rows:[{alignment_id:id,row_index:index}], evidence:[Evidence]}
Transformation = TransformBase plus exactly the tag-specific fields:
  identity: {}
  rename: {mappings:[{input_member:MemberKey, before:text, after:text}]}
  uppercase: {}
  remove_symbols: {symbols:[one-character-string]}
  align_insert_gaps: {gap_symbol:'-'}
  reverse_complement: {alphabet:dna|rna}
  translate: {translation_table:positive|null, frame:0|1|2,
              strand:+|-, input_intervals:[[index,index]]}
  concatenate: {segment_order:[id], output_intervals:[{segment_id:id,
                 interval_0based_half_open:[index,index]}]}
  missing_segment_gap_fill: {segment_id:id, output_interval_0based_half_open:[index,index]}
  native_terminal_dash_to_hash: {alignment_id:id, row_indices:[index]}
  native_duplicate_merge: {native_key:text, rule:overwrite_last|concatenate_in_order}
  native_first_contig: {genome_id:id, genome_sequence_record_id:id}
  mauve_first_block_projection: {xmfa_slot_id:id, block_index:0,
                native_input_order:[MemberKey]}
```

No transform is inferred just because a source code branch exists. Preserve source-declared possibility separately from observed transformation evidence. `translate.translation_table=null` is an unresolved map, not assumed standard code. Full original intervals require explicit correspondence, including reverse strand, translation, stripping and concatenation. `native_terminal_dash_to_hash` describes a known stage: it never recasts an input `#` as a generated mask.

```text
Segment = {segment_id:id, native_segment_token:text, genome_id:id|null,
  genome_sequence_record_id:id|null, contig_id:id|null,
  original_interval_0based_half_open:[index,index]|null, strand:+|-|unknown,
  input_member:MemberKey|null, alignment_id:id|null,
  concatenated_interval_0based_half_open:[index,index]|null,
  order_index:index|null, state:resolved|missing|conflicting, evidence:[Evidence]}
ReferenceBinding = {alignment_id:id, row_index:index, original_member:MemberRef|null,
  native_ref_type:id, native_ref_string:text|null, identity_state:resolved|unresolved,
  evidence:[Evidence]}
ConsensusAssociation = {consensus_alignment_id:id, consensus_row_index:index,
  source_alignment_id:id, source_population_id:id, frequency_table_id:id|null,
  columns:[{source_column_0based:index, consensus_position_0based:index|null,
            symbol:one-character-string}],
  method:native_table_consensus_then_remove_dash|unresolved,
  state:resolved|missing|conflicting, evidence:[Evidence]}
```

Consensus correspondence is extracted from the complete native frequency table's consensus tokens only when each alignment position is uniquely represented, the declared protein abbreviation mapping is known where required, and deleting its literal consensus dashes gives a byte-exact match to the retained consensus sequence. The source population must be explicitly associated. This is an association between two retained native artifacts, not a recalculation of majority/entropy inside the extractor. Non-majority `N`/`X` is distinct from deleting a majority gap. Without the native table, retain the sequence and an unresolved correspondence; later selected entropy calculation can still provide its separate computed majority values. The `.snp.tsv` is a position frequency table, not a list of per-member variant calls. `msa_reference_differences` supplies explicitly calculated per-member comparisons and their coordinate qualifications.

## MetaCATS category, biological group, R column and exported label

```text
Category = {category_id:id, metadata_document_id:id|null,
  metadata_column_index_0based:index|null, raw_heading_token:text|null,
  native_category_ordinal_1based:positive|null, native_output_stem:text|null,
  input_mode:files|groups|auto, group_ids:[id],
  state:resolved|missing|conflicting, evidence:[Evidence]}
BiologicalGroup = {group_id:id, category_id:id, raw_group_value:text,
  metadata_row_indices:[index], member_keys:[MemberKey],
  source_group_bindings:[FeatureGroupSource],
  membership_completeness:Completeness, evidence:[Evidence]}
FeatureGroupSource = {input_binding_id:id,group_id:id,source_record_id:id,
  evidence:[Evidence]}
AutoGroupEntry = {input_binding_id:id,entry_index_0based:index,
  original_parameter_pointer:JSON-pointer,feature_id:id,raw_group_value:text,
  member_keys:[MemberKey],evidence:[Evidence]}
MetadataMemberAssociation = {metadata_document_id:id, metadata_row_index:index,
  id_column_index_0based:index, raw_member_token:text, member_keys:[MemberKey],
  alignment_rows:[{alignment_id:id,row_index:index}],
  state:resolved|missing|conflicting|native_duplicate_merge, evidence:[Evidence]}
BiologicalAssignment = {category_id:id, alignment_id:id, row_index:index,
  member_key:MemberKey|null, group_id:id|null,
  state:resolved|missing|conflicting, evidence:[Evidence]}
BiologicalGroupPopulation = {group_population_id:id, category_id:id,
  groups:[{group_id:id,raw_group_value:text,evidence:[Evidence]}],
  completeness:Completeness, evidence:[Evidence]}
```

A group population is an explicit calculation population and explicit column order. It needs no R token. Its group list may include declared groups with zero observed sequence members; their zero margins are retained. Membership comes from actual alignment rows plus declared metadata/group records. Files mode does not uppercase implicitly. Groups mode requires actual feature-group membership/resource identity and sequence-acquisition evidence, not only two group names. Auto mode preserves every ordered original `auto_groups` `{id,grp}` entry, duplicates included, and its fetched sequence/member associations. Both groups and auto source branches uppercase retrieved sequences and run MAFFT, but their original membership provenance is distinct.

Existing native calculator inputs remain exactly:

```text
GroupAssignment = {category_id:id, alignment_id:id,row_index:index,
  member_key:MemberKey|null, metadata_row_index:index|null,
  metadata_column_index:index|null,raw_group_value:text|null,
  native_group_ordinal:positive|null,displayed_group_label:text|null,
  state:resolved|missing|conflicting|native_unlabeled,evidence:[Evidence]}
GroupColumn = {category_id:id,r_column_index_0based:index,r_group_token:id,
  native_group_ordinal:positive|null,group_id:id|null,
  exported_heading_index_0based:index|null,exported_label_token:text|null,
  state:resolved|wrong_native_label|unresolved,evidence:[Evidence]}
ExportedGroupAssociation = {category_id:id,table_id:id,
  heading_index_0based:index,raw_heading_token:text,group_id:id|null,
  r_column_index_0based:index|null,
  state:resolved|wrong_native_label|missing|conflicting,evidence:[Evidence]}
NativeTestAssociation = {association_id:id,category_id:id,
  table_id:id,row_index:index,test_kind:omnibus|pairwise,
  alignment_id:id|null,column_0based:index|null,group_ids:[id],
  r_columns_0based:[index],raw_groups_token:text|null,
  test_id:id|null,state:resolved|missing|conflicting|wrong_native_label,
  evidence:[Evidence]}
```

The association extractor must preserve all four identities: metadata value, native metadata ordinal, actual R column/index/token, exported label. Category ordinal and metadata column index also stay separate. Exact R evidence is mandatory only for native reproduction and native output joins. It may be an authenticated actual R `colnames(table(...))` observation tied to the category matrix and interpreter version, or equivalent actual column-identity evidence. Do not derive R tokens by sorting metadata. Twelve-group R 4.3.3 evidence uses `" 1"` through `" 9"`, then `"10"`, `"11"`, `"12"`; use corrected `EXAMPLES_002`, not the earlier unpadded provenance.

Metadata-only groups can shift exported headings. With metadata A/B/C but aligned rows only B/C, actual R columns correspond to native ordinals 2/3; exported headings can still be A/B/C. Preserve `wrong_native_label`; do not label B counts as A. Pair output `A,B` is unsplit native text until the complete category/export map establishes the corresponding test; commas inside biological group labels make string splitting especially invalid. Counts from adjusted matrices contain `#` but cannot identify whether it was original or generated without original-input/stage correspondence.

## Observed run and dependence records

```text
RunRecord = {original_task_id:id, settings:[Setting], commands:[Command],
  versions:[Version], conflicts:[SettingConflict], completeness:Completeness}
Setting = {name:<finite name>,value:<type below>,
  origin:requested|observed|retained_source,evidence:[Evidence],location:Location|null}
Command = {command_id:id,role:input_preparation|alignment|snp_analysis|
  association_test|tree_inference|reroot|unknown,argv:[text]|null,
  raw_command:text|null,origin:observed|retained_source,evidence:[Evidence],
  location:Location|null}
Version = {component:app_msa|msa_sequence_alignment|snp_analysis|app_metacats|
  metadata_parser|metacats_r|mafft|muscle|progressive_mauve|fasttree|r|perl,
  version:text|null,source_revision:text|null,
  origin:observed|retained_source,evidence:[Evidence],location:Location|null}
SettingConflict = {name:<Setting.name>,setting_indices:[index],
  code:requested_observed_conflict|observed_values_conflict|source_deployment_unproven}
DependenceGroup = {group_id:id,kind:duplicate_original_label|identical_sequence|
  same_original_member|same_source_record|repeated_artifact|derived_representation|
  shared_group_membership,member_keys:[MemberKey],alignment_rows:[{alignment_id:id,
  row_index:index}],document_ids:[id],source_record_ids:[id],evidence:[Evidence]}
```

Finite `Setting.name -> value` map: `input_mode -> ordinary_new_alignment|ordinary_prealigned|segment_alignment|segment_concatenation|mauve_first_block_projection|mauve_blocks|files|groups|auto`; `requested_molecule` and `observed_molecule -> dna|rna|protein|na|aa|unknown`; `aligner -> mafft|muscle|progressive_mauve|unknown`; `mafft_strategy -> auto|fftns1|fftns2|fftnsi|einsi|linsi|ginsi|unknown`; `case_policy -> preserve|uppercase|unknown`; `terminal_gap_policy -> exclude_terminal_dash|unknown`; `original_hash_policy -> exclude_hash|unknown`; `prealigned_bypass -> bool`; `snp_reference_type -> text`; `snp_reference_string -> text|null`; `epsilon -> number>=0`; `export_cutoff -> number in[0,1]`; `export_cutoff_comparison -> strict_less_than|unknown`; `threads -> positive`; `translation_table -> positive|null`; `tree_rooting -> original|midpoint|unknown`; `tree_model -> text`; `native_engine_version -> text`. Text tokens are retained facts, never executable instructions. Setting origins never collapse.

## Complete provider envelopes

```text
ReaderOutcome = {read_id:id,slot_id:id,artifact:Artifact,reader:ReaderSpec,
  status:ok|partial|invalid,document_ids:[id],diagnostics:[Diagnostic]}
NativeObservation = {observation_id:id,document_id:id,row_index:index,
  field:msa_score|msa_sequence_count|msa_symbol_count|metacats_chi_square|
    metacats_p_value|metacats_df|metacats_symbol_count,
  nested_indices:[index],number:NativeNumber,unit:hundredths_of_bit|sequences|
    observations|chi_square|probability|degrees_of_freedom,
  population_id:id|null,category_id:id|null,group_ids:[id],
  association_state:resolved|missing|conflicting|wrong_native_label,
  evidence:[Evidence]}
AssociationSet = {original_members:[OriginalMember],inline_inputs:[InlineSequenceInput],
  row_members:[RowMemberAssociation],
  transformations:[Transformation],correspondences:[Correspondence],
  feature_genomes:[FeatureGenomeAssociation],source_records:[SourceRecord],
  functions:[FunctionAssignment],function_equivalences:[FunctionEquivalence],
  taxonomy:[TaxonAssignment],dependence_groups:[DependenceGroup],
  requirements:[Requirement],diagnostics:[Diagnostic]}
MSAAnalysis = {analysis_id:id,mode:ordinary_new_alignment|ordinary_prealigned|
  segment_alignment|segment_concatenation|mauve_first_block_projection|mauve_blocks,
  alignment_id:id|null,frequency_table_id:id|null,consensus_alignment_id:id|null,
  tree_id:id|null,full_xmfa_slot_id:id|null,segment_ids:[id],
  reference:ReferenceBinding|null,output_role_evidence:[Evidence]}
MetaCATSAnalysis = {analysis_id:id,mode:files|groups|auto,alignment_id:id|null,
  metadata_document_id:id|null,category_ids:[id],
  adjusted_matrix_ids:[id],chisq_table_ids:[id],pair_table_ids:[id],
  raw_r_table_ids:[id],output_role_evidence:[Evidence]}
Populations = {alignments:[AlignmentPopulation],composition:[CompositionPopulation],
  taxonomy:[TaxonPopulation],leaves:[LeafPopulation]}
MSASheet = {schema_version:'bvbrc_msa_sheet_v1',tool:'C-L204-MSA',
  analysis:MSAAnalysis,inputs:[host InputBinding],run:RunRecord,
  documents:[ParsedDocument],read_outcomes:[ReaderOutcome],associations:AssociationSet,
  populations:Populations,segments:[Segment],consensus_associations:[ConsensusAssociation],
  tree_bindings:[TreeBinding],native_observations:[NativeObservation],
  native_tree_measurements:[shared NativeTreeMeasurement],
  support_observations:[shared SupportObservation],
  requirements:[Requirement],diagnostics:[Diagnostic]}
MetaCATSSheet = {schema_version:'bvbrc_metacats_sheet_v1',tool:'C-L205-MetaCATS',
  analysis:MetaCATSAnalysis,inputs:[host InputBinding],run:RunRecord,
  documents:[ParsedDocument],read_outcomes:[ReaderOutcome],associations:AssociationSet,
  populations:Populations,categories:[Category],groups:[BiologicalGroup],
  metadata_members:[MetadataMemberAssociation],auto_group_entries:[AutoGroupEntry],
  biological_assignments:[BiologicalAssignment],
  biological_group_populations:[BiologicalGroupPopulation],
  native_group_assignments:[GroupAssignment],native_group_columns:[GroupColumn],
  exported_groups:[ExportedGroupAssociation],native_test_associations:[NativeTestAssociation],
  native_observations:[NativeObservation],requirements:[Requirement],diagnostics:[Diagnostic]}
```

`NativeObservation.observation_id` is exactly `table_id + '/rows/' + original_row_index + '/' + field_pointer_suffix`, where field pointer suffix is the exact native field path (for MSA score, `score`). This preserves the existing entropy calculator observation IDs. The extraction records number/unit/population/identity; calculated cells remain in the separately saved component object specified next. The sheet is numerical, not only a claims table.

All document, row, source, transform, group, category, segment and population references validate against this exact analysis and retained inputs. Native table category IDs must agree with category bindings. Empty tables survive as full retained documents; they do not imply an empty tested population.

Tree adjunct records, using the existing exact mathematical contracts:

```text
LeafPopulation = {population_id:id,tree_id:id,node_indices:[index],
  completeness:'complete',evidence:[Evidence]}
TreeBinding = {tree_id:id,role:inference|midpoint_display|organismal,
  source_tree_id:id|null,alignment_id:id|null,command_id:id|null,
  branch_unit:expected_substitutions_per_model_site|joint_mixed_partition_model_site|native_unknown,
  support_method:fasttree_sh_like|native_unknown,
  support_scale:fraction|percent|statistic|native_unknown,
  tip_rows:[{node_index:index,alignment_id:id,row_index:index,evidence:[Evidence]}],
  evidence:[Evidence]}
NativeTreeMeasurement = {observation_id:id,field:branch_length|branch_support_native,
  value:number|null,raw_token:text|null,state:State,
  unit:expected_substitutions_per_model_site|joint_mixed_partition_model_site|
    native_unknown|percent|fraction|native_statistic,
  population_id:id,subject_id:id,method:id,location:Location|null,
  evidence:[Evidence],uncertainty:null|{kind:standard_error|interval|native_other,
    lower:number|null,upper:number|null,value:number|null,method:id},requirement_ids:[id]}
SupportObservation = {tree_id:id,node_index:index,native_observation_id:id,
  source_kind:internal_label|branch_comment|phyloxml_confidence,
  method:fasttree_sh_like|native_unknown,scale:fraction|percent|statistic|native_unknown,
  command_id:id|null,bootstrap_population_id:null,evidence:[Evidence]}
TipJoin = {gene_tree_id:id,gene_node_index:index,organismal_tree_id:id,
  organismal_node_index:index,subject:Subject,evidence:[Evidence]}
```

The installed shared native-observation/support validators govern their complete unit and uncertainty fields. Internal numeric labels alone do not establish FastTree SH support or bootstrap frequency. Requested/retained-source FastTree defaults do not establish the deployed branch model. Midpoint rerooted output retains its actual role; absent original inference tree remains absent. This work does not synthesize bootstrap replicates.

## Extractor entry points and exact outputs

```python
extract_inline_fasta_members(binding: dict, *, id_rule: str,
    encoding: str, molecule: str) -> ParseResult[InlineSequenceInput]

extract_alignment_associations(*, inputs: tuple[dict, ...],
    documents: tuple[dict, ...], declarations: dict) -> ParseResult[AssociationSet]

extract_metacats_associations(*, analysis: dict, documents: tuple[dict, ...],
    associations: dict, declarations: dict) -> ParseResult[MetaCATSAssociationSet]

extract_msa_sheet(*, analysis: dict, inputs: tuple[dict, ...],
    documents: tuple[dict, ...], read_outcomes: tuple[dict, ...], run: dict,
    associations: dict, populations: dict, segments: tuple[dict, ...],
    tree_bindings: tuple[dict, ...], parameters: dict) -> ParseResult[MSASheet]

extract_metacats_sheet(*, analysis: dict, inputs: tuple[dict, ...],
    documents: tuple[dict, ...], read_outcomes: tuple[dict, ...], run: dict,
    associations: dict, populations: dict, category_associations: dict,
    parameters: dict) -> ParseResult[MetaCATSSheet]

validate_msa_sheet(sheet: dict) -> dict
validate_metacats_sheet(sheet: dict) -> dict
```

`MetaCATSAssociationSet` is exactly `{categories,groups,metadata_members,auto_group_entries,biological_assignments,biological_group_populations,native_group_assignments,native_group_columns,exported_groups,native_test_associations,requirements,diagnostics}` with types above. `extract_alignment_associations.declarations` is exactly `{common:<resolved common_associations payload>,functions:<function_assignments payload>|null,taxonomy:<taxonomy_assignments payload>|null}`. `extract_metacats_associations.declarations` is the resolved metacats_context payload. Those closed role records are defined in `ASSOCIATION_HANDOFF_001.md` and the bundle contract; they never contain precomputed claims disguised as parser output. `parameters` are exactly `{source_dialect:'retained_bvbrc_msa'}` or `{source_dialect:'retained_bvbrc_metacats'}`. These name the interpretation, not the deployed version.

Each extractor is pure. Its `invalid` result has `value=null` only for a structurally contradictory analysis envelope. Missing independent evidence retains a partial sheet and specific requirements. A conflicting category cannot discard valid rows or another category's values; conflicting analyses remain separate at the adapter envelope. Validators validate saved relationships; they do not rerun native analysis or reconstruct numbers from an external service.
