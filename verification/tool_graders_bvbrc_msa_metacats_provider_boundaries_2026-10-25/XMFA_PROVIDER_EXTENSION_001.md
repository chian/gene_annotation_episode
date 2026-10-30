# Additive XMFA extension before initial provider v1 implementation

2026-10-25. Root explicitly accepted extending the not-yet-installed/published provider v1 before implementation, without creating a needless v2. The frozen base association and math files remain unchanged. This document specifies the exact additions and superseding closed records/signature; it does not modify the accepted pure XMFA types or existing AFA functions.

Normative pure dependency: `../tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/PROPOSED_CONTRACT.md`, SHA256 `f6ebf5348d260c2f84b6cf3d245a050a329b0fd670aa237a4a769f340943f701`, accepted by root's `ACCEPTED_XMFA_BOUNDARY_008.json`. Every nested XMFADocument, XMFASourceInputs, XMFASourceBindings, XMFASelection, CellRef, RecordRef, XMFACoordinates, XMFAInverseCoordinates, XMFAAlignmentComponents and XMFACoverageComponents record is exactly that complete contract. In particular XMFAMetadata.integer_value is the native Entry token; metadata member_number is distinct. Do not import a stale earlier proposal without that field.

Root owns the actual `xmfa_sources.bind_xmfa_sources(document,*,inputs,source_comparison)` and `validate_xmfa_bindings_for_document(document,bindings)`, plus `xmfa_source_contracts` and their tests. Their complete installed implementations were inspected for this extension. Root's additive XMFA diagnostic clarifications009/010 also apply. Optional original maps are not required for a valid native/staged-source binding. Source consumers must call the document-aware validation helper, which rechecks saved match records against the actual supplied XMFA and source_sequence. An authenticated arbitrary JSON sequence claim is not proof of equality with unrelated file bytes. Common AssociationSet includes root's accepted member_entities clarification013; original occurrence/entity identity is never inferred from equal names or shared evidence.

## Exact ReaderSpec, documents and source identity

Add the MSA-only closed reader variant:

```text
{reader:'mauve_xmfa_v1',dialect:'mauve1',alphabet:'dna',encoding:ascii|utf-8}
```

Dispatch only to `xmfa_formats.parse_mauve_xmfa(data,*,artifact,dialect,alphabet,encoding)`. Add `ParsedDocument={kind:'xmfa',value:XMFADocument}` to the existing closed union; validate with `xmfa_format_contracts.validate_xmfa_document`. The selection's semantic role is `full_xmfa`. A parser not yet installed remains an explicit parser_binding requirement, not fallback to FASTA. Parser partial diagnostics/valid blocks remain retained.

Superseding exact closed MSAAnalysis (one added field):

```text
{analysis_id:id,mode:ordinary_new_alignment|ordinary_prealigned|segment_alignment|
 segment_concatenation|mauve_first_block_projection|mauve_blocks,
 alignment_id:id|null,frequency_table_id:id|null,consensus_alignment_id:id|null,
 tree_id:id|null,full_xmfa_slot_id:id|null,xmfa_document_id:id|null,
 segment_ids:[id],reference:ReferenceBinding|null,output_role_evidence:[Evidence]}
```

`full_xmfa_slot_id` is the original caller-owned slot name in this analysis. It is **not** an acquired document ID, bytes hash, block ID or original member ID. `xmfa_document_id` is the actual parsed artifact-derived XMFADocument.document_id. Its commissioning form is SlotRef|null; compile it once after acquisition. When both are nonnull they must identify the same original full_xmfa selection. Missing bytes/parser leave actual document ID null with the exact slot requirement retained.

Full block requests require mode mauve_blocks. The first-block AFA/native frequency calculation remains a separately identified mauve_first_block_projection analysis, even when both derive from the same native job. Preserve that dependence. No flattened AlignmentDocument cast, inherited whole-genome denominator, row-index-as-member-number shortcut, or automatic block concatenation is allowed.

## Source input role and verified-byte handoff

Add supplied scientific role `xmfa_sources`, with authenticated closed value:

```text
{version:'bvbrc_msa_xmfa_sources_v1',analysis_id:id,
 items:[{document:SlotRef,inputs:XMFASourceInputs,
         source_readers:[XMFASourceReader],
         source_comparison:'case_insensitive_iupac_exact',evidence:[Evidence]}]}
XMFASourceReader =
 {file_id:id,reader:'fasta_records_for_xmfa_v1',
  id_rule:'first_whitespace_token',encoding:ascii|utf-8} |
 {file_id:id,reader:'raw_dna_for_xmfa_v1',encoding:'ascii'}
```

Each document is unique in this role and resolves to a selected XMFADocument. Source readers have unique file_id, refer to actual inputs.files, and must match their declared FastA/raw format; no encoding is guessed from filenames or decoder fallback. The full supplied typed source inputs remain retained. Every `files[*].artifact` must correspond to actual authenticated original selected Content, byte count and digest; source path strings remain uninterpreted recorded tokens, never local paths to open. Missing source bytes cannot be repaired by later arbitrary sequence retrieval or matching a basename/label/taxon. Add MSA-only semantic role `xmfa_staged_source`; it permits reader=null because this exact source-reader contract verifies its bytes without casting them to an alignment. Its supplied/acquired selection uses the unchanged SourceBinding union and custody checks.

New MSA-provider-owned pure module `bvbrc_msa_xmfa_inputs.py` has:

```python
verify_xmfa_source_inputs(inputs: dict, *,
    source_readers: tuple[dict,...], artifact_bytes: dict[str,bytes],
    content_bindings: tuple[dict,...], associations: dict) -> dict

extract_msa_xmfa_bindings(document: dict, *, verification: dict,
    source_comparison: str, evidence: tuple[dict,...]) -> dict
```

The adapter supplies only authenticated selected bytes, exact Content records and the validated common AssociationSet. `artifact_bytes` is keyed by Content.artifact_ref; each input Artifact's raw_artifact_ref, source_ref and sha256 must equal its Content binding, and actual byte length/digest must match. Original maps must resolve the full occurrence key, known original length and transformation_id in that AssociationSet; a merely matching label is insufficient. These functions perform no Store/path/network access. `verify_xmfa_source_inputs` returns:

```text
XMFASourceVerification = {supplied_inputs:XMFASourceInputs,
 source_readers:[XMFASourceReader],verified_inputs:XMFASourceInputs,
 files:[SourceFileVerification],
 status:ok|partial|invalid,requirements:[Requirement],diagnostics:[Diagnostic]}
SourceFileVerification = {file_id:id,artifact:Artifact,
 format:FastA|GenBank|raw|DNAstar,
 reader:XMFASourceReader|null,
 state:verified|missing_bytes|incompatible|unsupported,
 requirements:[Requirement],diagnostics:[Diagnostic]}
XMFABindingRecord = {document_id:id,source_comparison:'case_insensitive_iupac_exact',
 verification:XMFASourceVerification|null,bindings:XMFASourceBindings|null,
 state:resolved|partial|missing|conflicting,evidence:[Evidence],
 requirements:[Requirement],diagnostics:[Diagnostic]}
```

`verified_inputs` preserves original invocation declaration and ordered_file_ids. It contains only the actual byte-verified file records and original maps whose file/record and original member are themselves validated. Unsupported/missing/conflicting files and their full claimed records remain in supplied_inputs, SourceFileVerification and precise requirements. Original maps omitted from the effective inputs remain explicitly retained in supplied_inputs and qualified; they are not silently accepted or erased. The binder can therefore resolve valid members while other files remain missing. If there is no usable source input, return a missing/partial XMFABindingRecord and use bindings=None for source-dependent calculations; literal/native-coordinate work remains independent.

Exact initial byte-verification contracts:

* **FastA (`fasta_records_for_xmfa_v1`):** call the existing `parse_aligned_fasta` with exactly the selected first_whitespace_token and ASCII/UTF-8 encoding. Compare complete physical record order, exact raw_header (without `>`), entry_1based, parsed sequence and source location against every supplied XMFAInputRecord; record_id remains the caller's distinct identifier. The shared parser's unequal-length diagnosis does not make an unaligned FASTA record population incomplete: accept differing record lengths for this source-record interpretation when syntax/encoding/header/record boundaries are complete. Never claim that such a source is a complete alignment. Only layout whitespace normalization already declared by the shared reader is allowed and remains qualified; biological symbol validation requires ungapped DNA IUPAC as in the accepted source contract. No header inference, symbol stripping or sequence sorting. A source reader declaration is required even when a compatible alignment parse is already cached.
* **Raw DNA (`raw_dna_for_xmfa_v1`):** one record, entry_1based=1, header=null; ASCII DNA IUPAC in either case with optional CRLF/LF physical line endings. Remove only those line endings, never spaces, digits, dashes, comments or unknown symbols. Compare the exact resulting sequence and full-file Location to the supplied record. Empty bytes yield an explicitly empty record only if that is the actual declared complete raw record; they cannot establish a nonempty source or successful alignment.
* **GenBank/DNAstar:** first production provider v1 has no actual bound source-record extractor for these formats. Retain their full bytes/declarations and return `kind=parser_binding, role=xmfa_source_record_extractor, reason_code=xmfa_source_extractor_unbound`. They cannot enter verified_inputs solely because their JSON claim is authenticated. A future actual bound extractor plus source-reader provenance requires an explicit additive contract; a generic arbitrary-reader escape hatch is not provided here. Current BV-BRC MSA's staged input.fasta route remains usable.

Byte mismatch uses `xmfa_source_record_bytes_conflict`; missing content uses `xmfa_source_bytes_required`; missing source-reader declaration uses `xmfa_source_reader_required`; original identity/map failure uses the accepted original-map requirements. The verification record is a pure deterministic source-record check, not an acquisition result or scientific confidence score. Artifact source hashes and Content bindings remain exact. `extract_msa_xmfa_bindings` calls root's `bind_xmfa_sources` on verified_inputs, then `validate_xmfa_bindings_for_document` before returning the full typed binding. Source comparison is the accepted case-insensitive IUPAC exact match, with strand/complement and concatenated-file component boundaries preserved. Authentication of the invocation declaration proves the supplied value's custody; it does not alone prove that a real command used that order. Preserve its actual evidence role and run association.

## Superseding provider sheet and signature

The superseding initial `bvbrc_msa_sheet_v1` closed record is exactly:

```text
MSASheet = {schema_version:'bvbrc_msa_sheet_v1',tool:'C-L204-MSA',
 analysis:MSAAnalysis,inputs:[host InputBinding],run:RunRecord,
 documents:[ParsedDocument],read_outcomes:[ReaderOutcome],associations:AssociationSet,
 populations:Populations,segments:[Segment],consensus_associations:[ConsensusAssociation],
 tree_bindings:[TreeBinding],native_observations:[NativeObservation],
 native_tree_measurements:[NativeTreeMeasurement],support_observations:[SupportObservation],
 xmfa_bindings:[XMFABindingRecord],requirements:[Requirement],diagnostics:[Diagnostic]}
```

Every nested non-XMFA type is exactly the frozen complete record plus root's accepted association clarifications012/013. Ordinary analyses store xmfa_bindings=[]. MSAAnalysis uses the superseding closed record above. Add no XMFA fields to MetaCATSSheet, AlignmentDocument or existing MSA arithmetic outputs.

Superseding exact extraction signature:

```python
extract_msa_sheet(*, analysis: dict, inputs: tuple[dict,...],
    documents: tuple[dict,...], read_outcomes: tuple[dict,...], run: dict,
    associations: dict, populations: dict, segments: tuple[dict,...],
    tree_bindings: tuple[dict,...], parameters: dict,
    xmfa_bindings: tuple[dict,...] = ()) -> ParseResult[MSASheet]
```

Validate each binding record against the exact selected XMFADocument, source artifact/content provenance and original members/maps. `validate_msa_sheet` invokes root's document-aware binding validator for any nonnull bindings. A stored `match` label cannot validate an altered source/XMFA row. Absence of original maps does not invalidate source binding or native coordinate/literal component calculations; requested original coverage reports specific missing maps. Saved documents/source records/matrices remain sufficient for no-I/O recalculation.

## Four exact calculation requests and existing pure consumers

Add these MSA-only tags to CalculationRequest and use the existing CalculationOutcome wrapper unchanged. `document_id` is a SlotRef at commissioning and actual ID in resolved provider parameters. Selection.document_id is compiled the same way. `use_source_bindings` is an explicit bool; false passes None; true passes the validated matching binding when available and None plus its exact missing requirements when not available. It never launches source acquisition.

```text
{kind:'xmfa_column_coordinates',request_id:id,document_id:id,
 cells:[CellRef],use_source_bindings:bool}
{kind:'xmfa_source_positions',request_id:id,document_id:id,
 queries:[{member_number:positive,position_0based:index}],use_source_bindings:bool}
{kind:'xmfa_alignment_components',request_id:id,document_id:id,
 selection:XMFASelection,selected_pairs:[[positive,positive]],case_policy:preserve|uppercase}
{kind:'xmfa_interval_coverage',request_id:id,document_id:id,
 selection:XMFASelection,use_source_bindings:bool,
 basis:represented|multi_member_block|cooccupied_column}
```

Dispatch exactly to `xmfa_coordinates.xmfa_column_coordinates(document,*,cells,bindings)` and `xmfa_coordinates.xmfa_source_positions(document,*,queries,bindings)`, and to `xmfa_calculators.xmfa_alignment_components(document,*,selection,selected_pairs,case_policy)` and `xmfa_calculators.xmfa_interval_coverage(document,*,selection,bindings,basis)`. Their results are the complete accepted XMFACoordinates, XMFAInverseCoordinates, XMFAAlignmentComponents and XMFACoverageComponents. Root's `ACCEPTED_XMFA_CALCULATORS_WORKLOAD_014.md` specifies these exact module boundaries and the five validators in xmfa_calculation_contracts. Preserve all parameters, selected population, missing states, blocks, repeated placements and known union versus full coverage distinctions. These functions are a separately assigned math workload; their contract acceptance is not a claim they are installed today.

## Four finite requested projections

Extend the finite FactSelection/catalog; no arbitrary component pointer is accepted:

```text
{kind:'xmfa_coordinates',analysis_id:id,request_id:id,cells:[CellRef]}
{kind:'xmfa_source_positions',analysis_id:id,request_id:id,
 queries:[{member_number:positive,position_0based:index}]}
{kind:'xmfa_alignment_measurements',analysis_id:id,request_id:id,
 measurements:[XMFAMetricSelection]}
{kind:'xmfa_coverage',analysis_id:id,request_id:id,member_numbers:[positive],
 include_intervals:bool,include_original_coverage:bool}
```

Every selected cell/query/metric/member must already be present in the original selected calculation. Empty arrays mean explicitly empty return. Facts copy saved values, never compute another coordinate/metric or widen a source search. Add namespaces `xmfa_document`, `xmfa_file`, `xmfa_record` to the canonical reference codec and corresponding saved-reference validation. Original occurrences use the common member namespace with the complete three-field occurrence ID. Actual native member_number is a positive integer within its document, not an original input member reference.

```text
XMFACoordinateFact = {document_ref:id,cell:CellRef,member_number:positive|null,
 aligned_symbol:text,state:residue|gap|absent_zero|incompatible,
 native_position_1based:positive|null,native_position_0based:index|null,
 native_strand:+|-|null,forward_symbol:text|null,
 source_state:resolved|missing|conflicting|not_applicable,
 source_coordinate:XMFAForwardSourceFact|null,original_coordinates:[XMFAOriginalBaseFact],
 requirement_refs:[id]}
XMFAForwardSourceFact = {file_ref:id,record_ref:id,entry_1based:positive,
 position_0based:index,strand:+|-}
XMFAOriginalBaseFact = {member_ref:id,position_0based:index,original_length:index,
 strand:+|-,transformation_ref:id}
XMFAInverseFact = {document_ref:id,member_number:positive,position_0based:index,
 state:unique|multiple|none_in_document|unknown,matches:[CellRef],
 search_completeness:Completeness,requirement_refs:[id]}
XMFAMeasurementFact = {document_ref:id,population_ref:id,selection:XMFAMetricSelection,
 measurement:MeasurementFact}
XMFACoverageFact = {document_ref:id,population_ref:id,member_number:positive,
 basis:represented|multi_member_block|cooccupied_column,source_length:number|null,
 known_union_bases:number|null,placement_bases:number|null,
 multiply_represented_bases:number|null,excess_placement_bases:number|null,
 selected_coverage_fraction:number|null,complement_bases:number|null,
 known_union_intervals:[[index,index]]|null,complement_intervals:[[index,index]]|null,
 membership_completeness:Completeness,original_coverage:[XMFAOriginalCoverageFact]|null,
 requirement_refs:[id]}
XMFAOriginalCoverageFact = {member_ref:id,original_length:number|null,
 known_union_bases:number|null,coverage_fraction:number|null,
 mapping_completeness:Completeness}
```

Coordinate/native/source axes remain explicitly distinct. Missing original maps yield an empty original-coordinate list plus requirement when requested; native residues do not become original positions. Coverage interval arrays are copied only when include_intervals=true, otherwise both are null. Original coverage is copied only when include_original_coverage=true, otherwise null. Empty measured original coverage lists remain distinct from an omitted projection. Root explicitly accepted this additive serialized-unit clarification without changing the frozen pure contract or mathematical meaning: `nucleotides` for source_length, known_union_bases, multiply_represented_bases, complement_bases and original lengths/union counts; `nucleotide_placements` for placement_bases and excess_placement_bases; `fraction` for selected/original coverage fractions. Counts with multiplicity are thus distinguishable from the size of a covered position set. Add exactly `nucleotides|nucleotide_placements` to MeasurementFact's existing finite units. Other XMFA units are already `columns|members|characters|bits|fraction` as declared in the accepted pure contract. Pure calculator validators, saved cells and projection must agree with these exact serialized tokens; do not convert units during projection.

`XMFAMetricSelection` is the following closed union; a metric maps to the identically named saved NumericCell (only the symbol-count wrapper maps to symbol_counts[symbol].count):

```text
{metric:selected_column_count|present_member_count|zero_member_count|omitted_member_count,
 block_index:index}
{metric:site_present_member_count|absent_member_count|gap_count|nongap_count|
 canonical_count|ambiguity_count|other_count|literal_entropy_bits|
 canonical_entropy_bits|canonical_majority_fraction,
 block_index:index,column_0based:index}
{metric:'symbol_count',block_index:index,column_0based:index,symbol:text}
{metric:identical_canonical|substitutions|a_only_gap|b_only_gap|both_gap|
 ambiguous_or_other|comparable_canonical|identity_fraction,
 block_index:index,member_a:positive,member_b:positive}
```

`site_present_member_count` maps to sites[column].present_member_count, distinguishing it from the block count. Every requested symbol must have a saved symbol-count row; requesting an absent symbol does not silently synthesize a new cell. Pair order/identity obeys the exact original selected pair contract. All actual cell method IDs, numerator/denominator, states and requirements survive in MeasurementFact.

Fact-source names are `bvbrc_alignment_xmfa_coordinates`, `bvbrc_alignment_xmfa_source_positions`, `bvbrc_alignment_xmfa_measurements`, `bvbrc_alignment_xmfa_coverage`, using the same `{source_ref,field,value}` wrapper and saved-result-only BVBRCAlignmentReturns path as the base catalog. Update the original requested schema, encode/decode registry and actual saved identity checks together. Do not return complete raw XMFA/source sequences in a model-facing fact field.

## Ownership, tests and remaining qualification

Association owner A implements only the additional ReaderSpec/ParsedDocument validation variant, importing the actual XMFA validator. MSA provider owner C additionally owns new `bvbrc_msa_xmfa_inputs.py` and `tests/test_bvbrc_msa_xmfa_inputs.py`, the explicit extraction/sheet additions, and four dispatch tags. Adapter owner E owns authenticated source-byte selection and four finite projections; return owner F owns corresponding finite sources/reference proof. No provider worker edits root's XMFA source modules or the separate parser/calculator files. Implementation pin includes actual consumed new XMFA modules, not unrelated phylogeny dependencies.

Required retained examples: combined.xmfa's six blocks and 50/41/49 source lengths; represented union50/41/49, multi-member block union48/0/47, cooccupied union46/0/46; first-block pair1/3 has39 identities and7 substitutions over46 canonical comparisons. Minus member1 columns0/28/48 map to native source48/gap/1. Actual first-block AFA has49 columns and remains a separate analysis. Use the actual retained sources and accepted pure examples, not invented source-byte proof. Include source-less literal metrics, missing source bytes, mismatching JSON claimed sequences, correct/incorrect FastA record order, unequal source lengths, partial source files, raw DNA invalid symbols, unsupported GenBank/DNAstar, original map absence, conflicting original maps, changed saved match records, multiple placements/inverse queries, zero records and missing blocks. Recalculate from saved typed inputs without network/native calls, then verify exact selected facts through the ordinary child/parent custody path.

Full XMFA is still **unintegrated** until these provider/adapter/return additions and the actual pure calculators are installed and tested. Current/deployed versions, live AppService custody and full original genome provenance remain separately unverified. None of this turns a structurally readable XMFA into whole-genome biological completeness.
