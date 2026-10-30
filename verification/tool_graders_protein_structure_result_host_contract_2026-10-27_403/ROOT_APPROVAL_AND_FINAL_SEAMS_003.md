# Root approval and exact final seams, 403/003

2026-10-27. Root read the full original proposal, the revised record/port and
completion sections, and the complete additive002 lock/thread contract. The
following exact files are approved for coding, subject to the corrections here:

- PROPOSED_HOST_CONTRACT_001.md SHA256
  `c77e31299e540389804c93fade3f4e3856d7622dea9e8c1c0c8cdac7d49e8b7e`.
- ACTION_STATE_AND_THREAD_HANDOFF_002.md SHA256
  `d221f0f80afb5b92cc57d50ad24f4d3b39b19a45b502a834dbf0aa3e3eec2110`.

Those files now remain unchanged. This approves implementation boundaries, not
implementation completion or a new scientific design. The immutable user goal,
394 public ports, original A/B/C/D1 science and existing runtime remain authority.

## One correction to root's own method-name instruction

Root's instruction that the target description method was named
`operation_information` was wrong. The actual existing method is
`ExecutionTargetReader.describe_target(self, handle, scope, *, selector=None)`
in execution_progress.py, with an ExecutionProgressProvider wrapper of the same
name. Root inspected the definitions and ExecutionEpisodes.decision_context
call. Root owns that future description integration. Do not add or rename a
method to `operation_information`. The separate405 method correction remains
`returnable_handoff`. Both001/002 references to operation_information are
superseded by this correction; their original text is retained.

## One additional lock-bound accessor

The receipt lane supplies this small exact method so the host does not inspect
the opaque action's private ownership or lock token:

```python
def require_action(self, action: ProteinResultAction) -> None: ...
```

It rejects an action from another instance, a fabricated action or an expired
context; it changes nothing. All action-taking receipt methods and the host's
`_prepare_worker` call it. The host still checks its worker plan directory and
the absence of a parent Store transaction before the thread await. All other002
signatures, path ownership and cancellation-drain semantics stand unchanged.

## Private qualification versus committed completion

`publication.delivery_complete` records whether the selected collect's actual
work meets001's acquisition/worker/accounting criteria. It may be true in the
immutable private receipt just before runtime stores the returned outcome.
That private flag is not yet a public completion fact or authority grant.

Only `read_completed` may make that flag visible as completed work: require the
non-null matching completed runtime collect outcome. Thus the001 truth-table
row for a pending collect means public completion is false/unavailable; it must
not force an otherwise qualified staged receipt's immutable flag to false and
then rewrite it later. Private replay returns the same original receipt for
the existing runtime to record. No synthetic action or later receipt mutation.

`completed_receipts(context)` enumerates only completed collect actions. It
ignores pending/status actions and returns an empty list when none qualify,
after authenticating the context. An explicit `read_completed` of a pending or
status operation rejects. Do not confuse an empty current fact set during a
valid construction/iteration with an affirmative pending-action authorization.

The rest of the completion truth table is approved: absent/unauthenticated
original saved input or missing qualified later components is incomplete;
properly qualified but scientifically unavailable/invalid values can complete
a fully acquired request. Later byte loss never rewrites the recorded outcome.

## Historical dispatch and existing origin value

`NativeProteinStructureResults.applies(context)` is a pure role/selector-family
test: results role and selector version `protein_structure_result_selector_v1`.
It reads no target/artifact/resource. Exact native-target authorization occurs
in the selected-assignment/receipt paths. This pure dispatch is not a grant.
Root must call metadata-only facts/credit/completion paths before any generic
`_target` read that would reopen old handoff artifact bytes. The three approved
historical read ports and constructors remain free of producer/liveness checks.

The existing producer-bundle origin value is exactly:

```python
{
    'content_location': 'retained_complete_producer_bundle',
    'attempt_output_version': 'original_producer_manifest_and_verified_file_digests',
    'window_consistency': 'complete_files_matched_to_original_manifest',
    'completion_basis': 'requested_acquisition_and_observed_successful_attempt',
}
```

It is already permitted by the existing execution_result_origin schema. Return
it only for qualified complete original successful native acquisition, as001
requires; saved or failed native work returns null. Add no fifth protein source.

## Coding ownership and handoff

Fresh lane406 owns `protein_structure_result_receipts.py`, its focused tests
and packet406. It exports all closed TypedDict/private types from001/002,
ProteinResultReceipts and ProteinResultAction. It imports no result host and
performs no scientific byte decoding, publication, parsing or recalculation.

Fresh lane407 owns `native_protein_structure_results.py`, its focused tests
and packet407. It imports those exact406 types/ports and consumes392/393/396,
397/398/399/400 and root404 through their approved ports. It does not duplicate
receipt layout/proof or modify shared consumers. Both lanes can code against
these fixed interfaces immediately. One lane's final tests are not a blocker
for writing the other's implementation.

Root owns all remaining ExecutionEpisodes/service-factory/target-description,
communication/credit/endpoint integration and the complete receiving-episode
test. No prompt implementation, literature work, scoring change or accounting
acceptance is delegated. Keep112/308 until the entire original tool outcome is
demonstrated. Every verification uses the existing20GiB/4GiB/zero-swap/no-wall
local_jobs path with immutable executed snapshots and retained failures.
