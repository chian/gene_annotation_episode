# Additive Rfam retained-publication workload

A fresh worker owns only `gene_annotation_episode/rfam_batch_publication.py`,
`tests/test_rfam_batch_publication.py`, and new verification ending 239. Root
owns service/input construction, shared integration, the table projection and
authenticated episode return reader. Do not edit their files.

Read the complete original goal and its required principles, current AGENTS,
the original Rfam CONTRACT.md, BATCH_WORKLOAD_002.md and native batch contract.
Read complete relevant functions in tools.py, api_services.py, Store, current
rfam JSON parser/calculator/view/alignment modules and original BLAST sheet and
native-result publication examples. Source files/tests do not override the goal.

Implement the original publish_rfam_batch_result signature. Use the existing
publish_existing_acquisition helper for original-operation replay; supply
request AND selector in its arguments so a key cannot be replayed for a different
numerical selection. No acquisition, submission, polling or format substitution.
Validate the supplied original submission and result snapshot through the
existing service's prepared operands/decoder; no provider_jobs lookup.

Retain three separate data roles: original submission source; exact native
result source whose artifact is snapshot.content; and a derived grading source
whose parent_source_refs contain those two sources. This avoids cyclic identity
between a raw source and its sheet. Derived grading source provider is
`rfam_batch.grading`, origin tool, and artifact is a closed manifest:

```
{version: rfam_batch_retained_grading_v1,
 request, selector, source_ref, submission_source_ref, artifact_ref,
 input_identity, format, parse_ref, sheet_ref, calculation_ref,
 projection, projection_errors}
```

All refs are actual retained records/artifacts. parse_ref stores the full parser
outcome including mapping/issues; sheet_ref stores the actual numerical sheet;
calculation_ref stores the separate calculation. Both latter refs are null for
identity-rejected/unsupported scientific output. Full native bytes are retained
even then. The result has the original eight fields plus `grading_source_ref`:
{source_ref, submission_source_ref, artifact_ref, format, sheet_ref,
calculation_ref, projection, projection_errors, grading_source_ref}.
record_refs include all three source records, not artifact IDs. No fake biological
reference, fabricated taxonomy/function or unrequested full-sheet observation is
created. Each native match remains an individually identified row of the full
saved sheet. The root return reader authenticates source lineage and emits only
requested typed rows; W05/annotation-scoring is outside this workload.

For JSON, construct the exact v1 input identity from snapshot.request.input_operand
and the actual original job/source. Parse once for validated original row keys,
parse each available alignment by exact source JSON pointer and query identity,
then supply the bound component bundle to the JSON parser. Preserve invalid
optional alignments without erasing native scalar cells. Save full sheet and
calculator output with explicit RFAM_CALCULATION_PARAMETERS; use the existing
pure project_rfam_batch_result with exact artifact digests. Metadata is optional,
explicitly supplied from the selected retained reference, never auto-acquired.
Do not use display endpoints as model length.

For a v2 sequence_batch request, input_operand is the file identity without
version/expected_job_id/submission_source_ref; it contains filename,
submitted_file_sha256, submitted_file_bytes, header_transform and queries.
Exact file bytes are in submission_snapshot.request.file_base64 and validated
against its hash/length. Append the three identity fields to call table238's
pure populate_rfam_batch_tblout_sheet. Root supplies the exact new table view:
`project_rfam_batch_table_result(parsed, calculation, *, projection,
artifact_bindings)`, returning rfam_selected_projection_v1 with the common
JSON metric vocabulary. Save the wrapper as parse_ref, Infernal sheet as
sheet_ref, and unchanged calculate_infernal_search_scores(...,
parameters={hit_scope:reported}) as calculation_ref. Do not alias a table to the
JSON calculator. Optional table bias/model-span/etc. remain in full saved data;
root's later selector extension can request them explicitly.

For batch JSON preserve its full unattributed artifact and explicit unavailable
projection; never associate its hit order with inputs. For single-request
tblout, preserve artifact-only until a source-qualified query-name mapping is
implemented; do not assume EMBOSS_001 universally. The out report is separately
retained artifact information; do not turn it into false JSON source pointers.
Requested artifact-only acquisition can complete without a scientific sheet.
A requested projection rejected for original query/job identity is partial.
Valid requested unavailable optional quantities remain a delivered typed result.
Internal parse issues alone do not make unknown full model length an execution
failure. projection_errors contains only failure to deliver requested fields,
using specific closed code/scope/hit_key/field/source_pointer records.

Verification: actual retained JSON through service inputs and real Store;
original submission lineage; same-key exact replay; changed selector rejection;
native numeric values and alignment arithmetic; complete empty, partial,
malformed, wrong query/job; all full artifacts retained; requested unavailable
model coverage is a valid return; complete batch table integration as table238
and root's pure view become available. No further live POSTs. Existing bounded
runner 20GiB/4GiB/no wall cap, separate native vs synthetic attribution.
Root handles end-to-end receiving episodes; do not claim that from publication
tests. Reread objective and all sixteen principles verbatim after substantial
native study and at closure, plus these exact contracts.

## Additive integration clarifications

The table calculator is now
`rfam_batch_table_grader.calculate_rfam_batch_table_components(parsed,
parameters={hit_scope:reported})`. Its closed result has version
rfam_batch_table_calculation_v1, sheet_digest, parse_digest, parameters,
native_calculation, hits, query_strands and population_complete.
native_calculation is the unchanged Infernal calculator result; the wrapper adds
original-input associations, explicit sum-span/overlap-excess calculations and
complete-empty versus incomplete-unknown query/strand populations. Save this
whole wrapper as calculation_ref. This supersedes the earlier direct-calculation
storage sentence without modifying the native calculation or removing evidence.
The view only selects saved fields; it does no score calculation. An unbound
foreign native row has query_occurrence_key=null and all common attributed
metrics unavailable/identity_rejected, with original numbers retained in the
native_calculation. It must never be assigned to the first input query.

model_metadata_ref selects a retained source record whose artifact is the closed
metadata bundle, not a direct artifact alias. Validate its actual referenced
sources and preserve that optional source in grading lineage. No implicit read
or acquisition occurs. The metadata is still unbound to native models when the
original release/digest is unknown.

Accurately delivered unavailable cells, including invalid native scalar cells,
and qualified partial populations do not themselves fail the practical endpoint.
Original attribution rejection, unsupported requested scientific format,
invalid selected keys and incomplete acquisition remain specific partial
outcomes. Table wrapper codes may be copied into closed projection_errors using
the union with the original Rfam code enum; line locators use line:<n>, never a
false JSON pointer. HTTP-200 incomplete result bodies are now eligible for
retained partial publication through the ordinary API path, with no new request.
