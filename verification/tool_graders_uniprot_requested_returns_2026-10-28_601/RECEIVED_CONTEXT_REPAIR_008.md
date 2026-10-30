# Scientific context follows received records independently of credit

This is a repair contract under the original goal, not a goal or scope change.
Check060 exposed the supported custom-credit path described in
`verification/tool_graders_uniprot_host_returns_2026-10-28_606/RECEIPT_VIEW_TRACE_001.md`.

`episode_record_receipts=True` creates and maintains the actual episode ledger.
Nevertheless, `Workflow.working_state` currently filters scientific records only
when the selected credit callable advertises `requires_episode_receipts`.
A custom scalar without that attribute therefore exposes the global scoped
record view. `DecisionSource.call` then admits those automatically visible
records as `decision_input`. An unrequested source becomes inherited knowledge
despite a correctly restricted child form.

## Ownership and exact changes

Root owns the narrow edits to `gene_annotation_episode/runtime.py` and the
existing custom-parent-credit regression in `tests/test_episode_receipts.py`.
Worker606 retains ownership of its UniProt host files and the four actual
Workflow grant variants. No source or scientific scoring implementation changes.

Add `Workflow.uses_received_record_context(source) -> bool`: true when the
episode has the existing receipts ledger and is a scientific source. Use this
one condition for scientific `working_state` selection and for suppressing
automatic `decision_input` admission in both direct and exchange dispatch.
Requested form admission, original caller inputs and actual own-operation
receipts remain the routes that deliver scientific records.

Keep `receipt_projection`, `projection_arguments`, credit callables, numerical
units, continuation and action observations unchanged. Their existing attribute
still controls whether a credit callable receives its supported keyword inputs;
it no longer controls scientific information visibility.

Saved calls retain their original dispatched contexts and responses. Existing
receipt rows, completed observations and frozen inheritance prefixes are not
rewritten or deleted. No new transcript, store, record import or model call is
introduced. Resource-role assignment views and receipt-disabled legacy callers
retain their existing paths; this repair does not claim a universal capability
sandbox or complete the pending text-presentation templates.

## Verification

The four real UniProt Workflow cases keep a custom zero-credit callable without
the marker and `episode_record_receipts=True`. They must show the received
record view, exact requested fields through both parents, no source/sequence
grant beyond the requested combination, and unchanged closed replay after
native bytes are withdrawn. No permissive fixture marker may hide this defect.

The existing direct-protocol regression currently expects an unreceived stored
finding to appear in a child solely because its parent uses a different credit
callable. Correct that expectation: neither episode receives that finding, and
the child's finding progress starts at zero. This verifies the other dispatch
branch without injecting pre-existing source records as caller knowledge.

Run the relevant receipt, default-binding and decision-exchange regressions in
the bounded runner. Treat failures according to their actual causes; preserve
all earlier run evidence and report any unverified boundary explicitly.
