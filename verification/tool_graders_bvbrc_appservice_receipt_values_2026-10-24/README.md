# AppService support receipt values and effect confirmation

Component implementation, 2026-10-24. This workload owns only
`gene_annotation_episode/bvbrc_appservice_receipt_values.py`,
`tests/test_bvbrc_appservice_receipt_values.py`, and this verification directory.
It supplies the two frozen pure functions in the host-parts contract. It does
not acquire data, access a Store, publish sources, select work, retry, create an
episode, generate a controller observation, or calculate scientific credit.

## Authority and inspection

The complete immutable attachment was read from
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`.
Its SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The objective and all sixteen design principles were reread verbatim after
native consumer study and before implementation. The final handoff records
another authority and current-contract reread.

Inspected instructions and contracts: AGENTS.md; GOAL.md; the complete episode
structure and time-aware estimation documents; the practical execution document
and its original additive contract; the permanent tool-grader direction record;
the existing BV-BRC service inventory rows; and the complete original AppService
execution proposal, resolved service-input addendum, and host-parts contract.
These remain authoritative records and were not edited by this workload.

Inspected complete affected implementations: C1 `bvbrc_analysis_protocol.py`
and `bvbrc_analysis_transport.py`; C3 `bvbrc_application_definitions.py`; C4a
`bvbrc_appservice_contracts.py` and `bvbrc_appservice_readers.py`; the relevant
complete runtime schemas and their transitive contracts; the complete C4b
`api_bvbrc_appservice.py`; and the complete `api_selected_effects.py` journal.
The `SourceSnapshot` and Event definitions and existing service/journal tests
were also inspected. This is consumer/source-contract inspection, not a live
deployment or scientific-output claim.

## Implemented boundaries

`build_appservice_receipt(prepared, event, snapshot, *, common_receipt,
effect_receipts)` returns exactly `{contract, value, diagnostics}`. The value
validates against the named existing C4 contract. Supported projections are
CatalogReceipt, PreparationReceipt, WorkspaceReceipt, UploadReceipt,
TaskInfoReceipt, TaskObservation, CapabilityReceipt, and TaskHandoff. Native
failure without a stronger valid projection returns CommonReceipt with the
host-supplied identity, retained binding and specific diagnostics.

The host supplies the receipt construction reference and all actual source,
definition, input and effect references. The builder uses those values without
inventing identities or resolving custody. Root's persistence layer may replace
its own provisional construction reference with the real persisted source ID;
that codec is outside this module. Catalog definition extraction content stays
null until the host has actually retained it.

SnapshotBinding.selected_operands is exactly the host-frozen mapping of
`operation`, `request_sha256`, `arguments_sha256`, and `native_operands` from
PreparedOperation. The builder compares this mapping and actual response digest,
byte count, media type, timestamp and transport fields. Native call identity and
RPC correlation are checked before projecting or confirming native values.
The actual Event's HTTP status and body-completeness facts must also match the
snapshot: C4b emits them only after validating its configured endpoint and
request. Configuration is not duplicated in the prepared call or inferred from
an arbitrary matching response. Each journal payload digest is checked against
its exact prepared native operands and original selected target.

Workspace row pointers refer to the original native source: create/get use
`/result/0/<native index>`; ls uses the escaped original map key and original
local row index. A future ObjectSelection.row_pointer must match exactly one
WorkspaceReceipt.rows[].pointer. No implicit `/rows/N` association is created.
All rows and complete native arrays/maps survive malformed peers, wrong targets,
duplicates and native failures. Empty directory omission remains native absence.

`confirm_appservice_effects(prepared, event, snapshot, *, snapshot_binding,
effect_receipts)` returns the existing journal outcome-row shape. It confirms
create paths, upload nodes, submission acknowledgments and capability positions
only from correlated original response evidence. It preserves closed confirmed
and not_sent outcomes unchanged, including on replay without a snapshot. A
prepared_not_issued receipt requires the executor's issue/recovery path; this
pure function never manufactures that transition or a not_sent inference.

An acknowledged failed task confirms the submission effect and supplies no
usable handoff. The original submitted parameters are distinct from actual
scheduler-returned parameters and their exact source pointer. Effective producer
parameters remain absent until a separate acquired manifest supplies them.
Unknown state/timing is not replaced by a duration or scientific measurement.
Capability URL strings stay in internal CapabilityReceipts. A UUID-only object
keeps path null; task-info output never invents an output path.

## Numerical examples and verification meanings

The binary upload fixture is exactly seven bytes: `00 ff 41 43 47 54 0a`.
Its supplied SHA-256 is
`e2b6e5b6c9b10ec7b00ef38ae09acf7629ff38a30da4454ba162836c8d07d36d`.
The matching native file.size is 7 bytes and matching native sha256 produces
`accepted_bytes_match`. An additional native checksum algorithm is retained
without pretending to have checked it. Sizes 0 and 6 are not accepted for this
input. A node without file metadata does not confirm an upload. A deliberately
empty input can be confirmed with native size 0 and the actual empty-byte
SHA-256; an empty initial node with no checksum remains unknown.

A two-target create fixture returns one ancestor and two targets in reverse
target order. The first target binds native pointer `/result/0/2`, the second
`/result/0/1`; neither uses positional target matching. When the second target
is malformed, wrong-path, wrong-type, duplicated or explicitly failed, only the
first effect confirms and original missing index 1 remains visible.

The native SQL elapsed-time fixture `00:01:03` and missing-time sentinel
`0000-00-00 00:00:00` remain unchanged strings. No queue, runtime or turnaround
seconds are invented. These are support validation examples, not scientific
measurements or annotation scores.

The focused tests use the real C4b preparation/decoding path, existing C1/C3/C4a
readers/contracts, and real passive SelectedAPIEffects persistence. Socket entry
points are forbidden. All native responses are synthetic fixtures. Tests cover
positive and partial batches, exact target/UUID identity, original pointers,
complete fields, task-info bytes, input and response corruption, RPC/HTTP native
errors, absent response, upload counts/checksums, confirmed versus usable
handoff, immutable supplied inputs, and byte-identical closed journal replay.

`pytest.txt` records the corrected main run: **55 passed in 180.48 seconds**.
`pytest_additional.txt` records the later UUID-only-object and failed-host-receipt
cases: **2 passed, 55 deselected in 8.60 seconds**. The final suite run is retained
separately; overlapping runs must not be summed as independent coverage.

The expanded full run in `pytest_payload_binding.txt` passed **61 tests in
192.59 seconds**, including four changed-native-operand counterexamples.
`pytest_missing_response.txt` passed **3 tests in 13.38 seconds** after making
the missing-response failure code exactly `issued_effect_unknown`.
`pytest_qualification.txt` passed **8 tests in 26.06 seconds** after retaining
missing native echo qualifications. The final endpoint-binding run adds one
further counterexample and tests all cases together.

The final unchanged production code passed **62 tests in 142.20 seconds** using
`.venv/bin/python -m pytest -q tests/test_bvbrc_appservice_receipt_values.py`.
The complete output is `pytest_endpoint_binding.txt`. All tests remain synthetic;
this number is not added to earlier overlapping runs. The immutable objective,
entire sixteen-principle block, and exact native-support receipt contract were
reread verbatim immediately before final handoff. `FINAL_RECORD.json` identifies
the delivered files and retained test output by SHA-256.

An earlier development run had 45 passes and seven fixture-construction
failures because the test used WorkspaceTarget.role instead of the existing
WorkspaceTarget.purpose field. Correcting that test field enabled the create
cases; no production schema was changed to accommodate the fixture.

## Remaining integration and evidence

Root owns actual source retention, authenticated custody, input binding,
transport/recovery, receipt publication, requested typed return, credit and
continuation wiring. Download AcquisitionReceipt/bundle/scientific publication
is also root-owned. This component does not prove those complete episode paths.
No live BV-BRC request, native service output, HPC work, local database BLAST,
NCBI verification, literature processing, W05 work, or model prompt change was
performed. The original service inventory rows are unchanged and unfinished
scientific graders are not represented as completed by these support tests.
