# BV-BRC AppService input-transfer Workflow verification

Scope: fixed goal rows C-L225-input-transfer, shared C-L221-preparation and
C-L222-submission, and their API bindings. This directory does not change the
goal or mark any live service verified.

Final result: **4 tests passed in 85.36 seconds**. They executed from root's
isolated repair candidate. Actual imported module locations and SHA-256 values
were checked before pytest. After root applied the byte-identical repair, all
299 non-bytecode candidate package source/data files were compared with the
production checkout and matched. This is an isolated-candidate execution with
byte-identical production package verification, not a second production run.
See `RESULTS.json`, `candidate/imported-source-provenance.json`, and
`candidate-production-byte-comparison.json`.

The new test is `tests/test_bvbrc_appservice_transfer_workflow.py`. Decisions,
parent/preparation continuation, caller input, and native responses are explicit
synthetic fixtures. The test executes the real shared Workflow, original
commissions, `material.parse`, custody, selected API effects, source/receipt
publication, native decoders, practical completion proof, and requested forms.
It does not execute BLAST, contact BV-BRC, launch HPC work, or call a configured
model. Transfer does not receive an annotation-confidence score.

The exact fixture input is 60 bytes:

```python
b">synthetic-query supplied transfer fixture\r\nacgtACGT\r\nNNtt\r\n"
```

Its SHA-256 is
`6701d489aa02847b9342fb89448b68f25dde8a5942ed8884e61d0b9d5376baa9`.
The real FASTA parser obtains one 12-nucleotide member. The upload selects the
retained original source's `artifact_ref`, so the original mixed case, header,
and CRLF bytes remain unchanged. Parser projections are not substituted for
the uploaded file.

The original native request uses `Homology`, `input_source=fasta_file`, and
`input_fasta_file=/synthetic//work/input.fa`. Its original WorkspaceTarget has
that same path. The selected native `Workspace.create` uses
`createUploadNodes=1`; the controlled response returns the equivalent path
`/synthetic/work/input.fa`, Workspace UUID
`11111111-1111-1111-1111-111111111111`, and Shock URL
`https://shock.example.invalid/node/22222222-2222-2222-2222-222222222222`.
The upload uses that exact returned node and original filename
`original-synthetic-query.fa`. The simulated native upload reply reports
60 bytes and the matching SHA-256. Submission retains the original preparation
and upload receipts, exact parameters, explicit start parameter
`parent_id=synthetic-parent-225`, selected resource `selected-api`, and native
task ID `225123`. The controlled task acknowledgment is queued; it is not a
scientific completion claim.

The scenario has four completed API selections: prepare, create, upload, and
submit. One additional selected submit intentionally passes the upload receipt
as `preparation_receipt_ref`. The actual binder rejects that wrong-kind receipt
with `appservice_receipt_contract_conflict` before a native submission. The
scripted child then explicitly selects the original preparation receipt. This
is a test choice, not a production retry rule or fixed itinerary.

The original upload stays valid after that rejected selection. The fixture
asserts no new native call, receipt, completion, or observation for the invalid
selection. The final task handoff belongs to submit, not create or upload.
Requested support receipts and the final handoff cross API → launch → parent
through real typed returns and custody checks.

Operational accounting uses the existing caller-selected handoff unit of 2.
Observed API marginal gains are `[0, 0, 0, 2]`; create/upload are not independent
scientific gains. The real practical estimator yielded exact future credit
zero on the final validated submission, without an extra zero observation.
The launch receives one own observation for its closed child. Parent and input
preparation continuation are explicitly controlled fixtures; API and launch
closure use production practical proofs and the ordinary controller comparison.

The replay test reconstructs `ExecutionServiceFactory` from retained
configuration, reopens Store and Workflow, forbids native calls and new provider
decisions, and replays the original completed actions and closed Workflow. It
compares the executor's retained `outcome.json` with the service replay result,
and independently compares the complete runtime action row, including its
additional `pending_work_after_action`. Tables, archives, receipts, source
bytes, and retained run JSON files must remain unchanged.

The successful run had 8 completed own observations and 9 decision calls across
the four episodes. Three support receipts and one task handoff reached the
parent. The actual reopened Store/Workflow replay passed with unchanged data,
zero new decisions, and zero new native calls. `candidate/retained-run/` holds
the complete exported run and `numerical-byte-example.json` the checkable
projection. Reopening occurred in the original run directory; moving the
exported directory and replaying it elsewhere was not tested.

## Inspected path

The immutable objective and all 16 principles, AGENTS.md, GOAL.md, episode,
estimation, practical, task/steering, grader-goal, service-input, host-parts, and
selected-effects contracts were read. Relevant current fixed rows were read
from `research/tool_grader_goal_2026-10-24/WORK_STATUS.json`; the older inventory
file remains historical.

Implementation inspection included the complete input binder (`_Inputs.input`,
`resolve`, `submit_inputs` and its receipt/definition/object dependencies),
`BVBRCAppServiceService`, AppService host, custody, records, receipt projections,
and selected-call executor. The actual Workflow selection, selected execution,
return admission, facts, observations, controller, and closure paths were read,
along with the consuming ExecutionEpisodes and API execution methods. The real
material parser and native task-ID/upload decoding contracts were inspected.
Existing direct-driver and full Workflow tests were read as setup examples;
their direct-driver coverage is not claimed as this Workflow proof.

## Retained failures

`pytest-initial.log` records an initial fixture defect: the deliberately
synthetic task label was not numeric. Native decoding retained
`invalid_task_field`, `missing_task_id`, and `original_task_mismatch` instead of
creating a false successful handoff. The original receipts and events are in
`initial-fixture-failure-records.json`. The fixture task ID was corrected to
numeric `225123`; no production behavior was bypassed.

`pytest-corrected-fixture.log` records a production return-boundary failure:
`received_report_fact_conflict` at `runtime.py:3458`. All four selected operations
had already published valid PreparationReceipt, WorkspaceReceipt, UploadReceipt,
and TaskHandoff records. `ExecutionEpisodes.received_report_facts` supplied
`bvbrc_appservice_support_refs` for `launch_api`, where the specialist's own facts
already supplied that source. The requested support form exposed the duplicate.
The complete failed run is in `support-return-conflict-retained-run/` and its
diagnostic is `support-return-conflict-diagnostic.json`. The transfer agent
reported the defect to root and made no production edits.

Root repaired forwarding in `ExecutionEpisodes.received_report_facts` so only
annotation/scientific-process receivers add these forwarded support facts;
execution-role owners already supply the facts through their own binding.
The four passing tests retain the original requested support-return contract.

Exact commands and final verification results are recorded separately in this
directory. Live authentication, deployed service versions, successful real
Workspace uploads/submissions, and scientific Homology results remain
unverified by this support-only test.
