# R6 UniProt / query_uniprot: proposed next coding boundary

This is an additive boundary prerequisite, not implementation or R6 completion. Only this verification directory is written. No application code, tests, inventories, historical receipts or goals are changed. Source/AST, retained JSON and read-only SQLite examination used the host standard library. No application imports, API/HPC/auth calls, live tests or scientific grader were run.

Authority remains the original supplied attachment, read in full; its objective and entire operating-principles block were reread after each logical tool task. GOAL.md was not read. The fixed R6-P09 accounting and its Rfam-only CORRECTION_001 remain historical evidence. The parent's correction is explicit: there is no extra acquisition sheet. Reuse SourceSnapshot → ToolRegistry._import → api_service_acquisition_v1. Retrieval has no numerical scoring sheet or calculator.

## 1. Known actual ports and demonstrated gaps

| Current actual implementation | Preserved behavior | Exact gap addressed |
| --- | --- | --- |
| PublicClients.uniprot_record(accession); uniprot_search(query, *, size=10, cursor=None) | Existing installed client, exact HTTP entity bytes, request/headers/client digest; one GET per selected record/page | No new HTTP client needed |
| UniProtService and api.uniprot.record/search/collect | Parent-fixed typed request, API child owns selected operation, empty collect selector reuses original bytes | Literal query_uniprot absent; returned primary accession is only checked for nonempty text; no requested/returned accession relation |
| public.uniprot.record/search → ToolRegistry._import | Source artifact, protein reference, full sequence artifact, taxonomy/name/EC terms | Structured features/comments/evidence/audit omitted from publication result despite raw bytes retained |
| parse_uniprot(content) | Existing source identity/sequence/annotation extraction | Eager whole-list parsing loses all projected rows if a later row is malformed; no native ordinal, field-state/errors, secondary-accession correspondence; alternativeNames not included in this parser |
| uniprot_pagination(snapshot) | Actual Link cursor, total-results/release/date; known-host check | Invalid/unobserved next link collapses to None; no explicit requested page extent or typed child page return |
| APIServiceExecution.read_result/facts | Durable acquisition/source/ref/assignment validation and replay | UniProt publication result is not exposed (current special branch is Rfam); UniProt has no typed fact-family return |
| ExecutionEpisodes received_report_* / resolve_received_reference | Existing explicit receipt admission, forwarding and possession pattern | No UniProt source schemas, tuple validation, field admission or sequence-artifact namespace |
| communication.py / runtime.py | Deterministic recorded facts, closed forms, reference validation, original saved forms | Native recorded strings require a specifically registered exact schema; do not relax general free-text grammar |
| sequence.align → _sequence/_align_one | Existing reference sequence artifact reaches the common Biopython alignment sheet/calculator | Keep this actual scientific consumer; no new UniProt scientific score |
| blast_reference_metadata.read_uniprot_metadata | Existing pure extraction of EC/name/GO/evidence/taxon/native records | Only test callers found. It is available extraction code, not an established acquisition-to-BLAST metadata connection |

Five actual workflow names are established above: public.uniprot.record, public.uniprot.search, api.uniprot.record, api.uniprot.search, api.uniprot.collect. No actual function named normalize_query_uniprot, parse_uniprot_native, bind_uniprot_publication or uniprot_requested_facts exists in the inspected checkout. All such names below are PROPOSED.

## 2. Exact alias scope and immutable selected input

The pinned Biomni contract is query_uniprot(prompt=None, endpoint=None, max_results=5) -> dict. Its docstring advertises either natural language or a full/partial UniProt REST endpoint, with the direct example https://rest.uniprot.org/uniprotkb/P01308. It is not restricted to UniProtKB by its implementation: the direct branch forwards arbitrary HTTP URLs. Its prompt branch loads a schema and invokes _query_llm_for_api, with hidden reviewed-first and human defaults. max_results is never read after argument binding. The Gentner wrapper is query_uniprot(endpoint: str, max_results: int=5) -> str; it JSON-serializes that result and cuts it at 10,000 characters.

Do not import or execute either wrapper. Do not inherit natural-language dispatch, human/reviewed query defaults, arbitrary URL forwarding or 10,000-character truncation.

The first proposed alias covers exactly:
- UniProtKB single JSON entry: /uniprotkb/{accession}, optionally .json or format=json.
- UniProtKB one selected JSON search page: /uniprotkb/search with one nonblank query and optional size, cursor, format=json.
- Leading-slash, relative and exact https://rest.uniprot.org forms normalize to those same operations. Preserve the decoded query and opaque cursor exactly; no uppercase conversion, query rewriting, default organism, taxon inference or accession suffix stripping.
- Reject userinfo, fragment, non-HTTPS/other host/port, duplicate parameters, unknown parameters, unknown formats and unsupported paths before transport. Unknown parameters are not silently dropped.

The parent froze max_results as None/omitted rather than an implicit upstream 5. For search, an explicitly supplied integer 1..500 is the selected page size. An explicit URL size must be 1..500; if both are present they must agree. If neither is supplied, preserve the existing client/service search default of 10, explicitly recorded as the effective request. Reject rather than cap/truncate an out-of-range value. For record requests, reject a non-None max_results because it cannot describe record selection. None is treated identically to omission.

These are out of this first contract and must stay visible as unsupported/unverified: UniRef, UniParc, taxonomy/proteomes and other UniProt dataset endpoints; streaming, batch/id-mapping jobs, non-JSON formats, field-projected/sorted/filtered parameter variants beyond the listed query/size/cursor keys; sequence-isoform modes that need additional correspondence handling; natural-language prompt dispatch (excluded); arbitrary URLs. The installed UniProt client script can submit more paths, but that is not a bound typed capability. Completing this UniProtKB boundary cannot close all UniProt/alias modes merely by using the name query_uniprot.

The service request gains a closed third operation variant:
    {"operation":"query_uniprot","endpoint":"/uniprotkb/search?query=gene:ybhP&size=1","max_results":null}

Existing record/search variants remain. Preserve the original alias request in the assignment/receipt; derive a separate canonical record/search request for execution. The literal selected tool query_uniprot has empty action arguments, following the current API convention: endpoint and max_results belong to the original parent-owned service request, not a later mutable action argument. The launch catalog exposes query_uniprot only for the alias request. api.uniprot.collect remains the result operation. Its empty selector reuses the original snapshot; an explicit cursor/size selector acquires exactly that selected page of the original canonical query. Record selectors remain empty.

The alias is a commissioned API operation, not a direct scientific ToolRegistry capability. UniProtService.capabilities → APIServiceExecution.operation_contracts → ExecutionEpisodes.resource_tool_contracts supplies explicit resources=api and the actual launch/results route. workflow_execution_catalogs and scientific tool retrieval discover that declared port without activating it outside its selected resource child. Preserve evidence_axis, thought_pattern, child_tool_info and caller constraints.

## 3. Frozen pure parser / publication ports and exclusive file split

PROPOSED_CONTRACTS_001.json contains closed schemas (all object keys declared; all output keys required), exact signature text and eight optional requested fact families. This document supplies their relational semantics. The schema document is not an application import or an implemented capability.

### P: pure input/native parser owner, parallel with B

Owned files: new gene_annotation_episode/uniprot_native.py; only parse_uniprot and uniprot_pagination compatibility wrappers in acquisition.py; new focused pure-parser tests. Do not change PublicClients or API/return/credit code.

Proposed signatures:
    normalize_query_uniprot(endpoint: str, *, max_results: int | None = None) -> dict
    parse_uniprot_native(content: bytes, *, request: dict | None,
                         response_headers: dict | None) -> dict
    validate_uniprot_projection(parsed: dict) -> None

normalize_query_uniprot returns the existing canonical record/search request shape. The parser returns the exact ParsedPage schema, version uniprot_native_page_v1. request is the canonical effective request with actual selected cursor and resolved size; response_headers is the observed header mapping or None. Only the legacy parse_uniprot wrapper may pass request=None; it yields unverified correspondence, and cannot establish a bound API return. The pure module imports neither Store, PublicClients, requests nor an LLM. It does not fetch pages or create artifacts.

Parser output is independent of Store IDs. It contains original row ordinals/pointers, full valid sequence values, native field states, requested/primary/secondary relation, all feature/evidence/xref associations, page metadata and structured issues. A malformed row is represented by its exact issue ordinal/pointer and does not remove other rows. Compatibility wrappers may project the old keys from this single parser; they must not become a second parser policy.

### B: service and publication owner, parallel with P

Owned files: api_uniprot.py; only relevant catalog/direct acquisition/publication/error handling sections of tools.py; focused API/publication tests. A pure binding helper may live in tools.py as:
    bind_uniprot_publication(parsed: dict, *, source_ref: str,
                            native_artifact_ref: str,
                            references_by_ordinal: dict[int, dict]) -> dict

No change to the existing PublicClients HTTP acquisition. B consumes P's frozen shape. UniProtService normalizes the alias, validates the recorded native request against the effective request, preserves original alias input, and invokes only existing uniprot_record/uniprot_search. Known non-2xx responses remain failures. Missing transport evidence stays explicit/unknown; do not fabricate it. New selected response requests must include required accession or query/size and the actual cursor state; extra format=json from the installed client is expected. Do not accept a mismatched request merely because the conflicting key was absent.

decode uses the pure parser's identity/envelope result for a usable handoff; it must not declare an unmatched record usable. A well-formed search page containing a malformed row can still provide a native handoff with explicit issues. Collection publishes the valid records and marks partial projection through the existing projection_errors/partial mechanism. Native absent optional metadata is a successful observed absence, not a fetch failure. Invalid requested field content is partial, not fabricated empty data.

_import retains the original Source first, then creates reference/term/sequence records from valid rows, keyed by original ordinal. The helper binds each row to that exact reference and native source, attaches the source's existing native artifact reference, and emits uniprot_publication_v1 under result.uniprot_publication. It is an acquisition metadata descriptor, not a sheet. Public direct outcomes and service publication must agree on partial status and retained valid rows. Shared publish_existing_acquisition remains the sole service publication/idempotence path. No parallel publication store.

### R: typed receipt/return integration after P + B

Owned files: new uniprot_returns.py; api_service_execution.py; execution_episodes.py; only the UniProt exact-schema cases in communication.py; focused connected receipt/return tests. New source schemas belong in the pure uniprot_native.py contract block or a new uniprot_contracts.py owned by P, not duplicate copies in each consumer.

Proposed pure projection / validator ports:
    uniprot_requested_facts(publications: list[dict], *,
                            requested_sources: tuple[str, ...]) -> dict
    validate_uniprot_fact_rows(source: str, rows: list[dict], *,
                              resolve_publication) -> None

R must expose result.uniprot_publication through APIServiceExecution.read_result only after the existing acquired receipt, assignment, source, snapshot hash and outcome checks. Keep api_service_acquisition_v1 and api_service_acquired_result_v1; no second acquisition receipt family. New typed facts derive from the stored publication, not a new model call or live re-acquisition. Existing saved receipts lacking the publication extension remain legacy references-only; do not synthesize new facts into old closed forms or change old credit.

R registers exact per-family schemas in fact_sources, API facts, received_report_sources/facts, validate_received_report, received_form_references, resolve_received_reference and resolve. Validate source/ref/ordinal/pointer/accession/sequence as a tuple; mere same-store membership or matching taxon/name is insufficient. Add exact scoped namespaces uniprot_sequence and uniprot_native_artifact. Admit only references in requested facts actually delivered by the child's form, including their explicitly declared source/sequence operands. Forwarding preserves that original receipt and values; another source or acquisition with the same accession is not interchangeable.

communication.py's exact native-source schema handling and semantic traversal must recognize these schemas/$defs without opening generic strings or arbitrary dictionaries to model interpretation. Native names/IDs/modifiers are exact recorded values, validated against the retained publication, not model-written prose. runtime.form_references, _receive_form, facts and validate_report remain the existing generic consumers; verify their traversal/admission rather than creating a new runtime loop.

### M: later, separately reviewed presentation template

No prompt template is settled by this document. Exact affected consumers are ExecutionEpisodes.instructions/decision_context, APIServiceExecution.decision_context, providers._presentation and scientific_process_prompt._task/_steering/render_episode_steering. Currently the API context follows the JSON fallback; scientific parents use the common renderer. A separately reviewed template must repeat the detailed selected task, immutable query/accession/page and requested field meanings in TASK; STEERING selects actual page status, failures, useful received values and ordinary own action yield/uncertainty. No raw paragraph/JSON dump, host tracking hashes or invented evidence summary. Any bounded display window says what was included and exposes an explicit continuation/read operand; underlying data and returned typed facts remain complete.

## 4. Field meanings, native custody and semantic invariants

All pointers are RFC 6901 pointers into the exact retained native JSON; record lookup uses pointer "" for a single response or /results/{native ordinal} for search. Original array ordinals are never renumbered after filtering. Page header field pointers use the separate retained transport-header address space /headers/{lowercase-name}; this is declared by the Page container, not confused with native JSON. Unknown native fields and complete descriptions/comments/reference/citation text remain in the original artifact; a typed projection does not claim exhaustive native schema coverage.

Every TextField/IntegerField/TextArrayField has exactly state, value, pointer. state=present carries the exact native value; absent/null/invalid carry value=null and preserve their distinct meaning. Present empty strings/arrays stay empty when valid for that field. A required primary accession is nonblank; invalid identity suppresses that reference row only. Invalid native types remain accessible at their pointer and produce an Issue; they are not converted to zero, empty list or guessed text. Integer means JSON integer excluding boolean. Counts and lengths cannot be negative; taxon/version identifiers must be positive when present. No number is a probability or confidence estimate.

| Field/group | Native source and meaning | Unit / missingness / relationship |
| --- | --- | --- |
| requested_accession, primary_accession, secondary_accessions, accession_relation | Original record request; primaryAccession; secondaryAccessions; exact membership relation | Identifiers, not numbers. primary match wins; otherwise exact secondary membership. No case/suffix/name/taxon substitution. Search uses search_member with requested_accession=null |
| record_ordinal / record_pointer | Original native row position | Zero-based row ordinal, not result rank after filtering. Repeated accessions keep distinct ordinal/response identity |
| sequence.value / reported_length_aa / observed_length_aa | sequence.value; sequence.length; length of the complete valid native sequence | aa. Do not trim/uppercase/pad. Invalid alphabet/encoding retains raw data with invalid state; no sequence artifact or computed interval for it. Declared/observed disagreement stays conflict |
| sequence_ref | Existing reference's exact full sequence artifact | Validate its bytes equal the parsed sequence and that reference.source_ref/ordinal/accession match. Not the investigated target sequence |
| md5 / crc64 | Native sequence checksum strings | Native identifiers, not automatically recomputed truth. Empty/absent/invalid are separate; raw full sequence remains authority for stored artifact bytes |
| taxon_id, scientific_name, common_name, synonyms, lineage_names | organism.taxonomyId if present is NOT an accepted alias; actual current field is organism.taxonId; other exact organism keys | taxonId integer identifier. Lineage is the native ordered string array, no inferred ranks/taxids or organism-name joins. Native host/other organism data remains in the source |
| metadata ID/type/protein existence | uniProtkbId, entryType, proteinExistence | Native labels, not experimental confirmation. Date strings remain native, no invented timezone; audit versions remain identifiers |
| native_sections | proteinDescription, genes, comments, references, keywords, extraAttributes | Presence and native pointers; complete content retained, no prose generated in returns. References are citation metadata already in the molecular record, not literature acquisition/scoring |
| features ordinal/type/id | features array ordinal; type, featureId | Native feature identity tied to this source record. Description and other feature qualifiers remain complete at the feature pointer |
| feature start/end | location.start/end.value and .modifier | Native coordinates are 1-based inclusive aa. Keep modifier strings exactly. Only literal EXACT endpoints, positive integers, start<=end and an established compatible sequence permit [start-1,end) |
| feature native_sequence_id / sequence_binding | location.sequence when present, otherwise entry-local feature association | Do not map a named alternative/isoform onto the canonical sequence without explicit exact identity. Unresolved association gets no calculated interval |
| evidence rows | Every native evidences array, including those under names/EC, features, comments and cross references | evidenceCode/source/id plus original evidence and owning JSON pointers. Retain local list ordinal. No flattening into independent experiments; repeated citations or ECO codes are not independent support counts |
| cross references | uniProtKBCrossReferences[*].database/id/properties and evidence pointers | Original xref/property order and values; evidence.owner_pointer must equal the owning xref pointer when linked. No taxon-based or label-based join |
| native_record_count / publishable_record_count | Actual results list length (record=1), and valid identity rows published | count only. Invalid JSON/envelope native count is unknown, never 0. A valid empty search page is 0 |
| total_results | X-Total-Results if syntactically valid nonnegative integer | count for the original query, not this page or number of valid rows. Missing/null/invalid distinct |
| next_cursor / next_url / next_state | Actual Link rel=next, bounded to the original UniProtKB search/query | Opaque cursor. Retain URL and validate query/size constraints. Invalid or missing transport is not end-of-results. No automatic traversal |
| release / release_date | X-UniProt-Release / X-UniProt-Release-Date | Native strings. Cross-page differences are qualifications; no silent union into one release |
| whole_query_complete | True only when first page was explicitly selected (no original/selected cursor), observed headers establish no next page, total_results equals native_record_count, and no page-level integrity issue | False for known remaining/selected later-page subset; otherwise null. Never infer completeness from a short page |
| projection_state / issues | Deterministic parsing/publication status and exact pointer/code | complete/partial/invalid describes acquired data handling only, not scientific acceptance or annotation confidence |

A secondary accession is not globally unique: UniProt documents that an entry split can leave one old accession secondary to several new entries. Therefore relation=secondary means only that the returned entry explicitly lists the requested value. Preserve both values and this qualification; never claim unique canonical resolution or deduplicate separate primary entries by shared secondary accession. Primary source supplied by root: https://www.uniprot.org/help/accession_numbers .

Evidence text is retained as native data only. Selected typed evidence facts are ECO code, source, source ID, owner pointer and evidence pointer. Feature-description, comment, citation and protein-description paragraphs are not copied into typed evidence returns or paraphrased by a model. Requested native text may subsequently be read from the original source through the existing explicit source.read path. Full metadata custody is not permission to dump all metadata into a child return.

The eight fact families are pages, records, sequences, taxa, features, evidence, cross_references and failures. The parent requests exact source families via x-source; each has a fixed closed schema and includes all acquired rows for that selected page, with no maxItems/data truncation. Field absence remains in per-record groups even if the items array is empty. A field family omitted from the parent's form is not returned. Every non-page family includes the exact record anchor. Failure facts name the retained source plus structured Issue, never unrestricted findings or repair instructions.

## 5. Existing consumers and extension points

| Consumer | Required bounded action |
| --- | --- |
| acquisition.PublicClients / _skill / SourceSnapshot | Reuse unchanged; ensure exact HTTP body/headers and original request remain available |
| acquisition.parse_uniprot / uniprot_pagination | Thin compatibility projections from P; no separate native interpretation |
| api_uniprot.UniProtService all request/catalog/prepare/decode/publish paths | Add alias normalization and identity checks; preserve one selected operation/page and cache semantics |
| tools.ToolRegistry.catalog, _acquisition_request, _perform, _import, _execute_operation_async | Existing direct operations remain; shared parser/publication + valid partial preservation; literal alias stays commissioned |
| api_services.publish_existing_acquisition | Existing idempotent transaction/result partial hooks reused, not replaced |
| APIServiceExecution _execute_locked/_snapshot/_read_handoff/read_result/result_identity/facts/resolve | Persist publication with existing acquisition; expose validated typed metadata; saved replay reads original bytes, no new calls |
| APIServiceExecution credit_view/_completion + ExecutionEpisodes project_credit | No scoring-policy change. Counts remain existing caller-configured operational contributions; no new source/feature/evidence synthetic actions or scientific credit |
| tool_information.workflow_execution_catalogs/_documents/make_tool_info; resource_tool_information; scientific_tool_retrieval | Alias appears with meaningful supported input/scope instructions and explicit bound API route; no direct-operation inference by bare name |
| ExecutionEpisodes request/selector/prepare_assignment/_match_request | Preserve original parent request and selected cursor; alias normalization cannot permit request replacement |
| ExecutionEpisodes fact_sources/facts/received_report_sources/facts/validate_received_report/received_form_references/resolve_received_reference/resolve | Exact per-family admission, tuple custody, requested-only return, forwarding and replay |
| communication _compile_closed_schema/_validate_form/_validate_form_semantics/form_with_facts | Register exact finite native shapes and semantic reference traversal; deterministic recorded values |
| runtime form_references/_receive_form/report_sources/validate_report/facts | Verify generic consumers preserve original schemas, nested references and saved original forms; no parallel runtime |
| tools._sequence/_align_one and existing Biopython grader | Continue using actual reference sequence bytes and common scientific sheet; no acquisition-specific calculation |
| blast_reference_metadata.read_uniprot_metadata and its existing tests | Reuse for any later explicitly selected metadata analysis; do not claim it is currently connected or automatically create BLAST scientific facts |
| materials.source_window via source.read; state.query | Preserve complete native bytes/record access within actual received scope; windowing is explicit data reading, not loss of native data |
| providers._presentation and scientific_process_prompt | Separate template review described above |

Operational identity remains the existing normalized publication-record identity and source/native content custody. Alias input names must not create a second observation for the same selected action/replay. Do not rewrite original result_identity hashes or historic acquired-record credit. Verify alias versus canonical acquisition behavior before changing any identity policy; new metadata is not a reason to reprice old histories. One own selected operation supplies one local observation. Parsing, report generation and admission add none. Exact practical completion retains its existing terminal zero-future-credit semantics; a partial result remains repairable, not scientifically complete.

## 6. Evidence level and next handoff

The retained authentic response is 8,650 bytes, accession P0AAW1, secondary P75772, taxon 83333, sequence length 253 aa, one Chain feature [1,253] native inclusive, three citation records and 42 cross references. Xref ordinal 31 is GO:0005886 with ECO:0007005 / PubMed / 32127419; its evidence owner must remain /uniProtKBCrossReferences/31. This is native provenance, not a new finding or confidence score.

Historical report.json records a 2026-10-23 live record retrieval and cached original-response collection. The retained child forms returned completed flags, source/reference IDs and yield values, not the proposed metadata families. No authentic search-page body was newly acquired here. Controlled test source covers selected pages, recovery and replay, but this task ran none of those tests.

P and B may be assigned concurrently against the frozen JSON handoff. R follows their exact joined output. M remains a separate reviewed template, not a prerequisite for pure parsing. The first increment's bounded verification cases are in VERIFICATION_PLAN_001.md. Broader endpoint modes and any required fresh live verification remain unfinished. No unrelated provider, scientific scoring, literature or HPC task is introduced.
