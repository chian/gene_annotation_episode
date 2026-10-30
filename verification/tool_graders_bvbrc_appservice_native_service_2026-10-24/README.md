# C4b native service component verification

This directory records the native service/tool-information component only.
Custody, selected-effect durability, shared episode execution, typed return,
credit, continuation and scientific adapters have separate owners and claims.
No live BV-BRC request, credential use, remote job, local database BLAST or NCBI
verification is performed here.

The complete C1 protocol, C3 preparation, native transport, APIServicePrimitive,
MinHash implementation and shared API executor were inspected. Selected native
submission/status/task-info producer paths were examined from pinned retained
source; source inspection does not establish a deployed service version.

Initial dependency check: `.venv/bin/python -m pytest -q
tests/test_bvbrc_analysis_protocol.py tests/test_bvbrc_application_definitions.py
tests/test_bvbrc_analysis_transport.py` passed **152 tests in 0.64 seconds**.
This is dependency regression evidence, not implementation of C4b or integrated
AppService capability.

The missing resolved-input boundary was recorded before production coding in
`docs/TOOL_GRADER_BVBRC_APPSERVICE_SERVICE_INPUTS_2026-10-24_001.md`.

Final component result: **73 passed in 60.88 seconds** in
`PYTEST_SERVICE_FINAL.txt`, using the command recorded in `TEST_COMMAND_FINAL.json`.
An earlier combined run passed **222 tests in 59.50 seconds**: 70 overlapping
component checks and 152 unchanged C1/C3/transport dependency checks. Do not add
overlapping test counts. The final component run includes the root's later
frozen `SnapshotBinding.selected_operands` clarification and three additional
Workspace-create/upload cases.

The tests cover all eleven selected operations, closed original arguments,
host-supplied resolved values, exact RPC envelopes, C3 errors/qualifications,
independent create/upload/submission/capability effect descriptors, metadata
batch partials and reordered ancestors, supplied-link create, empty upload-node
creation without reading/uploading bytes, actual local HTTP multipart upload,
task identity and parameter conflicts, native `_preflight` additions, actual
parameter-field pointers, source-declared container override precedence,
separate status/log observations, valid selected status amid invalid peers,
task-info UUIDs, capability null entries, 200/206/range/body qualifications,
strict upload duplicate-member rejection, frozen publication callback operands,
and four-field information with separate invocation contracts. Embedded JSON
Schema resource boundaries are also checked.

Concrete supporting examples asserted by the tests:

* Upload `00 ff 41 43 47 54 0a`: seven original bytes, matching native file size
  and SHA-256, `accepted_bytes_match`; one multipart PUT and no submission.
* Range `2..4` of a six-byte object: `cde`, three returned bytes, HTTP 206,
  body complete, object incomplete; one GET.
* The same selected range ignored by HTTP 200: `abcdef`, six retained bytes,
  `range_ignored` qualification, full object observed; no local truncation.
* Interrupted six-byte response containing `abc`: three retained bytes,
  `download_incomplete`, qualified bytes available for the same host publication.

These are deliberately synthetic native-format fixtures and controlled local
HTTP exchanges, not retained production BV-BRC outputs or biological evidence.
The service implements individual invocations; the host must still authenticate
commission/receipt custody, reserve and record actual effects, admit typed returns,
publish immutable bundles, and apply its existing credit/completion rules.
No completed scientific adapter, live-resource verification, durable replay,
or complete episode-path integration is claimed by this component directory.

Native constraints remain explicit: create cannot enforce prohibition of ancestor
creation; upload/Workspace/task effects lack a proved remote idempotency key;
native `_preflight`, scheduler/effective parameters and original submitted values
stay separate; task status strings do not provide numeric scientific runtime;
task-info returns signature-redacted bytes; Workspace identity alone proves no
immutable producer-byte version; source definitions do not prove deployment.
