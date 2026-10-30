# Nine supporting operations: source and reuse boundaries

2026-10-28. Read-only implementation mapping; proposed interfaces below have
not been coded or accepted as completed bindings. This artifact is evidence,
not a goal or scope amendment. The authoritative user attachment was read in
full and its SHA-256 matched
`f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc`.

Only host Python standard-library file reading, AST inspection and hashing were
used. No application/scientific imports, tests, API requests, native programs,
dependency installation, model calls, prompt construction or scientific runs
were performed. No fixed inventory rows or production files were edited.
The nine inventory rows remain pending in all six existing completion columns.
Historical classification of the restriction helpers as scientific algorithms
does not override the current goal's explicit supporting-operation treatment.
None needs a new annotation-confidence sheet or calculator.

Paths in this report are relative to the repository root. `BM` abbreviates
`reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/`;
`GA` abbreviates `reference/episode_tools/src/gentner_ave/`.
Exact file/function hashes and inspected ranges are in `SOURCE_MANIFEST.json`.

## Existing shared authorities and actual limits

| Existing path | Exact retained output and receiving consumer | Reuse boundary and missing seam |
| --- | --- | --- |
| `acquisition.PublicClients.ncbi_search(database, term, *, size=10, offset=0)` | ESearch JSON bytes in `SourceSnapshot(service,url,request,retrieved_at,content,media_type,transport)`; `ToolRegistry._acquisition_request('public.ncbi.search',...)` selects the client; `_import` publishes `source_ref`, native `provider_result`, `raw_artifact_ref` | Already handles one explicit page. Current database allowlist includes protein, nuccore, assembly, taxonomy, biosample, bioproject and pubmed; **Gene, GEO/gds and SRA are absent**. New molecular aliases must use the R6 molecular allowlist, excluding literature. No autonomous search/fetch chain or first-hit selection. |
| `PublicClients.ncbi_sequence(accession, *, database='nuccore', start=None, end=None)` | GenBank/GenPept response bytes; nucleotide interval translates supplied zero-based half-open `[start,end)` to `seq_start=start+1,seq_stop=end`; `ToolRegistry._import('public.ncbi.sequence',...)` calls `parse_genbank` and publishes external `reference` records | Reuse the exact acquisition and parser. Imported references retain sequence, accession, molecule, length and source; original feature context stays in the retained source, not a complete typed CDS result. Parent/source interval joins and CDS selections still need a supporting projection. |
| `acquisition.parse_genbank(content)` | List of record dictionaries: accession/version, sequence or null, source record index, length, topology, annotations, features and unlocated features; each feature retains source feature index, ordered segments, strand, fuzzy boundary classes/text, partial flags, remote refs, location operator/text and qualifiers | Reuse this format reader. It deliberately does not infer that fetched-record coordinates are whole-accession coordinates. A CDS selector must preserve this distinction and must not assume every feature starts ATG or ends a complete stop. |
| `sequence_views.view_sequence(sequence, *, molecule, segments=None, orientation='as_is')` and `ToolRegistry._derive('sequence.view',...)` | Native extraction body contains exact sequence, ordered input segments, input/output lengths, orientation and coordinate system. `_derive` uses `sequence_extraction_grader.grade_extraction`, publishes mapped feature/product/observation records and retains grading in the source | Existing extraction sheet/calculator is the sole authority for any extraction-consistency components requested downstream. A support adapter must consume these results, not copy their scoring. Mixed-strand/remote or ambiguous compound CDS locations are not automatically representable by one global orientation. |
| `materials.register_material`, `artifact_file`, `artifact_path`, `source_window`, `read_material`, `member_page`, `annotation_page`, `read_member`, `read_header` | Registered source/material custody; exact byte windows with offsets, total bytes and continuation; member/feature paging keeps source/parser/native ordinal associations | Reuse supplied-source inspection. These are not unrestricted path-discovery tools. Default windows are bounded but caller `limit` has no global ceiling; wrapper limits must be explicit. `artifact_file` is streaming but has no total-byte/scratch cap. |
| `native_file_capture.capture_native_file` / `capture_declared_native_files` / `retained_native_file` | `NativeFileIdentity={artifact_ref,sha256,size_bytes,format}`; per-declaration verified/declared_absent/digest_mismatch/unavailable; regular-file and no-symlink producer opens; retained full digest/size verification | Reuse byte custody for large selected files/GEO native artifacts. These functions do not implement acquisition budgets, scientific parsing, receipt ownership or replay. The caller must enforce selected-file and total-scratch limits before/during capture. |
| `api_services.publish_existing_acquisition(tools,name,arguments,snapshot,scope,operation_key,*,publisher=None)` | Existing operation receipt; delegates to supplied publisher or `ToolRegistry._import`; preserves retained sources on partial projection failure and rejects reused keys with different operands | Reuse publication of already acquired bytes, avoiding a second network request. This is not a child-owned provider binding by itself. |
| `api_services.APIServicePrimitive` / `build_service` | Existing prepare/invoke/decode/publish/result-selector interface for current services | Current builder supports uniprot, bvbrc_data, ncbi_blast, bvbrc_minhash, rfam_batch and bvbrc_appservice. It has no general NCBI data, GEO, ARCHS4, BioMart or Addgene primitive. Nine alias strings have no production references in `gene_annotation_episode/*.py`. New aliases need actual selected-resource binding and requested returns; generic API infrastructure alone is not completion. |

Existing upstream provider wrappers are evidence, not a second episode workflow:

* `GA/tools/online_queries.query_geo` calls `GA/tools/ncbi.query_ncbi_database`
  (`esearch` then `esummary`) and converts the dict to potentially truncated
  JSON text. The native helper returns success/query_info/total_results/result,
  but `esearch` has no offset parameter, and invalid/missing counts fall back to
  returned-ID count. It is not an acquired GEO expression series.
* `GA/tools/online_queries.query_ensembl` delegates the direct endpoint to
  `BM/database.query_ensembl`, which calls `_query_rest_api` and returns
  `{success,query_info,result}` or an in-band error. Requests have no explicit
  timeout/byte cap and results are not retained as episode artifacts. The
  optional LLM/prompt branch is excluded. BioMart table retrieval and REST
  homology are distinct native formats; shared orthology output does not make
  their raw formats interchangeable.
* `GA/agents/data_preparation.make_data_preparation_agent` exposes
  `inspect_data_file` and `download_geo_series_tool`; it joins a filename to the
  data-lake directory and JSON-serializes GEO's path dict. This upstream agent
  is not adopted as an episode owner, receiver, grader or runtime.

## Shared requirements for the proposed supporting outputs

Each family has its own closed typed output. References point to real retained
source/artifact records; literal sequence/identifier strings remain source
values, not unconstrained interpretation. Requested fields must be projected
from the validated result and checked against its source, with no model-written
restatement. Runtime return schemas remain parent-owned. The separate
`scientific_process_results` provenance contract is not a molecular result
schema and must not be used to smuggle complete supporting data into a return.

Every result distinguishes `complete`, `partial`, `unavailable` and `invalid`.
Use `complete` only for the stated selected request/population; complete empty
data is different from failed acquisition, omitted records or an unread page.
Specific failure rows contain an enumerated code, affected original input
ordinals/record references, retained valid rows and exact missing requirement.
Native error bodies stay retained. Do not reinterpret exceptions or null values
as measured zero, absence, identity mappings or successful completion.

Proposed common failure-row shape (a record shape, not an execution framework):
`{code:enum,phase:'input'|'acquisition'|'parse'|'association'|'projection',
input_ordinals:list[int],native_row_ordinals:list[int],source_refs:list[ref],
valid_result_refs:list[ref],required_inputs:list[enum]}`. Specific initial code
sets are `gene_candidate_ambiguous`, `gene_accession_mismatch`,
`cds_geometry_unavailable`, `cds_remote_reference_missing`,
`plasmid_record_not_selected`, `plasmid_sequence_not_present`,
`restriction_enzyme_unknown`, `restriction_cut_geometry_unknown`,
`archs4_native_schema_unavailable`, `archs4_units_unavailable`,
`orthology_identity_mismatch`, `orthology_response_partial`,
`enrichment_catalog_context_unavailable`, `geo_value_column_unavailable`,
`geo_platform_join_ambiguous`, `geo_duplicate_measurement`,
`file_format_unsupported`, `file_preview_limit_reached`, plus the shared
`provider_error`, `response_truncated`, `source_identity_mismatch`,
`selected_input_unavailable`, `native_parse_failed`, and
`resource_limit_exceeded`. Required-input values name exact missing operands,
for example `selected_gene_id`, `remote_accession_sequence`, `source_unit`,
`native_schema`, `selected_value_column` or `selected_platform_id`; no free-form
repair instructions cross the typed boundary. Nonfatal qualifications such as
unknown units can accompany valid rows without falsely failing all acquisition.

Acquisition limits are explicit request operands: allowed provider operation,
selected IDs/query/field set, maximum IDs/records, response bytes, compressed
and expanded bytes where applicable, page offset/token and requested sample/
feature subset. A parser consumes supplied bytes/files only. It never searches,
downloads, retries, changes resources or expands a query. A returned next-page
selector is information for the owning episode; it does not trigger a loop.
Limits must fit the caller resource allocation; local maxima remain 20 GiB RAM
and 4 GiB scratch, without adding an artificial wall-time budget. Aurora paths
and `EpiCalib` charging remain the existing project rules; no Aurora capability
was checked by this task.

## 1. get_gene_coding_sequence

**Source:** `BM/molecular_biology.py:252-327`, complete nested functions read.
Signature is `(gene_name: str, organism: str, email: str=None) -> list[dict[str,str]]`,
but actual return is `{explanation,sequences:[{refseq_id,sequence}]}`.
The wrapper performs ESearch Gene, `retmax=5`; takes `IdList[0]`; fetches Gene
XML; takes the first locus accession/version; fetches nucleotide
`gbwithparts`; selects CDS features whose first `gene` qualifier equals the
input string; uses `feature.location.extract(seq_record).seq`. Any exception
becomes one `RuntimeError`; no matching CDS returns an empty sequence list.

**Actual native inputs/outputs:** ESearch IDs/count/page, Entrezgene XML locus
records, complete GenBank sequence/features. The wrapper loses alternative
Gene/locus matches, original search count, taxon identity, selected feature
ordinal, transcript/protein IDs, feature location, codon start, translational
table and partialness. Its explanatory claim that CDS always begins ATG and
ends a stop is not validated. Sequence output is extracted nucleotides, not a
new annotation prediction or protein-function confidence.

**Reuse and missing handoff:** R6 owns bounded Gene search/XML retrieval and
typed Gene-to-versioned-accession links. Existing NCBI nucleotide acquisition
and `parse_genbank` own sequence/native-feature parsing; existing extraction
owns matching ordered local sequence geometry. The support adapter accepts a
supplied GenBank/source selection directly, so an investigation need not start
with a publicly searchable name. If the legacy name/organism request is used,
return all bounded candidates for explicit episode selection; do not select
the first hit, locus or CDS behind the episode's back.

**Proposed exact interfaces, owned by gene-sequence adapter:**

```text
read_coding_sequences(
  records: list[parse_genbank output], *,
  selection: CodingSequenceSelection,
  extracted: list[ExistingExtractionResult],
  source_ref: SourceRef,
  source_request: NcbiSequenceRequest | SuppliedSourceSelection,
  gene_links: list[GeneAccessionLink]
) -> CodingSequenceResult
```

`CodingSequenceSelection` has `record_ordinals:list[int]`,
`feature_ordinals_by_record:list[{record_ordinal:int,feature_ordinals:list[int]}]`
and optional exact `gene_id`, `taxon_id`, `gene_symbol` filters with a declared
match field. `GeneAccessionLink` is the R6 output
`{gene_id,taxon_id,accession_version,relation_kind,native_gene_record_ordinal,
native_locus_path,source_ref}`; missing fields are null, not guessed.
`ExistingExtractionResult` has the exact selected feature key, supplied
`sequence.view` body, optional existing sheet/scores and retained result ref.

Each `CodingSequenceResult.records[]` contains
`{record_ordinal,feature_ordinal,accession_version,gene_id,taxon_id,
gene_qualifiers,transcript_ids,protein_ids,location_operator,ordered_segments,
strand,partial_start,partial_end,codon_start,transl_table,
sequence_ref,length_nt,extraction_result_ref,extraction_status,limitations}`.
`ordered_segments` copies parser start/end/strand/boundary kinds/text/ref/ref_db;
coordinates remain `zero_based_half_open` in the named fetched record.
Whole-accession mapping additionally includes the exact acquisition interval;
remote segments require separately supplied references. Unsupported compound
geometry is a retained feature with unavailable extraction, not an empty CDS.

`length_nt` is the actual extracted nucleotide count; no rounding, biological
probability or mandatory ATG/stop filter. `codon_start`/`transl_table` are native
qualifiers with ambiguity retained. Partial CDS is valid partial source work.
Mismatched Gene/taxon/accession joins yield association failures; missing record
or inaccessible remote segment remains a specific incomplete item. Requested
sequences equal existing extraction outputs exactly. No new numeric calculator.
The referenced existing numerical identities are
`sequence_extraction_sheet_v1`, `sequence_extraction_scores_v1`,
`build_extraction_sheet`, `calculate_extraction_scores` and `grade_extraction`;
the adapter does not create an alternative sheet for fetched CDSs.

## 2. get_plasmid_sequence

**Source:** `BM/molecular_biology.py:330-419`, including both providers.
Signature `(identifier: str, is_addgene: bool=None) -> dict|None`. Numeric input
automatically selects Addgene unless overridden. Addgene GETs
`https://www.addgene.org/{id}/sequences/`, takes the first `textarea.copy-from`,
requires literal first line `> Addgene NGS Result`, joins remaining lines and
returns `{source:'Addgene',identifier,sequence,explanation}`. Non-200/missing
textarea returns None after printing. No byte bound, timeout, alphabet check,
sequence-record multiplicity or native capture is provided.

NCBI searches `nuccore` with `Cloning vector {name}`, `retmax=1`, relevance sort;
takes the first UID; fetches FASTA; requires a single SeqIO record. The return
calls the search UID an accession and drops the FASTA record accession/title.
Search/network failures can raise; parse failures return None. Neither branch
establishes complete plasmid sequence, circular topology or identity merely
from a successful response.

**Reuse:** The NCBI branch aliases R6 Nucleotide selection/acquisition, using
the existing GenBank path where topology/features are requested. Preserve the
requested UID and returned accession/version separately. Addgene is a bounded
mode required by this wrapper; it has no existing production provider found in
this pass. It needs one explicitly selected read-only acquisition mode plus
retained HTML/selected sequence artifact, not a second NCBI provider or an
autonomous fallback. Numeric identifiers cannot silently choose a provider in
the new typed request.

```text
read_plasmid_sequences(
  native: bytes | list[parse_genbank output], *,
  request: PlasmidSequenceRequest, source_ref: SourceRef,
  format: 'genbank'|'fasta'|'addgene_sequence_html'
) -> PlasmidSequenceResult
```

Request explicitly names provider, exact selected record ID or supplied source,
desired native format and bounded selection. Rows are
`{requested_identifier,provider,native_record_ordinal,returned_accession,
sequence_record_id,sequence_source_label,sequence_ref,length_nt,
topology:'linear'|'circular'|'unknown',sequence_completeness:
'source_complete'|'source_partial'|'unknown',source_ref,native_locator}`.
`source_complete` requires an actual provider assertion with a locator; the
word "plasmid" or Addgene's page title is insufficient. Multiple Addgene
depositor/NGS records remain separate; the parser must not pick the first.
No sequence found after a valid bounded page differs from denied access,
unexpected HTML, invalid sequence or a truncated response. Preserve case/
normalization facts and ambiguous bases. Restriction and extraction consumers
use the exact selected sequence ref, length and explicit topology.

## 3–4. find_restriction_sites and find_restriction_enzymes

**Sources:** `BM/molecular_biology.py:725-788` and `:791-819`.
`find_restriction_sites(dna_sequence,enzymes,is_circular=True)` calls
`RestrictionBatch(enzymes).search(Seq(sequence.upper()),linear=not is_circular)`.
It emits all queried enzymes, including empty-site rows. Its displayed
`recognition_sequence` is actually `enzyme.elucidate()` (a cut diagram), not
plain `enzyme.site`. It includes `fst5,fst3,ovhg` only for enzymes with hits.
`find_restriction_enzymes(sequence,is_circular=False)` calls the same native
search over `Restriction.CommOnly`, returns only nonempty cut lists, and drops
the searched-enzyme inventory, sequence length and topology.

**Single authority:** Both aliases use one restriction mapping producer and
typed validator. `CommOnly` means the native commercial-enzyme batch, not all
known enzymes or an unspecified biological "common" set. Retain its exact
resolved member names, Biopython version and restriction dictionary identity.
No new scoring implementation is warranted.

**Verified source semantics, not execution results:**
`Bio/Restriction/Restriction.py` `FormattedSeq.__init__` prepends a space;
its `finditer` therefore uses one-based recognition starts. Circular matching
extends by `site_size-1` leading bases. `AbstractCut.search` returns the first
base after cleavage (one-based), not the recognition start. `OneCut._modify`
uses `recognition_start+fst5`; reverse uses `recognition_start-fst3`.
`TwoCuts` also uses `scd5/scd3`. `_drop` removes cuts outside linear sequence
on either strand and wraps circular cut positions. `NonPalindromic._search`
joins forward and reverse hits; the upstream wrapper drops orientation.
`elucidate` may contain `^`, `_`, `N`, unknown markers or a "cut twice not
implemented" message. It must not be parsed as the recognition motif.
The upstream explanation's "0-based recognition starts" and "negative = 3'
overhang" statements conflict with native semantics.

```text
run_restriction_mapping(
  sequence: str, *, sequence_binding: SelectedSequenceBinding,
  enzyme_selection: ExplicitEnzymeNames | CommercialBatchSnapshot,
  topology: 'linear'|'circular'
) -> RestrictionNativeResult

read_restriction_mapping(
  native: RestrictionNativeResult, *,
  selected_sequence: SelectedSequenceBinding,
  enzyme_catalog: RestrictionCatalogSnapshot
) -> RestrictionSiteResult
```

Both are proposed future interfaces; the first is a selected native operation,
the second deterministic validation. The producer must retain recognition
events and cut events before discarding strand information. It should reuse
the native pattern/search semantics, then cross-check events against native
`RestrictionBatch.search` lists; no independent matching/scoring algorithm.
Parsing the existing cut-only dict cannot uniquely recover recognition sites,
orientation, multiple cuts per site or circular origin crossings.

Explicit shapes:

```text
SelectedSequenceBinding = {
  sequence_ref, subject_ref|reference_ref, source_ref,
  length_nt:int, coordinate_system:'zero_based_half_open',
  origin_mapping_ref:ref|null, topology:'linear'|'circular'
}
RestrictionCatalogSnapshot = {
  biopython_version, dictionary_sha256, selected_enzyme_names:[str],
  enzymes:[{name,rebase_id:int|null,rebase_uri:str|null,
    recognition_iupac:str,cut_diagram:str,size_nt:int,
    fst5:int|null,fst3:int|null,scd5:int|null,scd3:int|null,
    native_ovhg:int|null,overhang_kind:'5_prime'|'3_prime'|'blunt'|'unknown'}]
}
RecognitionEvent = {
  event_ordinal:int,enzyme_name:str,match_orientation:'+'|'-'|'palindromic'|'unknown',
  segments:[{start:int,end:int}],crosses_origin:bool,
  native_match_start_1based:int|null,cut_event_ordinals:[int]
}
CutEvent = {
  cut_event_ordinal:int,enzyme_name:str,recognition_event_ordinal:int|null,
  pair_index:0|1, native_watson_after_cut_1based:int,
  watson_boundary_0based:int,crick_boundary_0based:int|null,
  native_unwrapped_watson:int|null,native_unwrapped_crick:int|null,
  crosses_origin:bool,geometry_status:'known'|'partly_known'|'unknown'
}
RestrictionSiteResult = {
  sequence_binding,catalog_ref,queried_enzyme_count:int,
  enzymes:[{name,recognition_events:[...],cut_events:[...],
    native_cut_positions_1based:[int],search_status:'complete'|'partial'|'invalid'}],
  status,failures
}
```

Coordinates are on the supplied forward sequence; recognition segments are
ordered zero-based half-open intervals, split at a circular origin. Cleavage
coordinates are boundaries between bases, not half-open feature intervals.
For a native one-based Watson position `p`, boundary is `p-1`; the native
Crick position is `p-ovhg` when the cut geometry is defined. Circular canonical
boundaries use modulo length, while unwrapped native coordinates and origin
crossing remain available. Reverse recognition orientation does not change
the reference coordinate frame. Do not infer complete event associations from
duplicate numeric cuts. Zero sites is an observed result only for an enzyme
actually searched over the declared input; omitted enzymes are not negatives.

Source-derived future example: EcoRI catalog has site `GAATTC`, `fst5=1`,
`fst3=-1`, `ovhg=-4`, REBASE 993. For `AAAAGAATTCTTTT`, recognition is `[4,10)`,
native cut list is expected `[6]`, Watson boundary 5 and Crick boundary 9,
with a 4-base 5' overhang. This is an expected source calculation, **not a
native run**. For circular `AATTCAAAAG`, EcoRI recognition wraps `[9,10),[0,5)`;
expected canonical native cut is 1, boundary 0; linear context has no complete
recognition event. Ambiguity, no-cut and twice-cut enzymes need explicit
source-defined qualifications instead of invented cleavage positions.

## 5. get_rna_seq_archs4

**Source:** `BM/genomics.py:974-1014`. Signature `(gene_name:str,K:int=10)->str`.
Calls `gget.archs4(gene_name,which='tissue')`, expects a DataFrame, uses `row.id`
and `row.median`, and formats rows while the DataFrame index is `<K`. It does
not sort, validate K/index, retain the full table or distinguish acquisition
failure from a text message. The docstring calls values maximum TPM while the
output calls them median TPM. Neither naming establishes actual measurement
units or normalization. Other returned columns are discarded.

No `gget` package source was present in either inspected Python 3.12
site-packages tree. Its endpoint, default species, native schema, units,
aggregation population and pagination cannot truthfully be established from
this caller. No ARCHS4 response was acquired. R6 ARCHS4 owns the actual bounded
request/response parser; the alias must consume that authority rather than
implement another provider around the prose string.

```text
read_archs4_expression(
  native: bytes, *, format: str, request: Archs4Selection,
  source_ref: SourceRef, field_map: VerifiedArchs4FieldMap
) -> Archs4ExpressionResult
project_archs4_tissues(result: Archs4ExpressionResult, *,
  row_offset:int, row_limit:int, order:DeclaredOrder) -> Archs4TissuePage
```

The `VerifiedArchs4FieldMap` is a specific missing R6 output, not permission to
guess: exact native paths for gene/species, tissue IDs/labels, each measurement,
statistic, units/normalization, source population and pagination. It must be
pinned to retained native bytes and provider release/schema. Requested K is
presentation count, not proof of complete acquisition. Preserve every supplied
native measurement, including nonmedian fields, with its meaning.

Typed rows:
`{native_row_ordinal,gene:{requested_id,returned_id,namespace,taxon_id},
tissue:{id,label,ontology_id},statistic,measurement:{value:number|null,
native_field,unit:string|null,normalization:string|null,
population_ref:ref|null,sample_count:int|null,uncertainty:typed|null},
condition_refs:[],sample_refs:[],aggregation_level:'tissue'|'sample',source_ref}`.
Unknown sample identities, conditions, replication or units remain null/empty
with an explicit `not_provided` reason; aggregated tissue medians do not
manufacture sample-level observations. Numeric values are native quantities,
never gene-function probabilities. Pagination records native total/token when
provided; otherwise total/exhaustion are unknown. A display page can be partial
while the retained provider response is complete. Same gene/taxon/source must
join every row; do not infer species from a gene symbol.

## 6. interspecies_gene_conversion

**Source:** `BM/genomics.py:108-281`. Inputs are ordered ENSEMBL gene strings
and source/target names. Supported mappings are human, mouse, rat, zebrafish,
fly/drosophila, worm, yeast, chicken, pig, cow, dog, macaque to hard-coded
BioMart dataset/homolog-attribute names. Native call is
`Dataset(name=source_dataset,host='http://www.ensembl.org').query(
attributes=['ensembl_gene_id',target_homolog_attribute],
filters={'link_ensembl_gene_id':gene_list})`.
Empty/failed filtered query causes an unfiltered whole-dataset query.
`dict(zip(source,target))` then overwrites multiple targets per source.
Missing mappings become NaN. A fixed current-directory CSV is written and only
a step string is returned; on repeated failure an all-NaN CSV is still written.
Same literal species string returns an empty string. It retrieves no orthology
type/confidence despite claiming one-to-one mappings. Its fallback also indexes
`ensembl_gene_id` despite relying elsewhere on positional DataFrame columns.

**Reuse:** R6 Ensembl/BioMart supplies bounded selected homology records, exact
release/dataset/attribute identity and retained native bytes. `query_ensembl`
REST wrappers are existing provider-source evidence but not a faithful
replacement format or a proved production binding. No `pybiomart` package
source was present in the inspected environments. Never repeat the unfiltered
fallback or collapse mappings to a dict.

```text
read_orthology_mappings(
  native_rows: list[NativeBioMartHomologyRow|NativeEnsemblHomologyRow], *,
  request: OrthologySelection, source_ref: SourceRef,
  provider_context: EnsemblDatasetIdentity
) -> OrthologyMappingResult
```

`OrthologySelection` is `{input_genes:[{input_ordinal,gene_id,namespace,
version|null}],source_taxon_id,target_taxon_id,source_species_name,
target_species_name,release|null,selected_fields,page}`.
`EnsemblDatasetIdentity` is `{host,dataset,release|null,assembly|null,
source_taxon_id,target_taxon_id,requested_attributes,filter,source_ref}`.
Source/target taxon identities must be supplied or provider-resolved, not
inferred from label equivalence.

Result retains one input row per original ordinal, including repeated genes,
and zero or more relation rows per input:
`{input_ordinal,source_gene_id,target_gene_id,source_taxon_id,target_taxon_id,
relationship_type:'ortholog_one2one'|'ortholog_one2many'|'ortholog_many2many'|
'homolog_unspecified'|'same_identifier'|'other_native',native_type:string|null,
native_relation_ordinal,identity_percent_source:number|null,
identity_percent_target:number|null,native_confidence:{value,type}|null,
source_ref,release,relation_status}`.
The confidence field, if actually present, retains the provider's native
metric/ordinal type; it is not function correctness and not inferred from
mapping multiplicity. Identity percentages require provider definition and
denominator, otherwise remain raw qualified fields. Empty target is a retained
unmapped native row, not proof no ortholog exists. `mapping_status` is
`mapped|no_mapping_in_complete_selected_response|not_returned_in_partial_response|
provider_failed|same_species_not_cross_species`.
Preserve one-to-many, many-to-many, duplicate native relations and uncertain
orthology. Same species can return explicitly labeled same-identifier rows
without claiming orthology. Requested output shape must permit multiple target
rows per input instead of requiring equal source/target list lengths.

## 7. get_gene_set_enrichment_analysis_supported_database_list

**Source:** `BM/genomics.py:1017-1018`; exact body is
`return gseapy.get_library_name()`. No arguments, retaining logic, bounds,
organism/release metadata or error handling exist. The declared return is
`list`; the delegated `gseapy` source is absent in both inspected environments.
Provider endpoint, defaults and full native response have not been inspected
or acquired; do not invent them from the wrapper name.

This is library catalog acquisition for the selected enrichment service.
The existing/future R3 enrichment provider must own the catalog and exact
library identities, using the same identities its analysis request consumes.
It has no enrichment score, p-value or annotation confidence of its own.

```text
read_enrichment_library_catalog(
  native: bytes|list[str], *, source_ref: SourceRef,
  request: EnrichmentCatalogRequest,
  provider_context: EnrichmentProviderIdentity
) -> EnrichmentLibraryCatalog
```

Request contains selected provider, organism/taxon if explicitly known, native
format and page/byte limit. Catalog contains provider/release/native source,
organism context, query/page/completeness and
`libraries:[{native_ordinal,name,library_identifier,version_or_year:null|string,
description:null|string,provider_ref,organism_ref:null|ref}]`.
Preserve actual names and ordering; do not infer a release from name text.
If only a name list exists, other fields remain unavailable. Names are validated
source strings; a future requested form can constrain values to this retained
catalog. Declared duplicates are preserved or explicitly linked, never silently
counted as independent libraries. Empty complete catalog is distinct from
unavailable dependency, provider error or a truncated page. Gene-set
enrichment selects an exact catalog identity; listing libraries does not run
enrichment or validate the scientific suitability of a chosen library.

## 8. download_geo_series

**Source:** `GA/tools/data_lake.py:102-141`; `(gse_id,workspace)->dict` imports
GEOparse before its try block, calls `get_GEO(gse_id,destdir=workspace,silent=True)`,
then `gse.pivot_samples('VALUE')` and `gse.phenotype_data`. Writes
`prepared_{gse}_expression.csv` and `prepared_{gse}_metadata.csv`; returns their
paths, shape, first 20 metadata column names, title and platform IDs.
Acquisition/pivot errors return `{'error':...}`; import, phenotype/write errors
can escape. A failed pivot loses the successful acquisition in the returned
shape. No selection, file budget, source receipt, multi-platform key or units
contract exists. Shape counts are operational metadata, not confidence.

**Native path read:** `GEOparse.get_GEO` defaults `how='full'`; GSE uses
`ftp://ftp.ncbi.nlm.nih.gov/geo/series/{range}/{GSE}/soft/{GSE}_family.soft.gz`.
Existing local file is reused by name without content identity checking.
`get_GEO_file -> utils.download_from_url -> Downloader.download` is the
transfer path; the complete downloader source was read but not executed.
It uses a default-location `NamedTemporaryFile` name, has no response-byte cap
or explicit HTTP/FTP timeout, and copies the downloaded temporary file to the
destination. Its FTP exception handler can suppress a failure when no expected
size was obtained. Those transport behaviors are not adopted as the bounded
R6 provider. A new selected transfer must use caller-owned project temporary
storage, explicit resource bounds and faithful failure receipts. `parse_GSE` parses
SERIES/SAMPLE/PLATFORM/DATABASE blocks, with GSM/GPL maps keyed by accessions.
`parse_GSM` retains metadata lists, column descriptions and a table;
`parse_table_data` reads tab-separated table text. `pivot_samples` concatenates
GSM tables, appends GSM name and pivots index `ID_REF`, values `VALUE`, columns
sample name. It does not incorporate platform in the feature key.
`phenotype_data` converts repeated characteristics into dotted column names
and joins other lists with commas, so retain original metadata lists too.
`utils.smart_open` defaults to text `errors='ignore'`; missing/invalid encoded
bytes must not silently disappear in the retained native artifact.

**Reuse:** R6 GEO owns one bounded series acquisition and its receipt. The
native compressed SOFT artifact feeds a saved-data reader; the alias does not
reacquire the series or use `query_geo` summaries as expression data. Existing
native-file custody supports retained artifacts. R6 and this alias must share
the same `GeoSeriesBundle` output. The `.csv` paths alone are insufficient.

```text
read_geo_series_bundle(
  native_file: NativeFileIdentity, *, request: GeoSeriesSelection,
  parsed_series: ParsedGeoSeries, source_ref: SourceRef
) -> GeoSeriesBundle
project_geo_matrix(
  bundle: GeoSeriesBundle, *, selected_gsm_ids:list[str],
  selected_platform_id:str, value_column:str,
  selected_feature_keys:list[GeoFeatureKey]|None
) -> GeoExpressionMatrix
```

`ParsedGeoSeries` is an explicit R6/parser handoff containing exact GSE ID,
all retained native block ordinals, unflattened series metadata, GSM metadata
lists/table columns/descriptions/native row ordinals, GPL tables/metadata,
and parse errors/coverage. `GeoSeriesSelection` has selected GSE, supplied
artifact or selected provider acquisition, selected GSM/GPL/columns, maximum
compressed/expanded/table bytes, requested page and exact bounds.

`GeoSeriesBundle` retains
`{gse_id,native_files,series_metadata,samples:[{gsm_id,platform_ids,
taxon_ids,channels,metadata_lists,condition_fields,replicate_fields}],
platforms:[{gpl_id,feature_namespace,metadata,annotation_table_ref}],
measurements:[{gsm_id,gpl_id,id_ref,value_column,native_row_ordinal,
value:number|null,native_missing_marker:null|string,
unit:null|string,scale:null|string,normalization:null|string,
condition_refs:[],replicate_ref:null|ref,source_ref}],
coverage:{requested,returned,missing,extra,complete},status,failures}`.
Raw nonnumeric values must be retained with parse qualification rather than
coerced to zero. Unknown units, biological/technical replicate identity,
normalization and correction methods stay unknown. `VALUE` can be counts,
normalized expression, intensity, log data or another source-defined quantity;
neither TPM nor log transformation is inferred.

Feature keys are `(gpl_id,id_ref)`; sample keys are GSM accessions. Matrix cells
join exact keys and preserve row/column order, native missingness and selected
value column. Same probe ID on two platforms is not a shared gene. A GPL
feature-to-gene map is separate native evidence and can be one-to-many.
Conflicting duplicate `(gsm,gpl,id_ref,column)` measurements require a retained
conflict or long-form output, never silent mean/first-row aggregation.

A file is not a paginated API response: a compressed-byte cap produces a
truncated acquisition, not a valid partial SOFT series unless complete blocks
can be identified and retained. Parsed sample/measurement displays page the
retained selection using stable keys. Original GSE sample counts, parsed table
counts and display-page counts stay distinct. Supplementary files/SRA links
are references; they are not downloaded automatically.

## 9. inspect_file

**Source:** `GA/tools/data_lake.py:28-99`; `(path:Path,head_rows=5)->str` dispatches
by suffix. Parquet reads all rows of the first ten columns before `.head`;
CSV/TSV/TXT uses `read_csv(nrows=head_rows)` but on failure reads the entire file
before slicing 2000 characters. H5AD uses backed mode but does not close its
file explicitly; JSON/Markdown/unknown text read the whole file before slicing.
`.pkl` invokes `pickle.load`, which is not a data-only inspection mechanism.
Returns prose only, with no selected-input authorization, provenance, exact
preview extent, resource cap, parse status or completeness contract.

**Reuse:** selected registered material/source/member readers above already
provide bounded exact data windows and native annotation/member pages.
The new alias is an adapter to those readers plus bounded table/container
schema inspection; no directory traversal, globs, data-lake enumeration,
arbitrary absolute-path resolution or executable deserialization. Given an
explicitly supplied file, registration occurs under the existing custody path;
the child receives its retained identity. Unknown formats can return bounded
byte/text windows and size; unsupported schema does not imply failed custody.

```text
inspect_supplied_file(
  selected: SelectedFile, *, request: FileInspectionRequest,
  reader: BoundedRetainedReader
) -> FileInspectionResult
```

`SelectedFile` contains `{material_ref,source_ref,native_file_identity,
declared_format,caller_selected:true}`. The reader is a narrow capability
`read(offset:int,limit:int)->bytes` for that one retained file, plus validated
format-specific metadata access; it is not a filesystem browser.
`FileInspectionRequest` contains `{format:'auto'|supported format,
representation:'metadata'|'table_preview'|'text_window'|'byte_window',
row_offset:int,row_limit:int,column_names:list[str]|null,
column_limit:int,byte_offset:int,byte_limit:int,max_expanded_bytes:int,
max_metadata_bytes:int}` with finite positive bounds where required.
No default allows unbounded row/column counts or recursion.

`FileInspectionResult` contains
`{selected_file_ref,format_detected,format_declaration_conflict,
shape:{rows:int|null,columns:int|null,rows_basis:'exact'|'preview'|'unknown'},
columns:[{name,native_type,ordinal}],preview:{representation,rows_or_text,
start,end,bytes_read,rows_read,columns_read},
pagination:{next_row_offset,next_byte_offset,complete_for_requested_window},
sample_metadata_ref:null|ref,feature_metadata_ref:null|ref,
status,failures,limitations}`.
Shape and byte counts are inspection metadata. A preview-derived row count is
not file total. CSV values stay literal until an explicit typed parser is
selected; H5AD `.obs`/`.var` identifiers and dimensions remain separate and no
matrix densification occurs. Parquet uses row-group/batch reads with a bounded
column selection. HDF5 metadata/variable-length cells/compressed data require
read limits, not merely a small displayed string. PKL is reported as an opaque
unsupported serialization unless a separately authorized safe conversion is
already supplied; this inspector never unpickles it.
All handles close; symlinks/nonregular files/path escapes are rejected at
selection/capture boundaries. A missing/changed artifact is a custody error;
malformed table can still supply an explicitly labeled bounded raw preview.

## Proposed independent future ownership

No coding worker is commissioned by this mapping. These are concrete proposed
file boundaries for the parent to use when assigning implementation. Shared
production registries get one integrator, avoiding concurrent edits.

| Owner | Proposed exclusively owned files | Exact dependency/output |
| --- | --- | --- |
| Sequence support | `gene_annotation_episode/gene_sequence_support.py`; `tests/test_gene_sequence_support.py` | CodingSequenceResult/PlasmidSequenceResult and validators above. Consumes existing parse_genbank/extraction and R6 GeneAccessionLink or supplied source. No transport implementation. |
| Restriction support | `gene_annotation_episode/restriction_site_support.py`, `restriction_site_worker.py`; `tests/test_restriction_site_support.py` | Both aliases share catalog, native event producer and validator. Independent of provider acquisition; needs explicit selected sequence, topology and native Biopython catalog snapshot. |
| Expression support | `gene_annotation_episode/expression_acquisition_support.py`; `tests/test_expression_acquisition_support.py` | ARCHS4 typed table and GeoSeriesBundle/matrix projections. Saved supplied SOFT parser work can proceed while R6 transport is missing. ARCHS4 verified field map is a specific missing input for authentic parser acceptance. |
| Orthology support | `gene_annotation_episode/orthology_support.py`; `tests/test_orthology_support.py` | One-to-many preserving native mapping readers. Consumes exact R6 BioMart table/Ensembl JSON schema, species/release context and selected original IDs. |
| Enrichment catalog support | `gene_annotation_episode/enrichment_library_support.py`; `tests/test_enrichment_library_support.py` | Catalog/result validator. Enrichment provider owner supplies authentic library-name payload/context; this module cannot independently guess organism/release defaults. |
| Supplied-file inspection | `gene_annotation_episode/supplied_file_inspection.py`; `tests/test_supplied_file_inspection.py` | Bounded source/member and format-aware preview adapter. Existing material/native-file custody is reused, not copied. |
| R6 provider owner | Existing `acquisition.py` and new selected provider adapters as explicitly assigned by parent; shared registry edits coordinated | SourceSnapshot/NativeFileIdentity plus GeneAccessionLink, VerifiedArchs4FieldMap/native payload, ParsedGeoSeries, EnsemblDatasetIdentity/native homology rows. NCBI nucleotide implementation remains the authority. Addgene mode is an explicit wrapper obligation, not an unnamed provider-family blocker. |
| One integration owner | Proposed `supporting_operation_bindings.py`, `supporting_operation_result_views.py`; sequential edits to `tools.py`, `api_services.py`, relevant resource/tool library binding files; focused integration tests | Exact alias-to-operation bindings, retained native result identity, closed requested typed forms, source/selection equality, partial-result returns and saved replay. Must inspect the current complete execution/admission paths before coding; none was changed or exercised here. |

These boundaries do not add episodes, scheduling, hidden retry/paging loops,
extra grading actions or continuation rules. The selected API/local/HPC child
owns execution choices. All nine outputs are supporting facts. Existing
scientific extraction scores can be referenced when they are actually used;
this work supplies no new confidence policy and does not touch W05.

The following names make missing provider seams concrete without declaring
them implemented. These are proposed ownership reservations for the existing
R6 provider owner; that owner must reconcile them with any subsequent R6 work
before coding. Each `invoke` is exactly one selected request under the existing
`APIServicePrimitive` interface, not a workflow or a newly independent provider
authority. Existing `PublicClients.ncbi_sequence` remains unchanged authority
for nucleotide acquisition.

| Proposed R6 file/mode | Exact missing pure handoff signature | Consumed by |
| --- | --- | --- |
| `api_ncbi_data.py`, Gene search/XML mode sharing current NCBI transport | `read_ncbi_gene_links(snapshot:SourceSnapshot, *, request:NcbiGeneSelection) -> list[GeneAccessionLink]`; candidate-page output also carries native count/offset/retmax/IDs and response completeness | `gene_sequence_support.read_coding_sequences` and the episode's explicit candidate selection |
| `api_addgene.py`, explicitly selected sequence-page mode | `read_addgene_sequence_records(snapshot:SourceSnapshot, *, plasmid_id:str) -> list[{native_record_ordinal,native_locator,sequence_source_label,sequence,source_claims}]` | `gene_sequence_support.read_plasmid_sequences`; actual parser may live there to avoid copying it |
| `api_archs4.py`, selected gene/tissue mode | `read_archs4_native(snapshot:SourceSnapshot, *, request:Archs4Selection) -> {native_payload_ref,field_map:VerifiedArchs4FieldMap,provider_context,page}` | `expression_acquisition_support.read_archs4_expression`; no second gget provider |
| `api_geo.py`, selected GSE native-file mode | `read_geo_native(native_file:NativeFileIdentity, *, request:GeoSeriesSelection) -> ParsedGeoSeries` | `expression_acquisition_support.read_geo_series_bundle`; one source parser must own SOFT parsing for R6 and the alias |
| `api_ensembl.py`, explicit BioMart/REST homology modes | `read_selected_homologies(snapshot:SourceSnapshot, *, request:OrthologySelection) -> {native_rows,provider_context:EnsemblDatasetIdentity,page}` | `orthology_support.read_orthology_mappings`; no unfiltered BioMart fallback or LLM endpoint construction |
| Selected enrichment provider adapter, proposed `api_enrichment_catalog.py` if no R3 owner already supplies this mode | `read_selected_library_payload(snapshot:SourceSnapshot, *, request:EnrichmentCatalogRequest) -> {native_names_or_rows,provider_context:EnrichmentProviderIdentity,page}` | `enrichment_library_support.read_enrichment_library_catalog`; same library identity used by the R3 enrichment request |

Each source/payload ref above must resolve to retained bytes plus the original
selected request, actual response status and completeness. API capability
registration and current result admission are the single integration owner's
edits. Missing provider access blocks its authentic acquisition verification;
it does not block pure supplied-data relation/geometry/inspection readers.

## Truthful completion and resource accounting

| Operation | Source inspected | Reuse established by source | Typed alias/child return complete | Native/live verification in this pass |
| --- | --- | --- | --- | --- |
| get_gene_coding_sequence | Yes | NCBI nucleotide + GenBank + extraction; missing Gene/feature selection projection | No | None |
| get_plasmid_sequence | Yes | NCBI sequence; Addgene mode absent in production binding | No | None |
| find_restriction_sites | Yes, native methods too | One Biopython restriction search authority | No | None |
| find_restriction_enzymes | Yes, native methods too | Same authority, explicit CommOnly snapshot | No | None |
| get_rna_seq_archs4 | Yes | R6 ARCHS4 alias boundary; delegated gget source absent locally | No | None |
| interspecies_gene_conversion | Yes | R6 Ensembl/BioMart boundary; delegated pybiomart source absent locally | No | None |
| enrichment database list | Yes | Existing delegated GSEAPY catalog call; gseapy source absent locally | No | None |
| download_geo_series | Yes, SOFT/parser/pivot methods too | R6 GEO, existing retained native-file custody | No | None |
| inspect_file | Yes | Existing bounded material/source/member readers | No | None |

Static presence in the two inspected Python 3.12 site-packages trees:
Biopython source exists in both; GEOparse/pandas/anndata/pyarrow source exists
only in the reference environment. gget/gseapy/pybiomart package/file source
was absent in both. This is not an import check or deployment diagnosis of all
resources. Credentials, provider access, actual response formats, local native
execution, HPC deployment and receiver integration remain unverified.
The separate verification-case file specifies future checks; no case there
was executed. Read-only mapping is not a completed operation.
