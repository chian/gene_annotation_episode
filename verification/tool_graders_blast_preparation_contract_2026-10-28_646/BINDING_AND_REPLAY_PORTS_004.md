# Selected bindings and historical forms

These are implementation interfaces for the existing nine preparation modes.
The original user-entered goal remains authoritative, with the two formatter
utilities excluded by the user's later instruction. No goal or scope is changed.

## Tool-information owner651

Exclusive files: native_blast_utility_tool_info.py,
tests/test_blast_preparation_tool_info_651.py and verification directory651.
Root owns the practical execution consumer. No runtime TASK/STEERING changes.

Legacy binding rows keep exactly program,mode,software,molecules. New pairs
require one additional `variants` field, a nonempty unique array of closed
records. A configured program is not permission to expose every mode/variant.

* convert_gi_list, inspect_seqid_list, aggregate_volumes, show_filters: {}.
* convert_seqid_list: {database_binding: unbound|bound}.
* create_subset_alias: {restriction_kind: gi_list|seqid_list|taxid_list|oid_masks,
  input_format: text|gi_list_binary|seqid_list_binary|null}. Only combinations in
  the shared restriction schema are legal; oid_masks uses null.
* aggregate_databases: {classic_source: null|inline|file,
  vdb_source: null|inline|file}, with at least one source nonnull.
* create_megablast_index: {input_format: fasta|blastdb,
  old_style_index: boolean, legacy: boolean}. Preserve the shared operation's
  legal combinations; the new-style path requires blastdb input.
* create_profile_database: {profile_type: rps|delta|cobalt,
  input_format: pssm_asn1_text|pssm_asn1_binary}.

Allow unknown molecule only for the identifier list modes; otherwise preserve
the shared operation's exact molecule constraints. Validate finite strict JSON
types and reject duplicate rows/variants, unknown keys and invented defaults.

Add the pure port
`native_blast_utility_binding_accepts_job(binding: dict, job: dict) -> bool`.
It validates the binding and job and checks exact program/mode/software/molecule
and selected variant membership. The returned tool's request schema constrains
the same choices. Factor those constraints once so descriptor and runtime do
not implement different policies. Root uses this port in the existing practical
binding check. Do not perform installation checks, acquisition or execution.

Tool information gives name, description, local resource and substantive
instructions for the actual selected operation. Explain original vs staged
lists, explicit dependencies, native diagnostics, failed partial products and
requested outputs where relevant. Native counts do not become annotation
scores. A VDB selection still needs the actual existing offline closure; the
descriptor does not establish that closure. Do not fabricate resource bindings.

Tests cover every pair and variant; descriptor and acceptance parity; unknown
and mixed bindings; unchanged legacy descriptors; invalid combinations; exact
software/molecule; missing variants. Run in bounded529, check110_tool_info651.

## Historical-form owner652

Exclusive files: communication.py, a new
blast_utility_historical_fact_schemas.py, tests/test_blast_utility_historical_forms_652.py
and verification directory652. Current result views and numerical validation
remain shared existing authorities. Root owns returns and integration.

The defect is exact comparison of every saved parent schema against only the
current expanded utility schema. Preserve exact acceptance of the historical
registered forms from the sealed check101_mask_conversion_workflow snapshot,
alongside current registered forms. Do not accept arbitrary narrower schemas,
weaken closed forms, rewrite saved requests or infer a historical schema from
an untrusted caller. Retain the original x-source and top-level-only restriction.

Create a pure frozen registry with detached copies of the actual prior registered
schemas, recording their source hash. Use the bounded runner to extract or test
application schemas; host stdlib source/hash inspection is permitted. Runtime
must not import a verification snapshot or execute historical source text.
Communication checks exact equality with either registered version. Existing
value and reference validation still applies. Verify saved legacy forms through
the actual NativeBLASTUtilityReturns._values path, new forms, mutation rejection,
nested x-source rejection and source mismatch. If a different consumer rejects
these unchanged values, report its exact location to root before editing it.

Use bounded529 check111_historical652. No native reruns or prompt edits.

## Shared verification discipline

Both owners read the user attachment in full and the646 contracts before coding.
Read complete affected consumers. All application imports/tests use bounded529:
20 GiB RAM,4 GiB scratch,zero swap,no wall cap. After each tool/substantial
external/native read, reread the goal objective and ENTIRE operating principles
verbatim from the original attachment. Reread this contract before reporting.
Descriptors and schema tests do not establish full Workflow or live verification.
