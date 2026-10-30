# Correct the GenomeAlignment receipt inputs to the real host chain

The first real host test in worker160's `pytest_001` and retained failed run
shows two C mismatches. Actual task_info receipts have purpose `observation`;
the earlier synthetic fixtures and C checked `support`. Actual task_info_object
selection gives a UUID with unknown path/type. Acquiring a typed job_result
manifest therefore uses Workspace.get followed by an exact receipt_row
selection. C previously accepted only direct task_info_object selection for
the manifest. The numerical native measurements are unaffected, but valid
associations and observed invocation information were incorrectly unavailable.

Root owns this correction to C and the host collector. Preserve all historical
test/run receipts. Correct the synthetic log helper to `observation` so future
tests exercise the actual API contract, rather than relaxing production checks
to preserve the earlier incorrect fixture.

Extend the closed RetainedRecord contract with actual `WorkspaceReceipt` for
`api.bvbrc_appservice.workspace_metadata` / `Workspace.get` only. No new record
shape or provider-authored witness is introduced. Validate its canonical
envelope and native snapshot; exact selected native RPC, request, requested
objects and returned native value; reparse its native metadata rows using the
existing deterministic Workspace parser; compare the stored rows and missing
indices to those actual decoded rows. This is acquisition metadata extraction,
not a scientific score or a saved scientific-result replay operation.

For a manifest acquired through receipt_row, require that exact authenticated
WorkspaceReceipt and row pointer, the actual row's path/UUID/type and the
manifest's metadata_receipt_ref. Match the native metadata row to the originally
requested task_info_object through the native parser's request indices, never
by independently sorting or assuming returned row order. Require the linked
TaskInfoReceipt to name this original task's job_result_id and its exact UUID.
Preserve the existing manifest/output-member checks and byte-version unknown.

The host follows only the explicit typed dependency from an acquired object's
receipt_row selection to its WorkspaceReceipt, and from that same object's
existing task_info_object association to the selected job_result_id receipt.
Both records require actual possession and completed original actions. The
original request, resource and handoff must agree. These are already-selected
operational identity dependencies; their native bytes may be supplied for
validation. They grant no stdout/stderr bytes and create no additional action.
Arbitrary references inside metadata are still not followed. Other TaskInfo
content, including logs, retains 014's explicit-content requirement.

Verify against the exact failed real-host run and new authentic acquisitions,
with wrong-row, wrong-task, altered-native-value and unreceived-log negatives.
The prior full synthetic C/E/F tests must still run, but do not establish this
new production path by themselves. Original facade pins remain historical;
new configuration pins are computed only after all changes are stable.
