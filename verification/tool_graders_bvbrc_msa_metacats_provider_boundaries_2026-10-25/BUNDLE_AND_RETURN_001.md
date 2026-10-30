# Bundle selection, authenticated inputs and requested returns

Contract proposal for root acceptance, 2026-10-25. Reuse the installed AppService `ArtifactBundle`, `AdapterSelection`, `SourceEvidence`, `ContentBinding`, publication custody and eight-field adapter result. No service call, path read, task selection, retry, upload or model call occurs inside a provider, calculator, adapter or saved-fact reader.

Normative dependencies are the frozen `PROVIDER_RECORDS_001.md`, `NATIVE_DOCUMENT_RECORDS_001.md`, `ASSOCIATION_HANDOFF_001.md`, accepted mathematical definitions in `CALCULATIONS_001.md` plus `MATH_HANDOFF_001.md` and root's `MATH_CLARIFICATIONS_007.md`. Root's accepted association clarifications012/013 apply additively to the frozen common declarations/AssociationSet and auto-entry custody. Provider-local native PValuePlan is superseded explicitly by `PROVIDER_PARAMETER_CLARIFICATIONS_002.md`. Initial provider v1 includes the separate additive `XMFA_PROVIDER_EXTENSION_001.md`, with the exact superseding MSAAnalysis/ReaderSpec/ParsedDocument/sheet, supplied source verification, four requests and four projections. That extension does not edit any frozen base record. `id`, `index`, `text`, State, Content, Evidence and every inherited record have exactly the frozen definitions.

## Adapter entry points

New facades `bvbrc_msa_bundle_adapter.py` and `bvbrc_metacats_bundle_adapter.py` export:

```python
ADAPTER_ID = 'bvbrc_msa'                 # other facade: 'bvbrc_metacats'
ADAPTER_VERSION = '1'
validate_parameters(parameters: dict) -> dict
parameters_schema() -> dict
requested_form_schema(fields: dict) -> dict
validate_requested_form(requested_form: dict) -> dict
consume_bundle(bundle: dict, *, artifact_bytes: dict[str,bytes],
    supplied_values: list[dict], requested_form: dict, parameters: dict) -> dict
implementation_sha256() -> str
```

Shared new modules are `bvbrc_alignment_bundle_contracts.py`, `bvbrc_alignment_bundle_resolution.py`, and `bvbrc_alignment_bundle_projection.py`. Their exact public boundaries are:

```python
# bvbrc_alignment_bundle_contracts
validate_parameters(parameters: dict, *, provider: str) -> dict
parameters_schema(*, provider: str) -> dict
requested_form_schema(fields: dict, *, provider: str) -> dict
validate_requested_form(requested_form: dict, *, provider: str) -> dict
# bvbrc_alignment_bundle_resolution
resolve_bundle(bundle: dict, *, artifact_bytes: dict[str,bytes],
    supplied_values: list[dict], parameters: dict, provider: str) -> dict
consume_bundle(bundle: dict, *, artifact_bytes: dict[str,bytes],
    supplied_values: list[dict], requested_form: dict, parameters: dict,
    provider: str) -> dict
# bvbrc_alignment_bundle_projection
project_requested_facts(*, sheet_set: dict|None, component_set: dict|None,
    missing_requirements: tuple[dict,...], diagnostics: tuple[dict,...],
    requested_form: dict, parameters: dict, provider: str) -> dict
validate_projected_facts(facts: dict, *, sheet_set: dict|None,
    component_set: dict|None, missing_requirements: tuple[dict,...],
    diagnostics: tuple[dict,...], requested_form: dict,
    parameters: dict, provider: str) -> dict
```

Shared provider values are exactly `msa|metacats`; the facades bind them. Projection returns the exact requested facts object and raises finite ValueError for a malformed selector or forged saved value. An unavailable selected dependency returns its typed null/requirements as specified below; it is not a malformed selector. The explicit requirement/diagnostic operands are the adapter's exact aggregate records, including host/selection failures that need not belong to a valid sheet. `validate_projected_facts` validates saved identities/relationships and the exact saved value records; it does not execute parsers/calculators or expand a requested selection. Each facade's `implementation_sha256()` hashes actual consumed new modules, accepted parser/calculator/value dependencies and host contract assets with length framing, using the existing configuration-only pattern. Do not add these modules to the ongoing phylogeny test dependency hash; MSA/MetaCATS have their own pin.

The host's pure adapter return remains exactly:

```text
{adapter_id:id,adapter_version:'1',status:ok|partial|invalid|failed,
 sheet:SheetSet|null,components:ComponentSet|null,facts:closed requested object,
 missing_requirements:[Requirement],diagnostics:[Diagnostic]}
```

`AppServicePublications._grade` saves `sheet`/`components` as authenticated contents and publishes the existing persisted `AdapterResult` keys `sheet_content` and `components_content`. It supplies `artifact_bytes` for bundle artifacts and explicitly selected `supplied_contents`, plus `supplied_values=[{evidence:Evidence,value:finite JSON}]` from custody. It does not grant parser authority to any unrelated object the adapter can see.

## Original commissioning shape

```text
SlotRef = {analysis_id:id,slot_id:id}
TreeRef = {analysis_id:id,slot_id:id,tree_index:index}
SourceBinding =
 {kind:'acquired_role',bundle_role:id} |
 {kind:'supplied_content',content:Content} |
 {kind:'original_input',input_binding_id:id,content:Content}
SlotSelection = {analysis_id:id,slot_id:id,semantic_role:<finite role>,
                 source:SourceBinding,reader:ReaderSpec|null}
Parameters = {version:'bvbrc_alignment_bundle_parameters_v1',
  artifact_selection:[SlotSelection],analyses:[AnalysisPlan],
  multiplicity_families:[CrossAnalysisMultiplicityPlan]}
AnalysisPlan = {analysis:Planned<MSAAnalysis|MetaCATSAnalysis>,
  population_plans:[PopulationPlan],scientific_inputs:[SuppliedInput],
  read_parameters:{source_dialect:retained_bvbrc_msa|retained_bvbrc_metacats},
  calculation_parameters:Planned<CalculationParameters>}
SuppliedInput = {role:<finite supplied role>,evidence:Evidence}
```

Every analysis ID is unique. Every `(analysis_id,slot_id)` is unique. The scientific provider is fixed by adapter ID; an MSA adapter cannot accept MetaCATS analysis or request tags. Two analyses may deliberately select the same original artifact with distinct meaning; keep both analyses and shared provenance. Equal repeated byte representations are not independent biological evidence.

Finite semantic roles: `original_sequences`, `staged_sequences`, `alignment`, `msa_frequency`, `consensus`, `tree`, `organismal_tree`, `full_xmfa`, `xmfa_staged_source`, `metadata`, `adjusted_matrix`, `chisq_export`, `pair_export`, `raw_r_omnibus`, `raw_r_pairwise`, `native_run_evidence`. Provider compatibility is explicit. A `full_xmfa` or `native_run_evidence` slot may use `reader=null` to retain opaque bytes while its parser binding is unfinished; this cannot satisfy a numerical dependency. `xmfa_staged_source` permits reader=null only under the exact source-verification contract in the additive XMFA extension. Other scientific roles require a compatible reader.

`Planned<T>` is a closed commissioning variant, not a generic substitution language. In the following declared paths only, replace saved document IDs by `SlotRef` and saved tree IDs by `TreeRef`: analysis alignment/frequency/consensus/metadata/table IDs and xmfa_document_id; alignment-population document; reference alignment; segment alignment; transformation input/output row alignments and native-mask alignment; correspondence alignment; row/member/metadata/group association alignments; exported-group/native-test table ID; tree binding tree/source-tree/alignment and tip-row alignments; relationship-comparison gene/organismal tree and tip-join tree IDs; calculation `alignment_id`, `observed_table_id`, reference alignment, and native PValuePlan `table_ids`; the four XMFA request document_id fields and nested XMFASelection.document_id. Array fields containing document IDs become arrays of the corresponding SlotRef. Store planned fields under their same explicit field names; after resolution, validate the saved `T` type. `full_xmfa_slot_id` remains the caller's slot string and is never substituted. Category/group/member/source/transform/population/request IDs are never substituted. Unavailable selected slots become typed missing dependencies, not made-up IDs. No arbitrary recursive string replacement is permitted.

Population plans are exactly:

```text
{kind:'whole_alignment',population_id:id,alignment:SlotRef}
{kind:'alignment_subset',population_id:id,alignment:SlotRef,row_indices:[index],
 columns_0based:[index],completeness:Completeness,evidence:[Evidence]}
{kind:'whole_tree',population_id:id,tree:TreeRef}
{kind:'composition',population:CompositionPopulation}
{kind:'taxonomy',population:TaxonPopulation}
```

A whole alignment uses actual parsed rows and observed columns; if no single observed width exists, use declared width if present, otherwise the maximum observed row length, with the actual partial/truncated completeness. It never claims omitted cells exist. A whole tree enumerates actual leaves of that exact selected tree. Explicit subsets preserve row/column order and supplied population completeness, qualified by document completeness.

Cross-analysis family operations and their nested records are exactly:

```text
CrossAnalysisMultiplicityPlan = {family_request_id:id,family:CrossAnalysisFamilyPlan,
 p_values:CrossAnalysisPValuePlan,method:none|bonferroni|holm|bh|by,alpha:number-in[0,1],
 dependence_assumption:none_required_between_tests|
 independent_or_positive_regression_dependence_assumed}
ScopedTestSelector = {analysis_id:id,test:TestSelector}
CrossAnalysisFamilyPlan = {family_id:id,analysis_ids:[id],category_ids:[id],
 test_kind:omnibus|pairwise,eligibility:'variable_site_positive_df',
 population_state:complete|known_count_only|declared_upper_bound|unknown,
 total_test_count:index|null,assumption:null|{kind:independently_known_count|
 parent_declared_upper_bound,count:index,evidence:[Evidence]},
 p_value_basis:native_unadjusted|source_mathematical_recalculation|
 biological_mathematical_recalculation,evidence:[Evidence],
 selection:all_eligible|explicit_tests,tests:[ScopedTestSelector]}
CrossAnalysisPValuePlan =
 {kind:'statistical_results',requests:[{analysis_id:id,request_id:id}],
  field:'mathematical_p'} |
 {kind:'native_tables',tables:[SlotRef],
  eligibility_statistics_requests:[{analysis_id:id,request_id:id}]}
```

This is a bundle-only commissioning record; provider-local FamilyPlan/TestSelector remain unchanged. `all_eligible` requires tests=[] and takes the exact eligible identities from only the explicitly named full results/unfiltered native tables. `explicit_tests` resolves each `(analysis_id,category_id,column_0based,kind,group_ids)` within that analysis and within the named source results to exactly one actual test ID. Identical category names in different analyses never join implicitly. Duplicate selectors, unresolved/ambiguous matches, mixed p-value bases or duplicate actual test IDs fail specifically. Compile the original TestFamily by copying its named fields, removing selection/tests and inserting resolved test_ids; pass the exact saved p cells with those IDs to unchanged `adjust_p_values`. Category_ids is a declaration set and may contain an ID used by multiple named analyses; it is never used alone for identity lookup. The accepted additive biological provenance is retained. These operations are saved under `ComponentSet.multiplicity_families` and are not extra episode actions.

## Reader union — exact installed parser dispatch

```text
{reader:'aligned_fasta',id_rule:'first_whitespace_token',encoding:ascii|utf-8}
{reader:'metacats_input_fasta',id_rule:'first_whitespace_token',encoding:ascii|utf-8}
{reader:'msa_frequency',alphabet:dna|protein,
 layout:current_without_reference|current_with_reference,encoding:ascii|utf-8}
{reader:'metacats_chisq',layout:current_filtered_tsv|legacy_example_tsv,
 category_id:id,encoding:ascii|utf-8}
{reader:'metacats_pair',layout:'current_filtered_tsv',category_id:id,encoding:ascii|utf-8}
{reader:'metacats_raw_r',kind:omnibus|pairwise,
 layout:'r_write_table_single_result_string',category_id:id,encoding:ascii|utf-8}
{reader:'metacats_metadata',delimiter:'tab',header:present|absent,encoding:ascii|utf-8}
{reader:'metacats_adjusted_matrix',category_id:id,encoding:ascii|utf-8}
{reader:'newick',dialect:newick|raxml_branch_labels|bvbrc_double_quoted_names,
 allow_multiple:bool}
{reader:'mauve_xmfa_v1',dialect:'mauve1',alphabet:'dna',encoding:ascii|utf-8}
```

The exact dispatch is to `parse_aligned_fasta`, new `parse_metacats_input_fasta`, `parse_msa_frequency_table`, `parse_metacats_chisq_table`, `parse_metacats_pair_table`, `parse_metacats_raw_r_table`, `parse_metacats_metadata`, `parse_metacats_adjusted_matrix`, and `parse_newick`, passing the exact selected kwargs and actual Artifact. The new MetaCATS-only FASTA reader was explicitly accepted by root:

```python
parse_metacats_input_fasta(data: bytes, *, artifact: dict,
    id_rule='first_whitespace_token', encoding='ascii') -> ParseResult[AlignmentDocument]
```

It preserves original `#` and all headers/symbols/duplicates with ordinary FASTA partial/layout handling. It does not substitute `#` for dashes and does not alter `parse_aligned_fasta` or `AlignmentDocument`. Original hash masks and generated terminal masks require different provenance. A transformed sequence cannot substitute for a missing original hash-containing input.

The full XMFA reader dispatches to `xmfa_formats.parse_mauve_xmfa`; its complete accepted pure handoff and exact provider additions are in `XMFA_PROVIDER_EXTENSION_001.md`. No XMFA is cast to AlignmentDocument. The first-block `.afa` remains independently usable by existing MSA calculators under its separate analysis. Root's installed source binder consumes actual byte-verified source records as defined in that extension; unsupported GenBank/DNAstar source extractors remain precise missing bindings. A not-yet-installed reader/calculator yields its exact parser/dependency requirement; retaining opaque XMFA does not establish whole-genome completeness.

## Selection and custody rules

1. Validate the original ArtifactBundle and original task/application identity (`MSA` or `MetaCATS`); preserve submitted, scheduler-returned and effective parameters separately. An original request to a different application is invalid.
2. `acquired_role` selects only exact `ArtifactMember.role == bundle_role`. The commissioning `OutputRequirement.role` must use this exact unique role. For multiple categories/analyses use distinct caller-owned roles such as `analysis_a.category_c.chisq`; semantic role is separate. The existing ArtifactMember **does not contain requirement_id**. Do not pretend a `requirement_id`-only adapter selector can resolve it, and do not infer a role from a filename.
3. One equivalent representation can have repeated acquisition receipts. Compare actual object identity, task, hash, byte count and observed range; preserve all receipts/artifact bindings and a repeated-representation qualification. Distinct candidate representations for the same selected role are ambiguous; do not choose newest/first/largest. Missing is a role-specific requirement. A parent can disambiguate before commissioning by distinct roles or an exact original OutputRequirement object selection.
4. An acquired parsed object requires complete body and complete object. Keep incomplete bytes/receipts but do not pass a selected byte window as a complete native document. Task association and producer-byte version qualifications survive even if parsing succeeds. A source snapshot proving current bytes is not proof those bytes were produced by the original task.
5. Supplied content must exactly match an entry in `bundle.supplied_contents`, and supplied values must exactly match a selected `bundle.supplied_scientific_metadata` Evidence binding. The original-input variant additionally requires exact equality with that original InputBinding.content. These bytes must have been explicitly supplied to the host; absence is `input_bytes` or `output_bytes` as appropriate, never an internal Store/path lookup.
6. Validate bytes against content byte count and SHA256 before reading. Cache parser results by exact Artifact **and ReaderSpec**, including category ID. Reading identical TSV bytes for two independently declared category identities is not itself a parser conflict. Conflicting actual format declarations are. Preserve every slot's identity and evidence even when equal reads can share a representation.
7. Evidence proves the exact retained value/pointer, not an arbitrary scientific claim. Cross-check supplied joins against bytes, original inputs, IDs, rows and transformations. No supplied ParsedDocument or NativeNumber claim bypasses parser validation. Source-code facts remain retained-source facts unless actual run evidence establishes deployment.

The existing phylogeny adapter is the custody/ownership precedent. Its global role uniqueness and its coarse conflicting-reader treatment are not a semantic template for multi-category MetaCATS. The proposed selectors work with the host's current artifact shape and require no host schema change.

## Fully defined supplied evidence roles

Each `SuppliedInput` role can appear at most once per analysis. Its Evidence points to the entire following closed value; any nested Evidence must also be authenticated by the original supplied-evidence set. A source-document record authenticates a selected underlying record, not an arbitrary `source_record_id` label.

`observed_run` value is the exact `RunRecord` in `PROVIDER_RECORDS_001.md`; its original_task_id must match the original task. Requested settings are cross-checked with original submitted parameters; retained source defaults cannot become observed settings.

`common_associations` value:

```text
{version:'bvbrc_alignment_associations_v1',analysis_id:id,
 input_sequences:[InputSequenceSelection],row_joins:[Planned<RowMemberAssociation>],
 automatic_row_joins:[AutomaticRowJoin],transformations:[Planned<Transformation>],
 correspondences:[Planned<Correspondence>],feature_genomes:[FeatureGenomeAssociation],
 source_records:[SourceRecord],member_entities:[MemberEntityAssociation]}
MemberEntityAssociation = {member_key:MemberKey,
 subject:{kind:feature|genome,id:id,source_record_id:id},evidence:[Evidence]}
InputSequenceSelection =
 {kind:'parsed_document',input_binding_id:id,document:SlotRef,
 member_id_rule:'first_whitespace_token',molecule:dna|rna|protein|mixed|unknown,
 host_member_joins:[{source_row_index:index,host_member_id:id}],evidence:[Evidence]} |
 {kind:'inline_fasta',input_binding_id:id,id_rule:'first_whitespace_token',
  encoding:ascii|utf-8,molecule:dna|rna|protein|mixed|unknown,evidence:[Evidence]}
AutomaticRowJoin = {alignment:SlotRef,input_binding_ids:[id],
 method:exact_unique_header|exact_unique_sequence,case_policy:literal|uppercase,
 gap_policy:literal|remove_alignment_dash,transformation_ids:[id],evidence:[Evidence]}
```

InputSequenceSelection enumerates physical FASTA rows and assigns MemberKey occurrence indices in source order. The inline alternative reads actual authenticated original InputBinding.inline_value with its original parameter pointer, using `extract_inline_fasta_members`; it creates no Artifact/AlignmentDocument and requests no redundant acquisition. Parsed-document host-member joins are explicit exact facts; optional unresolved host joins do not collapse occurrences. Original host members without supplied sequence content retain metadata-only facts. Explicit row joins preserve ambiguity/state, and must be consistent with supplied actual sequences/transforms. Automatic sequence comparison obeys the selected case/gap policy; it cannot insert translation, reverse complement or stripping automatically. Every successful automatic match is unique on both sides. Multiple supplied input bindings remain distinct even when labels match. Root's accepted `EXPLICIT_MEMBER_ENTITY_ASSOCIATIONS_013.md` adds member_entities to the declaration and saved AssociationSet: validate the full occurrence, nonempty evidence, explicit feature/genome Subject and exact source_record_id of the matching SourceRecord kind; reject duplicate relationship records. Derive OriginalMember feature/genome arrays only from these explicit links and the explicit FeatureGenomeAssociation chain. Ordinary source-record provenance can supply source_record_ids, but cannot establish entity identity. MetaCATS separately consumes the explicit AutoGroupEntry feature/member relation without mutating the common AssociationSet. Equal names or shared evidence content alone do not establish entity identity.

`function_assignments` value is `{version:'bvbrc_alignment_functions_v1',analysis_id:id,assignments:[FunctionAssignment],equivalences:[FunctionEquivalence]}`. `taxonomy_assignments` value is `{version:'bvbrc_alignment_taxonomy_v1',analysis_id:id,assignments:[TaxonAssignment]}`. Subject and source-record identities must exist; no function is inferred from an alignment or a gene name.

`msa_context` value is `{version:'bvbrc_msa_context_v1',analysis_id:id,segments:[Planned<Segment>],reference:Planned<ReferenceBinding>|null,tree_bindings:[Planned<TreeBinding>]}`. Original coordinate correspondences belong to common_associations; actual genome_sequence records, sequence entry, interval/strand, selected segment order and missing-segment gap fills are explicit. The declared analysis reference and this supplied reference must agree. No standard translation table or first contig is silently assumed.

`metacats_context` value:

```text
{version:'bvbrc_metacats_context_v1',analysis_id:id,
 metadata_joins:[MetadataJoinPlan],categories:[CategoryPlan],
 explicit_memberships:[Planned<BiologicalAssignment>],auto_group_entries:[AutoGroupEntry],
 group_sources:[{category_id:id,raw_group_value:text,bindings:[FeatureGroupSource]}],
 biological_group_populations:[BiologicalPopulationPlan],
 native_group_maps:[NativeGroupMap],r_columns:[RColumnEvidence],
 exported_group_joins:[Planned<ExportedGroupAssociation>],
 native_test_joins:[Planned<NativeTestAssociation>]}
MetadataJoinPlan = {metadata:SlotRef,id_column_index_0based:index,alignment:SlotRef,
 alignment_identity:raw_header|member_label,case_policy:'preserve',
 duplicate_policy:'retain_unresolved',evidence:[Evidence]}
CategoryPlan = {category_id:id,metadata:SlotRef|null,
 metadata_column_index_0based:index|null,raw_heading_token:text|null,
 native_category_ordinal_1based:positive|null,native_output_stem:text|null,
 input_mode:files|groups|auto,group_identity_rule:'exact_category_value',evidence:[Evidence]}
BiologicalPopulationPlan =
 {kind:'explicit',population:BiologicalGroupPopulation} |
 {kind:'observed_metadata_groups',group_population_id:id,category_id:id,
  order:'first_metadata_occurrence',include_metadata_only:bool,evidence:[Evidence]}
NativeGroupMap = {category_id:id,entries:[{raw_group_value:text,
  native_group_ordinal:positive,group_id:id,evidence:[Evidence]}],
  completeness:Completeness,evidence:[Evidence]}
RColumnEvidence = {category_id:id,adjusted_matrix:SlotRef,
  interpreter_version:id,columns:[{r_column_index_0based:index,r_group_token:id,
   native_group_ordinal:positive|null,group_id:id|null,evidence:[Evidence]}],
  completeness:Completeness,evidence:[Evidence]}
```

Category group IDs derived by `exact_category_value` are canonical UTF-8 percent encoding of category ID and exact metadata value under `metacats_group:<category>/<value>`; blank group values remain blank labels and are not conflated with missing cells. A metadata-derived biological population uses first observed metadata occurrence only as its explicitly chosen calculation order, never as R order. It inherits metadata/join completeness; including metadata-only groups is an explicit choice. Explicit memberships and source-group bindings are needed for groups-mode evidence when no original TSV exists. Auto mode preserves its ordered original parameter entries, supplied feature IDs and actual sequence acquisition; duplicate `{id,grp}` entries are not deduplicated silently. The adapter authenticates original group/auto InputBinding existence and every AutoGroupEntry.original_parameter_pointer and exact feature/group value against the original request before calling extract_metacats_associations. That pure extractor has no original InputBinding inventory; it validates a nonempty original binding ID and internal entry/pointer/category relations without requiring that original binding in AssociationSet.original_members. Such a request may legitimately have zero MemberFacts and no FASTA before retrieval. Every supplied member_key must still resolve to an actual common original_member, including when the fetched occurrence belongs to a different input binding. Empty fetched membership preserves known requested provenance with unresolved sequence links, never fabricated members or invented original content. This incorporates root's accepted association clarification012 and its explicit zero-MemberFact follow-up. Source-native ordinal maps, actual R-column evidence and exported-label associations remain independent operands; disagreement yields the corresponding `wrong_native_label` or conflicting state. A manually supplied join cannot make duplicated/conflicting metadata disappear. Native per-test `test_id` is nullable until its actual category/position/group identity is resolved; it is a native test identity, not a falsely equated recalculated test ID.

The additional supplied role `xmfa_sources` has exactly the closed payload, source-reader variants and byte-verification translation in `XMFA_PROVIDER_EXTENSION_001.md`. It is permitted only for the MSA provider. Common, function, taxonomy, MSA, MetaCATS, run and XMFA roles form the complete supplied-role union; no arbitrary role dispatch is accepted.

## Resolver output and local failures

```python
resolve_bundle(bundle, *, artifact_bytes, supplied_values, parameters, provider) -> Resolution
```

`Resolution` is a pure value record, not an active object or agent:

```text
Resolution = {provider:msa|metacats,parameters:Parameters,selections:[SelectionOutcome],
 analyses:[ResolvedAnalysis],requirements:[Requirement],diagnostics:[Diagnostic]}
SelectionOutcome = {analysis_id:id,slot_id:id,semantic_role:<role>,source:SourceBinding,
 reader:ReaderSpec|null,state:resolved|missing|ambiguous|incomplete|invalid|retained_unparsed,
 artifacts:[Artifact],content_bindings:[Content],acquisition_receipt_refs:[id],
 document_ids:[id],tree_ids:[id],requirement_ids:[id],diagnostics:[Diagnostic]}
ResolvedAnalysis = {analysis_id:id,status:ok|partial|invalid,
 analysis:MSAAnalysis|MetaCATSAnalysis|null,inputs:[host InputBinding],
 documents:[ParsedDocument],read_outcomes:[ReaderOutcome],
 scientific_values:[{role:<supplied role>,evidence:Evidence,value:<role's closed type>}],
 population_plans:[PopulationPlan],calculation_parameters:Planned<CalculationParameters>,
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

Non-resolvable optional fields of a saved analysis become null/list omissions only when its closed type permits that value; the matching SelectionOutcome and requirement retain the missing planned identity. Missing nested joins are retained as unresolved association rows or quarantined with exact paths. Do not create structurally invalid reference IDs and let a later broad exception hide them.

Specific finite new requirement/diagnostic codes: `alignment_original_task_conflict`, `alignment_slot_missing`, `alignment_slot_ambiguous`, `alignment_slot_incomplete`, `alignment_slot_sha256_conflict`, `alignment_declared_format_conflict`, `alignment_supplied_content_unbound`, `alignment_supplied_evidence_unbound`, `alignment_supplied_value_invalid`, `alignment_document_unavailable`, `alignment_member_join_missing`, `alignment_member_join_conflicting`, `original_member_occurrence_ambiguous`, `alignment_transformation_unproven`, `alignment_original_coordinates_required`, `msa_reference_unresolved`, `msa_consensus_correspondence_unresolved`, `msa_segment_membership_unresolved`, `msa_prealigned_definition_mismatch`, `msa_full_xmfa_binding_required`, `alignment_deployed_version_unproven`, `metacats_metadata_join_missing`, `metacats_metadata_duplicate_conflict`, `metacats_category_conflict`, `metacats_biological_group_membership_required`, `metacats_native_ordinal_required`, `metacats_r_column_evidence_required`, `metacats_exported_label_conflict`, `metacats_original_hash_provenance_required`, `metacats_test_family_incomplete`, `alignment_calculation_dependency_unavailable`, `alignment_calculation_invalid`, `alignment_projection_dependency_unavailable`, `alignment_unregistered_qualification`. Existing pure-function/host codes also remain registered verbatim. Each requirement ID scopes provider/analysis/slot-or-request/reason using separately escaped segments. Native/provenance qualifications can coexist with available mathematical values.

`invalid` means malformed or contradictory closed top-level contract, hash/identity contradiction, or no valid analysis envelope. Missing independent scientific evidence is `partial` with null dependent facts and retained valid calculations. `failed` is used only when the original bundle failed and no requested scientific value is usable. `ok` means the **requested projection** is satisfied, not that every optional mode/input/qualification is complete. All analysis failures remain saved even when the requested projection uses a successful analysis. No broad catch can convert a conflict to an empty-success result. Empty measured populations and header-only exports are represented explicitly, not treated as absent bytes.

```text
SheetSet = {schema_version:'bvbrc_alignment_sheet_set_v1',tool:C-L204-MSA|C-L205-MetaCATS,
 selections:[SelectionOutcome],analyses:[{analysis_id:id,status:ok|partial|invalid,
  sheet:MSASheet|MetaCATSSheet|null,requirements:[Requirement],diagnostics:[Diagnostic]}]}
ComponentSet = {schema_version:'bvbrc_alignment_component_set_v1',
 analyses:[{analysis_id:id,components:Components|null}],
 multiplicity_families:[{family_request_id:id,status:ok|partial|invalid,
  value:<existing MultiplicityResult>|null,requirements:[Requirement],diagnostics:[Diagnostic]}]}
```

## Finite requested projection contract

`requested_form_schema(fields)` takes `{parent_field_name:FactSelection}` and returns a closed JSON schema with all fields required and an `x-alignment-fact` annotation containing the exact selection. `validate_requested_form` reconstructs it and requires canonical equality (apart from required-key order). This is an ordinary finite projection catalog. Arbitrary formulas, paths, whole-sheet dumps, raw stdout and free-text findings are not selections.

Every selection has `kind`, plus the fields specified here:

```text
measurement: {analysis_id,request_id,metric:<catalog>,selector:<catalog selector>}
native_measurement: {analysis_id,table:SlotRef,row_index:index,field:NativeFieldSelector}
msa_sites: {analysis_id,request_id,columns_0based:[index]}
reference_differences: {analysis_id,request_id,row_indices:[index],columns_0based:[index]}
group_counts: {analysis_id,request_id,columns_0based:[index],group_ids:[id],symbols:[text]}
statistical_tests: {analysis_id,request_id,tests:[TestSelector]}
function_composition: {analysis_id,request_id,function_keys:[id]}
tree_branches: {analysis_id,request_id,node_indices:[index]}
multiplicity: {analysis_id:id|null,request_id:id|null,family_request_id:id|null,
 selection:all_family|explicit_tests,tests:[ScopedTestSelector]}
qualifications: {analysis_id,slot_id:id|null,request_id:id|null}
missing_requirements: {}
```

For multiplicity exactly one local `(analysis_id,request_id)` or global `family_request_id` is nonnull. `all_family` requires tests=[] and copies every saved result row in that explicitly selected family; `explicit_tests` resolves the exact analysis-scoped selectors through the original source results to IDs already in that saved family. Local selectors must name the local analysis. No future calculated ID is required at commissioning and no lookup joins by category alone. Other empty row selectors, including multiplicity explicit_tests=[], mean an explicitly empty selection, never implicit all rows. Every selected row must belong to its originally selected calculation population. Request-kind compatibility is validated before value lookup. `NativeFieldSelector` is the closed union `{kind:'score'|'n_sequences'|'chi_square'|'p_value'|'df'}` (each literal is a separate tag), `{kind:'dna_count',symbol:A|T|G|C|Deletion}`, `{kind:'protein_count',detail_index:index}`, `{kind:'export_group_count',heading_index:index,count_index:index}`, or `{kind:'raw_r_group_count',position_1based:positive,count_index:index}`. Native positions use original data-row ordinal, not a guessed future observation ID. The selected field must exist in the declared reader kind; it resolves to exactly one saved NativeObservation. This makes the original selector commissionable before output bytes/IDs exist. The four additional finite XMFA selectors/fact types are exactly the additive extension.

Closed measurement catalog; selector keys are exact and all mandatory (empty selector is `{}`):

| Request kind | Allowed metric tokens | Selector |
|---|---|---|
| alignment | member_count, site_count, cell_count, gap_cells, gap_fraction, canonical_cells, canonical_fraction, ambiguity_cells, ambiguity_fraction, stop_cells, stop_fraction, other_nongap_cells, other_nongap_fraction | {} |
| alignment | site_gap_count, site_canonical_count, site_ambiguity_count, site_stop_count, site_other_nongap_count, site_gap_fraction, site_canonical_fraction, site_canonical_majority_fraction, site_canonical_entropy_bits | {column_0based} |
| alignment | row_nongap_count, row_matrix_occupancy | {row_index} |
| alignment | pair_identical_positions, pair_substitutions, pair_both_gap_positions, pair_a_gap_only_positions, pair_b_gap_only_positions, pair_unpaired_nongap_ambiguous_positions, pair_identity_fraction | {row_a,row_b} |
| original_coverage | original_length, original_covered_positions, original_member_coverage | {row_index,input_binding_id,member_id} |
| msa_entropy | eligible_count, internal_gap_count, terminal_gap_excluded_count, literal_entropy_bits, native_score_recalculated, score_residual | {column_0based} |
| msa_reference_differences | difference_category_count | {row_index,category:<six accepted categories>} |
| native_statistics / biological_statistics | epsilon, augmented_total, continuity_delta, chi_square, df, mathematical_p, log_p | {test:TestSelector} |
| native_statistics | native_zero_rule_p | {test:TestSelector} |
| native_effects / biological_effects | raw_chi_square, cramers_v, raw_minimum_expected, raw_cells_below_5, raw_cells_below_1, raw_cell_denominator | {column_0based} |
| native_effects / biological_effects | total_variation | {column_0based,group_ids:[id,id]} |
| native_effects / biological_effects | frequency_delta | {column_0based,group_ids:[id,id],symbol:text} |
| expected_adequacy | minimum_expected, cells_below_5, cells_below_1, cell_denominator | {test:TestSelector} |
| function_composition | total_members, members_with_recorded_assignment, members_without_recorded_assignment | {} |
| function_composition | assigned_members, fraction_all, fraction_recorded | {function_key} |
| taxonomy | known_members, unknown_members, distinct_known_taxa, same_taxon_pairs, known_taxon_pairs, same_taxon_pair_fraction | {} |
| taxonomy | taxon_member_count | {taxon_id} |
| tree | tip_count, internal_node_count, rooted_representation_polytomies, unrooted_degree_polytomies, branch_length_sum, known_branch_length_sum, missing_branch_length_count | {} |
| tree | branch_length, support_rescaled | {node_index} |
| tree | patristic_distance | {node_a,node_b} |
| relationship_comparison | matched_tips, gene_splits, organismal_splits, shared_splits, rf, rf_fraction | {} |

Metric names above map to exact saved cells (the `site_`, `row_`, `pair_`, `raw_adequacy` and branch/distance mappings are fixed in code). Taxonomy names are the exact installed output keys; there is no invented `total_members` taxonomy cell. `taxon_member_count` maps to `rows[taxon_id].member_count`. `branch_length` maps to `branches[node_index].length`, and `patristic_distance` to `distances[node_a,node_b].value`. `ungapped_map` remains an internal component usable for validated reference-difference correspondence; it does not expose arbitrary raw maps by default.

All outward value records are closed:

```text
MeasurementFact = {value:number|null,state:State,unit:rows|columns|characters|positions|
 sequences|observations|members|taxa|pairs|tips|nodes|edges|splits|fraction|signed_fraction|
 bits|hundredths_of_bit|pseudocount_per_cell|augmented_observations|expected_observations|
 cells|chi_square|degrees_of_freedom|probability|natural_log_probability|
 expected_substitutions_per_model_site|joint_mixed_partition_model_site|native_unknown|
 percent|native_statistic|nucleotides|nucleotide_placements,
 origin:native_observation|calculated|fitted|derived|native_observed|native_fitted,
 method_ref:id,population_ref:id|null,numerator:number|null,denominator:number|null,
 requirement_refs:[id]}
MSASiteFact = {alignment_ref:id,population_ref:id,column_0based:index,
 eligible_count:number|null,internal_gap_count:number|null,
 terminal_gap_excluded_count:number|null,literal_entropy_bits:number|null,
 native_score_recalculated:number|null,score_residual:number|null,
 strict_majority_consensus:text|null,requirement_refs:[id]}
DifferenceFact = {alignment_ref:id,row_index:index,column_0based:index,
 member_character:text,reference_character:text,category:<six accepted categories>,
 member_ungapped_position_0based:index|null,reference_ungapped_position_0based:index|null,
 member_original:OriginalCoordinateFact|null,reference_original:OriginalCoordinateFact|null}
OriginalCoordinateFact = {member_ref:id,interval_0based_half_open:[index,index],
 strand:+|-|unknown,translation_table:positive|null,transformation_ref:id|null}
GroupCountFact = {alignment_ref:id,population_ref:id,category_ref:id,group_ref:id,
 column_0based:index,symbol:text,count:index|null,
 basis:biological|native_reproduction,state:State,requirement_refs:[id]}
StatisticalTestFact = {test_ref:id,category_ref:id,column_0based:index,
 kind:omnibus|pairwise,group_refs:[id],basis:biological|native_reproduction,
 chi_square:number|null,df:number|null,p_value:number|null,log_p:number|null,
 native_zero_rule_p:number|null,numerical_state:finite|underflow|unavailable,
 requirement_refs:[id]}
FunctionFact = {population_ref:id,function_ref:id,assigned_members:number|null,
 total_members:number|null,members_with_recorded_assignment:number|null,
 fraction_all:number|null,fraction_recorded:number|null,requirement_refs:[id]}
BranchFact = {tree_ref:id,node_index:index,split_ref:id|null,length:number|null,
 length_unit:expected_substitutions_per_model_site|joint_mixed_partition_model_site|
 native_unknown,support_rescaled:number|null,
 support_method:fasttree_sh_like|native_unknown,
 support_scale:percent|fraction|statistic|native_unknown,requirement_refs:[id]}
MultiplicityFact = {family_ref:id,test_ref:id,input_p:number|null,adjusted_p:number|null,
 method:none|bonferroni|holm|bh|by,alpha:number,total_test_count:index|null,
 rejected_at_alpha:bool|null,p_value_basis:native_unadjusted|
 source_mathematical_recalculation|biological_mathematical_recalculation,
 requirement_refs:[id]}
QualificationFact = {code:<registered finite diagnostic codes>,
 phase:custody|prepare|transport|native_decode|association|publication|recovery|return,
 severity:error|qualification,
 role_ref:id|null,requirement_refs:[id]}
RequirementFact = {requirement_ref:id,kind:definition|input_metadata|input_bytes|
 original_task|task_manifest|output_metadata|output_bytes|byte_version_evidence|
 scientific_metadata|parser_binding,role_ref:id|null,source_refs:[id],reason_ref:id}
```

Selections produce `MeasurementFact`, arrays of their matching fact type, or null only when the selected collection dependency is unavailable. A zero row result is `[]` only when the exact selected population is known empty. `missing_requirements` makes a one-to-one `RequirementFact` projection of the adapter's exact selected missing requirements, preserving original kind/source refs and canonically scoping the requirement/role/reason identifiers; the host AdapterResult.missing_requirements itself stays unchanged. Raw diagnostic messages stay internal. For raw count selections, a known absent symbol in a complete selected table is measured zero; incomplete tables yield null/qualified state. Biological test projections have `native_zero_rule_p=null` with basis biological; they never imply a native observation. Native scalar measurements retain native token state internally and return null when not available. No coordinate is returned without its identity proof.

References use `bvbrc_alignment_<kind>:<percent-encoded analysis_id>/<percent-encoded identifier>`; kinds are `field|alignment|member|population|category|group|tree|split|function|taxon|comparison|test|family|method|transformation|role|requirement|reason`. Each segment is canonical UTF-8 percent encoding and decoding verifies round trip. Global family IDs use reserved analysis segment `@families`. All requirement references (including those inside MeasurementFact/other facts) use reserved segment `@requirements` and the exact original requirement_id; RequirementFact role/reason references use the same segment and exact raw role/reason. This keeps host-origin and per-analysis requirements consistent without mutating their original records. Reject caller analysis IDs equal to either reserved segment. These are scoped identifiers, not Store receipt refs; real source/execution-result refs retain the host namespaces. Requested fields, category/group membership and test/row/coordinate relationships must validate against saved sheets/components and the original selected form.

## Saved facts and actual downstream consumers

New `bvbrc_alignment_returns.py` exports:

```python
alignment_fact_sources() -> dict
requested_sources(schema: dict) -> tuple[str,...]
project_alignment_facts(body: dict, *, requested_sources,
    sheet_set: dict|None, component_set: dict|None) -> dict
class BVBRCAlignmentReturns(EpisodeReturnRecords):
    def __init__(self, execution): ...
    def facts(self, context, schema): ...
    def received_context(self, context): ...
    def received_facts(self, context, schema): ...
    def validate_received_report(self, context, form, schema): ...
    def record_admission(self, context, form, schema, operation_key): ...
    def resolve_own(self, context, reference, namespace): ...
    def resolve_received(self, context, reference, namespace): ...
```

Finite fact-source names are `bvbrc_alignment_measurements`, `bvbrc_alignment_msa_sites`, `bvbrc_alignment_reference_differences`, `bvbrc_alignment_group_counts`, `bvbrc_alignment_statistical_tests`, `bvbrc_alignment_function_composition`, `bvbrc_alignment_tree_branches`, `bvbrc_alignment_multiplicity`, `bvbrc_alignment_requirements`, `bvbrc_alignment_qualifications`. Each source contains records `{source_ref:<actual execution_result ref>,field:<scoped field identifier>,value:<exact corresponding fact or nullable fact array>}`. `native_measurement` and `measurement` share the measurement family. Fact schemas enumerate fields, units, origins, enums and reference namespaces. No unrestricted findings/instructions strings.

The host authenticates both saved sheet and saved component content, original owner/run/scope/assignment, original selector, adapter pin, receipt and frozen result body. `project_alignment_facts` copies **only saved AdapterResult.facts**, validating selected identities against supplied saved proof. It does not rerun parsers/calculators, reproject unrequested metrics, open files or acquire data. Receiving episodes forward those exact validated requested values through `EpisodeReturnRecords`; they do not scan another episode's latest files or recalculate. Admission checks the exact original child report and actual received dependency refs. Null values do not excuse a forged test/group/row selector.

Required actual consumer edits (one integration owner):

* `bvbrc_appservice_adapters.bind_adapters` adds the two explicit installed pins; `selected_adapter` remains ordinary lookup.
* `APIServiceExecution.__init__` creates `self.alignment_returns`; `APIServiceExecution.resolve(context,reference,namespace)` adds only the new identifier namespaces.
* `BVBRCAppServiceHost.facts(context)` includes `alignment_returns.facts(context,schema)`; publication `_grade`, immutable storage, recovery and exact original endpoint completion remain unchanged.
* `ExecutionEpisodes.resource_tool_contracts` discovers only configured MSA/MetaCATS pins. `_appservice_sources`, `received_report_facts`, `resolve_received_reference`, `validate_received_report`, `received_form_references`, and `resolve` add the matching return owner. `received_report_sources` and `fact_sources` then consume the augmented existing source dictionary.
* Existing `bound_resource_tool_contracts(binding)`, `tool_information_contracts(direct_catalog,resource_catalog=())`, and `WorkflowServices.tool_information_catalog(scope)` continue to carry the exact declared commissioning route; no direct root scientific callable is added.

## Tool information and real invocation

New `bvbrc_alignment_tool_info.alignment_tool_contracts(*,resource_id:str,assignment_schema:dict,provider:str)->list[dict]` accepts provider `bvbrc_msa` or `bvbrc_metacats`. Preserve the three construction slots `evidence_axis`, `thought_pattern`, `child_tool_info`. Every child_tool_info has `name`, `description`, `resources`, `instructions`; include actual callable input_schema and commission routes using the existing pattern. Name/resource/description support parent selection; the selected child receives substantive instructions.

Proposed names are `bvbrc.msa.ordinary_alignment`, `bvbrc.msa.prealigned_analysis`, `bvbrc.msa.segment_alignment`, `bvbrc.msa.segment_concatenation`, `bvbrc.msa.mauve_alignment`, `bvbrc.metacats.files`, `bvbrc.metacats.groups`, `bvbrc.metacats.auto`. These map to native application `MSA` or `MetaCATS`, not to a new native app. Only installed adapter + original assignment contract establishes a bound route. Library mode descriptions retain unfinished prerequisites; they do not advertise an unsupported native parameter as executable.

The prealigned analysis descriptor can expose the real results-analysis route for supplied/authenticated prealigned output. Its prealigned **launch bypass** is not advertised as bound until actual definition evidence resolves the file-type mismatch. Keep the unfinished launch mode in accounting and source information; do not silently widen preparation enums or call an ordinary realignment a bypass. Other modes similarly advertise only actual installed routes. No capability check performs a service probe or independently chooses execution.

Instructions must distinguish launch preparation, explicit selected primitive AppService submission, selected status/log observation, Workspace enumeration/capability/download, original input transfer, requested result parser selection and typed return. Generic launch/API/results episodes own their iterations; no fixed polling itinerary. Real MSA source combines actual supplied file/group/feature/genome/segment input fields; it does not obey a single invented input_type switch. Current app definition does not declare the source's aligned-file type used for prealigned bypass. `prealigned_analysis` stays explicitly qualified until actual definition evidence resolves that mismatch; do not widen preparation enums silently. MAFFT/MUSCLE/progressiveMauve routes retain actual selected software evidence, and legacy ClustalW/RNA descriptions do not establish a current route. MetaCATS files/groups/auto have different acquisition/case/preparation provenance; MAFFT-aligned groups or auto entries are not falsely described as prealigned file input. Local retained-native component executions are verification evidence, not proof of a live BV-BRC deployment.

TASK remains the detailed recurring selected operation and constraints; STEERING contains only compact relevant prior facts. Full sheets, raw output, host hashes and internal tracking IDs stay outside model-facing prompts. No changes to W05, literature graders, scientific credit, timers, continuation or existing BLAST behavior are proposed.
