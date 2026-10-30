# Native VDB utility: coding handoffs for root review

Planning only, 2026-10-28. This supplies the missing native/request/capture ports
for 643, completed core 662 and completed parser 663. It changes no objective,
scientific calculation, prompt, inventory row or historical receipt. The user’s
original attachment remains authoritative. The formatter removals and 305 active
inventory remain. No implementation, application import, test, acquisition or
native invocation was performed for 664.

## 1. Fixed dependencies and exclusive coding ownership

Keep `blast_utility_operation_v3`, `blast_sequence_extraction_v2`,
`blast_database_inspection_v3` and `blast_vdb_utility_context_v1` exactly as 662
implemented. Use 663’s four public parser/normalizer ports; no alternate sequence
normalization, native average calculation or VDB search context is introduced.

| Owner | Exclusive files and concrete outputs |
| --- | --- |
| Native compiler/producer/capture | `native_blast_utility_contracts.py`, `native_blast_utility_driver.py`, `native_blast_utility_local.py`, `native_blast_utility_acquisition.py`; new `native_blast_vdb_utility_execution.py`. Own job-v3 schema, compiler, selected-file enumeration, one bwrap launch, sealed bundle/capture and conditional v3 failures. No result-worker or view edits. |
| Original context/assembly | New `native_blast_vdb_utility_context.py`; **all** `native_blast_utility_result_worker.py` edits, including VDB parser dispatch and calling the view owner’s projector. Own request-context schemas, fixed extraction/equality checks, occurrence qualification, manifest-v2 authentication and worker plans. No publication/view edits. |
| Requested views/publication/return | `blast_utility_result_views.py`, `native_blast_utility_result_publication.py`, `native_blast_utility_results.py`, `native_blast_utility_returns.py` and the explicit information-library/constructor consumers assigned in 665. Own selector/projection/publication/acquired version boundaries and typed return populations. Consume the context owner’s ports below. |

New tests belong separately to their owner. Existing core/parser files and tests
remain read-only dependencies unless root assigns a particular defect. The
preparation materialization module is not a VDB relocation mechanism. No owner
changes its existing grammars or v2 behavior for this task.

Root's final allocation combines native compiler/producer/capture and original
context/assembly into **one fresh coding owner**, including the entire worker
file. Pure views are assigned separately to 667; publication/results/returns
are the third coding owner. The table describes exclusive file boundaries,
not a requirement to spawn a fourth worker. The controlled full request/context
example is `REQUEST_CONTEXT_EXAMPLE_002.json`; its unbound runtime identities
are explicitly placeholders, not fabricated Store records or native evidence.

Existing reusable functions, rather than a fabricated search job:

* `native_blast_database_contracts.validate_native_blast_database_operand` and
  `validate_prepared_blast_database_manifest`: the primary prepared VDB operand.
* Existing standard/additional operand validators: explicitly selected supporting
  dependency operands, as already dispatched by utility preparation v2.
* `native_blast_utility_contracts.staged_relative`, `native_environment`,
  `database_file_selections`, `realized_path_maps`, requested-job/plan validators.
* Driver `_stage_inputs`, `_final_inputs`, `_observe_databases`, managed stream
  capture/sealing and immutable attempt ownership; adapt their v3 branches.
  Reuse the recursive inventory algorithm in
  `native_blast_database_driver._inventory` through one narrowly shared helper
  if needed; do not copy its search execution path.
* `blast_preparation_inputs.parse_blast_alias_document` for selected alias
  directive bytes, with the actual occurrence; not a new alias scanner.
* Acquisition `_selected_files`, `_key`, `_validate_saved`, `source_payload`,
  `capture_local_utility_bundle` and existing Store custody.
* Worker `qualified_utility_context`, `validate_context`, `_verify_file`,
  `validate_worker_plan`, `validate_worker_manifest` and immutable worker intents.
* Publication `_validate_receipt`, `validate_prepared_utility_result`,
  `_projection_context`, `publish_selected_utility_result`,
  `validate_utility_publication`: authenticate retained work, then project.
* `NativeBLASTUtilityResults.validate_job_inputs` and its actual `_known` /
  received-reference checks. A Store lookup alone is not admission.

Keep the common native lifecycle and `method_loop`. The selected local operation
is one tool invocation inside an episode, not a new episode, source-selection
agent, retry loop, scheduler, monitoring cadence or resource substitution.

## 2. Exact job-v3 and compatible old schemas

All objects below are closed: every listed key is required, additional keys are
rejected; `?` means a nullable value, not an omitted key. Common typed objects
refer to existing exact schemas, not a newly copied definition.

```text
NativeVDBJob = {
  version: "native_blast_utility_job_v3",
  operation: exact blast_utility_operation_v3,
  software: existing SOFTWARE_SCHEMA,
  environment: OfflineEnvironment,
  inputs: [VDBInput],
  databases: [exact additional-BLAST prepared VDB operand],  # exactly one
  outputs: [VDBOutput],                                    # exactly two
  vdb_context_request: VDBContextRequest,
  offline_execution: OfflineExecution
}
VDBInput = {
  input_key: nonblank token, role: "entry_batch" | "database_list",
  path: absolute path, format: "text", sha256: SHA256,
  size_bytes: integer >= 0, artifact_ref: artifact ID | null
}
VDBOutput = {
  role: "stdout" | "stderr", path_kind: "file",
  relative_path: confined relative path,
  format: "text" | "blast_vdb_cmd_table_v1" |
          "blast_vdb_info_text_v1" | "blast_vdb_paths_text_v1"
}
```

There is exactly one stdout and one stderr, with distinct paths. Stderr is text;
stdout’s format equals the exact operation’s output format. These are the old
simple managed stream descriptors, not v2 materialized output descriptors.
Inputs are exactly the independently selected `dbs_file` and/or `entry_batch`
slots, in `operation.input_occurrence_ids` order. An input key in the operation
is a request-local slot name until the matching bytes are captured; its spelling
does not authenticate a source or grant a file. No orphan/extra input is admitted.

`databases[0].database_key == operation.database_key`, `kind == vdb` and every
operation `binding_native_path` belongs to that operand’s `native_paths`.
Preserve the common schema’s important distinction:
`identity.preparation_type == unknown`, while
`manifest.preparation.preparation_type == vdb`. The manifest is the exact common
`native_blast_prepared_database_manifest_v1`, complete inventory and non-null
offline configuration included. Verify its selected file bytes equal the
embedded manifest, before and after execution and again from retained bytes in
original-context authentication. A common validator accepting it is not proof
of applied offline execution.

Preserve the existing `native_blast_utility_run_plan_v1`, bundle source version,
immutable plan/attempt/owner paths and requested-job wrapper:

```text
{argv: compile(job using original input paths),
 environment: job.environment, native_blast_utility: job}
```

Historical compatibility is two separate facts. Before 662, both native v1 and
v2 schema objects embedded generic `SCHEMAS.Operation`, then the union of
classic operation v1 and preparation operation v2. Their semantic validators
already constrained valid jobs to the corresponding program/version. The
pre-662 snapshot in 529/check122_vdb_core662_baseline records that history; it
must not be described as a historically single-branch schema.

Freeze each old public native-job schema’s nested Operation as that historical
v1+v2 union, constructed from exact version schemas, never today’s expanding
generic union. Preserve those old schema objects and semantic validators.
New job construction through `native_blast_utility_job_schema(program, mode)`
uses the exact applicable operation version (v1 classic, v2 preparation, v3
VDB) as an additional constraint. Add a detached v3 job branch whose operation
is only v3. No old job advertises VDB or acquires new environment/output roles.
Saved old jobs, forms, receipts and numerical meanings remain unchanged.

### Compiler and path semantics

Keep the existing signature of `compile_native_blast_utility_job(job: dict, *,
input_paths: dict, database_paths: dict, output_directory: str) -> list[str]`.
Its v3 branch dispatches by `(operation.version, program, mode, selection)`.
`DB` below is one argv element, space-joining original ordered selected `value`
tokens. It is not a shell expression. Original values, repetitions and order
are preserved; do not replace an accession/alias token with its bound path.

| Variant | Suffix after `EXE` and database source |
| --- | --- |
| entries, entry | `-entry comma_join(selectors.value) -outfmt TABLE -line_length N` |
| entries, entry_batch | `-entry_batch mapped_batch_path -outfmt TABLE -line_length N` |
| all_native_sequences | `-entry all -outfmt TABLE -line_length N` |
| all_references | `-entry all -ref -outfmt TABLE -line_length N` |
| info | `-info -line_length N` |
| paths | `-paths` |
| paths_all | `-paths_all` |

Each row has either `-db DB` or `-dbs_file mapped_database_list_path`, never both.
`TABLE` is the literal `%i<TAB>%a<TAB>%l<TAB>%s`, containing real tabs. `N` is
the recorded positive `line_length`, normally 80. Append
`-include_filtered_reads` after the mode suffix only when selected true for
entries or all_native_sequences. No other optional flags are compiled. In
particular no classic `-dbtype`, range/strand/get_dups/target_only/exact_length,
no selected-entry `-ref`, and no `-out`/`-logfile`.

Original input paths map to the existing immutable staged copies at
`attempt/<staged_relative(input)>` (that helper already includes `inputs/`).
These bytes are unchanged, including
database-list tokens: there is no v2 materialization or list rewriting. Database,
alias, configuration and native executable paths retain the original absolute
paths inside the namespace. V3 rejects a `database_paths` override that changes
them. Every selected `kind=path` value is its exact bound absolute path. Aliases
and accessions require a selected already-present offline resolver mapping;
the first real binding exposes absolute paths only until that mapping has been
verified. Compilation support does not claim such a mapping exists.

For `dbs_file`, authenticate whitespace tokens in order against
`database_selection.inputs`, including duplicate tokens and list_entry_ordinal.
For `entry_batch`, authenticate nonempty native lines in order against the exact
selectors, preserving duplicates; CRLF/LF handling follows retained native
source. Record byte/line positions in the authentication receipt. Reject a
representation whose native interpretation differs; a compiler never reads a
file to discover choices. These are VDB-specific lexical checks, not the
preparation `blast_database_lines` grammar.

## 3. Request context, documents and dependencies

```text
VDBContextRequest = {
  version: "native_blast_vdb_utility_context_request_v1",
  documents: [JSONDocumentSelection],
  source_inputs: [core SourceInput with source replaced by Origin],
  entry_identifier_bindings: [core entry binding with source replaced by Origin],
  member_bindings: [core VDBMember with every source/provenance replaced by Origin],
  sample_links: [core sample link with link.source replaced by SampleOrigin],
  dependency_databases: [existing prepared standard/additional operand],
  database_lists: [DatabaseListSelection],
  declared_dependencies: [DependencyRequest]
}
JSONDocumentSelection = {document_key: token, selection: JSONAddress}
JSONAddress =
  {kind:"database_manifest", database_key:token} |
  {kind:"database_metadata_manifest", database_key:token, manifest_index:int>=0} |
  {kind:"database_sidecar", database_key:token,
   role:"preparation_input_manifest"|"preparation_receipt"}
Origin =
  {kind:"request"} |
  {kind:"selected_json", document_key:token, pointer:RFC6901}
SampleOrigin = Origin |
  {kind:"dataset_sample", document_key:token,
   dataset_pointer:RFC6901, sample_index:int>=0}
DatabaseListSelection = {
  list_key:token,
  selection:{kind:"database_file", database_key:token, file_index:int>=0},
  grammar:"vdb_whitespace_tokens"|"blast_database_lines"
}
DependencyRequest = {
  role:"database", ordinal:int>=0, database_key:token, native_path_index:int>=0,
  native_reference:token,
  source:"db"|"dblist"|"dblist_file"|"vdblist"|"vdblist_file"|"num_volumes",
  list_ref: null | {kind:"input", input_key:token} |
                  {kind:"database_list", list_key:token},
  list_entry_ordinal:int>=0|null,
  declaration: DependencyDeclaration
}
DependencyDeclaration =
  {kind:"request"} |
  {kind:"selected_json", document_key:token, pointer:RFC6901} |
  {kind:"alias_directive", database_key:token, file_index:int>=0,
   directive:"DBLIST"|"VDBLIST", directive_row_ordinal:int>=0,
   token_ordinal:int>=0}
```

This is a small request locator schema, not a general provenance engine.
`selection_kind` and `include_filtered_reads` are derived from the operation,
not independently supplied. Context `dependency_database_bindings` are built
from the selected operands, never accepted as parent-supplied Store identities.
No `source_ref`, captured occurrence ID, prior-run source ID or
`initial_known_record_refs` is supplied in these new locator fields.

Document selections resolve only against the primary and explicitly selected
dependency operands. The selected descriptor supplies original path/hash/size
and any **actually received** artifact reference. No free path, URI, `received`
source wildcard, report-discovered path or Store search is accepted. A selected
metadata file can be an existing additional-BLAST metadata document; no search
context is invented to read its dataset/member/sample records.

The primary selected operand remains exactly one. Supporting operands have
unique keys disjoint from it, use the same common prepared-manifest validation,
and contribute their explicitly selected files to capture and offline closure.
They never become extra `-db` operands. A supporting operand cannot expand a
scope/grant: original job admission authenticates its non-null artifact/source
references using the same actual received-record machinery as the primary.

All list selections reference manifest `files[file_index]` of their declared
operand. The worker gives that **existing captured row** role `database_list`
and format `text` in the qualified occurrence catalog; it remains a database
occurrence, not an operation input. Its selected row identity is not changed.
Reject conflicting role declarations for a single selected row. The core’s
database-side list IDs then have actual descriptors and bytes in the worker,
even though the pure result deliberately carries only their binding membership.

### Fixed extraction/equality rules

`kind=request` means the values were supplied in the actual original request;
it does not claim independent metadata corroboration. Its qualified provenance
is `capture.source_ref` plus the exact pointer into
`/requested_job/native_blast_utility/vdb_context_request/...` in the retained
bundle JSON. This also covers explicitly supplied biological claims. Unprovided
identity stays null/unknown; a label is never promoted to a biological identity.

`kind=selected_json` requires all of the following fixed comparisons after the
selected file has been hashed, decoded and addressed with strict RFC6901:

| Context slot | Pointed original record and exact compared fields |
| --- | --- |
| source_inputs[i].source | Dataset object: dataset_key, dataset_type, selected_input, snapshot, run_identifiers. Ordinal/binding_native_path come from the actual operation, separately checked. Other original dataset fields, including a genuine search_context, are retained in bytes but unused. |
| entry_identifier_bindings[i].source | An identity object with namespace, value, version. The value must also equal the actual selector. Default literal namespace is blast_vdb_cmd.entry, using request provenance. |
| member_bindings[i].provenance | Member object: dataset_key, member_kind, member_identifier, relationship, read_identity, reference_identity, sample_key, plus exact native_identifier; alternatively existing additional-BLAST native_description.id supplies that last field. If both occur they must agree. binding_key is only the request-local association key. Nested source/provenance fields are compared separately, not treated as biological values. |
| member read_identity.source | Object with native_read_name, spot_id, read_index exactly. No read-index base is inferred. |
| member reference_identity.source | Object with identifier, full_length, sequence_sha256 exactly. No length/digest is filled from the helper to make a claim true. |
| sample_links[i].link.source | Utility sample record with dataset_key and link containing sample_key, sample_identifier, biosample_identifier; source fields excluded from value equality. |
| dataset_sample alternative | Original dataset object’s dataset_key and its sample_links[sample_index] three identity fields. The qualified source pointer targets that actual sample array element; receipt also retains dataset_pointer/sample_index to authenticate the dataset join. |

A fixed extractor returns only these typed fields; it does not evaluate arbitrary
field maps, transform identifiers, parse prose or infer joins. Reject missing or
conflicting values. JSON array indices are canonical nonnegative decimals;
escaped names use RFC6901 rules. No JSON-pointer alias or relative-path matching.
Every nested provenance slot must be authenticated, including read/reference
identity source fields. The pure 662 validator still validates every resulting
shape and relationship; it does not substitute for these byte checks.

Selected metadata provenance uses the **actual captured artifact ID** as
`source_ref`, with its real JSON pointer, following the existing additional-BLAST
retained-catalog convention. Its namespace is artifact, not source. The primary
and supporting `DatabaseBinding.source_ref` instead use the real
`capture.source_ref`, identifying the sealed original selection. The manifest’s
original declared provenance remains in the captured manifest; do not copy an
unauthenticated old source string into the new binding.

### Dependency equality

Convert each DependencyRequest to the exact common DATABASE_DEPENDENCY_SCHEMA
by resolving list_ref to its captured occurrence ID and removing declaration.
All existing 003/core constraints still apply. Additionally:

* `source=db` and request declaration must match an actual selected operation
  token/bound path. This proves original selection, not an alias edge.
* File sources require a real selected list descriptor and exact original
  token at list_entry_ordinal, according to its declared grammar. For the
  operation dbs_file, use vdb_whitespace_tokens and compare the entire ordered
  list, selection values and bound paths. `vdblist_file`/`dblist_file` are the
  common result source names; do not add `dbs_file` to the core schema.
* `dblist`/`vdblist` with alias_directive use the existing alias parser’s exact
  selected row/token and corresponding DBLIST/VDBLIST directive. The file is a
  selected manifest member. No alias token initiates acquisition.
* A selected_json declaration points to an original object with exact role,
  ordinal, database_key, native_path_index, native_reference, source and
  list_entry_ordinal. For file sources the independent list-byte check is still
  mandatory. This supports explicitly supplied metadata declarations, including
  num_volumes, without pretending that a path report reconstructed them.
* Request declaration is permitted for file sources only in addition to the
  list-byte check. Non-file dblist/vdblist/num_volumes claims require selected
  alias/JSON evidence; they are not synthesized from guessed filenames.

Preserve duplicate tokens/independent selection occurrences. If the same file
belongs to different explicitly selected operands, distinct selection keys and
occurrence IDs preserve those roles; Store bytes may deduplicate. Dependency
binding occurrence-ID sets remain disjoint, as core 662 requires. Unmatched
native paths stay unmatched. No parser-discovered path becomes a grant, input,
database binding, dependency declaration or follow-up action.

## 4. Qualification, authentication receipt and publication handoff

New context module public ports:

```python
validate_vdb_utility_context_request(value: dict, *, job: dict) -> dict
vdb_utility_context_request_schema() -> dict
vdb_utility_database_operands(job: dict) -> list[dict]
vdb_utility_document_selections(job: dict) -> list[dict]
qualify_vdb_utility_context(capture: dict, *, base_context: dict) -> dict
authenticate_vdb_utility_context(
    capture: dict, *, context: dict, contents_by_occurrence: dict[str, bytes]
) -> dict  # ContextAuthentication below; raises typed ContractError on conflict
validate_vdb_context_authentication(
    value: dict, *, capture: dict, context: dict
) -> dict  # pure receipt validation, no Store or document reads
```

`vdb_utility_database_operands` returns primary followed by declared supporting
operands in request order. `vdb_utility_document_selections` returns exact
selected catalog addresses and expected selection keys, not paths discovered
from bytes. The two functions let producer/capture and worker share selection
meaning without importing the result worker into execution.

Fixed internal extractor signatures are
`extract_vdb_dataset_claim(record: dict) -> dict`,
`extract_vdb_member_claim(record: dict) -> dict`,
`extract_vdb_identity_claim(record: dict) -> dict`,
`extract_vdb_read_identity_claim(record: dict) -> dict`,
`extract_vdb_reference_identity_claim(record: dict) -> dict`,
`extract_vdb_sample_claim(record: dict) -> dict`, and
`extract_vdb_dataset_sample_claim(record: dict, *, sample_index: int) -> dict`.
Their input/output keys are exactly the table above; original records may have
other keys, outputs may not. They are byte-claim extraction, not scientific
calculators. Keep them in the context module; reuse standard finite JSON and
pointer handling rather than importing `_vdb_units` with a fake search key.

Keep `qualified_utility_context(capture)` public and pure. Its v3 return has
exactly these keys:

```text
{operation, native_outcome, occurrences, database_binding, failures,
 operation_input_occurrences, vdb_context}
```

It first performs existing selection/capture identity checks, then calls the
qualifier. This produces a **claimed, structurally qualified** context; it is
not permission to publish metadata. Authenticate the actual Store capture in
publication as today, and actual retained bytes in original bounded parsing.

Occurrence construction is deterministic and preserves v1/v2 historical IDs:
for v3 operation-input rows use existing input_key; for every other row use
`native_blast_utility_occurrence_` plus `native_blast_digest` of the original
bundle identity and the complete tuple `{direction,input_key,database_key,role,
ordinal,original_path}`, with explicit null keys. This is the existing v2
algorithm extended to v3. The receipt occurrence likewise uses explicit null
input/database keys. Assign direction/role ordinals from the full selected
population before capture, preserving gaps when a selected file is missing.
Do not compact them to the surviving artifact population.

Bindings use the actual captured rows for their selected operand; only matched
retained originals enter occurrence_ids. Independent operation inputs retain
operation order and do not enter database membership. A missing occurrence
needed to qualify the selected context yields a specific unavailable result;
its absence cannot be filled with a synthetic descriptor or source.

Worker plan v1 remains unchanged and validated exactly. Introduce
`native_blast_utility_result_worker_plan_v2` only for VDB. `parse_original` has
the same exact key set as v1:

```text
{version,task:"parse_original",directory,context,files,capture,bundle_file}
```

Files are the existing ordered `{occurrence_id,path,sha256,size_bytes}` list,
one per qualified occurrence. `bundle_file` is the existing retained descriptor.
All selected JSON/list/alias bytes needed for authentication are already among
these selected occurrences; no new worker filesystem authority is added.
The worker hashes all files, checks the actual bundle against capture, checks
manifest bytes against embedded manifests, reads declared JSON/list/alias
documents, and authenticates every provenance slot before calling a VDB parser.

For v3, `_can_read_result` requires captured stdout **and** stderr plus a
qualifiable context. Call 663 with:

```python
parse_blast_vdb_extraction(  # or parse_blast_vdb_inspection
    stdout_bytes, occurrence=stdout_occurrence, operation=context["operation"],
    database_binding=context["database_binding"], outcome=context["native_outcome"],
    operation_input_occurrences=context["operation_input_occurrences"],
    vdb_context=context["vdb_context"], stderr_contents=stderr_bytes,
    stderr_occurrence=stderr_occurrence)
```

Use common result output filename `result.json`. Output schemas/calculations
are core 662’s exact extraction v2 / inspection v3. No new scientific family,
scoring sheet or parsing model is added.

### Exact manifest-v2 shape

Do not relax manifest-v1’s key set/version or alter historical files. A v2 plan
produces this exact closed manifest:

```text
{
 version:"native_blast_utility_result_worker_manifest_v2",
 task:"parse_original"|"project_saved", plan_sha256:SHA256,
 completed:boolean,
 outputs:{result?:ExistingOutputDescriptor, projection?:ExistingOutputDescriptor},
 failures:[existing UtilityFailure],
 context_authentication:ContextAuthentication|null
}
ExistingOutputDescriptor = {filename,sha256,size_bytes}  # exact existing type
ContextAuthentication = {
 version:"native_blast_vdb_context_authentication_v1",
 passed:true,
 bundle_artifact_ref:actual artifact ID,
 request_sha256:SHA256, context_sha256:SHA256,
 documents:[{document_key,selection,occurrence_id,artifact_ref,sha256,size_bytes}],
 provenance:[{context_pointer,origin,source_ref,
              source_namespace:"source"|"artifact",pointer}],
 lists:[{occurrence_id,grammar,sha256,size_bytes,
         entries:[{ordinal,line_number,token_ordinal,byte_start,byte_end,value}]}],
 dependencies:[{ordinal,declaration,list_occurrence_id}]
}
```

`?` on outputs means only the indicated allowed key may be absent; no arbitrary
role. Parse-original outputs are empty or exactly result; project-saved outputs
are exactly projection when completed. `context_pointer` is the exact RFC6901
location of a source/provenance object in the full qualified context. `origin`
is the original Origin/SampleOrigin object, not unrestricted prose. Documents
are in original documents order. Provenance rows follow source_inputs, entry
bindings, member provenance then nested read/reference provenance, and sample
links in original array order. Lists follow operation database_list, operation
entry_batch, then declared database_lists order; deduplicate only an identical
selected occurrence. Database-list grammar is as selected; entry-batch grammar
is `vdb_entry_lines`. Byte ranges are half-open UTF-8 byte spans; line_number is
one-based, token_ordinal is zero-based within that physical line. Dependencies
follow declared_dependencies order and retain the original declaration object.

`request_sha256 = native_blast_digest(capture.plan.requested_job)`;
`context_sha256 = native_blast_digest(context)`. The provenance array includes
every qualified provenance slot, not just metadata-backed rows. The pure receipt
validator reconstructs the exact document/provenance/dependency identities and
expected list values from original selection, checks every source namespace and
pointer, and validates list positions/counts. It does not pretend to reread
metadata bytes or re-prove the comparisons: their completed execution is bound
by the existing immutable worker receipt and original plan/output identities.

Authentication is null until all checks pass. On an authentication failure,
record `supplied_binding_conflict`, `input_identity_mismatch`,
`input_population_unavailable` or `semantic_validation_unavailable` as
appropriate, retain diagnostics in the existing worker receipt, leave no result
output, and keep completed false. No partially authenticated scientific context
is projected. Raw captured streams and all valid other artifacts remain usable
for explicitly selected repair. Authentication true plus a nonzero native exit
still permits a parsed result with valid rows and explicit native failure.

For `project_saved`, v2 plan retains existing keys and adds exactly
`context_authentication`, copied from the authenticated original parse receipt.
Its `files` keys remain result/prepared_database/prepared_manifest (the latter
two null for VDB). Context authentication is null only for an unavailable-result
view, with result file null. A successful saved projection copies the same
authentication object into its v2 manifest; it does not run the authentication
extractors, native readers or helper.

### No new authentication artifact or prepared version

Keep `native_blast_utility_prepared_v1`, retained-v1 and worker-receipt-v1 exact
outer key sets. The existing `worker_receipt_artifact_ref` already retains the
original plan, manifest, outputs, diagnostics and execution result. Its nested
manifest version now dispatches exactly to v1 or v2. A separate authentication
artifact or prepared version would duplicate that existing capability.

`validate_prepared_utility_result` must validate v3’s original receipt and
non-null passed context authentication whenever result_artifact_ref exists,
including exact capture/request/context/output identities. `_projection_context`
may reconstruct the same pure expected context from capture, but cannot turn a
null/failed authentication into trusted metadata. No selected metadata file is
decoded during this retained validation or saved-only replay.

View-owner signatures are `project_blast_utility_result(..., context=None)` and
`validate_blast_utility_projection(..., context=None)`, with full qualified
context mandatory on a VDB path. Selector validation retains its existing
`(..., *, operation)` signature. Shared pure result validation still runs when
projecting; its shared sequence-symbol validation is not a competing calculator.
Projection copies established values, never replaces numbers. Without a parsed
authenticated result, views may expose explicitly requested retained artifacts
and failures but no VDB identity/context facts. 665 owns its exact selector and
return version schemas.

## 5. Applied offline resource mechanism

Use one explicitly selected bwrap wrapper inside the existing local durable
producer. No general sandbox framework, acquisition path or second native run.
Strace remains verification instrumentation, not a production dependency.

```text
OfflineExecution = {
 version:"native_blast_vdb_offline_execution_v1",
 launcher:{path:absolute,sha256:SHA256,size_bytes:int>=0},
 runtime_files:[{path:absolute,sha256:SHA256,size_bytes:int>=0}],
 runtime_aliases:[{path:absolute,target_path:absolute}],
 system_interface_profile:"blast_vdb_bwrap_local_v1"
}
OfflineEnvironment = {
 NCBI_VDB_CONFIG: selected primary manifest offline_configuration.path,
 BLAST_USAGE_REPORT:"false", NCBI_USAGE_REPORT_ENABLED:"false",
 DO_NOT_TRACK:"1", LC_ALL:"C"
}
```

Runtime files are the explicitly pinned helper/loader/library/cache closure,
including launcher runtime dependencies as needed. Alias targets must name one
of those exact regular runtime files; duplicate/conflicting mount destinations,
data-path overlap, symlink traversal and paths escaping the selected closure are
rejected. These are runtime links, not VDB source aliases. Driver verifies every
selected runtime identity before and after. The configuration file is the
selected/captured database sidecar, not a guessed home configuration. No HOME,
credentials, proxy, resolver/download or arbitrary environment passthrough.
The selected helper executable must itself occur in runtime_files with the
software descriptor's exact path/hash; the launcher descriptor is measured too.
Receipt runtime_files are launcher first, then declared runtime_files in request
order, deduplicating only an identical path/identity.

`native_environment` adds the existing attempt-local TMPDIR/TMP/TEMP and
XDG_CACHE_HOME, plus producer-owned PWD equal to the attempt working directory.
Record this complete realized native environment. Launch bwrap with empty root,
`--unshare-user --unshare-pid --unshare-net --new-session --clearenv`, explicit
read-only binds for each selected native data/config/runtime file at its original
absolute path, explicit runtime aliases, staged operation files at their actual
staged absolute paths, and writable attempt tmp/cache/work locations only.
Directory VDB inputs are represented by empty destination directories plus their
complete selected file binds; do not mount an unchecked parent data directory.
Use `--proc /proc --dev /dev --chdir <attempt>` and explicit `--setenv` values.
After constructing the mount tree, use `--remount-ro /`: the installed man page
states that it makes that mount read-only without changing its child mounts.
This prevents writable empty-root paths from bypassing measured attempt scratch;
only the explicitly selected writable child mounts remain writable.
Do not bind the host root, home, whole repository, credentials, sockets, `/sys`,
arbitrary `/etc`, or broad `/usr/lib` trees. Mount destinations and writable
subtrees must be disjoint from original read-only identities.

Use bwrap’s documented `--json-status-fd` to record child creation and child exit
status in an attempt-local control file, passing that one FD explicitly. This is
a one-call process wrapper, not a polling loop. The installed bwrap man page
describes JSON-lines child-pid and exit-code records. That child-pid is expressed
in the namespace from which bwrap was launched, not necessarily the helper's PID
inside its new namespace, and is not a native dataset identity. Unknown status
fields are retained, not treated
as scientific evidence. No recorded child means native started=false and no
invented native return code. Child creation plus its exit record supplies the
attempt/return facts; do not claim this alone traces every successful exec/read.
Wrapper setup failure never masquerades as helper scientific completion.
In particular, a child-pid is launch-attempt evidence, not proof of a successful
helper exec. A positively identified wrapper exec failure records
`offline_child_exec_failed`, mapped to `native_start_failed`; retain the raw
wrapper/child exit code in the execution receipt and do not report it as a
confirmed helper returncode. Ambiguous setup/exec observations remain qualified
unavailable. Normal command completion requires a matching normal status/exit
and no wrapper failure, not merely child creation. Preserve existing native
failure/partial-output semantics when the actual helper outcome is established.
No new exec-tracing framework is required for this distinction.

New execution helper ports:

```python
validate_vdb_offline_execution(value: dict, *, job: dict) -> dict
compile_vdb_offline_argv(job: dict, *, attempt_directory: str,
                         native_argv: list[str], status_fd: int) -> list[str]
run_vdb_offline_once(job: dict, *, attempt_directory: str,
                     native_argv: list[str], stdout, stderr) -> dict
```

The last port returns a closed execution receipt, not a new result family:

```text
{version:"native_blast_vdb_offline_receipt_v1", launcher_argv:[str],
 status_fd:int>=0, status_records:[finite JSON object],
 launcher_returncode:int|null, child_pid:int>=1|null, child_exit_code:int|null,
 runtime_files:[{path,expected_sha256,expected_size_bytes,
                 before_sha256,before_size_bytes,final_sha256,final_size_bytes}],
 failures:[existing producer failure rows with the conditional v3 codes below]}
```

Persist it as the required conditional `offline_execution` field in a v3 bundle;
old bundle key sets stay exact. Managed stdout/stderr remain the only native
outputs. Existing bundle receipt capture retains this control receipt; no extra
scientific artifact role. `realized_argv` continues to mean the actual helper
argv, while launcher_argv records the wrapper command separately.
Conditional v3 producer codes are `offline_launcher_unavailable`,
`offline_runtime_identity_mismatch`, `offline_setup_failed`,
`offline_status_unavailable`, `offline_configuration_conflict`,
`offline_child_exec_failed`; map them into
existing typed dependency/input/start/semantic-validation failure meanings with
original diagnostics retained. Never retry after a wrapper or status failure.

The profile prospectively accounts for the 661-observed `/proc/filesystems`,
`/proc/stat`, the helper’s **own namespace PID** loginuid, eventfd synchronization
and local NETLINK_ROUTE acknowledgments. These are system interfaces, not
scientific-data downloads. `--proc` exposes the private PID namespace’s procfs;
this small mechanism does not claim per-proc-path syscall enforcement. The
network namespace prevents use of host network connectivity; do not claim that
failed NSCD attempts or local kernel acknowledgments are remote content. Exact
read auditing belongs to the prospective verification trace, not an invented
production allowlist success.

Apply the actual established local allocation: 20 GiB memory, 4 GiB scratch,
zero swap, no wall cap. All staging, writable cache/tmp, logs and outputs count
under that scratch allocation. Preserve its documented monitored-allocation /
per-file-limit limitations; do not call it a filesystem quota. No local database
BLAST search is added. API/HPC are not substitutes for this selected local
operation. An independently selected future Aurora binding requires real access
and project-storage paths plus EpiCalib charging, not a copied local claim.

## 6. Capture, failures, replay, credit and continuation

Extend `database_file_selections` to enumerate primary then supporting operands,
using existing manifest/receipt/metadata/input-manifest/config roles and stable
selection keys. Every selected original scientific/config file is pinned before
execution and after closure. A v3 VDB binary file is format unknown unless an
actual more specific format is selected; do not label it blastdb_binary.
Runtime identities are execution controls in the sealed bundle; scientific
context documents remain ordinary selected captured occurrences.

Reuse capture-v1 and source_payload. Capture creates the real
episode.execution_result source only after sealed-bundle validation and records
the actual auxiliary artifact IDs. Parent job construction cannot know that
source ID. Validate non-null originally selected references against actual
received records before launch; never seed known references with a previous run
or create a fake initial baseline. Captured metadata artifacts used in provenance
do not become delivered artifact grants. 665’s typed source/artifact/occurrence
namespaces must distinguish them at every return boundary.

Preserve 638/658 captured-bytes completeness: new v3 bundles require
`output_completeness_basis=captured_bytes`; a closed fully inventoried stream can
be complete while native exit is nonzero and its biological result incomplete.
No native return-code shortcut relabels it partial. Native stdout may yield
valid partial rows alongside diagnostics; 663/common validators preserve those
rows and original malformed-row ordinals. Missing, zero, failed, truncated and
incompatible remain distinct.

Existing attempt/worker intents are immutable. Replaying a sealed native attempt
does not run the helper again. Replaying a successful original parse validates
its saved outputs; saved projection never reads original native/metadata data.
Unsealed uncertain work is retained as uncertain, not automatically rerun.
Preserve 659: an explicitly selected later collection may repair unavailable
parsing from the same retained bundle; it does not rerun the native helper or
reacquire files. Earlier unavailable receipts/history remain facts. New parsed
facts may supersede unavailable current views without rewriting old observations.

One native bundle acquisition contributes once through existing credit_view.
Metadata parsing, receipt construction, view selection and repeated delivery add
no new scientific/acquisition contribution. Successful delivery of the original
typed requested view uses the ordinary practical-completion path: preserve final
actual gain, set future expected credit to exact zero immediately, and use the
configured controller. No extra zero turn, success score, model-composed report
or scientific acceptance gate is added.

## 7. Authentic evidence and required verification

658 acquired one archive (35,175 bytes, SHA256
266e59ba8a5033a084ddb95ab4518fe1c2e71a96e1fc20bb0b959a88c15567d7)
and independent FASTA (6,442 bytes, SHA256
165c749d742d0436d0482139fa0d734f7c4fdc7d9b428e73efaacaac416a97c8).
The supplied archive is a first-ten-spots fixture, not a complete run. The
offline configuration is 201 bytes, SHA256
ab65e06f45d7b49f187f3f79f963e909b8b20e2e2aa2d46b416cc40a9fe2c8fd.

661 performed exactly one strace+bwrap helper invocation. `.1.1` and `.1.2` each
returned 250 bases equal to their independent companion sequences. The helper
returned zero; configuration use included the 201-byte readable mmap, and a
network namespace was observed. Ordinary scientific/config/runtime file reads
matched before pins; no remote content was observed. The original check failed
postprocessing because C-octal `002` was passed to int(token,0); saved-only 121b
passed without another helper invocation. Wrapper wait fields left unknown by
that failure remain unknown.

The initial closure result remains **false**: retain all 22 initially undeclared
proc/local-IPC events. Do not retroactively change that allowlist. A new profile
can explicitly select the observed interfaces prospectively. Neither 661 nor
this plan establishes a production resource binding or a completed tool.

Controlled verification to implement under the established bounded check service
(20 GiB / 4 GiB / zero swap / no wall cap), never host application imports/tests:

1. All seven variants with both db/dbs_file forms; exact argv/env, duplicate
   selections, batch/list bytes, prohibited classic flags, unchanged path maps.
2. Exact pre-662 native schema compatibility and semantic v1/v2 rejection of
   VDB; actual saved classic/preparation artifacts unchanged.
3. Real capture-ID qualification from a newly created controlled Store; no
   prior source IDs or fake initial refs. Wrong document index/hash, missing
   manifest, forged pointer, nested provenance mismatch, source-vs-artifact
   namespace confusion and undeclared references must fail specifically.
4. Direct parent declarations versus selected JSON facts; fixed existing
   additional-BLAST dataset/member/sample layouts; conflicting sample links;
   missing identities remain unknown. Metadata provenance never grants bytes.
5. Database-side lists with actual captured descriptors, repeated token positions,
   dependency key/index mismatches, alias directive equality, metadata-backed
   declarations, unmatched bare native paths and attempted discovery grants.
6. Wrapper setup failure before child, child nonzero, missing status, changed
   runtime/config/input bytes, output truncation, scratch failure and sealed
   replay. Preserve all usable captured output and distinct attempt facts.
7. Successful metadata authentication recorded in manifest-v2 and unchanged
   manifest-v1 validation; saved publication/replay with metadata readers patched
   to fail; later selected 659 repair with no native rerun/new acquisition credit.
8. Complete typed child result delivery, source/artifact/occurrence permissions,
   parent receipt validation and ordinary exact-zero terminal behavior, using
   665’s exact requested-return cases. Pure parser or compiler tests do not prove
   this integrated path.

Before runtime exposure, the concrete missing facts are verification results,
not user design decisions: a real common prepared manifest/receipt for the
actually selected 658 fixture; applied production bwrap layout with exact runtime
aliases/config at original paths and status-FD behavior; live bounded lifecycle,
capture, worker authentication and requested typed return; prospective trace
closure under the newly declared interface profile. Other modes/source forms,
filtered reads, CSRA references, WGS and alias/accession mapping retain separately
named authentic fixture dependencies. No arbitrary download/credential is
authorized to fill them. Until these are measured, keep exposure claims narrow.

Read the original goal’s objective and entire OPERATING PRINCIPLES verbatim after
each tool/substantial read. Reread 643/001–003 and this port before declaring an
assigned coding boundary complete. Report controlled versus authentic evidence
separately and name unverified integration/resource facts.
