# Proposed cross-workload values

Review status: proposed alongside `PROPOSED_CONTRACT.md`; root must accept or
revise before coding. These are concrete Python-record interfaces, not a
runtime scoring language. All keys listed for a record are required; optional
values are explicitly nullable. Unknown extra keys are rejected. All strings
that carry scientific data are original source tokens or source-backed IDs;
decision/failure/method strings use the finite enums in the main contract.
Scientific arithmetic and source semantics can be reviewed independently of
serialization. These serialized shapes remain unfrozen until root accepts them;
the named unresolved subshapes listed in `WORKLOADS_AND_INTEGRATION.md` have an
explicit owner and cannot be invented independently by parallel coders.

## Existing values reused without conversion

`Artifact`, `SourceLocation`, `AlignmentDocument`, `AlignmentPopulation`,
`Evidence`, original-member correspondence and the inputs to shared
taxon/function/tree calculators retain their current exact validated shapes
in `phylogeny_format_contracts.py` and `phylogeny_calculation_contracts.py`.
Shared calculator outputs are retained verbatim beneath `shared_components`.
In particular their `quantity` uses `population_ref`, `method` and
`origin='derived'`; these are not silently relabeled to the proposed tool-owned
numeric cell's `population_id`, `method_id`, `origin='calculated'`. Tool-owned
native/statistical cells use `NumericCell` from section 2 of the main contract.
Projection explicitly reads the appropriate known shape.

`Diagnostic` is exactly the existing host shape and phase enum; the proposed
phase mapping is recorded in the main contract. `Requirement` is the exact host
`AcquisitionRequirement` shape `{requirement_id,kind,role,source_refs,reason_code}`.
Extra scope is held by sheet records `{requirement_id,analysis_id,
population_id:str|null,field:str|null}` and is not inserted into host requirements.
Parser status is `ok|partial|invalid`; pure provider/adapter status may additionally
be `failed` for an actual failed analysis with no usable requested facts.

## Parser outputs

Common `ParseResult[T]`:

```
{status: 'ok'|'partial'|'invalid', value: T|null, diagnostics: [Diagnostic]}
```

`NativeNumber` preserves scalar syntax before scientific interpretation:

```
{raw_token: str, value: finite number|null,
 state: 'available'|'missing'|'not_measured'|'failed'|'truncated'|'incompatible',
 token_kind: 'finite'|'blank'|'native_na'|'underflow'|'nonfinite'|'malformed',
 source_location: SourceLocation}
```

`MSAFrequencyTable`:

```
{table_id, artifact, alphabet: 'dna'|'protein', layout, encoding,
 header_tokens: [str], completeness,
 rows: [{row_index, source_location, alignment_position: NativeNumber,
   reference_position: NativeNumber|null, reference_character: str|null,
   score: NativeNumber, consensus_token: str, n_sequences: NativeNumber,
   dna_counts: null|{A:NativeNumber,T:NativeNumber,G:NativeNumber,
                    C:NativeNumber,Deletion:NativeNumber},
   protein_detail: null|[{raw_token, raw_residue_token,
                          symbol: str|null, count: NativeNumber}]}]}
```

`MetaCATSChiSquareTable`:

```
{table_id, artifact, layout, category_id, encoding, completeness,
 header_tokens: [str], group_heading_tokens: [str],
 rows: [{row_index, source_location, position_token: str,
   position_1based: int|null, position_qualification: 'plain'|'legacy_star'|'invalid',
   chi_square: NativeNumber, p_value: NativeNumber, df: NativeNumber,
   fewer_5_token: str|null,
   group_cells: [{heading_index:int, raw_token:str,
                  symbol_counts:[{symbol:str,count:NativeNumber}]}]}]}
```

Legacy starred positions retain both original token and parsed integer with
unresolved star semantics. Reading that integer is not establishing current
native source/method or reference-coordinate equivalence.

`MetaCATSPairTable`:

```
{table_id, artifact, layout, category_id, encoding, completeness,
 header_tokens: [str],
 rows: [{row_index, source_location, position: NativeNumber,
   p_value: NativeNumber, raw_groups_token: str}]}
```

The parser does not split ambiguously encoded group names. The extractor binds
the exact raw token using the full source-backed group population; zero or
multiple matching full pairs produce a finite missing/conflict result.

`MetaCATSRawRTable` (optional supplied unfiltered artifact) is:

```
{table_id,artifact,layout:'r_write_table_single_result_string',
 kind:'omnibus'|'pairwise',category_id,encoding,completeness,
 wrapper_column_token:str,wrapper_row_token:str,section_heading_token:str,
 omnibus_rows:null|[{row_index,source_location,site_token:str,position:NativeNumber,
   chi_square:NativeNumber,p_value:NativeNumber,df:NativeNumber,
   fewer_5_token:str,residue_diversity_token:str,
   positional_groups:[{position_1based:int,raw_token:str,
                      symbol_counts:[{symbol:str,count:NativeNumber}]}]}],
 pair_rows:null|[{row_index,source_location,site_token:str,position:NativeNumber,
   p_value:NativeNumber,column_a_1based:NativeNumber,column_b_1based:NativeNumber}]}
```

Only the row collection corresponding to kind is populated. Raw R column
positions are not metadata ordinals. `NA` placeholders retain exact native
tokens. Parser reads the known quoted `write.table` wrapper as data; it executes
no R expression and does not interpret arbitrary code. A complete current raw
file proves its rows, not independently the omitted all-missing input sites;
that association still comes from complete aligned/member data.

`GroupMetadataDocument`:

```
{document_id, artifact, encoding, delimiter:'tab', header:'present'|'absent',
 header_tokens:[str]|null, completeness,
 rows:[{row_index,source_location,cells:[str]}]}
```

No dictionary keyed by member ID replaces ordered rows. Empty and duplicate
cells/rows remain present. `AdjustedCategoryMatrix` is:

```
{document_id,artifact,category_id,encoding,completeness,
 rows:[{row_index,source_location,native_member_token:str,
        native_group_token:str,symbols:[str]}]}
```

It preserves `#` and other native tokens without passing through FASTA's symbol
validator. Supplying an adjusted matrix is optional; its exact association with
original input/metadata is still required for member interpretation.

## Association and calculation outputs

`BoundInvocation` is proposed as:

```
{request:AppServiceRequest,request_evidence:[Evidence],
 task:{task_id:str,application_id:'MSA'|'MetaCATS',handoff_source_ref:str,
       manifest_source_refs:[str]},task_evidence:[Evidence],
 observed_methods:[{field:'producer_version'|'aligner'|'aligner_version'|
    'alphabet'|'command_argv'|'r_version'|'locale'|'tree_model'|'support_method',
    value:str|[str]|null,state:'observed'|'unknown',evidence:[Evidence]}]}
```

`AppServiceRequest` is the exact existing validated native request shape from
`bvbrc_appservice_schemas.json`; its selected original definition and parameters
are retained, not a reduced surrogate request. No native producer-version claim
can be filled from the locally inspected source checkout alone. The host binds
the evidence before supplying this value. `observed_methods.command_argv` is
an argv array when observed; all other field variants are strings or null.

`TransformationMap`:

```
{transformation_id,
 kind:'rename'|'concatenate'|'trim'|'translate'|'uppercase'|'ungap'|'filter'|
      'first_contig'|'xmfa_projection',
 input_member_keys:[{input_binding_id,member_id,occurrence_index:int}],
 output_rows:[{alignment_id,row_index:int}],
 label_mappings:[{input_binding_id,member_id,occurrence_index:int,
                  original_label:str,staged_label:str,final_label:str}],
 residue_correspondences:[OriginalCoordinateJoin],
 completeness,evidence:[Evidence]}
```

This is a retained mapping, not an instruction to execute a transformation.
Translation code/frame and coordinate fields are on the explicit correspondence.
No complete coordinate map is implied by a rename or uppercase record.

`SegmentJoin`:

```
{analysis_id,alignment_id,row_index:int,segment_id,requested_segment_token:str,
 original_genome_id:str|null,original_contig_id:str|null,
 original_member:{input_binding_id,member_id}|null,
 locus_order_index:int|null,duplicate_suffix_token:str|null,
 final_interval_0based_half_open:[int,int]|null,
 padding_state:'observed_sequence'|'padded_missing_locus'|'unknown',
 transformation_id:str|null,evidence:[Evidence]}
```

`BoundGroupExpansion`:

```
{group_source_ref:str,group_path:str,group_content:EvidenceContent,
 expansion_evidence:[Evidence],completeness,
 members:[{member_id:str,occurrence_index:int,
           original_source_record_id:str,sequence_content:EvidenceContent|null,
           sequence_sha256:str|null,evidence:[Evidence]}]}
```

The member order and repeats are retained. A group path or count alone cannot
satisfy this original expansion. `BoundAutoAssignment` is
`{parameter_index:int,id:str,grp:str,evidence:[Evidence]}`; it records each exact
original submitted occurrence. `BoundHeaderDecision` is:

```
{metadata_document_id,header:'present'|'absent',
 basis:'explicit_input'|'recorded_native_decision'|'verified_source_reproduction',
 actual_native_check_header:bool,evidence:[Evidence]}
```

The native first-field regex heuristic is not silently replaced by exact-ID
matching when claiming a source-reproduced decision. Unresolved ambiguity
produces no header decision and preserves the bytes for repair.

`InputMember`:

```
{input_binding_id,member_id,occurrence_index:int,original_header:str|null,
 original_sequence_sha256:str|null,original_length:int|null,
 alphabet:'dna'|'protein'|'unknown',source_record_id:str|null,evidence:[Evidence]}
```

`GroupIdentity`:

```
{category_id,group_id,raw_group_value:str,native_group_ordinal:int|null,
 displayed_group_label:str|null,evidence:[Evidence]}
```

Group identity is category-local; `raw_group_value` is original, not a generated
interpretation. Ordinals must be proved from the complete native metadata
population or retained native matrix. Stable local IDs are not model-facing
evidence and cannot substitute for that proof.

`GroupColumnBinding` is:

```
{category_id,r_column_index_0based:int,r_group_token:str,
 native_group_ordinal:int|null,group_id:str|null,
 exported_heading_index_0based:int|null,exported_label_token:str|null,
 state:'resolved'|'wrong_native_label'|'unresolved',evidence:[Evidence]}
```

The metadata ordinal order, represented R column order and exported-heading
order are independently retained and then explicitly joined. K in native AA
pair df is the represented R column count. Metadata-only groups can contribute
headings/ordinals without any R column. The proposed >=10 unpadded lexical-order
problem was not reproduced in root's R 4.3.3 example: padded tokens preserved
numeric order. Keep those exact tokens. Missing runtime/locale evidence leaves the specific native column
join unresolved. Source-corrected group counts are not relabeled as native
exported counts when the exporter attached a wrong name.

`MSAInputAssociations`:

```
{status,input_members:[InputMember],row_members:[RowMemberJoin],
 original_correspondences:[OriginalCoordinateJoin],reference:ReferenceBinding|null,
 segments:[SegmentJoin],requirements:[Requirement],diagnostics:[Diagnostic]}
```

`MetaCATSInputAssociations`:

```
{status,input_members:[InputMember],row_members:[RowMemberJoin],
 categories:[{category_id,metadata_column_index:int,raw_category_token:str,evidence}],
 groups:[GroupIdentity],group_columns:[GroupColumnBinding],assignments:[GroupAssignment],
 extra_metadata_row_indices:[int],duplicate_metadata_row_groups:[[int]],
 unresolved_alignment_row_indices:[int],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`MSAEntropyComponents`:

```
{status,analysis_id,population_id,alignment_id,method_parameters,
 sites:[{column_0based:int,included_row_indices:[int],
         excluded_terminal_row_indices:[int],symbol_counts:[{symbol:str,count:int}],
         eligible_count:NumericCell,internal_gap_count:NumericCell,
         terminal_gap_excluded_count:NumericCell,literal_entropy_bits:NumericCell,
         native_score_recalculated:NumericCell,score_residual:NumericCell,
         strict_majority_consensus:str|null,native_observation_ids:[str]}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`method_parameters` is exactly `{alphabet,case_policy,terminal_gap,native_rounding}`
from the function arguments. Native observations remain separate sheet records.
Analysis identity is the explicit `analysis_id` argument supplied by the owned
sheet builder, not inferred from filename or a field missing from the shared
AlignmentPopulation. Full-row terminal bounds precede subset column selection.

`MSAReferenceComponents`:

```
{status,analysis_id,population_id,alignment_id,reference:ReferenceBinding,
 method_parameters:{alphabet,case_policy},
 differences:[{row_index:int,column_0based:int,member_character:str,
   reference_character:str,category,member_ungapped_position_0based:int|null,
   reference_ungapped_position_0based:int|null,
   member_original_correspondence:OriginalCoordinateJoin|null,
   reference_original_correspondence:OriginalCoordinateJoin|null}],
 counts:[{row_index:int,category,count:NumericCell}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`GroupCountComponents`:

```
{status,analysis_id,population_id,alignment_id,category_id,
 group_order:[GroupColumnBinding],method_parameters:{case_policy,terminal_mask,native_input_hash_policy},
 sites:[{table_id,column_0based:int,state:'all_missing'|'conserved'|'variable'|'unresolved',
   symbols:[str],observed_counts:[[int]],
   included_rows_by_group:[[int]],excluded_terminal_rows_by_group:[[int]],
   excluded_original_hash_rows_by_group:[[int]],internal_gap_rows_by_group:[[int]],
   unresolved_row_indices:[int],completeness,evidence:[Evidence]}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`observed_counts[symbol_index][group_index]` is explicit and rectangular. Every
eligible row contributes exactly one count to its assigned group and actual
symbol. Exclusion sets are disjoint except a separately documented conflict;
terminal `-` and original `#` provenance remain distinguishable. The denominator
for observed group frequencies is the corresponding matrix column sum. Group
membership totals remain separate from this per-site denominator.

`MetaCATSStatistics`:

```
{status,analysis_id,category_id,method_parameters,
 omnibus:[StatisticalCalculation],pairs:[StatisticalCalculation],
 exclusions:[{column_0based,test_kind,group_pair:null|[str,str],
              reason:'all_missing'|'conserved_placeholder'|'degenerate_df'|'unresolved'}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`method_parameters` retains all arguments to `metacats_statistics`, including
the exact kernel ID/version. `StatisticalCalculation` is:

```
{test_id,kind:'omnibus'|'pairwise',category_id,column_0based:int,
 group_ids:[str],raw_table_id,raw_symbols:[str],augmented_symbols:[str],
 original_category_group_count:int,epsilon:NumericCell,
 augmented_counts:[[number]],expected_counts:[[number]],
 augmented_total:NumericCell,continuity_delta:NumericCell,
 chi_square:NumericCell,df:NumericCell,mathematical_p:NumericCell,log_p:NumericCell,
 native_zero_rule_p:NumericCell,
 numerical_state:'finite'|'underflow'|'unavailable',
 method_id,native_observation_ids:[str],requirements:[Requirement]}
```

For omnibus `native_zero_rule_p` is not measured; no pair-only rule applies.
For pairwise, mathematical and source-native-zero-rule values always remain
different fields even if equal. Standard pair df and native AA df have different
`method_id`s. No numeric underflow becomes evidence p=1 in `mathematical_p`;
use null/underflow plus a finite log tail if supported. Exact native printed 1
is still preserved in its native observation. Complete tested-family enumeration
uses the explicit test IDs and excludes recorded non-tests, never TSV row count.

`MetaCATSEffects`:

```
{status,analysis_id,category_id,zero_margin_policy,
 sites:[{raw_table_id,column_0based:int,raw_chi_square:NumericCell,cramers_v:NumericCell,
   effective_symbol_count:int,effective_group_count:int,
   raw_expected:[[number]],augmented_adequacy:null|ExpectedAdequacy,
   raw_adequacy:ExpectedAdequacy,
   positive_observed_cells_below_5:int,native_fewer_5_recalculated:'Y'|'N'|null,
   pairs:[{group_ids:[str,str],frequency_deltas:[{symbol:str,value:NumericCell}],
           total_variation:NumericCell}]}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`ExpectedAdequacy` is `{table_id,minimum_expected:NumericCell,
cells_below_5:NumericCell,cells_below_1:NumericCell,cell_denominator:NumericCell}`.
The effect function receives raw counts only; `augmented_adequacy` belongs to
the statistics builder and remains null until supplied augmented E is explicitly
joined. Do not calculate augmented adequacy from raw expected counts.

`TestPValue` is `{test_id,value:NumericCell}`. `MultiplicityComponents`:

```
{status,family:TestFamily,method:'none'|'bonferroni'|'holm'|'bh'|'by',
 alpha:number,dependence_assumption,observed_p_count:int,
 total_test_count:int|null,harmonic_factor:number|null,
 results:[{test_id,input_p:NumericCell,adjusted_p:NumericCell,
           rejected_at_alpha:bool|null}],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

No hidden test count, cutoff, minimum group size or significance filter is
implied by these records. Unknown components are explicit states/requirements.

## Sheet builders and bundle interface

Provider builders proposed as ordinary separate functions:

```
build_msa_sheet(*, analysis, invocation, artifacts, alignments, frequency_tables,
                tree_documents, input_associations, supplied_metadata, populations)
    -> MSASheet
calculate_msa(sheet: MSASheet, *, parameters: MSACalculationParameters)
    -> {status,shared_components,native_entropy,reference_differences,
        requirements,diagnostics}
build_metacats_sheet(*, analysis, invocation, artifacts, alignments,
    chisq_tables, pair_tables, metadata_documents, adjusted_matrices,
    input_associations, supplied_metadata, populations, native_selection)
    -> MetaCATSSheet
calculate_metacats(sheet: MetaCATSSheet, *, parameters: MetaCATSCalculationParameters)
    -> {status,shared_components,group_counts,statistics,effects,multiplicity,
        requirements,diagnostics}
```

`native_observations` in each sheet preserve every parsed native numerical cell,
its record identity and source independent of calculation selection. Numerical
sheet population does not happen inside `child_tool_info` or model prompts.

Proposed adapter parameters:

```
{schema_version:'bvbrc_alignment_adapter_parameters_v1',
 tool:'C-L204-MSA'|'C-L205-MetaCATS',
 analyses:[{analysis_id,mode,scientific_inputs:Evidence|null,
            supplied_metadata:[Evidence],population_plans:[PopulationPlan],
            calculation_parameters:MSACalculationParameters|MetaCATSCalculationParameters}],
 artifact_selection:[{analysis_id,slot_id,role,reader:ReaderSpec,
    source_binding:{kind:'acquired_requirement',requirement_id:str}|
                   {kind:'supplied_content',content:EvidenceContent}}]}
```

`PopulationPlan` is either `{kind:'whole_alignment',population_id,slot_id}` or
`{kind:'alignment_subset',population_id,slot_id,row_indices:[int],columns_0based:[int]}`,
plus provider-specific explicit group/test-family/member populations already
defined above. The builder validates all identities and retains the final full
population record. No automatic all-pairs expansion, common-name join or
implicit projection population is allowed.

`ReaderSpec` is a closed tagged union of the parser signatures in the main
contract, omitting only data/artifact; it records actual format, layout and
encoding. `role` is one of `final_alignment|native_frequency_table|
native_consensus|native_tree|native_tree_log|native_xmfa|original_alignment|
original_metadata|adjusted_category_matrix|native_omnibus_table|
native_pairwise_table|native_method_log`. A role is not proof of provenance or
scientific method. Unsupported log dialects remain retained bytes/requirements,
not arbitrary regex extraction advertised as complete support.

`MSACalculationParameters` contains arrays of explicit shared alignment,
original coverage, function, taxon and tree requests plus
`entropy_requests` and `reference_difference_requests`, each holding the exact
function arguments and population/slot IDs. `MetaCATSCalculationParameters`
contains shared alignment/composition/taxon requests plus `group_count_requests`,
`statistics_requests`, `effect_requests` and `multiplicity_requests`, each with
the exact arguments above. Empty arrays mean not requested. Input data are
looked up only by validated saved identities, not string evaluation.

`consume_bundle` must use the actual host list
`supplied_values=[{evidence,value},...]` and exact original `supplied_contents`.
It cannot treat nested metadata source IDs as authenticated bytes. It returns
the existing eight-field AdapterResult; host custody/publication stays outside
the pure modules. Shape acceptance does not establish native truth.
