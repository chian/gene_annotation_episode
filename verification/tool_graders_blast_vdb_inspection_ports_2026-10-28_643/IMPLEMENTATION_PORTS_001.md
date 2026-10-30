# blast_vdb_cmd: supporting inspection and extraction ports

Planning record 643/001, 2026-10-28. This document proposes implementation boundaries; it does not implement, install, bind, test or commission an operation. Its authority is the user's supplied attachment and subsequent explicit directions, not this repository record. It does not amend that goal.

The required operation is blast_vdb_cmd. blast_formatter and blast_formatter_vdb are excluded by the user's later direction. VDB inspection/extraction is a supporting operation: reuse the shared BLAST utility extraction/inspection records, sequence checks and requested-return machinery. Do not create a scientific confidence score, search hit, artificial query, public-data submission, grading episode or new controller observation.

## 1. Evidence and current boundary

Primary evidence was retained before this task:

- 620/official_source/blast_vdb_cmd.cpp, NCBI source commit 864d3b0d51f61ff2d39c694869d41786f62e9ba8, SHA256 bdcf179e87a91a69096a648860b87b38a4fe16340d82d6117ee851e9dbec3d2d.
- 620/retained_native_help/blast_vdb_cmd.help.stdout and blast_vdb_cmd.version.stdout. Version output is 2.17.0+, package built July 1, 2025. No assertion is made that this retained source commit exactly matches that binary.
- 620/IMPLEMENTATION_BOUNDARIES_001.md and HANDOFF_001.md.
- 312/ROOT_REVIEW_001.md: historical VDB parser/calculator checks used synthetic native-format examples. Authentic paired BLAST geometry is not authentic VDB helper extraction.
- Historical WORK_STATUS.json row native/blast_vdb_cmd remains pending, with resources not established by that inventory and no row evidence. It is an inventory fact, not proof that reusable VDB parsing is absent.

Paths abbreviated 620 and 312 mean the corresponding tool_graders_blast_utility_boundaries_2026-10-28_620 and tool_graders_blast_vdb_2026-10-26_312 verification directories.

Current utility implementation has five classic modes. DatabaseBinding already admits kind vdb, but the shared reader rejects it, SequenceExtraction validates only blastdbcmd, and the utility native contract imports the standard database operand that excludes VDB. Its compiler adds -dbtype to every non-builder. The driver inventories classic prefix families. Result parsing, format selection, tool information and some projections dispatch on mode alone. Merely adding blast_vdb_cmd to a catalog would leave all of these paths wrong.

The current additional-BLAST operand in native_blast_database_contracts.py already represents prepared VDB sources, requires complete declared file inventory and offline_configuration, and has pure validation. The additional-BLAST driver's recursive VDB inventory is useful execution mechanics. Reuse these ports without creating a database-search job. A retained offline_configuration document alone does not prove its settings were applied or that native resolution could not use the network.

The exact existing parser is blast_vdb_inputs.parse_blast_vdb_member_sequences(contents, *, source_ref, source_version, extraction_context). It accepts only four columns, %i TAB %a TAB %l TAB %s, and specific entries. It does not accept entry=all, generic custom outfmt, FASTA, info or paths output. It requires selected input, snapshot, entry identities, return code, producer-complete state, filter/reference context and provenance. It preserves native text and per-row native_record.row_ordinal; its emitted record_key.record_ordinal is compacted after malformed rows and must not become the shared native row ordinal.

It is currently consumed by native_blast_database_metadata._vdb_units through declared documents/parsed_sources, explicit dataset/member bindings and then the existing VDB search sheet. That scientific consumer requires a real search context. Supporting extraction must not fabricate one. Its output can later be explicitly selected and bound as a metadata document by an episode that already owns the actual search.

## 2. Exact native modes and argv

The compiler must use an argv list, not a shell command. Let EXE be the selected absolute executable with pinned digest/version; DB be the explicitly selected ordered VDB source list; TABLE be the literal string "%i\t%a\t%l\t%s" with real tab characters, not backslash-t characters.

| Typed operation | Required native argv after EXE | Supporting return |
| --- | --- | --- |
| extract_sequences, entries, inline | -db DB -entry comma_joined_selected_values -outfmt TABLE -line_length N | shared SequenceExtraction |
| extract_sequences, entries, batch | -db DB -entry_batch STAGED_ENTRY_FILE -outfmt TABLE -line_length N | same extraction |
| extract_sequences, all_native_sequences | -db DB -entry all -outfmt TABLE -line_length N | same extraction, explicit regular native view (SRA/CSRA reads or WGS sequences) |
| extract_sequences, all_references | -db DB -entry all -ref -outfmt TABLE -line_length N | same extraction, explicit CSRA reference-view scope |
| info | -db DB -info -line_length N | shared DatabaseInspection with native VDB statistics |
| paths | -db DB -paths | shared DatabaseInspection with native top-level path report |
| paths_all | -db DB -paths_all | shared DatabaseInspection with native recursive flat path report |

For every row, -db DB may instead be exactly -dbs_file STAGED_DATABASE_LIST when that input form was selected. Never supply both. Default N is explicitly recorded as 80 and must be a positive integer. An explicit include_filtered_reads=true adds -include_filtered_reads only to entries/all_native_sequences. No -ref for selected entries: retained source dispatches each requested ID to read/WGS or CSRA reference utility by native ID type, while m_isRef controls the all branch. Reject an ineffective or conflicting selected-entry ref flag rather than claiming that it controlled the view.

The first authentic increment can exercise specific entries plus info/paths on one tiny supplied offline VDB source. all_native_sequences, all_references, batch/database-list and aliases retain their exact planned contracts and separately named fixture dependencies below; their verification is not implied by that first increment.

Compile no -dbtype, -range, -strand, -get_dups, -target_only or -exact_length. Those classic blastdbcmd options do not belong to this helper. Do not expose ghost scan_uncompressed/scan_compressed names that appear only in exclusion declarations. Require one typed mode; native Run can return zero after no effective operation. Reject simultaneous paths/paths_all even though source priority would choose paths. Do not infer another mode or silently choose a source, retry, sample, dump-all or cancel.

Use producer-managed stdout/stderr and omit -out and -logfile so the closed producer owns all output. The native default -out "-" writes stdout. Preserve exact native argv/environment and selected input occurrences.

Native supported output language also includes %f (default FASTA), %s, %a, %o, %i, %t, %l and %% escaping. The annotation binding deliberately uses the fixed four-column format for typed extraction. FASTA and arbitrary custom substitutions are not accepted as that format. A future explicitly selected FASTA reader can reuse domain.parse_sequences, but must not claim absent accession, length, OID, title or VDB membership fields. This plan does not require inventing another numerical policy for any format.

The source of each substitution is important:

| Native output | Source meaning and omission |
| --- | --- |
| %i | Bioseq first Seq-id, AsFastaString; retain exactly |
| %a | Same first Seq-id, GetSeqIdString(true); retain exactly; not a run/source proof |
| %l | Returned Bioseq instance length if set, otherwise N/A |
| %s | Returned Iupacna symbols if available, otherwise N/A |
| %o | Utility/source-view ordinal from native iterator or GetOIDFromVDBSeqId, cast to int; not a classic BLAST OID, spot or read index |
| %t | First native title if present, otherwise N/A |
| %f | Native FASTA writer; selecting %f switches to FASTA output instead of the four-column template |

The chosen four-column format omits %o and %t. Therefore native_oid is null and no native VDB ordinal or title is fabricated. Row ordinal is a byte-document locator, not biological identity. If %o is added later, use a separate signed native ordinal plus raw lexeme and exact source-view identity; do not populate the classic native_oid field.

## 3. Declared job, resource and input contract

Retain the original selected utility job/plan identity, one invocation, sealed original attempt, executable/environment custody and ordinary resource lifecycle. Add the VDB branch to the native utility requested-job union; do not create another autonomous execution path.

Use one prepared VDB selection operand per invocation, whose selected database_key and manifest describe the exact chosen set. Reuse the additional-BLAST VDB operand/validator by a public common port. Required facts are:

- kind=vdb; explicit original namespace/value/version/release/source and preparation method; exact ordered absolute native_paths; manifest version native_blast_prepared_database_manifest_v1, full file paths/digests/sizes and complete-inventory declaration; preparation_type=vdb in the manifest preparation record. Preserve unknown identity information.
- Exact manifest, preparation receipt, optional metadata/input manifests and required offline_configuration as original captured occurrences. Alias files and their supplied complete dependencies belong in the manifest/declared operand; a new path report cannot authorize another dependency.
- Explicitly selected native inputs with ordinals, kind path/alias/accession, original value, and their declared matching native_path. Preserve order and repeated list selections separately from the unique inventory of physical files. The first fixture should use an absolute supplied path. Accession/alias resolution needs an already declared offline mapping and actual applied resolver configuration; no implicit accession acquisition.
- Native operation input files entry_batch and database_list have independent input keys, original path/digest/size/format=text and captured bytes. The request records their exact ordered entries and source line ordinals. The staged bytes must agree with those values. Native database-list parsing splits whitespace, and batch processing reads nonempty lines; reject representations that would change the declared selection. A compiler must not read a file to discover additional choices.
- Each entry occurrence has ordinal and exact value. A corresponding optional supplied namespace/version identity is retained; otherwise use the explicitly defined namespace blast_vdb_cmd.entry for the literal command argument, not a guessed biological namespace. Duplicates are permitted and remain separate selector occurrences. An all selection is a distinct tagged variant, never an entry identifier.
- Dataset identity context is supplied and captured: dataset_key when established, selected_input, snapshot {release, snapshot_id, manifest_sha256}, dataset_type sra/csra/wgs/unknown, run identifiers and explicit provenance. Multiple source components remain distinct; a prepared set identity does not assert that they are one biological run.
- Optional member links are source-bound records keyed by native output record/identifier and supplied dataset. Reuse the meanings and nested types of existing VDB member metadata: member_kind read/reference/wgs_sequence/unknown; relationship reported_origin/catalog_membership; member_identifier; read_identity {native_read_name, spot_id|null, read_index|null, source}; reference_identity {identifier, full_length|null, sequence_sha256|null, source}; sample link when explicitly supplied. Remove search_key/hit indices from this supporting shape; do not synthesize them. Existing read_index is a nonnegative native value, with no newly inferred coordinate base. A source that states a base can retain that statement in its original metadata/provenance.

For the local branch, reuse only the tiny supplied offline input that fits actual 20 GiB RAM/4 GiB scratch accounting. No wall-time budget is added. This task authorizes no native execution on the host. A future normal native verification must use the established child-owned resource lifecycle, not a planning-shell bypass. There is no database BLAST search in this operation.

Current utility capture copies selected original database files into the Store. That works for a genuinely tiny offline fixture. Do not silently apply this to a large remote VDB dataset. A remote binding needs actual selected resource access, pinned helper/dependencies, immutable dataset/alias closure, resolver configuration applied under that resource, allowed data/cache/tmp locations and existing resource-owned execution/capture transport. No configured remote VDB utility capability was established here. If Aurora is actually selected, all software/data/cache/input/tmp/log/run paths stay under /lus/flare/projects/BioReason-Aurora-Test and new PBS jobs use -A EpiCalib; these constraints do not establish access or authorize a new dataset selection.

## 4. Shared result extensions and ownership of meaning

Keep every legacy v1 operation/result/receipt readable with its current meaning. New VDB branches use new versions blast_utility_operation_v2, blast_sequence_extraction_v2 and blast_database_inspection_v2 within the common families. They are additions to the common utility union, not parallel VDB scoring sheets. Existing classic results need no conversion or rewrite. A single common-core owner must freeze these shapes and update schema consumers that currently assume SCHEMAS[name]["properties"] is a single branch.

Operation v2 retains program/mode/database_key/input_occurrence_ids/molecule. For VDB molecule is dna, reflecting this helper's nucleotide output. Parameters contain:

    database_selection:
        source: db | dbs_file
        inputs: [{ordinal, kind: path|alias|accession, value,
                  binding_native_path, list_entry_ordinal: int|null}]
        list_occurrence_id: str|null
    line_length: positive integer
    selection: null for inspection, otherwise one of
        {kind: entries, source: entry|entry_batch,
         selectors: [{ordinal, value}], batch_occurrence_id: str|null}
        {kind: all_native_sequences}
        {kind: all_references}
    include_filtered_reads: boolean
    output_format: blast_vdb_cmd_table_v1 | blast_vdb_info_text_v1 |
                   blast_vdb_paths_text_v1

Validate the relationships rather than permitting arbitrary flag combinations. info/paths have include_filtered_reads=false; all_references also has false. output_format follows (program,mode). references in the table form come from selection kind and explicit member identity; they are not a universal ref flag. all_native_sequences names the regular native view: SRA/CSRA reads and WGS sequences keep their distinct member kinds. For specific entries, legacy reference_selection is null unless a genuine supplied context establishes its meaning; the absence of -ref does not prove that a selected native ID is a read.

Extend ArtifactOccurrence with native formats blast_vdb_cmd_table_v1, blast_vdb_info_text_v1 and blast_vdb_paths_text_v1, and input roles entry_batch/database_list. Reuse database_metadata and offline_configuration for declared context sources. No new output role is needed for managed stdout; the parsed record and exact saved artifact carry the specific meaning.

The closed VDB context keys are:

    version: blast_vdb_utility_context_v1
    source_inputs: [{
        ordinal: int>=0,
        selected_input: {kind: accession|path|alias, value: str},
        binding_native_path: absolute path,
        dataset_key: str|null, dataset_type: sra|csra|wgs|unknown,
        snapshot: {release: str|null, snapshot_id: str|null,
                   manifest_sha256: sha256|null},
        run_identifiers: [{namespace: str, value: str, version: str|null}],
        source: {source_ref: str, pointer: JSON pointer}
    }]
    selection_kind: entries|all_native_sequences|all_references|null
    include_filtered_reads: bool
    entry_identifier_bindings: [{
        selector_ordinal: int>=0,
        identifier: {namespace: str, value: str, version: str|null},
        source: {source_ref: str, pointer: JSON pointer}
    }]
    member_bindings: [{
        binding_key: str,
        native_identifier: str,
        dataset_key: str,
        member_kind: read|reference|wgs_sequence|unknown,
        member_identifier: {namespace: str, value: str, version: str|null},
        relationship: reported_origin|catalog_membership,
        read_identity: {native_read_name: str, spot_id: str|null,
                        read_index: int>=0|null, source: provenance}|null,
        reference_identity: {identifier: identity, full_length: int>=1|null,
                             sequence_sha256: sha256|null, source: provenance}|null,
        sample_key: str|null,
        provenance: {source_ref: str, pointer: JSON pointer}
    }]

Here identity and provenance expand to the exact nested shapes already shown; no unrestricted interpretation text is accepted. Every source_inputs ordinal corresponds to the original database_selection entry with identical selected value/path. Non-null dataset keys must refer to declared captured source metadata. entry_identifier_bindings cover each entries selector ordinal exactly once, retain its exact value, and are empty for other modes. member_bindings use exact reported %i equality; nonliteral aliases require a separately supplied source-grounded representation link before a row is given the binding. Multiple conflicting candidate bindings remain unresolved. A read binding cannot carry reference_identity and a reference binding cannot carry read_identity. sample_key is usable only with its independently supplied captured sample link; it is not inferred from a run label.

The corresponding vdb_member row contains the matching member binding plus its binding_key; it is null when a unique warranted link is unavailable. record_bindings retains the existing common shape {native_row_ordinal: int>=0, selector_ordinals: unique list[int>=0]}, with supplied explicit associations unable to contradict exact matches. All-mode rows have no selector associations and require no fabricated selector zero.

The native requested-job union adds native_blast_utility_job_v2 for this branch, with the existing software/environment/inputs/databases/outputs keys and declared vdb_context above. The result worker derives the runtime extraction context's returncode/producer_complete from authenticated original outcome/capture, never from a caller assertion. The producer stores the same exact selected v2 job and operation in the existing immutable utility plan/bundle lifecycle. Retain the current bundle source version and 638 discriminator; this plan does not require reversioning old bundles.

V2 results add operation_input_occurrences (the original non-database input occurrences) and vdb_context (closed source/view/member binding records above). The shared result-reference validator must admit the union of these and DatabaseBinding.occurrence_ids, not falsely put entry files in database membership. Native output occurrences remain distinct. All source/binding pointers must refer to original declared captured records or the original selected request.

Extraction reuses the current common record fields and validators:

| Common field | VDB mapping |
| --- | --- |
| record_key | output occurrence + "#/records/" + original native row ordinal |
| native_row_ordinal / line_number | original four-column text line ordinal / one-based line, including gaps after invalid rows |
| matched_selector_ordinals | every warranted original selected-entry occurrence; no deduplication of the request |
| association | exact literal native ID/accession match, explicit source-proven equivalent, or unresolved |
| native_oid | null; never row ordinal, spot ID, read index or VDB %o |
| native_identifier / native_accession | exact %i / %a values |
| native_reported_length | parsed native %l if a valid integer; preserve original lexeme in the native source |
| native_length_basis | returned_sequence; no assertion about complete unclipped read or genomic reference extent |
| original_sequence / normalized_sequence | raw returned symbols / shared normalization |
| returned_symbol_count | shared validated symbol count or null; not a confidence score |
| molecule | dna for this selected native operation |
| requested_range / effective_range | null; the helper did not accept a selected range and has not established a genomic origin |
| checks / failures | existing shared custody, syntax, selection, identity, length, symbol and execution meanings |
| completeness | actual row/capture qualification; good records survive other row/native failures |

Use the same shared normalization/count/length validators as classic extraction, factoring a public pure helper from blast_database_extraction where needed. Existing VDB metadata _symbols accepts a wider nt alphabet including U, whereas the shared declared-dna parser does not. Keep the legacy parser output unchanged; the supporting adapter applies the same declared-dna rule as blastdbcmd, retaining any disagreeing symbols and a null unusable shared count. Do not silently redefine either historical interpretation or create an alternative VDB score.

Add row-level vdb_member: null or the explicit member shape above, with binding source references. Native raw identifiers always remain even without such a link. Never split an accession on dots to manufacture run, spot or read relationships, equate all reads with spots, infer organism from sample context, or promote catalog_membership to reported_origin.

Add extraction scope {kind: selected_entries|all_native_sequences|all_references}. Selected-entry results retain missing_selector_ordinals and unexpected_record_keys. An all result has no fabricated selector list and no guessed population denominator; its observed rows are the native enumeration. Its complete_selection means the selected native enumeration was captured and completed without relevant diagnostics/parse failures, not that it is a biological run census. Unknown clipping/filter/source semantics remain unknown.

Inspection v2 reuses common NativeField locators/value_basis/missing_reason and adds explicit VDB field names, rather than copying counts into a classic sequence-database population:

| NativeField name | Value / unit / population |
| --- | --- |
| vdb_selected_inputs | native reported token list / native_input_tokens / selected invocation strings |
| vdb_resolved_paths | native reported token list / paths / resolved VDB selection |
| vdb_sequence_count | native integer / sequences / GetVDBStats(m_allDbs) population |
| vdb_total_unclipped_bases | native integer / nt / same population, native "(unclipped)" label |
| vdb_longest_sequence_bases | native integer / nt / same population |
| vdb_average_sequence_bases | native reported integer / nt / same population; never recompute as length/count |
| vdb_csra_inputs | native reported token list when present / paths / CSRA subset |
| vdb_reference_sequence_count | native integer / sequences / CSRA reference population |
| vdb_reference_total_bases | native integer / nt / CSRA reference population |

Preserve comma-formatted integer lexemes, zero, exact text locators and wrapped source blocks. Missing reference fields are null with native_field_absent, not zero. In a pure CSRA source the "CSRA Database(s)" label may be omitted even while reference counts are present; do not lose those counts or infer a missing label value. Source helper internals are not retained here, so do not assert a filtering/clipping definition beyond the reported label and function invocation. These numbers are not search denominators unless a separate exact context join establishes that meaning.

For paths/paths_all, add path_sections and path_records to DatabaseInspection v2. A section is {kind: vdb|vdb_alias|blast_db_alias, header_line_number: int|null, presence: reported_empty|reported_values|not_reported}. A row is {kind, section_ordinal, native_path_ordinal, native_path, line_number, matched_dependency_ordinals: int[]}. native_path_ordinal is zero-based across the entire emitted path-row stream; section_ordinal indexes the retained section list. An unreported section has null header_line_number. Retain original order, duplicate occurrences and native spelling. Recognize native "VDB(s):", "VDB Alias File(s):", and the exact native typo "Blats DB Alias File(s):". "None" after a header means an empty reported section, never a path named None. Top-level paths mode does not report alias sections. Flat -paths_all output establishes no edge direction, file digest, complete file inventory or alias validity.

Concurrent 642 owns preparation/alias semantics. When a path row matches an already supplied dependency, use its exact tuple:

    {ordinal, database_key, native_reference,
     source: db|dblist|dblist_file|vdblist|vdblist_file|num_volumes,
     list_occurrence_id: str|null, list_entry_ordinal: int|null}

Do not add a VDB-specific DatabaseArtifactSet or competing dependency tuple. A path that does not exactly match a supplied identity remains an unbound reported path; the parser does not discover/capture another resource. VDB alias compatibility/export remains unverified without authentic native context.

## 5. Parser and normalizer ports

Proposed pure module: gene_annotation_episode/blast_vdb_utility_inputs.py. No filesystem/network/process access.

    parse_blast_vdb_extraction(
        contents: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict,
        operation_input_occurrences: list[dict], vdb_context: dict,
        stderr_contents: bytes, stderr_occurrence: dict,
        record_bindings: list[dict] | None = None
    ) -> dict  # common SequenceExtraction v2

    normalize_blast_vdb_extraction(
        parsed: dict, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict,
        operation_input_occurrences: list[dict], vdb_context: dict,
        stderr_diagnostics: dict,
        record_bindings: list[dict] | None = None
    ) -> dict  # same common result, no native execution

    parse_blast_vdb_inspection(
        contents: bytes, *, occurrence: dict, operation: dict,
        database_binding: dict, outcome: dict,
        operation_input_occurrences: list[dict], vdb_context: dict,
        stderr_contents: bytes, stderr_occurrence: dict
    ) -> dict  # common DatabaseInspection v2

    parse_blast_vdb_diagnostics(
        contents: bytes, *, occurrence: dict, outcome: dict
    ) -> dict  # closed located native diagnostic categories, raw bytes retained

For selected-entry four-column parsing with a genuine existing single selected_input/dataset extraction context, reuse parse_blast_vdb_member_sequences and that exact context. Do not construct a fake source dataset, synthetic selected_input or fake search just to call it. Multiple inline source operands cannot be represented by inventing one selected_input for the old wrapper: use the shared lexical reader below, retain the real ordered selected inputs in vdb_context, and apply the same common supporting normalizer. A source-proven single alias remains that actual selected alias, with distinct resolved components. Unresolved source dataset/member assignments stay null; a dataset_key is never inferred from a row identifier.

For all-native-sequence/reference or multi-source four-column parsing, do not pass entry_identifiers=["all"] or a fabricated context to the existing parser. Extract a shared lexical four-column row reader inside blast_vdb_inputs.py, preserving the existing specific-entry wrapper's output and replay behavior. Proposed pure signature:

    read_blast_vdb_sequence_table(
        contents: bytes, *, source_ref: str, source_version: str
    ) -> dict
    # input identity, native text, rows with original ordinal/line/cells,
    # native nullable integers/symbol payload, located issues; no membership claims

The new supporting wrapper supplies the tagged all or multiple-source scope; the old wrapper continues exact specific-entry identity matching. If this common reader is not yet built, only specific entries with the existing genuine single-input context are eligible to be advertised; all/multiple-source work remains a named unfinished port, not a fabricated capability.

The normalizer must verify the retained input identity and exact context against the original occurrence/job. It must use native_record.row_ordinal for surviving legacy records, retain the original legacy parse payload for downstream replay, map syntax/length issues to shared failures and keep native bytes for skipped/N/A rows. It must not rewrite a legacy parsed record to look successfully linked.

Legacy duplicate entry identifiers make len(matches)!=1 and produce member_identifier_unlinked. For supporting literal selection coverage, the common adapter may establish the exact set of identical command-selector ordinals from the retained native ID/accession; preserve the legacy issue and an explicit located association explanation. Do not pretend that this identifies one emission with one duplicate request, resolves conflicting namespace/version identities or repairs a scientific dataset/member link. Nonliteral gnl|SRA| stripping already recognized by the legacy parser is not a new equivalence rule: treat it as an explicitly recorded sra_general_tag representation join. The help example gnl|SRR| is not a license to extend that equivalence by guesswork.

Native diagnostic matching must include the source messages "Failed to find Bioseq for", "Bioseq constains no sequence data", "Empty Bioseq", "Iterator returns BLAST_SEQSRC_ERROR" and "Failed to retrieve requested item", retaining spelling and actual prefix/line. These can identify partial extraction even with returncode zero. Native prefix/version variations require retained fixture proof; unrecognized warning/error text stays a located unknown diagnostic, never automatically successful selection.

Info parsing is distinct from the classic BLAST database info grammar. Read complete wrapped blocks and validate duplicate/conflicting populations. Paths parsing recognizes the three native sections with source locators. Unknown extra content remains retained/qualified, not silently treated as a database file. Both parsers call the common validator and shared outcome/capture checks.

## 6. Complete consumer and failure path

Changes must follow this actual path; no separate runtime gate or reviewer is proposed.

1. native_blast_utility_tool_info.py: register precise (program,mode) capabilities only after their dependencies are implemented. Any new runtime TASK/STEERING text requires the user's ongoing template feedback; this planning task writes none.
2. native_blast_utility_contracts.py: add v2 branch/operand/input/output formats, exact compiler and semantic validation; dispatch on (program,mode), not bare info/extract_sequences. Preserve original request/argv/identity and input occurrence order.
3. native_blast_utility_driver.py/local.py: retain one selected attempt, existing resource accounting and replay. Use shared prepared-VDB recursive inventory instead of classic prefix globbing; check immutable original files before and after; retain actual applied configuration provenance. No hidden resolver/download.
4. native_blast_utility_acquisition.py: capture exact sealed output streams, original selection/list/context files and declared database closure. An unexpected reported path is not automatically acquired. Expose genuine unavailable/mutated originals as capture failures.
5. native_blast_utility_result_worker.py: qualified_utility_context reconstructs VDB context from original request/bundle and exact captured metadata, never from an unbound caller-supplied context. Extend validate_context and RESULT_SCHEMAS by (program,mode); invoke the relevant parser for parse_original. project_saved reads the saved common result without native re-execution or fresh metadata acquisition.
6. native_blast_utility_result_publication.py: validate the new saved-result versions and original worker receipts/hashes. Preserve immutable source snapshot and exact publication identity.
7. blast_utility_result_views.py: extend common v2 selector/fact union for explicit all-mode row selection, VDB identity fields and path sections/rows. Existing entry selector ordinals, database-field names, check selection and explicit artifact slots retain their meanings. Projection copies shared values; no parser, scoring or recalculation lives here.
8. native_blast_utility_results.py/returns.py, practical_execution_operations.py, execution_progress.py and episode_receipts.py: carry the new union through the same parent-selected commission and immediate-child return. Verify operation/resource/source/row relationships and selected facts. Do not expand source references into every artifact or replace the original goal with a helper operation. Any new bundle version must also be recognized by the existing special source-dependency handling.
9. A later scientific consumer may receive the expressly selected native four-column artifact and exact dataset/member context and use native_blast_database_metadata documents/parsed_sources/_vdb_units. RunInfo counts, sample context and reference annotations remain independently sourced. No utility return alone creates a VDB search sheet or function score.

The v2 result selector keeps the current fields and adds:

- sequences.selection: {kind: selector_ordinals, values: int[]} for entries or {kind: native_row_ordinals, values: int[]|null} for an explicitly selected all output; null explicitly means all already-produced rows, not another dump.
- sequences.include_vdb_identity: boolean; ordinary sequence fields are independently selected.
- paths: null or {kinds: (vdb|vdb_alias|blast_db_alias)[], native_path_ordinals: int[]|null, include_sections: boolean}.
- vdb_context: boolean selecting closed provenance facts. This does not itself grant underlying metadata artifact bytes.

Old selector v1 stays valid. Include exact missing-selection records when requested entries/rows/fields are unavailable. Paths/native-row locators and source identity facts need constrained reference schemas and validation through return acceptance, not unrestricted findings prose. Use saved_data=result only when explicitly requested; artifact direction/role/ordinal selection retains 633's semantics. These additions share the same core owner as 642's common union changes.

Preserve 638 capture semantics verbatim in implementation:

- New producer bundles declare output_completeness_basis="captured_bytes". A fully captured, closed output is complete even when the native process failed.
- Native state/returncode, writer closure, output enumeration/capture completeness, declared database inventory and semantic/selection completeness are distinct facts.
- Legacy bundles lacking that discriminator keep their original interpretation; do not upgrade them during replay.
- Native nonzero exit yields native_nonzero_exit, not an invented output_inventory_incomplete when all bytes were captured. Open writer, unavailable native outcome and unestablished capture retain their specific codes.
- Valid partial rows survive native errors, skipped rows, unknown identity and failed selectors. Missing values are null with reason; failed extraction is not a zero-length sequence or negative scientific result.
- return status.state describes delivery of the requested typed view; it can be complete for fully delivered qualified facts from a failed native attempt. native_state and result_completeness communicate the separate outcome. Do not insert a scientific-success gate into practical completion.
- One acquired original bundle remains the existing operational contribution unit. Reprojection and parser construction make no new native action or observation. Preserve ordinary practical completion/controller behavior and the parent's typed return ownership.

Request/schema/binding contradictions fail before invoking native work with existing stable contract-error style. Native/data issues return shared located UtilityFailure rows (native_row_invalid, native_document_invalid, record_association_unresolved, selection_incomplete, sequence_length_conflict, sequence_symbol_invalid, supplied_binding_conflict, native_diagnostic_unrecognized, dependency_unavailable, input_identity_mismatch, native_nonzero_exit as applicable). Use existing meanings first; add a code only if a distinct VDB condition cannot be represented without ambiguity.

## 7. File ownership and ordered dependency outputs

No files below are assigned to this planning subagent. Root must appoint fresh owners before coding.

| Owner | Files / exact output | Depends on |
| --- | --- | --- |
| One shared utility-core owner | blast_utility_contracts.py, shared extraction normalization/validation port in blast_database_extraction.py, common version/schema registry | frozen v2 shapes above plus 642 union changes |
| VDB parser owner | new blast_vdb_utility_inputs.py; narrow shared lexical reader in blast_vdb_inputs.py preserving old parser/replay; parser fixtures/tests | frozen common input/result signatures and explicit fixture bytes |
| Native utility binding owner | native_blast_utility_contracts.py, driver.py, local.py, acquisition.py; public prepared-VDB validation/inventory port factored from existing additional-BLAST modules | exact v2 operation/operand/input formats; actual selected offline resource/config |
| Result/return owner | result_worker.py, result_publication.py, result_views.py, results.py, returns.py and affected generic consumer unions | saved common schemas, parser functions, captured original context |
| Alias/preparation owner 642 | its DatabaseArtifactSet/alias dependency/restriction ports only | literal dependency tuple shared with core; no new VDB extraction policy |
| Integration verifier | bounded fixture operation through real child-owned request/capture/result/return path; historical regressions | implemented ports and authentic supplied small source |

Do not have parser workers edit common schema constants, mode registries or projections concurrently. The dependencies are exact artifacts/types/functions, not a request to wait for all BLAST tools. A native fixture gap does not prevent pure contract/parser work with clearly labeled synthetic edge cases, but those examples cannot close authentic native verification.

## 8. Native fixtures and meaningful verification

No authentic VDB helper data output or supplied tiny VDB input was established by this planning inspection. Do not report source/help availability as native verification.

The smallest useful first native input is an explicitly supplied tiny immutable offline SRA VDB file/directory with two known distinct native read IDs, complete manifest, publisher/preparation provenance, resolver/offline configuration and an independently supplied record-to-run/read identity source. It permits one real selected-entry four-column extraction and info/paths capture. It does not prove paired-read/filtered/reference/alias variants unless it actually contains them.

Additional fixtures required for the mappings:

| Fixture | Native input and independent fact needed | What it proves |
| --- | --- | --- |
| Paired reads | tiny SRA with one spot containing at least two reads; explicit source record linking native read names, spot and read indexes | two reads remain separate, spot count not substituted for read count, original identities/ordinals retained |
| Filtered read | tiny source with a known filtered read and recorded native filtering provenance | include_filtered_reads flag and selected source view differ as recorded; no guessed denominator transfer |
| CSRA read/reference | tiny CSRA with at least one read and one reference with known full identity/length and actual required local dependencies | selected-ID native dispatch, all-reference -ref behavior, reference counts and identity kept separate from reads |
| Native returned extent | source with documented full read/reference extent that differs, if applicable, from helper returned symbols | native %l / returned symbols are not mislabeled genomic/full unclipped coordinates; absent proof remains unknown |
| WGS | tiny offline WGS input with two native contig/member IDs and exact source metadata | WGS sequence identity is not relabeled as SRA run/spot/read |
| Mixed selection | declared SRA + CSRA selected set, ordered manifest and original list file | wrapped info text, all selected versus CSRA reference populations, precise unresolved member origins |
| Aliases | actual small VDB alias and nested alias plus their complete supplied closure; optional classic alias only if actually supported by native input | paths versus paths_all flat sections, native typo, literal links to 642 dependencies without invented edges |
| Failed selection | known-good ID plus known-absent/invalid ID against the same tiny source | preserved good row, real stderr, actual returncode; zero exit cannot hide a missing selector |
| Native complete failure | a deterministic invalid selected operation/input in the permitted fixture lifecycle | closed captured streams remain byte-complete with nonzero native status under 638 |

Planned meaningful tests (not written or run in task 643):

1. Compiler equality against the exact native mode/argv table; no classic flags, silent mode priority or inferred remote action. Test distinct mode+program dispatch.
2. Operand/list validation: original order and duplicates, two mutually exclusive list forms, captured bytes versus declared lines, prepared manifest closure and applied-configuration evidence.
3. Four-column reader/adapter with valid rows around a malformed/N/A row: shared keys preserve native ordinal gaps and raw byte evidence. The old selected-entry parser and its replay payload retain their original behavior.
4. Literal IDs/accessions, duplicate selector occurrences and explicit representation links; conflicting namespaces/versions and unresolved multi-source origins never become invented identity matches.
5. Shared symbol/count/length behavior against classic extraction for identical declared-dna symbols, including lowercase, invalid characters and U. There is one normalization/check meaning.
6. Native omissions: missing %o/title/spot/read metadata remain absent; row ordinal never fills OID; full reference length and returned length are distinct; no inferred effective range.
7. info counts with commas, zero, mixed CSRA, missing optional labels, wrapped database lists, conflicting duplicate fields and truncated text; retain native integer average without recalculation.
8. paths/paths_all empty sections, native "Blats" spelling, repeated paths, absent sections and a reported undeclared dependency; no auto acquisition or fabricated alias graph.
9. all selection uses the new lexical reader/context, never the old specific-entry parser with all; all-references requires CSRA input and no filter flag. Known skip diagnostics prevent false complete enumeration.
10. Good row plus native nonzero; zero-exit missing selector; "Empty Bioseq"/no sequence data diagnostics; open writer; missing captured stream; unchanged legacy no-discriminator completeness.
11. Worker original-context authentication, cross-attempt/database/source/metadata splice rejection and complete parse-original versus project-saved identity. No new native execution on replay.
12. Parent receives exactly selected sequence/identity/path facts and explicit artifact/saved-data slots. Merely receiving provenance/source_ref never grants all native/database files.
13. One acquired original bundle and subsequent projections follow existing operational credit/ordinary practical completion semantics; no added scientific score, fake search, cancellation or observation.
14. Authentic fixture through the actual selected child-owned operation, source capture, deterministic worker, publication, requested typed return and accepted parent receipt. Standalone parser success is insufficient.
15. Focused classic utility/638/633 and existing VDB parser regressions only after affected changes; do not rerun unrelated successful groups.

The fixture/resource owner must deliver three specific retained inputs before authentic native verification:

    VDB_FIXTURE_MANIFEST.json:
        one actual selected source's absolute path(s), complete original file
        identities/total bytes, preparation/source provenance, snapshot and
        at least two known exact native entry values
    VDB_OFFLINE_BINDING.json:
        actual selected resource key, pinned executable/dependency identities,
        exact configuration file identities and paths, exact environment/
        working-directory settings that apply them, resolver search roots and
        declared dataset closure, plus retained evidence that this selected
        configuration resolves the fixture without acquiring remote content
    VDB_IDENTITY_BINDINGS.json:
        source-grounded dataset/run/member links and the optional paired-read/
        spot/reference/sample details that the selected fixture actually proves

These are required deliverable names for a future fixture/resource owner, not files fabricated or acquired in task 643. The fixture can supply fewer identity details and still prove basic extraction, with those fields null; only the corresponding richer identity tests remain unverified. A configuration document with no actual application settings/evidence does not satisfy VDB_OFFLINE_BINDING.json. No particular environment variable, credential or host value is guessed here.

If the first authentic fixture is unavailable, the concrete missing deliverable is one supplied accessible offline VDB source path plus its immutable manifest/configuration/provenance and known entry IDs, or an already configured resource and explicitly selected acquisition operation that can supply exactly that source. If acquisition needs credentials or a selected public dataset, that information must come from the real caller/resource configuration. No credential, remote host, accession or download size is guessed. A whole RunInfo query, arbitrary live SRA download or local database BLAST is not a substitute.

## 9. Task accounting

This task changed planning artifacts only inside verification/tool_graders_blast_vdb_inspection_ports_2026-10-28_643/. It used host text/JSON/AST/source inspection and retained primary evidence; no application imports, database-content reads, native commands, network acquisition, production/test edits or runtime prompt construction. The accompanying evidence file records source hashes and reading coverage, not passed tests.

The next concrete implementation increment is the shared v2 contract plus the selected-entry adapter and tuple-dispatched native/result path, verified against one actual tiny supplied offline source. Other native modes have the exact inputs and separate verification dependencies above. They remain unfinished until implemented and actually verified; no catalog or help result closes them.
