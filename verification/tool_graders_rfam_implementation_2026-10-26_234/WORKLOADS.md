# Rfam implementation boundaries, 2026-10-26

This is an additive implementation plan for the existing fixed requirement
`A-L068-rfam-batch` and its API binding. It does not change the original goal,
the scientific meaning of the row, or its completion criteria. The authoritative
goal is `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
(SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`).

The exact representation, sheet, numerical definitions, failure codes, and
receiving forms are in `../tool_graders_rfam_contract_2026-10-26_232/CONTRACT.md`.
Read that complete contract and its source/example records. It supplies contracts,
not proof of implementation. The local Infernal graders and BLAST graders remain
separate implementations; neither accepts this remote JSON by relabeling it.

The previous status-only goal turn made no implementation progress. Root
revalidated the prepared Infernal checkpoint and applied it after review in this
turn: recorded numerical grader tally 71, with all fixed scope rows retained.
Rfam remains unfinished and is not included in that tally.

## Exclusive workloads and actual dependencies

1. **HTTP transport and deployed native formats.** Own only
   `gene_annotation_episode/rfam_batch_transport.py`,
   `tests/test_rfam_batch_transport.py`, and new evidence under
   `verification/tool_graders_rfam_transport_2026-10-26_234/`.
   Implement `RfamBatchHTTP(timeout_seconds=...)`, `submit(sequence)`,
   `submit_file(content: bytes, *, filename: str)`, `status(job_id)`, and
   `result(job_id, *, representation)` returning the existing `SourceSnapshot`.
   `submit` freezes the ASCII sequence plus one newline and delegates to one
   byte-preserving `submit_file` POST. File submission allows exact supplied
   multi-record FASTA without inventing its response schema. Do not interpret
   scientific input or output in transport. Each selected method performs at
   most one HTTP request, retains actual request/response bytes and headers,
   preserves partial response bytes, and never retries, redirects, waits, or
   polls. No response means an explicit `AcquisitionError` with honest uncertain
   submission status. Fixed official origin and original handle remain binding.
   Test with a controlled HTTP opener/loopback, including duplicate headers,
   non-2xx responses, redirects, partial reads, missing response, invalid handles,
   replay-independent pure transport inputs, and exact multipart bytes.
   Then make explicitly selected tiny public-sequence single and multi-query
   native submissions, retaining each action separately. A multi-query fixture
   should include an occurrence repeated under another header to expose native
   identity handling. Save handles immediately. Observe each existing handle;
   never restart because a result is pending or an observation times out. There
   is no automated polling loop, fixed cadence, or job wall-time cap. Acquire
   JSON, tblout, and out separately when useful. Handoff exact native bytes,
   status tokens, full input occurrences, and an additive batch-format contract
   for review. Real format discovery must not be postponed behind the single
   query implementation. No new posting of private biological data is authorized;
   use the official public 119 nt example and its disclosed transformations.

2. **Native JSON sheet, numerical calculator, and selected view.** Own only
   `gene_annotation_episode/rfam_batch_contracts.py`,
   `gene_annotation_episode/rfam_batch_inputs.py`,
   `gene_annotation_episode/rfam_batch_grader.py`,
   `gene_annotation_episode/rfam_batch_views.py`, corresponding new tests, and
   new evidence under `verification/tool_graders_rfam_numerical_2026-10-26_235/`.
   Implement the exact `populate_rfam_batch_json_sheet`,
   `calculate_rfam_batch_components`, and `project_rfam_batch_result` signatures
   and closed records in the reviewed contract. Native score, E-value and GC,
   attributed physical coordinates, query span/union/overlap, missing data,
   duplicates, and source-qualified model denominators have their explicit
   definitions there. Keep parser cells independent so an invalid optional
   display or numeric cell cannot erase other valid measurements. Reject
   contradictory original query/job attribution while retaining raw evidence.
   Consume optional exact-source alignment components from workload 3; do not
   implement a second alignment parser. The real batch envelope from workload 1
   will receive an additive contract before its production parser is added;
   until then unknown batch shapes are explicit unfinished work, not completed
   empty searches. Test the official source example, retained expired-job
   response, synthetic valid zero, partial, duplicate, conflicting, reverse,
   overlapping, malformed, metadata and projection cases. Verify recalculation
   from saved sheets with acquisition and execution forbidden. Populate a full
   numerical example; metadata-only records do not satisfy this workload.

3. **Displayed alignment correspondence.** Own only
   `gene_annotation_episode/rfam_batch_alignment.py`,
   `tests/test_rfam_batch_alignment.py`, and new evidence under
   `verification/tool_graders_rfam_alignment_2026-10-26_236/`.
   Implement `parse_rfam_alignment_display` and the exact supplied/result shapes
   in the contract, including the additive explicit identity/bundle fields.
   Read the actual Infernal display specification and producer evidence. Preserve
   physical query/model coordinates, reverse orientation, insertion/deletion,
   local-end/truncation shorthand, and actual posterior-bin meanings. Native
   omitted correspondence remains unknown; unimplemented grammar must be
   distinguished from information absent from the representation. Do not infer
   a full model length from displayed endpoints, use model consensus as a
   physical reference protein, or turn PP into annotation probability. Accept
   supplied data only; no acquisition in parsers. Test complete native display
   examples and explicitly labelled synthetic mutations. Handoff exact per-hit
   components keyed by source hash and original row; the sheet owner consumes
   them without independently sorted-list joins. Shared constants can be
   imported when delivered; no shared-file editing or runtime service dependency.

4. **Shared integration — root only.** Own new `api_rfam.py`,
   `rfam_batch_publication.py`, and `rfam_batch_returns.py`, and any necessary
   edits to the existing service/episode/tool-information consumers named in
   contract section 7. Read complete affected paths before editing. Connect
   actual supplied subject and original handoff to the selected API primitive,
   then original source custody, saved sheet/calculation, requested typed
   projection, and both receiving episode boundaries. No hidden provider-jobs
   lookup or synthetic legacy job registration. Preserve actual shared-loop
   action accounting, replay, continuation, and practical endpoint validation.
   Compatibility repairs must leave historical facts unchanged while removing
   the old compound Rfam search/collect route from new episode execution.

The parser's output contract, not completion of the transport workload, is the
calculator dependency. The exact alignment-component contract, not completion
of every display case, is the sheet dependency. Actual batch bytes are required
only to settle the batch-envelope parser and occurrence mapping. Independent
single-query numerical and transport code can therefore proceed concurrently.
The fixed Rfam requirement still includes the remaining batch/format work.

## Instructions applying to every workload

Read the complete authoritative goal first. After each tool and substantial
external/native-output study, reread its objective and ALL sixteen design
principles verbatim, then the current exact contract. Do not edit the authority,
permanent design records, earlier receipts, scope, or accounting. Source
documents and implementation tests are evidence, not new user requirements.

Preserve the existing episodes and three construction slots. Use deterministic
functions and supplied metadata; no LLM scientific grading, invented confidence,
new grading episode, resource substitution, private loop, additional turns, or
changed annotation scoring. Keep detailed TASK and terse receiver-specific
STEERING distinct. No new prompt template is settled without user feedback.

Run meaningful checks within the caller's 20 GiB RAM and 4 GiB scratch, with no
invented wall-time budget. Use the existing bounded verification runner pattern;
retain invocation, native files, source hashes, test output and exact limits.
Do not run local database BLAST or access HPC. Each workload reports inspected,
synthetic, retained-native, actual native and integrated verification separately,
plus exact unfinished work. Share contract discrepancies promptly rather than
silently changing an interface or narrowing the tool's required meaning.
